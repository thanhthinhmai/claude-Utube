"""Outline width on frames of a film, as a share of the frame width (specs/028 T021, US2 scenario 1).

Same method as the visual report of the style (EVIDENCE.md, "Outlines" row 2): on each frame, run lengths of dark
pixels (luma < 70) along every 4th row; the mode of runs 3–40 px is the outline width.
  python3 my-styles/sketch-explainer/kit/tools/linewidth.py <video> <t1> [<t2> …]
Needs ffmpeg and numpy (tools/.venv).
"""
import subprocess
import sys
from collections import Counter

import numpy as np


def frame(video: str, t: float, w: int = 1920, h: int = 1080) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", video, "-frames:v", "1", "-vf", f"scale={w}:{h}",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w)


def runs(img: np.ndarray, thr: int = 70) -> Counter:
    c = Counter()
    for row in img[::4]:
        dark = np.concatenate(([0], (row < thr).astype(np.int8), [0]))
        d = np.diff(dark)
        for a, b in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
            if 3 <= b - a <= 40:
                c[int(b - a)] += 1
    return c


def main(argv):
    video, times = argv[0], [float(x) for x in argv[1:]]
    allc = Counter()
    for t in times:
        c = runs(frame(video, t))
        allc += c
        m = c.most_common(1)[0][0] if c else 0
        print(f"t={t:6.2f}  mode {m:2d} px  = {m / 1920 * 100:.2f}% of the width")
    m = allc.most_common(1)[0][0] if allc else 0
    print(f"all     mode {m:2d} px  = {m / 1920 * 100:.2f}% of the width (style: 0.45–0.6%)")
    return 0 if 0.0045 * 1920 <= m <= 0.0065 * 1920 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
