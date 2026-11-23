"""The core's queue of After Effects build requests (specs/031 T012, data-model.md, contracts/bridge-api.md).

$STUDIO_DATA/ae/requests/<id>/ holds request.json, bundle.tar, out/<name>.mp4. A job puts a request in (through the
proxy); the desktop app pulls one at a time (GET next), sends progress (a heartbeat), uploads results and finishes.
A claimed or running request without a heartbeat for 60 s fails with bridge_lost (the desktop app went away).
hello.json: when the desktop app last said hello and whether it found After Effects."""
import contextlib
import fcntl
import json
import os
import re
import secrets
import shutil
import time
from pathlib import Path

HEARTBEAT_S = 60
HELLO_S = 30
KEEP_S = 2 * 86400
MAX_RESULT = 500 * 1024 * 1024
ACTIVE = ("claimed", "running")
FINAL = ("done", "failed", "expired")
ID = re.compile(r"ae-\d{8}-\d{6}-[0-9a-f]{4}")
NAME = re.compile(r"MASTER|S[0-9]{1,3}[A-Z]?")

now = time.time                    # tests replace it


class QueueError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def root() -> Path:
    base = os.environ.get("STUDIO_DATA")
    if base:
        r = Path(base) / "ae"
    else:
        r = Path(__file__).resolve().parents[2] / ".studio" / "ae"
    (r / "requests").mkdir(parents=True, exist_ok=True)
    return r


def iso(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


@contextlib.contextmanager
def lock():
    with open(root() / ".lock", "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _dir(rid: str) -> Path:
    if not ID.fullmatch(rid or ""):
        raise QueueError("not_found", "no such AE request", 404)
    return root() / "requests" / rid


def _read(rid: str) -> dict:
    p = _dir(rid) / "request.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise QueueError("not_found", "no such AE request", 404) from None


def _write(r: dict) -> None:
    p = _dir(r["id"]) / "request.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(r, ensure_ascii=False))
    tmp.replace(p)


def _all() -> list:
    out = []
    for d in (root() / "requests").iterdir():
        try:
            out.append(json.loads((d / "request.json").read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return sorted(out, key=lambda r: r["created_t"])


def _sweep(t: float) -> None:
    """Fail requests whose desktop app stopped beating; drop finished requests older than 2 days."""
    for r in _all():
        if r["state"] in ACTIVE and t - r.get("heartbeat_t", r["created_t"]) > HEARTBEAT_S:
            r.update(state="failed", finished_at=iso(t),
                     error={"code": "bridge_lost", "message": "the desktop app stopped answering while it built this request "
                                                              "(closed, asleep or crashed); open it and try again", "log_tail": ""})
            _write(r)
        elif r["state"] in FINAL and t - r.get("finished_t", r["created_t"]) > KEEP_S:
            shutil.rmtree(_dir(r["id"]), ignore_errors=True)


def create(owner: str, job: str, film: str, shots: list, bundle: bytes) -> dict:
    if not shots or len(shots) > 100 or not all(isinstance(s, str) and NAME.fullmatch(s) for s in shots):
        raise QueueError("invalid", "shots: 1-100 ids like S13 (or MASTER)", 422)
    if not re.fullmatch(r"[a-z0-9-]{1,60}", film or ""):
        raise QueueError("invalid", "bad film name", 422)
    t = now()
    with lock():
        _sweep(t)
        rid = time.strftime("ae-%Y%m%d-%H%M%S-", time.gmtime(t)) + secrets.token_hex(2)
        d = root() / "requests" / rid
        (d / "out").mkdir(parents=True)
        (d / "bundle.tar").write_bytes(bundle)
        r = {"id": rid, "owner": owner, "job": job, "film": film, "shots": shots, "state": "queued", "progress": None,
             "results": {}, "checks": [], "marks": None, "duration": None, "error": None,
             "created": iso(t), "created_t": t, "claimed_at": None, "finished_at": None, "heartbeat_t": t}
        _write(r)
    return public(r)


def public(r: dict) -> dict:
    return {k: v for k, v in r.items() if not k.endswith("_t")}


def get(rid: str) -> dict:
    with lock():
        _sweep(now())
        return public(_read(rid))


def position(rid: str) -> int:
    """How many requests are ahead of this one (0 = next or running)."""
    rs = [r for r in _all() if r["state"] in ("queued",) + ACTIVE]
    ids = [r["id"] for r in rs]
    return ids.index(rid) if rid in ids else 0


def next_request():
    """Claim the oldest queued request, unless one is still claimed or running (one AE run at a time)."""
    t = now()
    with lock():
        _sweep(t)
        rs = _all()
        if any(r["state"] in ACTIVE for r in rs):
            return None
        for r in rs:
            if r["state"] == "queued":
                r.update(state="claimed", claimed_at=iso(t), heartbeat_t=t)
                _write(r)
                return public(r)
    return None


def _active(rid: str) -> dict:
    r = _read(rid)
    if r["state"] not in ACTIVE:
        raise QueueError("not_active", f"the request is {r['state']}", 409)
    return r


def progress(rid: str, body: dict) -> dict:
    t = now()
    with lock():
        r = _active(rid)
        r["heartbeat_t"] = t
        if body.get("state") == "running":
            r["state"] = "running"
            r["progress"] = {"shot": str(body.get("shot") or ""), "index": int(body.get("index") or 0),
                             "total": int(body.get("total") or len(r["shots"])), "at": iso(t)}
        _write(r)
        return public(r)


def bundle_path(rid: str) -> Path:
    r = _read(rid)
    if r["state"] not in ACTIVE:
        raise QueueError("not_active", f"the request is {r['state']}", 409)
    return _dir(rid) / "bundle.tar"


def result_part(rid: str, name: str) -> Path:
    """Where an upload is written before commit_result (only for an active request)."""
    if not NAME.fullmatch(name or ""):
        raise QueueError("invalid", "result name must be MASTER or a shot id", 422)
    with lock():
        _active(rid)
    return _dir(rid) / "out" / f"{name}.part"


def commit_result(rid: str, name: str) -> int:
    part = _dir(rid) / "out" / f"{name}.part"
    n = part.stat().st_size
    if n > MAX_RESULT:
        part.unlink(missing_ok=True)
        raise QueueError("too_big", "a result may be at most 500 MB", 413)
    part.replace(part.with_suffix(".mp4"))
    with lock():
        r = _read(rid)
        r["results"][name] = f"out/{name}.mp4"
        r["heartbeat_t"] = now()
        _write(r)
    return n


def put_result(rid: str, name: str, chunks) -> int:
    part = result_part(rid, name)
    n = 0
    with open(part, "wb") as f:
        for c in chunks:
            n += len(c)
            if n > MAX_RESULT:
                break
            f.write(c)
    if n > MAX_RESULT:
        part.unlink(missing_ok=True)
        raise QueueError("too_big", "a result may be at most 500 MB", 413)
    return commit_result(rid, name)


def finish(rid: str, body: dict) -> dict:
    t = now()
    with lock():
        r = _active(rid)
        if body.get("ok"):
            if not r["results"]:
                raise QueueError("invalid", "finish ok without any result", 422)
            r.update(state="done", checks=[str(c)[:500] for c in (body.get("checks") or [])][:200],
                     marks=body.get("marks"), duration=body.get("duration"))
        else:
            e = body.get("error") or {}
            r.update(state="failed", error={"code": str(e.get("code") or "build_error")[:40],
                                            "message": str(e.get("message") or "")[:2000],
                                            "log_tail": str(e.get("log_tail") or "")[-4000:]})
        r.update(finished_at=iso(t), finished_t=t)
        _write(r)
        return public(r)


def result_path(rid: str, name: str) -> Path:
    r = _read(rid)
    if name not in r["results"]:
        raise QueueError("not_found", f"no result {name}", 404)
    return _dir(rid) / r["results"][name]


def hello(body: dict) -> dict:
    h = {"at": iso(now()), "t": now(), "version": str(body.get("version") or "")[:40], "os": str(body.get("os") or "")[:20],
         "afterfx": str(body.get("afterfx") or "")[:400], "aerender": str(body.get("aerender") or "")[:400],
         "found": bool(body.get("found"))}
    p = root() / "hello.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(h))
    tmp.replace(p)
    return h


def bridge_status() -> dict:
    """ready = the desktop app said hello in the last 30 s and found After Effects (FR-009, FR-018)."""
    try:
        h = json.loads((root() / "hello.json").read_text())
    except (OSError, ValueError):
        h = None
    rs = _all()
    st = {"queued": sum(r["state"] == "queued" for r in rs), "running": sum(r["state"] in ACTIVE for r in rs)}
    if not h or now() - h["t"] > HELLO_S:
        return {**st, "ready": False, "seen": bool(h), "code": "ae_unavailable",
                "message": "open the claude-Utube desktop app on this computer to build After Effects films"}
    if not h["found"]:
        return {**st, "ready": False, "seen": True, "code": "ae_missing", "os": h["os"],
                "message": "the desktop app did not find After Effects on this computer (tray → After Effects…)"}
    return {**st, "ready": True, "seen": True, "afterfx": h["afterfx"], "os": h["os"], "version": h["version"]}
