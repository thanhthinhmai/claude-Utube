import unittest

import numpy as np

from helpers import FX, need_fixtures
from sl import color, measure


class ColorAudio(unittest.TestCase):
    def setUp(self):
        need_fixtures(self)

    def test_flat_luma(self):  # SC-002
        p = measure.analyze(FX / "flat.mp4")["profile"]
        expect = (0.2126 * 100 + 0.7152 * 150 + 0.0722 * 200) / 255
        self.assertAlmostEqual(p["luma"]["p50"], expect, delta=0.02)
        self.assertLess(p["dark"]["p50"], 0.01)

    def test_dark_bright(self):
        p = measure.analyze(FX / "bw.mp4")["profile"]
        self.assertAlmostEqual(p["dark"]["p50"], 0.5, delta=0.03)
        self.assertAlmostEqual(p["bright"]["p50"], 0.5, delta=0.03)

    def test_palette_three_colours(self):
        p = measure.analyze(FX / "stripes.mp4")["profile"]
        self.assertEqual(len(p["palette"]), 3, p["palette"])
        self.assertIn("palette_note", p)
        want = [color.to_lab(np.array([c], np.uint8))[0] for c in [(200, 30, 30), (30, 170, 40), (30, 40, 200)]]
        for w in want:
            self.assertLess(min(color.delta_e(w, np.array(c["lab"])) for c in p["palette"]), 5)

    def test_palette_six_from_rainbow(self):  # FR-007
        p = measure.analyze(FX / "rainbow.mp4")["profile"]
        self.assertEqual(len(p["palette"]), 6)
        self.assertAlmostEqual(sum(c["share"] for c in p["palette"]), 1.0, delta=0.35)

    def test_audio_silence(self):
        a = measure.analyze(FX / "tone.mp4")["profile"]["audio"]
        self.assertTrue(np.isfinite(a["lufs"]))
        self.assertEqual(a["silence_count"], 2)
        self.assertAlmostEqual(a["silence_total"], 1.5, delta=0.1)
        self.assertLess(a["first_voice_t"], 0.1)

    def test_no_audio(self):
        self.assertIsNone(measure.analyze(FX / "flat.mp4")["profile"]["audio"])


if __name__ == "__main__":
    unittest.main()
