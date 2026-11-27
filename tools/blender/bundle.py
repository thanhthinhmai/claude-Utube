"""What a Blender run is made of (specs/038 T018): the request of a film's Blender shots and each shot's version.

request.json (contracts/bridge-api.md) lists, for each shot, its frames (from timing.json, so both engines cut on the
same frame), its script blender/S<n>.py, its layers folder (cast cards, specs/038 US3) and its shot_plan entry.
A shot's version is a hash of everything its frames depend on: the script, the kit files it uses (uses.files_of),
its layers, its shot_plan entry, fps, size and length. A shot already built whose version is unchanged is skipped;
a changed one is listed "Must run again" by ae status (FR-016)."""
import hashlib
import json
from pathlib import Path

from blender import uses
from blender.config import BlenderError


def frames_of(film_dir, doc: dict, shots: list) -> dict:
    """{shot: frames} from timing.json; Blender shots cannot be drawn before the film has shot lengths."""
    from filmcheck import timing
    try:
        t = timing.load(Path(film_dir))
    except timing.TimingError as e:
        raise BlenderError("bad_plan", f"timing.json: {e.message}") from None
    if t is None:
        raise BlenderError("bad_plan", "the film has no timing.json yet; Blender shots take their length from it "
                                       "(make the animatic first: sh bin/studio ae draft <film>)")
    if int(t["fps"]) != int(doc["fps"]):
        raise BlenderError("bad_plan", f"timing.json is at {t['fps']} fps, film.json at {doc['fps']}")
    miss = [s for s in shots if s not in t["frames"]]
    if miss:
        raise BlenderError("bad_plan", f"timing.json has no length for {', '.join(miss)}")
    return {s: int(t["frames"][s]) for s in shots}


def _hash_path(h, p: Path) -> None:
    if p.is_file():
        h.update(p.read_bytes())
    elif p.is_dir():
        for q in sorted(p.rglob("*")):
            if q.is_file():
                h.update(str(q.relative_to(p)).encode())
                h.update(q.read_bytes())


def version(film_dir, doc: dict, shot: str, frames: int, g: dict = None) -> str:
    d = Path(film_dir)
    script = d / "blender" / f"{shot}.py"
    h = hashlib.sha1()
    plan = (doc.get("shot_plan") or {}).get(shot) or {}
    keep = {k: v for k, v in plan.items() if k not in ("suggested", "reason")}     # advice does not change frames
    h.update(json.dumps({"fps": doc["fps"], "size": doc["size"], "frames": frames, "plan": keep}, sort_keys=True).encode())
    h.update(script.read_bytes() if script.is_file() else b"")
    for f in (uses.files_of(script, g) if script.is_file() else []):
        h.update(f.encode())
        h.update((uses.KIT / f).read_bytes())
    _hash_path(h, d / "layers" / shot)
    return h.hexdigest()[:12]


def request(film_dir, doc: dict, shots: list, kind: str = "render", quarter: bool = False, still: dict = None) -> dict:
    d = Path(film_dir)
    frames = frames_of(d, doc, shots)
    plans = doc.get("shot_plan") or {}
    rows = []
    for s in shots:
        if not (d / "blender" / f"{s}.py").is_file():
            raise BlenderError("bad_plan", f"{s}: blender/{s}.py is missing")
        row = {"id": s, "frames": frames[s], "script": f"blender/{s}.py"}
        if (d / "layers" / s).is_dir():
            row["layers"] = f"layers/{s}"
        if plans.get(s):
            row["plan"] = plans[s]
        if (still or {}).get(s):
            row["still"] = int(still[s])
        rows.append(row)
    return {"kind": kind, "film": d.name, "fps": int(doc["fps"]), "size": list(doc["size"]), "quarter": bool(quarter),
            "shots": rows}
