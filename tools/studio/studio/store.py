"""State under .studio/: atomic JSON writes, exclusive creates, per-id locks (research.md §2–3).
Online mode (specs/007): jobs, reviews and decisions live in SQLite (db.py) instead; files of each
customer live under $STUDIO_DATA/accounts/<id>/ (see `as_account`)."""
import contextlib
import contextvars
import datetime as dt
import fcntl
import json
import os
import time
from pathlib import Path

# Tests replace this to move time forward
clock = time.time


class StudioError(Exception):
    """An error with a stable code, an HTTP status and a Vietnamese message."""

    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def mode() -> str:
    """`local` (phase 1, default) or `online` (specs/007)."""
    return "online" if os.environ.get("STUDIO_MODE") == "online" else "local"


def project_root() -> Path:
    """The studio code folder: library, library.lock, skills. Shared by every customer."""
    env = os.environ.get("STUDIO_ROOT")
    return Path(env).resolve() if env else Path(__file__).resolve().parents[3]


_account_root = contextvars.ContextVar("account_root", default=None)


def root() -> Path:
    """Where films/, references/ and my-styles/ are: the project in local mode, the customer's folder online."""
    return _account_root.get() or project_root()


def account_dir(account_id: str) -> Path:
    from . import db
    return db.data_dir() / "accounts" / account_id


@contextlib.contextmanager
def as_account(account_id: str):
    """Serve files of this customer only (online mode)."""
    d = account_dir(account_id)
    for sub in ("films", "references", "my-styles"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    tok = _account_root.set(d)
    try:
        yield d
    finally:
        _account_root.reset(tok)


def state_dir() -> Path:
    d = project_root() / ".studio"
    for sub in ("jobs", "reviews", "locks"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    return d


def now_iso() -> str:
    return dt.datetime.fromtimestamp(clock(), dt.timezone.utc).isoformat(timespec="seconds")


def age_seconds(iso: str) -> float:
    try:
        return clock() - dt.datetime.fromisoformat(iso).timestamp()
    except (TypeError, ValueError):
        return float("inf")


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def create_exclusive(path: Path, data) -> bool:
    """Create `path` only if it does not exist yet; never shows a half-written file. False if it existed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    try:
        os.link(tmp, path)
        return True
    except FileExistsError:
        return False
    finally:
        tmp.unlink(missing_ok=True)


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _lock_dir() -> Path:
    if mode() == "online":
        from . import db
        d = db.data_dir() / "locks"
        d.mkdir(parents=True, exist_ok=True)
        return d
    return state_dir() / "locks"


@contextlib.contextmanager
def lock(name: str):
    with open(_lock_dir() / f"{name}.lock", "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


# ---------- documents: jobs, reviews, decisions (same JSON in both modes) ----------
_DIRS = {"job": ("jobs", ".json"), "review": ("reviews", ".json"), "decision": ("reviews", ".decision.json")}


def _doc_path(kind: str, ident: str) -> Path:
    sub, ext = _DIRS[kind]
    return state_dir() / sub / f"{ident}{ext}"


def _row(kind: str, ident: str, data: dict):
    owner = data.get("owner") or "local"
    created = data.get("started_at") or data.get("created_at") or data.get("at") or now_iso()
    return (kind, ident, owner, data.get("status"), json.dumps(data, ensure_ascii=False), created, time.time_ns())


def doc_get(kind: str, ident: str):
    if mode() == "local":
        return read_json(_doc_path(kind, ident))
    from . import db
    with db.read() as con:
        r = con.execute("SELECT data FROM docs WHERE kind = ? AND id = ?", (kind, ident)).fetchone()
    return json.loads(r[0]) if r else None


def doc_put(kind: str, ident: str, data: dict) -> None:
    if mode() == "local":
        return write_json(_doc_path(kind, ident), data)
    from . import db
    with db.tx() as con:
        con.execute("INSERT OR REPLACE INTO docs VALUES (?, ?, ?, ?, ?, ?, ?)", _row(kind, ident, data))


def doc_create(kind: str, ident: str, data: dict) -> bool:
    """Create only if absent (first decision wins). False if it existed."""
    if mode() == "local":
        return create_exclusive(_doc_path(kind, ident), data)
    import sqlite3
    from . import db
    try:
        with db.tx() as con:
            con.execute("INSERT INTO docs VALUES (?, ?, ?, ?, ?, ?, ?)", _row(kind, ident, data))
        return True
    except sqlite3.IntegrityError:
        return False


def doc_list(kind: str, owner: str = None) -> list:
    """All documents of a kind (online: of one owner when given)."""
    if mode() == "local":
        sub, ext = _DIRS[kind]
        out = []
        for p in (state_dir() / sub).glob(f"[jr]-*{ext}"):
            if kind == "review" and p.name.endswith(".decision.json"):
                continue
            d = read_json(p)
            if d:
                out.append(d)
        return out
    from . import db
    q, args = "SELECT data FROM docs WHERE kind = ?", [kind]
    if owner:
        q, args = q + " AND owner = ?", args + [owner]
    with db.read() as con:
        return [json.loads(r[0]) for r in con.execute(q, args)]


def doc_versions(owner: str = None) -> dict:
    """{file-like name: version} of every job, review and decision, for the live event stream."""
    if mode() == "local":
        snap = {}
        for sub in ("jobs", "reviews"):
            for p in (state_dir() / sub).glob("[jr]-*.json"):
                try:
                    snap[p.name] = p.stat().st_mtime_ns
                except FileNotFoundError:
                    pass
        return snap
    from . import db
    q, args = "SELECT kind, id, updated_ns FROM docs", []
    if owner:
        q, args = q + " WHERE owner = ?", [owner]
    with db.read() as con:
        return {f"{i}{_DIRS[k][1]}": t for k, i, t in con.execute(q, args)}
