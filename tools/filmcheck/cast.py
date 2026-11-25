"""The cast of an After Effects film (specs/034, contracts/files.md → cast/cast.json, data-model "Character", "Cast").

cast/cast.json lists the film's characters: rig version, rig parameters (spec), the expressions and poses the script
needs, where the character came from (the channel's cast library) and its approval. A character's fingerprint covers
its spec, rig, needs and the sheet.json of its cast sheet, so a redraw or any change un-approves it (FR-012).
Standard library only; the rig catalog comes from tools/ae/rigs."""
import hashlib
import json
import os
import re
import time
from pathlib import Path

from ae import film as filmdoc
from ae import rigs

CHAR_ID = re.compile(r"[a-z0-9-]{1,32}")
PARA = re.compile(r"P[0-9]{2,3}")
COLOR = re.compile(r"#[0-9a-fA-F]{6}")
ROLES = ("hero", "support", "background")
KINDS = ("one", "group")
HATS = ("beanie", "cap", "curly", "puffs", "bun", "none")
COLOR_KEYS = ("hoodie", "pants", "shoes", "headColor", "rimColor")
SPEC_KEYS = COLOR_KEYS + ("hat", "stripe", "tie", "hood", "brows", "scale")
BROWS = (False, True, "angry", "worried")
SOURCES = ("ui", "chat", "library")
STATES = ("new", "ready", "approved", "changed")
MAX_CHARACTERS = 10


class CastError(Exception):
    def __init__(self, code: str, message: str, character: str = None):
        super().__init__(message)
        self.code, self.message, self.character = code, message, character


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def path(film_dir) -> Path:
    return Path(film_dir) / "cast" / "cast.json"


def sheet_dir(film_dir, cid: str) -> Path:
    return Path(film_dir) / "cast" / "sheets" / cid


def is_ae(film_dir) -> bool:
    return filmdoc.engine(film_dir) == "ae"


def exists(film_dir) -> bool:
    return path(film_dir).is_file()


def load(film_dir) -> dict:
    p = path(film_dir)
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"version": 1, "channel": None, "save_to_library": True, "characters": []}
    except (OSError, ValueError) as e:
        raise CastError("bad_cast", f"cast/cast.json cannot be read: {e}")
    if not isinstance(doc, dict) or not isinstance(doc.get("characters", []), list):
        raise CastError("bad_cast", "cast/cast.json must be an object with a characters list")
    doc.setdefault("version", 1)
    doc.setdefault("save_to_library", True)
    doc.setdefault("characters", [])
    return doc


def write_json(p: Path, doc) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def save(film_dir, doc: dict) -> None:
    write_json(path(film_dir), doc)


def find(doc: dict, cid: str) -> dict:
    for c in doc["characters"]:
        if c.get("id") == cid:
            return c
    raise CastError("no_character", f"no character {cid!r} in cast/cast.json", cid)


# ---------- validation (contracts/files.md) ----------
def _check_spec(spec, where: str, cid: str, errs: list) -> None:
    if not isinstance(spec, dict):
        errs.append((cid, "bad_spec", f"{where} must be an object"))
        return
    for k, v in spec.items():
        if k not in SPEC_KEYS:
            errs.append((cid, "bad_spec", f"{where}: unknown key {k!r} (allowed: {', '.join(SPEC_KEYS)})"))
        elif k in COLOR_KEYS and not (isinstance(v, str) and COLOR.fullmatch(v)):
            errs.append((cid, "bad_spec", f"{where}.{k} must be a #rrggbb colour"))
        elif k in ("stripe", "tie") and not (v is None or (isinstance(v, str) and COLOR.fullmatch(v))):
            errs.append((cid, "bad_spec", f"{where}.{k} must be a #rrggbb colour or null"))
        elif k == "hood" and not isinstance(v, bool):
            errs.append((cid, "bad_spec", f"{where}.hood must be true or false"))
        elif k == "brows" and v not in BROWS:
            errs.append((cid, "bad_spec", f"{where}.brows must be false, \"angry\" or \"worried\""))
        elif k == "scale" and not (isinstance(v, (int, float)) and not isinstance(v, bool) and 0.6 <= v <= 1.4):
            errs.append((cid, "bad_spec", f"{where}.scale must be a number from 0.6 to 1.4"))
        elif k == "hat":
            if not isinstance(v, dict) or v.get("kind") not in HATS or set(v) - {"kind", "color"}:
                errs.append((cid, "bad_spec", f"{where}.hat must be {{kind: {'|'.join(HATS)}, color}}"))
            elif "color" in v and not (isinstance(v["color"], str) and COLOR.fullmatch(v["color"])):
                errs.append((cid, "bad_spec", f"{where}.hat.color must be a #rrggbb colour"))


def _check_needs(needs, cid: str, errs: list) -> None:
    if not isinstance(needs, dict) or set(needs) - {"expressions", "poses", "walk"}:
        errs.append((cid, "bad_needs", "needs must be {expressions: [], poses: [], walk: bool}"))
        return
    for part in ("expressions", "poses"):
        rows = needs.get(part, [])
        if not isinstance(rows, list):
            errs.append((cid, "bad_needs", f"needs.{part} must be a list"))
            continue
        seen = set()
        for r in rows:
            if not (isinstance(r, dict) and isinstance(r.get("key"), str) and re.fullmatch(r"[A-Za-z0-9]{1,24}", r["key"])
                    and isinstance(r.get("label"), str) and 0 < len(r["label"]) <= 40):
                errs.append((cid, "bad_needs", f"needs.{part}: each item is {{key, label, para}} (got {r!r})"))
            elif r.get("para") is not None and not (isinstance(r["para"], str) and PARA.fullmatch(r["para"])):
                errs.append((cid, "bad_needs", f"needs.{part}.{r['key']}: para looks like P01"))
            elif r["key"] in seen:
                errs.append((cid, "bad_needs", f"needs.{part}: {r['key']} is listed twice"))
            else:
                seen.add(r["key"])
    if "walk" in needs and not isinstance(needs["walk"], bool):
        errs.append((cid, "bad_needs", "needs.walk must be true or false"))


def validate(doc: dict) -> list:
    """[(character id or None, code, message)]; empty when cast.json follows contracts/files.md."""
    errs = []
    chars = doc.get("characters")
    if not isinstance(chars, list):
        return [(None, "bad_cast", "characters must be a list")]
    if len(chars) > MAX_CHARACTERS:
        errs.append((None, "too_many", f"at most {MAX_CHARACTERS} characters"))
    if not isinstance(doc.get("save_to_library", True), bool):
        errs.append((None, "bad_cast", "save_to_library must be true or false"))
    seen = set()
    for c in chars:
        if not isinstance(c, dict):
            errs.append((None, "bad_cast", "each character is an object"))
            continue
        cid = c.get("id")
        if not (isinstance(cid, str) and CHAR_ID.fullmatch(cid)):
            errs.append((None, "bad_id", f"character id must match [a-z0-9-]{{1,32}} (got {cid!r})"))
            continue
        if cid in seen:
            errs.append((cid, "bad_id", f"character id {cid} is used twice"))
        seen.add(cid)
        if not (isinstance(c.get("name"), str) and 0 < len(c["name"]) <= 40):
            errs.append((cid, "bad_name", "name: 1 to 40 characters"))
        if c.get("role") not in ROLES:
            errs.append((cid, "bad_role", f"role must be one of {', '.join(ROLES)}"))
        kind = c.get("kind", "one")
        if kind not in KINDS:
            errs.append((cid, "bad_kind", "kind must be one or group"))
        try:
            rigs.parse(c.get("rig"))
            if not rigs.is_locked(c["rig"]):
                errs.append((cid, "bad_rig", f"rig {c['rig']} is not in tools/ae/rigs.lock"))
        except ValueError as e:
            errs.append((cid, "bad_rig", str(e)))
        if kind == "group":
            m = c.get("members")
            if not (isinstance(m, list) and 2 <= len(m) <= 8):
                errs.append((cid, "bad_members", "a group has 2 to 8 members"))
            else:
                for i, s in enumerate(m):
                    _check_spec(s, f"members[{i}]", cid, errs)
        else:
            _check_spec(c.get("spec", {}), "spec", cid, errs)
        _check_needs(c.get("needs", {"expressions": [], "poses": [], "walk": False}), cid, errs)
        fl = c.get("from_library")
        if fl is not None and not (isinstance(fl, dict) and isinstance(fl.get("channel"), str) and fl.get("id")
                                   and isinstance(fl.get("v"), int)):
            errs.append((cid, "bad_library", "from_library must be {channel, id, v} or null"))
        ap = c.get("approved")
        if ap is not None and not (isinstance(ap, dict) and ap.get("fingerprint") and ap.get("source") in SOURCES):
            errs.append((cid, "bad_approved", "approved must be {fingerprint, at, by, source} or null"))
    return errs


def catalog_warnings(film_dir, doc: dict = None) -> list:
    """[(id, message)] for needs the rig cannot draw (the sheet shows "No picture yet" for them)."""
    doc = doc or load(film_dir)
    out = []
    for c in doc["characters"]:
        try:
            cat = rigs.catalog(c["rig"])
        except (OSError, ValueError, KeyError):
            continue
        needs = c.get("needs") or {}
        for part, have in (("expressions", cat.get("expressions", [])), ("poses", cat.get("poses", []))):
            for r in needs.get(part, []):
                if isinstance(r, dict) and r.get("key") not in have:
                    out.append((c["id"], f"{part[:-1]} {r.get('key')!r} is not in the {c['rig']} catalog: "
                                         "its picture stays empty (No picture yet)"))
    return out


# ---------- fingerprints and states (data-model "Character") ----------
def _sheet_hash(film_dir, cid: str) -> str:
    p = sheet_dir(film_dir, cid) / "sheet.json"
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else ""


def char_fingerprint(film_dir, c: dict) -> str:
    body = {k: c.get(k) for k in ("rig", "kind", "spec", "members", "needs")}
    h = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode())
    h.update(b"\0" + _sheet_hash(film_dir, c["id"]).encode())
    return h.hexdigest()[:16]


def fingerprint(film_dir) -> str:
    """The cast point's fingerprint: cast.json without approvals + every character's sheet.json."""
    d = Path(film_dir)
    try:
        doc = load(d)
    except CastError:
        return hashlib.sha256(path(d).read_bytes()).hexdigest()[:16]
    body = dict(doc)
    body["characters"] = [{k: v for k, v in c.items() if k not in ("approved", "from_library")}   # saving to the library
                          for c in doc["characters"] if isinstance(c, dict)]                    # keeps an approval
    h = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode())
    for c in body["characters"]:
        if isinstance(c.get("id"), str) and CHAR_ID.fullmatch(c["id"]):
            h.update(b"\0" + c["id"].encode() + b"=" + _sheet_hash(d, c["id"]).encode())
    return h.hexdigest()[:16]


def open_notes(film_dir) -> dict:
    """{character id: number of open notes} from cast-notes.json."""
    try:
        from filmcheck import castnotes
        return castnotes.open_counts(film_dir)
    except Exception:       # noqa: BLE001 — a broken notes file must not hide the cast
        return {}


def has_sheet(film_dir, cid: str) -> bool:
    return (sheet_dir(film_dir, cid) / "sheet.json").is_file()


def state(film_dir, c: dict, notes: dict = None) -> str:
    """new (no sheet) · ready (sheet, not approved) · approved · changed (approved, then changed or noted)."""
    notes = open_notes(film_dir) if notes is None else notes
    ap = c.get("approved")
    if ap:
        if ap.get("fingerprint") == char_fingerprint(film_dir, c) and not notes.get(c["id"]):
            return "approved"
        return "changed"
    return "ready" if has_sheet(film_dir, c["id"]) else "new"


def states(film_dir, doc: dict = None) -> dict:
    doc = doc or load(film_dir)
    notes = open_notes(film_dir)
    return {c["id"]: state(film_dir, c, notes) for c in doc["characters"] if isinstance(c, dict) and c.get("id")}


def source(c: dict) -> str:
    fl = c.get("from_library")
    return f"library v{fl['v']}" if fl else "film"


def unapproved(film_dir) -> list:
    """Ids of characters that are not approved (the voice gate names them, FR-003)."""
    doc = load(film_dir)
    st = states(film_dir, doc)
    return [cid for cid, s in st.items() if s != "approved"]


def all_approved(film_dir) -> bool:
    doc = load(film_dir)
    return bool(doc["characters"]) and not unapproved(film_dir)


# ---------- approval ----------
def approve(film_dir, ids, source: str = "chat", by: str = "local") -> list:
    """Approve these characters; returns [] or the reasons nothing was written (exit code 1)."""
    if source not in SOURCES:
        raise CastError("bad_source", f"source: {', '.join(SOURCES)}")
    d = Path(film_dir)
    doc = load(d)
    notes = open_notes(d)
    why = []
    picked = [find(doc, i) for i in ids]
    for c in picked:
        if not has_sheet(d, c["id"]):
            why.append(f"{c['id']}: no cast sheet yet (run: sh bin/studio ae sheet {d.name} --only {c['id']})")
        elif notes.get(c["id"]):
            why.append(f"{c['id']}: {notes[c['id']]} open note(s); send them to Claude or delete them first")
    if why:
        return why
    for c in picked:
        c["approved"] = {"fingerprint": char_fingerprint(d, c), "at": now(), "by": by or "local", "source": source}
    save(d, doc)
    return []


def unapprove(film_dir, cid: str) -> bool:
    d = Path(film_dir)
    doc = load(d)
    c = find(doc, cid)
    if not c.get("approved"):
        return False
    c["approved"] = None
    save(d, doc)
    return True


def palette(c: dict) -> list:
    """[(label, #rrggbb)] of a character for the sheet's colour row."""
    specs = c.get("members") if c.get("kind") == "group" else [c.get("spec") or {}]
    out, seen = [], set()
    for s in specs or []:
        for k in COLOR_KEYS + ("stripe", "tie"):
            v = s.get(k)
            if isinstance(v, str) and v.lower() not in seen:
                seen.add(v.lower()); out.append((k, v.lower()))
        hat = s.get("hat") or {}
        if isinstance(hat.get("color"), str) and hat["color"].lower() not in seen:
            seen.add(hat["color"].lower()); out.append((hat.get("kind", "hat"), hat["color"].lower()))
    return out
