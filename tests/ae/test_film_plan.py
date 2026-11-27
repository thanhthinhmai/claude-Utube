"""specs/038 T005: shot_plan in film.json (per-shot engine and camera measures)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from ae import film  # noqa: E402


def make(d: Path, plan=None, default=None, scripts=()):
    (d / "ae").mkdir(parents=True, exist_ok=True)
    (d / "ae" / "a.jsx").write_text("CU.shot1=function(){};")
    doc = {"engine": "ae", "fps": 24, "shots": ["S1", "S2", "S3"], "ae_files": ["a.jsx"]}
    if plan is not None:
        doc["shot_plan"] = plan
    if default:
        doc["default_engine"] = default
    (d / "film.json").write_text(json.dumps(doc))
    for s in scripts:
        (d / "blender").mkdir(exist_ok=True)
        (d / "blender" / f"{s}.py").write_text("def shot(k):\n    k.set('classroom')\n")
    return d


class ShotPlan(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def test_old_film_is_all_ae(self):
        doc = film.load(make(self.d))
        self.assertEqual(doc["default_engine"], "ae")
        self.assertEqual(doc["shot_plan"], {})
        self.assertEqual([film.engine_of(doc, s) for s in doc["shots"]], ["ae", "ae", "ae"])
        self.assertEqual(film.blender_shots(doc), [])

    def test_engine_per_shot(self):
        doc = film.load(make(self.d, {"S2": {"engine": "blender", "set": "auditorium", "size": "wide", "lens": "normal",
                                             "cam_height": "eye", "depth": "deep", "layers": ["fg", "mid", "bg"],
                                             "occluder": True, "move": "dolly", "transition": "fade"}}, scripts=["S2"]))
        self.assertEqual(film.engine_of(doc, "S2"), "blender")
        self.assertEqual(film.engine_of(doc, "S1"), "ae")
        self.assertEqual(film.blender_shots(doc), ["S2"])
        film.validate_plan(self.d, doc)

    def test_default_engine_blender(self):
        doc = film.load(make(self.d, {"S1": {"engine": "ae"}}, default="blender"))
        self.assertEqual(film.blender_shots(doc), ["S2", "S3"])

    def bad(self, plan, default=None):
        with self.assertRaises(film.FilmError) as c:
            film.load(make(self.d, plan, default))
        self.assertEqual(c.exception.code, "bad_film_json")
        return c.exception.message

    def test_bad_values(self):
        self.assertIn("S9", self.bad({"S9": {"engine": "ae"}}))
        self.assertIn("engine", self.bad({"S1": {"engine": "maya"}}))
        self.assertIn("size", self.bad({"S1": {"size": "giant"}}))
        self.assertIn("cam_height", self.bad({"S1": {"cam_height": "roof"}}))
        self.assertIn("lens", self.bad({"S1": {"lens": "fisheye"}}))
        self.assertIn("depth", self.bad({"S1": {"depth": "huge"}}))
        self.assertIn("layers", self.bad({"S1": {"layers": ["fg", "sky"]}}))
        self.assertIn("move", self.bad({"S1": {"move": "spin"}}))
        self.assertIn("transition", self.bad({"S1": {"transition": "wipe"}}))
        self.assertIn("occluder", self.bad({"S1": {"occluder": "yes"}}))
        self.assertIn("default_engine", self.bad({}, default="page"))

    def test_blender_shot_needs_set_and_script(self):
        doc = film.load(make(self.d, {"S2": {"engine": "blender"}}))
        with self.assertRaises(film.FilmError) as c:
            film.validate_plan(self.d, doc)
        self.assertEqual(c.exception.code, "bad_plan")
        self.assertIn("set", c.exception.message)
        doc = film.load(make(self.d, {"S2": {"engine": "blender", "set": "hallway"}}))
        with self.assertRaises(film.FilmError) as c:
            film.validate_plan(self.d, doc)
        self.assertIn("blender/S2.py", c.exception.message)


if __name__ == "__main__":
    unittest.main()


CAM = {"size": "med", "start": {"scale": 1.1, "cx": 50, "cy": 45}, "move": "push", "zoom_pct": 5.6,
       "rate_pct_s": 2.0, "ease": [0.13, 0.48, 0.85], "ease_ae": [60, 70], "drift_px": [0, 8], "transition": "cut",
       "ref": "v01:S003", "option": 1}


class CameraBlock(unittest.TestCase):
    """specs/039 T006: craft flags and the chosen camera block of shot_plan."""
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def bad(self, row):
        with self.assertRaises(film.FilmError) as c:
            film.load(make(self.d, {"S1": row}))
        return c.exception.message

    def test_good(self):
        doc = film.load(make(self.d, {"S1": {"card": False, "action": True, "outdoor": False, "prop": True,
                                             "camera": dict(CAM)}}))
        self.assertEqual(doc["shot_plan"]["S1"]["camera"]["zoom_pct"], 5.6)

    def test_flags_are_bool(self):
        for k in ("card", "action", "outdoor", "prop"):
            self.assertIn(k, self.bad({k: 1}))

    def test_camera_rules(self):
        self.assertIn("start.scale", self.bad({"camera": dict(CAM, start={"scale": 5, "cx": 50, "cy": 50})}))
        self.assertIn("zoom_pct", self.bad({"camera": dict(CAM, zoom_pct=41)}))
        self.assertIn("ease", self.bad({"camera": dict(CAM, ease=[0.5, 0.4, 0.9])}))
        self.assertIn("ease", self.bad({"camera": dict(CAM, ease=[0.1, 0.5, 1.2])}))
        self.assertIn("move", self.bad({"camera": dict(CAM, move="orbit")}))
        self.assertIn("drift_px", self.bad({"camera": dict(CAM, drift_px=[1])}))

    def test_user_requested_move(self):
        film.load(make(self.d, {"S1": {"camera": dict(CAM, move="orbit", by_user_request=True)}}))
