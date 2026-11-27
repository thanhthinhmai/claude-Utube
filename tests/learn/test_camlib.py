"""specs/039 T012: learn camera (sl/camlib.py) and the camera part of learn save, on a synthetic set."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from helpers import Project
import camsynth
from sl import camlib, refset, save

FIX = Path(tempfile.mkdtemp(prefix="camlib.fx."))
KEY = None


def setUpModule():
    global KEY
    KEY = camsynth.make(FIX / "c.mp4")


def tearDownModule():
    shutil.rmtree(FIX, ignore_errors=True)


SIZES = ["med", "med", "wide", "med", "cu", "wide", "wide", "med"]


class Camlib(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        d = self.p.dir / "references" / "cam-set"
        (d / "videos").mkdir(parents=True)
        shutil.copy2(FIX / "c.mp4", d / "videos" / "v01.mp4")
        refset.write_json(d / "set.json", {"schema": refset.SCHEMA, "set": "cam-set",
                                           "videos": [{"id": "v01", "file": "v01.mp4"}]})
        rows = [{"id": f"S{i + 1:03d}", "t0": s["t0"], "t1": s["t1"], "scale": SIZES[i], "frame": f"f{i}.jpg"}
                for i, s in enumerate(KEY["shots"])]
        rows.append({"id": "S099", "t0": 23.9, "t1": 24.0, "short": True, "frame": "x.jpg"})
        refset.write_json(d / "profile" / "v01" / "shots.json", {"video": "v01", "shots": rows})
        labels = {r["id"]: {"card": False, "people": 1, "action": i % 2 == 0, "outdoor": False, "prop": False,
                            "subject": [40, 10, 60, 90]} for i, r in enumerate(rows[:-1])}
        refset.write_json(d / "profile" / "craft-labels.json", {"version": "x", "videos": {"v01": {"labels": labels}}})
        self.d = d

    def tearDown(self):
        self.p.close()

    def test_camera_json(self):
        tot = camlib.camera_set("cam-set", log=lambda *_: None)
        self.assertEqual(tot["videos"], 1)
        self.assertEqual(tot["need"], [])
        doc = json.loads((self.d / "profile" / "v01" / "camera.json").read_text())
        self.assertEqual(doc["measure"], "camtrack/1")
        rows = {r["id"]: r for r in doc["shots"]}
        r = rows["v01:S001"]
        self.assertEqual((r["size"], r["move"], r["action"]), ("med", "push", True))
        self.assertAlmostEqual(r["zoom_pct"], 6.0, delta=0.3)
        self.assertEqual((r["subject_x"], r["subject_y"], r["subject_h"], r["headroom"]), (50.0, 50.0, 80.0, 10.0))
        self.assertTrue(all((self.d / "profile" / "v01" / p).exists() for p in r["evidence"]))
        self.assertEqual(rows["v01:S002"]["transition"], "cut")
        self.assertIsNone(r["transition"])                          # the first shot has nothing before it
        bad = [x for x in doc["shots"] + doc["skipped"] if x["id"] == "v01:S099"][0]
        self.assertFalse(bad.get("reliable", False))                # 0.1 s: unreliable or skipped, never silent
        self.assertTrue(rows["v01:S007"]["parallax"])
        # a second run with the same shot list does nothing
        tot = camlib.camera_set("cam-set", log=lambda *_: None)
        self.assertEqual(tot["videos"], 0)

    def test_missing_labels_and_video(self):
        (self.d / "profile" / "craft-labels.json").unlink()
        tot = camlib.camera_set("cam-set", log=lambda *_: None)
        self.assertIn("learn craft-label", tot["need"])
        (self.d / "videos" / "v01.mp4").unlink()
        with self.assertRaises(camlib.CameraError):
            camlib.camera_set("cam-set", force=True, log=lambda *_: None)

    def test_summary(self):
        camlib.camera_set("cam-set", log=lambda *_: None)
        sm = camlib.summary(camlib.library("cam-set"))
        self.assertEqual(sm["transition_main"], "cut")
        med = sm["by_size"]["med"]
        self.assertEqual(med["n"], 4)
        self.assertTrue(med["thin"])
        self.assertEqual(len(med["zoom_pct"]), 3)
        self.assertLessEqual(med["zoom_pct"][0], med["zoom_pct"][1])
        self.assertGreater(sm["parallax_share"], 0)
        self.assertIsNotNone(med["ease_q"])

    def test_pick_evidence(self):
        rows = [{"id": f"v:S{i}", "size": ("med", "wide")[i % 2], "move": ("push", "static", "pan")[i % 3],
                 "reliable": i % 4 != 0, "dur": i, "evidence": ["a", "b"]} for i in range(400)]
        got = camlib.pick_evidence(rows, 150)
        self.assertEqual(len(got), 150)
        kinds = {(r["size"], r["move"]) for r in rows if r["id"] in got}
        self.assertEqual(len(kinds), 6)

    def test_write_into_style_keeps_the_rest(self):
        camlib.camera_set("cam-set", log=lambda *_: None)
        st = self.p.dir / "my-styles" / "sty"
        st.mkdir()
        (st / "shots.json").write_text('{"depth": {"version": 1}}')
        (st / "STYLE.md").write_text("x")
        n = save.write_camera("cam-set", st)
        self.assertEqual(n, len(KEY["shots"]) + 0)
        doc = json.loads((st / "camera.json").read_text())
        self.assertEqual(doc["source_set"], "cam-set")
        withev = [r for r in doc["shots"] if r["evidence"]]
        self.assertTrue(all((st / p).exists() for r in withev for p in r["evidence"]))
        self.assertEqual((st / "shots.json").read_text(), '{"depth": {"version": 1}}')
        self.assertEqual((st / "STYLE.md").read_text(), "x")


if __name__ == "__main__":
    unittest.main()
