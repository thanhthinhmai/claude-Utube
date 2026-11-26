"""A film's sound plan: films/<film>/sound/plan.json (specs/037 US1, data-model, research R6).

Each sound (cue) is anchored to a motion of its shot (animatic/keys.json of 035), to a word of a line
(narration.json + voices/words.json), to a share of the shot, or spans the whole shot. `resolve()` turns anchors into
film times from the shot lengths in timing.json, so when the Animatic changes a shot's length every later time
follows (FR-003). A gone anchor makes the cue `dropped`, a sound not found makes it `missing`; nothing synthetic
takes its place (FR-007). Cues the user changed (`by: user`) are never removed by a new plan (FR-025).

Films without timing.json / keys.json (AE films made before 035) fall back on out/render-shots.json or shots.json
for shot lengths, and have no motion anchors (research R1)."""
import hashlib
import json
import math
import os
import re
from pathlib import Path

SOURCES = ("sonniss", "freesound", "user")
CUTS = ("hard", "fade", "over")
BYS = ("auto", "user", "claude")
MIN_GAP = 0.2                    # seconds between two point sounds (density, FR-005)
PER_MIN = 12                     # sounds per minute when the style has no measured rate
DEFAULT_GAIN = -6.0              # dB against the voice when the style has none
DEFAULT_RANGE = (-24.0, 6.0)     # edit.mix_ranges sfx_db
MAX_ALTS = 7
RANK = {"auto": 0, "claude": 1, "user": 2}


class PlanError(Exception):
    """code: changed | bad | missing | not_found | off."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


# ---------- files ----------
def plan_file(d: Path) -> Path:
    return Path(d) / "sound" / "plan.json"


def _read(f: Path, default=None):
    try:
        return json.loads(Path(f).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write(f: Path, data) -> None:
    """Writes only when the text changes, so reading a plan (resolve + save) leaves the file and its time alone."""
    text = json.dumps(data, indent=1, ensure_ascii=False) + "\n"
    try:
        if f.read_text(encoding="utf-8") == text:
            return
    except OSError:
        pass
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, f)


def style_sfx(d: Path) -> dict:
    """The style's measured sound rules (kit/template.json → sound.sfx, written by `learn sfx`), or {}."""
    d = Path(d)
    srcs = [d / "kit" / "template.json"]
    style = (_read(d / "film.json", {}) or {}).get("style")
    if isinstance(style, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]*", style):
        from filmcheck import soundlib
        sd = soundlib.repo() / "my-styles" / style
        srcs += [sd / "template.json", sd / "kit" / "template.json"]
    for f in srcs:
        sfx = ((_read(f, {}) or {}).get("sound") or {}).get("sfx")
        if sfx:
            return sfx
    return {}


def load(d: Path) -> dict:
    p = _read(plan_file(d))
    if not isinstance(p, dict):
        p = {"version": 1, "timing_sha": "", "profile": "style" if style_sfx(d) else "default", "cues": [], "silences": [], "off": []}
    p.setdefault("cues", [])
    p.setdefault("off", [])
    p.setdefault("silences", [])
    return p


def base(d: Path) -> str:
    """What the page and --base compare: a hash of plan.json as it is on disk."""
    try:
        raw = plan_file(d).read_bytes()
    except OSError:
        raw = b""
    return hashlib.sha1(raw).hexdigest()[:16]               # 16 characters, like every base the app sends


def _check_base(d: Path, b) -> None:
    if b and b != base(d):
        raise PlanError("changed", "the sound plan changed since you opened it: reload and try again")


def save(d: Path, plan: dict) -> None:
    keep = {k: plan[k] for k in ("version", "timing_sha", "profile", "cues", "silences", "off") if k in plan}
    keep["version"] = 1
    _write(plan_file(d), keep)


# ---------- the film's clock ----------
def timing(d: Path) -> dict:
    """{fps, shots: [id], frames: {id: n}, source}: timing.json (035), else render-shots.json / shots.json."""
    d = Path(d)
    film = _read(d / "film.json", {}) or {}
    t = _read(d / "timing.json")
    if isinstance(t, dict) and t.get("frames"):
        fps = t.get("fps") or film.get("fps") or 30
        shots = [s for s in film.get("shots") or [] if s in t["frames"]] or list(t["frames"])
        return {"fps": fps, "shots": shots, "frames": {s: int(t["frames"][s]) for s in shots}, "source": "timing.json"}
    for f in (d / "out" / "render-shots.json", d / "shots.json"):
        m = _read(f)
        if isinstance(m, dict) and m.get("shots"):
            fps = m.get("fps") or film.get("fps") or 30
            rows = [r for r in m["shots"] if len(r) >= 4 and r[3]]
            return {"fps": fps, "shots": [r[3] for r in rows],
                    "frames": {r[3]: int(round((r[1] - r[0]) * fps)) for r in rows}, "source": f.name}
    raise PlanError("missing", "no shot lengths yet: timing.json (Animatic) or a rendered film is needed")


def timing_sha(tm: dict) -> str:
    return hashlib.sha1(json.dumps(tm["frames"], sort_keys=True).encode()).hexdigest()[:12]


def starts(tm: dict) -> dict:
    out, n = {}, 0
    for s in tm["shots"]:
        out[s] = n / tm["fps"]
        n += tm["frames"][s]
    return out


def keys(d: Path) -> dict:
    return _read(Path(d) / "animatic" / "keys.json", None)


def motion_name(k: dict) -> str:
    return f"{k.get('layer', '')} · {k.get('prop', '')}"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("·", " · ")).strip().lower()


def narration(d: Path) -> dict:
    n = _read(Path(d) / "narration.json", {}) or {}
    return {ln["id"]: ln for ln in n.get("lines", []) if "id" in ln}


def words(d: Path) -> dict:
    d = Path(d)
    n = _read(d / "narration.json", {}) or {}
    for f in filter(None, [n.get("words_file"), "voices/words.json"]):
        w = _read(d / f)
        if isinstance(w, dict):
            return w
    return {}


def _word_t(ws: list, word: str, end: bool = False):
    """Start (or end) of a word in its line."""
    want = re.sub(r"[^\w']", "", word or "").lower()
    for w in ws or []:
        if re.sub(r"[^\w']", "", str(w[0])).lower() == want:
            return max(0.0, float(w[2] if end and len(w) > 2 else w[1]))
    return None


# ---------- resolve ----------
def _anchor_time(c: dict, tm: dict, t0: dict, ks, lines: dict, wds: dict):
    """(time in film or None, why). Times are not yet rounded."""
    a = c.get("anchor") or {}
    shot = c["shot"]
    length = tm["frames"][shot] / tm["fps"]
    off = (a.get("offset_f") or 0) / tm["fps"]
    if "motion" in a:
        if ks is None:
            return None, "no animatic keys yet (animatic/keys.json)"
        want = _norm(a["motion"])
        hit = next((k for k in ks.get(shot, []) if _norm(motion_name(k)) == want), None)
        if not hit:
            return None, f"motion '{a['motion']}' is not in {shot}'s keys any more"
        rel = float(hit["t1"] if a.get("edge") == "end" else hit["t0"]) + off
        if rel >= length:
            return None, f"motion '{a['motion']}' now starts after {shot} ends"
        return t0[shot] + max(0.0, rel), ""
    if "line" in a:
        ln = lines.get(a["line"])
        if not ln:
            return None, f"line {a['line']} is gone"
        at = float(ln.get("at", 0))
        if a.get("word"):
            wt = _word_t(wds.get(a["line"]), a["word"], end=a.get("edge") == "end")
            if wt is None:
                return None, f"word '{a['word']}' is not in line {a['line']} any more"
            at += wt
        return at + off, ""
    if "shot_at" in a:
        return t0[shot] + float(a["shot_at"]) * length + off, ""
    if a.get("span") == "shot":
        return t0[shot] + off, ""
    return None, "the cue has no anchor"


def _density(cues: list, per_min: float, film_len: float) -> None:
    """Drop the least important point sounds when two are closer than MIN_GAP or the film has more than per_min a
    minute: auto before claude, quieter before louder; a user's cue is never dropped (FR-005)."""
    pts = [c for c in cues if c["state"] == "placed" and (c.get("anchor") or {}).get("span") != "shot"]
    order = sorted(pts, key=lambda c: c["at"])
    for a, b in zip(order, order[1:]):
        if a["state"] != "placed" or b["state"] != "placed":
            continue
        if b["at"] - a["at"] < MIN_GAP - 1e-9:
            loser = min((a, b), key=lambda c: (RANK.get(c["by"], 0), c.get("gain_db", 0), -c["at"]))
            if loser["by"] != "user":
                loser.update(state="dropped", why="too dense")
    cap = max(1, math.ceil(per_min * max(film_len, 1.0) / 60.0))
    live = [c for c in pts if c["state"] == "placed"]
    if len(live) > cap:
        for c in sorted(live, key=lambda c: (RANK.get(c["by"], 0), c.get("gain_db", 0)))[:len(live) - cap]:
            if c["by"] != "user":
                c.update(state="dropped", why="too dense")


def resolve(d: Path, plan: dict = None, save: bool = False) -> dict:
    """Times for every cue and silence (rounded to a frame), states and reasons. → the plan + shots, t0, t1, fps."""
    d = Path(d)
    plan = plan or load(d)
    tm = timing(d)
    t0 = starts(tm)
    film_len = sum(tm["frames"].values()) / tm["fps"]
    ks, lines, wds = keys(d), narration(d), words(d)
    sfx = style_sfx(d)
    plan["profile"] = "style" if sfx else "default"
    plan["off"] = [s for s in tm["shots"] if s in set(plan.get("off") or [])]
    off = set(plan["off"])
    for c in plan["cues"]:
        c.pop("at", None)
        c.pop("why", None)
        if c["shot"] not in tm["frames"]:
            c.update(state="dropped", why=f"shot {c['shot']} is gone")
            continue
        at, why = _anchor_time(c, tm, t0, ks, lines, wds)
        if at is None:
            c.update(state="dropped", why=why)
            continue
        if at >= film_len:
            c.update(state="dropped", why="after the end of the film")
            continue
        c["at"] = round(round(at * tm["fps"]) / tm["fps"], 4)
        if c["shot"] in off:
            c.update(state="off", why=f"sound off for {c['shot']}")      # kept and timed, back when the shot is on
        elif not c.get("entry"):
            c.update(state="missing", why=f"no sound found for '{c.get('query', '')}'")
        else:
            c["state"] = "placed"
    _density(plan["cues"], float(sfx.get("per_min") or PER_MIN), film_len)
    for s in plan["silences"]:
        s.pop("at", None)
        if s["shot"] in tm["frames"]:
            fake = {"shot": s["shot"], "anchor": {"edge": "end", **s["anchor"]}}   # a silence follows its word
            at, _ = _anchor_time(fake, tm, t0, ks, lines, wds)
            if at is not None:
                s["at"] = round(round(at * tm["fps"]) / tm["fps"], 4)
    plan["timing_sha"] = timing_sha(tm)
    if save:
        globals()["save"](d, plan)
    return {**plan, "shots": tm["shots"], "fps": tm["fps"], "t0": t0,
            "t1": {s: t0[s] + tm["frames"][s] / tm["fps"] for s in tm["shots"]}, "length": film_len,
            "timing_source": tm["source"], "base": base(d)}


# ---------- changes ----------
def _next_id(plan: dict) -> str:
    n = max([int(c["id"][1:]) for c in plan["cues"] if re.fullmatch(r"c\d+", c.get("id", ""))] + [0])
    return f"c{n + 1:02d}"


def gain_range(d: Path):
    from filmcheck import edit
    return edit.mix_ranges(Path(d))["sfx_db"]


def _gain(d: Path, g) -> float:
    lo, hi = gain_range(d)
    if g is None:
        mid = style_sfx(d).get("gain_db")
        g = mid[1] if isinstance(mid, list) and len(mid) == 3 else DEFAULT_GAIN
    return round(min(hi, max(lo, float(g))), 1)


def _remember(d: Path, hit: dict) -> None:
    """Keep the text of a chosen sound next to its copy (sound/cache/index.json), for the mix's CREDITS and the page."""
    f = Path(d) / "sound" / "cache" / "index.json"
    idx = _read(f, {}) or {}
    idx[hit["id"]] = {k: hit.get(k) for k in ("name", "category", "duration", "source", "credit", "license", "url")}
    _write(f, idx)


def choose(d: Path, query: str, cat: str = None, dur: float = None, scope: str = "all"):
    """(entry, alts) for a query, the chosen sound copied into the film. (None, []) when nothing is found."""
    from filmcheck import soundlib
    try:
        hits = soundlib.find(query, cat, dur, scope)
    except soundlib.LibraryError:
        hits = []
    hits = [h for h in hits if h.get("source") in SOURCES]
    for h in hits:
        try:
            soundlib.cache(h["id"], d, scope)
        except soundlib.LibraryError:
            continue
        _remember(d, h)
        alts = [x["id"] for x in hits if x["id"] != h["id"]][:MAX_ALTS]
        idx = Path(d) / "sound" / "cache" / "alts.json"
        al = _read(idx, {}) or {}
        al.update({x["id"]: {k: x.get(k) for k in ("name", "category", "duration", "source", "credit", "license", "url")}
                   for x in hits})
        _write(idx, al)
        return h["id"], alts
    return None, []


def _check_anchor(anchor: dict) -> dict:
    if not isinstance(anchor, dict):
        raise PlanError("bad", "anchor: one of motion, line, shot_at, span")
    kinds = [k for k in ("motion", "line", "shot_at", "span") if k in anchor and anchor[k] not in (None, "")]
    if len(kinds) != 1:
        raise PlanError("bad", "anchor: exactly one of motion, line, shot_at, span")
    if "shot_at" in anchor and not 0 <= float(anchor["shot_at"]) < 1:
        raise PlanError("bad", "shot_at: a share of the shot, 0 … < 1")
    if anchor.get("span") not in (None, "shot"):
        raise PlanError("bad", 'span: "shot"')
    return anchor


def add_cue(d: Path, shot: str, action: str, anchor: dict, query: str, cat: str = None, len_s: float = None,
            gain_db: float = None, cut: str = None, fade_s: float = None, by: str = "claude", scope: str = "all",
            base_sha: str = None) -> dict:
    d = Path(d)
    _check_base(d, base_sha)
    tm = timing(d)
    if shot not in tm["frames"]:
        raise PlanError("bad", f"no shot {shot} in this film ({', '.join(tm['shots'])})")
    if by not in BYS:
        raise PlanError("bad", f"by: {', '.join(BYS)}")
    anchor = _check_anchor(dict(anchor))
    span = anchor.get("span") == "shot"
    cut = cut or ("hard" if span else "fade")
    if cut not in CUTS:
        raise PlanError("bad", f"cut: {', '.join(CUTS)}")
    plan = load(d)
    if shot in (plan.get("off") or []):
        raise PlanError("off", f"sound is off for {shot}: turn it on first (sound shot on <film> {shot})")
    dur = len_s or (tm["frames"][shot] / tm["fps"] if span else None)
    entry, alts = choose(d, query, cat, dur, scope)
    c = {"id": _next_id(plan), "shot": shot, "action": action.strip()[:120], "anchor": anchor, "query": query.strip()[:200],
         "cat": (cat or "").upper(), "entry": entry, "alts": alts, "len_s": len_s, "gain_db": _gain(d, gain_db),
         "cut": cut, **({"fade_s": round(float(fade_s or 0.15), 3)} if cut == "fade" else {}), "by": by,
         "state": "placed" if entry else "missing"}
    plan["cues"].append(c)
    r = resolve(d, plan, save=True)
    return next(x for x in r["cues"] if x["id"] == c["id"])


def set_cue(d: Path, cue: str, fields: dict, by: str = "user", base: str = None, scope: str = "all") -> dict:
    d = Path(d)
    _check_base(d, base)
    plan = load(d)
    c = next((x for x in plan["cues"] if x["id"] == cue), None)
    if not c:
        raise PlanError("not_found", f"no cue {cue}")
    for k, v in fields.items():
        if k == "entry":
            from filmcheck import soundlib
            try:
                soundlib.cache(v, d, scope)
                hit = soundlib.get(v, scope) if not soundlib.via_proxy() else {"id": v}
            except soundlib.LibraryError as e:
                raise PlanError("bad" if e.code != "scope" else "scope", e.message) from None
            if hit.get("source") and hit["source"] not in SOURCES:
                raise PlanError("bad", "this sound's source is not allowed")
            if "name" in hit:
                _remember(d, soundlib.public(hit) if "path" in hit else hit)
            if c.get("entry") and c["entry"] != v and c["entry"] not in c["alts"]:
                c["alts"] = ([c["entry"]] + c["alts"])[:MAX_ALTS]
            c["alts"] = [a for a in c["alts"] if a != v][:MAX_ALTS]
            c["entry"] = v
        elif k == "offset_f":
            c["anchor"] = {**c["anchor"], "offset_f": int(v)}
        elif k == "gain_db":
            c["gain_db"] = _gain(d, v)
        elif k == "cut":
            if v not in CUTS:
                raise PlanError("bad", f"cut: {', '.join(CUTS)}")
            c["cut"] = v
            if v == "fade":
                c.setdefault("fade_s", 0.15)
            else:
                c.pop("fade_s", None)
        elif k == "fade_s":
            c["fade_s"] = round(max(0.01, min(3.0, float(v))), 3)
        elif k == "len_s":
            c["len_s"] = None if v in (None, 0) else round(max(0.05, float(v)), 3)
        else:
            raise PlanError("bad", f"cannot change {k}")
    c["by"] = by if by in BYS else "user"
    r = resolve(d, plan, save=True)
    return next(x for x in r["cues"] if x["id"] == cue)


def set_shots(d: Path, shots: list, on: bool, base: str = None) -> dict:
    """Turn the sound effects of whole shots off or back on. An off shot keeps its cues (state "off", not mixed) and
    takes no new ones; voice, music and chosen silences are not touched."""
    d = Path(d)
    _check_base(d, base)
    tm = timing(d)
    bad = [s for s in shots if s not in tm["frames"]]
    if bad or not shots:
        raise PlanError("bad", f"no shot {', '.join(bad) or '-'} in this film ({', '.join(tm['shots'])})")
    plan = load(d)
    off = set(plan.get("off") or [])
    off = off - set(shots) if on else off | set(shots)
    plan["off"] = [s for s in tm["shots"] if s in off]
    return resolve(d, plan, save=True)


def rm_cue(d: Path, cue: str, base: str = None) -> None:
    d = Path(d)
    _check_base(d, base)
    plan = load(d)
    if not any(c["id"] == cue for c in plan["cues"]):
        raise PlanError("not_found", f"no cue {cue}")
    plan["cues"] = [c for c in plan["cues"] if c["id"] != cue]
    resolve(d, plan, save=True)


def add_silence(d: Path, shot: str, anchor: dict, len_s: float, db: float = -57.0) -> dict:
    d = Path(d)
    tm = timing(d)
    if shot not in tm["frames"]:
        raise PlanError("bad", f"no shot {shot} in this film")
    if not 0.05 <= float(len_s) <= 10:
        raise PlanError("bad", "len: 0.05 … 10 s")
    plan = load(d)
    s = {"shot": shot, "anchor": dict(anchor), "len_s": round(float(len_s), 3), "db": round(min(0.0, float(db)), 1)}
    plan["silences"].append(s)
    r = resolve(d, plan, save=True)
    return r["silences"][-1]
