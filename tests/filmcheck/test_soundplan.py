"""specs/037 T019: cues anchored to motions, words, shares of a shot and whole shots; times follow the shot lengths;
gone anchors drop, sounds not found stay missing; density; --base; films made before 035."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
sys.path.insert(0, str(HERE))

import soundfilm  # noqa: E402
import soundfix  # noqa: E402
from filmcheck import soundlib, soundplan  # noqa: E402

F = 1 / 30


class PlanCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"STUDIO_DATA": str(t / "data"), "STUDIO_ROOT": str(t / "repo"),
                                                "FREESOUND_API_KEY": ""})
        self.env.start()
        self.noenv = mock.patch("filmcheck.eleven.load_env", return_value={})
        self.noenv.start()
        (t / "repo" / "references").mkdir(parents=True)
        soundlib.add_root(soundfix.make(t / "Sonniss" / "GDC2024"))
        soundlib.index()
        self.d = soundfilm.make(t / "films" / "f1")

    def tearDown(self):
        self.noenv.stop()
        self.env.stop()
        self.tmp.cleanup()

    def add(self, shot, anchor, query="window shatter", **kw):
        return soundplan.add_cue(self.d, shot, kw.pop("action", "a thing"), anchor, query, **kw)


class Anchors(PlanCase):
    def test_each_anchor_lands_within_a_frame(self):
        a = self.add("S2", {"motion": "Window · Scale", "edge": "start", "offset_f": 0})
        self.assertAlmostEqual(a["at"], 2.0 + 1.2, delta=F)
        b = self.add("S2", {"motion": "Hand R · Rotation", "edge": "end", "offset_f": 3}, query="cork pop")
        self.assertAlmostEqual(b["at"], 2.0 + 2.8 + 3 * F, delta=F)
        c = self.add("S1", {"line": "l01", "word": "window", "offset_f": 0}, query="bottle smash")
        self.assertAlmostEqual(c["at"], 0.3 + 0.1, delta=F)
        e = self.add("S3", {"shot_at": 0.5}, query="ball bounce")
        self.assertAlmostEqual(e["at"], 5.0 + 1.0, delta=F)
        s = self.add("S3", {"span": "shot"}, query="aquarium bubbles")
        self.assertAlmostEqual(s["at"], 5.0, delta=F)
        self.assertEqual(s["cut"], "hard")
        self.assertEqual([x["id"] for x in (a, b, c, e, s)], ["c01", "c02", "c03", "c04", "c05"])
        self.assertTrue(all(x["state"] == "placed" for x in (a, b, c, e, s)))
        self.assertTrue(a["entry"].startswith("s:") and len(a["alts"]) <= 7)
        self.assertTrue((self.d / "sound" / "cache" / (a["entry"].replace(":", "_") + ".wav")).is_file())
        for x in (a, b, c, e, s):                                          # rounded to a frame
            self.assertAlmostEqual(x["at"] * 30, round(x["at"] * 30), places=3)

    def test_times_follow_a_new_shot_length(self):
        a = self.add("S2", {"motion": "Window · Scale"})
        e = self.add("S3", {"shot_at": 0.25}, query="ball bounce")
        soundfilm.set_frames(self.d, {"S1": 45, "S2": 90, "S3": 60})       # S1 1.5 s instead of 2 s
        p = soundplan.resolve(self.d, save=True)
        at = {c["id"]: c["at"] for c in p["cues"]}
        self.assertAlmostEqual(at[a["id"]], a["at"] - 0.5, delta=F)
        self.assertAlmostEqual(at[e["id"]], e["at"] - 0.5, delta=F)
        self.assertNotEqual(soundplan.load(self.d)["timing_sha"], "")

    def test_gone_motion_drops_with_a_reason(self):
        a = self.add("S2", {"motion": "Hand R · Rotation"}, query="cork pop")
        soundfilm.set_frames(self.d, {"S1": 60, "S2": 60, "S3": 60})       # S2 2 s: the hand starts at 2.4 s
        p = soundplan.resolve(self.d)
        c = next(c for c in p["cues"] if c["id"] == a["id"])
        self.assertEqual(c["state"], "dropped")
        self.assertIn("Hand R · Rotation", c["why"])
        keys = json.loads((self.d / "animatic" / "keys.json").read_text())
        keys["S2"] = keys["S2"][:1]
        (self.d / "animatic" / "keys.json").write_text(json.dumps(keys))
        soundfilm.set_frames(self.d, soundfilm.FRAMES)
        c = next(c for c in soundplan.resolve(self.d)["cues"] if c["id"] == a["id"])
        self.assertEqual((c["state"], c["why"]), ("dropped", "motion 'Hand R · Rotation' is gone after the cut"))

    def test_not_found_stays_missing(self):
        c = self.add("S1", {"shot_at": 0.1}, query="spaceship laser zap")
        self.assertEqual((c["state"], c["entry"]), ("missing", None))
        self.assertIn("spaceship laser zap", c["why"])
        self.assertFalse(list((self.d / "sound" / "cache").glob("*.wav")) if (self.d / "sound" / "cache").exists() else [])

    def test_user_cues_survive_and_base_is_checked(self):
        a = self.add("S2", {"motion": "Window · Scale"}, by="claude")
        b0 = soundplan.base(self.d)
        with self.assertRaises(soundplan.PlanError) as e:
            soundplan.set_cue(self.d, a["id"], {"offset_f": 5}, base="0000")
        self.assertEqual(e.exception.code, "changed")
        c = soundplan.set_cue(self.d, a["id"], {"offset_f": 5}, base=b0)
        self.assertEqual(c["by"], "user")
        self.assertAlmostEqual(c["at"], a["at"] + 5 * F, delta=F)
        soundplan.resolve(self.d, save=True)
        self.assertEqual(soundplan.load(self.d)["cues"][0]["by"], "user")

    def test_density(self):
        a = self.add("S1", {"shot_at": 0.50}, query="cork pop", by="claude")
        b = self.add("S1", {"shot_at": 0.53}, query="button click", by="auto")        # 0.06 s later
        u = self.add("S1", {"shot_at": 0.55}, query="sneaker step", by="user")
        st = {c["id"]: c for c in soundplan.resolve(self.d)["cues"]}
        self.assertEqual(st[b["id"]]["state"], "dropped")
        self.assertEqual(st[b["id"]]["why"], "too dense")
        self.assertEqual(st[u["id"]]["state"], "placed")                       # never a user's cue
        # a style that allows 6 a minute: a 7 s film holds 1 point sound (+ the user's)
        (self.d / "kit").mkdir()
        (self.d / "kit" / "template.json").write_text(json.dumps({"sound": {"sfx": {"per_min": 6, "gain_db": [-12, -9, -6]}}}))
        self.add("S3", {"shot_at": 0.5}, query="ball bounce", by="auto")
        p = soundplan.resolve(self.d)
        self.assertEqual(p["profile"], "style")
        live = [c for c in p["cues"] if c["state"] == "placed"]
        self.assertTrue(any(c["by"] == "user" for c in live))
        self.assertLessEqual(len([c for c in live if c["by"] != "user"]), 1)


class Fallback(PlanCase):
    def setUp(self):
        super().setUp()
        self.d = soundfilm.make(Path(self.tmp.name) / "films" / "old", timing=False, keys=False)

    def test_film_before_035(self):
        c = self.add("S2", {"line": "l02", "word": "cheer"}, query="small crowd cheer")
        self.assertAlmostEqual(c["at"], 2.4 + 0.3, delta=F)
        m = self.add("S2", {"motion": "Window · Scale"})
        self.assertEqual(m["state"], "dropped")
        self.assertIn("keys", m["why"])
        self.assertEqual(soundplan.resolve(self.d)["timing_source"], "render-shots.json")


if __name__ == "__main__":
    unittest.main()
