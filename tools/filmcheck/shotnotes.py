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


# ---------- the video ----------
_probe_cache = {}


def probe(video) -> dict:
    """{duration, fps, has_video} of a video by ffprobe (picture stream), cached by size and mtime."""
    video = Path(video)
    st = video.stat()
    key = (str(video), st.st_size, st.st_mtime_ns)
    if key in _probe_cache:
        return _probe_cache[key]
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=duration,r_frame_rate,avg_frame_rate:format=duration", "-of", "json", str(video)],
                       capture_output=True, text=True, timeout=60)
    try:
        j = json.loads(p.stdout or "{}")
    except ValueError:
        j = {}
    streams = j.get("streams") or []
    s = streams[0] if streams else {}

    def rate(v):
        try:
            a, b = str(v).split("/")
            return float(a) / float(b) if float(b) else 0.0
        except (ValueError, ZeroDivisionError):
            return 0.0
    fps = rate(s.get("avg_frame_rate")) or rate(s.get("r_frame_rate"))
    dur = 0.0
    for v in (s.get("duration"), (j.get("format") or {}).get("duration")):
        try:
            dur = float(v)
            break
        except (TypeError, ValueError):
            continue
    out = {"duration": round(dur, 3), "fps": round(fps, 3) if fps else 0.0, "has_video": bool(streams) and dur > 0}
    if len(_probe_cache) > 256:
        _probe_cache.clear()
    _probe_cache[key] = out
    return out


def video_stamp(video) -> str:
    st = Path(video).stat()
    return f"{st.st_size}-{st.st_mtime_ns}"


# ---------- the shot marks (T010, data-model "Mốc shot") ----------
def _fps_of(value) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 30.0
    return f if 1 <= f <= 240 else 30.0


def check_shots(doc, duration: float = None) -> tuple:
    """(shots [{n, id, set, t0, t1}], problems [{row, rule, detail}]) of a shots.json document. `duration`: the video's
    length (else the document's own). Rows are numbered from 1; row 0 is the whole file."""
    problems = []

    def bad(row, rule, detail):
        problems.append({"row": row, "rule": rule, "detail": detail})
    if not isinstance(doc, dict) or not isinstance(doc.get("shots"), list):
        bad(0, "format", "shots.json phải là một đối tượng có danh sách \"shots\"")
        return [], problems
    rows = doc["shots"]
    fps = _fps_of(doc.get("fps"))
    frame = 1.0 / fps + 1e-6
    if duration is None:
        try:
            duration = float(doc.get("duration"))
        except (TypeError, ValueError):
            duration = None
    if not 1 <= len(rows) <= MAX_SHOTS:
        bad(0, "count", f"cần 1–{MAX_SHOTS} shot, đang có {len(rows)}")
        if len(rows) > MAX_SHOTS or not rows:
            return [], problems
    shots, seen = [], {}
    prev_t1 = None
    for i, r in enumerate(rows, 1):
        if not isinstance(r, (list, tuple)) or len(r) < 4 or not all(
                isinstance(x, (int, float)) and not isinstance(x, bool) for x in r[:2]):
            bad(i, "row", "mỗi dòng phải là [t0, t1, bối cảnh, mã shot] (t0, t1 là số giây)")
            prev_t1 = None
            continue
        t0, t1 = float(r[0]), float(r[1])
        sid = r[3] if isinstance(r[3], str) else (str(r[3]) if isinstance(r[3], (int, float)) and not isinstance(r[3], bool) else "")
        sid = sid.strip()
        if not sid or len(sid) > 100:
            bad(i, "id", "mã shot phải là chuỗi 1–100 ký tự")
        elif sid in seen:
            bad(i, "duplicate_id", f"mã shot {sid!r} trùng dòng {seen[sid]}")
        else:
            seen[sid] = i
        if i == 1 and abs(t0) > frame:
            bad(i, "start", f"shot đầu phải bắt đầu ở 0 s (đang là {t0:g} s)")
        if t1 <= t0:
            bad(i, "length", f"kết thúc {t1:g} s phải sau bắt đầu {t0:g} s")
        if prev_t1 is not None and abs(t0 - prev_t1) > frame:
            what = "chồng lên" if t0 < prev_t1 else "hở sau"
            bad(i, "gap", f"bắt đầu {t0:g} s {what} shot trước (kết thúc {prev_t1:g} s), lệch quá 1 khung")
        prev_t1 = t1
        st = r[2] if isinstance(r[2], str) else ""
        shots.append({"n": i, "id": sid, "set": st, "t0": round(t0, 3), "t1": round(t1, 3)})
    if duration is not None and shots and isinstance(rows[-1], (list, tuple)) and len(rows[-1]) >= 2:
        last = shots[-1]["t1"]
        if abs(last - duration) > frame:
            bad(len(rows), "end", f"shot cuối kết thúc ở {last:g} s nhưng video dài {duration:g} s (lệch quá 1 khung)")
    return (shots if not problems else []), problems


def load_shots(film_dir, prev: bool = False) -> dict:
    """The film's shot marks, checked against its video (FR-002). prev=True: the previous set (shots.prev.json with
    <name>.prev.mp4), ShotError not_found when there is none."""
    p = film_paths(film_dir)
    f = p["shots_prev" if prev else "shots"]
    video = p["video_prev" if prev else "video"]
    if not f.is_file():
        if prev:
            raise ShotError("not_found", "phim chưa có bản trước", 404)
        return {"valid": False, "missing": True, "problems": [], "duration": None, "fps": None, "source": None,
                "shots": []}
    try:
        doc = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return {"valid": False, "missing": False, "problems": [{"row": 0, "rule": "json", "detail": f"không đọc được: {e}"}],
                "duration": None, "fps": None, "source": None, "shots": []}
    duration = probe(video)["duration"] if video.is_file() else None
    shots, problems = check_shots(doc, duration)
    d = doc if isinstance(doc, dict) else {}
    fps = d.get("fps")
    return {"valid": not problems, "missing": False, "problems": problems,
            "duration": duration if duration is not None else d.get("duration"),
            "fps": int(fps) if isinstance(fps, (int, float)) and float(fps).is_integer() else fps,
            "source": d.get("source"), "shots": shots}


# ---------- small pictures of each shot (T011, research R3) ----------
_thumb_lock = threading.Lock()
_building = {}            # stamp folder → thread


def _thumb_key(shots) -> str:
    return hashlib.sha256(json.dumps([[s["t0"], s["t1"]] for s in shots]).encode()).hexdigest()[:16]


def _thumb_dir(film_dir) -> tuple:
    p = film_paths(film_dir)
    return p["thumbs"], p["video"]


def _cut(video: Path, t: float, out: Path) -> None:
    tmp = out.with_name(f".{out.name}.{threading.get_ident()}.tmp.jpg")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", str(video), "-frames:v", "1",
                    "-vf", "scale=320:-2", "-q:v", "5", str(tmp)], capture_output=True, timeout=60)
    if tmp.is_file() and tmp.stat().st_size:
        os.replace(tmp, out)
    tmp.unlink(missing_ok=True)


def _build(folder: Path, video: Path, shots: list, key: str) -> None:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.parent.iterdir():          # caches of other videos go
            if old != folder and old.is_dir():
                shutil.rmtree(old, ignore_errors=True)
        jobs = []
        for s in shots:
            for w, k in THUMB_AT.items():
                out = folder / f"{s['n']}_{w}.jpg"
                if not out.is_file():
                    jobs.append((s["t0"] + (s["t1"] - s["t0"]) * k, out))
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 2)) as ex:
            list(ex.map(lambda j: _cut(video, *j), jobs))
        (folder / ".done").write_text(key)
    finally:
        with _thumb_lock:
            _building.pop(str(folder), None)


def thumbs_state(film_dir, shots: list, start: bool = True) -> tuple:
    """("ready"|"building", video stamp) of the small pictures for these shots; starts the one background build."""
    base, video = _thumb_dir(film_dir)
    stamp = video_stamp(video)
    folder = base / stamp
    key = _thumb_key(shots)
    done = folder / ".done"
    try:
        if done.read_text() == key:
            return "ready", stamp
    except OSError:
        pass
    with _thumb_lock:
        if str(folder) not in _building:
            if not start:
                return "building", stamp
            if folder.is_dir() and done.exists():           # made for other shot marks: start over
                shutil.rmtree(folder, ignore_errors=True)
            t = threading.Thread(target=_build, args=(folder, video, list(shots), key), daemon=True)
            _building[str(folder)] = t
            t.start()
    return "building", stamp


def thumb(film_dir, n, which: str):
    """(path or None, state) of shot n's picture a|b|c. state: ready · building · missing. ShotError not_found when
    the film has no valid shot marks, n is out of range or `which` is not a|b|c."""
    if which not in THUMB_AT:
        raise ShotError("not_found", "không có ảnh này", 404)
    try:
        n = int(n)
    except (TypeError, ValueError):
        raise ShotError("not_found", "không có shot này", 404) from None
    p = film_paths(film_dir)
    if not p["video"].is_file():
        raise ShotError("not_found", "phim chưa có video", 404)
    r = load_shots(film_dir)
    if not r["valid"] or not 1 <= n <= len(r["shots"]):
        raise ShotError("not_found", "không có shot này", 404)
    state, stamp = thumbs_state(film_dir, r["shots"])
    f = p["thumbs"] / stamp / f"{n}_{which}.jpg"
    if f.is_file():                       # written whole (tmp then rename), so safe to serve while the rest is made
        return f, "ready"
    return None, "missing" if state == "ready" else "building"
