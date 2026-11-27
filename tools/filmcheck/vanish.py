"""Vanishing points and horizon from the straight lines of one frame (specs/038 T030, contracts/style-depth.md).

measure(img) -> {"horizon": float|None, "hfov_deg": float|None, "vps": [[x, y], …], "lines": int}
  horizon   height of the main vanishing point, 0 top … 1 bottom (may fall outside 0..1 when the camera tilts)
  hfov_deg  horizontal field of view from two orthogonal vanishing points, else None
  vps       up to two vanishing points, normalised to the frame
  lines     straight segments found; fewer than 20 → every value is None
The numbers are hints for the labeler (cam_height, lens), never a verdict on their own."""
import math
import random

import numpy as np

MIN_LINES = 20


def _load(img):
    import cv2
    if isinstance(img, (str, bytes)) or hasattr(img, "__fspath__"):
        a = cv2.imread(str(img))
        if a is None:
            raise ValueError(f"cannot read {img}")
        return a
    return np.asarray(img)


def _segments(a):
    import cv2
    h, w = a.shape[:2]
    scale = 960.0 / w if w > 960 else 1.0
    if scale != 1.0:
        a = cv2.resize(a, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    g = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY) if a.ndim == 3 else a
    e = cv2.Canny(cv2.GaussianBlur(g, (3, 3), 0), 50, 150)
    m = min(a.shape[:2])
    s = cv2.HoughLinesP(e, 1, np.pi / 180, threshold=40, minLineLength=int(m * 0.06), maxLineGap=int(m * 0.01) + 2)
    segs = [] if s is None else (s.reshape(-1, 4).astype(float) / scale)
    return list(segs)


def _converging(segs):
    """Segments that can point at a vanishing point: not flat, not upright (those meet at infinity in a frontal view)."""
    out = []
    for x1, y1, x2, y2 in segs:
        ang = abs(math.degrees(math.atan2(y2 - y1, x2 - x1))) % 180
        ang = min(ang, 180 - ang)
        if 4 < ang < 86:
            out.append((x1, y1, x2, y2, math.hypot(x2 - x1, y2 - y1)))
    return out


def _line(s):
    x1, y1, x2, y2 = s[:4]
    a, b = y2 - y1, x1 - x2
    n = math.hypot(a, b) or 1.0
    return a / n, b / n, -(a * x1 + b * y1) / n


def _meet(l1, l2):
    a1, b1, c1 = l1
    a2, b2, c2 = l2
    d = a1 * b2 - a2 * b1
    if abs(d) < 1e-6:
        return None
    return ((b1 * c2 - b2 * c1) / d, (a2 * c1 - a1 * c2) / d)


def _vote(segs, lines, w, h, tol, rng):
    """The point most segment lines pass close to, by length-weighted votes over sampled intersections."""
    n = len(segs)
    best, score, inl = None, 0.0, []
    tries = min(600, n * (n - 1) // 2)
    for _ in range(tries):
        i, j = rng.sample(range(n), 2)
        p = _meet(lines[i], lines[j])
        if p is None or not (-2 * w < p[0] < 3 * w and -2 * h < p[1] < 3 * h):
            continue
        sc, ids = 0.0, []
        for k, (a, b, c) in enumerate(lines):
            if abs(a * p[0] + b * p[1] + c) < tol:
                sc += segs[k][4]
                ids.append(k)
        if sc > score:
            best, score, inl = p, sc, ids
    if best is None or len(inl) < 6:
        return None, []
    pts = np.array([[lines[k][0], lines[k][1]] for k in inl])          # least squares refine on the inliers
    cs = np.array([-lines[k][2] for k in inl])
    wts = np.array([segs[k][4] for k in inl])
    try:
        sol, *_ = np.linalg.lstsq(pts * wts[:, None], cs * wts, rcond=None)
        best = (float(sol[0]), float(sol[1]))
    except np.linalg.LinAlgError:
        pass
    return best, inl


def measure(img, seed: int = 7) -> dict:
    a = _load(img)
    h, w = a.shape[:2]
    segs = _segments(a)
    out = {"horizon": None, "hfov_deg": None, "vps": [], "lines": len(segs)}
    if len(segs) < MIN_LINES:
        return out
    conv = _converging(segs)
    if len(conv) < 6:
        return out
    rng = random.Random(seed)
    tol = 0.01 * math.hypot(w, h)
    lines = [_line(s) for s in conv]
    vps = []
    v1, inl = _vote(conv, lines, w, h, tol, rng)
    if v1 is None:
        return out
    vps.append(v1)
    rest = [k for k in range(len(conv)) if k not in set(inl)]
    if len(rest) >= 6:
        v2, inl2 = _vote([conv[k] for k in rest], [lines[k] for k in rest], w, h, tol, rng)
        if v2 is not None and len(inl2) >= max(6, len(inl) // 4) and math.dist(v1, v2) > 0.2 * w:
            vps.append(v2)
    main = vps[0]                                          # the most supported one
    out["horizon"] = round(main[1] / h, 3)
    out["vps"] = [[round(x / w, 3), round(y / h, 3)] for x, y in vps]
    if len(vps) == 2:                                      # two orthogonal directions → focal length → field of view
        cx, cy = w / 2, h / 2
        d = -((vps[0][0] - cx) * (vps[1][0] - cx) + (vps[0][1] - cy) * (vps[1][1] - cy))
        if d > 0:
            f = math.sqrt(d)
            out["hfov_deg"] = round(math.degrees(2 * math.atan(w / 2 / f)), 1)
    return out
