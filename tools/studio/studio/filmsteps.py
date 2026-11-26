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


_el = {}


def el_voices() -> list:
    """The ElevenLabs voices of the owner's key (app) or of .env (command line), cached 10 minutes; [] without a key
    or when ElevenLabs cannot be reached (specs/036 FR-003)."""
    import time
    from filmcheck import eleven
    hit = _el.get("rows")
    if hit and time.time() - hit[0] < 600:
        return hit[1]
    rows = []
    try:
        if store.mode() == "online":
            from . import voicekeys
            sec = voicekeys.secret()
            rows = eleven.list_voices(sec["key"]) if sec else []
        elif eleven.setting("ELEVENLABS_API_KEY"):
            rows = eleven.list_voices()
    except eleven.ElevenError:
        rows = []
    _el["rows"] = (time.time(), rows)
    return rows


def voice_rows() -> list:
    """Both providers for the voice pickers: Kokoro then ElevenLabs, each with its provider, gender, age, cloned."""
    from filmcheck import voicecat
    return voicecat.catalog(el_voices(), kokoro=voices())


def voice_cost(d: Path) -> dict:
    """What reading the whole film again would spend at ElevenLabs (specs/036 FR-005, research R8)."""
    from filmcheck import voicecat
    rows = store.read_json(d / "lines.json") or []
    el = [r for r in rows if isinstance(r, dict) and voicecat.parse(r.get("voice") or "")[0] == "elevenlabs"]
    used = store.read_json(d / "voices" / "usage.json") or {}
    return {"chars": sum(len(r.get("say") or r.get("text") or "") for r in el), "lines": len(el),
            "used": int(used.get("total") or 0)}


def speaker_rows(d: Path) -> list:
    """specs/036 US2: [{id, name, source, role, setting, lines, issues}] for the Voice step; [] when lines.json is
    missing. Issues are the speaker's problems from the resolver (no narrator, no voice, same voice in a scene)."""
    from filmcheck import speakers
    rows = store.read_json(d / "lines.json")
    if not isinstance(rows, list):
        return []
    rows = [r for r in rows if isinstance(r, dict) and r.get("id")]
    try:
        res = speakers.resolve(d, rows, store.root())
    except Exception:                       # noqa: BLE001 — the page still opens with a damaged file
        return []
    out = []
    for sp, e in res["speakers"].items():
        out.append({"id": sp, "name": "Narrator" if sp == "narrator" else sp, "source": e["source"], "role": e.get("role"),
                    "setting": e["setting"], "lines": e["lines"],
                    "issues": [w for w in res["errors"] if f" {sp} " in f" {w} " or f'"{sp}"' in w]})
    missing = {r.get("speaker") or "narrator" for r in rows} - set(res["speakers"])
    for sp in sorted(missing):
        out.append({"id": sp, "name": "Narrator" if sp == "narrator" else sp, "source": None, "role": None, "setting": None,
                    "lines": [r["id"] for r in rows if (r.get("speaker") or "narrator") == sp],
                    "issues": [w for w in res["errors"] if f'"{sp}"' in w or (sp == "narrator" and "narrator" in w)]})
    return out


def narrator_now(d: Path) -> dict:
    """The narrator's voice and speed, the same the Done so far summary shows (specs/036 FR-041)."""
    from .donesofar import narrator_voice
    rows = store.read_json(d / "lines.json")
    return narrator_voice(d, rows if isinstance(rows, list) else [])


def emotions(d: Path) -> dict:
    """{line id: {emotion, emotion_applied}} from the last `voice make` (specs/036 FR-031)."""
    sp = store.read_json(d / "voices" / "speakers.json")
    e = sp.get("emotions") if isinstance(sp, dict) else None
    return e if isinstance(e, dict) else {}


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
        lib = castlib.available(d)
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
               "approved": c.get("approved"), "voice": c.get("voice"), "voice_options": c.get("voice_options") or [],
               "speaks": cast.speaks(d, c["id"])}                     # specs/036
        row["members" if row["kind"] == "group" else "spec"] = c.get("members") if row["kind"] == "group" else c.get("spec")
        chars.append(row)
    used = {r.get("para") for c in chars for k in ("expressions", "poses") for r in ((c.get("needs") or {}).get(k) or [])
            if isinstance(r, dict)}
    passages = {}
    if used - {None}:
        from filmcheck import script                                # T061: the passages each character plays in
        try:
            passages = {k: v for k, v in script.para_map(script.read_script(d / "SCRIPT.md")).items() if k in used}
        except Exception:                                           # no script or a broken one: ids only
            passages = {}
    return {"characters": chars, "errors": errors, "notes": notes, "notes_base": notes_base, "passages": passages,
            "save_to_library": doc.get("save_to_library", True), "library_available": lib,
            "fingerprint": cast.fingerprint(d), "skip": points.cast_skip_reason(d)}


def animatic_block(d: Path, j: dict = None):
    """The Animatic panel (specs/035 contracts/api.md); None for a film without the animatic point (page film)."""
    from filmcheck import animatic, cast, points, rhythm, timing
    if not cast.is_ae(d):
        return None
    building = None
    if j:
        mine = [a for a in store.doc_list("action") if a["job_id"] == j["id"] and a["op"] == "animatic-draft"
                and a["status"] in ("queued", "running")]
        if mine:
            sh = [x for a in mine for x in (a["args"].get("shots") or "").split(",") if x]
            building = {"shots": list(dict.fromkeys(sh)) or ["all"], "running": any(a["status"] == "running" for a in mine)}
    notes, notes_base = None, None
    try:
        if hasattr(animatic, "notes_load"):
            notes, notes_base = animatic.notes_load(d), animatic.notes_base(d)
    except Exception:                             # noqa: BLE001 — a broken notes file still shows the animatic
        notes = None
    base = {"started": False, "draft": None, "shots": [], "notes": notes, "notes_base": notes_base, "building": building,
            "skip": points.skip_reason(d, "animatic"), "limit": rhythm.SILENCE_MAX}
    try:
        t = animatic.timeline(d)
    except animatic.AnimaticError as e:
        return {**base, "error": None if e.code == "missing" else e.message}
    try:
        sil = animatic.silence(d)
    except animatic.AnimaticError:
        sil = None
    info = animatic.draft_info(d)
    fit = {x["shot"]: x for x in animatic.fit(d, all_states=True)}
    counts = animatic.open_notes(d)
    a = d / "animatic"
    v = (info or {}).get("built_at", "")
    shots = []
    for sh in t["shots"]:
        f = fit.get(sh["id"])
        shots.append({**sh, "frame_url": f"animatic/frames/{sh['id']}.jpg?v={v}" if (a / "frames" / f"{sh['id']}.jpg").is_file() else None,
                      "clip_url": f"animatic/clips/{sh['id']}.mp4?v={v}" if (a / "clips" / f"{sh['id']}.mp4").is_file() else None,
                      "fit": {k: f[k] for k in ("frames_new", "delta_s", "end_new", "head", "very_short", "motions", "state")}
                      if f else None, "notes_open": counts.get(sh["id"], 0)})
    return {**base, "started": True, "duration": t["duration"], "fps": t["fps"], "silence": sil, "shots": shots,
            "gaps": animatic.longest_gaps(d) if sil is not None and sil > rhythm.SILENCE_MAX else [],
            "draft": {"url": f"animatic/draft.mp4?v={v}", "current": animatic.draft_current(d), "built_at": info.get("built_at"),
                      "seconds": info.get("seconds"), "prev": (a / "draft.prev.mp4").is_file()}
            if info and (a / "draft.mp4").is_file() else None,
            "timing_base": timing.base(d), "can_undo": animatic.can_undo(d), "problems": animatic.problems(d)}


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
            "catalog": cat, "voices": voices() + [v["id"] for v in el_voices()], "voice_rows": voice_rows(),
            "voice_cost": voice_cost(d), "speakers": speaker_rows(d), "emotions": emotions(d), "narrator_voice": narrator_now(d), "mix_ranges": mix_ranges(d), "review": rv, "cast": cast_block(d),
            "animatic": animatic_block(d, j)}


def etag(v: dict) -> str:
    return '"' + str(abs(hash(json.dumps(v, sort_keys=True, ensure_ascii=False)))) + '"'
