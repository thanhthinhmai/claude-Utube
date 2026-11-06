"""Decode every frame of the measured part with ffmpeg into numpy arrays (research.md §3)."""
import subprocess
from pathlib import Path

import numpy as np

from .probe import is_whole, scaled_height
from .refset import StepError

WIDTH = 320


def iter_frames(path: Path, meta: dict, segs: list):
    """Yield (segment_index, t_in_video, frame H×320×3 uint8)."""
    h = scaled_height(meta["width"], meta["height"], WIDTH)
    size = WIDTH * h * 3
    whole = is_whole(segs, meta["duration"])
    for si, (a, b) in enumerate(segs):
        cmd = ["ffmpeg", "-v", "error", "-nostdin"]
        if not whole:
            cmd += ["-ss", f"{a:.4f}", "-t", f"{b - a:.4f}"]
        cmd += ["-i", str(path), "-an", "-sn",
                "-vf", f"scale={WIDTH}:{h}:flags=area,format=rgb24",
                "-f", "rawvideo", "-"]
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=size * 4)
        except FileNotFoundError:
            raise StepError("cần ffmpeg")
        k = 0
        try:
            while True:
                buf = p.stdout.read(size)
                if len(buf) < size:
                    break
                yield si, a + k / meta["fps"], np.frombuffer(buf, np.uint8).reshape(h, WIDTH, 3)
                k += 1
        finally:
            if p.poll() is None and len(buf) == size:      # consumer stopped early
                p.kill()
            p.stdout.close()
            err = p.stderr.read().decode(errors="replace")
            p.stderr.close()
            p.wait()
        if p.returncode != 0 and k == 0:
            raise StepError(f"ffmpeg không giải mã được: {err.strip()[:200]}")
