"""specs/023 T049: the kit's sound (timing, score, effects, mix). Run with the library's Python from its root:
   cd lib/lemo-opuscar && .venv/bin/python -m unittest discover -s <repo>/tests/render -p test_sound.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
SOUND = REPO / "my-styles" / "dusk-hypothetical" / "kit" / "sound"
sys.path.insert(0, os.getcwd())
sys.path.insert(0, str(SOUND))
import timing  # noqa: E402

TPL = json.loads((REPO / "my-styles" / "dusk-hypothetical" / "template.json").read_text())


class Timing(unittest.TestCase):
    def test_pauses_by_kind(self):
        lines = [{"id": "a", "para": 1, "text": "You wake up"}, {"id": "b", "para": 1, "text": "and it is quiet."},
                 {"id": "c", "para": 1, "text": "Nobody talks."}, {"id": "d", "para": 2, "text": "Then a sound."},
                 {"id": "e", "para": 2, "text": "Sixteen thousand words."}]
        at, end = timing.schedule(lines, {k: 1.0 for k in "abcde"}, TPL)
        v = TPL["voice"]
        self.assertAlmostEqual(at["b"] - at["a"] - 1, timing.mid(v["pause_in"]), places=3)
        self.assertAlmostEqual(at["c"] - at["b"] - 1, timing.mid(v["pause_sent"]), places=3)
        self.assertAlmostEqual(at["d"] - at["c"] - 1, timing.mid(v["pause_para"]), places=3)
        self.assertAlmostEqual(at["e"] - at["d"] - 1, max(timing.mid(v["pause_sent"]), timing.mid(v["pre_number"])), places=3)
        self.assertAlmostEqual(end, at["e"] + 1, places=3)


class Fit(unittest.TestCase):
    def test_fits_the_silence_rule_and_keeps_the_order(self):
        lines = [{"id": f"l{i}", "para": i // 3, "text": "Ten words." if i % 4 == 3 else "A short line."} for i in range(30)]
        spoken = {f"l{i}": 0.9 for i in range(30)}
        at, end, k = timing.fit(lines, spoken, TPL, silence_max=0.19, tail=1.45)
        self.assertLess(k, 1.0)
        self.assertLessEqual((end + 1.45 - 27) / (end + 1.45), 0.19 + 1e-9)
        g = lambda a, b: at[b] - at[a] - 0.9
        self.assertGreater(g("l2", "l3"), g("l0", "l1"))          # a paragraph pause stays longer than a sentence pause
        six = lines[:6]
        at2, end2, k2 = timing.fit(six, {ln["id"]: 3.0 for ln in six}, TPL)
        self.assertEqual(k2, 1.0)                                   # long lines: no need to shrink


HAVE_LIB = (Path.cwd() / "core" / "audio" / "sampler.py").exists()


@unittest.skipUnless(HAVE_LIB, "run from the library root with its Python")
class ScoreAndMix(unittest.TestCase):
    def test_score(self):
        import score
        y = score.compose([["benefit", 0, 4], ["cost", 4, 8]], 8.0, TPL, seed=3)
        self.assertEqual(y.shape, (8 * score.SR, 2))
        a, b = np.sqrt(np.mean(y[:4 * score.SR] ** 2)), np.sqrt(np.mean(y[4 * score.SR:] ** 2))
        self.assertGreater(a, 0.01)
        self.assertGreater(a, b)                                    # the cost is thinner than the benefit
        y2 = score.compose([["benefit", 0, 4], ["cost", 4, 8]], 8.0, TPL, seed=3)
        self.assertTrue(np.allclose(y, y2))                         # same seed, same score

    def test_mix_levels(self):
        import mix
        d = Path(tempfile.mkdtemp(prefix="mix."))
        try:
            (d / "voices").mkdir(); (d / "kit").mkdir()
            shutil.copy(REPO / "my-styles" / "dusk-hypothetical" / "template.json", d / "kit" / "template.json")
            sr = 24000
            t = np.arange(int(1.0 * sr)) / sr
            v = (0.3 * np.sin(2 * np.pi * 180 * t) * (1 + 0.5 * np.sin(2 * np.pi * 4 * t))).astype(np.float32)
            with wave.open(str(d / "voices" / "l1.wav"), "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((v * 32767).astype(np.int16).tobytes())
            ev = {"dur": 8.0, "ev": [{"type": "voice", "id": "l1", "t": t0} for t0 in (0.5, 2.5, 4.5, 6.2)] + [{"type": "pop", "t": 1.8}]}
            (d / "events.json").write_text(json.dumps(ev))
            (d / "beats.json").write_text(json.dumps([["benefit", 0, 4], ["cost", 4, 8]]))
            out = mix.mix(str(d))
            import soundfile as sf
            y, sr2 = sf.read(out)
            r = lambda a, b: float(np.sqrt(np.mean(y[int(a * sr2):int(b * sr2)] ** 2)))
            # the pauses (1.6–2.4 s in the benefit, 5.6–6.1 s in the cost): the cost's score sits lower (T067)
            self.assertGreater(20 * np.log10(r(1.6, 2.4) / r(5.6, 6.1)), 3.0)
            r = subprocess.run(["ffmpeg", "-hide_banner", "-i", out, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True)
            lufs = float([l for l in r.stderr.splitlines() if l.strip().startswith("I:")][-1].split()[1])
            self.assertAlmostEqual(lufs, -14.0, delta=1.0)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_mix_settings(self):                                     # specs/026 T046: mix.json from the job page
        import mix
        d = Path(tempfile.mkdtemp(prefix="mix."))
        try:
            (d / "voices").mkdir(); (d / "kit").mkdir()
            shutil.copy(REPO / "my-styles" / "dusk-hypothetical" / "template.json", d / "kit" / "template.json")
            sr = 24000
            v = (0.3 * np.sin(2 * np.pi * 180 * np.arange(sr) / sr)).astype(np.float32)
            with wave.open(str(d / "voices" / "l1.wav"), "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((v * 32767).astype(np.int16).tobytes())
            (d / "events.json").write_text(json.dumps({"dur": 6.0, "ev": [{"type": "voice", "id": "l1", "t": 0.5}]}))
            import soundfile as sf
            gap = lambda y, s: float(np.sqrt(np.mean(y[int(3 * s):int(5 * s)] ** 2)))     # noqa: E731  no voice here
            y1, s1 = sf.read(mix.mix(str(d)))
            (d / "mix.json").write_text(json.dumps({"music": "none"}))
            y2, s2 = sf.read(mix.mix(str(d)))
            self.assertLess(gap(y2, s2), gap(y1, s1) / 10)               # no music: the pause is near silent
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
