"""Shot grammar of a reference set (specs/021 T009; US1; FR-001 – FR-006; SC-001 agreement maths)."""
import json
import os
import unittest
from pathlib import Path

from helpers import FX, REPO, Project, need_fixtures
from sl import fetch, measure, refset, shots, summary

FAKE = REPO / "tests/online/fake_claude"


class Shots(unittest.TestCase):
    def setUp(self):
        need_fixtures(self)
        if not (FX / "shots6.mp4").exists():
            self.skipTest("shots6.mp4 is not made yet: run sh tests/learn/run.sh")
        self.p = Project()
        self.old = {k: os.environ.get(k) for k in ("STUDIO_CLAUDE_BIN", "FAKE_LABELS", "FAKE_CLAUDE_LOG", "STUDIO_EDITOR_MODEL")}
        os.environ["STUDIO_CLAUDE_BIN"] = str(FAKE)
        os.environ.pop("STUDIO_EDITOR_MODEL", None)
        os.environ["FAKE_CLAUDE_LOG"] = str(self.p.dir / "claude.log")
        fetch.fetch_files("six", [FX / "shots6.mp4"])
        measure.measure_set("six")

    def tearDown(self):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.p.close()

    def labels(self, mapping):
        f = self.p.dir / "labels.json"
        f.write_text(json.dumps(mapping))
        os.environ["FAKE_LABELS"] = str(f)

    def test_split_focus_places_sheets(self):
        shots.shots_set("six", log=lambda *_: None)
        d = json.loads(shots.shots_file("six", "v01").read_text())
        rows = d["shots"]
        self.assertEqual(len(rows), 6, [(r["t0"], r["t1"]) for r in rows])
        for k, r in enumerate(rows):
            self.assertAlmostEqual(r["t0"], 3.0 * k, delta=1 / 24 + 0.01)
        fs = [r["focus"]["focused_share"] for r in rows]
        self.assertEqual(fs[1], 0.0)                                      # shot 2: all blurred
        self.assertGreater(fs[3], 0.0)
        self.assertLessEqual(fs[3], 1 / 12 + 1e-6)                        # shot 4: one corner
        self.assertTrue(fs[0] >= 0.9 and fs[2] >= 0.9 and fs[4] >= 0.9)
        sets = [r["set"] for r in rows]
        self.assertEqual(sets[0], sets[2])
        self.assertEqual(sets[1], sets[4])
        self.assertEqual(len(set(sets)), 4, sets)
        sheet = refset.profile_dir("six", "v01") / "shot-sheets" / "v01_shots_1.jpg"
        from PIL import Image
        self.assertLess(Image.open(sheet).width, 1280)
        self.assertEqual(rows[0]["evidence"], "v01_shots_1.jpg#1")
        # resume: a second run does nothing
        self.assertEqual(shots.shots_set("six", log=lambda *_: None), [])

    def test_label_edit_summary_and_agreement(self):
        shots.shots_set("six", log=lambda *_: None)
        self.labels({"S001": ["cu", "eye", True], "S002": ["ecu", "low", False], "S003": ["huge", "top", False],
                     "S004": ["cu", "eye", False], "S005": ["wide", "ots", True], "S006": ["insert", "eye", False]})
        shots.label_set("six", log=lambda *_: None)
        d = json.loads(shots.shots_file("six", "v01").read_text())
        self.assertEqual([r["scale"] for r in d["shots"]], ["cu", "ecu", "huge", "cu", "wide", "insert"])
        self.assertTrue(d["shots"][3]["check"])                           # a close-up whose sharp tile is one corner
        row = shots.set_label("six", "v01:S002", ["scale=huge"])
        self.assertEqual(row["edited_by"], "user")
        shots.label_set("six", log=lambda *_: None)                       # a later run keeps the hand edit
        d = json.loads(shots.shots_file("six", "v01").read_text())
        self.assertEqual(d["shots"][1]["scale"], "huge")

        s = summary.build("six")
        vj = json.loads((refset.profile_dir("six", "v01") / "video.json").read_text())
        g = vj["shot_grammar"]
        self.assertEqual(g["labelled"], 5)
        self.assertEqual(g["inserts"], 1)
        self.assertEqual(g["scale_share"]["huge"], 0.4)
        self.assertEqual(g["subject_sharp_share"], 0.8)                   # 4 of 5 have a sharp tile
        self.assertEqual(g["sets"], 4)
        self.assertIn("shot_grammar", s["by_orientation"]["landscape"])
        self.assertIn("Shot grammar", (refset.set_dir("six") / "profile" / "summary.md").read_text())

        # an independent second pass that disagrees on two shots
        self.labels({"v01-S001": ["med", "eye", True], "v01-S002": ["huge", "low", False], "v01-S003": ["huge", "high", False],
                     "v01-S004": ["cu", "eye", False], "v01-S005": ["wide", "ots", True]})
        rep = shots.second_pass("six", n=5, log=lambda *_: None)
        self.assertEqual(rep["n"], 5)
        self.assertEqual(rep["scale_same"], 0.8)
        self.assertEqual(rep["scale_within_one"], 1.0)
        self.assertEqual(rep["angle_same"], 0.8)
        self.assertTrue((refset.set_dir("six") / "profile" / "agreement.json").exists())

    def test_grammar_runs_and_changes(self):
        rows = [{"id": f"S{i}", "t0": i, "t1": i + 1, "scale": s, "angle": "eye", "set": b, "focus": {"focused_share": 0.5}}
                for i, (s, b) in enumerate([("cu", "B1"), ("cu", "B1"), ("cu", "B2"), ("huge", "B2"), ("insert", "B3"), ("ecu", "B1")])]
        g = shots.grammar(rows)
        self.assertEqual(g["longest_same_scale"], 3)
        self.assertEqual(g["scale_change_share"], round(1 / 3, 3))       # cu-cu, cu-cu, cu-huge (pairs with the insert skipped)
        self.assertEqual(g["top_set_share"], 0.5)


if __name__ == "__main__":
    unittest.main()
