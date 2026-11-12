"""The whole studio on one machine, without Docker (specs/014): the web app, the API proxy and the worker of the
online studio as child processes of one supervisor, with every byte of data in one data folder.

    sh bin/studio app start|status|stop|import

The supervisor holds a lock on the data folder, writes host.json (and a pointer in ~/.config/claude-utube/ for the
chat flow), keeps a rotating log per part, starts a crashed part again, and on SIGTERM stops the whole tree.
Nothing here changes how the studio works: the parts get the same code as the VPS build, only other variables."""
import contextlib
import fcntl
import json
import logging
import logging.handlers
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
WEB_PORTS, PROXY_PORTS = range(8790, 8800), range(8780, 8790)
PARTS = ("web", "proxy", "worker")
LOG_BYTES = int(os.environ.get("STUDIO_HOST_LOG_BYTES") or 10 * 1024 * 1024)
LOG_COUNT = 5
READY_S, STOP_S = 30, 15
SANDBOX_WARNING = ("! the agent's Bash is not isolated on this machine (no sandbox): it runs with your user's rights; "
                   "it can only write files in its own job folder")


class HostError(Exception):
    def __init__(self, message, code=2):
        super().__init__(message)
        self.code = code


# ---------- places ----------
def default_data_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ClaudeUtube"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "claude-utube"


def pointer_file() -> Path:
    return Path.home() / ".config" / "claude-utube" / "host.json"


def check_data_dir(d: Path, project: Path = PROJECT) -> Path:
    d = Path(d).expanduser().resolve()
    if d == project.resolve() or d.is_relative_to(project.resolve()):
        raise HostError(f"the data folder must be outside the project folder ({project}); got {d}")
    try:
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".write-test"
        probe.write_text("ok")
        probe.unlink()
    except OSError as e:
        raise HostError(f"the data folder cannot be written: {d} ({e.strerror or e})") from None
    return d


def check_tools(project: Path = PROJECT) -> list:
    """What is missing, each with the studio's install command (R8). The studio never installs system software."""
    missing = []
    for mod, deps in (("fastapi", "ui"), ("uvicorn", "ui"), ("claude_agent_sdk", "online")):
        try:
            __import__(mod)
        except ImportError:
            missing.append(f"{mod} (Python): sh bin/studio deps {deps}")
    for tool, how in (("ffmpeg", "install ffmpeg (for example: sudo apt install ffmpeg)"),
                      ("ffprobe", "install ffmpeg (for example: sudo apt install ffmpeg)"),
                      ("node", "install Node.js 20 or newer")):
        if not shutil.which(tool):
            missing.append(f"{tool}: {how}")
    if not (project / "lib" / "lemo-opuscar" / "AGENTS.md").is_file():
        missing.append("the film library: sh bin/studio setup")
    if not (os.environ.get("STUDIO_CLAUDE_BIN") or shutil.which("claude") or _bundled_claude()):
        missing.append("Claude Code: sh bin/studio deps online")
    return missing


def _bundled_claude():
    try:
        import claude_agent_sdk
        p = Path(claude_agent_sdk.__file__).parent / "_bundled" / "claude"
        return str(p) if p.is_file() else None
    except ImportError:
        return None


# ---------- lock, state ----------
def lock(d: Path):
    """The open, locked file (keep it open), or None when another supervisor holds it."""
    f = open(Path(d) / "host.lock", "a+")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    return f


def is_locked(d: Path) -> bool:
    f = lock(d)
    if f is None:
        return True
    f.close()
    return False


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(data, indent=1))
    os.replace(tmp, path)


def read_state(d: Path):
    try:
        return json.loads((Path(d) / "host.json").read_text())
    except (OSError, ValueError):
        return None


def alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def running_pointer(project: Path = PROJECT):
    """The host started for this project and still running, from the pointer file (the chat flow, R7)."""
    try:
        p = json.loads(pointer_file().read_text())
    except (OSError, ValueError):
        return None
    if Path(p.get("project", "")).resolve() != Path(project).resolve() or not alive(p.get("pid")):
        return None
    if not is_locked(Path(p["data"])):
        return None
    return p


def port_free(port: int) -> bool:
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def free_port(ports, want=None, avoid=()) -> int:
    for p in ([want] if want else []) + list(ports):
        if p and p not in avoid and port_free(p):
            return p
    raise HostError(f"no free port in {ports.start}–{ports.stop - 1}")


# ---------- the supervisor (R1) ----------
def part_command(part: str, project: Path, web: int) -> list:
    py = sys.executable
    if part == "web":
        return [py, "-m", "uvicorn", "studio.server:app", "--app-dir", str(project / "tools" / "studio"),
                "--host", "127.0.0.1", "--port", str(web), "--log-level", "warning"]
    return [py, str(project / "tools" / "runner" / f"{part}.py")]


def part_env(data: Path, project: Path, web: int, proxy: int) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("STUDIO_HOST_")}
    env.update(STUDIO_MODE="online", STUDIO_DATA=str(data), STUDIO_ROOT=str(project), STUDIO_OWNER_UNLIMITED="1",
               RUNNER="local", STUDIO_PROXY=f"http://127.0.0.1:{proxy}", PROXY_HOST="127.0.0.1", PROXY_PORT=str(proxy),
               STUDIO_URL=f"http://127.0.0.1:{web}", MAIL_DIR=str(data / "mail"), TMPDIR=str(data / "tmp"),
               PYTHONUNBUFFERED="1")
    (data / "tmp").mkdir(exist_ok=True)
    if sandbox_available():
        env["STUDIO_AGENT_SANDBOX"] = "1"
    return env


RENDER_KEYS = ("STUDIO_RENDER_MODE", "STUDIO_RENDER_RENDERER", "STUDIO_RENDER_REASON", "PLAYWRIGHT_CHROME")


def render_probe(env: dict, project: Path) -> dict:
    """GPU or software for the worker's pages (specs/019): one run of tools/render/probe.mjs at start."""
    e = {k: v for k, v in env.items() if k not in RENDER_KEYS}
    e["STUDIO_LIB"] = str(project / "lib" / "lemo-opuscar")
    try:
        p = subprocess.run(["node", str(project / "tools" / "render" / "probe.mjs")], env=e, capture_output=True,
                           text=True, timeout=60)
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (OSError, ValueError, IndexError, subprocess.SubprocessError) as ex:
        return {"mode": "software", "renderer": None, "reason": f"probe failed: {ex}", "fix": None, "source": "auto",
                "chrome": None}


def apply_render(env: dict, r: dict) -> dict:
    """Export the probe result to the parts' env; the worker forwards it to jobs (worker.py LocalRunner)."""
    for k in RENDER_KEYS:
        env.pop(k, None)
    env["STUDIO_RENDER_MODE"] = r.get("mode") or "software"
    if r.get("renderer"):
        env["STUDIO_RENDER_RENDERER"] = r["renderer"]
    if r.get("reason"):
        env["STUDIO_RENDER_REASON"] = r["reason"]
    if r.get("mode") == "gpu" and r.get("chrome"):
        env["PLAYWRIGHT_CHROME"] = r["chrome"]
    return env


def sandbox_available() -> bool:
    """The agent's Bash can run in an OS sandbox (specs/016 R5): Seatbelt on macOS, bubblewrap and socat on Linux."""
    if sys.platform == "darwin":
        return True
    return bool(shutil.which("bwrap") and shutil.which("socat"))


def _logger(data: Path, part: str) -> logging.Logger:
    (data / "logs").mkdir(exist_ok=True)
    lg = logging.getLogger(f"studio.host.{part}")
    lg.handlers.clear()
    lg.propagate = False
    h = logging.handlers.RotatingFileHandler(data / "logs" / f"{part}.log", maxBytes=LOG_BYTES, backupCount=LOG_COUNT,
                                             encoding="utf-8")
    h.setFormatter(logging.Formatter("%(message)s"))
    lg.addHandler(h)
    lg.setLevel(logging.INFO)
    return lg


def _pump(stream, lg):
    for line in iter(stream.readline, b""):
        lg.info(line.decode("utf-8", "replace").rstrip("\n"))
    stream.close()


def supervise(data: Path, web: int, proxy: int, project: Path = PROJECT, held=None) -> int:
    data = Path(data)
    f = held or lock(data)
    if f is None:
        raise HostError("another studio is running on this data folder", 0)
    log = _logger(data, "host")
    env = part_env(data, project, web, proxy)
    render = render_probe(env, project)
    apply_render(env, render)
    log.info("render: %s · %s", render.get("mode"), render.get("renderer") or render.get("reason"))
    procs, starts, stopping = {}, {p: [] for p in PARTS}, threading.Event()
    state = {"pid": os.getpid(), "data": str(data), "project": str(project), "web": web, "proxy": proxy,
             "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "children": {}, "error": None,
             "render": render}

    def save():
        state["children"] = {p: procs[p].pid for p in procs}
        _write(data / "host.json", state)
        _write(pointer_file(), state)

    def launch(part):
        p = subprocess.Popen(part_command(part, project, web), cwd=str(project), env=env, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, start_new_session=True)
        threading.Thread(target=_pump, args=(p.stdout, _logger(data, part)), daemon=True).start()
        procs[part] = p
        starts[part].append(time.time())
        log.info("started %s (pid %s)", part, p.pid)

    def end(*_):
        stopping.set()
    signal.signal(signal.SIGTERM, end)
    signal.signal(signal.SIGINT, end)
    log.info("studio host on http://127.0.0.1:%s (proxy %s), data %s", web, proxy, data)
    for part in ("proxy", "worker", "web"):
        launch(part)
    save()
    try:
        while not stopping.wait(1.0):
            for part, p in list(procs.items()):
                if p.poll() is None:
                    continue
                recent = [t for t in starts[part] if time.time() - t < 60]
                if len(recent) >= 5:
                    state["error"] = f"{part} stopped 5 times within a minute; see logs/{part}.log"
                    log.error(state["error"])
                    stopping.set()
                    break
                log.info("%s exited (code %s); starting it again", part, p.returncode)
                time.sleep(2)
                launch(part)
                save()
    finally:
        for p in procs.values():
            with contextlib.suppress(ProcessLookupError):
                os.killpg(p.pid, signal.SIGTERM)
        end_at = time.time() + 8
        for p in procs.values():
            with contextlib.suppress(subprocess.TimeoutExpired):
                p.wait(max(0.1, end_at - time.time()))
        for p in procs.values():                       # jobs the worker started are in the same process groups
            with contextlib.suppress(ProcessLookupError):
                os.killpg(p.pid, signal.SIGKILL)
        _kill_job_processes(data)
        (data / "host.json").unlink(missing_ok=True)
        with contextlib.suppress(OSError, ValueError):
            if json.loads(pointer_file().read_text()).get("pid") == os.getpid():
                pointer_file().unlink()
        log.info("studio host stopped")
        f.close()
    return 1 if state["error"] else 0


def _kill_job_processes(data: Path) -> None:
    """Agents of running jobs have their own process groups (LocalRunner): end the ones recorded under jobs/."""
    for pidf in (Path(data) / "jobs").glob("*/.pid"):
        with contextlib.suppress(OSError, ValueError, ProcessLookupError):
            os.killpg(int(pidf.read_text().strip()), signal.SIGKILL)


# ---------- commands ----------
def _health(web: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{web}/api/v1/health", timeout=2) as r:
            return r.status == 200
    except OSError:
        return False


def start(data=None, web_port=None, proxy_port=None, foreground=False, project: Path = PROJECT, out=print, gate=None) -> int:
    data = check_data_dir(Path(data) if data else default_data_dir(), project)
    if gate:                         # the desktop app's license file (specs/017 R4); web and worker inherit it
        os.environ["STUDIO_LICENSE_GATE"] = str(Path(gate).expanduser())
    st = read_state(data)
    if is_locked(data) and st:
        out(f"✓ the studio is already running on this data folder\nURL: http://127.0.0.1:{st['web']}")
        return 0
    missing = check_tools(project)
    if missing:
        for m in missing:
            out(f"✗ {m}")
        raise HostError("some tools are missing; the studio does not install system software")
    web = free_port(WEB_PORTS, web_port)
    proxy = free_port(PROXY_PORTS, proxy_port, avoid={web})
    if not sandbox_available():
        out(SANDBOX_WARNING)
    if foreground:
        out(f"URL: http://127.0.0.1:{web}")
        return supervise(data, web, proxy, project)
    log = open(data / "logs" / "host-start.log", "ab") if (data / "logs").is_dir() else subprocess.DEVNULL
    subprocess.Popen([sys.executable, "-m", "studio.host", "supervise", str(data), str(web), str(proxy), str(project)],
                     cwd=str(project / "tools" / "studio"), stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                     start_new_session=True, env={**os.environ, "PYTHONPATH": str(project / "tools" / "studio")})
    end = time.time() + READY_S
    while time.time() < end:
        st = read_state(data)
        if st and st.get("error"):
            break
        if st and _health(st["web"]):
            out(f"✓ the studio is running · data {data} · logs {data / 'logs'}\nURL: http://127.0.0.1:{st['web']}")
            return 0
        time.sleep(0.3)
    tail = []
    for part in ("host", "web", "proxy", "worker"):
        p = data / "logs" / f"{part}.log"
        if p.is_file():
            tail += [f"[{part}] {x}" for x in p.read_text(errors="replace").splitlines()[-5:]]
    out("✗ the studio did not answer in time:\n" + "\n".join(tail[-20:]))
    return 1


def status(data=None) -> dict:
    data = Path(data or default_data_dir()).expanduser()
    st = read_state(data) if data.exists() else None
    up = bool(st) and is_locked(data) and alive(st.get("pid"))
    out = {"running": up, "data": str(data), "logs": str(data / "logs")}
    if up:
        out.update(url=f"http://127.0.0.1:{st['web']}", web=st["web"], proxy=st["proxy"],
                   parts={p: alive(pid) for p, pid in (st.get("children") or {}).items()}, started=st["started"],
                   render=st.get("render"))
        out.update(_job_counts(data))
    return out


def _db_jobs(data: Path) -> list:
    import sqlite3
    db = Path(data) / "studio.db"
    if not db.is_file():
        return []
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=10)
    try:
        return [json.loads(r[0]) for r in con.execute("SELECT data FROM docs WHERE kind = 'job'")]
    finally:
        con.close()


def _job_counts(data: Path) -> dict:
    js = [j for j in _db_jobs(data) if "charged" in j]
    return {"jobs_running": sum(j["status"] == "running" for j in js), "jobs_queued": sum(j["status"] == "queued" for j in js),
            "jobs": [{"id": j["id"], "name": j["name"], "status": j["status"]} for j in js if j["status"] == "running"]}


def check(project: Path = PROJECT) -> dict:
    """What the desktop app shows on its setup screen (specs/015 R2)."""
    missing = check_tools(project)
    return {"ok": not missing, "missing": missing, "data_default": str(default_data_dir())}


def cert(data=None) -> dict:
    """The share gateway's own TLS certificate (specs/018 R4): made once in <data>/share/, then reused."""
    import datetime
    import hashlib
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    d = Path(data or default_data_dir()).expanduser() / "share"
    d.mkdir(parents=True, exist_ok=True)
    cf, kf = d / "cert.pem", d / "key.pem"
    if not (cf.is_file() and kf.is_file()):
        key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "claude-Utube studio")])
        now = datetime.datetime.now(datetime.timezone.utc)
        c = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
             .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(days=1))
             .not_valid_after(now + datetime.timedelta(days=3650))
             .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
             .sign(key, hashes.SHA256()))
        fd = os.open(kf, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        cf.write_bytes(c.public_bytes(serialization.Encoding.PEM))
    pem = cf.read_text()
    der = x509.load_pem_x509_certificate(pem.encode()).public_bytes(serialization.Encoding.DER)
    return {"cert": pem, "key": kf.read_text(), "fingerprint": hashlib.sha256(der).hexdigest()}


WHISPER_MODELS = ("base.en", "base")   # small (Chinese) downloads on first use


def models(project: Path = PROJECT, out=print) -> int:
    """Download the speech-check models into the HuggingFace cache (specs/016 R3). Skips what is there."""
    py = project / "lib" / "lemo-opuscar" / ".venv" / "bin" / "python"
    if not py.is_file() and not os.environ.get("CU_MODELS_FAKE"):
        out("✗ the library's packages are missing: sh bin/studio deps voice")
        return 1
    code = 0
    for name in WHISPER_MODELS:
        if os.environ.get("CU_MODELS_FAKE"):
            ok, err = os.environ["CU_MODELS_FAKE"] != "fail", "network is unreachable"
        else:
            r = subprocess.run([str(py), "-c", "import sys; from faster_whisper.utils import download_model; "
                                "download_model(sys.argv[1])", name], capture_output=True, text=True)
            ok, err = r.returncode == 0, (r.stderr.strip().splitlines() or ["unknown error"])[-1]
        out(f"✓ {name}" if ok else f"✗ {name}: {err}")
        code = code if ok else 1
    return code


def stop(data=None, force=False, out=print) -> int:
    data = Path(data or default_data_dir()).expanduser()
    st = read_state(data)
    if not st or not alive(st.get("pid")) or not is_locked(data):
        out("✓ the studio is not running")
        return 0
    running = [j for j in _db_jobs(data) if "charged" in j and j["status"] == "running"]
    if running and not force:
        out("✗ jobs are running: " + ", ".join(f"{j['name']} ({j['id']})" for j in running)
            + ". Wait for them, or stop with --force (they are marked stopped).")
        return 1
    if running:
        _mark_stopped(data, [j["id"] for j in running])
    os.kill(int(st["pid"]), signal.SIGTERM)
    end = time.time() + STOP_S
    while time.time() < end and is_locked(data):
        time.sleep(0.2)
    if is_locked(data):
        with contextlib.suppress(ProcessLookupError):
            os.kill(int(st["pid"]), signal.SIGKILL)
        time.sleep(0.5)
    out("✓ the studio stopped")
    return 0


def _mark_stopped(data: Path, ids: list) -> None:
    os.environ.update(STUDIO_MODE="online", STUDIO_DATA=str(data))
    from studio import jobs
    for i in ids:
        with contextlib.suppress(Exception):
            jobs.finish(i, "stopped", error="Stopped when the studio was closed")


def owner_id(data: Path):
    import sqlite3
    db = Path(data) / "studio.db"
    if not db.is_file():
        return None
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=10)
    try:
        r = con.execute("SELECT id FROM accounts WHERE role = 'admin' AND deleted_at IS NULL ORDER BY created_at LIMIT 1").fetchone()
        return r[0] if r else None
    finally:
        con.close()


def import_project(data=None, project: Path = PROJECT, out=print) -> int:
    """Copy films/, my-styles/ and channels/ of a project into the owner's folder (R6); what is there stays."""
    data = Path(data or default_data_dir()).expanduser()
    owner = owner_id(data)
    if not owner:
        out("✗ there is no owner yet: start the studio (sh bin/studio app start), open it and create the owner first")
        return 2
    dest = data / "accounts" / owner
    copied, skipped = [], []
    for sub in ("films", "my-styles", "channels"):
        src = Path(project) / sub
        if not src.is_dir():
            continue
        (dest / sub).mkdir(parents=True, exist_ok=True)
        for item in sorted(src.iterdir()):
            target = dest / sub / item.name
            if target.exists() or target.is_symlink():
                skipped.append(f"{sub}/{item.name}")
            elif item.is_dir():
                shutil.copytree(item, target, symlinks=True)
                copied.append(f"{sub}/{item.name}")
            elif item.is_file():
                shutil.copy2(item, target)
                copied.append(f"{sub}/{item.name}")
    out(f"✓ copied {len(copied)}, kept {len(skipped)} that were already there · into {dest}")
    for c in copied:
        out(f"  + {c}")
    return 0


def main(argv=None) -> int:
    a = argv or sys.argv[1:]
    if a and a[0] == "supervise":
        return supervise(Path(a[1]), int(a[2]), int(a[3]), Path(a[4]))
    print("usage: python -m studio.host supervise <data> <web port> <proxy port> <project>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
