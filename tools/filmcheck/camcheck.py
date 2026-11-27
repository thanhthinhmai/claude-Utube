"""qc camera (specs/039 FR-018, FR-019, research R12): each built shot's camera against the option chosen for it.

Each shot's clip (animatic/shots/S#.mp4, else animatic/clips/S#.mp4) is measured with the same camera track as the
reference library (camtrack.measure, US1) and compared with shot_plan.<shot>.camera:
  cam_dir         the move goes the other way (push ↔ pull), or moves where the option holds still, or holds still
                  where the option moves
  cam_zoom        the zoom is more than 1 percentage point off
  cam_ease        the progress at the half of the shot is more than 0.10 off
  cam_parallax    the picture has parallax where the option has none (a 2D camera never does)
  cam_transition  the shot plan's transition is not the option's
A shot whose camera the user asked for by hand (camera.by_user_request) is not reported. A measure that cannot be
trusted (too short, too few corners) is a warning. The tier only reports, it never blocks `ae render` (R12).
Exceptions are per shot, with a reason, by the user only: tiers.add_exception refuses them inside a job (FR-019)."""
import hashlib
import json
import sys
import time
from pathlib import Path

from filmcheck import tiers

HERE = Path(__file__).resolve().parent
TIER = "camera"
RULES = ("cam_zoom", "cam_dir", "cam_ease", "cam_parallax", "cam_transition")
ZOOM_TOL = 1.0
EASE_TOL = 0.10
FIX = {"cam_zoom": "run `sh bin/studio camera fit <film>` (scales the keyed zoom until the picture measures the option)",
       "cam_dir": "the camera must move the way the chosen option does (push, pull or hold still)",
       "cam_ease": "use the option's ease (ease_ae) on the camera's two keys",
       "cam_parallax": "keep the camera 2D: scale and move the whole picture, no layer moving on its own depth",
       "cam_transition": "use the option's transition, or choose another option on the Camera page"}


class CameraCheckError(Exception):
    """Cannot check (exit code 2): not an AE film, no chosen camera, no clip for a shot. code 3: the draft could not
    be made (no After Effects, Blender or GPU)."""

    def __init__(self, message, code=2):
        super().__init__(message)
        self.code = code


def _film(d: Path) -> dict:
    sys.path.insert(0, str(HERE.parent))
    from ae import film as filmdoc
    try:
        return filmdoc.require_ae(d)
    except filmdoc.FilmError as e:
        raise CameraCheckError(e.message) from None


def _track():
    sys.path.insert(0, str(HERE.parent / "style-learn"))
    try:
        from sl import camtrack
    except ImportError as e:
        raise CameraCheckError(f"learn tools missing ({e}): sh bin/studio deps learn") from None
    return camtrack


def _moves(zoom: float) -> str:
    return "push" if zoom > 0 else "pull"


# ---------- rules (pure) ----------
def _issue(sid: str, rule: str, have, want, sev: str = "block") -> dict:
    return {"ref": sid, "shot": sid, "rule": rule, "severity": sev, "have": have, "want": want, "fix": FIX[rule]}


def rules(plan: dict, measured: dict) -> tuple:
    """plan {sid: shot_plan row}, measured {sid: camtrack.measure result}. Returns (issues, warnings)."""
    issues, warns = [], []
    for sid, m in measured.items():
        row = plan.get(sid) or {}
        cam = row.get("camera")
        if not cam or cam.get("by_user_request") or row.get("by_user_request"):
            continue
        if not m.get("reliable", True):
            warns.append({"rule": "unreliable", "shot": sid, "why": m.get("why_unreliable")})
        want_move = cam.get("move") or "static"
        want_zoom = float(cam.get("zoom_pct") or 0.0)
        have_zoom = float(m.get("zoom_pct") or 0.0)
        want_z = want_move in ("push", "pull")
        have_z = m.get("move") in ("push", "pull")
        if want_z and have_z and _moves(have_zoom) != _moves(want_zoom):
            issues.append(_issue(sid, "cam_dir", {"move": m["move"]}, {"move": want_move}))
        elif want_z and not have_z or have_z and not want_z and abs(have_zoom) > ZOOM_TOL:
            issues.append(_issue(sid, "cam_dir", {"move": m.get("move"), "zoom_pct": have_zoom},
                                 {"move": want_move, "zoom_pct": want_zoom}))
        elif abs(have_zoom - want_zoom) > ZOOM_TOL:
            issues.append(_issue(sid, "cam_zoom", {"zoom_pct": round(have_zoom, 2)}, {"zoom_pct": want_zoom}))
        we, he = cam.get("ease"), m.get("ease")
        if want_z and have_z and we and he and abs(float(he[1]) - float(we[1])) > EASE_TOL:
            issues.append(_issue(sid, "cam_ease", {"ease": he}, {"ease": we}))
        if m.get("parallax") and not cam.get("parallax"):
            issues.append(_issue(sid, "cam_parallax", {"parallax_px": m.get("parallax_px")}, {"parallax": False}))
        tr = row.get("transition")
        tr = tr.get("type") if isinstance(tr, dict) else tr
        if tr and cam.get("transition") and tr != cam["transition"]:
            issues.append(_issue(sid, "cam_transition", {"transition": tr}, {"transition": cam["transition"]}))
    return issues, warns


# ---------- clips ----------
def clip_of(d: Path, sid: str):
    for p in (d / "animatic" / "shots" / f"{sid}.mp4", d / "animatic" / "clips" / f"{sid}.mp4"):
        if p.is_file():
            return p
    return None


def _length(p: Path) -> float:
    import subprocess
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True, timeout=60)
    return float(r.stdout.strip() or 0)


def measure_all(d: Path, shots: list, measure=None) -> dict:
    """{sid: measured}; measure(path, t0, t1, trim_in, trim_out) is camtrack.measure (tests pass a fake)."""
    ct = None if measure else _track()
    measure = measure or ct.measure
    trim = ct.CUT_TRIM if ct else 0.05
    out, missing = {}, []
    for sid in shots:
        p = clip_of(d, sid)
        if not p:
            missing.append(sid)
            continue
        try:
            out[sid] = measure(p, 0.0, _length(p), trim, trim)
        except Exception as e:                       # noqa: BLE001 — camtrack.TrackError and broken clips
            out[sid] = {"reliable": False, "why_unreliable": str(e)[:200], "move": "static", "zoom_pct": 0.0}
    if missing:
        raise CameraCheckError(f"no clip for {', '.join(missing)}: build the draft first (sh bin/studio ae draft "
                               f"{d.name})")
    return out


def fingerprint(d: Path, plan: dict, shots: list) -> str:
    h = hashlib.sha256(json.dumps({s: (plan.get(s) or {}).get("camera") for s in shots}, sort_keys=True).encode())
    for s in shots:
        p = clip_of(d, s)
        h.update(f"{s}:{p.stat().st_size}:{int(p.stat().st_mtime)}".encode() if p else b"-")
    return h.hexdigest()[:16]


def _finish(d: Path, issues: list, warns: list, measures: dict, fp: str, seconds: float) -> dict:
    tiers.apply_exceptions(issues, tiers.load_exceptions(d))
    r = tiers.result(TIER, issues, measures, [], seconds, fp, warnings=warns)
    return tiers.save_tier(d, TIER, r)


def run(film_dir, shots=None, measure=None) -> dict:
    t0 = time.time()
    d = Path(film_dir)
    doc = _film(d)
    plan = doc.get("shot_plan") or {}
    want = [s for s in (shots or doc["shots"]) if s in doc["shots"]]
    have = [s for s in want if (plan.get(s) or {}).get("camera")]
    if not have:
        raise CameraCheckError("no shot has a chosen camera: approve the Camera page (or sh bin/studio camera choose)")
    m = measure_all(d, have, measure)
    issues, warns = rules(plan, m)
    return _finish(d, issues, warns, {"shots": m, "skipped": [s for s in want if s not in have]},
                   fingerprint(d, plan, have), time.time() - t0)


def recompute(film_dir) -> dict:
    """After qc except: the stored issues again with the exceptions (nothing measured again)."""
    d = Path(film_dir)
    r = tiers.load_tier(d, TIER)
    if not r:
        return {}
    for i in r["issues"]:
        i.pop("excepted", None)
    return _finish(d, r["issues"], r.get("warnings") or [], r["measures"], r["fingerprint"], r.get("seconds", 0))


# ---------- camera fit ----------
FIT_ROUNDS = 3
FIT_MIN_HAVE = 0.5           # a zoom read under 0.5 % cannot be scaled (a shot that barely moves: cam_dir, not fit)
FIT_SAME = 0.2               # the measure moved less than this after fit_k changed: the shot sets its own camera


def _draft(d: Path, shots: list) -> int:
    import subprocess
    repo = HERE.parent.parent
    return subprocess.run(["sh", str(repo / "bin" / "studio"), "ae", "draft", d.name, "--dir", str(d),
                           "--shots", ",".join(shots)]).returncode


def _clamp(k: float) -> float:
    from ae.film import FIT_K
    return round(min(FIT_K[1], max(FIT_K[0], k)), 3)


def fit_factors(plan: dict, issues: list, measured: dict, history=None) -> tuple:
    """({sid: new fit_k}, [sids that ignore the plan camera]) for the shots whose only zoom fault is its size
    (cam_zoom, same direction, readable). history {sid: [(fit_k, measured zoom), …]}: after two points the next
    factor is the secant through the last two (the read is not proportional to the key in a busy picture)."""
    history = history or {}
    dirs = {i["shot"] for i in issues if i["rule"] == "cam_dir" and not i.get("excepted")}
    out, own = {}, []
    for i in issues:
        sid = i["shot"]
        if i["rule"] != "cam_zoom" or i.get("excepted") or sid in dirs:
            continue
        cam = (plan.get(sid) or {}).get("camera") or {}
        want, have = float(cam.get("zoom_pct") or 0), float((measured.get(sid) or {}).get("zoom_pct") or 0)
        if abs(have) < FIT_MIN_HAVE or want * have <= 0:
            continue
        k1 = float(cam.get("fit_k") or 1.0)
        h = [p for p in history.get(sid, []) if p[0] != k1][-1:]
        if h:
            k0, h0 = h[0]
            if abs(have - h0) < FIT_SAME:
                own.append(sid)
                continue
            k = k1 + (want - have) * (k1 - k0) / (have - h0)
        else:
            k = k1 * want / have
        out[sid] = _clamp(k)
    return out, own


def fit(film_dir, shots=None, rounds: int = FIT_ROUNDS, measure=None, draft=None) -> dict:
    """Measure → scale each off shot's keyed zoom (shot_plan.<S>.camera.fit_k) → draft those shots again → measure,
    at most `rounds` times. Only cam_zoom is corrected; the other faults stay for the shot's jsx. Returns
    {rounds: [{shot: {have, want, fit_k}}], own_camera: [shots whose picture did not follow fit_k], result}."""
    from filmcheck import camsuggest
    d = Path(film_dir)
    draft = draft or _draft
    log, hist, own = [], {}, set()
    r = run(d, shots, measure)
    for _ in range(max(0, rounds)):
        plan = _film(d).get("shot_plan") or {}
        m = r["measures"]["shots"]
        for s in m:
            if (plan.get(s) or {}).get("camera"):
                hist.setdefault(s, []).append((float(plan[s]["camera"].get("fit_k") or 1.0), float(m[s].get("zoom_pct") or 0)))
        ks, o = fit_factors(plan, r["issues"], m, {s: v[:-1] for s, v in hist.items()})
        own |= set(o)
        ks = {s: k for s, k in ks.items() if s not in own and k != float(plan[s]["camera"].get("fit_k") or 1.0)}
        if not ks:
            break
        log.append({s: {"have": m[s]["zoom_pct"], "want": plan[s]["camera"]["zoom_pct"], "fit_k": k} for s, k in ks.items()})

        def put(raw, ks=ks):
            for s, k in ks.items():
                raw["shot_plan"][s]["camera"]["fit_k"] = k
        camsuggest._write_film(d, put)
        rc = draft(d, sorted(ks, key=lambda x: int(x[1:]) if x[1:].isdigit() else x))
        if rc:
            raise CameraCheckError(f"ae draft failed (exit {rc}) for {', '.join(ks)}", 3 if rc == 3 else 1)
        r = run(d, shots, measure)
    return {"rounds": log, "own_camera": sorted(own), "result": r}
