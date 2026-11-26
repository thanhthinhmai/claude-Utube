"""The Animatic of an After Effects film (specs/035): the timeline of shots and lines, the silence of the narration
measured the same way as the film check (research R4), the draft's state, and the per-shot fit suggestions (R3, R5).

Files: timing.json (filmcheck.timing), animatic/draft.json, animatic/keys.json, animatic/fit.json (skipped
suggestions only), animatic/notes.json (pins, US3)."""
import hashlib
import json
from pathlib import Path

from filmcheck import rhythm, timing

PAD = 0.25                     # a shot ends this long after its last word (user choice 2026-11-26)
VERY_SHORT = 1.0               # a shot shorter than this after a change is flagged
SQUEEZE_MAX = 2.0              # a motion squeezed more than this is cut instead (R5)


class AnimaticError(Exception):
    """code: missing (2) · changed (4) · origin (1) · bad_shot (1) · not_ae (2)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message

    def exit_code(self) -> int:
        return {"changed": 4, "missing": 2, "not_ae": 2}.get(self.code, 1)


def _wrap(fn):
    def go(*a, **kw):
        try:
            return fn(*a, **kw)
        except timing.TimingError as e:
            raise AnimaticError(e.code, e.message) from None
    go.__name__, go.__doc__ = fn.__name__, fn.__doc__
    return go


def adir(d: Path) -> Path:
    return Path(d) / "animatic"


def _read(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def narration_sha(d: Path) -> str:
    p = Path(d) / "narration.json"
    return _sha(p.read_bytes()) if p.is_file() else ""


def code_sha(d: Path) -> str:
    """The film's code: ae/*.jsx and cast/cast.json."""
    d = Path(d)
    h = hashlib.sha256()
    for p in sorted((d / "ae").glob("*.jsx")) + [d / "cast" / "cast.json"]:
        if p.is_file():
            h.update(p.relative_to(d).as_posix().encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()[:16]


# ---------- timeline and silence (US1) ----------
def _words(d: Path):
    """(narration, [(s, e, para)] in film time, sentences) from narration.json and the voice files (qc)."""
    from filmcheck import qc
    try:
        nar = qc.load_narration(Path(d))
    except qc.QcError as e:
        raise AnimaticError("missing", str(e)) from None
    if nar is None:
        raise AnimaticError("missing", "no narration.json yet: the voice comes before the Animatic")
    words = sorted((s, e, ln["para"]) for ln in nar["lines"] for (_, s, e) in ln["words"])
    sents = rhythm.sentences(nar["lines"], qc.line_texts(Path(d), nar))
    return nar, words, sents


@_wrap
def timeline(d: Path) -> dict:
    """{duration, fps, shots: [{id, t0, t1, frames, lines: [{id, at, end, last_word_end, text}]}]}."""
    doc = timing.require(d)
    rows = timing.lines(d, doc)
    texts = {}
    from filmcheck import qc
    try:
        nar = qc.load_narration(Path(d))
        texts = qc.line_texts(Path(d), nar) if nar else {}
    except qc.QcError:
        texts = {}
    shots = []
    for b in timing.bounds(doc):
        shots.append({**b, "frames": doc["frames"][b["id"]],
                      "lines": [{"id": r["id"], "at": r["at"], "end": r["end"], "last_word_end": r["last_word_end"],
                                 "text": texts.get(r["id"], "")} for r in rows if r["shot"] == b["id"]]})
    return {"duration": timing.duration(doc), "fps": doc["fps"], "shots": shots}


@_wrap
def measures(d: Path) -> dict:
    """rhythm.measure on the narration and the shots of timing.json: the film check's numbers before any render."""
    doc = timing.require(d)
    _, words, sents = _words(d)
    dur = max(timing.duration(doc), max(e for _, e, _ in words))
    m, _ = rhythm.measure(sents, words, dur, shots=timing.bounds(doc))
    return m


def silence(d: Path) -> float:
    """silence_ratio exactly as the film check measures it (R4)."""
    return measures(d).get("silence_ratio", 0.0)


@_wrap
def longest_gaps(d: Path, n: int = 3) -> list:
    """The n longest silent gaps between words: [{t0, t1, length, shot}], longest first."""
    doc = timing.require(d)
    _, words, _ = _words(d)
    gaps, ce = [], None
    for s, e, _ in words:
        if ce is not None and s > ce:
            gaps.append((ce, s))
        ce = e if ce is None else max(ce, e)
    bnds = timing.bounds(doc)
    out = []
    for a, b in sorted(gaps, key=lambda g: g[0] - g[1])[:n]:
        sid = next((x["id"] for x in bnds if x["t0"] <= a < x["t1"]), bnds[-1]["id"])
        out.append({"t0": round(a, 3), "t1": round(b, 3), "length": round(b - a, 3), "shot": sid})
    return out


# ---------- the draft ----------
def draft_info(d: Path):
    return _read(adir(d) / "draft.json")


def draft_current(d: Path) -> bool:
    """The draft was built from the current shot lengths, narration and code."""
    info = draft_info(d)
    if not info or not (adir(d) / "draft.mp4").is_file():
        return False
    try:
        doc = timing.load(d)
    except timing.TimingError:
        return False
    return (doc is not None and info.get("frames") == doc["frames"] and info.get("narration_sha") == narration_sha(d)
            and info.get("code_sha", code_sha(d)) == code_sha(d))


def step_state(d: Path) -> tuple:
    """(state, note) of the Animatic step: todo · done · stale."""
    info = draft_info(d)
    if not info or not (adir(d) / "draft.mp4").is_file():
        return ("todo", "")
    if draft_current(d):
        return ("done", "")
    try:
        doc = timing.load(d)
    except timing.TimingError as e:
        return ("stale", e.message)
    if doc is None or info.get("frames") != doc["frames"]:
        return ("stale", "shot lengths changed")
    if info.get("narration_sha") != narration_sha(d):
        return ("stale", "the voice changed")
    return ("stale", "the film's code changed")


# ---------- notes (counts; the notes themselves are US3) ----------
def open_notes(d: Path) -> dict:
    doc = _read(adir(d) / "notes.json", {}) or {}
    out = {}
    for s, ns in (doc.get("shots") or {}).items():
        n = sum(1 for x in ns if isinstance(x, dict) and x.get("state", "open") == "open")
        if n:
            out[s] = n
    return out


def problems(d: Path) -> list:
    """What stops the animatic approval (silence is asked separately: approve anyway)."""
    d = Path(d)
    why = []
    if not draft_current(d):
        why.append(f"there is no current draft (run: sh bin/studio ae draft {d.name})")
    why += [f"{s}: {n} open note(s)" for s, n in open_notes(d).items()]
    return why
