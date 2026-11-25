"""Versioned character rigs of the shared AE kit (specs/034 research R2, contracts/files.md → rigs.lock).

A rig version lives in tools/ae/kit/rigs/<family>/v<N>/ (ball.jsx + catalog.json) and never changes once it is in
tools/ae/rigs.lock: the lock holds the sha256 of every file of the folder (sorted by name, name + bytes). A change that
alters a picture is a new folder v<N+1> and a new lock line, so a character approved with ball@1 is drawn the same way
for ever (FR-019, FR-020)."""
import hashlib
import json
import re
from pathlib import Path

KIT = Path(__file__).resolve().parent / "kit"
RIGS = KIT / "rigs"
LOCK = Path(__file__).resolve().parent / "rigs.lock"
RIG_ID = re.compile(r"([a-z][a-z0-9]{0,15})@([1-9][0-9]{0,2})")


def parse(rig_id: str) -> tuple:
    m = RIG_ID.fullmatch(rig_id or "")
    if not m:
        raise ValueError(f"a rig id looks like ball@1, not {rig_id!r}")
    return m.group(1), int(m.group(2))


def folder(rig_id: str, root: Path = None) -> Path:
    fam, n = parse(rig_id)
    return (root or RIGS) / fam / f"v{n}"


def digest(rig_id: str, root: Path = None) -> str:
    d = folder(rig_id, root)
    if not d.is_dir():
        raise FileNotFoundError(f"no rig folder {d}")
    h = hashlib.sha256()
    for p in sorted(x for x in d.rglob("*") if x.is_file() and "__pycache__" not in x.parts):
        h.update(p.relative_to(d).as_posix().encode() + b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def load(lock: Path = None) -> dict:
    p = lock or LOCK
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(doc, dict):
        raise ValueError(f"{p} must be an object")
    return doc


def versions(family: str = None, lock: Path = None) -> list:
    """Locked rig ids, oldest first per family."""
    ids = [k for k in load(lock) if RIG_ID.fullmatch(k) and (family is None or parse(k)[0] == family)]
    return sorted(ids, key=lambda k: parse(k))


def latest(family: str = "ball", lock: Path = None):
    v = versions(family, lock)
    return v[-1] if v else None


def is_locked(rig_id: str, lock: Path = None) -> bool:
    return rig_id in load(lock)


def check(lock: Path = None, root: Path = None) -> list:
    """Locked ids whose folder changed or went missing."""
    bad = []
    for rid, want in load(lock).items():
        try:
            if digest(rid, root) != want:
                bad.append(rid)
        except (FileNotFoundError, ValueError):
            bad.append(rid)
    return bad


def lock(rig_id: str, lock: Path = None, root: Path = None) -> str:
    """Add a new version to the lock; an id already locked is refused (its folder is frozen)."""
    parse(rig_id)
    p = lock or LOCK
    doc = load(p)
    if rig_id in doc:
        raise ValueError(f"{rig_id} is already locked; a change is a new version")
    doc[rig_id] = digest(rig_id, root)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(dict(sorted(doc.items(), key=lambda kv: parse(kv[0]))), indent=2) + "\n")
    tmp.replace(p)
    return doc[rig_id]


def catalog(rig_id: str, root: Path = None) -> dict:
    """What the rig can draw (views, expressions, poses, walk, spec keys, hats)."""
    p = folder(rig_id, root) / "catalog.json"
    return json.loads(p.read_text(encoding="utf-8"))


def newer(rig_id: str, lock: Path = None):
    """The latest locked version of the same family when it is newer than rig_id, else None."""
    fam, n = parse(rig_id)
    top = latest(fam, lock)
    return top if top and parse(top)[1] > n else None
