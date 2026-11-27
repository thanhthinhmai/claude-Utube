"""The cast pass of Blender shots (specs/038 T046, research R6): before a Blender shot with characters is drawn,
1. the plan pass (Blender, no render) measures each character's angle to the camera, height on screen and state per
   frame (tools/blender/kit/cards.py measure → plan.json);
2. tools/blender/layers.py turns that into layers/<shot>/layers.json (views, track, size);
3. the layers pass (After Effects, kit/castlayer.jsx) draws every (character, view) as transparent PNG frames in
   layers/<shot>/<char>-<view>/, which the render pass puts on cards.
A shot whose layers.json is unchanged and whose layer folders are complete is not drawn again. The layers folder is
part of the Blender shot's version (blender/bundle.py), so a change of rig, pose or path draws the shot again."""
import json
import re
from pathlib import Path

CAST_CALL = re.compile(r"\bk\.(cast|crowd)\s*\(")
MIN_PX = 256
# crowd actions → rig poses, alternated every ACT_STEP frames so a crowd moves (rig ball@1 has no sit or clap pose)
CROWD_POSES = {"sit": ["lap"], "clap": ["chest", "both"], "cheer": ["both", "raise"], "wave": ["wave", "down"],
               "stand": ["down"], "point": ["pointR"], "look": ["down"]}
ACT_STEP = 8


def cast_shots(code: Path, shots: list) -> list:
    out = []
    for s in shots:
        p = Path(code) / "blender" / f"{s}.py"
        if p.is_file() and CAST_CALL.search(p.read_text(encoding="utf-8")):
            out.append(s)
    return out


def _cast(code: Path) -> dict:
    from ae import bundle
    return {c["id"]: c for c in bundle.cast_doc(code).get("characters", []) if isinstance(c, dict) and c.get("id")}


def pool_of(cast: dict, used: set, n: int) -> list:
    """Crowd layers: members of group characters first ("<id>.<i>"), then single characters not acted in the shot."""
    out = []
    for cid, c in cast.items():
        if c.get("kind") == "group":
            out += [f"{cid}.{i}" for i in range(len(c.get("members") or []))]
    out += [cid for cid, c in cast.items() if c.get("kind") != "group" and cid not in used]
    return out[:n]


def _split(name: str) -> tuple:
    cid, _, m = name.partition(".")
    return cid, (int(m) if m.isdigit() else None)


def crowd_track(action: str, frames: int) -> list:
    poses = CROWD_POSES.get(action, ["down"])
    return [{"f": f, "view": "front", "dir": 1, "pose": poses[(f - 1) // ACT_STEP % len(poses)]}
            for f in range(1, frames + 1, ACT_STEP if len(poses) > 1 else frames)]


def ae_plan(doc_layers: dict, crowd_px: int = 540) -> list:
    """The jobs of one shot for kit/castlayer.jsx."""
    from blender import layers
    shot, frames = doc_layers["shot"], doc_layers["frames"]
    chars = {c["id"]: c for c in doc_layers["chars"]}
    acts = (doc_layers.get("crowd") or {}).get("actions") or ["sit"]
    jobs = []
    for i, (name, view) in enumerate(layers.jobs(doc_layers)):
        cid, member = _split(name)
        if name in chars:
            c = chars[name]
            size, track = max(MIN_PX, c["height_px"]), c["track"]
        else:                                                  # a crowd layer
            size, track = crowd_px, crowd_track(acts[i % len(acts)], frames)
        jobs.append({"name": f"L-{shot}-{name}-{view}", "shot": shot, "layer": name, "char": cid, "member": member,
                     "view": view,
                     "frames": frames, "size": size + size % 2, "track": track})
    return jobs


def complete(code: Path, doc_layers: dict) -> bool:
    from blender import layers
    base = Path(code) / "layers" / doc_layers["shot"]
    for name, view in layers.jobs(doc_layers):
        if len(list((base / f"{name}-{view}").glob("f*.png"))) < doc_layers["frames"]:
            return False
    return True


def run(code, doc: dict, shots: list, progress=None, say=print, blender_build=None, ae_layers=None) -> list:
    """Measure, plan and draw the cast layers of these Blender shots; returns the shots whose layers were drawn."""
    from blender import bundle, layers
    code = Path(code)
    todo = cast_shots(code, shots)
    if not todo:
        return []
    if blender_build is None:
        from ae import mixed
        blender_build = mixed.blender_runner()
    if ae_layers is None:
        from ae import local
        ae_layers = local.build_layers
    req = bundle.request(code, doc, todo, kind="plan")
    for row in req["shots"]:
        row.pop("layers", None)                                # the plan pass does not read the layers
    say(f"cast: measuring {', '.join(todo)}")
    r = blender_build(code, req, progress=progress)
    cast = _cast(code)
    jobs, docs = [], {}
    for s in todo:
        plan = json.loads(Path(r["shots"][s]).read_text(encoding="utf-8"))
        chars = plan.get("chars") or {}
        miss = [c for c in chars if c not in cast]
        if miss:
            from blender.config import BlenderError
            raise BlenderError("layers", f"{s}: {', '.join(miss)} not in cast/cast.json")
        for cid, v in chars.items():
            v["rig"] = cast[cid].get("rig") or ""
        crowd = plan.get("crowd")
        pool = pool_of(cast, set(chars), layers.CROWD_POOL) if crowd else None
        d = layers.plan_doc(s, int(plan["fps"]), int(plan["frames"]), chars, crowd, pool)
        p = code / "layers" / s / "layers.json"
        old = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None
        docs[s] = d
        if old == d and complete(code, d):
            continue
        jobs += ae_plan(d)
    drawn = sorted({j["shot"] for j in jobs})
    if jobs:
        say(f"cast: After Effects draws {len(jobs)} layer(s) for {', '.join(drawn)}")
        ae_layers(code, {"fps": int(doc["fps"]), "jobs": jobs}, code / "layers", progress=progress)
    for s, d in docs.items():
        p = code / "layers" / s / "layers.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d, indent=1), encoding="utf-8")
    return drawn
