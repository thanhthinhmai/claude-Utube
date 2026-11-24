"""film.json of a film folder (specs/032 data-model.md): which engine draws the film and, for AE films, its shots."""
import json
import re
from pathlib import Path

ENGINES = ("page", "ae")
SHOT_ID = re.compile(r"S([0-9]{1,3}[A-Z]?)")


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
    return doc


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
