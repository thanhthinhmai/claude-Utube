"""specs/036 T006: pitch in semitones and the sound effects keep the length and do what they say."""
import math
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import voicefx  # noqa: E402

RATE = 24000


def tone(path: Path, freqs=(140.0,), secs=1.2):
    """A voiced-like buzz: a fundamental with harmonics, so pitch and band filters are measurable."""
    n = int(RATE * secs)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        frames = bytearray()
        for i in range(n):
            t = i / RATE
            v = sum(math.sin(2 * math.pi * f * k * t) / k for f in freqs for k in range(1, 80) if f * k < 11000)
            frames += struct.pack("<h", int(max(-1, min(1, v * 0.15)) * 32000))
        w.writeframes(bytes(frames))
    return path


def samples(path: Path):
    with wave.open(str(path)) as w:
        raw = w.readframes(w.getnframes())
    return [x / 32768 for x in struct.unpack(f"<{len(raw) // 2}h", raw)]


def f0(x):
    """Autocorrelation pitch of the middle 0.4 s."""
    mid = len(x) // 2
    s = x[mid - int(0.2 * RATE): mid + int(0.2 * RATE)]
    lo, hi = RATE // 500, RATE // 60
    best, lag = -1, lo
    for k in range(lo, hi):
        c = sum(s[i] * s[i + k] for i in range(0, len(s) - k, 2))
        if c > best:
            best, lag = c, k
    return RATE / lag


def band_energy(x, f_lo, f_hi):
    """Energy in a band over the middle 8192 samples."""
    import numpy as np
    mid = len(x) // 2
    s = np.array(x[mid - 4096: mid + 4096]) * np.hanning(8192)
    p = np.abs(np.fft.rfft(s)) ** 2
    f = np.fft.rfftfreq(8192, 1 / RATE)
    return float(p[(f >= f_lo) & (f < f_hi)].sum())


class VoiceFx(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp(prefix="vfx."))
        cls.raw = tone(cls.dir / "raw.wav")
        cls.base = f0(samples(cls.raw))

    def run_fx(self, name, **kw):
        out = self.dir / f"{name}.wav"
        voicefx.apply(self.raw, out, **kw)
        return out

    def test_up_four_semitones_raises_pitch_20_percent(self):
        for rb in ((True, False) if voicefx.has_rubberband() else (False,)):
            out = self.run_fx(f"up{rb}", pitch=4, rubberband=rb)
            self.assertGreaterEqual(f0(samples(out)) / self.base, 1.20, f"rubberband={rb}")
            self.assertAlmostEqual(voicefx.duration(out), voicefx.duration(self.raw), delta=0.05)

    def test_down_two_semitones_lowers_pitch(self):
        out = self.run_fx("down", pitch=-2)
        self.assertLess(f0(samples(out)), self.base * 0.95)

    def test_echo_tail_at_most_015_s(self):
        for fx in ("wall", "hall"):
            out = self.run_fx(fx, fx=fx)
            self.assertLessEqual(voicefx.duration(out), voicefx.duration(self.raw) + 0.16, fx)

    def test_phone_cuts_lows_and_highs(self):
        out = samples(self.run_fx("phone", fx="phone"))
        src = samples(self.raw)
        ratio_low = band_energy(out, 0, 250) / band_energy(src, 0, 250)
        ratio_mid = band_energy(out, 800, 2500) / band_energy(src, 800, 2500)
        ratio_high = band_energy(out, 5000, 11000) / band_energy(src, 5000, 11000)
        self.assertLess(ratio_low, ratio_mid / 4)
        self.assertLess(ratio_high, ratio_mid / 4)

    def test_nothing_to_do_is_a_copy(self):
        out = self.run_fx("plain")
        self.assertEqual(out.read_bytes(), self.raw.read_bytes())

    def test_fallback_without_rubberband(self):
        f = voicefx.pitch_filter(3, rubberband=False)
        self.assertTrue(f.startswith("asetrate="))
        self.assertIn("atempo=", f)

    def test_unknown_fx_is_refused(self):
        with self.assertRaises(ValueError):
            voicefx.chain(fx="underwater")


if __name__ == "__main__":
    unittest.main()
