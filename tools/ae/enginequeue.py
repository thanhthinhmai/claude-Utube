"""The core's queue of engine requests: After Effects (specs/032) and Blender (specs/038 T008, contracts/bridge-api.md).

$STUDIO_DATA/<engine>/requests/<id>/ holds request.json, bundle.tar, out/<name>.<mp4|tar>. A job puts a request in
(through the proxy); the desktop app pulls one at a time per engine (GET next), sends progress (a heartbeat), uploads
results and finishes. A claimed or running request without a heartbeat for 60 s fails with bridge_lost (the desktop app
went away). hello.json: when the desktop app last said hello and whether it found the engine.

Result names: AE "MASTER", "S<n>" (mp4) and "L<shot>-<char>-<view>" (tar of a PNG sequence with alpha, specs/038);
Blender "S<n>" (tar of the shot's PNG frames: the core makes the mp4 with its own ffmpeg)."""
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
ACTIVE = ("claimed", "running")
FINAL = ("done", "failed", "expired")
SHOT = r"S[0-9]{1,3}[A-Z]?"
ENGINES = {
    "ae": {"name": "After Effects", "names": re.compile(rf"MASTER|{SHOT}|L{SHOT}-[a-z0-9-]{{1,40}}-(?:front|back|34)"),
           "shots": re.compile(rf"MASTER|{SHOT}"), "max": 500 * 1024 * 1024, "tool": ("afterfx", "aerender"),
           "unavailable": "open the claude-Utube desktop app on this computer to build After Effects films",
           "missing": "the desktop app did not find After Effects on this computer (tray → After Effects…)"},
    "blender": {"name": "Blender", "names": re.compile(SHOT), "shots": re.compile(SHOT), "max": 2 * 1024 ** 3,
                "tool": ("blender", "version"),
                "unavailable": "open the claude-Utube desktop app on this computer to render Blender shots",
                "missing": "the desktop app did not find Blender on this computer (tray → Blender…)"},
}


class QueueError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def iso(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def ext_of(engine: str, name: str) -> str:
    return ".tar" if engine == "blender" or name.startswith("L") else ".mp4"


class Queue:
    """One engine's queue. `clock` gives the time (aequeue passes its module-level now so tests can move it)."""

    def __init__(self, engine: str, clock=time.time):
        if engine not in ENGINES:
            raise ValueError(engine)
        self.engine, self.e, self.clock = engine, ENGINES[engine], clock
        self.ID = re.compile(rf"{engine}-\d{{8}}-\d{{6}}-[0-9a-f]{{4}}")
        self.MAX_RESULT = self.e["max"]

    def root(self) -> Path:
        base = os.environ.get("STUDIO_DATA")
        r = Path(base) / self.engine if base else Path(__file__).resolve().parents[2] / ".studio" / self.engine
        (r / "requests").mkdir(parents=True, exist_ok=True)
        return r

    @contextlib.contextmanager
    def lock(self):
        with open(self.root() / ".lock", "a+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def _dir(self, rid: str) -> Path:
        if not self.ID.fullmatch(rid or ""):
            raise QueueError("not_found", f"no such {self.e['name']} request", 404)
        return self.root() / "requests" / rid

    def _read(self, rid: str) -> dict:
        try:
            return json.loads((self._dir(rid) / "request.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise QueueError("not_found", f"no such {self.e['name']} request", 404) from None

    def _write(self, r: dict) -> None:
        p = self._dir(r["id"]) / "request.json"
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(r, ensure_ascii=False))
        tmp.replace(p)

    def _all(self) -> list:
        out = []
        for d in (self.root() / "requests").iterdir():
            try:
                out.append(json.loads((d / "request.json").read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        return sorted(out, key=lambda r: r["created_t"])

    def _sweep(self, t: float) -> None:
        """Fail requests whose desktop app stopped beating; drop finished requests older than 2 days."""
        for r in self._all():
            if r["state"] in ACTIVE and t - r.get("heartbeat_t", r["created_t"]) > HEARTBEAT_S:
                r.update(state="failed", finished_at=iso(t),
                         error={"code": "bridge_lost", "message": f"the desktop app stopped answering while it built this "
                                f"{self.e['name']} request (closed, asleep or crashed); open it and try again", "log_tail": ""})
                self._write(r)
            elif r["state"] in FINAL and t - r.get("finished_t", r["created_t"]) > KEEP_S:
                shutil.rmtree(self._dir(r["id"]), ignore_errors=True)

    def create(self, owner: str, job: str, film: str, shots: list, bundle: bytes, kind: str = "build") -> dict:
        if not shots or len(shots) > 100 or not all(isinstance(s, str) and self.e["shots"].fullmatch(s) for s in shots):
            raise QueueError("invalid", "shots: 1-100 ids like S13" + (" (or MASTER)" if self.engine == "ae" else ""), 422)
        if not re.fullmatch(r"[a-z0-9-]{1,60}", film or ""):
            raise QueueError("invalid", "bad film name", 422)
        if not re.fullmatch(r"[a-z]{1,20}", kind or ""):
            raise QueueError("invalid", "bad request kind", 422)
        t = self.clock()
        with self.lock():
            self._sweep(t)
            rid = time.strftime(f"{self.engine}-%Y%m%d-%H%M%S-", time.gmtime(t)) + secrets.token_hex(2)
            d = self.root() / "requests" / rid
            (d / "out").mkdir(parents=True)
            (d / "bundle.tar").write_bytes(bundle)
            r = {"id": rid, "engine": self.engine, "kind": kind, "owner": owner, "job": job, "film": film, "shots": shots,
                 "state": "queued", "progress": None, "results": {}, "checks": [], "marks": None, "duration": None,
                 "error": None, "created": iso(t), "created_t": t, "claimed_at": None, "finished_at": None, "heartbeat_t": t}
            self._write(r)
        return public(r)

    def get(self, rid: str) -> dict:
        with self.lock():
            self._sweep(self.clock())
            return public(self._read(rid))

    def position(self, rid: str) -> int:
        """How many requests are ahead of this one (0 = next or running)."""
        ids = [r["id"] for r in self._all() if r["state"] in ("queued",) + ACTIVE]
        return ids.index(rid) if rid in ids else 0

    def next_request(self):
        """Claim the oldest queued request, unless one is still claimed or running (one run at a time per engine)."""
        t = self.clock()
        with self.lock():
            self._sweep(t)
            rs = self._all()
            if any(r["state"] in ACTIVE for r in rs):
                return None
            for r in rs:
                if r["state"] == "queued":
                    r.update(state="claimed", claimed_at=iso(t), heartbeat_t=t)
                    self._write(r)
                    return public(r)
        return None

    def _active(self, rid: str) -> dict:
        r = self._read(rid)
        if r["state"] not in ACTIVE:
            raise QueueError("not_active", f"the request is {r['state']}", 409)
        return r

    def progress(self, rid: str, body: dict) -> dict:
        t = self.clock()
        with self.lock():
            r = self._active(rid)
            r["heartbeat_t"] = t
            if body.get("state") == "running":
                r["state"] = "running"
                r["progress"] = {"shot": str(body.get("shot") or ""), "index": int(body.get("index") or 0),
                                 "total": int(body.get("total") or len(r["shots"])), "at": iso(t)}
                if body.get("frame") is not None:
                    r["progress"]["frame"] = int(body.get("frame") or 0)
                    r["progress"]["frames"] = int(body.get("frames") or 0)
            self._write(r)
            return public(r)

    def bundle_path(self, rid: str) -> Path:
        r = self._read(rid)
        if r["state"] not in ACTIVE:
            raise QueueError("not_active", f"the request is {r['state']}", 409)
        return self._dir(rid) / "bundle.tar"

    def result_part(self, rid: str, name: str) -> Path:
        """Where an upload is written before commit_result (only for an active request)."""
        if not self.e["names"].fullmatch(name or ""):
            raise QueueError("invalid", "bad result name for " + self.e["name"], 422)
        with self.lock():
            self._active(rid)
        return self._dir(rid) / "out" / f"{name}.part"

    def commit_result(self, rid: str, name: str) -> int:
        part = self._dir(rid) / "out" / f"{name}.part"
        n = part.stat().st_size
        if n > self.MAX_RESULT:
            part.unlink(missing_ok=True)
            raise QueueError("too_big", f"a result may be at most {self.MAX_RESULT // 1024 ** 2} MB", 413)
        ext = ext_of(self.engine, name)
        part.replace(part.with_suffix(ext))
        with self.lock():
            r = self._read(rid)
            r["results"][name] = f"out/{name}{ext}"
            r["heartbeat_t"] = self.clock()
            self._write(r)
        return n

    def put_result(self, rid: str, name: str, chunks) -> int:
        part = self.result_part(rid, name)
        n = 0
        with open(part, "wb") as f:
            for c in chunks:
                n += len(c)
                if n > self.MAX_RESULT:
                    break
                f.write(c)
        if n > self.MAX_RESULT:
            part.unlink(missing_ok=True)
            raise QueueError("too_big", f"a result may be at most {self.MAX_RESULT // 1024 ** 2} MB", 413)
        return self.commit_result(rid, name)

    def finish(self, rid: str, body: dict) -> dict:
        t = self.clock()
        with self.lock():
            r = self._active(rid)
            if body.get("ok"):
                if not r["results"]:
                    raise QueueError("invalid", "finish ok without any result", 422)
                r.update(state="done", checks=[str(c)[:500] for c in (body.get("checks") or [])][:200],
                         marks=body.get("marks"), duration=body.get("duration"),
                         keys=body.get("keys") if isinstance(body.get("keys"), dict) and len(json.dumps(body["keys"])) < 2_000_000 else None)
                for k in ("gpu", "version"):
                    if body.get(k):
                        r[k] = str(body[k])[:200]
            else:
                e = body.get("error") or {}
                r.update(state="failed", error={"code": str(e.get("code") or "build_error")[:40],
                                                "message": str(e.get("message") or "")[:2000],
                                                "log_tail": str(e.get("log_tail") or "")[-4000:]})
            r.update(finished_at=iso(t), finished_t=t)
            self._write(r)
            return public(r)

    def result_path(self, rid: str, name: str) -> Path:
        r = self._read(rid)
        if name not in r["results"]:
            raise QueueError("not_found", f"no result {name}", 404)
        return self._dir(rid) / r["results"][name]

    def hello(self, body: dict) -> dict:
        t = self.clock()
        h = {"at": iso(t), "t": t, "version": str(body.get("version") or "")[:40], "os": str(body.get("os") or "")[:20],
             "found": bool(body.get("found"))}
        for k in self.e["tool"]:
            h[k] = str(body.get(k) or "")[:400]
        if self.engine == "blender":
            h["gpu"] = str(body.get("gpu") or "")[:200]
        p = self.root() / "hello.json"
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(h))
        tmp.replace(p)
        return h

    def bridge_status(self) -> dict:
        """ready = the desktop app said hello in the last 30 s and found the engine (specs/032 FR-009, specs/038 FR-026)."""
        try:
            h = json.loads((self.root() / "hello.json").read_text())
        except (OSError, ValueError):
            h = None
        rs = self._all()
        st = {"queued": sum(r["state"] == "queued" for r in rs), "running": sum(r["state"] in ACTIVE for r in rs)}
        if not h or self.clock() - h["t"] > HELLO_S:
            return {**st, "ready": False, "seen": bool(h), "code": f"{self.engine}_unavailable", "message": self.e["unavailable"]}
        if not h["found"]:
            return {**st, "ready": False, "seen": True, "code": f"{self.engine}_missing" if self.engine == "ae" else "no_blender",
                    "os": h["os"], "message": self.e["missing"]}
        tool = self.e["tool"][0]
        out = {**st, "ready": True, "seen": True, tool: h.get(tool, ""), "os": h["os"], "version": h["version"]}
        if self.engine == "blender":
            out["gpu"] = h.get("gpu", "")
        return out


def public(r: dict) -> dict:
    return {k: v for k, v in r.items() if not k.endswith("_t")}
