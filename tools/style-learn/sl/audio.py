"""Loudness (EBU R128) and silences of the measured part (research.md §7)."""
import re
import subprocess
from pathlib import Path

import numpy as np

from .probe import is_whole

SR = 48000
WIN = 0.05            # 50 ms windows
SILENT_DB = -45.0
MIN_SILENCE = 0.25


def decode(path: Path, meta: dict, segs: list):
    """Mono float32 at 48 kHz for each segment, with the segment start time."""
    out = []
    whole = is_whole(segs, meta["duration"])
    for a, b in segs:
        cmd = ["ffmpeg", "-v", "error", "-nostdin"]
        if not whole:
            cmd += ["-ss", f"{a:.4f}", "-t", f"{b - a:.4f}"]
        cmd += ["-i", str(path), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
        r = subprocess.run(cmd, capture_output=True)
        out.append((a, np.frombuffer(r.stdout, np.float32)))
    return out


def loudness(samples: np.ndarray) -> tuple:
    if len(samples) < SR // 2:
        return None, None
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                        "-af", "ebur128", "-f", "null", "-"], input=samples.tobytes(), capture_output=True)
    err = r.stderr.decode(errors="replace")
    summ = err[err.rfind("Summary:"):] if "Summary:" in err else err
    i = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", summ)
    lra = re.search(r"LRA:\s+([\d.]+) LU", summ)
    lufs = float(i.group(1)) if i and i.group(1) != "-inf" else None
    return lufs, (float(lra.group(1)) if lra else None)


def silences(parts) -> dict:
    n = int(SR * WIN)
    total, count, first_voice = 0.0, 0, None
    for a, x in parts:
        k = len(x) // n
        if k == 0:
            continue
        rms = np.sqrt((x[:k * n].reshape(k, n).astype(np.float64) ** 2).mean(1))
        quiet = 20 * np.log10(rms + 1e-12) < SILENT_DB
        if first_voice is None and (~quiet).any():
            first_voice = a + float(np.argmax(~quiet)) * WIN
        run = 0
        for q in list(quiet) + [False]:
            if q:
                run += 1
            else:
                if run * WIN >= MIN_SILENCE:
                    total += run * WIN
                    count += 1
                run = 0
    return {"silence_total": round(total, 3), "silence_count": count,
            "first_voice_t": None if first_voice is None else round(first_voice, 3)}


def analyze(path: Path, meta: dict, segs: list):
    if not meta.get("has_audio"):
        return None
    parts = decode(path, meta, segs)
    allx = np.concatenate([x for _, x in parts]) if parts else np.zeros(0, np.float32)
    if len(allx) == 0:
        return None
    lufs, lra = loudness(allx)
    return {"lufs": lufs, "lra": lra, **silences(parts)}
