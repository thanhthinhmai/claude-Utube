"""API proxy between job containers and Anthropic (specs/007 contracts/runner.md, research R3, R13).

- `POST /v1/messages` (and `/v1/messages/count_tokens`): checks the job's own token, swaps it for the real key
  (ANTHROPIC_API_KEY of this process), forwards to ANTHROPIC_UPSTREAM, streams the answer back, adds the cost.
- `/internal/…`: what `sh bin/studio job …` and `review …` call from inside a container.
Logs carry token counts and cost only, never prompt text.

Run: STUDIO_MODE=online STUDIO_DATA=/data python tools/runner/proxy.py   (listens on 0.0.0.0:8780)"""
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

from studio import db, jobs, quotas, reviews, store  # noqa: E402
from studio.store import StudioError  # noqa: E402

log = logging.getLogger("studio.proxy")
PASS_HEADERS = ("anthropic-version", "anthropic-beta", "content-type", "accept")
BACK_HEADERS = ("content-type", "retry-after", "request-id", "anthropic-ratelimit-requests-remaining",
                "anthropic-ratelimit-tokens-remaining", "x-should-retry")


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
            usage.update({k: v for k, v in (m.get("usage") or {}).items() if isinstance(v, (int, float))})
        elif ev.get("type") == "message_delta":
            usage.update({k: v for k, v in (ev.get("usage") or {}).items() if isinstance(v, (int, float))})
    return model, usage


def charge(job: dict, model: str, usage: dict) -> None:
    usd = quotas.cost_of(model or "", usage)
    total = quotas.add_cost(job["id"], usd)
    log.info("job %s model %s in %s out %s cache_w %s cache_r %s cost $%.4f total $%.4f", job["id"], model,
             usage.get("input_tokens"), usage.get("output_tokens"), usage.get("cache_creation_input_tokens"),
             usage.get("cache_read_input_tokens"), usd, total)
    if total >= quotas.settings()["job_cost_cap_usd"]:
        over_cap(job["id"])


def over_cap(job_id: str) -> None:
    quotas.fail(job_id, "The job used more than its cost limit and was stopped. Your credit was refunded.", "studio")
    revoke(job_id)


# ---------- app ----------
class StepIn(BaseModel):
    text: str = Field(max_length=120)
    progress: Optional[dict] = None


class LogIn(BaseModel):
    lines: list = Field(default_factory=list, max_length=60)


class DoneIn(BaseModel):
    film: Optional[str] = None
    style: Optional[str] = None


class FailIn(BaseModel):
    text: str = Field(max_length=2000)
    by: str = "studio"


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

    async def forward(request: Request, path: str, metered: bool):
        job, h = job_of(request)
        if metered and (job.get("cost_usd") or 0) >= quotas.settings()["job_cost_cap_usd"]:
            over_cap(job["id"])
            return _anthropic_error(429, "rate_limit_error", "job cost limit reached")
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            return _anthropic_error(500, "api_error", "the studio has no API key")
        headers = {k: v for k, v in request.headers.items() if k.lower() in PASS_HEADERS}
        headers["x-api-key"] = key
        body = await request.body()
        req = client.build_request("POST", upstream + path, content=body, headers=headers)
        r = await client.send(req, stream=True)
        back = {k: v for k, v in r.headers.items() if k.lower() in BACK_HEADERS}
        if r.status_code >= 400:              # 429, 529, 5xx… passed through so the SDK retries (R13)
            data = await r.aread()
            await r.aclose()
            log.info("job %s upstream %s", job["id"], r.status_code)
            return Response(data, status_code=r.status_code, headers=back)
        is_stream = r.headers.get("content-type", "").startswith("text/event-stream")
        if not is_stream:
            data = await r.aread()
            await r.aclose()
            _mark_ok(h)
            if metered:
                try:
                    msg = json.loads(data)
                    charge(job, msg.get("model"), msg.get("usage") or {})
                except (json.JSONDecodeError, AttributeError):
                    pass
            return Response(data, status_code=r.status_code, headers=back)

        async def relay():
            chunks = []
            try:
                async for chunk in r.aiter_raw():
                    chunks.append(chunk)
                    yield chunk
            finally:
                await r.aclose()
                _mark_ok(h)
                if metered:
                    model, usage = usage_of_stream(chunks)
                    charge(job, model, usage)
        return StreamingResponse(relay(), status_code=r.status_code, headers=back)

    @app.post("/v1/messages")
    async def messages(request: Request):
        return await forward(request, "/v1/messages", metered=True)

    @app.post("/v1/messages/count_tokens")
    async def count_tokens(request: Request):
        return await forward(request, "/v1/messages/count_tokens", metered=False)

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
                log_level="warning")


if __name__ == "__main__":
    main()
