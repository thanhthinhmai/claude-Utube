"""State under .studio/: atomic JSON writes, exclusive creates, per-id locks (research.md §2–3)."""
import contextlib
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


def root() -> Path:
    env = os.environ.get("STUDIO_ROOT")
    return Path(env).resolve() if env else Path(__file__).resolve().parents[3]


def state_dir() -> Path:
    d = root() / ".studio"
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


@contextlib.contextmanager
def lock(name: str):
    with open(state_dir() / "locks" / f"{name}.lock", "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
