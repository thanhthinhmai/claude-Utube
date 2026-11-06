import sys
import types
import unittest

import numpy as np

from helpers import FX, need_fixtures
from sl import probe, speech


class FakeModel:
    calls = []

    def __init__(self, *a, **k):
        pass

    def transcribe(self, audio, language=None, word_timestamps=False):
        FakeModel.calls.append(audio)
        w = types.SimpleNamespace(word=" hello", start=0.5, end=0.9)
        return [types.SimpleNamespace(words=[w])], types.SimpleNamespace(language="en")


class Transcribe(unittest.TestCase):
    def setUp(self):
        need_fixtures(self)
        FakeModel.calls = []
        self.saved = sys.modules.get("faster_whisper")
        sys.modules["faster_whisper"] = types.SimpleNamespace(WhisperModel=FakeModel)

    def tearDown(self):
        if self.saved is None:
            sys.modules.pop("faster_whisper", None)
        else:
            sys.modules["faster_whisper"] = self.saved

    def test_passes_decoded_samples_not_a_path(self):
        # PyAV 19 breaks faster-whisper when it opens files itself; we hand it 16 kHz samples instead
        m = probe.probe(FX / "tone.mp4")
        r = speech.transcribe(FX / "tone.mp4", m, [[0.0, m["duration"]]])
        self.assertEqual(len(FakeModel.calls), 1)
        a = FakeModel.calls[0]
        self.assertIsInstance(a, np.ndarray)
        self.assertEqual(a.dtype, np.float32)
        self.assertAlmostEqual(len(a) / 16000, 5.0, delta=0.1)
        self.assertEqual(r, {"language": "en", "words": [{"word": "hello", "start": 0.5, "end": 0.9}]})

    def test_segment_offsets(self):
        m = probe.probe(FX / "long.mp4")                 # no audio track: every segment is skipped
        r = speech.transcribe(FX / "long.mp4", m, probe.segments(m["duration"]))
        self.assertEqual(r["words"], [])
        self.assertEqual(FakeModel.calls, [])                 # model never called without audio
        m2 = probe.probe(FX / "tone.mp4")
        r2 = speech.transcribe(FX / "tone.mp4", m2, [[1.0, 2.0], [3.0, 4.5]])
        self.assertEqual([w["start"] for w in r2["words"]], [1.5, 3.5])   # word times shifted by segment start


if __name__ == "__main__":
    unittest.main()
