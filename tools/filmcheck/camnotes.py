"""Camera notes of an AE film (specs/039 R10, data-model "Camera note"): films/<f>/camera/notes.json on pins.py.

Group "shots"; a note is pinned on one option's still: {id, shot, option, x, y, text}. Every write names the base it
was made on; an old base is refused ("changed", exit 4). "Send notes to Claude" starts a lot; the fix job runs
`camera suggest --shots <noted> --keep-others` then `camera stills --shots …`, so the other shots keep every byte."""
import json
import sys
from pathlib import Path

from filmcheck import camsuggest, pins

NOTES = pins.Book("camera/notes.json", "shots")


class CamNoteError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message

    def exit_code(self) -> int:
        return 4 if self.code == "changed" else 2


def _wrap(fn):
    def go(*a, **kw):
        try:
            return fn(*a, **kw)
        except pins.PinError as e:
            raise CamNoteError(e.code, e.message) from None
    go.__name__, go.__doc__ = fn.__name__, fn.__doc__
    return go


def base(d: Path) -> str:
    return NOTES.base(d)


@_wrap
def add(d: Path, shot: str, option: int, x, y, text: str, by: str = "owner", b: str = None) -> dict:
    NOTES.check_base(d, b)
    shot = (shot or "").strip().upper()
    o = camsuggest.load(d) or {}
    row = (o.get("shots") or {}).get(shot)
    if not row:
        raise CamNoteError("bad_shot", f"no camera options for {shot or '?'}")
    try:
        option = int(option)
    except (TypeError, ValueError):
        raise CamNoteError("bad_note", "option is a number") from None
    if option not in {x["n"] for x in row["options"]}:
        raise CamNoteError("bad_note", f"{shot} has no option {option}")
    x, y = pins.xy(x, y)
    book = NOTES.load(d)
    n = NOTES.new(book, shot, by=by, shot=shot, option=option, x=x, y=y, text=pins.text(text))
    NOTES.write(d, book)
    return n


@_wrap
def remove(d: Path, nid: str, b: str = None) -> None:
    doc = NOTES.load(d)
    for key, n in NOTES.all_notes(doc):
        if n.get("id") == nid:
            NOTES.delete(d, key, nid, b)
            return
    raise CamNoteError("no_note", f"no note {nid}")


@_wrap
def reply(d: Path, nid: str, text: str, done: bool = None, b: str = None) -> dict:
    return NOTES.reply(d, nid, text, done, b)


def open_notes(d: Path) -> dict:
    """{shot: [open notes]}."""
    try:
        return NOTES.open_by(d)
    except pins.PinError:
        return {}


def open_shots(d: Path) -> list:
    return [s for s in _order(d) if s in open_notes(d)]


def _order(d: Path) -> list:
    o = camsuggest.load(d) or {}
    return list((o.get("shots") or {}).keys())


def summary(d: Path) -> str:
    """"N camera notes on: S3, S7" (film order) for the revise decision."""
    by = open_notes(d)
    n = sum(len(v) for v in by.values())
    if not n:
        return ""
    order = _order(d) or sorted(by)
    return f"{n} camera note{'' if n == 1 else 's'} on: {', '.join(s for s in order if s in by)}"


def start_lot(d: Path, job: str, shots=None) -> dict:
    return NOTES.start_lot(d, job, shots)


def end_lot(d: Path, job: str = None, error: str = None) -> None:
    try:
        NOTES.end_lot(d, job, error)
    except pins.PinError:
        pass


def cli(a, d: Path) -> int:
    try:
        if a.ncmd == "add":
            n = add(d, a.shot, a.n, a.x, a.y, a.text, b=a.base)
            print(json.dumps(n, ensure_ascii=False) if a.json else f"✓ note {n['id']} on {n['shot']} option {n['option']}")
            return 0
        if a.ncmd == "remove":
            remove(d, a.id, b=a.base)
            print(f"✓ note {a.id} removed")
            return 0
        doc = NOTES.load(d)
        if a.json:
            print(json.dumps({"base": NOTES.base(d), **doc}, ensure_ascii=False))
            return 0
        print(f"base {NOTES.base(d)}")
        for key, n in NOTES.all_notes(doc):
            mark = "✓" if n.get("done") else "○"
            print(f"{key} o{n.get('option')} {n['id']} {mark} ({n.get('x')}, {n.get('y')}) {n['text']}"
                  + (f"\n    ↳ {n['reply']}" if n.get("reply") else ""))
        return 0
    except (CamNoteError, pins.PinError) as e:
        print(f"✗ {e.message}", file=sys.stderr)
        return e.exit_code()
