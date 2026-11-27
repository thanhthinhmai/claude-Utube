"""camera suggest|choose|retime (specs/039 US2, research R4–R6): 2–3 camera options per shot of an AE film.

Each shot of the film (shot_plan: size, people, card, action, outdoor, prop; length from timing.json or shots.json) is
scored against every reference shot of the style's camera library with a fixed table (R4, WEIGHTS), so each option can
say in one line why it was picked (FR-007). Options (R5):
  1 ★  the camera of the most similar reliable reference shot: its zoom and drift per second times the film shot's
       length, zoom held inside p25–p75 of the size; its ease (the size's median when the shot is not reliable)
  2    the best reference shot that differs from option 1 in size or direction
  3    the summary of the next wider size, or a still camera when the size holds ≥ 15 % still shots
Duplicates (same size and move, |Δzoom| < 1, |Δcx|, |Δcy| < 10) are dropped. An option outside p25–p75 carries a note.
A camera block already in shot_plan stays as an option with ref "film". The library only holds 2D moves (camtrack), so
with parallax_share < 0.05 no option moves the camera (FR-009).

Start framing (T016): start.scale puts the main person at the reference shot's height (subject_h) against the person's
height at scale 1. Before a build has marks, the person's height at scale 1 is the median subject_h of the reference at
that size, so scale = subject_h / median (≥ 1), and cx/cy follow subject_x/y; then the frame is pushed in until the
start and end windows both stay inside the picture (no edge shows, like camInside of the kit).

ease_ae: AE eases a key pair with speed 0 and an influence per side; EASE_TABLE holds where that Bézier is at ¼, ½, ¾ for
influences 5–95, and the closest pair to the chosen ease is written for the kit (R7).

options.json is written atomically under camera/options.json.lock. Durations change after Voice: retime() keeps each
option's rate per second and computes zoom and drift for the new length (R6); the Camera point's fingerprint skips them."""
import datetime as dt
import json
import math
import sys
from pathlib import Path

from filmcheck import shotnotes, stylerefs

HERE = Path(__file__).resolve().parent
ORDER = ["ecu", "cu", "med", "wide", "huge"]
WEIGHTS = {"card": 3, "size": 3, "people": 2, "action": 2, "outdoor": 1, "prop": 1, "dur": 1}
FLAGS = ("action", "outdoor", "prop")
MIN_SCORE = 0.5                   # below this no reference shot is "similar" (ref: null)
EVIDENCE_GAP = 0.1                # a shot with evidence frames wins over a better one by less than this
STATIC_SHARE = 0.15
PARALLAX_SHARE = 0.05
MOVES_2D = ("static", "push", "pull", "pan")
W, H = 1920, 1080
TOL = 0.05                        # p25–p75 edges after rounding


class CameraError(Exception):
    """Cannot suggest (exit code 2): not an AE film, no shot plan, no camera library."""


def _film():
    sys.path.insert(0, str(HERE.parent))
    from ae import film as filmdoc
    return filmdoc


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


# ---------- the library ----------
def load_library(d: Path, doc: dict, style: str = None, refset: str = None) -> dict:
    """{"source", "style", "summary", "shots", "root"} from --set, else --style, else the film's style."""
    if refset:
        sys.path.insert(0, str(HERE.parent / "style-learn"))
        try:
            from sl import camlib
        except ImportError as e:
            raise CameraError(f"learn tools missing ({e}): sh bin/studio deps learn") from None
        rows = camlib.library(refset)
        if not rows:
            raise CameraError(f"references/{refset} has no camera library: run `sh bin/studio learn camera {refset}`")
        for r in rows:                     # evidence paths relative to references/<set>/profile/
            if r.get("evidence"):
                vid = r["id"].split(":")[0]
                r["evidence"] = [f"{vid}/{e}" for e in r["evidence"]]
        return {"source": f"set:{refset}", "style": doc.get("style") or stylerefs.slug_of(d),
                "summary": camlib.summary(rows), "shots": rows}
    slug = style or doc.get("style") or stylerefs.slug_of(d)
    if not slug:
        raise CameraError("the film names no style: pass --style or --set")
    f = stylerefs.style_dir(d, slug) / "camera.json"
    try:
        lib = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise CameraError(f"my-styles/{slug} has no camera.json: run `sh bin/studio learn camera <set>` "
                          f"then `sh bin/studio learn save <set> {slug} --update`") from None
    return {"source": f"style:{slug}", "style": slug, "summary": {k: v for k, v in lib.items() if k != "shots"},
            "shots": lib.get("shots") or []}


def ref_file(d: Path, rel: str) -> Path:
    """The file of a reference frame (an option's ref_frames entry), only inside the camera library the options came
    from: my-styles/<style>/camera/… or references/<set>/profile/<vid>/camera/…; CameraError otherwise."""
    o = load(Path(d)) or {}
    src = str(o.get("source") or "")
    if src.startswith("style:"):
        base = stylerefs.style_dir(Path(d), src[6:])
    elif src.startswith("set:"):
        sys.path.insert(0, str(HERE.parent / "style-learn"))
        from sl import refset
        base = refset.set_dir(src[4:]) / "profile"
    else:
        raise CameraError("no camera options")
    base = base.resolve()
    p = (base / (rel or "")).resolve()
    if base not in p.parents or "camera" not in p.relative_to(base).parts[:-1] \
            or p.suffix.lower() not in (".jpg", ".jpeg", ".png") or not p.is_file():
        raise CameraError(f"no reference frame {rel}")
    return p


# ---------- the film's shots ----------
def durations(d: Path, doc: dict) -> dict:
    """Seconds per shot: timing.json, else the film's shots.json (R6)."""
    try:
        t = json.loads((d / "timing.json").read_text(encoding="utf-8"))
        fps = float(t.get("fps") or doc.get("fps") or 30)
        out = {s: f / fps for s, f in (t.get("frames") or {}).items() if s in doc["shots"]}
        if len(out) == len(doc["shots"]):
            return out
    except (OSError, ValueError):
        pass
    try:
        rows = json.loads((d / "shots.json").read_text(encoding="utf-8")).get("shots") or []
        out = {r[3]: float(r[1]) - float(r[0]) for r in rows if len(r) > 3 and r[3] in doc["shots"]}
    except (OSError, ValueError, TypeError, IndexError):
        out = {}
    missing = [s for s in doc["shots"] if s not in out]
    if missing:
        raise CameraError(f"no length for {', '.join(missing[:5])}: write timing.json or shots.json first")
    return out


def film_shot(plan: dict, dur: float) -> dict:
    return {"size": plan.get("size"), "people": plan.get("people"), "card": plan.get("card"),
            **{k: plan.get(k) for k in FLAGS}, "dur": dur}


# ---------- similarity (R4) ----------
def _group(n):
    return None if n is None else min(int(n), 3)


def similarity(shot: dict, ref: dict):
    """(score 0–1, why {field: match}) or (None, None) when the card flag differs (never similar)."""
    why, have, got = {}, 0.0, 0.0
    if shot.get("card") is not None:
        if ref.get("card") is not None and bool(ref["card"]) != bool(shot["card"]):
            return None, None
        why["card"] = 1.0 if ref.get("card") is not None else 0.0
    if shot.get("size"):
        a, b = shot["size"], ref.get("size")
        why["size"] = 1.0 if a == b else (0.5 if a in ORDER and b in ORDER and abs(ORDER.index(a) - ORDER.index(b)) == 1
                                          else 0.0)
    if shot.get("people") is not None:
        why["people"] = 1.0 if _group(shot["people"]) == _group(ref.get("people")) else 0.0
    for k in FLAGS:
        if shot.get(k) is not None:
            why[k] = 1.0 if ref.get(k) is not None and bool(ref[k]) == bool(shot[k]) else 0.0
    rd = ref.get("dur") or 0
    why["dur"] = round(max(0.0, 1 - abs(math.log(shot["dur"] / rd)) / math.log(3)), 3) if rd > 0 else 0.0
    for k, m in why.items():
        have += WEIGHTS[k]
        got += WEIGHTS[k] * m
    return round(got / have, 3), why


def ranked(shot: dict, shots: list) -> list:
    out = []
    for r in shots:
        s, why = similarity(shot, r)
        if s is not None:
            out.append((s, why, r))
    out.sort(key=lambda x: (-x[0], x[2]["id"]))
    return out


def _prefer_evidence(cands: list):
    """The best candidate, or one with evidence frames that is less than EVIDENCE_GAP behind it."""
    if not cands:
        return None
    best = cands[0]
    if not best[2].get("evidence"):
        for c in cands[1:]:
            if best[0] - c[0] >= EVIDENCE_GAP:
                break
            if c[2].get("evidence"):
                return c
    return best


# ---------- AE ease table (R7) ----------
def _bezier_at(a: float, b: float, t: float) -> float:
    """Value of AE's speed-0 ease (out influence a, in influence b, 0–1) at time t, from 0 to 1."""
    x1, x2 = a, 1 - b
    lo, hi = 0.0, 1.0
    for _ in range(40):                    # x(s) rises, so bisect for s
        s = (lo + hi) / 2
        x = 3 * (1 - s) ** 2 * s * x1 + 3 * (1 - s) * s * s * x2 + s ** 3
        lo, hi = (s, hi) if x < t else (lo, s)
    s = (lo + hi) / 2
    return 3 * (1 - s) * s * s + s ** 3


EASE_TABLE = [((i, o), [round(_bezier_at(o / 100, i / 100, q), 3) for q in (0.25, 0.5, 0.75)])
              for i in range(5, 100, 5) for o in range(5, 100, 5)]


def ease_ae(ease) -> list:
    """[in, out] influence (%) whose ease is closest to [q¼, q½, q¾]; None for a still camera."""
    if not ease:
        return None
    (i, o), _ = min(EASE_TABLE, key=lambda e: sum((a - b) ** 2 for a, b in zip(e[1], ease)))
    return [float(i), float(o)]


def clean_ease(e):
    """Three rising numbers in 0–1 (camtrack may overshoot), or None. A curve that does all its move in one quarter
    (from a nearly still zoom, a flash) is not an ease to copy: None, so the size's median is used."""
    if not e or len(e) != 3:
        return None
    out, m = [], 0.0
    for x in e:
        m = max(m, min(1.0, max(0.0, float(x))))
        out.append(round(m, 3))
    if not 0.1 <= out[1] <= 0.9 or out[2] - out[0] < 0.2:
        return None
    return out


# ---------- framing (T016) ----------
def framing(ref: dict, base_sum: dict, size_sum: dict, zoom_pct: float, drift: list) -> dict:
    """start {scale, cx, cy}: the person at the reference height and place, the whole move inside the picture.
    base_sum: the summary of the size the shot is drawn at (its person height at scale 1); size_sum: the option's size
    (its median height when the option comes from the summary, not from one reference shot)."""
    mh = ((base_sum or {}).get("subject_h") or [None, None, None])[1]
    sh = (ref or {}).get("subject_h") or ((size_sum or {}).get("subject_h") or [None, None, None])[1]
    scale = max(1.0, sh / mh) if sh and mh else 1.0
    sx, sy = (ref or {}).get("subject_x"), (ref or {}).get("subject_y")
    cx = 50 + (50 - sx) / scale if sx is not None else 50.0
    cy = 50 + (50 - sy) / scale if sy is not None else 50.0
    end = 1 + zoom_pct / 100
    scale = max(scale, 1 / end if end > 0 else 4.0)
    for _ in range(300):                   # push in until the start and end windows fit
        h = 50 / scale
        cx, cy = min(max(cx, h), 100 - h), min(max(cy, h), 100 - h)
        se = scale * end
        he = 50 / se
        ex, ey = cx + drift[0] / W * 100 / se, cy + drift[1] / H * 100 / se
        if he <= ex <= 100 - he and he <= ey <= 100 - he or scale >= 4:
            break
        scale *= 1.01
    return {"scale": round(min(scale, 4.0), 3), "cx": round(cx, 1), "cy": round(cy, 1)}


# ---------- options (R5) ----------
def _q(sum_size: dict, key: str):
    v = (sum_size or {}).get(key)
    return v if v and len(v) == 3 and v[0] is not None else None


def _note(opt: dict, sum_size: dict, main: str) -> str:
    out = []
    zq, dq, uq = _q(sum_size, "zoom_pct"), _q(sum_size, "drift_px"), _q(sum_size, "dur")
    if opt["move"] in ("push", "pull") and zq and not zq[0] - TOL <= abs(opt["zoom_pct"]) <= zq[2] + TOL:
        out.append(f"zoom {abs(opt['zoom_pct']):.1f}% ngoài p25–p75 ({zq[0]:.1f}–{zq[2]:.1f}%)")
    if opt["move"] != "static" and dq and math.hypot(*opt["drift_px"]) > dq[2] + 1:
        out.append(f"trôi {math.hypot(*opt['drift_px']):.0f} px trên p75 ({dq[2]:.0f} px)")
    if uq and not uq[0] - TOL <= opt["dur"] <= uq[2] + TOL:
        out.append(f"shot {opt['dur']:.1f}s ngoài p25–p75 của cỡ này ({uq[0]:.1f}–{uq[2]:.1f}s)")
    if opt["transition"] != main:
        out.append(f"chuyển cảnh {opt['transition']}, video mẫu chủ yếu {main}")
    return "; ".join(out) or None


def _from_ref(ref: dict, size: str, dur: float, summ: dict, clamp: bool) -> dict:
    by = summ.get("by_size") or {}
    ss = by.get(size) or {}
    move = ref["move"] if ref.get("move") in MOVES_2D else "static"
    if move in ("push", "pull") and abs(float(ref.get("zoom_pct") or 0)) < 1.0 and \
            math.hypot(*(ref.get("drift_px") or [0, 0])) >= 4.0:
        move = "pan"                       # a zoom under 1 % with a real drift reads as a pan
    rate = float(ref.get("rate_pct_s") or 0) if move in ("push", "pull") else 0.0
    zoom = rate * dur
    zq = _q(ss, "zoom_pct")
    if clamp and move in ("push", "pull") and zq:
        zoom = math.copysign(min(max(abs(zoom), zq[0]), zq[2]), zoom or (1 if move == "push" else -1))
    rdur = float(ref.get("dur") or dur) or dur
    k = dur / rdur
    drift = [round(float(x) * k, 1) for x in (ref.get("drift_px") or [0, 0])] if move != "static" else [0.0, 0.0]
    dq = _q(ss, "drift_px")
    mag = math.hypot(*drift)
    if clamp and dq and mag > dq[2] > 0:
        drift = [round(x * dq[2] / mag, 1) for x in drift]
    ease = clean_ease(ref.get("ease")) if ref.get("reliable") else clean_ease(ss.get("ease_q"))
    if move == "static":
        ease = None
    elif ease is None:
        ease = clean_ease(ss.get("ease_q"))
    return {"size": size, "move": move, "zoom_pct": round(zoom, 2), "rate_pct_s": round(zoom / dur, 3) if dur else 0.0,
            "ease": ease, "ease_ae": ease_ae(ease), "drift_px": drift,
            "cam_height": ref.get("cam_height"), "lens": ref.get("lens")}


def _from_summary(size: str, dur: float, summ: dict, still: bool) -> dict:
    ss = (summ.get("by_size") or {}).get(size) or {}
    if still:
        return {"size": size, "move": "static", "zoom_pct": 0.0, "rate_pct_s": 0.0, "ease": None, "ease_ae": None,
                "drift_px": [0.0, 0.0], "cam_height": None, "lens": None}
    rq = _q(ss, "rate_pct_s")
    push = ss.get("push_share", 0) >= ss.get("pull_share", 0)
    rate = (rq[1] if rq else 1.0) * (1 if push else -1)
    zoom = rate * dur
    zq = _q(ss, "zoom_pct")
    if zq:
        zoom = math.copysign(min(max(abs(zoom), zq[0]), zq[2]), zoom)
    ease = clean_ease(ss.get("ease_q"))
    return {"size": size, "move": "push" if push else "pull", "zoom_pct": round(zoom, 2),
            "rate_pct_s": round(zoom / dur, 3), "ease": ease, "ease_ae": ease_ae(ease), "drift_px": [0.0, 0.0],
            "cam_height": None, "lens": None}


def _same(a: dict, b: dict) -> bool:
    return (a["size"] == b["size"] and a["move"] == b["move"] and abs(a["zoom_pct"] - b["zoom_pct"]) < 1
            and abs(a["start"]["cx"] - b["start"]["cx"]) < 10 and abs(a["start"]["cy"] - b["start"]["cy"]) < 10)


SIZE_VI = {"ecu": "cận cảnh đặc tả", "cu": "cận cảnh", "med": "trung cảnh", "wide": "toàn cảnh", "huge": "đại cảnh",
           "insert": "chèn"}


def _reason(ref: dict, why: dict, score: float, opt: dict, zq) -> str:
    bits = [SIZE_VI.get(ref.get("size"), ref.get("size") or "?")]
    if ref.get("people") is not None:
        bits.append(f"{ref['people']} người")
    for k, vi in (("action", "hành động"), ("outdoor", "ngoài trời"), ("prop", "đạo cụ")):
        if ref.get(k) and why.get(k):
            bits.append(vi)
    tail = ""
    if opt["move"] in ("push", "pull") and zq:
        inside = zq[0] <= abs(opt["zoom_pct"]) <= zq[2]
        tail = f"; zoom {abs(opt['zoom_pct']):.1f}% {'trong' if inside else 'ngoài'} p25–p75 của {SIZE_VI.get(opt['size'], opt['size'])}"
    return f"giống {ref['id']} ({', '.join(bits)}, điểm {score:.2f}){tail}"


def options_for(sid: str, plan: dict, dur: float, lib: dict) -> dict:
    """The options of one shot: {"dur", "options"} (data-model "Camera option")."""
    summ = lib["summary"]
    by = summ.get("by_size") or {}
    main = summ.get("transition_main") or "cut"
    shot = film_shot(plan, dur)
    cands = ranked(shot, lib["shots"])
    reliable = [c for c in cands if c[2].get("reliable")]
    engine = plan.get("engine") or ("blender" if plan.get("size") in ("wide", "huge") else "ae")
    size0 = plan.get("size")
    opts = []
    first_size = [None]                   # the size the shot is drawn at when the plan names none: option 1's

    def add(base: dict, ref, score, why, reason, clamp_note=True):
        o = {"n": len(opts) + 1, "recommended": not opts, "engine": engine, "dur": round(dur, 3), **base,
             "transition": main}
        o["start"] = framing(ref, by.get(size0 or first_size[0] or o["size"]), by.get(o["size"]), o["zoom_pct"],
                             o["drift_px"])
        o.update({"ref": ref["id"] if ref else None,
                  "ref_frames": (ref or {}).get("evidence") or None, "score": score, "why": why, "reason": reason})
        o["note"] = _note(o, by.get(o["size"]), main)
        if any(_same(o, p) for p in opts):
            return False
        opts.append(o)
        return True

    best = _prefer_evidence(reliable)
    if best and best[0] >= MIN_SCORE:
        s, why, ref = best
        size = size0 or ref.get("size") or "med"
        base = _from_ref(ref, size, dur, summ, clamp=True)
        add(base, ref, s, why, _reason(ref, why, s, base, _q(by.get(size), "zoom_pct")))
    else:
        top = cands[0][0] if cands else 0.0
        size = size0 or "med"
        add(_from_summary(size, dur, summ, still=False), None, top, None,
            f"không có shot mẫu giống (điểm cao nhất {top:.2f}); lấy trung vị của {SIZE_VI.get(size, size)}")
    first = opts[0]
    first_size[0] = first["size"]
    # option 2: the best reference shot that differs in size or direction
    others = [c for c in cands if c[0] >= MIN_SCORE and
              ((c[2].get("size") or first["size"]) != first["size"] or c[2].get("move") != first["move"])]
    pick = _prefer_evidence(others)
    if pick:
        s, why, ref = pick
        base = _from_ref(ref, ref.get("size") or first["size"], dur, summ, clamp=False)
        add(base, ref, s, why, _reason(ref, why, s, base, _q(by.get(base["size"]), "zoom_pct")))
    # option 3: the next wider size, or a still camera
    ss = by.get(first["size"]) or {}
    if ss.get("static_share", 0) >= STATIC_SHARE and first["move"] != "static":
        add(_from_summary(first["size"], dur, summ, still=True), None, None, None,
            f"máy đứng: {ss['static_share'] * 100:.0f}% shot {SIZE_VI.get(first['size'], first['size'])} của video mẫu đứng yên")
    elif first["size"] in ORDER and ORDER.index(first["size"]) + 1 < len(ORDER):
        wider = ORDER[ORDER.index(first["size"]) + 1]
        if by.get(wider):
            add(_from_summary(wider, dur, summ, still=False), None, None, None,
                f"cỡ rộng hơn một bậc: trung vị của {SIZE_VI[wider]} (n={by[wider]['n']})")
    # the film maker's own camera block stays an option
    own = plan.get("camera")
    if isinstance(own, dict) and own.get("start"):
        o = {"n": len(opts) + 1, "recommended": False, "engine": engine, "dur": round(dur, 3),
             **{k: own.get(k) for k in ("size", "move", "start", "zoom_pct", "rate_pct_s", "ease", "ease_ae",
                                        "drift_px")},
             "transition": own.get("transition", main), "cam_height": plan.get("cam_height"), "lens": plan.get("lens"),
             "ref": "film", "ref_frames": None, "score": None, "why": None, "reason": "máy quay đã có trong shot_plan"}
        if own.get("by_user_request"):
            o["by_user_request"] = True
        o["note"] = _note(o, by.get(o["size"]), main) if o.get("zoom_pct") is not None else None
        if not any(_same(o, p) for p in opts):
            if len(opts) == 3:                 # at most 3: the film maker's camera takes the place of option 3
                opts.pop()
            o["n"] = len(opts) + 1
            opts.append(o)
    return {"dur": round(dur, 3), "options": opts}


# ---------- files ----------
def opath(d: Path) -> Path:
    return Path(d) / "camera" / "options.json"


def load(d: Path):
    try:
        return json.loads(opath(d).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _dump(doc) -> bytes:
    return (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode()


def _require(d: Path) -> dict:
    filmdoc = _film()
    try:
        doc = filmdoc.require_ae(d)
    except filmdoc.FilmError as e:
        raise CameraError(e.message) from None
    if not doc.get("shots"):
        raise CameraError("film.json has no shots")
    return doc


def suggest(d: Path, style: str = None, refset: str = None, shots=None, keep_others: bool = False) -> dict:
    d = Path(d)
    doc = _require(d)
    lib = load_library(d, doc, style, refset)
    durs = durations(d, doc)
    want = list(shots) if shots else list(doc["shots"])
    bad = [s for s in want if s not in doc["shots"]]
    if bad:
        raise CameraError(f"not shots of this film: {', '.join(bad)}")
    plans = doc.get("shot_plan") or {}
    with shotnotes.locked(opath(d)):
        old = load(d) or {}
        olds = old.get("shots") or {}
        out = {"version": 1, "style": lib["style"], "source": lib["source"], "made_at": now(),
               "summary": {"transition_main": lib["summary"].get("transition_main"),
                           "parallax_share": lib["summary"].get("parallax_share")},
               "shots": {}}
        for s in doc["shots"]:
            if s not in want:
                if s in olds and (keep_others or shots):
                    out["shots"][s] = olds[s]
                continue
            row = options_for(s, plans.get(s) or {}, durs[s], lib)
            prev = (olds.get(s) or {}).get("choice")
            ns = {o["n"] for o in row["options"]}
            if prev and prev.get("n") in ns and prev.get("source") != "auto":
                row["choice"] = prev
            else:
                row["choice"] = {"n": 1, "recommended": 1, "source": "auto", "by": "claude", "at": out["made_at"]}
            out["shots"][s] = row
        shotnotes.write_atomic(opath(d), _dump(out))
    return out


CAM_KEYS = ("size", "move", "start", "zoom_pct", "rate_pct_s", "ease", "ease_ae", "drift_px", "transition")


def _write_film(d: Path, fn):
    """Change film.json under its lock and check it with ae/film.py before it is saved."""
    filmdoc = _film()
    p = Path(d) / "film.json"
    with shotnotes.locked(p):
        raw = json.loads(p.read_text(encoding="utf-8"))
        fn(raw)
        try:
            filmdoc._check_plan(json.loads(json.dumps(raw)))
        except filmdoc.FilmError as e:
            raise CameraError(e.message) from None
        shotnotes.write_atomic(p, (json.dumps(raw, ensure_ascii=False, indent=2) + "\n").encode())


def camera_block(opt: dict) -> dict:
    b = {k: opt.get(k) for k in CAM_KEYS}
    if opt.get("by_user_request"):
        b["by_user_request"] = True
    return b


def choose(d: Path, sid: str, n: int, by: str = "owner", source: str = "user") -> dict:
    d = Path(d)
    doc = _require(d)
    if sid not in doc["shots"]:
        raise CameraError(f"{sid} is not a shot of this film")
    with shotnotes.locked(opath(d)):
        o = load(d)
        if not o or sid not in (o.get("shots") or {}):
            raise CameraError(f"{sid} has no camera options: run `sh bin/studio camera suggest {d.name}`")
        row = o["shots"][sid]
        opt = next((x for x in row["options"] if x["n"] == n), None)
        if not opt:
            raise CameraError(f"{sid} has no option {n} (have {', '.join(str(x['n']) for x in row['options'])})")
        rec = next((x["n"] for x in row["options"] if x.get("recommended")), 1)
        row["choice"] = {"n": n, "recommended": rec, "source": source, "by": by, "at": now()}

        def put(raw):
            sp = raw.setdefault("shot_plan", {}).setdefault(sid, {})
            sp["camera"] = camera_block(opt)
            sp["move"] = opt["move"]
        _write_film(d, put)
        shotnotes.write_atomic(opath(d), _dump(o))
    return {"shot": sid, "choice": row["choice"], "camera": camera_block(opt)}


def choose_auto(d: Path, by: str = "claude") -> list:
    """Every shot without a camera block takes its choice (★ when auto): the agent's path when the point is off."""
    o = load(d) or {}
    done = []
    for sid, row in (o.get("shots") or {}).items():
        done.append(choose(d, sid, (row.get("choice") or {}).get("n", 1), by=by,
                           source=(row.get("choice") or {}).get("source", "auto")))
    return done


def retime(d: Path) -> list:
    """New lengths (timing.json) → zoom and drift from each option's rate; returns [{shot, dur0, dur1, zoom0, zoom1}]."""
    d = Path(d)
    doc = _require(d)
    durs = durations(d, doc)
    changes = []
    with shotnotes.locked(opath(d)):
        o = load(d)
        if not o:
            return []
        for sid, row in (o.get("shots") or {}).items():
            new = durs.get(sid)
            if not new or abs(new - row["dur"]) < 1e-3:
                continue
            k = new / row["dur"] if row["dur"] else 1.0
            ch = row.get("choice") or {}
            z0 = None
            for opt in row["options"]:
                z = round((opt.get("rate_pct_s") or 0) * new, 2)
                if opt["n"] == ch.get("n"):
                    z0 = (opt["zoom_pct"], z)
                opt["zoom_pct"] = max(-40.0, min(40.0, z))
                opt["drift_px"] = [round(x * k, 1) for x in opt["drift_px"]]
                opt["dur"] = round(new, 3)
            changes.append({"shot": sid, "dur0": row["dur"], "dur1": round(new, 3),
                            "zoom0": z0[0] if z0 else None, "zoom1": z0[1] if z0 else None})
            row["dur"] = round(new, 3)
        if changes:
            chosen = {c["shot"]: next(x for x in o["shots"][c["shot"]]["options"]
                                      if x["n"] == (o["shots"][c["shot"]].get("choice") or {}).get("n", 1))
                      for c in changes}

            def put(raw):
                for sid, opt in chosen.items():
                    sp = (raw.get("shot_plan") or {}).get(sid)
                    if sp and sp.get("camera"):
                        sp["camera"]["zoom_pct"] = opt["zoom_pct"]
                        sp["camera"]["drift_px"] = opt["drift_px"]
            _write_film(d, put)
            shotnotes.write_atomic(opath(d), _dump(o))
    return changes


def line(sid: str, opt: dict, chosen: bool) -> str:
    e = "/".join(f"{x:.2f}".lstrip("0") for x in opt["ease"]) if opt.get("ease") else "-"
    dr = ",".join(f"{x:.0f}" for x in opt["drift_px"])
    ref = f"  ← {opt['ref']} ({opt['score']:.2f})" if opt.get("ref") and opt.get("score") is not None else (
        "  ← film" if opt.get("ref") == "film" else "  ← summary")
    mark = "*" if opt.get("recommended") else " "
    pick = "▶" if chosen else " "
    return (f"{pick}{sid:<4} {opt['n']}{mark} {opt['size']:<6} {opt['move']:<6} {opt['zoom_pct']:+.1f}% ease {e} "
            f"drift {dr}{ref}" + (f"  ! {opt['note']}" if opt.get("note") else ""))
