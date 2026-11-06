import json
import sys
import types
import unittest

from helpers import FX, Project, need_fixtures
import learn
from sl import fetch, measure, refset, summary


class OriginalAudio(unittest.TestCase):
    def fmt(self, lang, note=""):
        return {"vcodec": "none", "acodec": "opus", "language": lang, "format_note": note}

    def test_single_language_is_original(self):
        info = {"formats": [self.fmt("en"), self.fmt("en"), {"vcodec": "avc1", "acodec": "none"}]}
        self.assertTrue(fetch.audio_original(info, self.fmt("en")))

    def test_marked_original(self):
        info = {"formats": [self.fmt("en", "English original (default)"), self.fmt("de", "German")]}
        self.assertTrue(fetch.audio_original(info, info["formats"][0]))

    def test_dubbed_unmarked_is_unknown(self):
        info = {"formats": [self.fmt("en"), self.fmt("de")]}
        self.assertIsNone(fetch.audio_original(info, self.fmt("de")))


class NoSpeech(unittest.TestCase):
    def setUp(self):
        need_fixtures(self)
        self.p = Project()
        self.saved = sys.modules.get("faster_whisper")

        class Silent:                       # Whisper on music: a language guess and no words
            def __init__(self, *a, **k):
                pass

            def transcribe(self, audio, language=None, word_timestamps=False):
                return [], types.SimpleNamespace(language="zh")
        sys.modules["faster_whisper"] = types.SimpleNamespace(WhisperModel=Silent)

    def tearDown(self):
        if self.saved is None:
            sys.modules.pop("faster_whisper", None)
        else:
            sys.modules["faster_whisper"] = self.saved
        self.p.close()

    def test_music_only_is_reported_not_guessed(self):
        fetch.fetch_files("music-set", [FX / "tone.mp4"])
        measure.measure_set("music-set", log=lambda *_: None)
        self.assertEqual(learn.main(["transcribe", "music-set"]), 0)
        vj = json.loads((refset.profile_dir("music-set", "v01") / "video.json").read_text())
        self.assertEqual(vj["speech"]["words"], 0)
        self.assertIsNone(vj["speech"]["language"])            # not the meaningless "zh" guess
        s = summary.build("music-set")
        self.assertEqual(s["no_speech"], ["v01"])
        self.assertIsNone(s["by_orientation"]["landscape"]["metrics"]["speech_rate"]["median"])
        self.assertIsNotNone(s["by_orientation"]["landscape"]["metrics"]["first_voice_t"]["median"])
        self.assertIn("Không phát hiện lời nói", (refset.set_dir("music-set") / "profile" / "summary.md").read_text())


if __name__ == "__main__":
    unittest.main()
