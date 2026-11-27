"""The layers plan of cast cards (specs/038 T041, data-model "Layers plan", research R6)."""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from blender import layers  # noqa: E402


def samples(rels, h=400, elev=10, **kw):
    return [{"f": i + 1, "rel": r, "height_px": h, "elev": elev, **kw} for i, r in enumerate(rels)]


class Views(unittest.TestCase):
    def test_bounds(self):
        self.assertEqual(layers.view_of(0), ("front", 1))
        self.assertEqual(layers.view_of(70), ("34", 1))
        self.assertEqual(layers.view_of(-70), ("34", -1))
        self.assertEqual(layers.view_of(170), ("back", 1))
        self.assertEqual(layers.view_of(-170), ("back", 1))

    def test_hysteresis_15_degrees(self):
        b = layers.FRONT_MAX
        self.assertEqual(layers.view_of(b + 10, ("front", 1)), ("front", 1))     # within 15° past the bound: keep
        self.assertEqual(layers.view_of(b + 16, ("front", 1)), ("34", 1))
        self.assertEqual(layers.view_of(b - 10, ("34", 1)), ("34", 1))
        self.assertEqual(layers.view_of(b - 16, ("34", 1)), ("front", 1))
        rels = [b - 2, b + 2, b - 2, b + 2, b + 3]                                # jitter at the bound: no flicker
        self.assertEqual([t["view"] for t in layers.char_plan("hero", "ball@1", samples(rels))["track"]], ["front"])

    def test_dir_flips_only_past_the_middle(self):
        self.assertEqual(layers.view_of(-5, ("34", 1)), ("front", 1))
        self.assertEqual(layers.view_of(-40, ("34", 1)), ("34", -1))


class Plan(unittest.TestCase):
    def test_track_only_on_change(self):
        s = samples([0, 0, 0, 80, 80, 80], pose="down")
        s[4]["pose"] = s[5]["pose"] = "wave"
        p = layers.char_plan("hero", "ball@1", s)
        self.assertEqual([(t["f"], t["view"], t.get("pose")) for t in p["track"]],
                         [(1, "front", "down"), (4, "34", "down"), (5, "34", "wave")])
        self.assertEqual(p["views"], ["front", "34"])

    def test_height_and_card_angle(self):
        p = layers.char_plan("hero", "ball@1", samples([0, 0], h=500, elev=40))
        self.assertEqual(p["height_px"], 600)
        self.assertEqual(p["card_angle_max"], 40)
        self.assertEqual(layers.char_plan("hero", "ball@1", samples([0], h=1000))["height_px"], 1080)

    def test_layers_doc_and_crowd(self):
        doc = layers.plan_doc("S3", 24, 72, {"hero": {"rig": "ball@1", "samples": samples([0, 0])}},
                              crowd={"count": 40, "actions": ["sit", "clap"]}, crowd_pool=["kid1", "kid2", "kid3", "kid4", "kid5"])
        self.assertEqual(doc["shot"], "S3")
        self.assertEqual(doc["chars"][0]["id"], "hero")
        self.assertEqual(doc["crowd"]["pool"], ["kid1", "kid2", "kid3", "kid4"])   # a small set of layers
        self.assertEqual(doc["crowd"]["count"], 40)
        self.assertEqual(doc["card_angle_max"], 10)
        jobs = layers.jobs(doc)
        self.assertIn(("hero", "front"), jobs)
        self.assertEqual(len([j for j in jobs if j[0].startswith("kid")]), 4)      # crowd: front view only


if __name__ == "__main__":
    unittest.main()
