"""A film whose shots are drawn by After Effects or Blender (specs/038 T019, constitution 4.0.0 VII).

build() is a drop-in for the AE runner (local.build / remote.build): same arguments, same result
{master, marks, duration, checks, keys, dir, log}, plus engines {shot: {engine, version, gpu}}. A film without
Blender shots goes straight to the AE runner with the arguments it got, so its bundle and video stay as in 032
(SC-009). A mixed film: AE shots in one MASTER, Blender shots each in its own S<n>.mp4 (skipped when built before
with the same version), then splice.assemble() joins them on timing.json's frames."""
import hashlib
import json
import os
from pathlib import Path

from ae import film as filmdoc, splice


def in_job() -> bool:
    return bool(os.environ.get("STUDIO_JOB") and os.environ.get("STUDIO_PROXY")) and os.environ.get("STUDIO_AE_LOCAL") != "1"


def ae_runner():
    if in_job():
        from ae import remote
        return remote.build
    from ae import local
    return local.build


def blender_runner():
    from blender import local, remote
    return remote.build if remote.active() and os.environ.get("STUDIO_BLENDER_LOCAL") != "1" else local.build


def state_path(code: Path, draft: bool) -> Path:
    return Path(code) / "out" / "blender" / ("state-quarter.json" if draft else "state.json")


def load_state(code: Path, draft: bool) -> dict:
    try:
        return json.loads(state_path(code, draft).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def ae_version(code: Path) -> str:
    """Fingerprint of the film's own AE code (the shared kit is tracked by ae uses)."""
    h = hashlib.sha1()
    for p in sorted((Path(code) / "ae").glob("*.jsx")):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def plan_status(code: Path, doc: dict, shots=None) -> dict:
    """{shot: {"engine", "version", "built", "stale"}} for Blender shots: stale when built with another version."""
    from blender import bundle, uses
    shots = filmdoc.blender_shots(doc, shots)
    out = {}
    if not shots:
        return out
    try:
        frames = bundle.frames_of(code, doc, shots)
    except Exception:          # noqa: BLE001 — no timing yet: nothing built, nothing stale
        return {s: {"engine": "blender", "version": "", "built": "", "stale": False} for s in shots}
    st, g = load_state(code, False), uses.kit_graph()
    for s in shots:
        v = bundle.version(code, doc, s, frames[s], g)
        built = (st.get(s) or {}).get("version", "")
        out[s] = {"engine": "blender", "version": v, "built": built, "stale": bool(built) and built != v}
    return out


def blender_part(code: Path, doc: dict, shots: list, draft: bool = False, progress=None, say=print,
                 force: bool = False) -> dict:
    """Render the Blender shots whose version changed; {shot: {"clip", "version", "gpu"}} for all of them."""
    from blender import bundle, uses
    if not shots:
        return {}
    frames = bundle.frames_of(code, doc, shots)
    from ae import castpass                                  # specs/038 US3: cast layers first, they are in the version
    castpass.run(code, doc, shots, progress=progress, say=say)
    g = uses.kit_graph()
    st = load_state(code, draft)
    vers = {s: bundle.version(code, doc, s, frames[s], g) for s in shots}
    todo = [s for s in shots if force or (st.get(s) or {}).get("version") != vers[s]
            or not Path((st.get(s) or {}).get("clip", "")).is_file()]
    skipped = [s for s in shots if s not in todo]
    if skipped:
        say(f"blender: {', '.join(skipped)} unchanged, kept")
    if todo:
        req = bundle.request(code, doc, todo, quarter=draft)
        r = blender_runner()(code, req, progress=progress)
        for s in todo:
            st[s] = {"version": vers[s], "clip": r["shots"][s], "gpu": r.get("gpu", ""), "frames": frames[s]}
        p = state_path(code, draft)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(st, indent=1))
    return {s: {"clip": st[s]["clip"], "version": vers[s], "gpu": st[s].get("gpu", "")} for s in shots}


def estimate(code: Path, doc: dict, shots: list, draft: bool) -> str:
    from blender import bundle, estimate as est
    bl = filmdoc.blender_shots(doc, shots)
    frames = bundle.frames_of(code, doc, bl) if bl else {}
    st = load_state(code, draft)
    todo = sum(n for s, n in frames.items() if (st.get(s) or {}).get("version") is None
               or not Path((st.get(s) or {}).get("clip", "")).is_file()
               or (st.get(s) or {}).get("version") != bundle.version(code, doc, s, n))
    return est.line(todo, len([s for s in shots if s not in bl]), quarter=draft)


def build(code, shots=None, progress=None, draft: bool = False, say=print, **kw) -> dict:
    code = Path(code)
    doc = filmdoc.require_ae(code)
    run_ae = ae_runner()
    if kw.get("sheet"):                                   # a cast sheet is drawn by After Effects alone, not the film's shots
        return run_ae(code, None, progress=progress, **kw)
    picked = filmdoc.pick_shots(doc, shots)
    bl = filmdoc.blender_shots(doc, picked)
    if not bl:                                            # 032 path, same arguments as before
        if draft:
            return run_ae(code, shots, progress=progress, draft=True, **kw)
        return run_ae(code, shots, progress=progress, **kw)
    filmdoc.validate_plan(code, doc, bl)
    from blender import bundle
    frames = bundle.frames_of(code, doc, picked)
    say(estimate(code, doc, picked, draft))
    ae = [s for s in picked if s not in bl]
    r = {"checks": [], "keys": {}, "marks": [], "log": ""}
    if ae:
        r = run_ae(code, ae, progress=progress, draft=True, **kw) if draft else run_ae(code, ae, progress=progress, **kw)
    blend = blender_part(code, doc, bl, draft=draft, progress=progress, say=say)
    by = {str(m[3]): m for m in r.get("marks") or []}
    if ae:
        v = splice.probe(r["master"])
        size = (v["w"], v["h"])
    else:
        size = tuple(doc["size"]) if not draft else (doc["size"][0] // 4 // 2 * 2, doc["size"][1] // 4 // 2 * 2)
    segs = []
    for s in picked:
        if s in blend:
            segs.append({"shot": s, "clip": blend[s]["clip"], "start": 0, "frames": frames[s],
                         "set": (doc["shot_plan"].get(s) or {}).get("set", "")})
        else:
            if s not in by:
                raise splice.SpliceError(f"the AE build did not make {s}")
            segs.append({"shot": s, "clip": r["master"], "start": float(by[s][0]), "frames": frames[s],
                         "set": by[s][2] if len(by[s]) > 2 else ""})
    trans = {s: (doc["shot_plan"].get(s) or {}).get("transition") for s in picked}
    trans = {s: t for s, t in trans.items() if t and t != "cut"}
    out = code / "out" / ("mixed-draft.mp4" if draft else "mixed.mp4")
    res = splice.assemble(segs, out, doc["fps"], size, trans)
    av = ae_version(code)
    engines = {s: ({"engine": "blender", "version": blend[s]["version"], "gpu": blend[s]["gpu"]} if s in blend
                   else {"engine": "ae", "version": av}) for s in picked}
    return {"master": res["out"], "marks": res["marks"], "duration": res["duration"], "checks": r.get("checks") or [],
            "keys": r.get("keys") or {}, "dir": str(out.parent), "log": r.get("log", ""), "engines": engines,
            "source": "mixed"}


def fix_pieces(code: Path, doc: dict, shots: list, build_ae, progress=None, say=print) -> tuple:
    """For ae fix: {shot: (clip, start second)} of the rebuilt shots of either engine, plus the AE result."""
    bl = filmdoc.blender_shots(doc, shots)
    filmdoc.validate_plan(code, doc, bl)
    ae = [s for s in shots if s not in bl]
    pieces, r = {}, {"checks": [], "marks": []}
    if ae:
        r = build_ae(code, ae)
        pieces.update(splice.pieces_from_master(r["master"], r["marks"], ae))
    for s, b in blender_part(code, doc, bl, progress=progress, say=say, force=False).items():
        pieces[s] = (b["clip"], 0.0)
    return pieces, r
