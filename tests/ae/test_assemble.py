"""specs/038 T015: splice.assemble() joins AE pieces (offsets into a MASTER) and Blender shot clips frame-exact."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from ae import splice  # noqa: E402

FPS = 24


def clip(path: Path, frames: int, color: str) -> str:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=160x90:r={FPS}",
                    "-frames:v", str(frames), "-pix_fmt", "yuv420p", str(path)], check=True)
    return str(path)


def count(path: str) -> int:
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_frames", "-of", "csv=p=0", path], capture_output=True, text=True)
    return int(r.stdout.strip())


def mean(path: str, frame: int) -> float:
    """Mean luma of one frame (0..255)."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"select=eq(n\\,{frame}),scale=1:1,format=gray",
                        "-frames:v", "1", "-f", "rawvideo", "-"], capture_output=True)
    return r.stdout[0] if r.stdout else -1


class Assemble(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        # an AE MASTER with S1 (frames 0..23, white) and S3 (frames 24..59, gray) back to back
        a = clip(cls.tmp / "a.mp4", 24, "white")
        b = clip(cls.tmp / "b.mp4", 36, "gray")
        cls.master = str(cls.tmp / "master.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a, "-i", b, "-filter_complex", "[0:v][1:v]concat=n=2:v=1[v]",
                        "-map", "[v]", "-pix_fmt", "yuv420p", cls.master], check=True)
        cls.s2 = clip(cls.tmp / "S2.mp4", 30, "black")        # Blender shot
        cls.s4 = clip(cls.tmp / "S4.mp4", 20, "white")        # Blender shot, 4 frames short of its timing

    def segs(self):
        return [{"shot": "S1", "clip": self.master, "start": 0, "frames": 24},
                {"shot": "S2", "clip": self.s2, "start": 0, "frames": 30},
                {"shot": "S3", "clip": self.master, "start": 1.0, "frames": 36},
                {"shot": "S4", "clip": self.s4, "start": 0, "frames": 24}]

    def test_cuts_are_frame_exact(self):
        r = splice.assemble(self.segs(), self.tmp / "cut.mp4", FPS, (160, 90))
        self.assertEqual(r["frames"], 114)
        self.assertEqual(count(r["out"]), 114)
        self.assertEqual([m[3] for m in r["marks"]], ["S1", "S2", "S3", "S4"])
        self.assertEqual(r["marks"][2][:2], [round(54 / FPS, 4), round(90 / FPS, 4)])
        self.assertGreater(mean(r["out"], 23), 200)      # last S1 frame white
        self.assertLess(mean(r["out"], 24), 30)          # first S2 frame black
        self.assertTrue(90 < mean(r["out"], 60) < 160)   # S3 gray, taken from the MASTER at 1.0 s
        self.assertGreater(mean(r["out"], 113), 200)     # S4 held its last frame for the 4 missing frames

    def test_fade_and_dip_keep_every_shot_length(self):
        r = splice.assemble(self.segs(), self.tmp / "tr.mp4", FPS, (160, 90), {"S2": "dip", "S3": "fade"})
        self.assertEqual(count(r["out"]), 114)
        self.assertLess(mean(r["out"], 23), 60)          # S1 dips to black before S2
        self.assertLess(mean(r["out"], 24), 30)
        mid = mean(r["out"], 54 + 4)                     # the dissolve from S2 (black) into S3 (gray)
        self.assertTrue(5 < mid < 120, mid)
        self.assertTrue(90 < mean(r["out"], 54 + 12) < 160)

    def test_missing_clip(self):
        segs = self.segs()
        segs[1]["clip"] = str(self.tmp / "nope.mp4")
        with self.assertRaises(splice.SpliceError):
            splice.assemble(segs, self.tmp / "x.mp4", FPS, (160, 90))


if __name__ == "__main__":
    unittest.main()
