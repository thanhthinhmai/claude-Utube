"""specs/036 T021, T035: each line reads with its speaker's voice; side parts keep one voice and never share a scene's
voice; films from before 036 read as before."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import speakers  # noqa: E402


class Speakers(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="spk."))
        self.d = self.root / "films" / "demo"
        self.d.mkdir(parents=True)
        ch = self.root / "channels" / "dusk"
        ch.mkdir(parents=True)
        (ch / "channel.json").write_text(json.dumps({"slug": "dusk", "voice": "am_michael", "speed": 1.1}))
        (self.d / "channel.json").write_text(json.dumps({"channel": "dusk"}))

    def res(self, rows):
        return speakers.resolve(self.d, rows, self.root)

    def test_order_and_narrator(self):
        (self.d / "film.json").write_text(json.dumps({"voices": {"mom": {"mode": "own", "voice": "el:v_mom"},
                                                                  "kid": {"mode": "narrator", "pitch": 4}}}))
        rows = [{"id": "a", "para": "P01", "text": "Night."},
                {"id": "b", "para": "P01", "text": "Hi.", "speaker": "mom"},
                {"id": "c", "para": "P01", "text": "Yes.", "speaker": "kid"},
                {"id": "d", "para": "P02", "text": "Quick.", "speaker": "kid", "voice": "bf_emma"},
                {"id": "e", "para": "P02", "text": "Now.", "speaker": "narrator", "emotion": "whisper"}]
        r = self.res(rows)
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["lines"]["a"], {"mode": "own", "voice": "am_michael", "speed": 1.1})
        self.assertEqual(r["lines"]["b"]["voice"], "el:v_mom")
        self.assertEqual((r["lines"]["c"]["voice"], r["lines"]["c"]["pitch"], r["lines"]["c"]["formant"]),
                         ("am_michael", 4, "shifted"))                         # the narrator plays the kid
        self.assertNotIn("d", r["lines"])                                      # a hand-written voice wins
        self.assertEqual(r["lines"]["e"]["emotion"], "whisper")
        self.assertEqual(r["speakers"]["narrator"]["lines"], ["a", "e"])
        self.assertEqual(r["speakers"]["kid"]["source"], "film")

    def test_channel_voice_file_wins_over_old_field(self):
        speakers.save_channel_voice(self.root, "dusk", narrator={"voice": "el:pNInz6obpgDQ", "speed": 1.05})
        r = self.res([{"id": "a", "text": "x"}])
        self.assertEqual((r["lines"]["a"]["voice"], r["speakers"]["narrator"]["source"]), ("el:pNInz6obpgDQ", "narrator"))
        doc = json.loads((self.root / "channels" / "dusk" / "VOICE.json").read_text())
        self.assertIn("approved", doc["narrator"])

    def test_channel_without_narrator(self):
        (self.root / "channels" / "dusk" / "channel.json").write_text(json.dumps({"slug": "dusk"}))
        r = self.res([{"id": "a", "text": "x"}])
        self.assertIn("choose a narrator voice", r["errors"][0])

    def test_no_channel_keeps_old_default(self):
        (self.d / "channel.json").unlink()
        rows = [{"id": "a", "text": "Old line.", "voice": "am_michael", "speed": 1.1}, {"id": "b", "text": "No voice."}]
        self.assertEqual(speakers.apply(self.d, rows, self.root, write=False), rows)

    def test_unknown_speaker_and_bad_fields(self):
        r = self.res([{"id": "a", "text": "x", "speaker": "ghost"}])
        self.assertIn('speaker "ghost" has no voice', r["errors"][0])
        with self.assertRaises(speakers.SpeakerError) as e:
            speakers.apply(self.d, [{"id": "a", "text": "x", "role": "alien", "emotion": "angry", "fx": "space"}],
                           self.root, write=False)
        self.assertIn("role is one of", str(e.exception))
        self.assertIn("emotion is one of", str(e.exception))
        self.assertIn("fx is one of", str(e.exception))

    def test_speakers_json_keeps_fallback(self):
        (self.d / "voices").mkdir()
        (self.d / "voices" / "speakers.json").write_text(json.dumps({"fallback": {"provider": "kokoro"}}))
        speakers.apply(self.d, [{"id": "a", "text": "x"}], self.root)
        sp = json.loads((self.d / "voices" / "speakers.json").read_text())
        self.assertEqual((sp["fallback"], sp["narrator"]["lines"]), ({"provider": "kokoro"}, ["a"]))

    # ---------- side parts (T035) ----------
    def test_side_parts_in_one_scene_differ(self):
        speakers.save_channel_voice(self.root, "dusk", role="man", settings=[
            {"mode": "narrator", "pitch": -2, "speed": 0.95}, {"mode": "own", "voice": "am_adam"}])
        rows = [{"id": "a", "para": "P01", "text": "x"},
                {"id": "b", "para": "P01", "text": "x", "speaker": "guard", "role": "man"},
                {"id": "c", "para": "P01", "text": "x", "speaker": "cop", "role": "man"},
                {"id": "d", "para": "P01", "text": "x", "speaker": "chef", "role": "man"},
                {"id": "e", "para": "P03", "text": "x", "speaker": "guard", "role": "man"}]
        r = self.res(rows)
        self.assertEqual(r["errors"], [])
        keys = {sp: speakers.dup_key(r["speakers"][sp]["setting"]) for sp in ("narrator", "guard", "cop", "chef")}
        self.assertEqual(len(set(keys.values())), 4, keys)
        self.assertEqual(r["speakers"]["guard"]["lines"], ["b", "e"])           # one voice for the whole film
        self.assertEqual(r["lines"]["b"], r["lines"]["e"])
        self.assertEqual(r["speakers"]["chef"]["setting"]["pitch"], -1)         # choices used up: one semitone more

    def test_forced_same_voice_is_an_error(self):
        (self.d / "film.json").write_text(json.dumps({"voices": {"mom": {"mode": "own", "voice": "am_michael", "speed": 1.1}}}))
        r = self.res([{"id": "a", "para": "P02", "text": "x"}, {"id": "b", "para": "P02", "text": "x", "speaker": "mom"}])
        self.assertTrue(any("scene P02: narrator and mom have the same voice" in e for e in r["errors"]), r["errors"])


class Commands(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="spkc."))
        (self.root / "channels" / "dusk").mkdir(parents=True)
        (self.root / "channels" / "dusk" / "channel.json").write_text(json.dumps({"slug": "dusk"}))
        self.d = self.root / "films" / "demo"
        self.d.mkdir(parents=True)
        (self.d / "channel.json").write_text(json.dumps({"channel": "dusk"}))
        (self.d / "lines.json").write_text(json.dumps([{"id": "a", "para": "P01", "text": "Night."},
                                                        {"id": "b", "para": "P01", "text": "Hi.", "speaker": "kid", "role": "boy"}]))
        self.env = {**os.environ, "STUDIO_ROOT": str(self.root), "STUDIO_TTS_FAKE": "1"}
        for k in ("STUDIO_JOB_TOKEN", "STUDIO_PROXY", "STUDIO_TTS_DRY"):
            self.env.pop(k, None)

    def run_(self, *args):
        return subprocess.run(["sh", str(REPO / "bin" / "studio"), "voice", *args], capture_output=True, text=True, env=self.env)

    def test_check_channel_and_make(self):
        r = self.run_("check", "demo")
        self.assertEqual(r.returncode, 1)
        self.assertIn("choose a narrator voice", r.stderr)
        r = self.run_("make", "demo")
        self.assertEqual(r.returncode, 1)
        self.assertIn("choose a narrator voice", r.stderr)
        r = self.run_("channel", "dusk", "narrator", "--voice", "am_michael", "--speed", "1.1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("am_michael", r.stdout)
        r = self.run_("channel", "dusk", "role", "boy", "--pitch", "3", "--speed", "1.05")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_("check", "demo")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("kid", r.stdout)
        self.assertIn("pitch +3", r.stdout)
        r = self.run_("make", "demo")
        self.assertEqual(r.returncode, 0, r.stderr)
        made = json.loads((self.d / "voices" / ".made.json").read_text())
        self.assertEqual((made["a"]["voice"], made["b"]["voice"], made["b"]["pitch"]), ("am_michael", "am_michael", 3))
        sp = json.loads((self.d / "voices" / "speakers.json").read_text())
        self.assertEqual(sp["kid"]["role"], "boy")

    def test_bad_role_choice(self):
        r = self.run_("channel", "dusk", "role", "boy", "--pitch", "9")
        self.assertEqual(r.returncode, 2)
        self.assertIn("pitch", r.stderr)


if __name__ == "__main__":
    unittest.main()
