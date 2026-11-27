"""The cast pass of Blender shots (specs/038 T044, T046) with the fake AE: plan pass → layers.json → AE layers bundle
→ transparent PNG frames in layers/<shot>/<char>-<view>/, skipped when nothing changed."""
import json
import os
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ae import bundle, castpass, local  # noqa: E402
import castfilm  # noqa: E402

FRAMES = 12


def film(tmp: Path) -> Path:
    d = castfilm.make(tmp / "f1")
    doc = json.loads((d / "film.json").read_text())
    doc.update(shots=["S1", "S2"], size=[320, 180], shot_plan={"S2": {"engine": "blender", "set": "hallway"}})
    (d / "film.json").write_text(json.dumps(doc))
    (d / "timing.json").write_text(json.dumps({"version": 1, "fps": 30, "frames": {"S1": 30, "S2": FRAMES}}))
    (d / "blender").mkdir()
    (d / "blender" / "S2.py").write_text('def shot(k):\n    k.set("hallway")\n    k.cam(size="wide")\n'
                                         '    k.cast("hero", at=(0, 2, 0), face=180)\n    k.crowd(area=(-3, 4, 3, 8), count=6, actions=["clap"])\n')
    return d


def fake_plan(rel_after: int = 99):
    """A Blender plan pass: hero faces the camera, then turns to 3/4 at frame 6."""
    calls = []

    def run(code, req, progress=None):
        calls.append(req)
        out = {}
        for row in req["shots"]:
            p = Path(code) / "out" / "plan" / f"{row['id']}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            samples = [{"f": f, "rel": 0 if f < 6 else rel_after, "height_px": 300, "elev": 12, "walk": False,
                        **({"pose": "wave"} if f >= 3 else {})} for f in range(1, row["frames"] + 1)]
            p.write_text(json.dumps({"shot": row["id"], "fps": 30, "frames": row["frames"],
                                     "chars": {"hero": {"rig": "", "samples": samples}},
                                     "crowd": {"count": 6, "actions": ["clap"]}}))
            out[row["id"]] = str(p)
        return {"shots": out}
    return run, calls


class CastPass(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.d = film(self.tmp)
        self.old = {k: os.environ.get(k) for k in ("STUDIO_AE_FAKE", "STUDIO_AE_WORK", "STUDIO_AE_CONFIG")}
        os.environ.update(STUDIO_AE_FAKE="1", STUDIO_AE_WORK=str(self.tmp / "work"),
                          STUDIO_AE_CONFIG=str(self.tmp / "ae.json"))

    def tearDown(self):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def doc(self):
        return json.loads((self.d / "film.json").read_text())

    def test_only_shots_that_call_cast(self):
        self.assertEqual(castpass.cast_shots(self.d, ["S1", "S2"]), ["S2"])

    def test_layers_bundle(self):
        jobs = [{"name": "L-S2-hero-front", "shot": "S2", "char": "hero", "member": None, "view": "front",
                 "frames": FRAMES, "size": 256, "track": [{"f": 1, "view": "front", "dir": 1}]}]
        r = bundle.make(self.d, None, self.tmp / "b.tar", layers={"fps": 30, "jobs": jobs})
        with tarfile.open(r["path"]) as t:
            names = t.getnames()
            entry = t.extractfile("entry.jsx").read().decode()
            meta = json.loads(t.extractfile("bundle.json").read())
        self.assertIn("kit/castlayer.jsx", names)
        self.assertIn("data/layers.json", names)
        self.assertNotIn("ae/shots.jsx", names)                      # the film's own shots are not built
        self.assertIn("CU.castLayers(", entry)
        self.assertEqual(meta["kind"], "layers")
        self.assertEqual(r["shots"], ["L-S2-hero-front"])

    def test_pass_draws_then_keeps(self):
        run, calls = fake_plan()
        drawn = castpass.run(self.d, self.doc(), ["S1", "S2"], say=lambda x: None, blender_build=run)
        self.assertEqual(drawn, ["S2"])
        self.assertEqual(calls[0]["kind"], "plan")
        lj = json.loads((self.d / "layers" / "S2" / "layers.json").read_text())
        hero = lj["chars"][0]
        self.assertEqual(hero["rig"], "ball@1")                        # filled from cast/cast.json
        self.assertEqual(hero["views"], ["front", "34"])
        self.assertEqual(lj["crowd"]["pool"], ["classmates.0", "classmates.1", "friend"])
        for name in ("hero-front", "hero-34", "classmates.0-front", "classmates.1-front", "friend-front"):
            pngs = sorted((self.d / "layers" / "S2" / name).glob("f*.png"))
            self.assertEqual(len(pngs), FRAMES, name)
        from PIL import Image
        im = Image.open(self.d / "layers" / "S2" / "hero-front" / "f0001.png")
        self.assertEqual(im.mode, "RGBA")
        self.assertEqual(im.getpixel((2, 2))[3], 0)                   # transparent ground
        self.assertEqual(im.getpixel((im.width // 2, im.height - 4))[3], 255)
        self.assertEqual(castpass.run(self.d, self.doc(), ["S2"], say=lambda x: None, blender_build=run), [])  # unchanged
        run2, _ = fake_plan(rel_after=-99)                            # turned the other way: 3/4 dir -1, drawn again
        self.assertEqual(castpass.run(self.d, self.doc(), ["S2"], say=lambda x: None, blender_build=run2), ["S2"])

    def test_unknown_character_stops(self):
        (self.d / "cast" / "cast.json").write_text(json.dumps({"characters": []}))
        run, _ = fake_plan()
        from blender.config import BlenderError
        with self.assertRaises(BlenderError):
            castpass.run(self.d, self.doc(), ["S2"], say=lambda x: None, blender_build=run)

    def test_crowd_track_moves(self):
        t = castpass.crowd_track("clap", 20)
        self.assertEqual([x["pose"] for x in t], ["chest", "both", "chest"])
        self.assertEqual(castpass.crowd_track("sit", 20), [{"f": 1, "view": "front", "dir": 1, "pose": "lap"}])

    def test_ae_error_is_reported(self):
        os.environ["FAKE_AE_MODE"] = "err"
        try:
            run, _ = fake_plan()
            with self.assertRaises(local.AeError):
                castpass.run(self.d, self.doc(), ["S2"], say=lambda x: None, blender_build=run)
        finally:
            os.environ.pop("FAKE_AE_MODE", None)


if __name__ == "__main__":
    unittest.main()
