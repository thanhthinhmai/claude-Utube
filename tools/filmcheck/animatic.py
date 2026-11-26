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


# ---------- fit suggestions (US2, research R3, R5) ----------
def _fit_doc(d: Path) -> dict:
    return _read(adir(d) / "fit.json", {}) or {}


def _shot_sha(doc: dict, rows: list, shot: str) -> str:
    """What a skip was about: the shot's length and the starts of its lines (FR-013)."""
    ats = [(r["id"], r["at"]) for r in rows if r["shot"] == shot]
    return _sha(json.dumps([doc["frames"][shot], ats]).encode())


def motions(keys: list, end_new: float) -> list:
    """The shot's keyframed motions a shorter shot ending at end_new (seconds in the shot) drops or squeezes (R5)."""
    out = []
    for k in keys or []:
        t0, t1 = float(k.get("t0", 0)), float(k.get("t1", 0))
        name = f"{k.get('layer', '?')} · {k.get('prop', '?')}"
        if t0 >= end_new - 1e-6:
            out.append({"layer": k.get("layer"), "prop": k.get("prop"), "name": name, "t0": t0, "t1": t1, "effect": "drop"})
        elif t1 > end_new + 1e-6:
            ratio = round((t1 - t0) / max(end_new - t0, 1e-6), 2)
            out.append({"layer": k.get("layer"), "prop": k.get("prop"), "name": name, "t0": t0, "t1": t1,
                        "effect": "clip" if ratio > SQUEEZE_MAX else "squeeze", "ratio": ratio})
    return out


@_wrap
def fit(d: Path, all_states: bool = False) -> list:
    """Per-shot suggestions: the shot ends PAD after its last word and its first line starts at the cut (head dropped;
    the film's first shot keeps its head). [{shot, frames, frames_new, delta_s, end_new, head, very_short, motions,
    state}] for shots with lines whose end moves more than one frame or whose head is longer than one frame.
    Skipped suggestions are left out unless all_states (they come back when the shot's length or lines change)."""
    doc = timing.require(d)
    fps = float(doc["fps"])
    rows = timing.lines(d, doc)
    keys = _read(adir(d) / "keys.json", {}) or {}
    skipped = _fit_doc(d).get("skipped") or {}
    out = []
    for i, b in enumerate(timing.bounds(doc, exact=True)):
        mine = [r for r in rows if r["shot"] == b["id"]]
        if not mine:
            continue
        first = min(r["first_word_at"] for r in mine) - b["t0"]
        last = max(r["last_word_end"] for r in mine) - b["t0"]
        head = 0.0 if i == 0 else max(0.0, first)
        need = last - head                                     # the last word may never be cut
        n_new = max(timing.MIN_FRAMES, int(round((need + PAD) * fps)))
        while n_new / fps < need - 1e-6:
            n_new += 1
        n = doc["frames"][b["id"]]
        if abs(n_new - n) <= 1 and head * fps <= 1:
            continue
        sha = _shot_sha(doc, rows, b["id"])
        state = "skipped" if skipped.get(b["id"]) == sha else "new"
        if state == "skipped" and not all_states:
            continue
        end_new = n_new / fps
        out.append({"shot": b["id"], "frames": n, "frames_new": n_new, "delta_s": round((n_new - n) / fps, 3),
                    "end_new": round(end_new, 3), "head": round(head, 3), "very_short": end_new < VERY_SHORT,
                    "motions": motions(keys.get(b["id"]), end_new) if n_new - n < 0 else [], "state": state})
    return out


def _check_base(d: Path, expect) -> None:
    if expect is not None and expect != timing.base(d):
        raise AnimaticError("changed", "the shot lengths changed since you looked: reload and try again")


@_wrap
def accept(d: Path, shots, by: str = "claude", expect: str = None) -> dict:
    """Accept the suggestions of these shots ("all" = every open one): one history entry (Undo gives it all back).
    Returns {accepted: [shot], silence}."""
    _check_base(d, expect)
    sug = {s["shot"]: s for s in fit(d, all_states=True)}
    if shots == "all":
        pick = [s for s, x in sug.items() if x["state"] == "new"]
    else:
        pick = [str(s).upper() for s in shots]
        bad = [s for s in pick if s not in sug]
        if bad:
            raise AnimaticError("bad_shot", f"no suggestion for {', '.join(bad)}")
    if not pick:
        raise AnimaticError("bad_shot", "no open suggestion to accept")
    timing.shift(d, {s: sug[s]["frames_new"] for s in pick}, head={s: sug[s]["head"] for s in pick}, by=by,
                 why="fit " + ",".join(pick), expect=expect)
    f = _fit_doc(d)
    for s in pick:
        (f.get("skipped") or {}).pop(s, None)
    _write_fit(d, f)
    return {"accepted": pick, "silence": silence(d)}


def _write_fit(d: Path, f: dict) -> None:
    from filmcheck import shotnotes
    shotnotes.write_atomic(adir(d) / "fit.json", (json.dumps({"skipped": f.get("skipped") or {}}, indent=1) + "\n").encode())


@_wrap
def skip(d: Path, shot: str, expect: str = None) -> dict:
    """Leave this shot as it is; its suggestion comes back when its length or lines change (FR-013)."""
    shot = str(shot).upper()
    with timing.lock(d):
        _check_base(d, expect)
        doc = timing.require(d)
        if shot not in doc["frames"]:
            raise AnimaticError("bad_shot", f"not a shot of this film: {shot}")
        rows = timing.lines(d, doc)
        f = _fit_doc(d)
        f.setdefault("skipped", {})[shot] = _shot_sha(doc, rows, shot)
        _write_fit(d, f)
    return {"skipped": shot}


@_wrap
def undo(d: Path, expect: str = None) -> dict:
    """Give back the lengths from before the last accepted change (refused at the origin, FR-015)."""
    try:
        timing.undo(d, expect=expect)
    except timing.TimingError as e:
        raise AnimaticError(e.code, e.message) from None
    return {"silence": silence(d)}


def can_undo(d: Path) -> bool:
    try:
        doc = timing.load(d)
    except timing.TimingError:
        return False
    return bool(doc and doc.get("history"))
