"""specs/039 T022: the chosen camera reaches the AE bundle (data/camera.json, CU.planCam) and the Blender kit (a still
camera with a lens zoom); films without a camera block bundle as before."""
import json
import shutil
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "blender"))

from ae import bundle  # noqa: E402
from kit import camblock  # noqa: E402

CAM = {"size": "med", "move": "push", "start": {"scale": 1.2, "cx": 45.0, "cy": 50.0}, "zoom_pct": 6.0,
       "rate_pct_s": 2.0, "ease": [0.15, 0.5, 0.85], "ease_ae": [60.0, 50.0], "drift_px": [0.0, 12.0], "transition": "cut"}


def make_film(d: Path, plan=None) -> Path:
    (d / "ae").mkdir(parents=True, exist_ok=True)
    (d / "ae" / "shots.jsx").write_text('CU.shot1 = function () { return 1; };\nCU.shot2 = function () { return 2; };\n')
    doc = {"engine": "ae", "fps": 30, "shots": ["S1", "S2"], "ae_files": ["shots.jsx"]}
    if plan is not None:
        doc["shot_plan"] = plan
    (d / "film.json").write_text(json.dumps(doc))
    return d


class Bundle(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="camkit."))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def names(self, d, shots=None):
        r = bundle.make(d, shots, self.tmp / f"{d.name}.tar")
        with tarfile.open(r["path"]) as t:
            names = t.getnames()
            cam = json.loads(t.extractfile("data/camera.json").read()) if "data/camera.json" in names else None
        return names, cam

    def test_camera_json_from_shot_plan(self):
        d = make_film(self.tmp / "f", {"S1": {"size": "med", "move": "push", "camera": CAM}})
        names, cam = self.names(d)
        self.assertIn(bundle.CAMERA_DATA, names)
        self.assertEqual(cam, {"S1": CAM})
        names, cam = self.names(d, ["S2"])                       # only the bundled shots
        self.assertNotIn(bundle.CAMERA_DATA, names)

    def test_old_film_unchanged(self):
        d = make_film(self.tmp / "old")
        names, _ = self.names(d)
        self.assertNotIn(bundle.CAMERA_DATA, names)

    def test_kit_has_plan_cam(self):
        lib = (ROOT / "tools/ae/kit/lib.jsx").read_text()
        self.assertIn("CU.planCam = function (comp, id, skip)", lib)
        self.assertIn('CU.WORK + "/data/camera.json"', lib)
        self.assertIn("setTemporalEaseAtKey", lib)
        self.assertIn("CU.camera(comp, frames, skip, 0)", lib)  # measured motion (camFromMotion) still wins inside


class Blender(unittest.TestCase):
    def test_lens_zoom_still_camera(self):
        p = camblock.from_block(CAM)
        self.assertEqual(p["move"], "zoom")                    # never dolly or orbit
        self.assertEqual(p["parallax"], 0.0)
        self.assertAlmostEqual(p["zoom"], 1.06)
        self.assertAlmostEqual(p["lens_scale"], 1.2)
        self.assertEqual(p["ease"], (50.0, 60.0))               # k.cam's ease is (out, in)
        self.assertAlmostEqual(p["shift0"][0], -0.06, places=4)   # centred 5 % left of the middle at ×1.2
        self.assertEqual(p["shift0"][1], 0.0)
        self.assertLess(p["shift"][1], 0.0)                     # drifting down on screen = Blender shift y down

    def test_static_has_no_ease(self):
        p = camblock.from_block({**CAM, "move": "static", "zoom_pct": 0.0, "drift_px": [0, 0], "ease_ae": None})
        self.assertEqual((p["zoom"], p["ease"]), (1.0, (0.0, 0.0)))

    def test_camera_py_uses_block(self):
        src = (ROOT / "tools/blender/kit/camera.py").read_text()
        self.assertIn("camblock.from_block", src)
        self.assertIn('plan.get("camera")', src)


if __name__ == "__main__":
    unittest.main()
