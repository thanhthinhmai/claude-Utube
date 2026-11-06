"""Per-frame tone statistics, Lab colour and the k-means palette (research.md §6)."""
import numpy as np

W709 = np.array([0.2126, 0.7152, 0.0722], np.float32)
NOISE_SHARE = 0.01     # clusters under 1 % of pixels are compression noise, not palette colours


def frame_stats(rgb: np.ndarray) -> tuple:
    f = rgb.astype(np.float32) / 255.0
    luma = f @ W709
    mx, mn = f.max(2), f.min(2)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    return (float(luma.mean()), float(luma.std()), float(np.median(sat)),
            float((luma < 0.06).mean()), float((luma > 0.94).mean()))


def to_lab(rgb) -> np.ndarray:
    c = np.asarray(rgb, np.float64).reshape(-1, 3) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], 1)


def delta_e(a, b) -> float:
    return float(np.linalg.norm(np.asarray(a, float) - np.asarray(b, float)))


def kmeans(x: np.ndarray, k: int = 8, iters: int = 25, seed: int = 7):
    rng = np.random.default_rng(seed)
    k = min(k, len(x))
    centers = [x[rng.integers(len(x))]]
    for _ in range(1, k):                                    # k-means++ start
        d2 = ((x[:, None, :] - np.array(centers)[None]) ** 2).sum(2).min(1)
        s = d2.sum()
        centers.append(x[rng.integers(len(x))] if s <= 0 else x[rng.choice(len(x), p=d2 / s)])
    c = np.array(centers)
    for _ in range(iters):
        lab = ((x[:, None, :] - c[None]) ** 2).sum(2).argmin(1)
        new = np.array([x[lab == j].mean(0) if (lab == j).any() else c[j] for j in range(len(c))])
        if np.allclose(new, c):
            break
        c = new
    lab = ((x[:, None, :] - c[None]) ** 2).sum(2).argmin(1)
    return c, lab


def palette(pixels: np.ndarray, top: int = 6) -> tuple:
    """6 largest colour clusters after merging near-duplicates (ΔE76 < 5). Returns (palette, note or None)."""
    if len(pixels) == 0:
        return [], "không có điểm ảnh"
    lab = to_lab(pixels)
    centers, labels = kmeans(lab)
    groups = []
    for j in range(len(centers)):
        m = labels == j
        if m.any():
            groups.append({"n": int(m.sum()), "lab": lab[m].mean(0), "rgb": pixels[m].astype(float).mean(0)})
    merged = True
    while merged and len(groups) > 1:                         # merge the closest pair while ΔE < 5
        merged = False
        best = min(((delta_e(a["lab"], b["lab"]), i, j) for i, a in enumerate(groups)
                    for j, b in enumerate(groups) if i < j), default=None)
        if best and best[0] < 5:
            _, i, j = best
            a, b = groups[i], groups[j]
            n = a["n"] + b["n"]
            groups[i] = {"n": n, "lab": (a["lab"] * a["n"] + b["lab"] * b["n"]) / n,
                         "rgb": (a["rgb"] * a["n"] + b["rgb"] * b["n"]) / n}
            del groups[j]
            merged = True
    groups.sort(key=lambda g: -g["n"])
    total = len(pixels)
    groups = [g for g in groups if g["n"] / total >= NOISE_SHARE]     # compression fringes at colour edges
    out = [{"hex": "#%02x%02x%02x" % tuple(int(round(v)) for v in g["rgb"]),
            "lab": [round(float(v), 2) for v in g["lab"]], "share": round(g["n"] / total, 4)} for g in groups[:top]]
    note = None if len(out) >= top else f"chỉ có {len(out)} màu phân biệt được (ΔE76 ≥ 5)"
    return out, note


def sample_pixels(rgb: np.ndarray, n: int, rng) -> np.ndarray:
    flat = rgb.reshape(-1, 3)
    return flat[rng.integers(0, len(flat), n)]
