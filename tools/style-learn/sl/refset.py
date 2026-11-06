"""Reference sets: references/<set>/set.json and paths (data-model.md: ReferenceSet, Video)."""
import datetime
import json
import os
import re
from pathlib import Path

SCHEMA = "style-learn/1"
SLUG = re.compile(r"^[a-z0-9-]{3,40}$")
MEDIA_EXT = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v", ".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus"}


class UsageError(Exception):
    """Bad input from the user: exit code 2."""


class StepError(Exception):
    """A step could not finish: exit code 1."""


def root() -> Path:
    # STUDIO_ROOT lets tests point at a temporary project
    env = os.environ.get("STUDIO_ROOT")
    return Path(env).resolve() if env else Path(__file__).resolve().parents[3]


def refs_dir() -> Path:
    return root() / "references"


def check_slug(name: str, what: str = "tên bộ") -> str:
    if not SLUG.match(name or ""):
        raise UsageError(f"{what} \"{name}\" không hợp lệ: chỉ chữ thường, số, gạch nối, 3–40 ký tự")
    return name


def set_dir(name: str) -> Path:
    return refs_dir() / check_slug(name)


def write_json(path: Path, data) -> None:
    """Write atomically: a crash never leaves half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load(name: str) -> dict:
    p = set_dir(name) / "set.json"
    if not p.exists():
        raise StepError(f"chưa có bộ tham chiếu \"{name}\". Chạy trước: sh bin/studio learn fetch {name} …")
    return read_json(p)


def save(name: str, data: dict) -> None:
    write_json(set_dir(name) / "set.json", data)


def new_set(name: str, kind: str, inputs, max_seconds: float = 180, deny=()) -> dict:
    if not 30 <= max_seconds <= 1800:
        raise UsageError("--max-seconds phải trong khoảng 30–1800")
    return {
        "schema": SCHEMA, "set": check_slug(name), "source": {"kind": kind, "inputs": list(inputs)},
        "max_seconds": max_seconds, "deny": list(deny), "videos": [],
        "created": datetime.date.today().isoformat(),
    }


def next_id(data: dict) -> str:
    return f"v{len(data['videos']) + 1:02d}"


def source_sig(path: Path) -> str:
    st = path.stat()
    return f"{st.st_size}:{int(st.st_mtime)}"


def video_path(name: str, v: dict) -> Path:
    return set_dir(name) / "videos" / v["file"]


def profile_dir(name: str, vid: str) -> Path:
    return set_dir(name) / "profile" / vid
