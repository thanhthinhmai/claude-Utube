"""API proxy between job containers and Anthropic (specs/007 contracts/runner.md, research R3, R13;
specs/008 contracts/runner.md).

- `POST /v1/messages` (and `/v1/messages/count_tokens`): checks the job's own token, then sends the call through
  the Claude account (plan) used least in the last 5 hours, as `Authorization: Bearer <its token>`. A plan at its
  limit (429) or with a broken sign-in (401) hands the call to the next account. With none left: the fallback
  ANTHROPIC_API_KEY if set, else wait up to 15 s for one, else the job fails as the studio's fault.
  Every call is a row in `call`; tokens count against the job's token cap.
- `/internal/…`: what `sh bin/studio job …`, `review …` and `web fetch` call from inside a container.
Logs carry token counts and cost only, never prompt text.

Run: STUDIO_MODE=online STUDIO_DATA=/data python tools/runner/proxy.py   (listens on 0.0.0.0:8780)"""
import asyncio
import hashlib
import json
import logging
import os
import secrets
import sys
import time
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "studio"))

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from filmcheck import topics as yt_topics, webfetch  # noqa: E402
from studio import claude_plan, db, jobs, quotas, reviews, store  # noqa: E402
from studio.store import StudioError  # noqa: E402

log = logging.getLogger("studio.proxy")
# Claude Code's own headers go through as they are (research R3); these never do
DROP_HEADERS = ("host", "content-length", "connection", "authorization", "x-api-key", "cookie", "accept-encoding",
                "proxy-authorization", "transfer-encoding", "keep-alive", "upgrade", "te", "trailer")
BACK_HEADERS = ("content-type", "retry-after", "request-id", "anthropic-ratelimit-requests-remaining",
                "anthropic-ratelimit-tokens-remaining", "x-should-retry")
FETCH_LIMIT = 60               # pages one job may open (specs/010 R4)
WAIT_FOR_REST_S = 15            # specs/008 FR-110, like neb-creative-tool's WAIT_FOR_REST_MS


def stall_seconds() -> float:
    """A stream with no content for this long is cut so Claude Code sends the call again. Anthropic's keep-alive
    pings do not count: in the second live run they ran for 20 minutes with nothing else (2026-11-09)."""
    return float(os.environ.get("STUDIO_STREAM_STALL_S", "300"))


def only_pings(chunk: bytes) -> bool:
    """True when an SSE chunk carries nothing but keep-alive pings (or blank lines)."""
    for line in chunk.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if not line or line == "event: ping" or (line.startswith("data:") and '"ping"' in line and "content" not in line):
            continue
        return False
    return True


class Stalled(Exception):
    pass


# ---------- job tokens ----------
def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue(job_id: str) -> str:
    """A new token for one run of a job (32 random bytes; only the hash is kept)."""
    token = "sk-job-" + secrets.token_urlsafe(32)
    with db.tx() as con:
        con.execute("INSERT INTO job_tokens VALUES (?, ?, ?, NULL, ?)", (_hash(token), job_id, store.now_iso(), time.time()))
    return token


def revoke(job_id: str) -> None:
    with db.tx() as con:
        con.execute("UPDATE job_tokens SET revoked_at = ? WHERE job_id = ? AND revoked_at IS NULL",
                    (store.now_iso(), job_id))


def last_ok(job_id: str) -> float:
    """When Claude last answered this job successfully (or when its token was issued)."""
    with db.read() as con:
        r = con.execute("SELECT max(last_ok_at) FROM job_tokens WHERE job_id = ?", (job_id,)).fetchone()
    return r[0] or 0.0


def _mark_ok(token_hash: str) -> None:
    with db.tx() as con:
        con.execute("UPDATE job_tokens SET last_ok_at = ? WHERE token_hash = ?", (time.time(), token_hash))


def _token(request: Request) -> str:
    t = request.headers.get("x-api-key") or ""
    auth = request.headers.get("authorization") or ""
    if not t and auth.lower().startswith("bearer "):
        t = auth[7:].strip()
    return t


class Denied(Exception):
    def __init__(self, status: int, kind: str, message: str):
        self.status, self.kind, self.message = status, kind, message


def job_of(request: Request, job_id: str = None):
    """(job, token hash) for a live token of a running job; Denied otherwise."""
    t = _token(request)
    if not t:
        raise Denied(401, "authentication_error", "missing job token")
    h = _hash(t)
    with db.read() as con:
        r = con.execute("SELECT job_id, revoked_at FROM job_tokens WHERE token_hash = ?", (h,)).fetchone()
    if not r or r["revoked_at"]:
        raise Denied(401, "authentication_error", "job token is not valid")
    if job_id and r["job_id"] != job_id:
        raise Denied(403, "permission_error", "this token belongs to another job")
    j = store.doc_get("job", r["job_id"])
    if not j or j["status"] in jobs.FINAL:       # waiting_review still lets the agent finish its last reply
        raise Denied(401, "authentication_error", "the job is not running")
    return j, h


def _anthropic_error(status: int, kind: str, message: str, retry_after: int = None) -> JSONResponse:
    r = JSONResponse({"type": "error", "error": {"type": kind, "message": message}}, status_code=status)
    if retry_after:
        r.headers["retry-after"] = str(retry_after)
    return r


# ---------- usage ----------
def _numbers(u) -> dict:
    """Token counts of a usage block, plus the web search count (specs/010 R4: Claude Code's WebSearch is a call
    with the server tool `web_search`, counted in server_tool_use)."""
    u = u or {}
    out = {k: v for k, v in u.items() if isinstance(v, (int, float))}
    n = (u.get("server_tool_use") or {}).get("web_search_requests") if isinstance(u.get("server_tool_use"), dict) else None
    if isinstance(n, (int, float)) and n:
        out["web_search_requests"] = n
    return out


def usage_of_stream(chunks: list) -> tuple:
    """(model, usage) from the SSE events of a streamed answer: message_start, then message_delta totals."""
    model, usage, buf = None, {}, b"".join(chunks).decode("utf-8", "replace")
    for line in buf.splitlines():
        if not line.startswith("data:"):
            continue
        try:
            ev = json.loads(line[5:].strip())
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "message_start":
            m = ev.get("message") or {}
            model = m.get("model") or model
            usage.update(_numbers(m.get("usage")))
        elif ev.get("type") == "message_delta":
            usage.update(_numbers(ev.get("usage")))
    return model, usage


def charge(job: dict, via: str, model: str, usage: dict) -> None:
    """Record the call and stop the job past its token cap (FR-116)."""
    t = quotas.record_call(job["id"], via, model, usage)
    s = quotas.settings()
    log.info("job %s via %s model %s tokens %s (job %s) cost $%.4f", job["id"], via, model, quotas.tokens_of(usage),
             t["tokens"], t["cost_usd"])
    if t["tokens"] >= s["job_token_cap"]:
        over_cap(job["id"])


def over_cap(job_id: str) -> None:
    if not jobs.publish_cut(job_id, "the job reached its token limit during the Publish step"):   # specs/011 R7
        quotas.fail(job_id, "The job used more than its token limit and was stopped. Your credit was refunded.", "studio")
    revoke(job_id)


def strip_oauth_beta(value: str) -> str:
    return ",".join(b for b in (x.strip() for x in (value or "").split(",")) if b and not b.startswith("oauth-"))


# ---------- app ----------
class StepIn(BaseModel):
    text: str = Field(max_length=120)
    progress: Optional[dict] = None


class YouTubeIn(BaseModel):
    endpoint: str = Field(max_length=20)
    params: dict = Field(default_factory=dict)


YT_LOCK = __import__("threading").Lock()           # one YouTube call at a time: the day's units stay right


class LogIn(BaseModel):
    lines: list = Field(default_factory=list, max_length=60)


class DoneIn(BaseModel):
    film: Optional[str] = None
    style: Optional[str] = None


class FailIn(BaseModel):
    text: str = Field(max_length=2000)
    by: str = "studio"


class FetchIn(BaseModel):
    url: str = Field(max_length=2000)


class ReviewIn(BaseModel):
    kind: str
    set: Optional[str] = None
    summary: str = Field(max_length=200_000)
    final_round: bool = False


def create_app() -> FastAPI:
    import contextlib
    upstream = os.environ.get("ANTHROPIC_UPSTREAM", "https://api.anthropic.com").rstrip("/")
    client = httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=600, write=60, pool=10))

    @contextlib.asynccontextmanager
    async def lifespan(_):
        yield
        await client.aclose()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

    @app.exception_handler(Denied)
    async def denied(_, e: Denied):
        return _anthropic_error(e.status, e.kind, e.message)

    @app.exception_handler(StudioError)
    async def studio_error(_, e: StudioError):
        return JSONResponse({"error": {"code": e.code, "message": e.message}}, status_code=e.status)

    @app.get("/health")
    def health():
        return {"ok": True}

    async def send(request: Request, path: str, body: bytes, auth: dict, api: bool):
        headers = {k: v for k, v in request.headers.items() if k.lower() not in DROP_HEADERS}
        if api:
            beta = strip_oauth_beta(headers.pop("anthropic-beta", ""))
            if beta:
                headers["anthropic-beta"] = beta
        headers.update(auth)
        headers["accept-encoding"] = "identity"     # httpx would ask for gzip; streamed answers are relayed raw
        url = upstream + path + (f"?{request.url.query}" if request.url.query else "")
        return await client.send(client.build_request("POST", url, content=body, headers=headers), stream=True)

    async def relay_answer(r, job: dict, h: str, via: str, metered: bool):
        back = {k: v for k, v in r.headers.items()
                if k.lower() in BACK_HEADERS or k.lower().startswith("anthropic-ratelimit-unified-")}
        if r.status_code >= 400:              # 529, 5xx…: the service's trouble, passed through so the SDK retries
            data = await r.aread()
            await r.aclose()
            log.info("job %s via %s upstream %s", job["id"], via, r.status_code)
            return Response(data, status_code=r.status_code, headers=back)
        if not r.headers.get("content-type", "").startswith("text/event-stream"):
            data = await r.aread()
            await r.aclose()
            _mark_ok(h)
            if metered:
                try:
                    msg = json.loads(data)
                    charge(job, via, msg.get("model"), _numbers(msg.get("usage")))
                except (json.JSONDecodeError, AttributeError):
                    pass
            return Response(data, status_code=r.status_code, headers=back)

        async def stream():
            chunks, limit = [], stall_seconds()
            it, last = r.aiter_raw().__aiter__(), time.monotonic()
            try:
                while True:
                    try:
                        chunk = await asyncio.wait_for(it.__anext__(), timeout=limit)
                    except StopAsyncIteration:
                        break
                    except asyncio.TimeoutError:
                        chunk = b""
                    now = time.monotonic()
                    if not only_pings(chunk):
                        last = now
                    elif now - last > limit:     # broken off, not ended: the client sees an error and retries
                        log.info("job %s via %s: stream stalled %.0f s with no content, cut", job["id"], via, now - last)
                        raise Stalled()
                    if chunk:
                        chunks.append(chunk)
                        yield chunk
            finally:
                await r.aclose()
                _mark_ok(h)
                if metered:
                    model, usage = usage_of_stream(chunks)
                    charge(job, via, model, usage)
        return StreamingResponse(stream(), status_code=r.status_code, headers=back)

    async def forward(request: Request, path: str, metered: bool):
        job, h = job_of(request)
        s = quotas.settings()
        if metered and (job.get("tokens") or 0) >= s["job_token_cap"]:
            over_cap(job["id"])
            return _anthropic_error(429, "rate_limit_error", "job token limit reached")
        body = await request.body()
        waited = False
        while True:
            for slot in await asyncio.to_thread(claude_plan.usable):            # least used first (R4)
                token = await asyncio.to_thread(claude_plan.access_token, slot)
                if not token:
                    await asyncio.to_thread(claude_plan.mark_needs_signin, slot)
                    log.info("job %s plan:%s cannot refresh its sign-in", job["id"], slot)
                    continue
                r = await send(request, path, body, {"authorization": f"Bearer {token}"}, api=False)
                if r.status_code == 401:                                      # refresh once, then give up on it
                    await r.aclose()
                    token = await asyncio.to_thread(claude_plan.access_token, slot, True)
                    r = await send(request, path, body, {"authorization": f"Bearer {token}"}, api=False) if token else None
                    if r is None or r.status_code == 401:
                        if r is not None:
                            await r.aclose()
                        await asyncio.to_thread(claude_plan.mark_needs_signin, slot)
                        log.info("job %s plan:%s 401: needs sign-in", job["id"], slot)
                        continue
                await asyncio.to_thread(claude_plan.note_usage, slot, r.headers)
                if r.status_code == 429:                                      # the plan's limit: next account
                    await r.aclose()
                    until = await asyncio.to_thread(claude_plan.mark_limited, slot, claude_plan.reset_at(r.headers))
                    log.info("job %s plan:%s 429: rests until %s", job["id"], slot, until)
                    continue
                if r.status_code < 400:
                    await asyncio.to_thread(claude_plan.mark_ok, slot)
                return await relay_answer(r, job, h, f"plan:{slot}", metered)
            key = os.environ.get("ANTHROPIC_API_KEY")
            if key:                                                           # FR-117: the fallback key
                r = await send(request, path, body, {"x-api-key": key}, api=True)
                return await relay_answer(r, job, h, "api", metered)
            nxt = await asyncio.to_thread(claude_plan.next_free)
            if nxt and not waited:
                delay = claude_plan._ts(nxt[1]) - store.clock()
                if delay <= WAIT_FOR_REST_S:
                    waited = True
                    await asyncio.sleep(max(0.0, delay) + 0.05)
                    continue
            when = f" until {nxt[1][11:16]} UTC" if nxt else ""
            quotas.fail(job["id"], f"No Claude account is available{when}. Your credit was refunded.", "studio")
            revoke(job["id"])
            log.info("job %s: no Claude account available%s", job["id"], when)
            return _anthropic_error(429, "rate_limit_error", f"no Claude account is available{when}")

    @app.post("/v1/messages")
    async def messages(request: Request):
        return await forward(request, "/v1/messages", metered=True)

    @app.post("/v1/messages/count_tokens")
    async def count_tokens(request: Request):
        return await forward(request, "/v1/messages/count_tokens", metered=False)

    @app.api_route("/v1/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    @app.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def unknown(rest: str):
        """Only the Messages API goes through (research R3)."""
        return _anthropic_error(404, "not_found_error", "not available through the studio")

    # ---------- what the CLI in a container calls ----------
    @app.post("/internal/jobs/{job_id}/step")
    def step(job_id: str, body: StepIn, request: Request):
        job_of(request, job_id)
        jobs.step(job_id, body.text, jobs.parse_progress(f"{body.progress['done']}/{body.progress['total']}")
                  if body.progress else None)
        return {"ok": True}

    @app.post("/internal/jobs/{job_id}/log")
    def add_log(job_id: str, body: LogIn, request: Request):
        job_of(request, job_id)
        jobs.log(job_id, *[str(x) for x in body.lines])
        return {"ok": True}

    @app.post("/internal/jobs/{job_id}/done")
    def done(job_id: str, body: DoneIn, request: Request):
        """Recorded for the worker, which checks quality before the job is really done (R14)."""
        job_of(request, job_id)
        links = {k: v for k, v in {"film": body.film, "style": body.style}.items() if v}
        jobs.update(job_id, lambda j: (j.__setitem__("reported", {"done": True, **links}),
                                       j["log"].append(jobs._line("Agent reported done"))))
        return {"ok": True}

    @app.post("/internal/jobs/{job_id}/fail")
    def failed(job_id: str, body: FailIn, request: Request):
        job_of(request, job_id)
        jobs.update(job_id, lambda j: j.__setitem__("reported", {"done": False, "error": body.text[:500],
                                                                 "by": body.by if body.by in ("studio", "customer") else "studio"}))
        return {"ok": True}

    @app.post("/internal/reviews/request", status_code=201)
    def review_request(body: ReviewIn, request: Request):
        job, _ = job_of(request)
        with store.as_account(job["owner"]):        # style-2 reads the customer's set (proof/compare.json)
            r = reviews.create(job["id"], body.kind, body.set, body.summary, body.final_round)
        return {"id": r["id"]}

    @app.post("/internal/web/fetch")
    async def web_fetch(body: FetchIn, request: Request):
        """Opens a page for a job container, which has no internet of its own (specs/010 R4). Logs the host only."""
        job, _ = job_of(request)
        seen = {}

        def count(j):
            seen["n"] = int(j.get("web_fetches") or 0)
            if seen["n"] < FETCH_LIMIT:
                j["web_fetches"] = seen["n"] + 1
        jobs.update(job["id"], count)
        if seen["n"] >= FETCH_LIMIT:
            raise Denied(429, "fetch_limit", f"a job may open at most {FETCH_LIMIT} pages")
        from urllib.parse import urlsplit
        host = urlsplit(body.url).hostname or "?"
        try:
            r = await asyncio.to_thread(webfetch.fetch, body.url)
        except webfetch.FetchError as e:
            log.info("job %s web fetch %s: %s", job["id"], host, e.code)
            return JSONResponse({"error": {"code": e.code, "message": e.message}}, status_code=e.http)
        log.info("job %s web fetch %s: %s", job["id"], host, r["status"])
        return r

    @app.post("/internal/youtube")
    async def youtube(body: YouTubeIn, request: Request):
        """YouTube numbers for a `topics` job (specs/013 R5): the key, the day's units and a 24-hour cache stay here."""
        job, _ = job_of(request)
        if job.get("kind") != "topics":
            raise Denied(403, "permission_error", "only a topics job may call YouTube")
        if body.endpoint not in yt_topics.ENDPOINTS:
            raise Denied(400, "invalid_request_error", "unknown YouTube endpoint")
        key = yt_topics.read_online_key(db.data_dir())
        if not key:
            return JSONResponse({"error": {"code": "youtube_not_ready", "message": "the studio has no YouTube key"}},
                                status_code=503)
        limit = quotas.settings().get("youtube_daily_units", 9000)

        def call():
            with YT_LOCK:
                f = yt_topics.Fetcher.local(key, yt_topics.online_usage(db.data_dir(), limit), yt_topics.online_cache(db.data_dir()))
                out = f.get(body.endpoint, body.params)
                return out, f.units
        try:
            out, units = await asyncio.to_thread(call)
        except yt_topics.QuotaError as e:
            log.info("job %s youtube %s: quota", job["id"], body.endpoint)
            return JSONResponse({"error": {"code": "youtube_quota", "message": str(e)}}, status_code=429)
        except yt_topics.TopicError as e:
            log.info("job %s youtube %s: error", job["id"], body.endpoint)
            return JSONResponse({"error": {"code": "youtube_error", "message": yt_topics.redact(str(e), key)}}, status_code=502)
        log.info("job %s youtube %s: %s units%s", job["id"], body.endpoint, units, " (cache)" if not units else "")
        return {**out, "_cached": units == 0, "_units": units}

    @app.get("/internal/reviews/{rid}")
    def review_status(rid: str, request: Request):
        job, _ = job_of(request)
        r = reviews.load(rid)
        if r["job_id"] != job["id"]:
            raise Denied(404, "not_found_error", "no such review")
        return r

    return app


def main():
    import uvicorn
    os.environ.setdefault("STUDIO_MODE", "online")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    uvicorn.run(create_app(), host=os.environ.get("PROXY_HOST", "0.0.0.0"), port=int(os.environ.get("PROXY_PORT", "8780")),
                log_level="warning", timeout_graceful_shutdown=10)   # a stalled stream must not hold a restart


if __name__ == "__main__":
    main()
