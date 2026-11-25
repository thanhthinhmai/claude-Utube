"""specs/036 T007: voice ids carry their provider; one catalogue for Kokoro and ElevenLabs."""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from filmcheck import eleven, voicecat  # noqa: E402
from fake_eleven import VOICES  # noqa: E402


class VoiceCat(unittest.TestCase):
    def test_ids(self):
        self.assertEqual(voicecat.parse("el:abc"), ("elevenlabs", "abc"))
        self.assertEqual(voicecat.parse("kokoro:af_bella"), ("kokoro", "af_bella"))
        self.assertEqual(voicecat.parse("am_michael"), ("kokoro", "am_michael"))     # films before 036

    def test_kokoro_row(self):
        r = voicecat.kokoro_row("bf_emma")
        self.assertEqual((r["id"], r["gender"], r["accent"], r["provider"]), ("kokoro:bf_emma", "female", "British", "kokoro"))

    def test_catalogue_joins_both_providers(self):
        el = [eleven.public_voice(v) for v in VOICES]
        rows = voicecat.catalog(el, kokoro=["am_michael", "af_heart"])
        self.assertEqual([r["provider"] for r in rows], ["kokoro", "kokoro"] + ["elevenlabs"] * 4)
        mine = next(r for r in rows if r["id"] == "el:v_mine")
        self.assertTrue(mine["cloned"])
        lib = next(r for r in rows if r["id"] == "el:v_lib")
        self.assertEqual((lib["cloned"], lib["library"]), (False, True))
        adam = next(r for r in rows if r["id"] == "el:v_narr")
        self.assertEqual((adam["gender"], adam["desc"], adam["cloned"]), ("male", "deep", False))


if __name__ == "__main__":
    unittest.main()
