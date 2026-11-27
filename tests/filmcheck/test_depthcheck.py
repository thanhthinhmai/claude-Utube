"""qc depth (specs/038 T034, contracts/style-depth.md): shots closer or shallower than the reference are blocked."""
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
from filmcheck import depthcheck, tiers  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"
FAKE = REPO / "tests/online/fake_claude"

WIDE = {"n": 12, "cam_height": {"eye": 0.6, "high": 0.4}, "lens": {"wide": 0.5, "normal": 0.45, "long": 0.05},
        "depth": {"deep": 0.7, "mid": 0.3}, "layers_p25": 2, "layers_p50": 3, "occluder_share": 0.4, "evidence": []}
DEPTH = {"version": 1, "by_size": {"wide": WIDE, "med": {**WIDE, "n": 8}, "cu": {**WIDE, "n": 3, "layers_p25": 1}}}


def lab(scale="wide", lens="normal", depth="deep", layers=("mid", "bg", "far"), **kw):
    return {"scale": scale, "lens": lens, "depth": depth, "layers": list(layers), "cam_height": "eye", **kw}


class Rules(unittest.TestCase):
    def rule_of(self, plan, label, plans=None, depth=DEPTH):
        iss, warn = depthcheck.rules({"S1": plan}, {"S1": label}, depth, plans or {})
        return [(i["rule"], i["severity"]) for i in iss], warn

    def test_pass(self):
        self.assertEqual(self.rule_of({"size": "wide"}, lab())[0], [])

    def test_depth_close(self):
        self.assertEqual(self.rule_of({"size": "wide"}, lab(scale="med"))[0], [("depth_close", "block")])
        self.assertEqual(self.rule_of({"size": "wide"}, lab(lens="long"))[0], [("depth_close", "block")])

    def test_depth_shallow(self):
        self.assertEqual(self.rule_of({"size": "wide"}, lab(layers=("mid",)))[0], [("depth_shallow", "block")])
        self.assertEqual(self.rule_of({"size": "wide"}, lab(depth="shallow"))[0], [("depth_shallow", "block")])
        self.assertEqual(self.rule_of({"size": "wide"}, lab(depth="mid"))[0], [])      # 30 % of the reference is mid

    def test_card_angle(self):
        got = self.rule_of({"size": "wide"}, lab(), plans={"S1": {"card_angle_max": 80}})[0]
        self.assertEqual(got, [("card_angle", "block")])
        self.assertEqual(self.rule_of({"size": "wide"}, lab(), plans={"S1": {"card_angle_max": 60}})[0], [])

    def test_few_samples_only_warn(self):
        got, warn = self.rule_of({"size": "cu"}, lab(scale="ecu", depth="shallow", layers=("mid",)))
        self.assertTrue(got and all(s == "warn" for _, s in got))
        self.assertIn("few_samples", [w["rule"] for w in warn])

    def test_size_share_warning(self):
        plans = {f"S{i}": {"size": "cu" if i < 8 else "wide"} for i in range(10)}
        labels = {s: lab(scale=p["size"]) for s, p in plans.items()}
        _, warn = depthcheck.rules(plans, labels, DEPTH, {})
        self.assertIn("size_share", [w["rule"] for w in warn])


class Run(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(exist_ok=True)
        self.root = Path(tempfile.mkdtemp(dir=TMP))
        self.d = self.root / "films" / "f1"
        (self.d / "animatic" / "shots").mkdir(parents=True)
        (self.d / "ae").mkdir()
        (self.d / "ae" / "shots.jsx").write_text("//\n")
        doc = {"engine": "ae", "fps": 24, "size": [320, 180], "shots": ["S1", "S2"], "ae_files": ["shots.jsx"],
               "style": "deep-style", "shot_plan": {"S1": {"size": "wide"}, "S2": {"size": "wide"}}}
        (self.d / "film.json").write_text(json.dumps(doc))
        for s in ("S1", "S2"):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x180:d=1:r=24",
                            str(self.d / "animatic" / "shots" / f"{s}.mp4")], check=True)
        st = self.root / "my-styles" / "deep-style"
        st.mkdir(parents=True)
        (st / "shots.json").write_text(json.dumps({"depth": DEPTH}))
        self.labels = self.root / "labels.json"
        self.labels.write_text(json.dumps({"S2": ["wide", "eye", False, "hall", {"depth": "deep",
                                                                                 "layers": ["mid", "bg", "far"]}],
                                           "S1": ["med", "eye", False, "hall", {"depth": "deep",
                                                                                "layers": ["mid", "bg", "far"]}]}))
        self.old = {k: os.environ.get(k) for k in ("STUDIO_CLAUDE_BIN", "FAKE_LABELS", "STUDIO_ROOT", "STUDIO_JOB",
                                                   "FAKE_LABELS_MODE")}
        os.environ.update(STUDIO_CLAUDE_BIN=str(FAKE), FAKE_LABELS=str(self.labels), STUDIO_ROOT=str(self.root))
        os.environ.pop("STUDIO_JOB", None)
        os.environ.pop("FAKE_LABELS_MODE", None)

    def tearDown(self):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.root, ignore_errors=True)

    def test_run_gate_and_exception(self):
        self.assertTrue(depthcheck.gate(self.d))                               # not run yet: blocks
        r = depthcheck.run(self.d, say=lambda x: None)
        self.assertFalse(r["pass"])
        self.assertEqual([(i["ref"], i["rule"]) for i in r["issues"] if i["severity"] == "block"], [("S1", "depth_close")])
        self.assertEqual(tiers.load_tier(self.d, "depth")["fingerprint"], r["fingerprint"])
        why = depthcheck.gate(self.d)
        self.assertTrue(any("S1" in w and "depth_close" in w for w in why))
        os.environ["STUDIO_JOB"] = "job-1"                                     # FR-014: never inside a job
        with self.assertRaises(tiers.TierError):
            tiers.add_exception(self.d, "S1", "depth_close", "the close-up is the point")
        os.environ.pop("STUDIO_JOB")
        tiers.add_exception(self.d, "S1", "depth_close", "the close-up is the point")
        self.assertTrue(depthcheck.recompute(self.d)["pass"])
        self.assertEqual(depthcheck.gate(self.d), [])
        (self.d / "film.json").write_text((self.d / "film.json").read_text().replace('"wide"}}', '"med"}}'))
        self.assertTrue(any("changed" in w for w in depthcheck.gate(self.d)))  # stale after a change

    def test_gate_blocks_ae_render(self):
        """T037: ae render stops (exit 1) and names the shot while qc depth fails."""
        import contextlib
        import io
        from unittest import mock
        from ae import cli as aecli
        depthcheck.run(self.d, say=lambda x: None)
        err = io.StringIO()
        with mock.patch("filmcheck.points.gate", return_value=[]), contextlib.redirect_stderr(err), \
                mock.patch.object(aecli, "do_build", side_effect=AssertionError("must not build")):
            code = aecli.main(["render", "f1", "--dir", str(self.d)])
        self.assertEqual(code, 1)
        self.assertIn("S1 depth_close", err.getvalue())

    def test_reuses_labels(self):
        depthcheck.run(self.d, say=lambda x: None)
        os.environ["FAKE_LABELS_MODE"] = "fail"                                # a second run must not call Claude
        r = depthcheck.run(self.d, say=lambda x: None)
        self.assertTrue(r["measures"]["labels"]["reused"])

    def test_style_without_depth(self):
        (self.root / "my-styles" / "deep-style" / "shots.json").write_text("{}")
        with self.assertRaises(depthcheck.DepthError):
            depthcheck.run(self.d, say=lambda x: None)
        self.assertEqual(depthcheck.gate(self.d), [])                          # nothing to compare: no block


if __name__ == "__main__":
    unittest.main()
