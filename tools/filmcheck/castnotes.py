"""Notes on the cast sheet of an AE film (specs/034 contracts/files.md → cast-notes.json, data-model "Cast note").

A note is pinned on one picture (frame + x/y in percent), or general (frame null), or a request to draw a picture the
sheet lacks (kind "view", one open per frame). Every write names the base it was made on (sha256 of the file); an old
base is refused with the current content (409 "changed"). "Send notes to Claude" starts a lot: the open notes at that
moment; notes written later wait for the next lot (FR-013)."""
import hashlib
import json
import os
import secrets
import time
from pathlib import Path

from filmcheck import cast

TEXT_MAX = 2000
KINDS = ("note", "view")


class CastNoteError(Exception):
    def __init__(self, code: str, message: str, current: dict = None):
        super().__init__(message)
        self.code, self.message, self.current = code, message, current

    def exit_code(self) -> int:
        return 4 if self.code == "changed" else 2


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def path(film_dir) -> Path:
    return Path(film_dir) / "cast-notes.json"


def _raw(film_dir) -> bytes:
    try:
        return path(film_dir).read_bytes()
    except FileNotFoundError:
        return b""


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def empty() -> dict:
    return {"version": 1, "characters": {}}


def load(film_dir) -> dict:
    raw = _raw(film_dir)
    if not raw:
        return empty()
    try:
        doc = json.loads(raw.decode("utf-8"))
    except ValueError as e:
        raise CastNoteError("bad_notes", f"cast-notes.json cannot be read: {e}")
    if not isinstance(doc, dict) or not isinstance(doc.get("characters", {}), dict):
        raise CastNoteError("bad_notes", "cast-notes.json must have a characters object")
    doc.setdefault("version", 1)
    doc.setdefault("characters", {})
    return doc


def base(film_dir) -> str:
    return _sha(_raw(film_dir))


def current(film_dir) -> dict:
    return {"base": base(film_dir), "doc": load(film_dir)}


def _write(film_dir, doc: dict) -> str:
    p = path(film_dir)
    data = (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, p)
    return _sha(data)


def _check_base(film_dir, b) -> None:
    if b is not None and b != base(film_dir):
        raise CastNoteError("changed", "the notes changed since you opened them: reload", current(film_dir))


def notes_of(doc: dict, cid: str) -> list:
    return doc["characters"].setdefault(cid, {"notes": []}).setdefault("notes", [])


def all_notes(doc: dict):
    for cid, v in doc["characters"].items():
        for n in (v or {}).get("notes", []):
            yield cid, n


def open_counts(film_dir) -> dict:
    """{character id: open notes} (cast.py uses it for the states and the gate)."""
    out = {}
    for cid, n in all_notes(load(film_dir)):
        if not n.get("done"):
            out[cid] = out.get(cid, 0) + 1
    return out


def open_by_character(film_dir) -> dict:
    out = {}
    for cid, n in all_notes(load(film_dir)):
        if not n.get("done"):
            out.setdefault(cid, []).append(n)
    return out


def _frames(film_dir, cid: str) -> dict:
    p = cast.sheet_dir(film_dir, cid) / "sheet.json"
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {f.get("key"): f for f in doc.get("frames", []) if isinstance(f, dict)}


def _text(t) -> str:
    t = (t or "").strip() if isinstance(t, str) else ""
    if not 1 <= len(t) <= TEXT_MAX:
        raise CastNoteError("bad_text", f"a note is 1 to {TEXT_MAX} characters")
    return t


def _pin(film_dir, cid, frame, x, y) -> tuple:
    if x is None and y is None:
        return None, None
    if frame is None:
        raise CastNoteError("bad_pin", "a pin needs a picture (frame)")
    f = _frames(film_dir, cid).get(frame)
    if not f or not f.get("file"):
        raise CastNoteError("bad_pin", f"{frame} has no picture to pin a note on")
    try:
        x, y = float(x), float(y)
    except (TypeError, ValueError):
        raise CastNoteError("bad_pin", "x and y are numbers from 0 to 100") from None
    if not (0 <= x <= 100 and 0 <= y <= 100):
        raise CastNoteError("bad_pin", "x and y are numbers from 0 to 100")
    return round(x, 1), round(y, 1)


def _character(film_dir, cid: str) -> None:
    try:
        cast.find(cast.load(film_dir), cid)
    except cast.CastError as e:
        raise CastNoteError("no_character", e.message) from None


def _find(doc: dict, cid: str, nid: str) -> dict:
    for n in doc["characters"].get(cid, {}).get("notes", []):
        if n.get("id") == nid:
            return n
    raise CastNoteError("no_note", f"no note {nid} on {cid}")


def add(film_dir, cid: str, kind: str = "note", frame: str = None, x=None, y=None, text: str = None,
        by: str = "owner", b: str = None) -> dict:
    _check_base(film_dir, b)
    _character(film_dir, cid)
    if kind not in KINDS:
        raise CastNoteError("bad_kind", "kind: note or view")
    frame = frame or None
    doc = load(film_dir)
    if kind == "view":
        if not frame:
            raise CastNoteError("bad_frame", "a view request names the picture (frame)")
        if any(n.get("kind") == "view" and n.get("frame") == frame and not n.get("done") for n in notes_of(doc, cid)):
            raise CastNoteError("duplicate", f"{frame} is already requested")
        x = y = None
        text = text or "Draw this view"
    elif frame is not None and frame not in _frames(film_dir, cid):
        raise CastNoteError("bad_frame", f"{cid} has no picture {frame}")
    x, y = _pin(film_dir, cid, frame, x, y)
    t = now()
    n = {"id": f"n-{secrets.token_hex(4)}", "kind": kind, "frame": frame, "x": x, "y": y, "text": _text(text),
         "done": False, "by": by or "owner", "created": t, "updated": t, "reply": None}
    notes_of(doc, cid).append(n)
    _write(film_dir, doc)
    return n


def edit(film_dir, cid: str, nid: str, text: str = None, x=None, y=None, b: str = None) -> dict:
    """Change a note's words, or move its pin (the words stay)."""
    _check_base(film_dir, b)
    doc = load(film_dir)
    n = _find(doc, cid, nid)
    if text is not None:
        n["text"] = _text(text)
    if x is not None or y is not None:
        n["x"], n["y"] = _pin(film_dir, cid, n.get("frame"), x, y)
    n["updated"] = now()
    _write(film_dir, doc)
    return n


def delete(film_dir, cid: str, nid: str, b: str = None) -> None:
    _check_base(film_dir, b)
    doc = load(film_dir)
    n = _find(doc, cid, nid)
    notes_of(doc, cid).remove(n)
    if doc.get("lot") and nid in doc["lot"].get("notes", []):
        doc["lot"]["notes"].remove(nid)
    _write(film_dir, doc)


def toggle_view(film_dir, cid: str, frame: str, by: str = "owner", b: str = None):
    """"Request this view" / "Undo": adds the open view request of this picture, or removes it. Returns the note or None."""
    _check_base(film_dir, b)
    doc = load(film_dir)
    for n in notes_of(doc, cid):
        if n.get("kind") == "view" and n.get("frame") == frame and not n.get("done"):
            delete(film_dir, cid, n["id"])
            return None
    return add(film_dir, cid, "view", frame, by=by)


def reply(film_dir, nid: str, text: str, done: bool = None, b: str = None) -> dict:
    """Claude's answer to a note; done=True ticks it, done=False opens it again."""
    _check_base(film_dir, b)
    doc = load(film_dir)
    for cid, n in all_notes(doc):
        if n.get("id") == nid:
            t = (text or "").strip()
            if not 1 <= len(t) <= TEXT_MAX:
                raise CastNoteError("bad_text", f"a reply is 1 to {TEXT_MAX} characters")
            n["reply"], n["updated"] = t, now()
            if done is not None:
                n["done"] = bool(done)
            _write(film_dir, doc)
            return n
    raise CastNoteError("no_note", f"no note {nid}")


def start_lot(film_dir, job: str) -> dict:
    """"Send notes to Claude": the open notes now form the lot this job redraws."""
    doc = load(film_dir)
    ids = [n["id"] for _, n in all_notes(doc) if not n.get("done")]
    doc["lot"] = {"job": job, "notes": ids, "since": now()}
    _write(film_dir, doc)
    return doc["lot"]


def end_lot(film_dir) -> None:
    doc = load(film_dir)
    if doc.pop("lot", None) is not None:
        _write(film_dir, doc)


def summary(film_dir) -> str:
    """"N notes on: friend, hero" for the revise decision."""
    by = open_by_character(film_dir)
    n = sum(len(v) for v in by.values())
    return f"{n} note{'' if n == 1 else 's'} on: {', '.join(sorted(by))}" if n else ""
