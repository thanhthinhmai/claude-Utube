"""Sound notes of an AE film (specs/037 US3, data-model "notes.json"): `sound/notes.json`, one list of notes per shot.

Like the cast notes (castnotes.py, specs/034) without pins: a note is written on a shot, Claude answers it (`reply`) and
ticks it (`done`). Every write names the base it was made on (sha256 of the file); an old base is refused (409
"changed"). "Send notes to Claude" starts a lot: the open notes at that moment; notes written later wait for the next."""
import hashlib
import json
import os
import re
import secrets
import time
from pathlib import Path

TEXT_MAX = 2000


class SoundNoteError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message

    def exit_code(self) -> int:
        return 4 if self.code == "changed" else 2


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def path(film_dir) -> Path:
    return Path(film_dir) / "sound" / "notes.json"


def _raw(film_dir) -> bytes:
    try:
        return path(film_dir).read_bytes()
    except FileNotFoundError:
        return b""


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def load(film_dir) -> dict:
    raw = _raw(film_dir)
    if not raw:
        return {"version": 1, "shots": {}}
    try:
        doc = json.loads(raw.decode("utf-8"))
    except ValueError as e:
        raise SoundNoteError("bad_notes", f"sound/notes.json cannot be read: {e}") from None
    if not isinstance(doc, dict) or not isinstance(doc.get("shots", {}), dict):
        raise SoundNoteError("bad_notes", "sound/notes.json must have a shots object")
    doc.setdefault("version", 1)
    doc.setdefault("shots", {})
    return doc


def base(film_dir) -> str:
    return _sha(_raw(film_dir))


def _write(film_dir, doc: dict) -> str:
    p = path(film_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, p)
    return _sha(data)


def _check_base(film_dir, b) -> None:
    if b is not None and b != base(film_dir):
        raise SoundNoteError("changed", "the sound notes changed since you opened them: reload")


def all_notes(doc: dict):
    for shot, ns in doc["shots"].items():
        for n in ns or []:
            yield shot, n


def open_counts(film_dir) -> dict:
    """{shot: open notes}."""
    out = {}
    for shot, n in all_notes(load(film_dir)):
        if not n.get("done"):
            out[shot] = out.get(shot, 0) + 1
    return out


def _shots(film_dir) -> list:
    from filmcheck import soundplan
    try:
        return list(soundplan.starts(soundplan.timing(film_dir)))
    except Exception:                        # no timing yet: any S<n>
        return []


def _shot(film_dir, shot: str) -> str:
    shot = (shot or "").strip().upper()
    known = _shots(film_dir)
    if not re.fullmatch(r"S\d{1,3}", shot) or (known and shot not in known):
        raise SoundNoteError("bad_shot", f"no shot {shot or '?'}" + (f" (shots: {', '.join(known)})" if known else ""))
    return shot


def _text(t, what: str = "a note") -> str:
    t = t.strip() if isinstance(t, str) else ""
    if not 1 <= len(t) <= TEXT_MAX:
        raise SoundNoteError("bad_text", f"{what} is 1 to {TEXT_MAX} characters")
    return t


def add(film_dir, shot: str, text: str, by: str = "owner", b: str = None) -> dict:
    _check_base(film_dir, b)
    shot = _shot(film_dir, shot)
    doc = load(film_dir)
    t = now()
    n = {"id": f"n-{secrets.token_hex(4)}", "text": _text(text), "done": False, "by": by or "owner", "created": t,
         "updated": t, "reply": None}
    doc["shots"].setdefault(shot, []).append(n)
    _write(film_dir, doc)
    return {**n, "shot": shot}


def delete(film_dir, shot: str, nid: str, b: str = None) -> None:
    _check_base(film_dir, b)
    shot = (shot or "").strip().upper()
    doc = load(film_dir)
    ns = doc["shots"].get(shot) or []
    n = next((x for x in ns if x.get("id") == nid), None)
    if n is None:
        raise SoundNoteError("no_note", f"no note {nid} on {shot}")
    ns.remove(n)
    if not ns:
        doc["shots"].pop(shot, None)
    if doc.get("lot") and nid in doc["lot"].get("notes", []):
        doc["lot"]["notes"].remove(nid)
    _write(film_dir, doc)


def reply(film_dir, nid: str, text: str, done: bool = None, b: str = None) -> dict:
    """Claude's answer to a note; done=True ticks it, done=False opens it again."""
    _check_base(film_dir, b)
    doc = load(film_dir)
    for shot, n in all_notes(doc):
        if n.get("id") == nid:
            n["reply"], n["updated"] = _text(text, "a reply"), now()
            if done is not None:
                n["done"] = bool(done)
            _write(film_dir, doc)
            return {**n, "shot": shot}
    raise SoundNoteError("no_note", f"no note {nid}")


def start_lot(film_dir, job: str) -> dict:
    """"Send notes to Claude": the open notes now form the lot this job answers."""
    doc = load(film_dir)
    ids = [n["id"] for _, n in all_notes(doc) if not n.get("done")]
    doc["lot"] = {"job": job, "notes": ids, "since": now()}
    doc.pop("failed_lot", None)
    doc.pop("last_lot", None)
    _write(film_dir, doc)
    return doc["lot"]


def end_lot(film_dir, job: str = None, error: str = None) -> None:
    """The round is over: Claude sent the mix again, or (job, error) the job failed or stopped (the notes stay open)."""
    if not path(film_dir).is_file():
        return
    doc = load(film_dir)
    lot = doc.get("lot")
    if lot is None or (job and lot.get("job") != job):
        return
    doc.pop("lot")
    if error:
        doc["failed_lot"] = {"job": lot.get("job"), "error": str(error)[:300], "at": now()}
    else:
        doc["last_lot"] = {"job": lot.get("job"), "notes": list(lot.get("notes") or []), "at": now()}
    _write(film_dir, doc)


def summary(film_dir) -> str:
    """"N notes on: S2, S5" for the revise decision."""
    by = open_counts(film_dir)
    n = sum(by.values())
    return f"{n} sound note{'' if n == 1 else 's'} on: {', '.join(sorted(by, key=lambda s: int(s[1:])))}" if n else ""


def show(film_dir) -> str:
    doc = load(film_dir)
    rows = [f"base {base(film_dir)}"]
    for shot in sorted(doc["shots"], key=lambda s: int(s[1:]) if s[1:].isdigit() else 0):
        for n in doc["shots"][shot]:
            mark = "✓" if n.get("done") else "○"
            rows.append(f"{shot} {n['id']} {mark} {n['text']}" + (f"\n    ↳ {n['reply']}" if n.get("reply") else ""))
    if doc.get("lot"):
        rows.append(f"lot: {len(doc['lot']['notes'])} note(s) sent to {doc['lot']['job']}")
    return "\n".join(rows)
