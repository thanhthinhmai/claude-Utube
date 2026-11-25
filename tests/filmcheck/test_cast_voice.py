"""specs/036 T034 (SC-005): a character that speaks needs a voice before the cast is approved; the voice goes to the
channel's cast library (a new voice = a new version) and comes back with the character; `voice cast sample|set`."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(Path(__file__).parent))
import castfilm  # noqa: E402
from filmcheck import cast, castlib, speakers  # noqa: E402
from test_cast import fake_sheet  # noqa: E402

TMP = Path(tempfile.gettempdir()) / "cast-voice-tests"
LINES = [{"id": "L01", "para": "P01", "text": "The night was long."},
         {"id": "L02", "para": "P01", "text": "Where is my guitar?", "speaker": "hero"},
         {"id": "L03", "para": "P02", "text": "Right here, under the bed, where you left it.", "speaker": "hero"}]


class CastVoice(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(dir=TMP))
        self.acc = self.tmp / "data" / "accounts" / "u1"
        self.d = castfilm.make(self.acc / "films" / "f1", characters=(castfilm.HERO, castfilm.FRIEND))
        (self.d / "lines.json").write_text(json.dumps(LINES))
        for c in ("hero", "friend"):
            fake_sheet(self.d, c)
        (self.acc / "channels" / "default").mkdir(parents=True)
        (self.acc / "channels" / "default" / "channel.json").write_text(json.dumps({"slug": "default"}))
        self.env = {**os.environ, "STUDIO_ROOT": str(self.tmp), "STUDIO_TTS_FAKE": "1"}
        for k in ("STUDIO_JOB", "STUDIO_PROXY", "STUDIO_MODE", "STUDIO_TTS_DRY", "STUDIO_JOB_TOKEN"):
            self.env.pop(k, None)

    def studio(self, *args):
        return subprocess.run(["sh", str(REPO / "bin" / "studio"), *args], capture_output=True, text=True, env=self.env,
                              cwd=self.tmp, timeout=120)

    def set_options(self):
        doc = cast.load(self.d)
        cast.find(doc, "hero")["voice_options"] = [
            {"setting": {"mode": "own", "voice": "am_adam", "speed": 1.05}, "why": "young and quick"},
            {"setting": {"mode": "narrator", "pitch": 3}, "why": "the narrator, higher"}]
        cast.save(self.d, doc)

    def test_gate(self):
        self.assertEqual(cast.speaks(self.d, "hero"), 2)
        self.assertEqual(cast.speaks(self.d, "friend"), 0)
        why = cast.approve(self.d, ["hero", "friend"])
        self.assertEqual(len(why), 1)
        self.assertIn("hero: speaks 2 line(s) but has no voice", why[0])
        self.assertEqual(cast.approve(self.d, ["friend"]), [])               # silent characters need no voice
        doc = cast.load(self.d)
        cast.find(doc, "hero")["voice"] = {"mode": "own", "voice": "am_adam"}
        cast.save(self.d, doc)
        self.assertEqual(cast.approve(self.d, ["hero"]), [])
        self.assertEqual(cast.states(self.d)["hero"], "approved")
        doc = cast.load(self.d)
        cast.find(doc, "hero")["voice"]["speed"] = 1.2                        # a new voice: approve again
        cast.save(self.d, doc)
        self.assertEqual(cast.states(self.d)["hero"], "changed")
        doc["characters"][0]["voice"] = {"mode": "own", "voice": "nobody!"}
        self.assertTrue(any(k == "bad_voice" for _, k, _m in cast.validate(doc)))

    def test_set_and_sample(self):
        self.set_options()
        (self.d / "channel.json").write_text(json.dumps({"channel": "dusk", "film": {"voice": "am_michael", "speed": 1.0}}))
        r = self.studio("voice", "cast", str(self.d), "sample", "hero")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Kokoro, free", r.stdout)
        self.assertIn('"Right here, under the bed, where you left it."', r.stdout)   # the longest line ≤ 120
        for n in (1, 2):
            self.assertTrue((self.d / "cast" / "voices" / "hero" / f"{n}.wav").is_file())
        opt = cast.find(cast.load(self.d), "hero")["voice_options"][1]
        self.assertEqual(opt["sample"], "voices/hero/2.wav")
        r = self.studio("voice", "cast", str(self.d), "set", "hero", "--option", "2")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(cast.find(cast.load(self.d), "hero")["voice"], {"mode": "narrator", "pitch": 3})
        res = speakers.resolve(self.d, LINES, self.tmp)                      # the cast voice reads hero's lines
        self.assertEqual((res["lines"]["L02"]["voice"], res["lines"]["L02"]["pitch"]), ("am_michael", 3))
        self.assertEqual(self.studio("voice", "cast", str(self.d), "set", "hero", "--option", "5").returncode, 2)
        r = self.studio("voice", "cast", str(self.d), "set", "hero", "--voice", "el:pNInz6obpgDQ", "--speed", "1.1")
        self.assertEqual(r.returncode, 0, r.stderr)
        doc = cast.load(self.d)
        cast.find(doc, "hero")["voice_options"][0]["setting"] = {"mode": "own", "voice": "el:pNInz6obpgDQ"}
        cast.save(self.d, doc)
        r = self.studio("voice", "cast", str(self.d), "sample", "hero", "--option", "1")    # costs characters
        self.assertEqual(r.returncode, 1)
        self.assertIn("ElevenLabs 45 characters", r.stdout)
        self.assertIn("--yes", r.stderr)

    def test_edit_op(self):                                               # T033: the app's "Use this voice"
        from filmcheck import edit
        self.set_options()
        r = edit.run(self.d, "cast-voice", {"character": "hero", "option": "1"})
        self.assertTrue(r["ok"], r)
        self.assertEqual(cast.find(cast.load(self.d), "hero")["voice"], {"mode": "own", "voice": "am_adam", "speed": 1.05})
        r = edit.run(self.d, "cast-voice", {"character": "hero", "mode": "narrator", "pitch": "2.5", "speed": "1.1"})
        self.assertEqual(cast.find(cast.load(self.d), "hero")["voice"], {"mode": "narrator", "pitch": 2.5, "speed": 1.1})
        r = edit.run(self.d, "cast-voice", {"character": "hero", "voice": "el:pNInz6obpgDQ", "cloned_ok": "1"})
        self.assertIn("cloned_ok", cast.find(cast.load(self.d), "hero")["voice"])
        for bad in ({"character": "hero", "option": "9"}, {"character": "hero", "voice": "nobody"},
                    {"character": "hero", "mode": "narrator", "pitch": "12"}):
            r = edit.run(self.d, "cast-voice", bad)
            self.assertFalse(r.get("ok"), (bad, r))

    def test_voice_page_changes_the_cast(self):                           # T038: the Voice page on a cast character
        from filmcheck import edit
        os.environ["STUDIO_EDIT_NO_RUN"] = "1"
        try:
            doc = cast.load(self.d)
            cast.find(doc, "hero")["voice"] = {"mode": "own", "voice": "am_adam"}
            cast.save(self.d, doc)
            self.assertEqual(cast.approve(self.d, ["hero"]), [])
            r = edit.run(self.d, "voice-speaker", {"speaker": "hero", "mode": "narrator", "pitch": "3",
                                                    "confirm": "speaker"})
            self.assertTrue(r["ok"], r)
        finally:
            os.environ.pop("STUDIO_EDIT_NO_RUN", None)
        self.assertEqual(cast.find(cast.load(self.d), "hero")["voice"], {"mode": "narrator", "pitch": 3.0})
        self.assertEqual(cast.states(self.d)["hero"], "changed")              # FR-040: approve the character again
        film = json.loads((self.d / "film.json").read_text())
        self.assertNotIn("hero", film.get("voices") or {})                    # film.json keeps no second copy

    def test_library_keeps_the_voice(self):
        doc = cast.load(self.d)
        cast.find(doc, "hero")["voice"] = {"mode": "narrator", "pitch": 2}
        cast.save(self.d, doc)
        speakers.save_channel_voice(self.acc, "default", narrator={"voice": "am_michael", "speed": 1.0})
        self.assertEqual(cast.approve(self.d, ["hero", "friend"]), [])
        self.assertEqual(castlib.save_approved(self.d, ["hero"]), ["✓ default/hero: v1 (new)"])
        v1 = json.loads((self.acc / "channels/default/cast/hero/v1/character.json").read_text())
        self.assertEqual((v1["voice"], v1["voice_narrator"]), ({"mode": "narrator", "pitch": 2}, "am_michael"))
        d2 = castfilm.make(self.acc / "films" / "f2", characters=(castfilm.HERO,))
        r = castlib.use(d2, "default/hero")
        self.assertEqual(cast.find(cast.load(d2), "hero")["voice"], {"mode": "narrator", "pitch": 2})   # no question asked
        self.assertNotIn("voice (the channel's narrator changed: listen and approve again)", r["lacking"])
        speakers.save_channel_voice(self.acc, "default", narrator={"voice": "bm_george", "speed": 1.0})   # FR-016
        r = castlib.use(d2, "default/hero")
        self.assertIn("voice (the channel's narrator changed: listen and approve again)", r["lacking"])
        self.assertFalse(r["approved"])
        # a new voice is a new version
        doc = cast.load(self.d)
        cast.find(doc, "hero")["voice"] = {"mode": "own", "voice": "am_adam"}
        cast.save(self.d, doc)
        self.assertEqual(cast.approve(self.d, ["hero"]), [])
        self.assertEqual(castlib.save_approved(self.d, ["hero"]), ["✓ default/hero: v2 (new)"])


if __name__ == "__main__":
    unittest.main()
