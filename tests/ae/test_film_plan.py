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
