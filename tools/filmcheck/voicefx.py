"""After the voice is read (specs/036 research R6, R7): pitch in semitones and a sound effect, with ffmpeg.

Works the same for every provider. The length stays (an echo tail adds at most 0.15 s), so dur.json and the
picture timing hold."""
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

FX = {
    "none": "",
    "phone": "highpass=f=300,lowpass=f=3400,acompressor=ratio=4,volume=1.2",
    "wall": "lowpass=f=700,volume=0.45,aecho=0.6:0.4:25:0.25",
    "radio": "highpass=f=500,lowpass=f=4000,acrusher=bits=10:mix=0.25",
    "hall": "aecho=0.8:0.7:60|120:0.35|0.2",
}
EMOTIONS = ("neutral", "whisper", "shout", "laugh", "cry", "sarcastic")
FALLBACK_GAIN = {"whisper": "volume=-6dB", "shout": "volume=3dB"}    # when the provider cannot act it
TAIL = 0.15


@lru_cache(maxsize=1)
def has_rubberband() -> bool:
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return " rubberband " in out


def pitch_filter(semitones: float, formant: str = None, rate: int = 24000, rubberband: bool = None) -> str:
    st = max(-6.0, min(6.0, float(semitones or 0)))
    if abs(st) < 0.01:
        return ""
    r = 2 ** (st / 12)
    formant = formant or ("shifted" if st > 0 else "preserved")
    if has_rubberband() if rubberband is None else rubberband:
        return f"rubberband=pitch={r:.5f}:formant={formant}"
    return f"asetrate={rate * r:.0f},aresample={rate},atempo={1 / r:.5f}"     # tone and timbre move together


def chain(pitch: float = 0, formant: str = None, fx: str = "none", emotion_fallback: str = None,
          rate: int = 24000, rubberband: bool = None) -> str:
    if fx not in FX:
        raise ValueError(f"unknown fx '{fx}' (one of {', '.join(FX)})")
    parts = [pitch_filter(pitch, formant, rate, rubberband), FALLBACK_GAIN.get(emotion_fallback or "", ""), FX[fx]]
    return ",".join(p for p in parts if p)


def duration(path: Path) -> float:
    import wave
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def apply(raw: Path, out: Path, pitch: float = 0, formant: str = None, fx: str = "none",
          emotion_fallback: str = None, rubberband: bool = None) -> Path:
    """raw .wav → out .wav (24 kHz mono 16-bit). With nothing to do, a plain copy."""
    raw, out = Path(raw), Path(out)
    import wave
    with wave.open(str(raw)) as w:
        rate = w.getframerate()
    f = chain(pitch, formant, fx, emotion_fallback, rate, rubberband)
    if not f:
        if raw.resolve() != out.resolve():
            shutil.copyfile(raw, out)
        return out
    limit = duration(raw) + (TAIL if fx in ("wall", "hall") else 0)
    tmp = out.with_name(out.stem + ".fx.wav")
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(raw), "-af", f, "-t", f"{limit:.3f}",
                        "-ar", str(rate), "-ac", "1", "-sample_fmt", "s16", str(tmp)], capture_output=True, text=True)
    if r.returncode != 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg could not apply '{f}': {r.stderr.strip()[-300:]}")
    tmp.replace(out)
    return out
