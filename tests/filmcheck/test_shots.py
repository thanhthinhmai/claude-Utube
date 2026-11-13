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
        env = {**os.environ, "STUDIO_LIB": str(LIB), "STUDIO_ROOT": str(cls.root),
               "STUDIO_CLAUDE_BIN": str(REPO / "tests/online/fake_claude")}       # never a real Claude in tests (specs/021)
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
        j = json.loads(self.cli("qc", "except", "shots-6", "--list", "--json").stdout)              # T055
        self.assertEqual(len(j["exceptions"]), 4)
        self.assertEqual(self.cli("qc", "accept-style", "shots-6").returncode, 2)                       # no reason
        acc = self.cli("qc", "accept-style", "shots-6", "--reason", "a darker film on purpose", "--json")
        self.assertEqual(acc.returncode, 0)
        self.assertEqual(json.loads(acc.stdout)["style_accept"]["reason"], "a darker film on purpose")
        gate = self.cli("render-gate", "shots-6")
        self.assertIn("1 open frame problem", gate.stderr)
        self.assertNotIn("style warning", gate.stderr)
        self.assertIn("a darker film on purpose", (self.d / "CHECKS.md").read_text())


SEQ = ("cu huge cu wide cu med cu huge cu wide " "cu cu cu cu cu cu " "med cu huge cu wide cu med cu huge cu wide cu med huge").split()


@unittest.skipUnless(HAVE_PAGE, "needs node and the library's playwright-core")
class Grammar(unittest.TestCase):
    """specs/021 T023: blurred frames block; the film's shot grammar against the style's (labels from a fake Claude)."""

    @classmethod
    def setUpClass(cls):
        TMP.mkdir(exist_ok=True)
        cls.root = Path(tempfile.mkdtemp(dir=TMP))
        st = cls.root / "my-styles" / "g-style"
        st.mkdir(parents=True)
        (st / "shots.json").write_text(json.dumps({
            "scale_share": {"cu": [0.1, 0.35], "huge": [0.1, 0.3]}, "angle_share": {"eye": [0.35, 0.6]},
            "scale_change_share": [0.75, 0.95], "longest_same_scale_max": 3, "focused_share_p50": [0.0, 1.0]}))
        shots = [{"id": f"P{i:02d}.0", "t0": i * 2.0, "t1": i * 2.0 + 2, "set": "room"} for i in range(30)]
        for i in (5, 15, 25):
            shots[i]["look"] = "blur"
        cls.d = samples.make_tier_film(cls.root, "grammar-30", shots=shots, cards=[], style="g-style")
        cls.labels = cls.root / "labels.json"
        cls.labels.write_text(json.dumps({f"P{i:02d}.0": [sc, "low" if i in (3, 17, 22) else "eye", False]
                                          for i, sc in enumerate(SEQ)}))
        cls.log = cls.root / "claude.log"
        cls.r = cls.run_shots()

    @classmethod
    def run_shots(cls, **extra):
        env = {**os.environ, "STUDIO_LIB": str(LIB), "STUDIO_ROOT": str(cls.root), "STUDIO_CLAUDE_BIN": str(REPO / "tests/online/fake_claude"),
               "FAKE_LABELS": str(cls.labels), "FAKE_CLAUDE_LOG": str(cls.log), **extra}
        p = subprocess.run([PY, str(REPO / "tools/filmcheck/cli.py"), "qc", "shots", "grammar-30", "--json"], capture_output=True,
                           text=True, env=env, cwd=str(cls.root), timeout=900)
        return json.loads(p.stdout) if p.stdout.strip() else {"error": p.stderr}

    def test_blurred_frames_block(self):
        got = sorted(i["ref"] for i in self.r["issues"] if i["rule"] == "blurred")
        self.assertEqual(got, ["P05.0", "P15.0", "P25.0"], self.r.get("error"))
        self.assertTrue(all(i["severity"] == "block" for i in self.r["issues"] if i["rule"] == "blurred"))

    def test_grammar_warnings_with_shot_ids(self):
        rules = {i["rule"]: i for i in self.r["issues"] if i["severity"] == "warn"}
        self.assertIn("style_scale_cu", rules)
        self.assertIn("style_angle_eye", rules)
        run = rules["style_same_scale_run"]
        self.assertEqual(run["shots"], [f"P{i:02d}.0" for i in range(10, 16)])
        self.assertNotIn("style_scale_huge", rules)                        # 5/30 is inside 0.1–0.3
        self.assertNotIn("style_scale_change", rules)
        fault = {"P05.0", "P15.0", "P25.0", "film", "P10.0"}
        false = {i["ref"] for i in self.r["issues"]} - fault
        self.assertLessEqual(len(false), 1, false)                        # SC-005

    def test_labels_are_reused_and_sheets_carry_them(self):
        calls = len(self.log.read_text().splitlines())
        again = self.run_shots()
        self.assertTrue(again["measures"]["labels"]["reused"])
        self.assertEqual(len(self.log.read_text().splitlines()), calls)   # no second labelling for the same source

    def test_labeler_failure_is_a_warning(self):
        (self.d / ".check" / "labels.json").unlink()
        r = self.run_shots(FAKE_LABELS_MODE="fail")
        self.assertIn("shot_grammar_unchecked", [i["rule"] for i in r["issues"]])
        r = self.run_shots()                                               # restore the labels for the other tests
        self.assertFalse(r["measures"]["labels"]["reused"])
        self.assertTrue((self.d / ".check" / "shots" / "label-sheet-1.jpg").exists())   # the unmarked sheet the labeler saw

    def test_style_without_grammar_is_skipped(self):
        (self.root / "my-styles" / "g-style" / "shots.json").rename(self.root / "shots.json.bak")
        try:
            r = self.run_shots()
            self.assertTrue(any("shot grammar" in x for x in r["skipped"]))
        finally:
            (self.root / "shots.json.bak").rename(self.root / "my-styles" / "g-style" / "shots.json")


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
