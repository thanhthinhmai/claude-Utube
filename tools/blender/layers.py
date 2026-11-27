"""The layers plan of cast cards (specs/038 T042, data-model "Layers plan", research R6). Pure: runs on the host on
what the Blender plan pass measured per frame, and writes layers/<shot>/layers.json for the AE layers pass.

A sample per frame and character: {f, rel, height_px, elev, pose?, expr?, walk?}
  rel        signed angle (degrees) between where the character faces and where the camera is, seen from above:
             0 the character faces the camera, ±180 its back is to the camera, sign = which side
  height_px  the character's height on screen
  elev       the camera's angle above the character's middle: the card turns about its upright axis only, so this is
             how much the camera sees the card at a slant (card_angle, > 75 blocks in qc depth)"""
import json
from pathlib import Path

FRONT_MAX = 30          # |rel| up to this: the rig's front view
BACK_MIN = 100          # |rel| from this: the back view; between the two: the 3/4 view, dir = side. The rig's 3/4
                        # view faces the camera, so past 100° (walking away) it read as walking backwards
HYST = 15               # a view changes only 15° past its bound, so the card does not flicker
MAX_PX = 1080
CROWD_POOL = 4
STATE = ("pose", "expr", "walk")


def _raw(rel: float) -> tuple:
    a = abs(rel)
    if a <= FRONT_MAX:
        return "front", 1
    if a >= BACK_MIN:
        return "back", 1
    return "34", (1 if rel >= 0 else -1)


def view_of(rel: float, prev: tuple = None) -> tuple:
    """(view, dir) of the rig for this angle, keeping prev while within HYST past the bound."""
    rel = ((rel + 180) % 360) - 180
    if prev is None:
        return _raw(rel)
    v, d = prev
    a = abs(rel)
    if v == "front" and a <= FRONT_MAX + HYST:
        return prev
    if v == "back" and a >= BACK_MIN - HYST:
        return prev
    if v == "34" and FRONT_MAX - HYST < a < BACK_MIN + HYST:
        side = 1 if rel >= 0 else -1
        if side != d and a > HYST:          # turned past the middle to the other side
            return "34", side
        return prev
    return _raw(rel)


def char_plan(cid: str, rig: str, samples: list) -> dict:
    track, views, prev, last = [], [], None, None
    for s in sorted(samples, key=lambda x: x["f"]):
        prev = view_of(s.get("rel", 0), prev)
        st = {"view": prev[0], "dir": prev[1], **{k: s[k] for k in STATE if s.get(k) is not None}}
        if st != last:
            track.append({"f": s["f"], **st})
            last = st
        if prev[0] not in views:
            views.append(prev[0])
    h = max([s.get("height_px") or 0 for s in samples] or [0])
    return {"id": cid, "rig": rig, "height_px": int(min(MAX_PX, round(h * 1.2))), "views": views, "track": track,
            "card_angle_max": round(max([abs(s.get("elev") or 0) for s in samples] or [0]), 1)}


def plan_doc(shot: str, fps: int, frames: int, chars: dict, crowd: dict = None, crowd_pool: list = None) -> dict:
    """chars {id: {rig, samples}} → layers.json."""
    doc = {"shot": shot, "fps": fps, "frames": frames,
           "chars": [char_plan(c, v.get("rig") or "", v.get("samples") or []) for c, v in chars.items()]}
    if crowd:
        doc["crowd"] = {"pool": list(crowd_pool or [])[:CROWD_POOL], "actions": list(crowd.get("actions") or ["sit"]),
                        "count": int(crowd.get("count") or 0)}
    doc["card_angle_max"] = max([c["card_angle_max"] for c in doc["chars"]] or [0])
    return doc


def jobs(doc: dict) -> list:
    """(char, view) pairs the AE layers pass draws: each character's views; the crowd pool, front view only."""
    out = [(c["id"], v) for c in doc["chars"] for v in c["views"]]
    out += [(p, "front") for p in (doc.get("crowd") or {}).get("pool", [])]
    return out


def write(film_dir, doc: dict) -> Path:
    p = Path(film_dir) / "layers" / doc["shot"] / "layers.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    return p
