"""The independent shot labeler with a fake Claude (specs/021 T006; FR-002, FR-010)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import labeler  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"
FAKE = REPO / "tests/online/fake_claude"


class Labeler(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(exist_ok=True)
        self.d = Path(tempfile.mkdtemp(dir=TMP))
        self.sheet = self.d / "sheet-1.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x180", "-frames:v", "1",
                        str(self.sheet)], check=True)
        self.log = self.d / "log.jsonl"
        self.old = {k: os.environ.get(k) for k in ("STUDIO_CLAUDE_BIN", "FAKE_CLAUDE_LOG", "FAKE_LABELS",
                                                   "FAKE_LABELS_MODE", "STUDIO_EDITOR_MODEL", "STUDIO_MODEL")}
        os.environ.update(STUDIO_CLAUDE_BIN=str(FAKE), FAKE_CLAUDE_LOG=str(self.log))
        for k in ("FAKE_LABELS", "FAKE_LABELS_MODE", "STUDIO_EDITOR_MODEL", "STUDIO_MODEL"):
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_labels_and_prompt(self):
        f = self.d / "labels.json"
        f.write_text(json.dumps({"S001": ["huge", "top", False], "S002": ["ecu", "eye", True]}))
        os.environ["FAKE_LABELS"] = str(f)
        r = labeler.label([(self.sheet, ["S001", "S002", "S003"])], {"S001": {"focused_share": 0.5, "sharpest_at": [1, 1]}})
        self.assertEqual(r["labels"]["S001"]["scale"], "huge")
        self.assertTrue(r["labels"]["S002"]["foreground_blur"])
        self.assertEqual(r["labels"]["S003"]["scale"], "med")
        self.assertEqual(r["calls"], 1)
        args = json.loads(self.log.read_text().splitlines()[-1])
        self.assertIn("--model", args)
        self.assertEqual(args[args.index("--model") + 1], "claude-opus-5-5")
        self.assertEqual(args[args.index("--tools") + 1], "Read")

    def test_prompt_has_only_sheets_and_ids(self):
        p = labeler.prompt([self.sheet], ["P01.0"], {"P01.0": {"focused_share": 0.25, "sharpest_at": [2, 1]}})
        self.assertIn(str(self.sheet.resolve()), p)
        self.assertIn("- P01.0 focus=0.25 sharpest=2,1", p)
        self.assertNotIn("SCRIPT", p)

    def test_bad_answers_and_failure(self):
        os.environ["FAKE_LABELS_MODE"] = "bad"
        with self.assertRaises(labeler.LabelError):
            labeler.label([(self.sheet, ["S001"])], {})
        self.assertEqual(len(self.log.read_text().splitlines()), 2)          # asked twice
        os.environ["FAKE_LABELS_MODE"] = "fail"
        with self.assertRaises(labeler.LabelError):
            labeler.label([(self.sheet, ["S001"])], {})

    def test_batches_of_four_sheets(self):
        groups = [(self.sheet, [f"S{i:03d}"]) for i in range(1, 10)]
        self.assertEqual(labeler.label(groups, {})["calls"], 3)

    def test_schema_v3_depth(self):
        """specs/038: cam_height, lens, depth, layers, occluder; measured lines go into the prompt."""
        f = self.d / "labels.json"
        f.write_text(json.dumps({"S001": ["huge", "high", False, "hall",
                                          {"cam_height": "high", "lens": "wide", "depth": "deep",
                                           "layers": ["far", "fg", "mid"], "occluder": True}]}))
        os.environ["FAKE_LABELS"] = str(f)
        r = labeler.label([(self.sheet, ["S001", "S002"])], {"S001": {"vanish": {"horizon": 0.25, "hfov_deg": 70.0,
                                                                                 "lines": 90}}})
        a, b = r["labels"]["S001"], r["labels"]["S002"]
        self.assertEqual((a["cam_height"], a["lens"], a["depth"], a["occluder"]), ("high", "wide", "deep", True))
        self.assertEqual(a["layers"], ["fg", "mid", "far"])                 # in depth order
        self.assertEqual((b["cam_height"], b["depth"], b["layers"]), ("eye", "mid", ["mid", "bg"]))
        p = labeler.prompt([self.sheet], ["S001", "S002"], {"S001": {"vanish": {"horizon": 0.25, "hfov_deg": 70.0,
                                                                                "lines": 90}}})
        self.assertIn("horizon=0.25 hfov=70.0 lines=90", p)
        self.assertIn("- S002 focus=? sharpest=?,? lines=? (no measure)", p)
        self.assertIn("cam_height", json.dumps(labeler.SCHEMA))

    def test_vanish_disagrees(self):
        self.assertTrue(labeler.vanish_disagrees({"cam_height": "low"}, {"horizon": 0.2}))
        self.assertTrue(labeler.vanish_disagrees({"cam_height": "top"}, {"horizon": 0.8}))
        self.assertFalse(labeler.vanish_disagrees({"cam_height": "high"}, {"horizon": 0.2}))
        self.assertFalse(labeler.vanish_disagrees({"cam_height": "low"}, {"horizon": None}))
        self.assertFalse(labeler.vanish_disagrees({"cam_height": "low"}, None))
        self.assertTrue(labeler.contradicts({"scale": "wide", "cam_height": "low"}, {}, {"horizon": 0.1}))

    def test_contradicts_and_steps(self):
        self.assertTrue(labeler.contradicts({"scale": "cu"}, {"focused_share": 1 / 12, "sharpest_at": [0, 2]}))
        self.assertFalse(labeler.contradicts({"scale": "cu"}, {"focused_share": 0.5, "sharpest_at": [1, 1]}))
        self.assertFalse(labeler.contradicts({"scale": "huge"}, {"focused_share": 1.0, "sharpest_at": [1, 1]}))
        self.assertEqual(labeler.steps_apart("ecu", "med"), 2)
        self.assertIsNone(labeler.steps_apart("insert", "cu"))


if __name__ == "__main__":
    unittest.main()
