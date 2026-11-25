"""GET /jobs/{id}/steps (specs/026 contracts/api.md): the step rail, the review points, what a change makes run again,
and the choices the edit panels may offer (catalogue of the film's kit, voices, mix ranges). Read only."""
import json
import zipfile
from pathlib import Path

from . import donesofar, jobs, reviews, store
from .store import StudioError

ROOT = Path(__file__).resolve().parents[3]
_voices = None


def voices() -> list:
    """The library's Kokoro voices (names inside voices-v1.0.bin, a zip of .npy files); [] when the model is missing."""
    global _voices
    if _voices is None:
        f = ROOT / "lib" / "lemo-opuscar" / "core" / "tts" / "voices-v1.0.bin"
        try:
            with zipfile.ZipFile(f) as z:
                _voices = sorted(n[:-4] for n in z.namelist() if n.endswith(".npy"))
        except (OSError, zipfile.BadZipFile):
            _voices = []
    return _voices


def catalog(d: Path):
    """Names the Shots panel may offer: the kit's catalogue plus the film's custom sets; None without a scene table."""
    cat = store.read_json(d / "kit" / "catalog.json")
    scenes = store.read_json(d / "scenes.json")
    if not cat or not isinstance(scenes, dict):
        return None
    pre = {}
    for k, v in (cat.get("act_prefixes") or {}).items():
        pre[k] = cat.get(v, []) if isinstance(v, str) else list(v)
    return {"sets": list(cat.get("sets") or []) + [f"custom:{c}" for c in scenes.get("custom") or []],
            "cams": list(cat.get("cams") or []), "acts": list(cat.get("acts") or []), "act_prefixes": pre}


def mix_ranges(d: Path) -> dict:
    """research R11: music under the voice within the style's measured range ± 3 dB; the rest fixed."""
    t = store.read_json(d / "kit" / "template.json") or {}
    lo, hi = ((t.get("sound") or {}).get("music_under_voice_db")) or [-8.5, -3.3]
    cur = store.read_json(d / "mix.json") or {}
    return {"under": [round(lo - 3, 1), round(hi + 3, 1)], "duck": [-20, 0], "sfx": [-24, 6],
            "music": ["seed:7", "seed:3", "seed:11", "none"], "current": cur,
            "defaults": {"music": "seed:7", "music_under_voice_db": round((lo + hi) / 2, 1), "duck_db": -6, "sfx_db": 0}}


def cast_block(d: Path):
    """The Cast panel (specs/034 contracts/api.md); None for a film without the cast point (page film)."""
    from filmcheck import cast, points
    if not cast.is_ae(d):
        return None
    try:
        doc = cast.load(d)
        st = cast.states(d, doc)
        errors = [{"character": c, "code": k, "message": m} for c, k, m in cast.validate(doc)]
    except cast.CastError as e:
        return {"characters": [], "error": e.message, "notes": None, "notes_base": None, "save_to_library": True,
                "library_available": False, "fingerprint": None, "skip": None}
    counts = cast.open_notes(d)
    notes, notes_base = None, None
    try:
        from filmcheck import castnotes
        notes, notes_base = castnotes.load(d), castnotes.base(d)
    except ImportError:
        pass
    except Exception:                             # noqa: BLE001 — a broken notes file still shows the sheets
        notes = None
    try:
        from filmcheck import castlib
        lib = castlib.available()
    except Exception:                             # noqa: BLE001
        lib = False
    chars = []
    for c in doc["characters"]:
        if not isinstance(c, dict) or not c.get("id"):
            continue
        sheet = store.read_json(cast.sheet_dir(d, c["id"]) / "sheet.json")
        prev = (cast.sheet_dir(d, c["id"]).parent / f"{c['id']}.prev" / "sheet.json").is_file()
        row = {"id": c["id"], "name": c.get("name"), "role": c.get("role"), "kind": c.get("kind", "one"),
               "state": st.get(c["id"]), "source": cast.source(c), "rig": c.get("rig"), "needs": c.get("needs"),
               "palette": cast.palette(c), "sheet": {"frames": sheet.get("frames", []), "built_at": sheet.get("built_at")}
               if isinstance(sheet, dict) else None, "has_prev": prev, "notes_open": counts.get(c["id"], 0),
               "approved": c.get("approved")}
        row["members" if row["kind"] == "group" else "spec"] = c.get("members") if row["kind"] == "group" else c.get("spec")
        chars.append(row)
    return {"characters": chars, "errors": errors, "notes": notes, "notes_base": notes_base,
            "save_to_library": doc.get("save_to_library", True), "library_available": lib,
            "fingerprint": cast.fingerprint(d), "skip": points.cast_skip_reason(d)}


def pending_review(j: dict):
    for rid in reversed(j.get("review_ids") or []):
        try:
            r = reviews.load(rid)
        except StudioError:
            continue
        if r["kind"] in reviews.POINT_KINDS:
            return {"id": r["id"], "kind": r["kind"], "decision": r["decision"]}
    return None


def view(j: dict) -> dict:
    from filmcheck import edit, points, steps
    d = donesofar.film_dir(j)
    if d is None:
        raise StudioError("not_found", "this job has no film folder yet", 404)
    rv = pending_review(j)
    pending = {rv["kind"]} if rv and not rv["decision"] else set()
    busy = edit.read_lock(d)
    job_step = j.get("step") if j["status"] == "running" and j.get("step") in steps.STEPS else None
    cat = catalog(d)
    has_kit = (d / "kit" / "catalog.json").is_file()
    return {"film": d.name, "steps": steps.status(d, job_step, pending, busy),
            "points": points.status(d, pending), "impact": {p: steps.impact(p, d) for p in points.POINTS},
            "busy": {"step": busy["step"], "since": busy["since"]} if busy else None,
            "editable": {"shots": cat is not None,
                         "reason": None if cat is not None else ("no scene table" if has_kit else "style has no kit")},
            "catalog": cat, "voices": voices(), "mix_ranges": mix_ranges(d), "review": rv, "cast": cast_block(d)}


def etag(v: dict) -> str:
    return '"' + str(abs(hash(json.dumps(v, sort_keys=True, ensure_ascii=False)))) + '"'
