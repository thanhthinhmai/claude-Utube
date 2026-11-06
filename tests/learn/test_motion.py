import unittest

from helpers import FX, need_fixtures
from sl import measure


class Motion(unittest.TestCase):
    def setUp(self):
        need_fixtures(self)

    def run_file(self, name):
        return measure.analyze(FX / name, max_seconds=180)

    def test_fast_pan(self):
        r = self.run_file("pan_fast.mp4")
        dx = [row["dx"] for row in r["rows"][1:] if row["motion_ok"]]
        self.assertGreater(len(dx), 50)
        mean = sum(dx) / len(dx)
        # texture moves left by 2 px/frame at 320 wide → dx ≈ -2
        self.assertAlmostEqual(mean, -2.0, delta=0.2)
        self.assertLess(r["profile"]["still_ratio"], 0.05)

    def test_slow_pan_counts_as_still(self):
        r = self.run_file("pan_slow.mp4")
        p = r["profile"]
        self.assertGreater(p["still_ratio"], 0.9)               # 0.3 px/frame at 720 < 0.5
        self.assertAlmostEqual(p["motion_720"]["p50"], 0.3, delta=0.12)

    def test_cuts_flash_dissolve(self):  # SC-002
        p = self.run_file("cuts.mp4")["profile"]
        fps = 30
        expected = [30, 60, 90, 162, 192]
        found = [round(t * fps) for t in p["cuts"]]
        hits = sum(any(abs(f - e) <= 1 for f in found) for e in expected)
        false = sum(not any(abs(f - e) <= 1 for e in expected) for f in found)
        self.assertGreaterEqual(hits / len(expected), 0.95, found)
        self.assertLessEqual(false, 0, found)
        self.assertEqual(len(p["flashes"]), 1, p["flashes"])
        self.assertAlmostEqual(p["flashes"][0] * fps, 70, delta=1)
        self.assertEqual(len(p["soft_transitions"]), 1, p["soft_transitions"])
        a, b = p["soft_transitions"][0]
        self.assertTrue(a * fps <= 126 <= b * fps)


if __name__ == "__main__":
    unittest.main()
