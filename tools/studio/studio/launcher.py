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
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def ensure(timeout: float = 5.0) -> dict:
    """Running server info; starts one in the background if needed (never a second one)."""
    with store.lock("server"):
        i = info()
        if alive(i):
            return i
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
                    i = {"pid": p.pid, "port": port, "started_at": store.now_iso(), "version": VERSION}
                    store.write_json(info_path(), i)
                    return i
                time.sleep(0.1)
            if p.poll() is None:
                p.terminate()
        raise StudioError("ui_unavailable", f"không bật được giao diện (cổng {ports()[0]}–{ports()[-1]} bận "
                          f"hoặc lỗi; xem .studio/server.log)", 503)


def stop() -> bool:
    i = info()
    if not i:
        return False
    stopped = False
    if alive(i):                     # only ever signal our own server
        os.kill(i["pid"], signal.SIGTERM)
        for _ in range(50):
            if not _pid_alive(i["pid"]):
                break
            time.sleep(0.1)
        stopped = True
    info_path().unlink(missing_ok=True)
    return stopped
