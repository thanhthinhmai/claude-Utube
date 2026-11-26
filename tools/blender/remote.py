"""Blender through the desktop app's bridge from inside a job (specs/038 T013): the job sends a bundle (kit, shot
scripts, layers, request.json) to the proxy (/internal/blender/requests), waits for the desktop app to render it, then
downloads one result per shot (S<n>: mp4, or a tar of PNG frames that is packed here)."""
import io
import json
import os
import shutil
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from blender import local
from blender.config import BlenderError

POLL_S = 1.0


def active() -> bool:
    return bool(os.environ.get("STUDIO_JOB") and os.environ.get("STUDIO_PROXY"))


def _base() -> str:
    return os.environ.get("STUDIO_PROXY", "http://proxy:8780").rstrip("/")


def _call(method: str, path: str, data: bytes = None, ctype: str = None, timeout: float = 60):
    token = os.environ.get("STUDIO_JOB_TOKEN") or os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or ""
    h = {"authorization": f"Bearer {token}"}
    if ctype:
        h["content-type"] = ctype
    req = urllib.request.Request(_base() + path, data=data, method=method, headers=h)
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read()).get("error") or {}
        except Exception:     # noqa: BLE001
            err = {}
        raise BlenderError(err.get("code") or err.get("type") or "bridge", err.get("message") or f"the studio answered {e.code}") from None
    except (urllib.error.URLError, OSError) as e:
        raise BlenderError("blender_unavailable", f"the studio proxy cannot be reached: {e}") from None


def status() -> dict:
    with _call("GET", "/internal/blender/status") as r:
        return json.loads(r.read())


def bundle(film_dir: Path, req: dict) -> bytes:
    """A tar with kit/, the shot scripts, layers and request.json, the same tree local.stage() writes."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for p in local._files(local.KIT):
            tar.add(p, arcname="kit/" + str(p.relative_to(local.KIT)))
        for sh in req["shots"]:
            for rel in (sh.get("script"), sh.get("layers")):
                src = film_dir / rel if rel else None
                if src and src.exists():
                    tar.add(src, arcname=rel)
                elif rel and rel == sh.get("script"):
                    raise BlenderError("bad_plan", f"{sh['id']}: {rel} is missing")
        data = json.dumps(req, indent=1).encode()
        ti = tarfile.TarInfo("request.json")
        ti.size = len(data)
        tar.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


def submit(film: str, shots: list, kind: str, tar: bytes) -> str:
    b = uuid.uuid4().hex
    meta = json.dumps({"film": film, "shots": shots, "kind": kind}).encode()
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"meta\"\r\nContent-Type: application/json\r\n\r\n").encode() + meta + \
        (f"\r\n--{b}\r\nContent-Disposition: form-data; name=\"bundle\"; filename=\"bundle.tar\"\r\n"
         "Content-Type: application/x-tar\r\n\r\n").encode() + tar + f"\r\n--{b}--\r\n".encode()
    with _call("POST", "/internal/blender/requests", body, f"multipart/form-data; boundary={b}") as r:
        return json.loads(r.read())["id"]


def _download(rid: str, name: str, dest: Path) -> Path:
    with _call("GET", f"/internal/blender/requests/{rid}/result/{name}", timeout=600) as r, open(dest, "wb") as f:
        while True:
            c = r.read(1 << 20)
            if not c:
                break
            f.write(c)
    return dest


def build(film_dir, shots: list, fps: int, size, kind: str = "render", quarter: bool = False, plans: dict = None,
          progress=None) -> dict:
    d = Path(film_dir)
    req = {"kind": kind, "film": d.name, "fps": int(fps), "size": list(size), "quarter": bool(quarter),
           "shots": [{"id": sh["id"], "frames": int(sh["frames"]), "script": f"blender/{sh['id']}.py",
                      **({"layers": f"layers/{sh['id']}"} if (d / "layers" / sh["id"]).is_dir() else {}),
                      **({"plan": (plans or {}).get(sh["id"])} if (plans or {}).get(sh["id"]) else {})}
                     for sh in shots]}
    rid = submit(d.name, [s["id"] for s in req["shots"]], kind, bundle(d, req))
    print(f"Blender request {rid}: waiting for the desktop app", flush=True)
    last, st = None, {}
    while True:
        with _call("GET", f"/internal/blender/requests/{rid}") as r:
            st = json.loads(r.read())
        if st["state"] == "queued" and last != ("queued", st.get("ahead")):
            last = ("queued", st.get("ahead"))
            if st.get("ahead"):
                print(f"waiting for Blender: {st['ahead']} request(s) ahead", flush=True)
        if st["state"] == "running" and progress and st.get("progress") and st["progress"] != last:
            last = st["progress"]
            progress({"state": "running", **st["progress"]})
        if st["state"] == "done":
            break
        if st["state"] in ("failed", "expired"):
            e = st.get("error") or {}
            raise BlenderError(e.get("code") or "bridge_lost", e.get("message") or "the Blender run failed", e.get("log_tail") or "")
        time.sleep(POLL_S)
    out = {"run": rid, "log": "", "gpu": st.get("gpu") or "", "version": st.get("version") or "", "shots": {}}
    dest = d / "out" / "blender"
    dest.mkdir(parents=True, exist_ok=True)
    for sh in req["shots"]:
        name = f"{sh['id']}-quarter" if quarter else sh["id"]
        with tempfile.TemporaryDirectory() as tmp:
            got = _download(rid, sh["id"], Path(tmp) / "result")
            head = got.read_bytes()[:512]
            if kind == "render" and len(head) > 262 and head[257:262] == b"ustar":
                frames = Path(tmp) / sh["id"]
                frames.mkdir()
                with tarfile.open(got) as t:
                    t.extractall(frames, filter="data")
                out["shots"][sh["id"]] = str(local.pack(frames, fps, dest / f"{name}.mp4"))
            else:
                ext = {"render": ".mp4", "plate": ".png", "plan": ".json"}[kind]
                target = dest / f"{name}{ext}" if kind == "render" else dest / f"{sh['id']}-{kind}{ext}"
                shutil.move(str(got), target)
                out["shots"][sh["id"]] = str(target)
    return out
