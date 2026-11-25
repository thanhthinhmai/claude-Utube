"""specs/036 T009: voice make reads Kokoro and ElevenLabs lines, asks before spending characters, keeps the raw voice so
an effect change does not read again, and reads a whole film with Kokoro on request."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fake_eleven import FakeEleven  # noqa: E402

LINES = [
    {"id": "l1", "para": "P01", "text": "It is three in the morning.", "voice": "am_michael"},
    {"id": "l2", "para": "P01", "text": "Is that a real fish?", "voice": "el:v_girl", "pitch": 2},
    {"id": "l3", "para": "P02", "text": "I can't say no to him.", "voice": "el:v_narr", "fx": "wall"},
]


class VoiceMakeProviders(unittest.TestCase):
    def setUp(self):
        self.fake = FakeEleven(left=10000).start()
        self.root = Path(tempfile.mkdtemp(prefix="vmp."))
        self.d = self.root / "films" / "demo"
        self.d.mkdir(parents=True)
        self.write(LINES)
        self.env = {**os.environ, "STUDIO_ROOT": str(self.root), "STUDIO_TTS_FAKE": "1",
                    "STUDIO_ELEVEN_URL": self.fake.url, "ELEVENLABS_API_KEY": self.fake.key}
        for k in ("STUDIO_JOB_TOKEN", "STUDIO_PROXY", "ELEVENLABS_MODEL", "STUDIO_TTS_DRY"):
            self.env.pop(k, None)

    def tearDown(self):
        self.fake.stop()

    def write(self, rows):
        (self.d / "lines.json").write_text(json.dumps(rows))

    def make(self, *args, **env):
        return subprocess.run(["sh", str(REPO / "bin" / "studio"), "voice", "make", "demo", *args],
                              capture_output=True, text=True, env={**self.env, **env})

    def speak_calls(self):
        return [c for c in self.fake.calls if c[1].startswith("/v1/text-to-speech/")]

    def test_asks_before_spending(self):
        r = self.make()
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("elevenlabs: 42 characters for 2 line(s); 10000 left", r.stdout)
        self.assertIn("--yes", r.stderr)
        self.assertEqual(self.speak_calls(), [])
        self.assertFalse((self.d / "voices" / "l1.wav").exists())

    def test_reads_both_providers(self):
        r = self.make("--yes")
        self.assertEqual(r.returncode, 0, r.stderr)
        v = self.d / "voices"
        for i in ("l1", "l2", "l3"):
            self.assertTrue((v / f"{i}.wav").is_file(), i)
            self.assertTrue((v / ".raw" / f"{i}.wav").is_file(), i)
        self.assertEqual(len(self.speak_calls()), 2)
        align = json.loads((v / "align.json").read_text())
        self.assertEqual(set(align), {"l2", "l3"})
        self.assertEqual(align["l2"]["source"], "el")
        u = json.loads((v / "usage.json").read_text())
        self.assertEqual((u["total"], u["runs"][0]["chars_estimated"]), (42, 42))
        self.assertEqual(self.fake.used, 42)
        made = json.loads((v / ".made.json").read_text())
        self.assertEqual(made["l2"]["pitch"], 2)
        self.assertEqual(made["l3"]["fx"], "wall")
        self.assertEqual(made["l3"]["model"], "eleven_multilingual_v2")
        self.assertNotIn("pitch", made["l1"])                       # defaults stay out: old .made.json still match
        dur = json.loads((v / "dur.json").read_text())
        self.assertEqual(set(dur), {"l1", "l2", "l3"})

    def test_charged_from_the_answer(self):                            # the plan charges fewer than the letters
        self.fake.cost = 0.5
        r = self.make("--yes")
        self.assertEqual(r.returncode, 0, r.stderr)
        u = json.loads((self.d / "voices" / "usage.json").read_text())
        self.assertEqual((u["runs"][0]["chars_estimated"], u["runs"][0]["chars"]), (42, self.fake.used))
        self.assertEqual(self.fake.used, 21)                            # 10 + 11: "character-cost" of each line

    def test_busy_is_tried_again(self):                                # a 429 (Starter: 3 lines at once) is not a failure
        self.fake.busy = 99
        r = self.make("--yes", "--only", "l2", STUDIO_ELEVEN_BACKOFF="0.01")
        self.assertEqual(r.returncode, 3)                               # still busy after 5 tries
        self.assertIn("ElevenLabs is busy", r.stderr)
        self.fake.busy, n = 2, len(self.speak_calls())
        r = self.make("--yes", STUDIO_ELEVEN_BACKOFF="0.01")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.speak_calls()) - n, 4)                # 2 lines + 2 tries again
        self.assertTrue((self.d / "voices" / "l3.wav").is_file())

    def test_effect_change_does_not_read_again(self):
        self.assertEqual(self.make("--yes").returncode, 0)
        n = len(self.speak_calls())
        rows = json.loads((self.d / "lines.json").read_text())
        rows[2]["fx"] = "phone"
        rows[1]["pitch"] = 4
        self.write(rows)
        r = self.make("--changed")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("effects only 2", r.stdout)
        self.assertEqual(len(self.speak_calls()), n)
        self.assertEqual(json.loads((self.d / "voices" / ".made.json").read_text())["l3"]["fx"], "phone")

    def test_one_line_needs_no_yes(self):
        r = self.make("--only", "l2")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.speak_calls()), 1)

    def test_not_enough_characters_reads_nothing(self):
        self.fake.limit = 30
        r = self.make("--yes")
        self.assertEqual(r.returncode, 3)
        self.assertIn("not enough characters: need 42, have 30", r.stderr)
        self.assertIn("--provider kokoro", r.stderr)
        self.assertEqual(self.speak_calls(), [])
        self.assertFalse((self.d / "voices" / "l1.wav").exists())

    def test_whole_film_with_kokoro(self):
        r = self.make("--provider", "kokoro")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.speak_calls(), [])
        sp = json.loads((self.d / "voices" / "speakers.json").read_text())
        self.assertEqual(sp["fallback"]["voices"], {"el:v_girl": "af_heart", "el:v_narr": "am_michael"})
        self.assertFalse((self.d / "voices" / "usage.json").exists())

    def test_bad_key_is_exit_3(self):
        r = self.make("--yes", ELEVENLABS_API_KEY="sk_wrong_000000000000")
        self.assertEqual(r.returncode, 3)
        self.assertIn("does not work", r.stderr)
        self.assertNotIn("sk_wrong_000000000000", r.stdout + r.stderr)

    def test_usage_command(self):
        self.make("--yes")
        r = subprocess.run(["sh", str(REPO / "bin" / "studio"), "voice", "usage", "demo"], capture_output=True, text=True,
                           env=self.env)
        self.assertIn("elevenlabs: 42 characters in 1 run(s)", r.stdout)

    def test_old_film_unchanged(self):
        """A film from before 036 (no prefixes, no new fields) is read only by Kokoro, never asks."""
        self.write([{"id": "a", "text": "Old line.", "voice": "am_michael", "speed": 1.1}])
        r = self.make()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.fake.calls, [])
        self.assertEqual(json.loads((self.d / "voices" / ".made.json").read_text())["a"],
                         {"text": "Old line.", "voice": "am_michael", "speed": 1.1})


class Emotions(unittest.TestCase):                                    # specs/036 T039 (FR-030, FR-031, FR-032)
    setUp, tearDown, write, make, speak_calls = (VoiceMakeProviders.setUp, VoiceMakeProviders.tearDown,
                                                 VoiceMakeProviders.write, VoiceMakeProviders.make,
                                                 VoiceMakeProviders.speak_calls)

    def emo_rows(self):
        rows = [dict(r) for r in LINES]
        rows[1]["emotion"] = "whisper"                                 # el:v_girl
        rows[0]["emotion"] = "shout"                                   # Kokoro: never acted
        return rows

    def test_v3_sends_the_tag(self):
        self.write(self.emo_rows())
        r = self.make("--yes", ELEVENLABS_MODEL="eleven_v3")
        self.assertEqual(r.returncode, 0, r.stderr)
        sent = {c[1].split("/")[3]: c[2] for c in self.speak_calls()}
        self.assertEqual(sent["v_girl"]["text"], "[whispers] Is that a real fish?")
        self.assertEqual(sent["v_girl"]["model_id"], "eleven_v3")
        self.assertEqual(json.loads((self.d / "lines.json").read_text())[1]["text"], "Is that a real fish?")
        self.assertIn("elevenlabs: 53 characters", r.stdout)            # 42 + "[whispers] " counted
        self.assertEqual(self.fake.used, 53)
        sp = json.loads((self.d / "voices" / "speakers.json").read_text())
        self.assertEqual(sp["emotions"], {"l1": {"emotion": "shout", "emotion_applied": False},
                                          "l2": {"emotion": "whisper", "emotion_applied": True}})

    def test_other_model_does_not_act(self):
        self.write(self.emo_rows())
        r = self.make("--yes")
        self.assertEqual(r.returncode, 0, r.stderr)
        sent = {c[1].split("/")[3]: c[2] for c in self.speak_calls()}
        self.assertEqual(sent["v_girl"]["text"], "Is that a real fish?")
        sp = json.loads((self.d / "voices" / "speakers.json").read_text())
        self.assertFalse(sp["emotions"]["l2"]["emotion_applied"])
        r = self.make("--provider", "kokoro")
        sp = json.loads((self.d / "voices" / "speakers.json").read_text())
        self.assertEqual({k: v["emotion_applied"] for k, v in sp["emotions"].items()}, {"l1": False, "l2": False})

    def test_no_alignment_uses_the_recogniser(self):                    # research R2
        self.fake.align = False
        r = self.make("--yes", ELEVENLABS_MODEL="eleven_v3")
        self.assertEqual(r.returncode, 0, r.stderr)
        align = json.loads((self.d / "voices" / "align.json").read_text())
        self.assertEqual(align["l2"], {"source": "asr"})

    def test_wall_line_passes_the_word_check(self):                     # FR-032 with a fake recogniser
        sys.path.insert(0, str(REPO / "tools"))
        from filmcheck import voicecheck
        self.assertEqual(self.make("--yes").returncode, 0)
        rows = json.loads((self.d / "lines.json").read_text())
        dur = json.loads((self.d / "voices" / "dur.json").read_text())
        words = {}
        for r in rows:
            ws = r["text"].split()
            step = max(0.1, (dur[r["id"]] - 0.2) / len(ws))
            words[r["id"]] = [[w, round(0.1 + i * step, 3), round(0.1 + (i + 1) * step, 3)] for i, w in enumerate(ws)]
        (self.d / "voices" / "words.json").write_text(json.dumps(words))
        issues = voicecheck.run(self.d, REPO / "lib" / "lemo-opuscar")["issues"]
        self.assertNotIn(("asr_mismatch", "l3"), [(i["rule"], i.get("ref")) for i in issues])
        self.assertEqual(json.loads((self.d / "voices" / ".made.json").read_text())["l3"]["fx"], "wall")


if __name__ == "__main__":
    unittest.main()
