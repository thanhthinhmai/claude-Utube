"""Build through the desktop app's bridge from inside a job (specs/032 T009/T015): the job sends the bundle to the
proxy (/internal/ae/requests), waits for the desktop app to build it, then downloads the MASTER clip."""
import json
import os
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from ae import bundle
from ae.local import AeError

POLL_S = 1.0


def _base() -> str:
    return os.environ.get("STUDIO_PROXY", "http://proxy:8780").rstrip("/")


def _headers() -> dict:
    token = os.environ.get("STUDIO_JOB_TOKEN") or os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or ""
    return {"authorization": f"Bearer {token}"}


def _call(method: str, path: str, data: bytes = None, ctype: str = None, timeout: float = 60):
    h = _headers()
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
        raise AeError(err.get("code") or err.get("type") or "bridge", err.get("message") or f"the studio answered {e.code}") from None
    except (urllib.error.URLError, OSError) as e:
        raise AeError("ae_unavailable", f"the studio proxy cannot be reached: {e}") from None


def status() -> dict:
    with _call("GET", "/internal/ae/status") as r:
        return json.loads(r.read())


def submit(film: str, shots: list, tar: bytes) -> str:
    b = uuid.uuid4().hex
    meta = json.dumps({"film": film, "shots": shots}).encode()
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"meta\"\r\nContent-Type: application/json\r\n\r\n").encode() + meta + \
        (f"\r\n--{b}\r\nContent-Disposition: form-data; name=\"bundle\"; filename=\"bundle.tar\"\r\n"
         "Content-Type: application/x-tar\r\n\r\n").encode() + tar + f"\r\n--{b}--\r\n".encode()
    with _call("POST", "/internal/ae/requests", body, f"multipart/form-data; boundary={b}") as r:
        return json.loads(r.read())["id"]


def build(film_dir, shots=None, progress=None, sheet: dict = None) -> dict:
    d = Path(film_dir)
    with tempfile.TemporaryDirectory() as tmp:
        b = bundle.make(d, shots, Path(tmp) / "bundle.tar", sheet=sheet)
        rid = submit(d.name, b["shots"], Path(b["path"]).read_bytes())
    print(f"AE request {rid}: waiting for the desktop app", flush=True)
    last = None
    while True:
        with _call("GET", f"/internal/ae/requests/{rid}") as r:
            st = json.loads(r.read())
        if st["state"] == "queued" and last != ("queued", st.get("ahead")):
            last = ("queued", st.get("ahead"))
            if st.get("ahead"):
                print(f"waiting for AE: {st['ahead']} request(s) ahead", flush=True)
        if st["state"] == "running" and progress and st.get("progress") and st["progress"] != last:
            last = st["progress"]
            progress({"state": "running", **st["progress"]})
        if st["state"] == "done":
            break
        if st["state"] in ("failed", "expired"):
            e = st.get("error") or {}
            raise AeError(e.get("code") or "build_error", e.get("message") or "the AE build failed", e.get("log_tail") or "")
        time.sleep(POLL_S)
    out = d / "out"
    out.mkdir(exist_ok=True)
    master = out / f"ae-{rid}.mp4"
    with _call("GET", f"/internal/ae/requests/{rid}/result/MASTER", timeout=600) as r, open(master, "wb") as f:
        while True:
            c = r.read(1 << 20)
            if not c:
                break
            f.write(c)
    return {"master": str(master), "marks": st.get("marks") or [], "duration": st.get("duration") or 0,
            "checks": [c for c in st.get("checks") or [] if c.startswith("CHECK ")], "log": "", "dir": str(out)}
