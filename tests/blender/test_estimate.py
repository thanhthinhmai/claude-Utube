"""specs/038 T020: build estimate from measured seconds per frame."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from blender import config, estimate  # noqa: E402


class Estimate(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.get("STUDIO_BLENDER_CONFIG")
        os.environ["STUDIO_BLENDER_CONFIG"] = str(Path(tempfile.mkdtemp()) / "blender.json")

    def tearDown(self):
        if self.old is None:
            os.environ.pop("STUDIO_BLENDER_CONFIG", None)
        else:
            os.environ["STUDIO_BLENDER_CONFIG"] = self.old

    def test_frames_times_measured_rate(self):
        config.save({"secPerFrame": 6.0})
        self.assertEqual(estimate.blender_seconds(100), 600)
        self.assertEqual(estimate.blender_seconds(100, quarter=True), 120)
        self.assertEqual(estimate.line(100), "estimate: blender 100 frames ≈ 10 min")

    def test_default_rate_and_ae(self):
        self.assertEqual(estimate.blender_seconds(10), 10 * config.SEC_PER_FRAME)
        self.assertIn("ae 3 shot(s) ≈ 3 min", estimate.line(0, 3))
        estimate.remember_ae(2, 60)
        self.assertEqual(config.load()["aeSecPerShot"], 30)
        estimate.remember_ae(1, 60)
        self.assertEqual(config.load()["aeSecPerShot"], 40)
        self.assertEqual(estimate.line(0, 0), "estimate: nothing to build")


if __name__ == "__main__":
    unittest.main()
