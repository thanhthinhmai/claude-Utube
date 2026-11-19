"""How much of a frame is in focus, measured the same way on reference frames and on film frames (specs/021 FR-003,
research R1). Python standard library and ffmpeg only.

The frame is scaled to 480 px wide in grey; the letterbox (rows near black and flat, from each edge) and the subtitle
band (the bottom part of the picture) are left out; the rest is cut into 4 × 3 tiles. A tile is in focus when the
variance of its Laplacian is at least FOCUS_T."""
import subprocess
from pathlib import Path

FOCUS_T = 200.0         # set on dusk-hypothetical's reference frames: 99.3 % have a tile this sharp (research R1, T020)
W = 480
COLS, ROWS = 4, 3
EDGE = 3                # rows kept clear of a letterbox edge


class FocusError(Exception):
    """The frame cannot be read."""


def _grey(image: Path):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(image), "-vf", f"scale={W}:-2,format=gray",
                        "-f", "rawvideo", "-"], capture_output=True)
    n = len(p.stdout)
    if p.returncode != 0 or n == 0 or n % W:
        raise FocusError(f"{Path(image).name} cannot be read: {p.stderr.decode(errors='replace').strip()[-200:]}")
    return p.stdout, n // W


def _bar(px: bytes, y: int) -> bool:
    row = px[y * W:(y + 1) * W]
    m = sum(row) / W
    var = sum((v - m) ** 2 for v in row[::4]) / (W // 4)
    return m < 0.03 * 255 and var ** 0.5 < 0.01 * 255


def measure(image, subtitle_band: float = 0.18) -> dict:
    """{tiles, focused_share, sharpest, sharpest_at: [col, row], letterbox: [top, bottom] (fractions)}."""
    px, h = _grey(Path(image))
    top = 0
    while top < h // 3 and _bar(px, top):
        top += 1
    bot = h
    while bot > h * 2 // 3 and _bar(px, bot - 1):
        bot -= 1
    top_bar, bot_bar = top, h - bot                     # the bar's own edge is sharp: keep clear of it
    if top:
        top += EDGE
    if bot < h:
        bot -= EDGE
    pic = bot - top
    y1 = bot - int(round(pic * subtitle_band))          # leave out the subtitle band
    y0 = top
    tiles = []
    th = (y1 - y0) // ROWS
    tw = W // COLS
    for r in range(ROWS):
        for c in range(COLS):
            s = q = 0.0
            n = 0
            for y in range(max(1, y0 + r * th), min(h - 1, y0 + (r + 1) * th)):
                base = y * W
                up, dn = base - W, base + W
                for x in range(max(1, c * tw), min(W - 1, (c + 1) * tw)):
                    v = 4 * px[base + x] - px[base + x - 1] - px[base + x + 1] - px[up + x] - px[dn + x]
                    s += v
                    q += v * v
                    n += 1
            tiles.append(round(q / n - (s / n) ** 2, 1) if n else 0.0)
    best = max(range(len(tiles)), key=lambda i: tiles[i])
    return {"tiles": tiles, "focused_share": round(sum(t >= FOCUS_T for t in tiles) / len(tiles), 3),
            "sharpest": tiles[best], "sharpest_at": [best % COLS, best // COLS],
            "letterbox": [round(top_bar / h, 3), round(bot_bar / h, 3)]}


def share(tiles: list, t: float = None) -> float:
    """The focused share of stored tile variances at a threshold (default FOCUS_T)."""
    t = FOCUS_T if t is None else t
    return round(sum(x >= t for x in tiles) / len(tiles), 3) if tiles else 0.0
