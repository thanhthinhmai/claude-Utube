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


if __name__ == "__main__":
    unittest.main()
