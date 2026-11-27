"""Camera path of one shot (specs/039 research R1): total 2D zoom, ease, drift and parallax.

One measure for the reference (learn camera) and for the studio's own films (qc camera), so both compare (FR-005).

1. Chain: craft.pairs() gives a camera model (dx, dy, z) per sampled pair (12 frames/s, 320×180): content at x (from
   the frame centre) in frame k is found at (1+z)·x + d in frame k+1. Chaining the pairs maps frame 0 onto frame k:
   x_k = A_k·x_0 + B_k, with A the scale and B the content shift at the centre.
2. Refine: the chained map of the whole shot drifts by about 0.1 %/s, so the first and last frames are matched
   directly at 640×360, starting from the chained map (craft.warp + block_shifts ±2 + fit_camera, up to 3 rounds).
3. Numbers:
     zoom_pct   (A − 1)·100, negative = zooming out
     drift_px   how far the camera window moved on screen at 1080p ([x, y], + = right/down): −B·(1080/360)
     ease       share of the move done at ¼, ½, ¾ of the measured span (log A when zooming, else drift along B)
     parallax   after the refined fit, p75 of the leftover shift of textured blocks (a block that does not fit within
                ±PARALLAX_SEARCH counts as PARALLAX_SEARCH+1), in px at 1080p. A camera that really moves leaves the
                near and far layers apart; a 2D zoom leaves almost nothing.
The edges of a shot (craft.EDGE_TRIM each side) are left out, as in craft: transitions live there.

PARALLAX_PX: set in T005 from two groups (see the note at the constant)."""
import numpy as np

from sl import craft

FPS = craft.FPS
RW, RH = 640, 360                 # refine size
TO_1080 = 1080 / RH
STILL_ZOOM = 0.5                  # |zoom| below this (%) and
STILL_DRIFT = 4.0                 # drift below this (px at 1080p) is a still camera
PAN_MIN = 4.0
PARALLAX_SEARCH = 4               # px at 640 for the leftover pass
# T005 calibration (2026-11-27): see specs/039-camera-review/checks/sc001.md. Starting value 6 px at 1080p
# (2 px at 360 high), between the 2D-zoom group and the moving-camera group.
PARALLAX_PX = 6.0
MIN_DUR = 1.0
MIN_INLIERS = 6


class TrackError(Exception):
    pass


def _chain(ps):
    """[(A, Bx, By)] for k = 0..n (frame k relative to frame 0), at sample size (320×180)."""
    A, bx, by = 1.0, 0.0, 0.0
    out = [(A, bx, by)]
    for p in ps:
        dx, dy, z = p["model"]
        A, bx, by = A * (1 + z), bx * (1 + z) + dx, by * (1 + z) + dy
        out.append((A, bx, by))
    return out


def _refine(a, b, A, bx, by, rounds=4):
    """Fit the map a → b at refine size, starting from (A, bx, by); returns (A, bx, by, inliers, leftover px)."""
    dx, dy, z = bx, by, A - 1
    inl = 0
    for r in range(rounds):
        w = craft.warp(b, dx, dy, z)
        gx, gy = craft.global_shift(a, w) if r == 0 else (0, 0)   # the chain leans to whole px: catch what it missed
        sx, sy, valid = craft.block_shifts(a, np.roll(w, (-gy, -gx), axis=(0, 1)) if (gx or gy) else w,
                                           search=craft.SEARCH if r == 0 else 2)
        sx, sy = sx + gx, sy + gy
        ex, ey, ez, keep = craft.fit_camera(sx, sy, valid, a.shape)
        inl = int(keep.sum())
        # the warp samples b at x + s(x); a residual shift r at x adds to s: compose to first order
        dx, dy, z = dx + ex * (1 + z), dy + ey * (1 + z), z + ez * (1 + z)
        if abs(ex) < 0.02 and abs(ey) < 0.02 and abs(ez) * RW / 2 < 0.02:
            break
    # leftover shifts after the final fit, for parallax
    w = craft.warp(b, dx, dy, z)
    S = PARALLAX_SEARCH
    sx, sy, valid = craft.block_shifts(a, w, search=S)
    h, wd = a.shape
    nby, nbx, _ = craft._grid(h, wd)
    tex = a[:nby * craft.BLOCK, :nbx * craft.BLOCK].reshape(nby, craft.BLOCK, nbx, craft.BLOCK).std((1, 3)) > 3.0
    tex[0, :] = tex[-1, :] = False                     # the outer ring sees new picture coming in at a zoom
    tex[:, 0] = tex[:, -1] = False
    left = np.where(valid, np.hypot(sx, sy), S + 1.0)[tex]
    leftover = float(np.percentile(left, 75)) if left.size >= 6 else 0.0
    return 1 + z, dx, dy, inl, leftover


def _quartiles(curve):
    """curve: progress values 0..1 at evenly spaced samples → value at ¼, ½, ¾."""
    n = len(curve) - 1
    if n < 2:
        return None
    t = np.linspace(0, 1, n + 1)
    return [round(float(np.interp(q, t, curve)), 3) for q in (0.25, 0.5, 0.75)]


def track(frames, first, last) -> dict:
    """frames: grey samples at craft size; first/last: grey frames at refine size (the span's ends)."""
    ps = craft.pairs(frames) if len(frames) >= 2 else []
    ch = _chain(ps)
    A, bx, by = ch[-1]
    k = RW / craft.SW                                  # chained shift is at 320 wide → refine size
    A2, bx2, by2, inl, leftover = _refine(first, last, A, bx * k, by * k)
    zoom = (A2 - 1) * 100
    drift = [-bx2 * TO_1080, -by2 * TO_1080]
    mag = float(np.hypot(*drift))
    if abs(zoom) < STILL_ZOOM and mag < STILL_DRIFT:
        move, ease = "static", None
    else:
        if abs(zoom) >= STILL_ZOOM:
            move = "push" if zoom > 0 else "pull"
            la = np.log([c[0] for c in ch])
            curve = la / la[-1] if abs(la[-1]) > 1e-6 else None
        else:
            move = "pan" if mag >= PAN_MIN else "static"
            u = np.array([bx, by]) / (np.hypot(bx, by) or 1)
            proj = np.array([c[1] * u[0] + c[2] * u[1] for c in ch])
            curve = proj / proj[-1] if abs(proj[-1]) > 1e-6 else None
        ease = _quartiles(np.clip(curve, -0.5, 1.5)) if curve is not None else None
    par_px = round(leftover * TO_1080, 2)
    return {"move": move, "zoom_pct": round(zoom, 2), "drift_px": [round(drift[0], 1), round(drift[1], 1)],
            "ease": ease, "parallax_px": par_px, "parallax": par_px > PARALLAX_PX, "inliers": inl}


def measure(path, t0: float, t1: float) -> dict:
    """The camera of [t0, t1] of a video: track() plus duration, rate and reliability."""
    t0, t1 = float(t0), float(t1)
    dur = t1 - t0
    a, b = t0 + craft.EDGE_TRIM, t1 - craft.EDGE_TRIM
    if b - a < 3 / FPS:
        a, b = t0, t1
    frames = craft.sample(path, a, b)
    ends = craft.sample(path, a, b, fps=FPS, size=(RW, RH))
    if len(frames) < 2 or len(ends) < 2:
        raise TrackError(f"too few frames in {t0:.2f}–{t1:.2f}")
    out = track(frames, ends[0], ends[-1])
    span = max(1e-6, (len(ends) - 1) / FPS)
    out["dur"] = round(dur, 3)
    out["rate_pct_s"] = round(out["zoom_pct"] / span, 3)
    why = None
    if dur < MIN_DUR:
        why = f"shorter than {MIN_DUR:.0f} s"
    elif out["inliers"] < MIN_INLIERS:
        why = "too few blocks fit the camera"
    elif _flash(ends):
        why = "flash or cut inside the shot"
    out["reliable"] = why is None
    out["why_unreliable"] = why
    return out


def _flash(ends) -> bool:
    m = ends.reshape(len(ends), -1).mean(1)
    return bool(len(m) > 2 and np.max(np.abs(np.diff(m))) > 40)
