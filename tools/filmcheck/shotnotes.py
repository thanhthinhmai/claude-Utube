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


# ---------- the notes book (T023, data-model "Sổ ghi chú") ----------
def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _dump(doc: dict) -> bytes:
    return (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def _read_raw(film_dir) -> tuple:
    """(bytes, doc) of shot-notes.json; a missing file is b"" and an empty book."""
    f = film_paths(film_dir)["notes"]
    try:
        raw = f.read_bytes()
    except FileNotFoundError:
        return b"", {"version": 1, "shots": {}}
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        doc = None
    if not isinstance(doc, dict) or not isinstance(doc.get("shots"), dict):
        doc = {"version": 1, "shots": {}}
    return raw, doc


def orphans_of(doc: dict, shots: dict) -> list:
    """Shot ids with notes that are not in the current shot marks (FR-015); [] when the marks are missing or broken."""
    if not shots.get("valid"):
        return []
    ids = {s["id"] for s in shots["shots"]}
    return sorted(k for k, v in doc.get("shots", {}).items() if k not in ids and isinstance(v, dict) and v.get("notes"))


def read_notes(film_dir) -> dict:
    raw, doc = _read_raw(film_dir)
    return {"base": _sha(raw), "doc": doc, "orphans": orphans_of(doc, load_shots(film_dir))}


def _invalid(field: str, message: str):
    return ShotError("invalid", f"{field}: {message}", 422, {"field": field})


def validate(doc, shots: list, images_dir: Path = None) -> None:
    """Raise ShotError invalid (422, extra.field) at the first broken field (data-model "Sổ ghi chú")."""
    if not isinstance(doc, dict) or doc.get("version", 1) != 1 or not isinstance(doc.get("shots"), dict):
        raise _invalid("doc", "cần {\"version\": 1, \"shots\": {…}}")
    length = {s["id"]: s["t1"] - s["t0"] for s in shots}
    if len(doc["shots"]) > MAX_SHOTS * 2:
        raise _invalid("shots", "quá nhiều shot")
    seen = set()
    for sid, sh in doc["shots"].items():
        f = f"shots.{sid}"
        if not isinstance(sid, str) or not sid.strip() or len(sid) > 100:
            raise _invalid("shots", "mã shot phải là chuỗi 1–100 ký tự")
        if not isinstance(sh, dict):
            raise _invalid(f, "phải là một đối tượng")
        if sh.get("status", "none") not in STATUSES:
            raise _invalid(f"{f}.status", f"phải là một trong {', '.join(STATUSES)}")
        if sh.get("status_by", "auto") not in ("auto", "user"):
            raise _invalid(f"{f}.status_by", "phải là auto hoặc user")
        notes = sh.get("notes", [])
        if not isinstance(notes, list):
            raise _invalid(f"{f}.notes", "phải là một danh sách")
        if len(notes) > 200:
            raise _invalid(f"{f}.notes", "quá 200 ghi chú")
        for i, n in enumerate(notes):
            nf = f"{f}.notes[{i}]"
            if not isinstance(n, dict):
                raise _invalid(nf, "phải là một đối tượng")
            nid = n.get("id")
            if nid is not None:
                if not isinstance(nid, str) or not re.fullmatch(NOTE_ID, nid):
                    raise _invalid(f"{nf}.id", "phải có dạng n-<8 ký tự hex>")
                if nid in seen:
                    raise _invalid(f"{nf}.id", "trùng mã ghi chú")
                seen.add(nid)
            text = n.get("text", "")
            if not isinstance(text, str) or len(text) > MAX_TEXT:
                raise _invalid(f"{nf}.text", f"chữ tối đa {MAX_TEXT} ký tự")
            imgs = n.get("images", [])
            if not isinstance(imgs, list) or len(imgs) > MAX_IMAGES:
                raise _invalid(f"{nf}.images", f"tối đa {MAX_IMAGES} ảnh")
            for im in imgs:
                if not isinstance(im, str) or not re.fullmatch(IMAGE_NAME, im):
                    raise _invalid(f"{nf}.images", "tên ảnh không hợp lệ")
                if images_dir is not None and not (images_dir / im).is_file():
                    raise _invalid(f"{nf}.images", f"không có ảnh {im} trong shot-notes/")
            if len(set(imgs)) != len(imgs):
                raise _invalid(f"{nf}.images", "ảnh bị lặp")
            if not text.strip() and not imgs:
                raise _invalid(f"{nf}.text", "ghi chú cần chữ hoặc ít nhất 1 ảnh")
            at = n.get("at")
            if at is not None:
                if not isinstance(at, (int, float)) or isinstance(at, bool) or at < 0 or (
                        sid in length and at > length[sid] + 1e-6):
                    raise _invalid(f"{nf}.at", "mốc giây phải là null hoặc từ 0 tới độ dài shot")
            if not isinstance(n.get("done", False), bool):
                raise _invalid(f"{nf}.done", "phải là true hoặc false")
            reply = n.get("reply")
            if reply is not None and (not isinstance(reply, str) or len(reply) > MAX_TEXT):
                raise _invalid(f"{nf}.reply", f"trả lời tối đa {MAX_TEXT} ký tự")


def _note_key(n: dict) -> tuple:
    return (n.get("id"), n.get("text", ""), tuple(n.get("images", [])), n.get("at"), bool(n.get("done", False)))


def derive_status(notes: list) -> str:
    if not notes:
        return "none"
    return "fix" if any(not n.get("done") for n in notes) else "fixed"


def derive(doc: dict, prev_doc: dict) -> None:
    """FR-007 on `doc` in place: a shot whose notes changed goes back to auto; an auto shot takes the status its notes
    give; a status changed by hand with the notes unchanged is the user's."""
    prev = prev_doc.get("shots", {}) if isinstance(prev_doc, dict) else {}
    for sid in list(doc["shots"]):
        sh = doc["shots"][sid]
        old = prev.get(sid) if isinstance(prev.get(sid), dict) else {}
        notes = sh.get("notes", [])
        changed = [_note_key(n) for n in notes] != [_note_key(n) for n in old.get("notes", [])]
        status = sh.get("status", "none")
        if changed:
            sh["status_by"] = "auto"
        elif status != old.get("status", "none"):
            sh["status_by"] = "user"
        else:
            sh["status_by"] = sh.get("status_by", old.get("status_by", "auto"))
        if sh["status_by"] == "auto":
            sh["status"] = derive_status(notes)
        sh["notes"] = notes
        if not notes and sh["status"] == "none":
            del doc["shots"][sid]                    # a shot not in the book = no notes


def _clean_note(n: dict, old: dict, by: str, now: str) -> dict:
    out = {"id": n.get("id") or f"n-{secrets.token_hex(4)}", "at": None if n.get("at") is None else round(float(n["at"]), 1),
           "text": n.get("text", ""), "images": list(n.get("images", [])), "done": bool(n.get("done", False))}
    if old:
        out["by"], out["created"] = old.get("by", by), old.get("created", now)
        same = (old.get("text", ""), old.get("images", []), old.get("at")) == (out["text"], out["images"], out["at"])
        out["updated"] = old.get("updated", now) if same and bool(old.get("done", False)) == out["done"] else now
    else:
        out["by"], out["created"], out["updated"] = by, now, now
    if n.get("reply") is not None:
        out["reply"] = n["reply"]
    return out


def _images_in(doc: dict) -> set:
    return {im for sh in doc.get("shots", {}).values() if isinstance(sh, dict)
            for n in sh.get("notes", []) if isinstance(n, dict) for im in n.get("images", []) if isinstance(im, str)}


def save_notes(film_dir, base: str, doc, by: str = "local", now: float = None) -> dict:
    """Write the whole book if `base` is still the file's fingerprint (FR-009). Returns {base, doc}.
    ShotError changed (409, extra.current = {base, doc}) when someone saved first; invalid (422) on a broken field."""
    p = film_paths(film_dir)
    t = clock() if now is None else now
    stamp = now_iso(t)
    with locked(p["notes"]):
        raw, cur = _read_raw(film_dir)
        if base != _sha(raw):
            raise ShotError("changed", "ghi chú vừa được người khác đổi: tải lại rồi lưu lại", 409,
                            {"current": {"base": _sha(raw), "doc": cur}})
        shots = load_shots(film_dir)
        validate(doc, shots["shots"] if shots["valid"] else [], p["images"])
        old_notes = {n.get("id"): n for sh in cur.get("shots", {}).values() if isinstance(sh, dict)
                     for n in sh.get("notes", []) if isinstance(n, dict) and n.get("id")}
        new = {"version": 1, "shots": {}}
        if isinstance(cur.get("lot"), dict):          # a fix run in progress (specs/031): only start_lot/end_lot change it
            new["lot"] = cur["lot"]
        for sid, sh in doc["shots"].items():
            new["shots"][sid] = {"status": sh.get("status", "none"), "status_by": sh.get("status_by", "auto"),
                                 "notes": [_clean_note(n, old_notes.get(n.get("id")), by, stamp) for n in sh.get("notes", [])]}
        derive(new, cur)
        data = _dump(new)
        write_atomic(p["notes"], data)
        _tidy_images(p["images"], _images_in(new), _images_in(cur), t)
        return {"base": _sha(data), "doc": new}


def _tidy_images(folder: Path, used: set, used_before: set, now: float) -> None:
    """Pictures taken off a note go now; pictures never put in a note go after ORPHAN_IMAGE_AGE (data-model)."""
    if not folder.is_dir():
        return
    for f in folder.iterdir():
        if not re.fullmatch(IMAGE_NAME, f.name) or f.name in used:
            continue
        try:
            if f.name in used_before or now - f.stat().st_mtime > ORPHAN_IMAGE_AGE:
                f.unlink()
        except OSError:
            pass


# ---------- pictures for notes (T024, research R9) ----------
MAGIC = ((b"\x89PNG", "png"), (b"\xff\xd8\xff", "jpg"))


def image_kind(data: bytes):
    for head, ext in MAGIC:
        if data.startswith(head):
            return ext
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def save_image(film_dir, data: bytes, now: float = None) -> str:
    """Store one picture under a server-made name; its file time is the app's clock (for the one-hour tidy)."""
    if len(data) > MAX_IMAGE_BYTES:
        raise ShotError("too_large", f"ảnh tối đa {MAX_IMAGE_BYTES // (1024 * 1024)} MB", 413)
    ext = image_kind(data)
    if not ext:
        raise ShotError("bad_image", "chỉ nhận ảnh PNG, JPEG hoặc WebP", 415)
    folder = film_paths(film_dir)["images"]
    while True:
        name = f"img-{secrets.token_hex(6)}.{ext}"
        if not (folder / name).exists():
            break
    path = image_path(film_dir, name)
    write_atomic(path, data)
    t = clock() if now is None else now
    os.utime(path, (t, t))
    return name


# ---------- Claude's side: answer a note (notes reply) ----------
def reply(film_dir, note_id: str, text: str, done=None, base: str = "", by: str = "claude") -> dict:
    """Write Claude's one-line answer on a note; done=True ticks it, False opens it again, None leaves it. The shot's
    status follows (FR-007). ShotError not_found (no such note), changed (base is old), invalid."""
    if not isinstance(text, str) or len(text) > MAX_TEXT:
        raise ShotError("invalid", f"trả lời tối đa {MAX_TEXT} ký tự", 422, {"field": "reply"})
    g = read_notes(film_dir)
    if base != g["base"]:
        raise ShotError("changed", "ghi chú đã đổi từ lần đọc trước: chạy lại notes show", 409,
                        {"current": {"base": g["base"], "doc": g["doc"]}})
    doc = g["doc"]
    for sh in doc["shots"].values():
        for n in sh.get("notes", []):
            if n.get("id") == note_id:
                n["reply"] = text.strip()
                if done is not None:
                    n["done"] = bool(done)
                return save_notes(film_dir, base, doc, by)
    raise ShotError("not_found", f"không có ghi chú {note_id}", 404)


def show_lines(film_dir, everything: bool = False) -> tuple:
    """(lines, number of open notes) of `notes show`: notes grouped by shot, in film order, then the gone shots."""
    d = Path(film_dir).resolve()
    g = read_notes(d)
    marks = load_shots(d)
    by_id = {s["id"]: s for s in marks["shots"]} if marks["valid"] else {}
    order = [s["id"] for s in marks["shots"]] if marks["valid"] else []
    order += sorted(k for k in g["doc"]["shots"] if k not in by_id)
    names = {"none": "No notes", "ok": "No issue", "fix": "Needs fix", "fixed": "Fixed"}
    fmt = lambda t: f"{int(t // 60)}:{t - 60 * int(t // 60):04.1f}"     # noqa: E731
    lines, open_n = [], 0
    if not marks["valid"]:
        lines.append("! shots.json is missing or not valid: shot numbers and film times are not known")
    for sid in order:
        sh = g["doc"]["shots"].get(sid)
        if not isinstance(sh, dict):
            continue
        notes = [n for n in sh.get("notes", []) if everything or not n.get("done")]
        open_n += sum(1 for n in sh.get("notes", []) if not n.get("done"))
        if not notes:
            continue
        s = by_id.get(sid)
        head = (f"Shot {s['n']} · {sid} · {fmt(s['t0'])}–{fmt(s['t1'])} ({s['t1'] - s['t0']:.1f} s)" if s
                else f"Gone shot {sid} (not in shots.json any more)")
        lines.append(f"{head} · {names.get(sh.get('status', 'none'), sh.get('status'))}")
        for n in notes:
            if n.get("at") is None:
                where = "whole shot"
            elif s:
                where = f"at {fmt(n['at'])} in the shot · {fmt(s['t0'] + n['at'])} in the film"
            else:
                where = f"at {fmt(n['at'])} in the shot"
            lines.append(f"  [{'fixed' if n.get('done') else 'open'}] {n.get('id')} · {where} · by {n.get('by', '?')}")
            for t in (n.get("text") or "(picture only)").splitlines() or [""]:
                lines.append(f"      {t}")
            for im in n.get("images", []):
                lines.append(f"      picture: {d / 'shot-notes' / im}")
            if n.get("reply"):
                lines.append(f"      reply: {n['reply']}")
    lines.append(f"{open_n} open note{'' if open_n == 1 else 's'}")
    lines.append(f"base: {g['base']}")
    return lines, open_n


# ---------- fix runs: the notes one "Fix with Claude" job works on (specs/031 R7, FR-011, FR-012) ----------
LOT_LIMIT = 10


def open_notes_in_order(film_dir) -> list:
    """[(note id, film second)] of open notes, in film order (shot start + the note's second); gone shots last."""
    g = read_notes(film_dir)
    marks = load_shots(film_dir)
    by_id = {x["id"]: x for x in marks["shots"]} if marks["valid"] else {}
    out = []
    for sid, sh in g["doc"]["shots"].items():
        if not isinstance(sh, dict):
            continue
        t0 = by_id[sid]["t0"] if sid in by_id else float("inf")
        for n in sh.get("notes", []):
            if not n.get("done") and n.get("id"):
                out.append((n["id"], t0 + (n.get("at") or 0)))
    return sorted(out, key=lambda x: x[1])


def active_lot(film_dir, live=None):
    """The lot of a running fix job, or None. live(job id) -> bool says whether that job still runs; a lot left by a
    job that ended (stopped, crashed) counts as free."""
    lot = read_notes(film_dir)["doc"].get("lot")
    if not isinstance(lot, dict):
        return None
    if live is not None and not live(lot.get("job")):
        return None
    return lot


def start_lot(film_dir, job: str, limit: int = LOT_LIMIT, live=None, now: float = None) -> dict:
    """Mark the first `limit` open notes (film order) as this job's lot. Returns {lot, left}.
    ShotError in_progress (409) when a live job holds a lot; no_open_notes (422)."""
    p = film_paths(film_dir)
    with locked(p["notes"]):
        raw, cur = _read_raw(film_dir)
        lot = cur.get("lot")
        if isinstance(lot, dict) and (live is None or live(lot.get("job"))):
            raise ShotError("in_progress", f"Claude is already fixing this film's notes (job {lot.get('job')})", 409,
                            {"job": lot.get("job")})
        ordered = open_notes_in_order(film_dir)
        if not ordered:
            raise ShotError("no_open_notes", "this film has no open notes to fix", 422)
        take = [nid for nid, _ in ordered[:limit]]
        cur["lot"] = {"job": job, "notes": take, "since": now_iso(clock() if now is None else now)}
        write_atomic(p["notes"], _dump(cur))
    return {"lot": cur["lot"], "left": len(ordered) - len(take)}


def end_lot(film_dir, job: str = None) -> bool:
    """Drop the lot (only this job's when `job` is given). True when one was dropped."""
    p = film_paths(film_dir)
    with locked(p["notes"]):
        raw, cur = _read_raw(film_dir)
        lot = cur.get("lot")
        if not isinstance(lot, dict) or (job and lot.get("job") != job):
            return False
        del cur["lot"]
        write_atomic(p["notes"], _dump(cur))
    return True


def merge_lot_replies(lib_dir, work_dir, job: str = None, failed_why: str = None) -> dict:
    """Copy Claude's answers on the lot's notes from the job's copy of the book into the library's, one note at a
    time on the newest base, so notes added or edited meanwhile stay as they are. A lot note without an answer gets
    one saying it was not fixed (no note is left without a word). Returns {replied, unanswered}."""
    lot = read_notes(lib_dir)["doc"].get("lot")
    if not isinstance(lot, dict) or (job and lot.get("job") != job):
        return {"replied": 0, "unanswered": 0}
    work = {}
    if work_dir is not None and film_paths(work_dir)["notes"].is_file():
        work = {n.get("id"): n for sh in read_notes(work_dir)["doc"]["shots"].values() if isinstance(sh, dict)
                for n in sh.get("notes", []) if isinstance(n, dict)}
    replied = unanswered = 0
    for nid in lot.get("notes", []):
        w = work.get(nid) or {}
        text, done = w.get("reply"), bool(w.get("done"))
        if failed_why or not text:
            text, done = (failed_why or "Not fixed in this run: Claude gave no answer for this note."), False
            unanswered += 1
        else:
            replied += 1
        for _ in range(3):                           # the user may save between our read and write
            try:
                reply(lib_dir, nid, text[:MAX_TEXT], done=done, base=read_notes(lib_dir)["base"])
                break
            except ShotError as e:
                if e.code == "not_found":            # the user deleted the note meanwhile
                    break
                if e.code != "changed":
                    raise
    return {"replied": replied, "unanswered": unanswered}


# ---------- film replace: a new video, keeping one previous (T031, research R7) ----------
def replace_video(film_dir, new_video, new_shots=None) -> dict:
    """Check the new video (and its shots.json), keep the current pair as <name>.prev.mp4 + shots.prev.json (dropping
    an older previous pair), put a copy of the new video in place with os.replace (a new file: hard links of the old
    one elsewhere are untouched), write the new shots.json, drop the small-picture cache. Nothing changes on refusal."""
    d = Path(film_dir)
    p = film_paths(d)
    src = Path(new_video).expanduser().resolve()
    if not src.is_file():
        raise ShotError("bad_video", f"không có tệp video {src}", 400)
    if src in (p["video"], p["video_prev"]):
        raise ShotError("bad_video", "video mới phải là một tệp khác video của phim", 400)
    info = probe(src)
    if not info["has_video"]:
        raise ShotError("bad_video", f"{src.name} không đọc được như một video có hình", 400)
    marks, kept = None, False
    if new_shots is not None:
        try:
            marks = json.loads(Path(new_shots).expanduser().read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise ShotError("invalid", f"không đọc được shots.json mới: {e}", 400) from None
        shots, problems = check_shots(marks, info["duration"])
        if problems:
            raise ShotError("invalid", "; ".join(f"dòng {x['row']} {x['rule']}: {x['detail']}" for x in problems[:5]), 400)
    elif p["shots"].is_file():
        try:
            cur = json.loads(p["shots"].read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cur = None
        if cur is not None and not check_shots(cur, info["duration"])[1]:
            marks, kept = cur, True
    old = probe(p["video"])["duration"] if p["video"].is_file() else None
    if marks is not None:
        marks = {**marks, "version": 1, "video": p["video"].name, "duration": info["duration"]}
    tmp = p["video"].with_name(f".{p['video'].name}.{os.getpid()}.new.tmp")
    shutil.copyfile(src, tmp)
    try:
        with locked(p["video"]):
            if p["video"].is_file():
                p["video_prev"].unlink(missing_ok=True)
                p["shots_prev"].unlink(missing_ok=True)
                os.replace(p["video"], p["video_prev"])
                if p["shots"].is_file():
                    os.replace(p["shots"], p["shots_prev"])
            os.replace(tmp, p["video"])
            if marks is not None:
                write_atomic(p["shots"], (json.dumps(marks, ensure_ascii=False, indent=1) + "\n").encode())
            else:
                p["shots"].unlink(missing_ok=True)
    finally:
        tmp.unlink(missing_ok=True)
    shutil.rmtree(p["thumbs"], ignore_errors=True)
    return {"old": old, "new": info["duration"], "shots": len(marks["shots"]) if marks else None, "kept_marks": kept,
            "prev": p["video_prev"].is_file()}
