"""shots export (specs/029 FR-003a, research R5): write a finished web film's shots.json from its page's window.SHOTS
and window.DUR, read with tools/filmcheck/plan.mjs (no frames drawn), checked against the video's length (ffprobe).
    export(film_dir, lib) -> (exit code, lines)    0 written · 1 no SHOTS, wrong SHOTS or length off · 2 no film/video"""
import json
import os
from pathlib import Path

from filmcheck import shotnotes

HERE = Path(__file__).resolve().parent


def page_plan(d: Path, lib) -> dict:
    """{dur, shots, …} from the page (plan.mjs). Raises ValueError with the reason."""
    from filmcheck import plancheck
    if not (d / "index.html").is_file():
        raise ValueError(f"{d.name}/index.html is not there: the page cannot export window.SHOTS")
    if not lib or not Path(lib, "core/render/page.mjs").is_file():
        raise ValueError("the library is not installed (sh bin/studio deps)")
    try:
        p = plancheck._node([HERE / "plan.mjs", d, lib])
    except plancheck.PlanError as e:
        raise ValueError(str(e)) from None
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise ValueError(f"the page could not be read: {(p.stderr or p.stdout).strip()[-300:]}") from None


def doc_from(shots_rows, duration: float, fps: float, video: str, source: str = "page") -> dict:
    rows = [[round(float(r[0]), 3), round(float(r[1]), 3), str(r[2]) if len(r) > 2 and r[2] is not None else "",
             str(r[3]) if len(r) > 3 and r[3] is not None else ""] for r in shots_rows]
    f = round(fps) if fps and abs(fps - round(fps)) < 0.01 else round(fps, 3)
    return {"version": 1, "video": video, "duration": round(duration, 3), "fps": f or 30, "source": source,
            "shots": rows}


def write_from_rows(d: Path, rows, source="page") -> tuple:
    """Check rows [[t0, t1, set, id]] against the film's video and write shots.json. (code, lines)."""
    p = shotnotes.film_paths(d)
    info = shotnotes.probe(p["video"])
    if not info["has_video"]:
        return 2, [f"✗ {p['video'].name} cannot be read as a video"]
    doc = doc_from(rows, info["duration"], info["fps"], p["video"].name, source)
    shots, problems = shotnotes.check_shots(doc, info["duration"])
    if problems:
        return 1, [f"✗ shots row {x['row']}: {x['rule']} — {x['detail']}" for x in problems[:20]]
    shotnotes.write_atomic(p["shots"], (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode())
    return 0, [f"✓ shots.json: {len(shots)} shots · {info['duration']:.2f} s ({source})"]


def export(film_dir, lib=None) -> tuple:
    d = Path(film_dir)
    if not d.is_dir():
        return 2, [f"✗ film folder not found: {d}"]
    try:
        p = shotnotes.film_paths(d)
    except shotnotes.ShotError as e:
        return 2, [f"✗ {e.message}"]
    if not p["video"].is_file():
        return 2, [f"✗ {p['video'].name} is not there yet: render and mux the film first"]
    lib = lib or os.environ.get("STUDIO_LIB") or str(HERE.parents[1] / "lib" / "lemo-opuscar")
    try:
        page = page_plan(d, lib)
    except ValueError as e:
        return 1, [f"✗ {e}"]
    if not isinstance(page.get("shots"), list) or not page["shots"]:
        return 1, ["✗ the page does not export window.SHOTS ([[t0, t1, set, id]], contracts/film-page.md of specs/020)"]
    dur = page.get("dur")
    info = shotnotes.probe(p["video"])
    frame = 1.0 / (info["fps"] or 30) + 1e-6
    if isinstance(dur, (int, float)) and abs(float(dur) - info["duration"]) > frame:
        return 1, [f"✗ window.DUR is {float(dur):.3f} s but {p['video'].name} is {info['duration']:.3f} s "
                   "(more than 1 frame apart): render the film again"]
    return write_from_rows(d, page["shots"])
