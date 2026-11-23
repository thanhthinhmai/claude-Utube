"""Per-shot notes on the film page (specs/029): the shot marks (shots.json), the notes book (shot-notes.json and the
pictures in shot-notes/), the small pictures of each shot (.shots/thumbs/) and the one previous video kept by
`film replace`. Shared by the app's server and by `sh bin/studio shots|notes|film …`. Python 3 standard library plus
ffmpeg/ffprobe; nothing here imports the app (data-model.md, contracts/files.md)."""
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import threading
import time
from pathlib import Path

MAX_SHOTS = 300
MAX_TEXT = 2000
MAX_IMAGES = 4
MAX_IMAGE_BYTES = 10 * 1024 * 1024
IMAGE_NAME = r"img-[0-9a-f]{12}\.(png|jpg|webp)"
ORPHAN_IMAGE_AGE = 3600
NOTE_ID = r"n-[0-9a-f]{8}"
STATUSES = ("none", "fix", "fixed", "ok")
THUMB_AT = {"a": 0.12, "b": 0.50, "c": 0.88}
EMPTY_SHA = hashlib.sha256(b"").hexdigest()

# Tests move time forward by replacing this (the server passes the app's clock instead)
clock = time.time


class ShotError(ValueError):
    """A refusal with a stable code, an HTTP status and a Vietnamese message (the server turns it into StudioError)."""

    def __init__(self, code: str, message: str, status: int = 400, extra: dict = None):
        super().__init__(message)
        self.code, self.message, self.status, self.extra = code, message, status, extra or {}


# ---------- safe paths (T003) ----------
def film_paths(film_dir) -> dict:
    """Every file of this feature inside one film folder; each must stay inside it (FR-010, SC-007)."""
    d = Path(film_dir)
    base = d.resolve()
    name = base.name
    if not re.fullmatch(r"[a-z0-9-]{1,60}", name):
        raise ShotError("bad_name", "tên phim không hợp lệ", 400)
    rel = {"shots": "shots.json", "shots_prev": "shots.prev.json", "notes": "shot-notes.json", "images": "shot-notes",
           "thumbs": ".shots/thumbs", "video": f"{name}.mp4", "video_prev": f"{name}.prev.mp4"}
    out = {}
    for k, r in rel.items():
        p = (base / r).resolve()
        if not p.is_relative_to(base) or p == base:
            raise ShotError("bad_name", "đường dẫn không hợp lệ", 400)
        out[k] = p
    return out


def image_path(film_dir, file: str) -> Path:
    """A picture of the notes book by its server-made name only."""
    if not isinstance(file, str) or not re.fullmatch(IMAGE_NAME, file):
        raise ShotError("bad_name", "tên ảnh không hợp lệ", 400)
    folder = film_paths(film_dir)["images"]
    p = (folder / file).resolve()
    if not p.is_relative_to(folder):
        raise ShotError("bad_name", "tên ảnh không hợp lệ", 400)
    return p


# ---------- atomic writes and a file lock (T004, same way as tools/studio/studio/store.py) ----------
def write_atomic(path, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


@contextlib.contextmanager
def locked(path):
    """An exclusive lock on <file>.lock next to `path`, across threads and processes."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path.with_name(path.name + ".lock"), "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def now_iso(t: float = None) -> str:
    return dt.datetime.fromtimestamp(clock() if t is None else t, dt.timezone.utc).isoformat(timespec="seconds")
