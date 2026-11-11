"""Online-mode test project: temporary data folder, mails written to files, a fake style library."""
import json
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
FAKE_CLAUDE = Path(__file__).resolve().parent / "fake_claude"
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
    """A Messages API that answers with FAKE_USAGE; model `overloaded` gets 529. Records what it saw:
    path, query, the API key, the plan token (Bearer), anthropic-beta, model.
    Plan tokens (Bearer) behave as `app.state.plan[token]` says (specs/008): "ok" (default), "limit:<s>" (429 until
    s seconds from now, with the plan's reset header), "limit-after:<n>:<s>" (the limit after n good answers) or "401". Plan answers carry the plan's rate-limit headers."""
    import time as _t
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    app, seen = FastAPI(), []
    app.state.plan, app.state.count = {}, {}

    @app.post("/v1/messages")
    async def messages(request: Request):
        body = await request.json()
        auth = request.headers.get("authorization") or ""
        bearer = auth[7:] if auth.lower().startswith("bearer ") else None
        seen.append({"key": request.headers.get("x-api-key"), "bearer": bearer, "model": body.get("model"),
                     "beta": request.headers.get("anthropic-beta"), "query": str(request.url.query)})
        plan_headers = {}
        if bearer:
            how = app.state.plan.get(bearer, "ok")
            app.state.count[bearer] = app.state.count.get(bearer, 0) + 1
            if how.startswith("limit-after:"):              # "limit-after:<n>:<s>": n good answers, then the limit
                n, secs = how[12:].split(":")
                how = f"limit:{secs}" if app.state.count[bearer] > int(n) else "ok"
            if how == "401":
                return JSONResponse({"type": "error", "error": {"type": "authentication_error", "message": "bad token"}},
                                    status_code=401)
            if how.startswith("limit:"):
                reset = int(_t.time() + float(how[6:]))
                return JSONResponse({"type": "error", "error": {"type": "rate_limit_error", "message": "limit"}},
                                    status_code=429, headers={"anthropic-ratelimit-unified-status": "rejected",
                                                              "anthropic-ratelimit-unified-reset": str(reset),
                                                              "anthropic-ratelimit-unified-5h-utilization": "1.0",
                                                              "anthropic-ratelimit-unified-5h-reset": str(reset)})
            plan_headers = {"anthropic-ratelimit-unified-status": "allowed",
                            "anthropic-ratelimit-unified-5h-utilization": "0.25",
                            "anthropic-ratelimit-unified-5h-reset": str(int(_t.time() + 3600)),
                            "anthropic-ratelimit-unified-7d-utilization": "0.1",
                            "anthropic-ratelimit-unified-7d-reset": str(int(_t.time() + 86400 * 3))}
        if body.get("model") == "overloaded":
            return JSONResponse({"type": "error", "error": {"type": "overloaded_error", "message": "busy"}},
                                status_code=529, headers={"retry-after": "1"})
        if body.get("stream") and body.get("model") == "stall":     # starts, then only keep-alive pings (live run 2)
            import asyncio
            from fastapi.responses import StreamingResponse

            async def pings():
                yield ('event: message_start\ndata: ' + json.dumps({"type": "message_start", "message": {
                    "model": "stall", "usage": {"input_tokens": 5, "output_tokens": 1}}}) + '\n\n').encode()
                while True:
                    await asyncio.sleep(0.2)
                    yield b'event: ping\ndata: {"type": "ping"}\n\n'
            return StreamingResponse(pings(), media_type="text/event-stream", headers=plan_headers)
        if body.get("stream"):                       # SSE like the real API; gzip when the caller accepts it
            import gzip
            from fastapi.responses import Response
            usage_start = {k: v for k, v in FAKE_USAGE.items() if k != "output_tokens"} | {"output_tokens": 1}
            sse = (f'event: message_start\ndata: {json.dumps({"type": "message_start", "message": {"model": body.get("model"), "usage": usage_start}})}\n\n'
                   f'event: message_delta\ndata: {json.dumps({"type": "message_delta", "usage": {"output_tokens": FAKE_USAGE["output_tokens"]}})}\n\n'
                   'event: message_stop\ndata: {"type": "message_stop"}\n\n').encode()
            headers = {**plan_headers, "content-type": "text/event-stream"}
            if "gzip" in (request.headers.get("accept-encoding") or ""):
                sse, headers["content-encoding"] = gzip.compress(sse), "gzip"
            return Response(sse, headers=headers)
        return JSONResponse({"id": "msg_1", "type": "message", "role": "assistant", "model": body.get("model"),
                             "content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn", "usage": FAKE_USAGE},
                            headers=plan_headers)
    app.state.seen = seen
    app.state.yt_keys, app.state.yt_calls = [], []

    @app.get("/youtube/v3/{endpoint}")
    def youtube(endpoint: str, request: Request):
        """A fake YouTube Data API with the hand-checked numbers of tests/filmcheck/youtube_samples.py (specs/013)."""
        sys.path.insert(0, str(REPO / "tests" / "filmcheck"))
        import youtube_samples
        params = dict(request.query_params)
        app.state.yt_calls.append(endpoint)
        if params.get("id") == "dQw4w9WgXcQ" and params.get("key", "").startswith("AIzaBAD"):
            return JSONResponse({"error": {"code": 400, "message": "API key not valid"}}, status_code=400)
        return youtube_samples.answer(endpoint, params, app.state.yt_keys)

    return app


class Studio(OnlineProject):
    """OnlineProject plus the fake Claude API, the real proxy and a worker (RUNNER=local, fake agent)."""

    def __init__(self, concurrency: int = 2, interval: float = 0.1, plan: bool = False):
        """plan=True: no API key; Claude accounts are signed in with the fake Claude Code (specs/008)."""
        super().__init__()
        import threading
        samples()
        self.old.update({k: os.environ.get(k) for k in ("RUNNER", "STUDIO_AGENT_CMD", "STUDIO_MODERATION",
                                                         "ANTHROPIC_API_KEY", "ANTHROPIC_UPSTREAM", "STUDIO_CLAUDE_BIN")})
        self.upstream_app = fake_upstream()
        self.upstream = Server(self.upstream_app)
        self.old["STUDIO_YOUTUBE_URL"] = os.environ.get("STUDIO_YOUTUBE_URL")
        os.environ.update(RUNNER="local", STUDIO_MODERATION="fake", ANTHROPIC_API_KEY=REAL_KEY,
                          ANTHROPIC_UPSTREAM=self.upstream.url, STUDIO_CLAUDE_BIN=str(FAKE_CLAUDE),
                          STUDIO_AGENT_CMD=f"{sys.executable} {FAKE_AGENT}",
                          STUDIO_YOUTUBE_URL=self.upstream.url + "/youtube/v3")
        if plan:
            os.environ.pop("ANTHROPIC_API_KEY")
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


def sign_in(c, slot: int, email: str) -> dict:
    """Sign a Claude account in through the admin API, with the fake Claude Code (STUDIO_CLAUDE_BIN=FAKE_CLAUDE)."""
    r = c.post(f"/api/v1/admin/claude/accounts/{slot}/login", headers=W)
    assert r.status_code == 200, r.text
    r = c.post(f"/api/v1/admin/claude/accounts/{slot}/code", json={"code": f"good-{email}"}, headers=W)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- an MCP client, like an agent (specs/009) ----------
class McpAgent:
    """Talks to the studio's MCP server at <web>/api/mcp with a real MCP client (Streamable HTTP).
    `call` returns (is_error, data or error text); one session per call, as the server is stateless."""

    def __init__(self, web_url: str, secret: str = None, headers: dict = None):
        self.url = web_url + "/api/mcp"
        self.headers = dict(headers or {})
        if secret:
            self.headers["Authorization"] = f"Bearer {secret}"

    def _run(self, fn):
        import asyncio
        import httpx2
        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        async def go():
            async with httpx2.AsyncClient(headers=self.headers, timeout=60) as hc:
                async with streamable_http_client(self.url, http_client=hc) as streams:
                    async with ClientSession(streams[0], streams[1]) as cs:
                        await cs.initialize()
                        return await fn(cs)
        return asyncio.run(go())

    def tools(self) -> list:
        return sorted(t.name for t in self._run(lambda cs: cs.list_tools()).tools)

    def call(self, name: str, args: dict = None):
        r = self._run(lambda cs: cs.call_tool(name, args or {}))
        text = r.content[0].text if r.content else ""
        if r.is_error:
            return True, text
        return False, json.loads(text) if text[:1] in "{[" else text

    def ok(self, name: str, args: dict = None):
        err, data = self.call(name, args)
        assert not err, f"{name}: {data}"
        return data

    def resource(self, uri: str) -> str:
        r = self._run(lambda cs: cs.read_resource(uri))
        return r.contents[0].text
