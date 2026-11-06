"""Camera motion by phase correlation, and cut / flash / dissolve detection (research.md §4–5)."""
import numpy as np

STILL_PX_720 = 0.5      # below this many px/frame at 720 wide, the camera counts as still
PEAK_OK = 0.05          # phase-correlation peak below this: motion estimate not trusted
CUT_MIN = 0.4


def gray(rgb: np.ndarray) -> np.ndarray:
    return rgb.astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def window(shape) -> np.ndarray:
    return np.outer(np.hanning(shape[0]), np.hanning(shape[1])).astype(np.float32)


def spectrum(g: np.ndarray, win: np.ndarray) -> np.ndarray:
    return np.fft.rfft2((g - g.mean()) * win)


def _sub(lo: float, c: float, hi: float) -> float:
    """Sub-pixel offset of a phase-correlation peak (Foroosh et al. 2002). A parabola fit under-reads
    slow pans by about half; this keeps the error near 10 % at 0.1 px/frame."""
    cs, s = (hi, 1.0) if hi > lo else (lo, -1.0)
    if cs <= 0 or c <= 0:
        return 0.0
    d = cs / (cs + c)
    if not 0 <= d < 1:
        d = cs / (cs - c) if cs != c else 0.0
    return s * d if 0 <= d < 1 else 0.0


def shift(prev_F: np.ndarray, cur_F: np.ndarray, shape) -> tuple:
    """Displacement (dx, dy) with cur(x) ≈ prev(x - d): content moving right gives dx > 0. Also the peak height."""
    R = cur_F * np.conj(prev_F)
    R /= np.abs(R) + 1e-12
    r = np.fft.irfft2(R, s=shape)
    H, W = shape
    y, x = np.unravel_index(int(np.argmax(r)), r.shape)
    peak = float(r[y, x])
    ox = _sub(r[y, (x - 1) % W], r[y, x], r[y, (x + 1) % W])
    oy = _sub(r[(y - 1) % H, x], r[y, x], r[(y + 1) % H, x])
    dx = x + ox if x <= W / 2 else x + ox - W
    dy = y + oy if y <= H / 2 else y + oy - H
    return float(dx), float(dy), peak


def hist(rgb: np.ndarray) -> np.ndarray:
    q = (rgb >> 4).reshape(-1, 3)
    n = q.shape[0]
    return np.concatenate([np.bincount(q[:, c], minlength=16) for c in range(3)]).astype(np.float32) / n


def hdist(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.abs(a - b).sum() / 6.0)


def thumb(rgb: np.ndarray) -> np.ndarray:
    """A 20-wide thumbnail for the dissolve test (block average)."""
    h, w = rgb.shape[:2]
    bh, bw = h // 12, w // 20
    t = rgb[:bh * 12, :bw * 20].astype(np.float32).reshape(12, bh, 20, bw, 3).mean((1, 3))
    return t


def events(d: np.ndarray, hists: np.ndarray, lum: np.ndarray, thumbs: np.ndarray, starts: set) -> dict:
    """Find hard cuts, flashes and soft transitions (dissolves) as frame indices.
    d[i] = histogram distance from frame i-1 to i (0 at segment starts). Never looks across a segment start."""
    n = len(d)
    seg_end = np.zeros(n, int)       # last frame index of each frame's segment
    end = n - 1
    for i in range(n - 1, -1, -1):
        seg_end[i] = end
        if i in starts:
            end = i - 1
    pad = np.pad(d, 15, mode="edge")
    med = np.median(np.lib.stride_tricks.sliding_window_view(pad, 31), axis=1)
    thr = np.maximum(CUT_MIN, 8 * med)

    flashes, skip = [], set()
    for i in range(1, n):
        if i in starts or lum[i] - lum[i - 1] <= 0.2:
            continue
        for j in range(i + 1, min(i + 7, seg_end[i] + 1)):
            if abs(lum[j] - lum[i - 1]) < 0.08 and hdist(hists[i - 1], hists[j]) < 0.25:
                flashes.append(i)
                skip.update(range(i, j + 1))
                break

    cuts = []
    for i in range(1, n):
        if i in starts or i in skip or d[i] <= thr[i]:
            continue
        k = min(i + 2, seg_end[i])
        if hdist(hists[i - 1], hists[k]) > CUT_MIN and not (cuts and cuts[-1] == i - 1):
            cuts.append(i)

    cutset = set(cuts)
    soft = []
    for span in (12, 24):
        for i in range(0, n - span):
            j = i + span
            if j > seg_end[i] or any(c in cutset or c in skip for c in range(i + 1, j + 1)):
                continue
            if hdist(hists[i], hists[j]) < CUT_MIN:
                continue
            ends = np.abs(thumbs[i] - thumbs[j]).mean()
            mid = np.abs(thumbs[(i + j) // 2] - (thumbs[i] + thumbs[j]) / 2).mean()
            if ends > 30 and mid < 0.15 * ends:
                soft.append([i, j])
    merged = []
    for a, b in sorted(soft):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return {"cuts": cuts, "flashes": flashes, "soft": merged}
