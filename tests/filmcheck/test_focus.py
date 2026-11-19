"""The shared focus measure (specs/021 T004; FR-003; research R1)."""
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import focus  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"


def make(path: Path, vf: str, src: str = "cellauto=s=960x540:rule=110:rate=1"):     # fine detail everywhere, like a real frame
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", src, "-frames:v", "1", "-vf", vf, str(path)],
                   check=True)
    return path


@unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
class Focus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TMP.mkdir(exist_ok=True)
        cls.d = Path(tempfile.mkdtemp(dir=TMP))

    def test_sharp_and_blurred(self):
        sharp = focus.measure(make(self.d / "sharp.jpg", "null"))
        self.assertGreaterEqual(sharp["focused_share"], 0.9)
        blur = focus.measure(make(self.d / "blur.jpg", "gblur=sigma=8"))
        self.assertEqual(blur["focused_share"], 0.0)

    def test_half_in_focus(self):
        vf = "split[a][b];[b]gblur=sigma=8,crop=480:540:480:0[r];[a][r]overlay=480:0"
        r = focus.measure(make(self.d / "half.jpg", vf))
        self.assertGreaterEqual(r["focused_share"], 0.4)
        self.assertLessEqual(r["focused_share"], 0.7)            # tiles on the seam count as sharp
        self.assertLess(r["sharpest_at"][0], 2)                      # the sharp half is on the left

    def test_letterbox_and_subtitle_band_left_out(self):
        # a blurred picture with black bars and a sharp white subtitle line in the band
        vf = ("gblur=sigma=8,drawbox=x=0:y=0:w=iw:h=66:color=black:t=fill,drawbox=x=0:y=474:w=iw:h=66:color=black:t=fill,"
              "drawbox=x=300:y=420:w=360:h=24:color=white:t=fill,drawbox=x=310:y=426:w=20:h=12:color=black:t=fill,"
              "drawbox=x=360:y=426:w=20:h=12:color=black:t=fill,drawbox=x=410:y=426:w=20:h=12:color=black:t=fill")
        r = focus.measure(make(self.d / "bars.jpg", vf, src="testsrc2=s=960x540:r=1"))   # a colour source: black stays 0
        self.assertAlmostEqual(r["letterbox"][0], 66 / 540, delta=0.02)
        self.assertAlmostEqual(r["letterbox"][1], 66 / 540, delta=0.02)
        self.assertEqual(r["focused_share"], 0.0, r)

    def test_speed(self):
        f = make(self.d / "speed.jpg", "null")
        t = time.time()
        for _ in range(5):
            focus.measure(f)
        self.assertLessEqual((time.time() - t) / 5, 0.15)

    def test_unreadable(self):
        bad = self.d / "bad.jpg"
        bad.write_text("not a picture")
        with self.assertRaises(focus.FocusError):
            focus.measure(bad)


if __name__ == "__main__":
    unittest.main()
