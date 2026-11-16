"""Craft measures in time (specs/023 research R2, R3): camera move, movement inside the shot, transition into it.

One measure for learning (learn craft) and for the studio's checks (tools/filmcheck/motioncheck.py), so both read the
same numbers. Pure numpy; frames come from ffmpeg.

Camera: every sampled pair (12 frames/s, 320×180 grey) is split into 16×16 blocks; each block finds its shift by the
smallest sum of absolute differences within ±SEARCH px (sub-pixel by a parabola). A camera model (shift x, shift y,
zoom about the centre) is fitted by least squares with outliers dropped twice.
Inside the shot: the second frame is warped back by the camera model; blocks still differing by more than the shot's
noise (median + 4·1.4826·MAD, at least NOISE_MIN grey levels) are movement. Speeds are px/s at 1280 wide.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

FPS = 12
SW, SH = 320, 180
BLOCK = 16
SEARCH = 6
NOISE_MIN = 3.0
ACTIVE_BLOCKS = 2            # a sampled pair has movement when at least this many blocks move
STILL_PX_S = 4.0             # camera slower than this (px/s at 1280) and
STILL_ZOOM = 0.5             # zooming less than this (%/s) is still
EDGE_TRIM = 0.15             # seconds left out at each end of a shot (transitions live there)
TO_1280 = 1280 / SW


class CraftError(Exception):
    pass


# ---------------------------------------------------------------- frames

def _ffmpeg(args, w, h, ch):
    cmd = ["ffmpeg", "-v", "error", "-nostdin"] + args
    try:
        out = subprocess.run(cmd, capture_output=True, check=True).stdout
    except FileNotFoundError:
        raise CraftError("cần ffmpeg") from None
    except subprocess.CalledProcessError as e:
        raise CraftError("ffmpeg: " + e.stderr.decode(errors="replace").strip()[:200]) from None
    n = len(out) // (w * h * ch)
    a = np.frombuffer(out[:n * w * h * ch], np.uint8).reshape(n, h, w, ch) if ch > 1 else \
        np.frombuffer(out[:n * w * h], np.uint8).reshape(n, h, w)
    return a.astype(np.float32)


def sample(path, t0, t1, fps=FPS, size=(SW, SH)):
    """Grey frames of [t0, t1) at fps, as float32 (n, h, w); frame k is at t0 + k/fps."""
    w, h = size
    return _ffmpeg(["-ss", f"{max(0.0, t0):.3f}", "-t", f"{max(0.0, t1 - t0):.3f}", "-i", str(path),
                    "-vf", f"fps={fps},scale={w}:{h}:flags=area,format=gray", "-f", "rawvideo", "-"], w, h, 1)


def native(path, t0, t1, size=(160, 90)):
    """RGB frames of [t0, t1) at the video's own rate (for transitions), float32 0–1, and that rate."""
    w, h = size
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=avg_frame_rate",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout.strip()
    num, _, den = r.partition("/")
    fps = float(num) / float(den or 1) if num else 30.0
    f = _ffmpeg(["-ss", f"{max(0.0, t0):.3f}", "-t", f"{max(0.0, t1 - t0):.3f}", "-i", str(path),
                 "-vf", f"scale={w}:{h}:flags=area,format=rgb24", "-f", "rawvideo", "-"], w, h, 3)
    return f / 255.0, fps


def load_images(paths, size=(SW, SH)):
    from PIL import Image
    return np.stack([np.asarray(Image.open(p).convert("L").resize(size, Image.BILINEAR), np.float32) for p in paths])


# ---------------------------------------------------------------- camera

def _grid(h, w):
    nby, nbx = h // BLOCK, w // BLOCK
    ys = (np.arange(nby) + 0.5) * BLOCK - h / 2
    xs = (np.arange(nbx) + 0.5) * BLOCK - w / 2
    return nby, nbx, np.meshgrid(xs, ys)


def block_shifts(a, b, search=SEARCH):
    """Per block: (sx, sy, valid). Content at x in a is found at x + s in b."""
    h, w = a.shape
    nby, nbx, _ = _grid(h, w)
    hh, ww = nby * BLOCK, nbx * BLOCK
    A = a[:hh, :ww]
    bp = np.pad(b, search, mode="edge")
    offs = [(oy, ox) for oy in range(-search, search + 1) for ox in range(-search, search + 1)]
    sad = np.empty((len(offs), nby, nbx), np.float32)
    for i, (oy, ox) in enumerate(offs):
        B = bp[search + oy:search + oy + hh, search + ox:search + ox + ww]
        sad[i] = np.abs(A - B).reshape(nby, BLOCK, nbx, BLOCK).sum((1, 3))
    n = 2 * search + 1
    cube = sad.reshape(n, n, nby, nbx)
    best = sad.argmin(0)
    by, bx = np.divmod(best, n)

    def sub(c, l, r):
        d = l - 2 * c + r
        return np.where(d > 1e-6, 0.5 * (l - r) / np.maximum(d, 1e-6), 0.0)

    iy, ix = np.indices((nby, nbx))
    c = cube[by, bx, iy, ix]
    l = cube[np.clip(by, 0, n - 1), np.clip(bx - 1, 0, n - 1), iy, ix]
    r = cube[np.clip(by, 0, n - 1), np.clip(bx + 1, 0, n - 1), iy, ix]
    u = cube[np.clip(by - 1, 0, n - 1), np.clip(bx, 0, n - 1), iy, ix]
    d = cube[np.clip(by + 1, 0, n - 1), np.clip(bx, 0, n - 1), iy, ix]
    sx = bx - search + np.where((bx > 0) & (bx < n - 1), sub(c, l, r), 0)
    sy = by - search + np.where((by > 0) & (by < n - 1), sub(c, u, d), 0)
    std = A.reshape(nby, BLOCK, nbx, BLOCK).std((1, 3))
    valid = (std > 3.0) & (c < 0.7 * np.median(sad, 0)) & (bx > 0) & (bx < n - 1) & (by > 0) & (by < n - 1)
    return sx, sy, valid


def fit_camera(sx, sy, valid, shape):
    """(dx, dy, zoom, inliers): s(x, y) = (dx + zoom·x, dy + zoom·y) about the frame centre."""
    h, w = shape
    _, _, (X, Y) = _grid(h, w)
    keep = valid.copy()
    dx = dy = z = 0.0
    for _ in range(3):
        if keep.sum() < 6:
            return 0.0, 0.0, 0.0, keep
        x, y, u, v = X[keep], Y[keep], sx[keep], sy[keep]
        M = np.zeros((2 * len(x), 3))
        M[0::2, 0], M[1::2, 1] = 1, 1
        M[0::2, 2], M[1::2, 2] = x, y
        rhs = np.empty(2 * len(x))
        rhs[0::2], rhs[1::2] = u, v
        dx, dy, z = np.linalg.lstsq(M, rhs, rcond=None)[0]
        res = np.hypot(sx - (dx + z * X), sy - (dy + z * Y))
        keep = valid & (res < max(0.6, 3 * np.median(res[keep])))
    return float(dx), float(dy), float(z), keep


def warp(b, dx, dy, z):
    """b sampled at x + s(x): brings b back onto a under the camera model."""
    h, w = b.shape
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w / 2, h / 2
    X = xs + dx + z * (xs + 0.5 - cx)
    Y = ys + dy + z * (ys + 0.5 - cy)
    X, Y = np.clip(X, 0, w - 1.001), np.clip(Y, 0, h - 1.001)
    x0, y0 = X.astype(int), Y.astype(int)
    fx, fy = X - x0, Y - y0
    return (b[y0, x0] * (1 - fx) + b[y0, x0 + 1] * fx) * (1 - fy) + (b[y0 + 1, x0] * (1 - fx) + b[y0 + 1, x0 + 1] * fx) * fy


def block_diffs(a, b, model):
    """Mean |a − warp(b)| per inner block (the outer ring of blocks is left out: the warp is unsure there)."""
    dx, dy, z = model
    h, w = a.shape
    nby, nbx, _ = _grid(h, w)
    d = np.abs(a - warp(b, dx, dy, z))[:nby * BLOCK, :nbx * BLOCK]
    return d.reshape(nby, BLOCK, nbx, BLOCK).mean((1, 3))[1:-1, 1:-1]


# ---------------------------------------------------------------- one shot

def pairs(frames):
    """Per sampled pair: camera model, block diffs, and the median own shift of blocks that do not follow the camera."""
    out = []
    for a, b in zip(frames[:-1], frames[1:]):
        sx, sy, valid = block_shifts(a, b)
        dx, dy, z, inl = fit_camera(sx, sy, valid, a.shape)
        if abs(z) * a.shape[1] / 2 > 0.15:          # zooming: match again on the warped frame (block matching leans to whole px)
            rx, ry, rv = block_shifts(a, warp(b, dx, dy, z), search=2)
            ex, ey, ez, inl2 = fit_camera(rx, ry, rv, a.shape)
            dx, dy, z = dx + ex, dy + ey, z + ez
        out_blocks = valid & ~inl
        own = float(np.median(np.hypot(sx[out_blocks], sy[out_blocks]))) if out_blocks.sum() >= 2 else None
        out.append({"model": (dx, dy, z), "diff": block_diffs(a, b, (dx, dy, z)), "own": own, "n_out": int(out_blocks.sum())})
    return out


def noise_of(ps):
    allv = np.concatenate([p["diff"].ravel() for p in ps]) if ps else np.zeros(1)
    med = float(np.median(allv))
    mad = float(np.median(np.abs(allv - med)))
    return max(NOISE_MIN, med + 4 * 1.4826 * mad)


def classify_cam(ps, fps=FPS):
    if not ps:
        return {"type": "still", "px_s": 0.0, "zoom_pct_s": 0.0, "ease_in_s": None, "ease_out_s": None}
    m = np.array([p["model"] for p in ps])
    vx, vy, z = (float(np.median(m[:, i])) for i in range(3))
    px_s = float(np.hypot(vx, vy) * fps * TO_1280)
    zoom = float(z * fps * 100)
    edge_px_s = abs(zoom) * 6.4                  # %/s of zoom → px/s at the left/right edge of a 1280 frame
    if px_s < STILL_PX_S and abs(zoom) < STILL_ZOOM:
        kind = "still"
    elif abs(zoom) >= STILL_ZOOM and edge_px_s >= px_s:
        kind = "push" if zoom > 0 else "pull"
    else:
        kind = "drift-h" if abs(vx) >= abs(vy) else "drift-v"
    ease_in = ease_out = None
    if kind != "still":
        sp = np.hypot(m[:, 0], m[:, 1]) * fps * TO_1280 + np.abs(m[:, 2]) * fps * 100 * 6.4
        target = 0.8 * float(np.median(sp))
        above = np.nonzero(sp >= target)[0]
        if len(above):
            ease_in, ease_out = round(above[0] / fps, 3), round((len(sp) - 1 - above[-1]) / fps, 3)
    return {"type": kind, "px_s": round(px_s, 2), "zoom_pct_s": round(zoom, 3), "ease_in_s": ease_in, "ease_out_s": ease_out}


def inner(ps, t0, noise, fps=FPS):
    """Movement inside the shot: active share, peak share, spans [t0, t1, mean share, [x, y]], their durations."""
    if not ps:
        return {"active_share": 0.0, "peak": 0.0, "spans": [], "rise_s": []}
    shares, active, centres = [], [], []
    for p in ps:
        mov = p["diff"] > noise
        shares.append(float(mov.mean()))
        active.append(int(mov.sum()) >= ACTIVE_BLOCKS)
        if mov.any():
            yy, xx = np.nonzero(mov)
            centres.append(((xx.mean() + 1.5) / (mov.shape[1] + 2), (yy.mean() + 1.5) / (mov.shape[0] + 2)))
        else:
            centres.append(None)
    spans, i = [], 0
    while i < len(active):
        if not active[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(active) and (active[j + 1] or (j + 2 < len(active) and active[j + 2])):
            j += 1                                     # a single quiet sample inside movement does not split it
        if j - i + 1 >= 2:
            cs = [c for c in centres[i:j + 1] if c]
            spans.append([round(t0 + i / fps, 3), round(t0 + (j + 1) / fps, 3), round(float(np.mean(shares[i:j + 1])), 4),
                          [round(float(np.mean([c[0] for c in cs])), 3), round(float(np.mean([c[1] for c in cs])), 3)]])
        i = j + 1
    return {"active_share": round(float(np.mean([s[1] - s[0] for s in spans]) * len(spans) / (len(ps) / fps)), 4) if spans else 0.0,
            "peak": round(max(shares), 4), "spans": spans, "rise_s": [round(s[1] - s[0], 3) for s in spans]}


def follow(cam, ps, inn):
    """The camera moves with a subject: movement in most of the shot while the camera drifts, or in most pairs a group
    of blocks stays put on screen while the rest slides."""
    if cam["type"] not in ("drift-h", "drift-v") or not ps:
        return False
    if inn["active_share"] >= 0.6:
        return True
    sp = cam["px_s"] / (FPS * TO_1280)               # px per sample at 320
    hits = sum(1 for p in ps if p["n_out"] >= ACTIVE_BLOCKS and p["own"] is not None and p["own"] < 0.4 * sp)
    return hits >= 0.5 * len(ps)


def measure_frames(frames, t0=0.0, fps=FPS):
    ps = pairs(frames)
    noise = noise_of(ps)
    cam = classify_cam(ps, fps)
    inn = inner(ps, t0, noise, fps)
    if follow(cam, ps, inn):
        cam["type"] = "follow"
    return {"cam": cam, "inner": inn, "noise": round(noise, 3)}


def measure_shot(path, shot):
    """One shots[] element of craft.json for a shot {id, t0, t1} of a video."""
    t0, t1 = float(shot["t0"]), float(shot["t1"])
    a, b = t0 + EDGE_TRIM, t1 - EDGE_TRIM
    if b - a < 3 / FPS:
        a, b = t0, t1
    frames = sample(path, a, b)
    m = measure_frames(frames, a)
    out = {"id": shot.get("id"), "t0": t0, "t1": t1, "cam": m["cam"], "inner": m["inner"], "noise": m["noise"]}
    if t0 > 0:
        out["trans_in"] = transition(path, t0)
    return out


# ---------------------------------------------------------------- transitions (R3)

def _luma(f):
    return f @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def transition(path, t_cut, half=0.35):
    """Kind and length of the transition at a cut: streak, fade, dip, flash, wipe, dissolve, or cut."""
    fr, fps = native(path, t_cut - half, t_cut + half)
    if len(fr) < 4:
        return {"type": "cut", "dur": 0.0}
    g = _luma(fr)                                  # (n, h, w)
    lum = g.mean((1, 2))
    A, B = g[0], g[-1]

    def bright_band(x):
        rows = x.mean(1)
        flat = x.std(1) < 0.08
        return float(((rows > 0.8) & flat).mean())
    base_band = max(bright_band(A), bright_band(B))
    streak = [i for i in range(len(g)) if bright_band(g[i]) >= 0.15 + base_band]
    if streak and 0.06 <= len(streak) / fps <= 0.3:
        return {"type": "streak", "dur": round(len(streak) / fps, 3)}
    ref = min(lum[0], lum[-1])
    m = int(lum.argmin())
    if lum[m] < 0.06 and ref > 0.12:
        lo = m
        while lo > 0 and lum[lo - 1] < 0.85 * lum[0]:
            lo -= 1
        hi = m
        while hi < len(lum) - 1 and lum[hi + 1] < 0.85 * lum[-1]:
            hi += 1
        black = int((lum < 0.03).sum())
        fall = (m - lo) / fps
        ramp = fall + (hi - m) / fps - black / fps
        if ramp >= 0.1:
            return {"type": "fade", "dur": round((hi - lo + 1) / fps, 3)}
        if black >= 2:
            return {"type": "dip", "dur": round(black / fps, 3)}
    if any(lum[i] > 0.9 and lum[i] - ref > 0.3 for i in range(1, len(lum) - 1)):
        return {"type": "flash", "dur": round(int((lum > 0.9).sum()) / fps, 3)}
    span = float(np.abs(A - B).mean())
    steps = np.abs(np.diff(g, axis=0)).mean((1, 2))
    if span > 0.02 and steps.max() >= 0.6 * span:   # one frame-to-frame jump carries the change: a hard cut
        return {"type": "cut", "dur": 0.0}
    dAf, dBf = np.abs(g - A).mean((1, 2)), np.abs(g - B).mean((1, 2))
    between = int(((dAf > 0.2 * span) & (dBf > 0.2 * span)).sum())   # frames that are neither the shot before nor after
    best = None
    for axis in (0, 1):                            # columns, then rows
        dA = np.abs(g - A).mean(1 + axis)          # (n, w) or (n, h)
        dB = np.abs(g - B).mean(1 + axis)
        span = float(np.abs(A - B).mean())
        if span < 0.04:
            return {"type": "cut", "dur": 0.0}
        after = dA < 0.5 * dB
        before = dB < 0.5 * dA
        mixed = ~(after | before) & (np.maximum(dA, dB) > 0.3 * span)
        mid = [i for i in range(len(g)) if 0.05 < after[i].mean() < 0.95 or mixed[i].mean() > 0.3]
        if len(mid) >= 3:
            mix = float(np.mean([mixed[i].mean() for i in mid]))
            runs = all(np.count_nonzero(np.diff(after[i].astype(int))) <= 2 for i in mid)
            kind = "wipe" if mix < 0.3 and runs else "dissolve"
            cand = (mix, {"type": kind, "dur": round(max(len(mid), between) / fps, 3)})
            if best is None or cand[0] < best[0]:
                best = cand
    return best[1] if best else {"type": "cut", "dur": 0.0}


# ---------------------------------------------------------------- command line (used by tools/filmcheck/motioncheck.py)

def main(argv):
    """python -m sl.craft frames <img…>       → {"cam", "inner", "noise"} for frames taken in order at 12/s
       python -m sl.craft video <mp4> <shots.json>  → {"shots": [...]} (shots.json: [{"id", "t0", "t1"}])"""
    if len(argv) >= 2 and argv[0] == "frames":
        print(json.dumps(measure_frames(load_images(argv[1:]))))
        return 0
    if len(argv) == 3 and argv[0] == "video":
        shots = json.loads(Path(argv[2]).read_text())
        print(json.dumps({"shots": [measure_shot(argv[1], s) for s in shots]}))
        return 0
    print(main.__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except CraftError as e:
        print(f"✗ {e}", file=sys.stderr)
        sys.exit(3)


# ---------------------------------------------------------------- a whole reference set (learn craft, T021)

PERSON_SKIP = ("insert", "short", "unknown", None)
STRIP_FRAMES, STRIP_W = 8, 320


def _set_mod():
    from . import refset
    return refset


def measure_video(name: str, vid: str, log=print) -> dict:
    """craft.json of one video of a reference set: every shot of its shots.json."""
    refset = _set_mod()
    data = refset.load(name)
    v = next(x for x in data["videos"] if x["id"] == vid)
    path = refset.video_path(name, v)
    prof = refset.profile_dir(name, vid)
    rows = json.loads((prof / "shots.json").read_text(encoding="utf-8"))["shots"]
    out = []
    for i, s in enumerate(rows):
        m = measure_shot(path, s)
        m["scale"] = s.get("scale")
        m["person"] = None if s.get("scale") is None else s.get("scale") not in PERSON_SKIP
        out.append(m)
        if (i + 1) % 50 == 0:
            log(f"  {vid}: {i + 1}/{len(rows)} cảnh")
    res = {"video": vid, "fps_sample": FPS, "shots": out}
    refset.write_json(prof / "craft.json", res)
    return res


def strip(path, t0, t1, out, n=STRIP_FRAMES, w=STRIP_W):
    """n frames evenly over [t0, t1] side by side, each w px wide."""
    from PIL import Image
    h = round(w * 9 / 16)
    ts = [t0 + (t1 - t0) * (k + 0.5) / n for k in range(n)]
    im = Image.new("RGB", (n * w, h))
    for k, t in enumerate(ts):
        f = _ffmpeg(["-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1", "-vf", f"scale={w}:{h}", "-f", "rawvideo",
                     "-pix_fmt", "rgb24", "-"], w, h, 3)
        if len(f):
            im.paste(Image.fromarray(f[0].astype(np.uint8)), (k * w, 0))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    im.save(out, quality=88)


def pick_strips(name: str, n: int = 80, seed: int = 41) -> list:
    """[(vid, shot)] of n person shots spread evenly over videos and scales (fixed seed)."""
    import random
    refset = _set_mod()
    rnd = random.Random(seed)
    pools = {}
    for v in refset.load(name)["videos"]:
        f = refset.profile_dir(name, v["id"]) / "shots.json"
        if not f.exists():
            continue
        for s in json.loads(f.read_text(encoding="utf-8"))["shots"]:
            if s.get("scale") not in PERSON_SKIP and s["t1"] - s["t0"] >= 1.0:
                pools.setdefault((v["id"], s["scale"]), []).append(s)
    keys = sorted(pools)
    rnd.shuffle(keys)
    out = []
    while len(out) < n and any(pools.values()):
        for k in keys:
            if pools[k] and len(out) < n:
                out.append((k[0], pools[k].pop(rnd.randrange(len(pools[k])))))
    return out


def craft_set(name: str, only=None, strips: int = 80, log=print) -> int:
    refset = _set_mod()
    data = refset.load(name)
    done = 0
    for v in data["videos"]:
        if only and v["id"] not in only:
            continue
        if not refset.video_path(name, v).exists() or not (refset.profile_dir(name, v["id"]) / "shots.json").exists():
            log(f"= {v['id']}: thiếu video hoặc shots.json, bỏ qua")
            continue
        r = measure_video(name, v["id"], log)
        moving = sum(s["cam"]["type"] != "still" for s in r["shots"])
        log(f"✓ {v['id']}: {len(r['shots'])} cảnh, máy động {moving}")
        done += 1
    if strips:
        for vid, s in pick_strips(name, strips):
            v = next(x for x in data["videos"] if x["id"] == vid)
            path = refset.video_path(name, v)
            if path.exists():
                strip(path, s["t0"], s["t1"], refset.profile_dir(name, vid) / "strips" / f"{s['id']}.jpg")
        log(f"✓ {strips} dải khung trong profile/<v>/strips/")
    return 0 if done else 1


def evidence(name: str, vid: str, t: float, label: str, w: int = 640) -> Path:
    from PIL import Image
    refset = _set_mod()
    v = next(x for x in refset.load(name)["videos"] if x["id"] == vid)
    h = round(w * 9 / 16)
    f = _ffmpeg(["-ss", f"{t:.3f}", "-i", str(refset.video_path(name, v)), "-frames:v", "1", "-vf", f"scale={w}:{h}",
                 "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], w, h, 3)
    if not len(f):
        raise CraftError(f"không lấy được khung {vid} @ {t}")
    out = refset.profile_dir(name, vid) / "evidence" / f"{label}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(f[0].astype(np.uint8)).save(out, quality=90)
    return out
