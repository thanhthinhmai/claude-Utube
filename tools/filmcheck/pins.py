"""Pinned notes shared by the cast sheet (specs/034, cast-notes.json) and the Animatic draft (specs/035, animatic/notes.json).

A book of notes is one JSON file `{version: 1, <group>: {<key>: {notes: [note]}}, lot?, last_lot?, failed_lot?}`; the
group is "characters" (cast) or "shots" (animatic). A note is pinned on a picture (frame + x/y in percent), or general
(frame null). Every write names the base it was made on (sha256 of the file, 16 hex); an old base is refused with the
current content ("changed"). "Send notes to Claude" starts a lot: the open notes at that moment; notes written later
wait for the next lot. A failed round keeps the notes open and records the error (research R9)."""
import hashlib
import json
import os
import secrets
import time
from pathlib import Path

TEXT_MAX = 2000


class PinError(Exception):
    def __init__(self, code: str, message: str, current: dict = None):
        super().__init__(message)
        self.code, self.message, self.current = code, message, current

    def exit_code(self) -> int:
        return 4 if self.code == "changed" else 2


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def text(t, what: str = "a note") -> str:
    t = (t or "").strip() if isinstance(t, str) else ""
    if not 1 <= len(t) <= TEXT_MAX:
        raise PinError("bad_text", f"{what} is 1 to {TEXT_MAX} characters")
    return t


def xy(x, y) -> tuple:
    try:
        x, y = float(x), float(y)
    except (TypeError, ValueError):
        raise PinError("bad_pin", "x and y are numbers from 0 to 100") from None
    if not (0 <= x <= 100 and 0 <= y <= 100):
        raise PinError("bad_pin", "x and y are numbers from 0 to 100")
    return round(x, 1), round(y, 1)


class Book:
    """One notes file of a film: rel is its path inside the film folder, group the name of its keyed object."""

    def __init__(self, rel: str, group: str):
        self.rel, self.group = rel, group

    # ---------- the file ----------
    def path(self, film_dir) -> Path:
        return Path(film_dir) / self.rel

    def raw(self, film_dir) -> bytes:
        try:
            return self.path(film_dir).read_bytes()
        except FileNotFoundError:
            return b""

    def empty(self) -> dict:
        return {"version": 1, self.group: {}}

    def load(self, film_dir) -> dict:
        raw = self.raw(film_dir)
        if not raw:
            return self.empty()
        name = Path(self.rel).name
        try:
            doc = json.loads(raw.decode("utf-8"))
        except ValueError as e:
            raise PinError("bad_notes", f"{name} cannot be read: {e}")
        if not isinstance(doc, dict) or not isinstance(doc.get(self.group, {}), dict):
            raise PinError("bad_notes", f"{name} must have a {self.group} object")
        doc.setdefault("version", 1)
        doc.setdefault(self.group, {})
        return doc

    def base(self, film_dir) -> str:
        return sha(self.raw(film_dir))

    def current(self, film_dir) -> dict:
        return {"base": self.base(film_dir), "doc": self.load(film_dir)}

    def write(self, film_dir, doc: dict) -> str:
        p = self.path(film_dir)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
        tmp.write_bytes(data)
        os.replace(tmp, p)
        return sha(data)

    def check_base(self, film_dir, b) -> None:
        if b is not None and b != self.base(film_dir):
            raise PinError("changed", "the notes changed since you opened them: reload", self.current(film_dir))

    # ---------- notes ----------
    def notes_of(self, doc: dict, key: str) -> list:
        return doc[self.group].setdefault(key, {"notes": []}).setdefault("notes", [])

    def all_notes(self, doc: dict):
        for key, v in doc[self.group].items():
            for n in (v or {}).get("notes", []):
                yield key, n

    def open_by(self, film_dir) -> dict:
        out = {}
        for key, n in self.all_notes(self.load(film_dir)):
            if not n.get("done"):
                out.setdefault(key, []).append(n)
        return out

    def open_counts(self, film_dir) -> dict:
        return {k: len(v) for k, v in self.open_by(film_dir).items()}

    def find(self, doc: dict, key: str, nid: str) -> dict:
        for n in doc[self.group].get(key, {}).get("notes", []):
            if n.get("id") == nid:
                return n
        raise PinError("no_note", f"no note {nid} on {key}")

    def new(self, doc: dict, key: str, by: str = "owner", **fields) -> dict:
        t = now()
        n = {"id": f"n-{secrets.token_hex(4)}", **fields, "done": False, "by": by or "owner", "created": t,
             "updated": t, "reply": None}
        self.notes_of(doc, key).append(n)
        return n

    def delete(self, film_dir, key: str, nid: str, b: str = None) -> None:
        self.check_base(film_dir, b)
        doc = self.load(film_dir)
        n = self.find(doc, key, nid)
        self.notes_of(doc, key).remove(n)
        if doc.get("lot") and nid in doc["lot"].get("notes", []):
            doc["lot"]["notes"].remove(nid)
        self.write(film_dir, doc)

    def reply(self, film_dir, nid: str, words: str, done: bool = None, b: str = None) -> dict:
        """Claude's answer to a note; done=True ticks it, done=False opens it again."""
        self.check_base(film_dir, b)
        doc = self.load(film_dir)
        for _, n in self.all_notes(doc):
            if n.get("id") == nid:
                n["reply"], n["updated"] = text(words, "a reply"), now()
                if done is not None:
                    n["done"] = bool(done)
                self.write(film_dir, doc)
                return n
        raise PinError("no_note", f"no note {nid}")

    # ---------- rounds ----------
    def start_lot(self, film_dir, job: str, keys=None) -> dict:
        """"Send notes to Claude": the open notes now (of these keys, or all) form the lot this job answers."""
        doc = self.load(film_dir)
        ids = [n["id"] for k, n in self.all_notes(doc) if not n.get("done") and (not keys or k in keys)]
        doc["lot"] = {"job": job, "notes": ids, "since": now()}
        doc.pop("failed_lot", None)
        doc.pop("last_lot", None)
        self.write(film_dir, doc)
        return doc["lot"]

    def end_lot(self, film_dir, job: str = None, error: str = None) -> None:
        """The round is over; with an error the notes stay open and the page offers to send them again."""
        doc = self.load(film_dir)
        lot = doc.get("lot")
        if lot is None or (job and lot.get("job") != job):
            return
        doc.pop("lot")
        if error:
            doc["failed_lot"] = {"job": lot.get("job"), "error": str(error)[:300], "at": now()}
        else:
            doc["last_lot"] = {"job": lot.get("job"), "notes": list(lot.get("notes") or []), "at": now()}
        self.write(film_dir, doc)

    def summary(self, film_dir) -> str:
        """"N notes on: a, b" for the revise decision."""
        by = self.open_by(film_dir)
        n = sum(len(v) for v in by.values())
        return f"{n} note{'' if n == 1 else 's'} on: {', '.join(sorted(by))}" if n else ""
