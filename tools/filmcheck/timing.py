"""Shot lengths of an After Effects film: films/<film>/timing.json (specs/035 data-model, research R1, R2).

One source for the draft, the fit suggestions, Sound and the final render: {version 1, fps, frames {S#: n},
history [{frames, narration_at, at, by, why}] (≤ 50, the state before each accepted change), origin {frames, at}}.
A change of shot lengths moves narration.json's line starts with their shots and writes both files under one lock
(timing.lock). Old films get timing.json from the real lengths of a build (shots_<proj>.json / build-shots.json)."""
import hashlib
import json
from pathlib import Path

from filmcheck import shotnotes

VERSION = 1
MIN_FRAMES = 6                 # 0.2 s at 30 fps
HISTORY_MAX = 50


class TimingError(Exception):
    """code: missing (2) · bad (2) · changed (4) · origin (1) · bad_shot (1)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message

    def exit_code(self) -> int:
        return {"changed": 4, "missing": 2, "bad": 2}.get(self.code, 1)


def path(d: Path) -> Path:
    return Path(d) / "timing.json"


def lock(d: Path):
    return shotnotes.locked(Path(d) / "timing")          # films/<film>/timing.lock


def _dump(doc) -> bytes:
    return (json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


def film(d: Path) -> dict:
    """{fps, shots: [id]} from film.json."""
    try:
        f = json.loads((Path(d) / "film.json").read_text(encoding="utf-8"))
        shots = [str(s) for s in f["shots"]]
        fps = f.get("fps") or 30
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise TimingError("bad", f"film.json cannot be read: {e}") from None
    if not shots:
        raise TimingError("bad", "film.json has no shots")
    return {"fps": fps, "shots": shots}


def check(doc: dict, f: dict) -> None:
    if not isinstance(doc, dict) or doc.get("version") != VERSION:
        raise TimingError("bad", "timing.json: version must be 1")
    fr = doc.get("frames")
    if not isinstance(fr, dict):
        raise TimingError("bad", "timing.json: frames is missing")
    miss = [s for s in f["shots"] if s not in fr]
    extra = [s for s in fr if s not in f["shots"]]
    if miss or extra:
        raise TimingError("bad", "timing.json: frames must list every shot of film.json"
                          + (f" (missing {', '.join(miss)})" if miss else "") + (f" (not shots: {', '.join(extra)})" if extra else ""))
    for s, n in fr.items():
        if not isinstance(n, int) or isinstance(n, bool) or n < MIN_FRAMES:
            raise TimingError("bad", f"timing.json: {s} must be a whole number of frames, at least {MIN_FRAMES}")
    if len(doc.get("history") or []) > HISTORY_MAX:
        raise TimingError("bad", f"timing.json: history keeps at most {HISTORY_MAX} entries")


def load(d: Path):
    """timing.json checked against film.json, or None when the film has none yet."""
    p = path(d)
    if not p.is_file():
        return None
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise TimingError("bad", f"timing.json cannot be read: {e}") from None
    f = film(d)
    check(doc, f)
    doc["frames"] = {s: doc["frames"][s] for s in f["shots"]}          # film order
    doc.setdefault("history", [])
    doc["fps"] = f["fps"]
    return doc


def require(d: Path) -> dict:
    doc = load(d)
    if doc is None:
        raise TimingError("missing", "no timing.json yet: build the film once (ae draft) to measure its shots")
    return doc


def save(d: Path, doc: dict) -> None:
    """Write timing.json atomically (the caller holds lock(d) when it read the file first)."""
    doc["history"] = (doc.get("history") or [])[-HISTORY_MAX:]
    check(doc, film(d))
    shotnotes.write_atomic(path(d), _dump(doc))


def base(d: Path) -> str:
    """16 hex characters of timing.json's bytes ("0"*16 when there is none): the --base of the animatic commands."""
    p = path(d)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.is_file() else "0" * 16


def bounds(doc: dict, exact: bool = False) -> list:
    """[{id, t0, t1}] in seconds, in film order (rounded to 0.1 ms unless exact)."""
    fps, t, out = float(doc["fps"]), 0, []
    r = (lambda x: x) if exact else (lambda x: round(x, 4))
    for s, n in doc["frames"].items():
        out.append({"id": s, "t0": r(t / fps), "t1": r((t + n) / fps)})
        t += n
    return out


def duration(doc: dict) -> float:
    return round(sum(doc["frames"].values()) / float(doc["fps"]), 4)


def _marks(src) -> list:
    """[[t0, t1, label, id]] from a marks file (shots_<proj>.json, build-shots.json) or a list."""
    if isinstance(src, (str, Path)):
        src = json.loads(Path(src).read_text(encoding="utf-8"))
    if isinstance(src, dict):
        src = src.get("shots") or []
    return src


def from_marks(d: Path, marks, by: str = "build") -> dict:
    """Write timing.json from the real lengths of a build when the film has none (an old film). Returns the doc."""
    with lock(d):
        doc = load(d)
        if doc is not None:
            return doc
        f = film(d)
        fps = float(f["fps"])
        fr = {}
        for m in _marks(marks):
            t0, t1, sid = float(m[0]), float(m[1]), str(m[3] if len(m) > 3 else m[2])
            fr[sid] = max(MIN_FRAMES, int(round((t1 - t0) * fps)))
        miss = [s for s in f["shots"] if s not in fr]
        if miss:
            raise TimingError("bad", f"the build marks have no length for {', '.join(miss)}")
        doc = {"version": VERSION, "fps": f["fps"], "frames": {s: fr[s] for s in f["shots"]}, "history": [],
               "origin": {"frames": {s: fr[s] for s in f["shots"]}, "at": shotnotes.now_iso(), "by": by}}
        save(d, doc)
        return doc


# ---------- lines (R2) ----------
def _narration_path(d: Path) -> Path:
    return Path(d) / "narration.json"


def _read_narration(d: Path) -> dict:
    p = _narration_path(d)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise TimingError("missing", f"narration.json cannot be read: {e}") from None


def start(d: Path, by: str = "claude") -> dict:
    """The Animatic step begins: keep the lengths of this moment as `origin` (once; Undo stops there, FR-015) and
    write narration.json in the form this module writes it, so an Undo gives back the same bytes."""
    with lock(d):
        doc = require(d)
        if not doc.get("origin"):
            doc["origin"] = {"frames": dict(doc["frames"]), "at": shotnotes.now_iso(), "by": by}
            save(d, doc)
        if _narration_path(d).is_file():
            nar = _read_narration(d)
            data = _dump(nar)
            if _narration_path(d).read_bytes() != data:
                shotnotes.write_atomic(_narration_path(d), data)
        return doc


def assign(spans: list, bnds: list) -> dict:
    """{line id: shot id}: the shot holding most of the line [a, b] (R2); a line past the last cut belongs to the last shot."""
    out = {}
    for lid, a, b in spans:
        best, got = None, -1.0
        for s in bnds:
            ov = min(b, s["t1"]) - max(a, s["t0"])
            if ov > got + 1e-9:
                best, got = s["id"], ov
        if got <= 0:                                  # a zero-length line: the shot it starts in
            best = next((s["id"] for s in bnds if s["t0"] <= a < s["t1"]), bnds[-1]["id"])
        out[lid] = best
    return out


def lines(d: Path, doc: dict = None) -> list:
    """[{id, para, at, end, last_word_end, first_word_at, shot}] in film order (data-model "Câu thoại có mốc").
    `end` = at + the line's audio length (dur.json); the speech is [first word, last word] from words.json."""
    from filmcheck import qc
    doc = doc or require(d)
    try:
        nar = qc.load_narration(Path(d))
    except qc.QcError as e:
        raise TimingError("missing", str(e)) from None
    if nar is None:
        raise TimingError("missing", "no narration.json yet: the voice comes before the Animatic")
    raw = _read_narration(d)
    durs = {}
    if raw.get("durations_file"):
        try:
            durs = json.loads((Path(d) / raw["durations_file"]).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            durs = {}
    rows = []
    for ln in nar["lines"]:
        ws = ln["words"]
        first = min(s for _, s, _ in ws)
        last = max(e for _, _, e in ws)
        end = ln["at"] + float(durs[ln["id"]]) if ln["id"] in durs else last
        rows.append({"id": ln["id"], "para": ln["para"], "at": ln["at"], "end": round(end, 4),
                     "first_word_at": round(first, 4), "last_word_end": round(last, 4)})
    owner = assign([(r["id"], r["first_word_at"], r["last_word_end"]) for r in rows], bounds(doc))
    for r in rows:
        r["shot"] = owner[r["id"]]
    return rows


def shift(d: Path, new_frames: dict, *, head: dict = None, by: str = "claude", why: str = "", expect: str = None) -> dict:
    """Change shot lengths and move the lines with their shots (R2): at_new = t0_new + (at_old − t0_old) − head[shot].
    Both files are written under timing.lock; the state before goes to history (Undo). `expect` = base(d) the caller saw."""
    head = head or {}
    with lock(d):
        if expect is not None and expect != base(d):
            raise TimingError("changed", "the shot lengths changed since you looked: reload and try again")
        doc = require(d)
        bad = [s for s in new_frames if s not in doc["frames"]]
        if bad:
            raise TimingError("bad_shot", f"not a shot of this film: {', '.join(bad)}")
        old_b = {b["id"]: b for b in bounds(doc, exact=True)}
        rows = lines(d, doc)
        nar = _read_narration(d)
        frames = dict(doc["frames"])
        frames.update({s: int(n) for s, n in new_frames.items()})
        new = dict(doc, frames=frames)
        check(new, film(d))
        new_b = {b["id"]: b for b in bounds(new, exact=True)}
        owner = {r["id"]: r["shot"] for r in rows}
        before = {ln["id"]: ln["at"] for ln in nar.get("lines") or []}
        for ln in nar.get("lines") or []:
            s = owner.get(ln["id"])
            if s is None:
                continue
            at = new_b[s]["t0"] + (float(ln["at"]) - old_b[s]["t0"]) - float(head.get(s) or 0)
            ln["at"] = round(max(0.0, at), 4)
        hist = list(doc.get("history") or [])
        hist.append({"frames": dict(doc["frames"]), "narration_at": before, "at": shotnotes.now_iso(), "by": by, "why": why})
        new["history"] = hist[-HISTORY_MAX:]
        save(d, new)
        shotnotes.write_atomic(_narration_path(d), _dump(nar))
        return new


def undo(d: Path, *, expect: str = None) -> dict:
    """Give back the lengths and line starts from before the last accepted change; refused at the origin (FR-015)."""
    with lock(d):
        if expect is not None and expect != base(d):
            raise TimingError("changed", "the shot lengths changed since you looked: reload and try again")
        doc = require(d)
        hist = list(doc.get("history") or [])
        if not hist:
            raise TimingError("origin", "nothing to undo: these are the lengths the Animatic started with")
        last = hist.pop()
        nar = _read_narration(d)
        for ln in nar.get("lines") or []:
            if ln["id"] in last.get("narration_at", {}):
                ln["at"] = last["narration_at"][ln["id"]]
        doc["frames"] = dict(last["frames"])
        doc["history"] = hist
        save(d, doc)
        shotnotes.write_atomic(_narration_path(d), _dump(nar))
        return doc
