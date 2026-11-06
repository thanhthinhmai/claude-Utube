import csv
import json
import unittest

from helpers import FX, Project, need_fixtures
from sl import fetch, measure, refset, summary


class Pipeline(unittest.TestCase):
    def setUp(self):
        need_fixtures(self)
        self.p = Project()

    def tearDown(self):
        self.p.close()

    def test_fetch_measure_summary(self):
        files = [FX / "cuts.mp4", FX / "pan_fast.mp4", FX / "broken.mp4"]
        fetch.fetch_files("demo-set", files)
        data = refset.load("demo-set")
        self.assertEqual([v["id"] for v in data["videos"]], ["v01", "v02", "v03"])
        self.assertTrue(all(v["origin"] == "local" for v in data["videos"]))

        done = measure.measure_set("demo-set")
        data = refset.load("demo-set")
        states = {v["id"]: v["state"] for v in data["videos"]}
        self.assertEqual(states, {"v01": "measured", "v02": "measured", "v03": "skipped"})
        self.assertTrue(data["videos"][2]["skip_reason"])
        self.assertEqual(sorted(done), ["v01", "v02"])

        prof = refset.profile_dir("demo-set", "v01")
        with open(prof / "frames.csv") as f:
            header = next(csv.reader(f))
        self.assertEqual(header, ["i", "t", "dx", "dy", "motion", "motion_ok", "hist_d", "cut", "flash",
                                  "luma", "contrast", "sat", "dark", "bright"])
        vj = json.loads((prof / "video.json").read_text())
        self.assertEqual(vj["schema"], "style-learn/1")
        self.assertEqual(vj["frames_measured"], vj["frames_expected"])
        # 222 frames at 30 fps → 4 sheets of 2 s (the last one partial)
        self.assertEqual(len(vj["sheets"]), 4)
        self.assertTrue((prof / "sheets" / vj["sheets"][0]).exists())

        # resume: nothing is measured twice (FR-011)
        self.assertEqual(measure.measure_set("demo-set"), [])

        s = summary.build("demo-set")
        self.assertTrue(s["low_count_warning"])
        m = s["by_orientation"]["landscape"]["metrics"]["luma_p50"]
        self.assertTrue(m["min"] <= m["median"] <= m["max"])
        self.assertEqual(s["skipped"][0]["id"], "v03")
        self.assertTrue((refset.set_dir("demo-set") / "profile" / "summary.md").exists())

    def test_count_limits(self):  # FR-002
        for n in (2, 31):
            with self.assertRaises(refset.UsageError):
                fetch.check_count(n)
        self.assertEqual(fetch.check_count(12), 12)

    def test_bad_set_name(self):
        with self.assertRaises(refset.UsageError):
            refset.set_dir("Bad Name")


if __name__ == "__main__":
    unittest.main()
