"""qc depth (specs/038 FR-012–FR-015, contracts/style-depth.md): each shot's camera and space against the reference.

One middle frame per shot (the animatic clip, else the built Blender clip, else a quarter-size Blender still), labelled
by the independent labeler (schema v3, with the measured lines), compared with the style's `depth.by_size`:
  depth_close    the shot came out tighter than shot_plan.size, or a long lens the reference hardly uses (< 10 %)
  depth_shallow  fewer layers than the reference's p25, or shallower than 75 % of the reference at that size
  card_angle     a Blender cast card turned more than 75° from the camera (plan pass, US3)
A size with fewer than 5 reference shots only warns (FR-015). Exceptions are per shot, with a reason, by the user only
(tiers.add_exception refuses inside a job, FR-014). gate() blocks `ae render` until the tier passes for this source."""
import hashlib
import json
import subprocess
from pathlib import Path

from filmcheck import labeler, stylerefs, tiers

TIER = "depth"
RULES = ("depth_close", "depth_shallow", "card_angle")
ORDER = ["ecu", "cu", "med", "wide", "huge"]
DEPTHS = ["shallow", "mid", "deep"]
MIN_N = 5
CARD_MAX = 75
SHARE_GAP = 0.10
FIX = {"depth_close": "move the camera back, or use a normal or wide lens",
       "depth_shallow": "add a foreground occluder, a far wall or a window (k.fg, a deeper set, a wider lens)",
       "card_angle": "turn the character towards the camera, or move the camera"}


class DepthError(Exception):
    """Cannot check (exit code 2): not an AE film, no depth block in the style, no frame for a shot."""


def _film(d: Path) -> dict:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from ae import film as filmdoc
    try:
        return filmdoc.require_ae(d)
    except filmdoc.FilmError as e:
        raise DepthError(e.message) from None


def style_depth(d: Path, doc: dict = None):
    """The style's depth block, or None. The style: film.json "style", else the film's treatment or channel."""
    slug = (doc or {}).get("style") or stylerefs.slug_of(d)
    if not slug:
        return None, None
    try:
        sg = json.loads((stylerefs.style_dir(d, slug) / "shots.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return slug, None
    dep = sg.get("depth") if isinstance(sg, dict) else None
    return slug, (dep if dep and dep.get("by_size") else None)


def fingerprint(d: Path, dep: dict) -> str:
    h = hashlib.sha256((tiers.fingerprint(d) + json.dumps(dep, sort_keys=True) + labeler.version()).encode())
    return h.hexdigest()[:16]


# ---------- rules (pure) ----------
def _issue(sid: str, rule: str, sev: str, have: dict, want: dict, **extra) -> dict:
    return {"ref": sid, "shot": sid, "rule": rule, "severity": sev, "have": have, "want": want, "fix": FIX[rule], **extra}


def rules(plans: dict, labels: dict, depth: dict, card_plans: dict) -> tuple:
    """plans {sid: shot_plan row}, labels {sid: label v3}, depth: the style block, card_plans {sid: plan.json}.
    Returns (issues, warnings)."""
    by = depth.get("by_size") or {}
    issues, warns, few = [], [], set()
    for sid, lab in labels.items():
        plan = plans.get(sid) or {}
        size = plan.get("size") or lab.get("scale")
        if size not in ORDER:
            continue
        want = by.get(size)
        if not want:
            few.add(size)
            continue
        sev = "block" if want.get("n", 0) >= MIN_N else "warn"
        if sev == "warn":
            few.add(size)
        got = lab.get("scale")
        long_share = (want.get("lens") or {}).get("long", 0)
        if got in ORDER and ORDER.index(got) < ORDER.index(size):
            issues.append(_issue(sid, "depth_close", sev, {"size": got}, {"size": size}))
        elif lab.get("lens") == "long" and long_share < 0.10:
            issues.append(_issue(sid, "depth_close", sev, {"lens": "long"}, {"lens_long_share": long_share}))
        n_lay = len(lab.get("layers") or [])
        dshare = want.get("depth") or {}
        d = lab.get("depth")
        at_or_below = sum(v for k, v in dshare.items() if k in DEPTHS and d in DEPTHS
                          and DEPTHS.index(k) <= DEPTHS.index(d))
        if n_lay < int(want.get("layers_p25") or 0):
            issues.append(_issue(sid, "depth_shallow", sev, {"layers": n_lay}, {"layers_p25": want["layers_p25"]}))
        elif d in DEPTHS and dshare and at_or_below < 0.25:
            issues.append(_issue(sid, "depth_shallow", sev, {"depth": d}, {"depth": dshare}))
    for sid, cp in (card_plans or {}).items():
        ang = (cp or {}).get("card_angle_max") or 0
        if ang > CARD_MAX:
            issues.append(_issue(sid, "card_angle", "block", {"card_angle_max": ang}, {"max": CARD_MAX}))
    for size in sorted(few, key=ORDER.index):
        warns.append({"rule": "few_samples", "size": size, "have": (by.get(size) or {}).get("n", 0), "want": MIN_N})
    total = sum(int(v.get("n") or 0) for v in by.values())
    sizes = [(plans.get(s) or {}).get("size") or labels[s].get("scale") for s in labels]
    sizes = [s for s in sizes if s in ORDER]
    if total and sizes:
        for size in ORDER:
            have = sizes.count(size) / len(sizes)
            ref = int((by.get(size) or {}).get("n") or 0) / total
            if abs(have - ref) > SHARE_GAP:
                warns.append({"rule": "size_share", "size": size, "have": round(have, 2), "want": round(ref, 2)})
    return issues, warns


# ---------- frames ----------
def _mid(clip: Path, dst: Path) -> bool:
    try:
        n = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v", "-show_entries",
                            "stream=nb_read_packets", "-of", "csv=p=0", str(clip)], capture_output=True, text=True,
                           timeout=60).stdout.strip()
        k = max(0, int(n or 1) // 2)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clip), "-vf", f"select=eq(n\\,{k})", "-frames:v", "1",
                        "-q:v", "3", str(dst)], check=True, timeout=120)
        return dst.is_file()
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def frames(d: Path, doc: dict, say=print) -> dict:
    """{sid: jpg}: animatic clip, else built Blender clip, else a quarter-size Blender still (GPU, local)."""
    out = d / ".check" / "depth"
    out.mkdir(parents=True, exist_ok=True)
    got, need_still = {}, []
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from ae import film as filmdoc
    for sid in doc["shots"]:
        dst = out / f"{sid}.jpg"
        clips = [d / "animatic" / "shots" / f"{sid}.mp4"]
        if filmdoc.engine_of(doc, sid) == "blender":
            clips += [d / "out" / "blender" / f"{sid}.mp4", d / "out" / "blender" / f"{sid}-quarter.mp4"]
        if any(c.is_file() and _mid(c, dst) for c in clips):
            got[sid] = dst
        elif filmdoc.engine_of(doc, sid) == "blender":
            need_still.append(sid)
        else:
            raise DepthError(f"{sid}: no frame to look at; make the animatic first: sh bin/studio ae draft {d.name}")
    if need_still:
        from blender import bundle, local, remote
        from blender.config import BlenderError
        try:
            fr = bundle.frames_of(d, doc, need_still)
            req = bundle.request(d, doc, need_still, quarter=True, still={s: max(1, fr[s] // 2) for s in need_still})
            say(f"  blender stills: {', '.join(need_still)}")
            r = (remote.build if remote.active() else local.build)(d, req)
        except BlenderError as e:
            raise DepthError(f"Blender stills: {e.message}") from None
        for sid, p in r["shots"].items():
            from PIL import Image
            Image.open(p).convert("RGB").save(out / f"{sid}.jpg", quality=90)
            got[sid] = out / f"{sid}.jpg"
    return got


def sheets(pics: dict, out: Path, per: int = 12) -> list:
    """Contact sheets for the labeler: 4 columns, each cell captioned with its shot id. [(sheet, [ids])]"""
    from PIL import Image, ImageDraw
    cw, ch, cap, cols = 480, 270, 28, 4
    ids = list(pics)
    groups = []
    for k in range(0, len(ids), per):
        part = ids[k:k + per]
        rows = (len(part) + cols - 1) // cols
        sh = Image.new("RGB", (cols * (cw + 6) + 6, rows * (ch + cap + 6) + 6), (17, 17, 17))
        dr = ImageDraw.Draw(sh)
        for j, sid in enumerate(part):
            x, y = 6 + (j % cols) * (cw + 6), 6 + (j // cols) * (ch + cap + 6)
            dr.text((x + 4, y + 6), sid, fill=(255, 230, 120))
            sh.paste(Image.open(pics[sid]).convert("RGB").resize((cw, ch)), (x, y + cap))
        p = out / f"depth-sheet-{k // per + 1}.jpg"
        sh.save(p, quality=90)
        groups.append((p, part))
    return groups


# ---------- the tier ----------
def _card_plans(d: Path, doc: dict) -> dict:
    out = {}
    for sid in doc["shots"]:
        p = d / "out" / "blender" / "plan" / f"{sid}.json"
        try:
            out[sid] = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return out


def _finish(d: Path, issues: list, warns: list, measures: dict, fp: str, seconds: float) -> dict:
    tiers.apply_exceptions(issues, tiers.load_exceptions(d))
    r = tiers.result(TIER, issues, measures, [], seconds, fp, warnings=warns)
    return tiers.save_tier(d, TIER, r)


def run(film_dir, say=print) -> dict:
    import time
    t0 = time.time()
    d = Path(film_dir)
    doc = _film(d)
    slug, dep = style_depth(d, doc)
    if not dep:
        raise DepthError(f"the style {slug or '(none)'} has no depth block; learn it again with the labeler v3 "
                         "(sh bin/studio learn …) before qc depth")
    fp = fingerprint(d, dep)
    lf = d / ".check" / "depth-labels.json"
    try:
        old = json.loads(lf.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        old = {}
    if old.get("fingerprint") == fp and old.get("labels"):
        labels, info = old["labels"], {"reused": True, "model": old.get("model")}
        say("  labels: reused")
    else:
        pics = frames(d, doc, say)
        groups = sheets(pics, d / ".check" / "depth")
        van = labeler.vanish_hints(pics)
        try:
            got = labeler.label(groups, {s: {"vanish": van.get(s)} for s in pics})
        except labeler.LabelError as e:
            raise DepthError(str(e)) from None
        labels = got["labels"]
        for s, v in van.items():
            if s in labels:
                labels[s]["vanish"] = v
                labels[s]["check"] = labeler.vanish_disagrees(labels[s], v)
        info = {"reused": False, "model": got["model"], "calls": got["calls"], "usage": got["usage"]}
        lf.write_text(json.dumps({"fingerprint": fp, "model": got["model"], "at": tiers.now(), "labels": labels},
                                 ensure_ascii=False), encoding="utf-8")
        say(f"  labels: {len(labels)} shots · {got['model']}")
    issues, warns = rules(doc.get("shot_plan") or {}, labels, dep, _card_plans(d, doc))
    return _finish(d, issues, warns, {"style": slug, "labels": info, "shots": labels}, fp, time.time() - t0)


def recompute(film_dir) -> dict:
    """After qc except: the stored issues again with the exceptions (no new labels)."""
    d = Path(film_dir)
    r = tiers.load_tier(d, TIER)
    if not r:
        return {}
    for i in r["issues"]:
        i.pop("excepted", None)
    return _finish(d, r["issues"], r.get("warnings") or [], r["measures"], r["fingerprint"], r.get("seconds", 0))


def gate(film_dir) -> list:
    """[] when `ae render` may run; else one reason per blocked shot, with the fix or the command to run."""
    d = Path(film_dir)
    try:
        doc = _film(d)
    except DepthError:
        return []
    _, dep = style_depth(d, doc)
    if not dep:
        return []                                   # nothing measured to compare with
    r = tiers.load_tier(d, TIER)
    if not r:
        return [f"qc depth has not run: sh bin/studio qc depth {d.name}"]
    if r.get("fingerprint") != fingerprint(d, dep):
        return [f"the film changed since qc depth: sh bin/studio qc depth {d.name}"]
    return [f"{i['shot']} {i['rule']}: have {json.dumps(i['have'])}, want {json.dumps(i['want'])} — {i['fix']}"
            for i in r["issues"] if i["severity"] == "block" and not i.get("excepted")]
