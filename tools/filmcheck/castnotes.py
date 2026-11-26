"""Notes on the cast sheet of an AE film (specs/034 contracts/files.md → cast-notes.json, data-model "Cast note").

A note is pinned on one picture (frame + x/y in percent), or general (frame null), or a request to draw a picture the
sheet lacks (kind "view", one open per frame). Every write names the base it was made on (sha256 of the file); an old
base is refused with the current content (409 "changed"). "Send notes to Claude" starts a lot: the open notes at that
moment; notes written later wait for the next lot (FR-013). The file, bases, replies and lots are pins.py (specs/035)."""
import json

from filmcheck import cast, pins

TEXT_MAX = pins.TEXT_MAX
KINDS = ("note", "view")
BOOK = pins.Book("cast-notes.json", "characters")
CastNoteError = pins.PinError

now = pins.now
path = BOOK.path
load = BOOK.load
base = BOOK.base
current = BOOK.current
_write = BOOK.write
_check_base = BOOK.check_base
notes_of = BOOK.notes_of
all_notes = BOOK.all_notes
open_counts = BOOK.open_counts             # {character id: open notes} (cast.py uses it for the states and the gate)
open_by_character = BOOK.open_by
delete = BOOK.delete
reply = BOOK.reply
start_lot = BOOK.start_lot
end_lot = BOOK.end_lot
summary = BOOK.summary                     # "N notes on: friend, hero" for the revise decision
_text = pins.text
_find = BOOK.find


def empty() -> dict:
    return BOOK.empty()


def _frames(film_dir, cid: str) -> dict:
    p = cast.sheet_dir(film_dir, cid) / "sheet.json"
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {f.get("key"): f for f in doc.get("frames", []) if isinstance(f, dict)}


def _pin(film_dir, cid, frame, x, y) -> tuple:
    if x is None and y is None:
        return None, None
    if frame is None:
        raise CastNoteError("bad_pin", "a pin needs a picture (frame)")
    f = _frames(film_dir, cid).get(frame)
    if not f or not f.get("file"):
        raise CastNoteError("bad_pin", f"{frame} has no picture to pin a note on")
    return pins.xy(x, y)


def _character(film_dir, cid: str) -> None:
    try:
        cast.find(cast.load(film_dir), cid)
    except cast.CastError as e:
        raise CastNoteError("no_character", e.message) from None


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
    n = BOOK.new(doc, cid, by=by, kind=kind, frame=frame, x=x, y=y, text=_text(text))
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


def toggle_view(film_dir, cid: str, frame: str, by: str = "owner", b: str = None):
    """"Request this view" / "Undo": adds the open view request of this picture, or removes it. Returns the note or None."""
    _check_base(film_dir, b)
    doc = load(film_dir)
    for n in notes_of(doc, cid):
        if n.get("kind") == "view" and n.get("frame") == frame and not n.get("done"):
            delete(film_dir, cid, n["id"])
            return None
    return add(film_dir, cid, "view", frame, by=by)
