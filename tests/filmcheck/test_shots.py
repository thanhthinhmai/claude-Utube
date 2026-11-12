"""Tier 2, one frame per shot (specs/020 T021; US2; FR-011 – FR-015; SC-003)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import shotcheck, tiers  # noqa: E402

import samples  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"
LIB = REPO / "lib" / "lemo-opuscar"
PY = str(REPO / "tools" / ".venv" / "bin" / "python") if (REPO / "tools" / ".venv" / "bin" / "python").is_file() else sys.executable
HAVE_PAGE = shutil.which("node") and (LIB / "node_modules" / "playwright-core").is_dir()
SHOT = 2.0
FAULTS = {3: ("flat", {"look": "flat"}), 9: ("dark", {"look": "dark"}), 15: ("blown", {"look": "blown"}),
          21: ("missing_glyph", {}), 27: ("text_over_subtitle", {})}


def shots6():
    shots = [{"id": f"P{i:02d}.0", "t0": i * SHOT, "t1": (i + 1) * SHOT} for i in range(37)]
    for i, (_, look) in FAULTS.items():
        shots[i].update(look)
    shots[33]["look"] = "cardbg"                           # US2 AC4: a dark plain card background with its text
    cards = [{"id": "glyph", "t0": 21 * SHOT + 0.2, "t1": 22 * SHOT - 0.2, "text": "ODD  SIGN"},
             {"id": "low", "t0": 27 * SHOT + 0.2, "t1": 28 * SHOT - 0.2, "text": "LOW CARD", "pos": "bottom"},
             {"id": "title", "t0": 33 * SHOT + 0.2, "t1": 34 * SHOT - 0.2, "text": "CHAPTER TWO"}]
    cues = [[27 * SHOT, 28 * SHOT, "A subtitle under the card"]]
    return shots, cards, cues


@unittest.skipUnless(HAVE_PAGE, "needs node and the library's playwright-core")
class ShotCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TMP.mkdir(exist_ok=True)
        cls.root = Path(tempfile.mkdtemp(dir=TMP))
        st = cls.root / "my-styles" / "tier-style"
        st.mkdir(parents=True)
        (st / "qc.json").write_text(json.dumps({"luma_p50": [0.6, 0.8]}))      # the film is darker than this style
        shots, cards, cues = shots6()
        cls.d = samples.make_tier_film(cls.root, "shots-6", shots=shots, cards=cards, cues=cues, style="tier-style")
        cls.p = cls.cli("qc", "shots", "shots-6", "--json")
        cls.r = json.loads(cls.p.stdout) if cls.p.stdout.strip() else None

    @classmethod
    def cli(cls, *args):
        env = {**os.environ, "STUDIO_LIB": str(LIB), "STUDIO_ROOT": str(cls.root)}
        return subprocess.run([PY, str(REPO / "tools" / "filmcheck" / "cli.py"), *args], capture_output=True, text=True,
                              env=env, cwd=str(cls.root), timeout=900)

    def test_sc003_six_faults(self):
        self.assertIsNotNone(self.r, self.p.stderr)
        self.assertEqual(self.p.returncode, 1)
        got = {(i["ref"], i["rule"]) for i in self.r["issues"]}
        want = {(f"P{i:02d}.0", rule) for i, (rule, _) in FAULTS.items()} | {("film", "style_luma")}
        self.assertTrue(want <= got, sorted(got))
        fault_shots = {f"P{i:02d}.0" for i in FAULTS} | {"film"}
        false = {ref for ref, _ in got if ref not in fault_shots}
        self.assertLessEqual(len(false), 1, sorted(got))                      # ≤ 1 good shot reported in 31
        self.assertNotIn("P33.0", false)                                      # the card is not "flat"
        self.assertEqual([i["severity"] for i in self.r["issues"] if i["rule"] == "style_luma"], ["warn"])

    def test_sheet_with_shot_ids(self):
        sheets = self.r["measures"]["sheets"]
        self.assertTrue(sheets)
        self.assertTrue((self.d / sheets[0]).is_file())
        self.assertTrue((self.d / ".check" / "shots" / "P03.0.jpg").is_file())

    def test_gate_exception_and_accept(self):
        self.cli("qc", "plan", "shots-6")                     # the cards are short (card_read); only the shot part matters here
        gate = self.cli("render-gate", "shots-6")
        self.assertEqual(gate.returncode, 1)
        self.assertIn("frame problem", gate.stderr)
        self.assertEqual(self.cli("qc", "except", "shots-6", "P03.0", "flat").returncode, 2)          # no reason
        self.assertEqual(self.cli("qc", "except", "shots-6", "P03.0", "missing_glyph", "--reason", "x").returncode, 2)
        for i, (rule, _) in FAULTS.items():
            if rule != "missing_glyph":
                self.assertEqual(self.cli("qc", "except", "shots-6", f"P{i:02d}.0", rule, "--reason", "on purpose").returncode, 0)
        r = tiers.load_tier(self.d, "shots")
        self.assertEqual([i["rule"] for i in r["issues"] if i["severity"] == "block" and not i.get("excepted")],
                         ["missing_glyph"])
        self.assertEqual(self.cli("qc", "accept-style", "shots-6").returncode, 2)                       # no reason
        self.assertEqual(self.cli("qc", "accept-style", "shots-6", "--reason", "a darker film on purpose").returncode, 0)
        gate = self.cli("render-gate", "shots-6")
        self.assertIn("1 open frame problem", gate.stderr)
        self.assertNotIn("style warning", gate.stderr)
        self.assertIn("a darker film on purpose", (self.d / "CHECKS.md").read_text())


class Scoring(unittest.TestCase):
    """The scoring alone, on measured numbers (no browser)."""

    def frame(self, shot, t, **m):
        base = {"luma_mean": 0.3, "sat_p50": 0.4, "dominant_share": 0.1, "luma_sd": 0.15, "content_p50": 0.3,
                "blown_share": 0.0, "text_share": 0.0}
        base.update(m)
        return {"key": shot, "shot": shot, "t": t, "texts": [], "m": base}

    def test_rules(self):
        shots = [{"id": f"S{i}", "t0": i * 2.0, "t1": i * 2.0 + 2} for i in range(4)]
        frames = [self.frame("S0", 1, dominant_share=0.7), self.frame("S1", 3, luma_sd=0.01, text_share=0.05),
                  self.frame("S2", 5, content_p50=0.02, luma_sd=0.01), self.frame("S3", 7, blown_share=0.5, dominant_share=0.9)]
        iss, meas, skipped = shotcheck.score(frames, shots, None, {}, 8.0)
        self.assertEqual([(i["ref"], i["rule"]) for i in iss], [("S0", "flat"), ("S2", "dark"), ("S3", "blown")])
        self.assertIn("style: no measurements", skipped[-1])
        iss, _, skipped = shotcheck.score(frames[:1], shots[:1], None, {"cuts_per_min": [16, 26]}, 2.0)
        self.assertIn("under 30 s", skipped[-1])

    def test_weighted_median(self):
        self.assertEqual(shotcheck.wmedian([(0.1, 1), (0.5, 5), (0.9, 1)]), 0.5)


if __name__ == "__main__":
    unittest.main()
