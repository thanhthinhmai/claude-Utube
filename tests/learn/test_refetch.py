"""specs/023 T019: refetch puts a downloaded file in place of the known video it matches (no network)."""
import subprocess
import unittest

import numpy as np

from helpers import Project
from sl import fetch, refset, shots


def clip(path, colour, seconds, fps=10):
    """A plain-coloured video with a white bar, `seconds` long."""
    w, h = 320, 180
    f = np.zeros((h, w, 3), np.uint8)
    f[:] = colour
    f[60:120, 100:220] = 250
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps),
                          "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], stdin=subprocess.PIPE)
    p.stdin.write(f.tobytes() * int(seconds * fps))
    p.stdin.close()
    p.wait()


class Refetch(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.p = Project()
        self.tmp = self.p.dir / "dl"
        self.tmp.mkdir()
        data = refset.new_set("old-set", "videos", [])
        for vid, dur in (("v01", 4.0), ("v02", 6.0), ("v03", 6.4)):
            data["videos"].append({"id": vid, "file": f"{vid}.mp4", "duration": dur, "state": "transcribed"})
        refset.save("old-set", data)
        (refset.set_dir("old-set") / "videos").mkdir()
        # v02 and v03 kept their shot sheets: v02 is red, v03 is blue
        for vid, col in (("v02", (200, 40, 40)), ("v03", (40, 40, 200))):
            prof = refset.profile_dir("old-set", vid)
            prof.mkdir(parents=True)
            fr = np.zeros((180, 320, 3), np.uint8); fr[:] = col; fr[60:120, 100:220] = 250
            Image.fromarray(fr).save(prof / "f.jpg")
            rows = [{"id": "S001", "t0": 0, "t1": 6, "mid": 3.0}]
            g = shots.draw_sheets(rows, lambda s: prof / "f.jpg", prof / "shot-sheets", f"{vid}_shots")
            rows[0]["evidence"] = f"{g[0][0].name}#1"
            refset.write_json(prof / "shots.json", {"shots": rows})
        self.data = refset.load("old-set")

    def tearDown(self):
        self.p.close()

    def run_place(self, colour, seconds):
        src = self.tmp / "re_x.mp4"
        clip(src, colour, seconds)
        return fetch.place("old-set", self.data, src, "https://example.invalid/v/x", log=lambda *_: None)

    def test_unique_length_without_frames(self):
        self.assertEqual(self.run_place((90, 90, 90), 4.0), "v01")
        v = next(v for v in self.data["videos"] if v["id"] == "v01")
        self.assertEqual(v["url"], "https://example.invalid/v/x")
        self.assertTrue((refset.set_dir("old-set") / "videos" / "v01.mp4").exists())

    def test_frames_pick_between_close_lengths(self):
        self.assertEqual(self.run_place((40, 40, 200), 6.2), "v03")     # 6.2 s fits both v02 and v03; blue is v03

    def test_frames_refuse_a_different_video(self):
        self.assertIsNone(self.run_place((40, 200, 40), 6.0))           # right length, wrong pictures

    def test_no_length_match(self):
        self.assertIsNone(self.run_place((90, 90, 90), 9.0))

    def test_length_candidates(self):
        got = [v["id"] for v in fetch.length_candidates(self.data["videos"], 6.2)]
        self.assertEqual(got, ["v02", "v03"])


if __name__ == "__main__":
    unittest.main()
