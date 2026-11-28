"""Measure a ball@3 cast-sheet picture (specs/040 T006, SC-002): height in heads, eye / leg / hand widths over head width.

usage: tools/.venv/bin/python specs/040-whatif-rig/measure_sheet.py <front.jpg> [...]
The sheet has a flat light background; the figure is everything that differs from it (the soft floor shadow is dropped
by a stronger threshold near the feet). Widths are pixel runs along rows; accuracy about +-1 px."""
import json
import sys

import numpy as np
from PIL import Image


def runs(row):
    out, start = [], None
    for i, v in enumerate(list(row) + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append((start, i))
            start = None
    return out


def measure(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(int)
    bg = np.median(np.concatenate([a[:4].reshape(-1, 3), a[:, :4].reshape(-1, 3)]), axis=0)
    diff = np.abs(a - bg).sum(axis=2)
    mask = diff > 90
    lum0 = a.mean(axis=2)
    grey = (np.abs(a[..., 0] - a[..., 1]) < 6) & (np.abs(a[..., 2] - a[..., 1]) < 8) & (lum0 > 140) & (lum0 < 215)
    rows = np.where((mask & ~grey).any(axis=1))[0]     # the floor shadow is a neutral grey: not the figure
    top, bot = int(rows[0]), int(rows[-1])
    lum = a.mean(axis=2)
    dark = (lum < 70) & mask
    # head: the topmost big dark blob, grown by flood fill (the eyes leave holes; hats and hair are not this dark).
    # Its widest rows give the centre; the silhouette run there (with the light rim) is the head width W.
    from collections import deque
    seed = None
    for y in range(top, bot):
        rr = [(s, e) for s, e in runs(dark[y]) if e - s >= 15]
        if rr:
            s0, e0 = max(rr, key=lambda r: r[1] - r[0])
            seed = (y + 3, (s0 + e0) // 2)
            break
    seen = np.zeros_like(dark)
    q = deque([seed]); seen[seed] = True
    ys0 = seed[0]
    while q:
        y, x = q.popleft()
        for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= yy < dark.shape[0] and 0 <= xx < dark.shape[1] and dark[yy, xx] and not seen[yy, xx] and yy < ys0 + 160:
                seen[yy, xx] = True
                q.append((yy, xx))
    rows = {}
    for y in np.where(seen.any(axis=1))[0]:
        xs = np.where(seen[y])[0]
        rows[int(y)] = (int(xs.min()), int(xs.max()) + 1)
    wmax = max(e - s for s, e in rows.values())
    rows_c = [y for y, (s, e) in rows.items() if e - s >= wmax - 1]
    head_row = int(round(sum(rows_c) / len(rows_c)))
    hs, he = rows[min(rows, key=lambda y: abs(y - head_row))]
    for s, e in runs(mask[head_row]):
        if s <= hs and e >= he:
            hs, he = s, e
            break
    head_w = he - hs
    head_top = head_row - head_w / 2.0
    height = bot - head_top
    # eyes: light runs (white and its grey ring) on the eye rows, inside the head
    eye = 0
    for y in range(int(head_row - head_w * 0.08), int(head_row + head_w * 0.12)):
        for s, e in runs(lum[y, hs:he] > 120):
            if e - s < head_w * 0.45:
                eye = max(eye, e - s)
    # legs: two runs a little above the shoes (12 % of the height above the bottom)
    ly = int(bot - 0.14 * height)
    leg_runs = [e - s for s, e in runs(mask[ly]) if e - s > 3]
    legs = sorted(leg_runs)[:2] if len(leg_runs) >= 2 else leg_runs
    # hands: dark runs below the head, near the hips
    hand = 0
    for y in range(int(head_row + head_w * 0.9), int(bot - 0.2 * height)):
        rr = [e - s for s, e in runs(dark[y]) if e - s > 3]
        if len(rr) == 2 and abs(rr[0] - rr[1]) <= 2 and max(rr) < head_w * 0.5:   # two matching balls: the hands
            hand = max(hand, max(rr))
    W = float(head_w)
    return {"file": path, "head_w_px": head_w, "height_heads": round(height / W, 2), "eye_W": round(eye / W, 3),
            "leg_W": round((sum(legs) / len(legs) if legs else 0) / W, 3), "hand_W": round(hand / W, 3),
            "legs_px": legs, "height_px": round(height, 1)}


if __name__ == "__main__":
    print(json.dumps([measure(p) for p in sys.argv[1:]], indent=1))
