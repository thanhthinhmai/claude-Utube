"""Camera path of one shot (specs/039 research R1): total 2D zoom, ease, drift and parallax.

One measure for the reference (learn camera) and for the studio's own films (qc camera), so both compare (FR-005).
The same method as the hand measure of charisma-30 (out/measure/deep.py), which the user checked shot by shot:

1. Frame to frame (30 frames/s, grey 640×360): corners (goodFeaturesToTrack) followed by pyramidal Lucas–Kanade, a
   similarity (zoom, turn, shift) fitted with RANSAC. Block matching (craft.py) was tried first and failed on cartoon
   frames (flat colours, moving characters): zoom off by up to 6 points on charisma-ref (checks/sc001.md).
2. The frame maps are chained: T maps frame 0 onto the last frame.
     zoom_pct   (scale of T − 1)·100, negative = zooming out
     drift_px   how far the camera window moved on screen at 1080p ([x, y], + = right/down): −(T·c − c)·3
     ease       share of the move done at ¼, ½, ¾ of the measured span (log zoom when zooming, else drift)
3. Parallax: corners of the first frame are followed through the whole shot. One similarity is fitted to where they
   start and end (RANSAC, 1 px at 360 high); a second one to the points the first leaves out. When the second fits at
   least PAR_MIN_POINTS points and PAR_MIN_SHARE of them, and lands more than PARALLAX_PX (1080p) away from the first
   at those points, two layers moved apart: a camera that really moves. A 2D zoom has one layer. A second "layer" fixed
   on screen is an overlay (sponsor card, logo), and one narrower than PAR_MIN_SPAN of the frame is a character moving
   as a block (charisma-ref S044/S045/S086); neither counts.
At a shot end only a frame or so is left out after a straight cut, the whole transition after a soft one (learn
camera knows both); without them craft.EDGE_TRIM is left out at each end."""
import numpy as np

from sl import craft

FPS = 30
RW, RH = 640, 360
TO_1080 = 1080 / RH
STILL_ZOOM = 0.5                  # |zoom| below this (%) and
STILL_DRIFT = 4.0                 # drift below this (px at 1080p) is a still camera
PAN_MIN = 4.0
RANSAC_PX = 1.0                   # px at 640×360
PAR_MIN_POINTS = 12
PAR_MIN_SHARE = 0.25
PAR_MIN_SPAN = 0.4                # the second layer spans at least this share of the frame width
# T005 calibration (2026-11-27, checks/sc001.md): charisma-ref, 89 shots of 2D zoom/pan, largest leftover 8.6 px
# (S027, a 0.8 s pan) and 5.7 px (S041); the synthetic two-layer shot (near layer ×2 zoom, ×3 drift) 15 px. The
# Blender tests on disk (s68) used a lens zoom, so they have no parallax (0.0). Threshold between the groups:
PARALLAX_PX = 10.0
MIN_DUR = 1.0
MIN_INLIERS = 12


class TrackError(Exception):
    pass


def _cv():
    try:
        import cv2
    except ImportError:
        raise TrackError("cần OpenCV: sh bin/studio deps learn") from None
    return cv2


def _corners(cv2, g):
    p = cv2.goodFeaturesToTrack(g, 600, 0.01, 8)
    return None if p is None else p.astype(np.float32)


def _pair(cv2, a, b):
    """3×3 similarity mapping frame a onto frame b, and its inlier count (None, 0 when it cannot be fitted)."""
    p0 = _corners(cv2, a)
    if p0 is None or len(p0) < 12:
        return None, 0
    p1, st, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None, winSize=(21, 21), maxLevel=3)
    ok = st.ravel() == 1
    if ok.sum() < 12:
        return None, 0
    M, inl = cv2.estimateAffinePartial2D(p0[ok], p1[ok], method=cv2.RANSAC, ransacReprojThreshold=RANSAC_PX,
                                         maxIters=4000)
    if M is None:
        return None, 0
    return np.vstack([M, [0, 0, 1]]), int(inl.sum())


def _scale(T) -> float:
    return float(np.hypot(T[0, 0], T[1, 0]))


def _parallax(cv2, frames) -> float:
    """px at 1080p between two layers that each move rigidly, or 0.0 (see the module note)."""
    p0 = _corners(cv2, frames[0])
    if p0 is None or len(p0) < 2 * PAR_MIN_POINTS:
        return 0.0
    cur, alive = p0.copy(), np.ones(len(p0), bool)
    for a, b in zip(frames[:-1], frames[1:]):
        nxt, st, _ = cv2.calcOpticalFlowPyrLK(a, b, cur, None, winSize=(21, 21), maxLevel=3)
        alive &= st.ravel() == 1
        cur = nxt
    s, e = p0[alive].reshape(-1, 2), cur[alive].reshape(-1, 2)
    if len(s) < 2 * PAR_MIN_POINTS:
        return 0.0
    M1, in1 = cv2.estimateAffinePartial2D(s, e, method=cv2.RANSAC, ransacReprojThreshold=RANSAC_PX, maxIters=4000)
    if M1 is None:
        return 0.0
    out = in1.ravel() == 0
    if out.sum() < PAR_MIN_POINTS:
        return 0.0
    M2, in2 = cv2.estimateAffinePartial2D(s[out], e[out], method=cv2.RANSAC, ransacReprojThreshold=RANSAC_PX,
                                          maxIters=4000)
    if M2 is None:
        return 0.0
    k = in2.ravel() == 1
    if k.sum() < PAR_MIN_POINTS or k.sum() < PAR_MIN_SHARE * len(s):
        return 0.0
    pts = s[out][k]
    if abs(np.hypot(M2[0, 0], M2[1, 0]) - 1) < 0.002 and abs(M2[0, 1]) < 0.002 and np.hypot(*M2[:, 2]) < 0.5:
        return 0.0                                     # fixed on screen: an overlay (logo, card), not a layer of the set
    x = pts[:, 0]
    if np.percentile(x, 95) - np.percentile(x, 5) < PAR_MIN_SPAN * RW:
        return 0.0                                     # narrow: a character moving as a block, not a layer of the set
    d = (pts @ M2[:, :2].T + M2[:, 2]) - (pts @ M1[:, :2].T + M1[:, 2])
    return float(np.median(np.hypot(d[:, 0], d[:, 1]))) * TO_1080


def _quartiles(curve):
    n = len(curve) - 1
    if n < 2:
        return None
    t = np.linspace(0, 1, n + 1)
    return [round(float(np.interp(q, t, curve)), 3) for q in (0.25, 0.5, 0.75)]


def track(frames) -> dict:
    """frames: grey uint8 (n, 360, 640) at FPS."""
    cv2 = _cv()
    c = np.array([RW / 2, RH / 2, 1.0])
    T = np.eye(3)
    logz, shift, inl = [0.0], [np.zeros(2)], []
    for a, b in zip(frames[:-1], frames[1:]):
        M, k = _pair(cv2, a, b)
        inl.append(k)
        if M is not None:
            T = M @ T
        logz.append(np.log(_scale(T)))
        shift.append((T @ c)[:2] - c[:2])
    zoom = (_scale(T) - 1) * 100
    drift = [-float(shift[-1][0]) * TO_1080, -float(shift[-1][1]) * TO_1080]
    mag = float(np.hypot(*drift))
    ease = None
    if abs(zoom) >= STILL_ZOOM:
        move = "push" if zoom > 0 else "pull"
        lz = np.array(logz)
        ease = _quartiles(np.clip(lz / lz[-1], -0.5, 1.5))
    elif mag >= max(STILL_DRIFT, PAN_MIN):
        move = "pan"
        u = shift[-1] / (np.hypot(*shift[-1]) or 1)
        proj = np.array([sh @ u for sh in shift])
        ease = _quartiles(np.clip(proj / proj[-1], -0.5, 1.5)) if abs(proj[-1]) > 1e-6 else None
    else:
        move = "static"
    par = round(_parallax(cv2, frames), 2)
    return {"move": move, "zoom_pct": round(zoom, 2), "drift_px": [round(drift[0], 1), round(drift[1], 1)],
            "ease": ease, "parallax_px": par, "parallax": par > PARALLAX_PX,
            "inliers": int(np.median(inl)) if inl else 0}


def frames_of(path, a: float, b: float):
    f = craft.sample(path, a, b, fps=FPS, size=(RW, RH))
    return f.astype(np.uint8)


CUT_TRIM = 0.05                   # s left out at a straight cut (the cut may be a frame off)


def trim_for(trans: dict) -> float:
    """Seconds to leave out at a shot end: a frame or so at a straight cut, the whole transition otherwise."""
    if not trans or trans.get("type") in (None, "cut"):
        return CUT_TRIM
    return max(craft.EDGE_TRIM, float(trans.get("dur") or 0) / 2 + CUT_TRIM)


def measure(path, t0: float, t1: float, trim_in: float = None, trim_out: float = None) -> dict:
    """The camera of [t0, t1] of a video: track() plus duration, rate and reliability. Without trims, craft.EDGE_TRIM
    is left out at each end (the transitions are unknown)."""
    t0, t1 = float(t0), float(t1)
    dur = t1 - t0
    a = t0 + (craft.EDGE_TRIM if trim_in is None else trim_in)
    b = t1 - (craft.EDGE_TRIM if trim_out is None else trim_out)
    if b - a < 3 / FPS:
        a, b = t0, t1
    fr = frames_of(path, a, b)
    if len(fr) < 2:
        raise TrackError(f"too few frames in {t0:.2f}–{t1:.2f}")
    out = track(fr)
    span = max(1e-6, (len(fr) - 1) / FPS)
    out["dur"] = round(dur, 3)
    out["rate_pct_s"] = round(out["zoom_pct"] / span, 3)
    why = None
    if dur < MIN_DUR:
        why = f"shorter than {MIN_DUR:.0f} s"
    elif out["inliers"] < MIN_INLIERS:
        why = "too few corners fit the camera"
    elif _flash(fr):
        why = "flash or cut inside the shot"
    out["reliable"] = why is None
    out["why_unreliable"] = why
    return out


def _flash(fr) -> bool:
    m = fr.reshape(len(fr), -1).mean(1)
    return bool(len(m) > 2 and np.max(np.abs(np.diff(m))) > 40)
