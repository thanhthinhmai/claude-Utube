"""A synthetic film for the camera track (specs/039 T002): known total zoom, ease, drift and parallax per shot.

make(path) draws shots with synth.world()/view() (camera = a window over a large textured picture) and returns the key:
  {"fps", "shots": [{"t0", "t1", "zoom_pct", "ease": [q¼, q½, q¾] | None, "drift_px": [x, y] at 1080p,
                     "parallax": bool, "move"}]}
The camera path follows p(u) = u^a / (u^a + (1−u)^a), so the share of the move done at ¼, ½, ¾ of the shot is known.
A parallax shot has a second picture over the lower 40 % that zooms twice as much and drifts three times as far, as a
near layer does when a real camera moves. 640×360 at 30 fps; the key is at 1080p (×3)."""
import subprocess
from pathlib import Path

import numpy as np

import synth

W, H, FPS = synth.W, synth.H, synth.FPS
DUR = 3.0
TO_1080 = 1080 / H

SHOTS = [
    dict(zoom=6.0, a=1.6, dx=0, dy=8),
    dict(zoom=3.0, a=1.6, dx=0, dy=0),
    dict(zoom=9.0, a=2.2, dx=0, dy=12),
    dict(zoom=-5.0, a=1.6, dx=0, dy=0),
    dict(zoom=0.0, a=1.0, dx=0, dy=0),                       # still
    dict(zoom=0.0, a=1.6, dx=60, dy=0),                       # pan
    dict(zoom=6.0, a=1.6, dx=0, dy=8, parallax=True),
    dict(zoom=6.0, a=1.6, dx=0, dy=8, actor=True),            # a block moving on its own inside the shot
]


def progress(u, a):
    u = min(1.0, max(0.0, u))
    if a == 1.0:
        return u
    return u ** a / (u ** a + (1 - u) ** a)


def frame(wld, near, i, s, t):
    p = progress(t / DUR, s["a"])
    z = 1 + s["zoom"] / 100 * p
    cx = 700 + i * 150 + s["dx"] / TO_1080 * p / z      # the screen shifts by dx (1080p) at the end
    cy = 600 + s["dy"] / TO_1080 * p / z
    img = synth.view(wld, cx, cy, z)
    if s.get("parallax"):
        zn = 1 + 2 * s["zoom"] / 100 * p
        nx = 900 + 3 * s["dx"] / TO_1080 * p / zn
        ny = 500 + 3 * s["dy"] / TO_1080 * p / zn
        lower = synth.view(near, nx, ny, zn)
        cut = int(H * 0.6)
        img[cut:] = lower[cut:]
    if s.get("actor"):
        x = int(W * 0.3 + 120 * np.sin(np.pi * t / DUR))
        img[120:200, x:x + 40] = (230, 60, 60)
    return img


def make(path: Path) -> dict:
    wld, near = synth.world(7), synth.world(23)
    n = int(DUR * FPS)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    key = {"fps": FPS, "shots": []}
    for i, s in enumerate(SHOTS):
        for k in range(n):
            proc.stdin.write(np.clip(frame(wld, near, i, s, k / FPS), 0, 255).astype(np.uint8).tobytes())
        moving = s["zoom"] or s["dx"] or s["dy"]
        move = "static" if not moving else ("push" if s["zoom"] > 0 else "pull" if s["zoom"] < 0 else "pan")
        key["shots"].append({"t0": i * DUR, "t1": (i + 1) * DUR, "zoom_pct": s["zoom"], "move": move,
                             "ease": [round(progress(q, s["a"]), 3) for q in (0.25, 0.5, 0.75)] if moving else None,
                             "drift_px": [s["dx"], s["dy"]], "parallax": bool(s.get("parallax"))})
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError("ffmpeg failed")
    return key
