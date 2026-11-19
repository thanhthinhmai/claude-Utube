"""specs/023 T035: learn pairs — ≥ 3 pairs, kept reference frames only, a side-by-side clip from a strip."""
import subprocess
import unittest

from PIL import Image

from helpers import Project
from sl import pairs, refset, shots


class Pairs(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        refset.save("p-set", refset.new_set("p-set", "videos", []))
        prof = refset.profile_dir("p-set", "v01")
        prof.mkdir(parents=True)
        f = prof / "f.jpg"
        Image.new("RGB", (320, 180), (90, 60, 120)).save(f)
        shots.draw_sheets([{"id": "S001"}, {"id": "S002"}], lambda s: f, prof / "shot-sheets", "v01_shots")
        (prof / "strips").mkdir()
        Image.new("RGB", (8 * 320, 180), (40, 40, 80)).save(prof / "strips" / "S003.jpg")
        self.ours = []
        for i in range(3):
            o = self.p.dir / f"o{i}.jpg"
            Image.new("RGB", (1280, 720), (200, 100, 50)).save(o)
            self.ours.append(str(o))

    def tearDown(self):
        self.p.close()

    def test_sheet(self):
        out = pairs.sheet("p-set", 1, "faces", self.ours, ["v01_shots_1.jpg#1", "v01_shots_1.jpg#2", "v01/strips/S003.jpg#4"])
        self.assertTrue(out.exists())
        self.assertEqual(out.parent.name, "1")
        self.assertIn("pairs", str(out))

    def test_too_few_pairs(self):
        with self.assertRaises(refset.UsageError):
            pairs.sheet("p-set", 1, "faces", self.ours[:2], ["v01_shots_1.jpg#1", "v01_shots_1.jpg#2"])

    def test_bad_reference(self):
        with self.assertRaises(refset.UsageError):
            pairs.sheet("p-set", 1, "faces", self.ours, ["v01_shots_1.jpg#1", "v01_shots_1.jpg#2", "somewhere.png"])

    def test_clip(self):
        mp4 = self.p.dir / "ours.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=red:s=320x180:d=2", "-pix_fmt", "yuv420p",
                        str(mp4)], check=True)
        out = pairs.clip("p-set", 1, "acting", str(mp4), "v01/strips/S003.jpg")
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                                   capture_output=True, text=True).stdout)
        self.assertAlmostEqual(dur, 2.0, delta=0.2)
        w = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width", "-of", "csv=p=0",
                            str(out)], capture_output=True, text=True).stdout.strip()
        self.assertEqual(w, "1280")                                          # two 640-wide halves


if __name__ == "__main__":
    unittest.main()
