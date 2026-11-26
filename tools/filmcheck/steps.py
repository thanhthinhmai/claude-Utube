"""The ten steps of a film and what a change makes run again (specs/026, data-model "Step"). Standard library only."""
import json
import time
from pathlib import Path

from filmcheck import points, report, tiers

STEPS = ["Treatment", "Script", "Cast", "Voice", "Animatic", "Look", "Picture", "Shots", "Mix", "Render", "Self-check",
         "Publish"]
GRAPH = {"Script": ["Cast", "Voice"], "Cast": ["Picture", "Animatic"], "Voice": ["Animatic", "Picture", "Mix"],
         "Animatic": ["Mix", "Render"], "Look": ["Picture"], "Picture": ["Shots"], "Shots": ["Render"], "Mix": ["Self-check"],
         "Render": ["Self-check"], "Self-check": ["Publish"], "Publish": []}
POINT_STEP = {"script": "Script", "cast": "Cast", "voice": "Voice", "animatic": "Animatic", "shots": "Shots", "mix": "Mix",
              "publish": "Publish"}
STEP_POINT = {v: k for k, v in POINT_STEP.items()}
AE_ONLY = ("Cast", "Animatic")                      # web page films have neither (specs/034, 035)
WEB_ONLY = ("Look", "Picture", "Shots")             # AE films draw in After Effects and review the animatic
AE_LABEL = {"Mix": "Sound", "Render": "Final render"}
AE_GRAPH = {**GRAPH, "Mix": ["Render", "Self-check"]}   # AE films: the Sound comes before the final render (specs/037)


def hidden(film_dir) -> tuple:
    """The steps this film does not have."""
    return WEB_ONLY if points.is_ae(Path(film_dir)) else AE_ONLY


def after(step: str, film_dir=None) -> list:
    """Every step that depends on this one, in film order (only the film's own steps when film_dir is given)."""
    g = GRAPH
    if film_dir is not None:
        hide = hidden(film_dir)
        g = AE_GRAPH if points.is_ae(Path(film_dir)) else GRAPH
    seen, todo = set(), list(g.get(step, []))
    while todo:
        s = todo.pop()
        if s not in seen:
            seen.add(s)
            todo += g.get(s, [])
    if film_dir is not None:
        return [s for s in STEPS if s in seen and s not in hide]
    return [s for s in STEPS if s in seen]


def impact(point: str, film_dir=None) -> list:
    """The steps that must run again when this point's work changes ("If you change this")."""
    return after(POINT_STEP[points.check_point(point)], film_dir)


def _mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


def _iso_time(s) -> float:
    try:
        return time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone
    except (TypeError, ValueError):
        return 0.0


def voice_problem(d: Path):
    """None when every voice line says the script and has its file; else why the voice must run again."""
    lines = d / "lines.json"
    if not lines.is_file() or not (d / "SCRIPT.md").is_file():
        return None
    try:
        rows = [r for r in json.loads(lines.read_text(encoding="utf-8")) if isinstance(r, dict)]
    except (OSError, ValueError):
        return "lines.json cannot be read"
    from filmcheck import qc, script
    try:
        sc = script.read_script(d / "SCRIPT.md")
    except script.ScriptError:
        return None
    said = [w for p in sc["paragraphs"] for w in qc.norm_words(p["text"])]
    voice = [w for r in rows for w in qc.norm_words(r.get("text", ""))]
    if said != voice:
        return "the voice lines do not say the current script"
    missing = [r["id"] for r in rows if r.get("id") and not (d / "voices" / f"{r['id']}.wav").is_file()]
    return f"{len(missing)} line(s) have no voice file" if missing else None


def _tier_state(d: Path, name: str, fp: str):
    t = tiers.load_tier(d, name)
    if not t:
        return None
    return "stale" if t.get("fingerprint") != fp else "done"


def cast_state(d: Path) -> tuple:
    """Cast step (AE films, specs/034): skipped · todo (no cast.json, or a character without sheet) · done."""
    why = points.cast_skip_reason(d)
    if why:
        return ("skipped", why)
    from filmcheck import cast
    if not cast.exists(d):
        return ("todo", "")
    try:
        doc = cast.load(d)
    except cast.CastError as e:
        return ("stale", e.message)
    missing = [c["id"] for c in doc["characters"] if not cast.has_sheet(d, c["id"])]
    return ("todo", f"no sheet: {', '.join(missing)}") if missing else ("done", "")


def animatic_state(d: Path) -> tuple:
    """Animatic step (AE films, specs/035): todo (no current draft) · done · stale (the draft is older than the shot
    lengths, the narration or the film's code)."""
    from filmcheck import animatic
    return animatic.step_state(d)


def base_states(film_dir: Path) -> dict:
    """{step: (state, note)} from the film's files only: done · todo · stale · skipped."""
    d = Path(film_dir)
    data = report.load(d)
    fp = tiers.fingerprint(d)
    out = {}
    out["Treatment"] = ("done", "") if (d / "TREATMENT.md").is_file() else ("todo", "")
    if (data.get("script") or {}).get("verdict") == "skipped":
        out["Script"] = ("skipped", "no narration")
        out["Voice"] = ("skipped", "no narration")
    else:
        out["Script"] = ("done", "") if (d / "SCRIPT.md").is_file() else ("todo", "")
        if (d / "voices").is_dir() and any((d / "voices").glob("*.wav")):
            why = voice_problem(d)
            out["Voice"] = ("stale", why) if why else ("done", "")
        else:
            out["Voice"] = ("todo", "")
    out["Cast"] = cast_state(d)
    out["Animatic"] = animatic_state(d) if points.is_ae(d) else ("skipped", "not an After Effects film")
    out["Look"] = ("done", "") if (d / "index.html").is_file() else ("todo", "")
    out["Picture"] = (_tier_state(d, "plan", fp) or "todo", "")
    out["Shots"] = (_tier_state(d, "shots", fp) or "todo", "")
    mix = d / "out" / "mix.wav"
    if mix.is_file():
        inputs = [d / "mix.json", d / "narration.json"] + sorted((d / "voices").glob("*.wav"))
        if points.is_ae(d):                          # specs/037: the sound plan and the Animatic's shot lengths
            inputs += [d / "sound" / "plan.json", d / "timing.json"]
        out["Mix"] = ("stale", "older than its inputs") if any(_mtime(p) > _mtime(mix) for p in inputs) else ("done", "")
    else:
        out["Mix"] = ("todo", "")
    video = d / "out" / "video.mp4"
    r = _tier_state(d, "render", fp)
    if r or video.is_file():
        if r == "stale":
            out["Render"] = ("stale", "the picture changed")
        elif mix.is_file() and video.is_file() and _mtime(mix) > _mtime(video):
            out["Render"] = ("stale", "the sound must be put back on the video")
        else:
            out["Render"] = ("done", "")
    else:
        out["Render"] = ("todo", "")
    f = _tier_state(d, "final", fp)
    if f:
        final_at = _iso_time((tiers.load_tier(d, "final") or {}).get("at"))
        out["Self-check"] = ("stale", "") if f == "stale" or (video.is_file() and _mtime(video) > final_at + 1) else ("done", "")
    else:
        out["Self-check"] = ("todo", "")
    pub = data.get("publish")
    if pub:
        at = _iso_time(pub.get("at"))
        newer = _mtime(d / "publish" / "pack.json") > at + 1 or _mtime(video) > at + 1
        out["Publish"] = ("stale", "") if newer else ("done", "")
    else:
        out["Publish"] = ("todo", "")
    return out


def status(film_dir: Path, job_step: str = None, pending: set = frozenset(), busy: dict = None) -> list:
    """[{name, state, note, point}] for the step rail: base states, then the job's own step (running), the review
    points that wait (waiting), the busy lock (running) and stale steps after a change (data-model)."""
    d = Path(film_dir)
    base = base_states(d)
    pst = points.status(d, pending)
    out = []
    ae = points.is_ae(d)
    hide = WEB_ONLY if ae else AE_ONLY
    for name in STEPS:
        if name in hide:
            continue                     # each kind of film shows only its own steps (specs/034, 035)
        state, note = base[name]
        pt = STEP_POINT.get(name)
        info = pst.get(pt) if pt else None
        if info:
            if info["state"] == "waiting":
                state, note = "waiting", "Review now"
            elif info["state"] == "approved" and state == "done":
                note = "Approved"
            elif info["state"] == "off" and state == "done":
                note = "Not reviewed"
        if busy and busy.get("step") == name:
            state, note = "running", "Busy"
        elif job_step and job_step == name and state != "waiting":
            state = "running"
        out.append({"name": name, "label": AE_LABEL.get(name, name) if ae else name, "state": state, "base": base[name][0], "note": note, "point": pt,
                    "review_on": bool(info and info["on"]),
                    "approved_at": info["approved_at"] if info and info["state"] == "approved" else None})
    return out
