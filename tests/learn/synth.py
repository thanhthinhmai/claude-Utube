"""A synthetic film with known camera moves, in-shot movement and transitions (specs/023 T002, SC-003).

make(path) draws the video with numpy (camera = a window over a large smooth world picture; a "hand" = a block
that rises in 0.4 s and then holds) and encodes it with ffmpeg; it returns the answer key:
  {"fps", "width", "shots": [{"t0", "t1", "cam", "inner": [[t0, t1]], "trans_in": (type, dur)}]}
Speeds in the key are px/s at 1280 wide and %/s of zoom, as in craft.json. 640×360 at 30 fps keeps the test fast;
craft.py samples at 12 frames/s and 320×180 anyway."""
import subprocess
from pathlib import Path

import numpy as np

W, H, FPS = 640, 360, 30
SHOT = 2.5


def world(seed=7, w=2400, h=1400):
    """Smooth random texture with strong detail at 8–40 px, so block matching locks on everywhere."""
    r = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    for cell, amp in ((48, 70), (16, 45), (6, 25)):
        g = r.normal(0, 1, (h // cell + 3, w // cell + 3)).astype(np.float32)
        ys, xs = np.arange(h) / cell, np.arange(w) / cell
        y0, x0 = ys.astype(int), xs.astype(int)
        fy, fx = (ys - y0)[:, None], (xs - x0)[None, :]
        a, b = g[y0][:, x0], g[y0][:, x0 + 1]
        c, d = g[y0 + 1][:, x0], g[y0 + 1][:, x0 + 1]
        out += amp * ((a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy)
    out = np.clip(out + 120, 10, 235)
    rgb = np.stack([out, out * 0.85 + 20, out * 0.7 + 30], -1)
    return np.clip(rgb, 0, 255).astype(np.float32)


def view(wld, cx, cy, zoom):
    """The camera's frame: a W/zoom × H/zoom window centred at (cx, cy), resampled bilinearly to W × H."""
    xs = cx + (np.arange(W) - W / 2 + 0.5) / zoom
    ys = cy + (np.arange(H) - H / 2 + 0.5) / zoom
    x0, y0 = np.floor(xs).astype(int), np.floor(ys).astype(int)
    fx, fy = (xs - x0)[None, :, None], (ys - y0)[:, None, None]
    a, b = wld[y0][:, x0], wld[y0][:, x0 + 1]
    c, d = wld[y0 + 1][:, x0], wld[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


# shot table: camera (px/s at 640 wide → key doubles it to 1280), zoom %/s, hand (rise start, s) or None,
# hand_world: the hand is drawn in the world (moves with the background) unless "screen" (camera follows it)
SHOTS = [
    dict(cam="still", hand=None),
    dict(cam="still", hand=0.9),
    dict(cam="drift-h", vx=20, hand=None),
    dict(cam="drift-v", vy=15, hand=None),
    dict(cam="push", zoom=3.0, hand=None),
    dict(cam="pull", zoom=-3.0, hand=None),
    dict(cam="drift-h", vx=-20, hand=1.1),
    dict(cam="drift-h", vx=20, hand=None, static_block=True),
    dict(cam="follow", vx=25, hand=None, follow=True),
    dict(cam="still", hand=0.6),
]
# transition INTO shot i (index), centred on the cut
TRANS = {2: ("streak", 0.15), 4: ("dip", 0.13), 6: ("fade", 0.3), 7: ("wipe", 0.3), 9: ("dissolve", 0.4)}


def shot_frame(wld, i, s, t):
    """Frame of shot i at t seconds into the shot."""
    cx = 600 + i * 120 + s.get("vx", 0) * t
    cy = 500 + s.get("vy", 0) * t
    zoom = (1 + s.get("zoom", 0) / 100) ** t
    img = view(wld, cx, cy, zoom)
    if s.get("hand") is not None:                       # a "hand" rises 60 px in 0.4 s, then holds
        k = ease((t - s["hand"]) / 0.4)                 # drawn in the world: it slides with the background when the camera moves
        hx, hy = int(W * 0.62 - s.get("vx", 0) * t), int(H * 0.62 - 60 * k - s.get("vy", 0) * t)
        img[hy:hy + 50, hx:hx + 28] = (225, 190, 160)
    if s.get("static_block"):                           # a block fixed in the world: moves only with the camera
        x = int(W * 0.4 - s["vx"] * t)
        img[150:200, max(0, x):max(0, x + 30)] = (225, 190, 160)
    if s.get("follow"):                                 # a figure walking with the camera: fixed on screen, legs swing
        img[180:280, 300:330] = (60, 70, 160)
        sw = int(10 * np.sin(t * 2 * np.pi * 1.5))
        img[280:320, 300 + sw:312 + sw] = (60, 70, 160)
    return img


def frame_at(wld, j, n_shot):
    """Frame j of the film, transitions included. Frames are made one at a time, so memory stays flat."""
    i, k = divmod(j, n_shot)
    base = shot_frame(wld, i, SHOTS[i], k / FPS)
    for ti, (kind, dur) in TRANS.items():
        cut = ti * n_shot
        half = max(1, round(dur * FPS / 2))
        if not cut - half <= j < cut + half:
            continue
        u = (j - (cut - half) + 0.5) / (2 * half)
        if kind == "streak":                            # a bright horizontal smear over the middle band
            band = slice(int(H * 0.3), int(H * 0.62))
            base[band] = base[band] * 0.15 + 240 * 0.85
        elif kind == "dip":
            base = np.zeros_like(base) + 2
        elif kind == "fade":                            # out to black, then up
            base = base * abs(2 * u - 1)
        else:                                           # wipe and dissolve mix the frames either side of the span
            a_last = shot_frame(wld, ti - 1, SHOTS[ti - 1], (n_shot - half - 1) / FPS)
            b_first = shot_frame(wld, ti, SHOTS[ti], half / FPS)
            if kind == "wipe":                          # the next shot slides in from the left
                x = int(W * u)
                base = a_last.copy()
                base[:, :x] = b_first[:, :x]
            else:
                base = a_last * (1 - u) + b_first * u
    return base


def make(path: Path) -> dict:
    wld = world()
    n_shot = int(SHOT * FPS)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16", "-pix_fmt", "yuv420p", str(path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for j in range(len(SHOTS) * n_shot):
        p.stdin.write(np.clip(frame_at(wld, j, n_shot), 0, 255).astype(np.uint8).tobytes())
    p.stdin.close()
    if p.wait():
        raise SystemExit("ffmpeg failed")
    key = {"fps": FPS, "width": W, "shots": []}
    for i, s in enumerate(SHOTS):
        t0, t1 = i * SHOT, (i + 1) * SHOT
        inner = []
        if s.get("hand") is not None:
            inner.append([round(t0 + s["hand"], 3), round(t0 + s["hand"] + 0.4, 3)])
        if s.get("follow"):
            inner.append([t0, t1])
        key["shots"].append({"t0": t0, "t1": t1, "cam": s["cam"], "inner": inner,
                             "px_s": abs(s.get("vx", 0) or s.get("vy", 0)) * 1280 / W,
                             "trans_in": TRANS.get(i, ("cut", 0.0)) if i else None})
    return key


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(make(Path(sys.argv[1])), indent=1))
