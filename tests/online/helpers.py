"""Online-mode test project: temporary data folder, mails written to files, a fake style library."""
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "studio"))


def _ui_helpers():
    """tests/ui/helpers.py (same module name as this file, so load it by path)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("ui_helpers", REPO / "tests" / "ui" / "helpers.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

ENV = ("STUDIO_ROOT", "STUDIO_MODE", "STUDIO_DATA", "MAIL_DIR", "STUDIO_URL")
W = {"X-Studio": "1"}
PASSWORD = "correct horse battery"


class OnlineProject:
    """STUDIO_ROOT is a project with a fake library (from the UI tests); STUDIO_DATA holds accounts and the DB."""

    def __init__(self):
        self.base = _ui_helpers().Project()     # films, sets, styles and a fake library
        self.dir = self.base.dir
        self.data = Path(tempfile.mkdtemp(prefix="online data."))
        self.mails = self.data / "outbox"
        self.old = {k: os.environ.get(k) for k in ENV}
        os.environ.update(STUDIO_ROOT=str(self.dir), STUDIO_MODE="online", STUDIO_DATA=str(self.data),
                          MAIL_DIR=str(self.mails), STUDIO_URL="https://studio.test")

    def close(self):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.data, ignore_errors=True) if not os.environ.get("KEEP_DATA") else print("data:", self.data)
        self.base.close()

    def client(self):
        from fastapi.testclient import TestClient
        from studio.server import create_app
        return TestClient(create_app(), base_url="https://studio.test")

    def flush_mail(self) -> list:
        from studio import mail
        mail.flush()
        return sorted(self.mails.glob("*.eml")) if self.mails.exists() else []

    def last_link(self, email: str, kind: str) -> str:
        """The token of the newest verify/reset mail sent to `email`."""
        for p in reversed(self.flush_mail()):
            text = p.read_text(errors="replace")
            if f"To: {email}" in text:
                m = re.search(rf"#/{kind}/([A-Za-z0-9_\-]+)", text)
                if m:
                    return m.group(1)
        raise AssertionError(f"no {kind} mail for {email}")

    def signup_verified(self, email: str, c=None):
        """A logged-in client of a new member, added the way the owner does in Settings → Users (specs/008)."""
        from studio import accounts
        c = c or self.client()
        accounts.add_user(email, PASSWORD, "customer")
        assert c.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}, headers=W).status_code == 200
        return c

    def copy_fixtures_to(self, account_id: str):
        """Give a customer the demo film, set and style of the UI test project (their own copies)."""
        from studio import store
        d = store.account_dir(account_id)
        for sub in ("films", "references", "my-styles"):
            shutil.copytree(self.dir / sub, d / sub, dirs_exist_ok=True)
        return d


def account_id(c) -> str:
    return c.get("/api/v1/me").json()["id"]


# ---------- running jobs (phase 3): sample films, a fake Claude API, the proxy and a worker ----------
TMP = Path(__file__).resolve().parent / ".tmp"
FAKE_AGENT = Path(__file__).resolve().parent / "fake_agent.py"
REAL_KEY = "sk-ant-real-key-for-tests"
FAKE_USAGE = {"input_tokens": 100_000, "output_tokens": 10_000, "cache_creation_input_tokens": 0,
              "cache_read_input_tokens": 0}          # $0.60 at the opus price of SETTINGS_DEFAULT


def samples() -> dict:
    """good.mp4 (about −14 LUFS, peak −11 dB) and loud.mp4 (about −4 LUFS), 3 s each, made once."""
    TMP.mkdir(exist_ok=True)
    out = {}
    for name, amp in (("good", 0.2818), ("loud", 0.9)):
        p = TMP / f"{name}.mp4"
        if not p.exists():
            import subprocess
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=320x180:d=3:r=10",
                            "-f", "lavfi", "-i", f"aevalsrc={amp}*sin(2*PI*1000*t):s=48000:d=3",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", str(p)],
                           check=True)
        out[name] = p
    f = TMP / "frame.jpg"
    if not f.exists():
        import subprocess
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=orange:s=160x90:d=1",
                        "-frames:v", "1", str(f)], check=True)
    out["frame"] = f
    return out


def free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Server:
    """A uvicorn server for `app` in a thread."""

    def __init__(self, app):
        import threading
        import time
        import uvicorn
        self.port = free_port()
        self.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="warning",
                                                    lifespan="off"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        for _ in range(200):
            if self.server.started:
                break
            time.sleep(0.02)
        self.url = f"http://127.0.0.1:{self.port}"

    def close(self):
        self.server.should_exit = True
        self.thread.join(5)


def fake_upstream():
    """A Messages API that answers with FAKE_USAGE; model `overloaded` gets 529. Records the keys it saw."""
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    app, seen = FastAPI(), []

    @app.post("/v1/messages")
    async def messages(request: Request):
        body = await request.json()
        seen.append({"key": request.headers.get("x-api-key"), "model": body.get("model")})
        if body.get("model") == "overloaded":
            return JSONResponse({"type": "error", "error": {"type": "overloaded_error", "message": "busy"}},
                                status_code=529, headers={"retry-after": "1"})
        return {"id": "msg_1", "type": "message", "role": "assistant", "model": body.get("model"),
                "content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn", "usage": FAKE_USAGE}
    app.state.seen = seen
    return app


class Studio(OnlineProject):
    """OnlineProject plus the fake Claude API, the real proxy and a worker (RUNNER=local, fake agent)."""

    def __init__(self, concurrency: int = 2, interval: float = 0.1):
        super().__init__()
        import threading
        samples()
        self.old.update({k: os.environ.get(k) for k in ("RUNNER", "STUDIO_AGENT_CMD", "STUDIO_MODERATION",
                                                         "ANTHROPIC_API_KEY", "ANTHROPIC_UPSTREAM")})
        self.upstream_app = fake_upstream()
        self.upstream = Server(self.upstream_app)
        os.environ.update(RUNNER="local", STUDIO_MODERATION="fake", ANTHROPIC_API_KEY=REAL_KEY,
                          ANTHROPIC_UPSTREAM=self.upstream.url,
                          STUDIO_AGENT_CMD=f"{sys.executable} {FAKE_AGENT}")
        sys.path.insert(0, str(REPO / "tools" / "runner"))
        import proxy
        import worker
        from studio import quotas
        quotas.update_settings({"concurrency": concurrency})
        self.proxy = Server(proxy.create_app())
        self.worker = worker.Worker(worker.LocalRunner(), self.proxy.url)
        self.interval = interval
        self.stop_flag = threading.Event()
        self.thread = None

    def start(self):
        import threading
        self.thread = threading.Thread(target=self.worker.run_forever, args=(self.interval, self.stop_flag), daemon=True)
        self.thread.start()

    def wait(self, job_id: str, statuses=("done", "failed", "stopped"), timeout: float = 60):
        import time
        from studio import jobs
        end = time.time() + timeout
        while time.time() < end:
            j = jobs.load(job_id)
            if j["status"] in statuses:
                return j
            time.sleep(0.05)
        raise AssertionError(f"{job_id} still {jobs.load(job_id)['status']} after {timeout}s: {jobs.load(job_id)['log'][-5:]}")

    def close(self):
        self.stop_flag.set()
        if self.thread:
            self.thread.join(10)
        self.proxy.close()
        self.upstream.close()
        super().close()


def film_job(c, idea: str = "A small fox finds a lantern", style: str = None, seconds: int = 20, **extra):
    style = style or first_library_style()
    return c.post("/api/v1/jobs", json={"kind": "film", "style": style, "idea": idea, "seconds": seconds, **extra}, headers=W)


def first_library_style() -> str:
    from studio import resources
    return resources.library()["styles"][0]["slug"]


# ---------- Claude plan accounts (specs/008) ----------
FAKE_CLAUDE = Path(__file__).resolve().parent / "fake_claude"


def sign_in(c, slot: int, email: str) -> dict:
    """Sign a Claude account in through the admin API, with the fake Claude Code (STUDIO_CLAUDE_BIN=FAKE_CLAUDE)."""
    r = c.post(f"/api/v1/admin/claude/accounts/{slot}/login", headers=W)
    assert r.status_code == 200, r.text
    r = c.post(f"/api/v1/admin/claude/accounts/{slot}/code", json={"code": f"good-{email}"}, headers=W)
    assert r.status_code == 200, r.text
    return r.json()
