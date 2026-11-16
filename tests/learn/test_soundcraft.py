"""specs/023 T023: soundcraft on synthetic audio with known pauses, music, tempo and sound effects."""
import unittest

import numpy as np

import helpers  # noqa: F401
from sl import soundcraft as sc

SR = sc.SR


def synth(seconds=40.0, bpm=90.0, music_db=-14.0, seed=3):
    """A fake narrator (band noise bursts at known word times), a chord bed with a kick at bpm, 6 clicks in pauses."""
    rnd = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    words, cur, k = [], 0.3, 0
    plan = []                                  # (gap after this word)
    while cur < seconds - 2:
        k += 1
        word = "three" if k % 11 == 0 else "word"
        dur = 0.3
        if k % 7 == 0:
            gap, mark = 0.9, "."                # paragraph
        elif k % 4 == 0:
            gap, mark = 0.42, "."               # sentence
        else:
            gap, mark = 0.12, ""
        if (k + 1) % 11 == 0 and gap < 0.35:
            gap = 0.35                          # the pause before a number
        words.append({"word": word + mark, "start": round(cur, 3), "end": round(cur + dur, 3)})
        plan.append(gap)
        cur += dur + gap
    voice = np.zeros(n, np.float32)
    for w in words:
        a, b = int(w["start"] * SR), int(w["end"] * SR)
        burst = rnd.normal(0, 1, b - a)
        spec = np.fft.rfft(burst)
        f = np.fft.rfftfreq(b - a, 1 / SR)
        spec[(f < 300) | (f > 3000)] = 0
        env = np.ones(b - a)
        ramp = int(0.01 * SR)
        env[:ramp], env[-ramp:] = np.linspace(0, 1, ramp), np.linspace(1, 0, ramp)
        voice[a:b] = np.fft.irfft(spec, b - a) * env       # an even word with 10 ms fades, like speech
    voice /= np.sqrt(np.mean(voice[voice != 0] ** 2))
    chord = sum(np.sin(2 * np.pi * f * t) for f in (220.0, 277.2, 329.6)) / 3
    beat = 60 / bpm
    kick = np.zeros(n)
    for b0 in np.arange(0, seconds, beat):
        i = int(b0 * SR)
        m = min(n - i, int(0.18 * SR))
        kick[i:i + m] += np.sin(2 * np.pi * 60 * np.arange(m) / SR) * np.exp(-np.arange(m) / (0.05 * SR))
    music = chord * 0.6 + kick * 1.6
    music *= 10 ** (music_db / 20) / np.sqrt(np.mean(music ** 2))
    sfx_t = []
    gaps = [(words[i]["end"], words[i + 1]["start"]) for i in range(len(words) - 1) if plan[i] >= 0.8]
    for a, b in gaps[:6]:
        tc = (a + b) / 2
        i = int(tc * SR)
        voice[i:i + 200] += rnd.normal(0, 4, 200)
        sfx_t.append(tc)
    return (voice + music).astype(np.float32), words, plan, sfx_t


class SoundCraft(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audio, cls.words, cls.plan, cls.sfx = synth()
        cls.res = sc.analyze(cls.audio, cls.words)

    def test_pauses(self):
        sp = self.res["speech"]
        self.assertAlmostEqual(float(np.median(sp["pause_in"])), 0.12, delta=0.05)
        self.assertAlmostEqual(float(np.median(sp["pause_sent"])), 0.42, delta=0.05)
        self.assertAlmostEqual(float(np.median(sp["pause_para"])), 0.9, delta=0.05)
        self.assertAlmostEqual(float(np.median(sp["pre_number"])), 0.35, delta=0.05)
        self.assertTrue(sp["wpm_10s"])

    def test_music_present_and_level(self):
        w = [x for x in self.res["music"]["windows"] if x[2] is not None]
        self.assertGreaterEqual(sum(bool(x[2]) for x in w) / len(w), 0.8)
        levels = [x[3] for x in w if x[3] is not None]
        self.assertAlmostEqual(float(np.median(levels)), -14.0, delta=2.0)

    def test_no_music(self):
        audio, words, _, _ = synth(music_db=-200)
        w = [x for x in sc.music_windows(audio, words) if x[2] is not None]
        self.assertLessEqual(sum(bool(x[2]) for x in w) / max(1, len(w)), 0.2)

    def test_tempo(self):
        self.assertAlmostEqual(self.res["music"]["tempo"], 90.0, delta=5.0)

    def test_sfx(self):
        got = self.res["sfx"]["onsets"]
        hits = sum(any(abs(g - s) < 0.1 for g in got) for s in self.sfx)
        self.assertGreaterEqual(hits, len(self.sfx) - 1)
        self.assertLessEqual(abs(len(got) - len(self.sfx)), 1)

    def test_beat_grid_removed(self):
        beat = 60 / 90
        grid = [round(0.1 + k * beat, 3) for k in range(60)]
        extra = [1.3, 7.0, 15.5, 22.2, 30.9, 36.4]
        got = sc.off_grid(sorted(grid + extra), 90)
        self.assertEqual(sorted(got), extra)

    def test_numbers(self):
        self.assertTrue(sc.is_number("16,000") and sc.is_number("three") and not sc.is_number("tree"))


if __name__ == "__main__":
    unittest.main()
