"""film.json of a film folder (specs/032 data-model.md): which engine draws the film and, for AE films, its shots."""
import json
import re
from pathlib import Path

ENGINES = ("page", "ae")
SHOT_ENGINES = ("ae", "blender")        # specs/038: engines one shot of an AE film can use
SHOT_ID = re.compile(r"S([0-9]{1,3}[A-Z]?)")
# specs/038 data-model.md "Shot plan": allowed values of each shot_plan field
PLAN_CHOICES = {
    "engine": SHOT_ENGINES, "suggested": SHOT_ENGINES,
    "size": ("ecu", "cu", "med", "wide", "huge", "insert"),
    "cam_height": ("low", "eye", "high", "top"),
    "lens": ("wide", "normal", "long"),
    "depth": ("shallow", "mid", "deep"),
    "move": ("static", "push", "pull", "pan", "dolly", "orbit", "track", "crane", "zoom"),
    "transition": ("cut", "fade", "dip"),
}
LAYERS = ("fg", "mid", "bg", "far")
FLAGS = ("occluder", "card", "action", "outdoor", "prop")        # specs/039 R4: same meaning as craft-label
CAM_MOVES = ("static", "push", "pull", "pan")                    # specs/039: 2D camera moves of a camera block
CAM_TRANSITIONS = ("cut", "fade", "dip", "streak", "flash", "wipe", "dissolve")


class FilmError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def load(film_dir) -> dict:
    """film.json with defaults; a folder without it is a page film (films made before 032)."""
    d = Path(film_dir)
    p = d / "film.json"
    if not p.is_file():
        return {"engine": "page"}
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise FilmError("bad_film_json", f"film.json cannot be read: {e}")
    if not isinstance(doc, dict):
        raise FilmError("bad_film_json", "film.json must be an object")
    eng = doc.get("engine", "page")
    if eng not in ENGINES:
        raise FilmError("bad_film_json", f"film.json: engine must be one of {', '.join(ENGINES)}, not {eng!r}")
    doc["engine"] = eng
    if eng == "ae":
        doc.setdefault("fps", 30)
        doc.setdefault("size", [1920, 1080])
        doc.setdefault("shots", [])
        doc.setdefault("ae_files", sorted(f.name for f in (d / "ae").glob("*.jsx")) if (d / "ae").is_dir() else [])
        if not isinstance(doc["fps"], (int, float)) or not 1 <= doc["fps"] <= 120:
            raise FilmError("bad_film_json", "film.json: fps must be a number between 1 and 120")
        if not (isinstance(doc["size"], list) and len(doc["size"]) == 2 and all(isinstance(v, int) and v > 0 for v in doc["size"])):
            raise FilmError("bad_film_json", "film.json: size must be [width, height]")
        bad = [s for s in doc["shots"] if not (isinstance(s, str) and SHOT_ID.fullmatch(s))]
        if bad:
            raise FilmError("bad_film_json", f"film.json: shot ids look like S1, S13, S38A; bad: {bad[:3]}")
        for f in doc["ae_files"]:
            if not (isinstance(f, str) and re.fullmatch(r"[A-Za-z0-9_.-]+\.jsx", f)):
                raise FilmError("bad_film_json", f"film.json: ae_files holds plain .jsx names, not {f!r}")
            if not (d / "ae" / f).is_file():
                raise FilmError("bad_film_json", f"film.json: ae/{f} is missing")
        _check_plan(doc)
    return doc


def _check_plan(doc: dict) -> None:
    """specs/038: default_engine and shot_plan values (FR-003, FR-012)."""
    doc.setdefault("default_engine", "ae")
    doc.setdefault("shot_plan", {})
    if doc["default_engine"] not in SHOT_ENGINES:
        raise FilmError("bad_film_json", f"film.json: default_engine must be one of {', '.join(SHOT_ENGINES)}")
    plan = doc["shot_plan"]
    if not isinstance(plan, dict):
        raise FilmError("bad_film_json", "film.json: shot_plan must be an object keyed by shot id")
    for sid, row in plan.items():
        if sid not in doc["shots"]:
            raise FilmError("bad_film_json", f"film.json: shot_plan has {sid}, which is not in shots")
        if not isinstance(row, dict):
            raise FilmError("bad_film_json", f"film.json: shot_plan.{sid} must be an object")
        for key, allowed in PLAN_CHOICES.items():
            if key in row and row[key] not in allowed:
                raise FilmError("bad_film_json", f"film.json: shot_plan.{sid}.{key} must be one of {', '.join(allowed)}, "
                                                 f"not {row[key]!r}")
        if "layers" in row and not (isinstance(row["layers"], list) and all(x in LAYERS for x in row["layers"])):
            raise FilmError("bad_film_json", f"film.json: shot_plan.{sid}.layers holds some of {', '.join(LAYERS)}")
        for key in FLAGS:
            if key in row and not isinstance(row[key], bool):
                raise FilmError("bad_film_json", f"film.json: shot_plan.{sid}.{key} must be true or false")
        if "camera" in row:
            _check_camera(sid, row["camera"])
        if "people" in row and not (isinstance(row["people"], int) and row["people"] >= 0):
            raise FilmError("bad_film_json", f"film.json: shot_plan.{sid}.people must be a whole number")
        for key in ("set", "reason"):
            if key in row and not isinstance(row[key], str):
                raise FilmError("bad_film_json", f"film.json: shot_plan.{sid}.{key} must be text")


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _check_camera(sid: str, cam) -> None:
    """specs/039 data-model "Shot plan": the chosen camera of a shot (written only by `camera choose|retime`)."""
    where = f"film.json: shot_plan.{sid}.camera"
    if not isinstance(cam, dict):
        raise FilmError("bad_film_json", f"{where} must be an object")
    if cam.get("size") not in PLAN_CHOICES["size"]:
        raise FilmError("bad_film_json", f"{where}.size must be one of {', '.join(PLAN_CHOICES['size'])}")
    move = cam.get("move")
    if not (isinstance(move, str) and (move in CAM_MOVES or cam.get("by_user_request") is True)):
        raise FilmError("bad_film_json", f"{where}.move must be one of {', '.join(CAM_MOVES)} "
                                         "(another move only with by_user_request: true)")
    st = cam.get("start")
    if not (isinstance(st, dict) and all(_num(st.get(k)) for k in ("scale", "cx", "cy"))):
        raise FilmError("bad_film_json", f"{where}.start must be {{scale, cx, cy}}")
    if not 0.5 <= st["scale"] <= 4:
        raise FilmError("bad_film_json", f"{where}.start.scale must be between 0.5 and 4")
    if not (_num(cam.get("zoom_pct")) and abs(cam["zoom_pct"]) <= 40):
        raise FilmError("bad_film_json", f"{where}.zoom_pct must be a number from -40 to 40")
    if not _num(cam.get("rate_pct_s")):
        raise FilmError("bad_film_json", f"{where}.rate_pct_s must be a number")
    e = cam.get("ease")
    if e is not None and not (isinstance(e, list) and len(e) == 3 and all(_num(x) and 0 <= x <= 1 for x in e)
                              and e[0] <= e[1] <= e[2]):
        raise FilmError("bad_film_json", f"{where}.ease must be three rising numbers from 0 to 1, or null")
    ea = cam.get("ease_ae")
    if ea is not None and not (isinstance(ea, list) and len(ea) == 2 and all(_num(x) and 0.1 <= x <= 100 for x in ea)):
        raise FilmError("bad_film_json", f"{where}.ease_ae must be [in, out] influence from 0.1 to 100")
    d = cam.get("drift_px")
    if not (isinstance(d, list) and len(d) == 2 and all(_num(x) for x in d)):
        raise FilmError("bad_film_json", f"{where}.drift_px must be [x, y]")
    if cam.get("transition", "cut") not in CAM_TRANSITIONS:
        raise FilmError("bad_film_json", f"{where}.transition must be one of {', '.join(CAM_TRANSITIONS)}")


def engine_of(doc: dict, shot: str) -> str:
    """The engine that draws one shot of an AE film (shot_plan, else default_engine)."""
    return (doc.get("shot_plan") or {}).get(shot, {}).get("engine") or doc.get("default_engine", "ae")


def blender_shots(doc: dict, shots=None) -> list:
    return [s for s in (shots if shots is not None else doc.get("shots", [])) if engine_of(doc, s) == "blender"]


def validate_plan(film_dir, doc: dict, shots=None) -> None:
    """Before a build: each Blender shot names its set and has its script films/<name>/blender/<shot>.py."""
    d = Path(film_dir)
    for s in blender_shots(doc, shots):
        row = doc["shot_plan"].get(s, {})
        if not row.get("set"):
            raise FilmError("bad_plan", f"{s} is a Blender shot but shot_plan.{s}.set is empty; name a set of the Blender kit")
        if not (d / "blender" / f"{s}.py").is_file():
            raise FilmError("bad_plan", f"{s} is a Blender shot but blender/{s}.py is missing")


def engine(film_dir) -> str:
    try:
        return load(film_dir)["engine"]
    except FilmError:
        return "page"


def require_ae(film_dir) -> dict:
    """The AE film's film.json, or FilmError naming the engine the film uses (FR-002)."""
    doc = load(film_dir)
    if doc["engine"] != "ae":
        raise FilmError("not_ae", f"{Path(film_dir).name} is drawn by the web page engine (engine \"{doc['engine']}\"), "
                                  "not After Effects; use sh bin/studio render for it")
    return doc


def pick_shots(doc: dict, wanted) -> list:
    """Shot ids to build: all shots, or the wanted ones in film order (unknown ids raise)."""
    if not wanted:
        return list(doc["shots"])
    want = [w.strip() for w in wanted if w.strip()]
    want = [w if w.startswith("S") else "S" + w for w in want]
    unknown = [w for w in want if w not in doc["shots"]]
    if unknown:
        raise FilmError("bad_shot", f"no such shot in film.json: {', '.join(unknown)}")
    return [s for s in doc["shots"] if s in want]
