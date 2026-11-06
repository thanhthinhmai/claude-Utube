"""Start the web server in the background, check it, stop it (research.md §7)."""
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from . import APP_ID, VERSION, store
from .store import StudioError

TOOLS = Path(__file__).resolve().parents[1]          # tools/studio


def ports() -> list:
    a, b = (int(x) for x in os.environ.get("STUDIO_UI_PORTS", "8787-8799").split("-"))
    return list(range(a, b + 1))


def info_path() -> Path:
    return store.state_dir() / "server.json"


def info():
    return store.read_json(info_path())


def url(port: int, path: str = "/") -> str:
    return f"http://localhost:{port}{path}"


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, TypeError):
        return False


def _health(port: int, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/health", timeout=timeout) as r:
            return json.loads(r.read()).get("app") == APP_ID
    except Exception:
        return False


def alive(i=None) -> bool:
    i = i if i is not None else info()
    return bool(i) and _pid_alive(i.get("pid")) and _health(i.get("port"))


def _free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Like uvicorn: a port only held by closed connections (TIME_WAIT, ~60 s after a restart) is free;
        # a port someone is listening on is still refused.
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def code_stamp() -> str:
    """Changes whenever the server code or the UI files change (e.g. after `git pull`)."""
    files = [f for f in (TOOLS / "studio").rglob("*") if f.suffix in (".py", ".js", ".css", ".html")]
    return str(max((f.stat().st_mtime_ns for f in files), default=0))


def _orphans() -> list:
    """Studio servers of THIS project that server.json does not know about (left from an older run)."""
    try:
        out = subprocess.run(["ps", "-ww", "-eo", "pid=,args="], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    known = (info() or {}).get("pid")
    mine = f"--app-dir {TOOLS} "
    pids = []
    for line in out.splitlines():
        pid, _, args = line.strip().partition(" ")
        if "studio.server:app" in args and mine in args + " " and pid.isdigit() and int(pid) not in (known, os.getpid()):
            pids.append(int(pid))
    return pids


def _kill(pid: int):
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return
    for _ in range(50):
        if not _pid_alive(pid):
            return
        time.sleep(0.1)


def ensure(timeout: float = 5.0) -> dict:
    """Running server info; starts one in the background if needed (never a second one)."""
    with store.lock("server"):
        for pid in _orphans():          # an old server would hold the first port and run old code
            _kill(pid)
        i = info()
        if alive(i):
            if i.get("code") == code_stamp():
                return i
            _kill(i["pid"])               # code changed since it started (git pull): restart
        log = open(store.state_dir() / "server.log", "ab")
        for port in ports():
            if not _free(port):
                continue
            env = dict(os.environ, STUDIO_ROOT=str(store.root()))
            p = subprocess.Popen([sys.executable, "-m", "uvicorn", "studio.server:app", "--app-dir", str(TOOLS),
                                  "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
                                 env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
            t0 = time.time()
            while time.time() - t0 < timeout:
                if p.poll() is not None:
                    break
                if _health(port, 0.3):
                    i = {"pid": p.pid, "port": port, "started_at": store.now_iso(), "version": VERSION,
                         "code": code_stamp()}
                    store.write_json(info_path(), i)
                    return i
                time.sleep(0.1)
            if p.poll() is None:
                p.terminate()
        raise StudioError("ui_unavailable", f"không bật được giao diện (cổng {ports()[0]}–{ports()[-1]} bận "
                          f"hoặc lỗi; xem .studio/server.log)", 503)


def stop() -> bool:
    """Stop this project's server, and any old one of this project that server.json forgot."""
    stopped = False
    for pid in _orphans():
        _kill(pid)
        stopped = True
    i = info()
    if i and alive(i):               # only ever signal our own server
        _kill(i["pid"])
        stopped = True
    info_path().unlink(missing_ok=True)
    return stopped
