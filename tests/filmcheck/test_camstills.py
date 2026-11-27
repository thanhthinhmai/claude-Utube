"""camera stills (specs/039 T024): the end box for a given zoom and drift, the start cut, missing engine → 3, shots not
written → 2 (fake AE and Blender builds)."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from filmcheck import camstills, camsuggest  # noqa: E402
import test_camsuggest as ts  # noqa: E402


def opt(scale=1.0, cx=50.0, cy=50.0, zoom=0.0, drift=(0, 0), n=1):
    return {"n": n, "start": {"scale": scale, "cx": cx, "cy": cy}, "zoom_pct": zoom, "drift_px": list(drift)}


class Windows(unittest.TestCase):
    def test_push_box_is_centred_and_smaller(self):
        crop, end = camstills.windows(opt(zoom=25.0), 480, 270)
        self.assertEqual(tuple(round(x) for x in crop), (0, 0, 480, 270))
        self.assertEqual(tuple(round(x) for x in end), (48, 27, 432, 243))     # 1/1.25 of the frame, centred

    def test_start_cut(self):
        crop, _ = camstills.windows(opt(scale=2.0, cx=25.0, cy=50.0), 480, 270)
        self.assertEqual(tuple(round(x) for x in crop), (0, 68, 240, 202))

    def test_drift_moves_the_box(self):
        _, end = camstills.windows(opt(zoom=0.0, drift=(192, 0)), 480, 270)
        self.assertEqual(round(end[0]), 48)          # 192 px of 1920 = a tenth of the frame to the right
        self.assertEqual(round(end[1]), 0)

    def test_draw_size_and_box_colour(self):
        from PIL import Image
        img = camstills.draw(Image.new("RGB", (480, 270), (20, 20, 20)), opt(zoom=25.0))
        self.assertEqual(img.size, camstills.SIZE)
        self.assertEqual(img.getpixel((48, 135)), camstills.BOX)


class Make(ts.Base):
    def setUp(self):
        super().setUp()
        plan = {k: dict(v) for k, v in ts.PLAN.items()}
        plan["S2"].update(engine="blender", set="gym")
        self.d = ts.make_film(self.root, plan=plan)
        (self.d / "ae" / "shots.jsx").write_text("CU.shot1 = function () {};\nCU.shot3 = function () {};\n")
        (self.d / "blender").mkdir()
        (self.d / "blender" / "S2.py").write_text("k.cam()\n")
        camsuggest.suggest(self.d)
        from PIL import Image
        self.png = self.root / "frame.png"
        Image.new("RGB", (480, 270), (90, 120, 160)).save(self.png)

    def fake_ae(self, d, shots):
        self.assertEqual(os.environ.get("STUDIO_AE_CAMSTILL"), "1")
        mp4 = self.root / "m.mp4"
        import subprocess
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=blue:s=480x270:r=30:d=2",
                        "-pix_fmt", "yuv420p", str(mp4)], check=True)
        return {"master": str(mp4), "marks": [[0, 1, "", "S1"], [1, 2, "", "S3"]]}

    def fake_blender(self, d, doc, shots):
        self.assertNotIn("camera", doc["shot_plan"]["S2"])
        self.assertEqual(doc["shot_plan"]["S2"]["move"], "static")
        return {"gpu": "OPTIX", "shots": {s: str(self.png) for s in shots}}

    def test_every_option_gets_a_still(self):
        r = camstills.make(self.d, say=lambda x: None, ae_build=self.fake_ae, blender_build=self.fake_blender)
        o = camsuggest.load(self.d)
        n = sum(len(row["options"]) for row in o["shots"].values())
        self.assertEqual(len(r["stills"]), n)
        for row in o["shots"].values():
            for x in row["options"]:
                self.assertTrue((self.d / x["still"]).is_file())
        self.assertIsNone(os.environ.get("STUDIO_AE_CAMSTILL"))

    def test_software_render_stops(self):
        with self.assertRaises(camstills.StillError) as e:
            camstills.make(self.d, shots=["S2"], say=lambda x: None,
                           blender_build=lambda d, doc, s: {"gpu": "CPU", "shots": {}})
        self.assertEqual(e.exception.exit_code, 3)

    def test_missing_engine_is_3(self):
        class Missing(Exception):
            message = "After Effects is not set up"

            def exit_code(self):
                return 3

        def no_ae(d, shots):
            raise Missing()
        with self.assertRaises(camstills.StillError) as e:
            camstills.make(self.d, shots=["S1"], say=lambda x: None, ae_build=no_ae)
        self.assertEqual(e.exception.exit_code, 3)

    def test_shot_not_written_is_2(self):
        (self.d / "ae" / "shots.jsx").write_text("CU.shot1 = function () {};\n")
        with self.assertRaises(camstills.StillError) as e:
            camstills.make(self.d, say=lambda x: None, ae_build=self.fake_ae, blender_build=self.fake_blender)
        self.assertEqual(e.exception.exit_code, 2)
        self.assertIn("S3", str(e.exception))


if __name__ == "__main__":
    unittest.main()
