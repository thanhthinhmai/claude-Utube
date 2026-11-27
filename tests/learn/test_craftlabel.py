"""specs/027 FR-014: craft labels (craftlabel.py) and learn craft-label (sl/craftset.py), with a fake labeler."""
import json
import unittest

from helpers import Project
from sl import craftset, refset

from filmcheck import craftlabel


def lab(card=False, people=1, action=False, outdoor=False, prop=False, subject=None):
    return {"card": card, "people": people, "action": action, "outdoor": outdoor, "prop": prop, "subject": subject}


class Subject(unittest.TestCase):
    """specs/039 T007: the main person's box (composition)."""
    def test_box_kept(self):
        got = craftlabel.valid({"shots": [{"id": "S1", **lab(subject=[30, 12.34, 60, 95])}]}, ["S1"])
        self.assertEqual(got["S1"]["subject"], [30.0, 12.3, 60.0, 95.0])

    def test_null_and_bad_boxes(self):
        for b in (None, [10, 10, 5, 50], [-1, 0, 50, 50], [0, 0, 50, 101], [1, 2, 3], "x"):
            got = craftlabel.valid({"shots": [{"id": "S1", **lab(subject=b)}]}, ["S1"])
            self.assertIsNotNone(got, b)
            self.assertIsNone(got["S1"]["subject"], b)

    def test_card_or_empty_has_no_subject(self):
        got = craftlabel.valid({"shots": [{"id": "S1", **lab(card=True, subject=[1, 1, 50, 50])},
                                          {"id": "S2", **lab(people=0, subject=[1, 1, 50, 50])}]}, ["S1", "S2"])
        self.assertIsNone(got["S1"]["subject"])
        self.assertIsNone(got["S2"]["subject"])

    def test_schema_asks_for_subject(self):
        self.assertIn("subject", craftlabel.SCHEMA["properties"]["shots"]["items"]["required"])
        self.assertIn("subject", craftlabel.SYSTEM)


class Valid(unittest.TestCase):
    def test_every_id_in_form(self):
        ans = {"shots": [{"id": "S1", **lab(action=True)}, {"id": "S2", **lab(card=True, people=3, action=True)}]}
        got = craftlabel.valid(ans, ["S1", "S2"])
        self.assertTrue(got["S1"]["action"])
        self.assertEqual(got["S2"], {"card": True, "people": 0, "action": False, "outdoor": False, "prop": False, "subject": None})

    def test_missing_or_bad(self):
        self.assertIsNone(craftlabel.valid({"shots": [{"id": "S1", **lab()}]}, ["S1", "S2"]))
        self.assertIsNone(craftlabel.valid({"shots": [{"id": "S1", **lab(people=12)}]}, ["S1"]))
        self.assertIsNone(craftlabel.valid({"shots": [{"id": "S1", **lab(), "action": "yes"}]}, ["S1"]))
        self.assertIsNone(craftlabel.valid({"shots": [{"id": "SX", **lab()}]}, ["S1"]))

    def test_no_people_no_action(self):
        got = craftlabel.valid({"shots": [{"id": "S1", **lab(people=0, action=True, prop=True, outdoor=True)}]}, ["S1"])
        self.assertEqual((got["S1"]["action"], got["S1"]["prop"], got["S1"]["outdoor"]), (False, False, True))


class Shares(unittest.TestCase):
    def test_denominators(self):
        rows = [lab(action=True, prop=True), lab(), lab(people=0, outdoor=True), lab(card=True, people=0),
                {**lab(outdoor=True), "ots": True}]
        s = craftlabel.shares(rows)
        self.assertEqual((s["shots"], s["people_shots"]), (4, 3))
        self.assertEqual((s["action"], s["prop"]), (round(1 / 3, 3), round(1 / 3, 3)))
        self.assertEqual((s["outdoor"], s["ots"]), (0.5, 0.25))

    def test_spread(self):
        self.assertEqual(craftlabel.spread([0.1, 0.3, 0.2, 0.4, None]),
                         {"min": 0.1, "p25": 0.175, "p50": 0.25, "p75": 0.325, "max": 0.4})
        self.assertEqual(craftlabel.spread([]), {})


class LabelSet(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.p = Project()
        d = self.p.dir / "references" / "ref-set"
        refset.write_json(d / "set.json", {"schema": refset.SCHEMA, "set": "ref-set", "videos": [{"id": "v01"}, {"id": "v02"}]})
        for vid, n in (("v01", 4), ("v02", 3)):
            prof = d / "profile" / vid
            (prof / "shot-frames").mkdir(parents=True)
            rows = []
            for i in range(1, n + 1):
                Image.new("RGB", (64, 36), (40 * i, 20, 60)).save(prof / "shot-frames" / f"S{i:03d}.jpg")
                rows.append({"id": f"S{i:03d}", "frame": f"shot-frames/S{i:03d}.jpg", "scale": "med",
                             "angle": "ots" if i == 1 else "eye", "evidence": f"{vid}_shots_1.jpg#{i}"})
            rows.append({"id": "S099", "frame": "x.jpg", "short": True})
            refset.write_json(prof / "shots.json", {"video": vid, "shots": rows})
        tf = self.p.dir / "my-styles" / "sty" / "template.json"
        tf.parent.mkdir(parents=True)
        tf.write_text(json.dumps({"version": 1, "source": {}}), encoding="utf-8")
        self.calls = []

    def tearDown(self):
        self.p.close()

    def fake(self, groups):
        ids = [i for g in groups for i in g[1]]
        self.calls.append(ids)
        for g in groups:
            self.assertTrue(g[0].exists())
        return {"labels": {i: lab(action=i in ("S001", "S002"), outdoor=i == "S003", prop=i == "S001") for i in ids},
                "model": "claude-opus-5-5", "usage": {}, "calls": 1}

    def test_cache_summary_write(self):
        tot = craftset.label_set("ref-set", labeler=self.fake, log=lambda *_: None)
        self.assertEqual((tot["shots"], tot["videos"]), (7, 2))
        self.assertNotIn("S099", self.calls[0])                       # short shots get no label
        craftset.label_set("ref-set", labeler=self.fake, log=lambda *_: None)
        self.assertEqual(len(self.calls), 2)                           # cached: nothing labelled again
        sm = craftset.summary("ref-set")
        self.assertEqual(sm["per_video"]["v01"]["action"], 0.5)
        self.assertEqual(sm["per_video"]["v02"]["action"], round(2 / 3, 3))
        self.assertEqual(sm["per_video"]["v01"]["ots"], 0.25)
        self.assertEqual(craftset.summary("ref-set", skip=("v02",))["videos"], ["v01"])
        c = craftset.write_style("ref-set", "sty", sm)
        tpl = json.loads((self.p.dir / "my-styles" / "sty" / "template.json").read_text())
        self.assertEqual(tpl["craft"]["action"]["rule"], "error")
        self.assertIn("craft-labels.json", tpl["source"]["craft"])
        self.assertEqual(tpl["craft"]["action"]["min"], c["action"]["share_p25"])
        self.assertEqual(tpl["craft"]["ots"]["range"], [0.25, round(1 / 3, 3)])
        ev = (self.p.dir / "my-styles" / "sty" / "EVIDENCE.md").read_text()
        self.assertIn("## Craft shares (specs/027)", ev)
        craftset.write_style("ref-set", "sty", sm)                     # written twice: one section
        self.assertEqual((self.p.dir / "my-styles" / "sty" / "EVIDENCE.md").read_text().count("## Craft shares"), 1)

    def test_force_and_new_shots(self):
        craftset.label_set("ref-set", labeler=self.fake, log=lambda *_: None)
        craftset.label_set("ref-set", force=True, labeler=self.fake, log=lambda *_: None)
        self.assertEqual(len(self.calls), 4)


if __name__ == "__main__":
    unittest.main()
