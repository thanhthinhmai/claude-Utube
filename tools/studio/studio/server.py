"""Local web server: API v1, live events, files by id, the web UI (contracts/api-v1.md)."""
import asyncio
import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import APP_ID, VERSION, gate, jobs, resources, reviews, store
from urllib.parse import urlsplit
from .store import StudioError

WEB = Path(__file__).resolve().parent / "web"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]"}
LOCAL_CLIENTS = {"127.0.0.1", "::1", "testclient"}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def err(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


class DecisionIn(BaseModel):
    value: Literal["approve", "revise", "accept_anyway", "stop"]
    note: Optional[str] = Field(default=None, max_length=4000)


class FreshStaticFiles(StaticFiles):
    """UI files: the browser must re-check them on every load (answered with a cheap 304 when unchanged),
    so a `git pull` never leaves an old app.js running against a new page."""

    async def get_response(self, path, scope):
        resp = await super().get_response(path, scope)
        resp.headers["Cache-Control"] = "no-cache"
        return resp


# Online mode (specs/007): paths open without logging in
MCP_RATE_FACTOR = 5      # protocol messages per tool call (handshake, notice, call), with room to spare
PUBLIC_API = ("/api/v1/health", "/api/v1/auth/", "/api/v1/uploads/t/", "/api/v1/films/t/")   # tickets: the link is the key


def owner(request: Request):
    """Whose data this request may see: None in local mode (everything), else the logged-in account id."""
    a = getattr(request.state, "account", None)
    return a["id"] if a else None


def create_app() -> FastAPI:
    online = store.mode() == "online"
    app = FastAPI(title="claude-Utube studio API", version=VERSION,
                  openapi_url="/api/v1/openapi.json", docs_url="/api/v1/docs", redoc_url=None)

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if gate.path() and request.url.path != "/api/v1/health":          # the desktop app's license (specs/017 R4)
            is_open, why = gate.check()
            if not is_open:
                if request.url.path.startswith("/api/"):
                    return err("license_locked", f"claude-Utube is locked (license: {why})", 423)
                return HTMLResponse(gate.LOCKED_HTML, status_code=423)
        if online:
            return await online_guard(request, call_next)
        return await local_only(request, call_next)

    async def online_guard(request: Request, call_next):
        """Online: no loopback rule; CSRF by header and Origin; a session for every API path but the public ones;
        each customer only sees their own files (store.as_account).
        An API token (Authorization: Bearer fs_…, specs/009 research R1-R3) acts as its owner instead of a cookie:
        no CSRF check (a browser never sends it by itself), the role capped, some paths closed, a rate per minute,
        and one log row per request."""
        auth = request.headers.get("authorization") or ""
        bearer = auth[7:].strip() if auth[:7].lower() == "bearer " else None
        path = request.url.path
        if bearer is not None and path.startswith("/api/") and not path.startswith(PUBLIC_API):
            return await token_request(request, call_next, bearer)
        if path == "/api/mcp" or path.startswith("/api/mcp/"):
            return err("bad_token", "máy chủ MCP cần mã API (Authorization: Bearer)", 401)
        ticket = path.startswith("/api/v1/uploads/t/")         # the link is the key; no cookie is used (specs/009)
        if request.method not in SAFE_METHODS and not ticket:
            ctype = request.headers.get("content-type", "")
            empty = request.headers.get("content-length", "0") == "0" and "transfer-encoding" not in request.headers
            if request.headers.get("x-studio") != "1" or not (empty or ctype.startswith("application/json")
                                                              or ctype.startswith("multipart/form-data")):
                return err("csrf", "thiếu header X-Studio hoặc nội dung không hợp lệ", 403)
            origin = request.headers.get("origin")
            if origin and urlsplit(origin).netloc.lower() != (request.headers.get("host") or "").lower():
                return err("csrf", "nguồn gửi không khớp tên miền", 403)
        request.state.account = None
        request.state.token = None
        if path.startswith("/api/") and not path.startswith(PUBLIC_API):
            from . import accounts
            try:
                a = accounts.current(request.cookies.get(accounts.COOKIE))
            except StudioError as e:
                return err(e.code, e.message, e.status)
            if not a:
                return err("auth_required", "cần đăng nhập", 401)
            request.state.account = a
            with store.as_account(a["id"]):
                resp = await call_next(request)
        else:
            resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        return resp

    async def token_request(request: Request, call_next, secret: str):
        from . import ratelimit, tokens
        found = tokens.resolve(secret)
        if not found:
            return err("bad_token", "mã API không đúng, đã thu hồi hoặc đã hết hạn", 401)
        owner, token, role = found
        method, path = request.method, request.url.path
        ip = request.client.host if request.client else ""
        if tokens.is_forbidden(method, path):
            tokens.record(token, method, path, "token_forbidden", ip)
            return err("token_forbidden", "mã API không làm được việc này; hãy dùng trình duyệt", 403)
        # The MCP endpoint itself is only the protocol (handshake, then one POST per tool call); the work of a tool is
        # an in-process REST call, which counts against the rate and is logged like any other. So /api/mcp has its own,
        # wider budget and no log row: one tool call = one row (SC-207).
        mcp = path == "/api/mcp"
        try:
            ratelimit.hit("token-mcp" if mcp else "token", token["id"],
                          limit=token["rate_per_min"] * (MCP_RATE_FACTOR if mcp else 1), window=60)
        except StudioError as e:
            if not mcp:
                tokens.record(token, method, path, "rate_limit", ip)
            r = err(e.code, e.message, e.status)
            r.headers["Retry-After"] = str(getattr(e, "retry_after", 60))
            return r
        account = {**dict(owner), "role": role}            # never more than the owner's role now (FR-214)
        request.state.account, request.state.token, request.state.token_outcome = account, token, "allowed"
        with store.as_account(account["id"]):
            resp = await call_next(request)
        if not mcp:
            tokens.record(token, method, path, request.state.token_outcome, ip)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        return resp

    async def local_only(request: Request, call_next):
        host = (request.headers.get("host") or "").lower()
        hostname = host.rsplit(":", 1)[0] if not host.startswith("[") else host.split("]")[0] + "]"
        if hostname not in LOCAL_HOSTS:                       # DNS rebinding
            return err("bad_host", "chỉ mở được qua localhost", 403)
        client = request.client.host if request.client else ""
        if client not in LOCAL_CLIENTS:
            return err("not_local", "chỉ truy cập được từ chính máy này", 403)
        if request.method not in SAFE_METHODS:                 # CSRF: needs a header a foreign page cannot send
            ctype = request.headers.get("content-type", "")
            if request.headers.get("x-studio") != "1" or not ctype.startswith("application/json"):
                return err("csrf", "thiếu header X-Studio hoặc nội dung không phải JSON", 403)
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        return resp

    @app.exception_handler(StudioError)
    async def studio_error(_, e: StudioError):
        r = err(e.code, e.message, e.status)
        if getattr(e, "extra", None):          # e.g. resets_at of quota_exceeded, reason of content_rejected
            import json
            body = json.loads(r.body)
            body["error"].update(e.extra)
            r = JSONResponse(body, status_code=e.status)
        if getattr(e, "retry_after", None):
            r.headers["Retry-After"] = str(e.retry_after)
        return r

    @app.exception_handler(RequestValidationError)
    async def invalid(_, e: RequestValidationError):
        return err("invalid", "dữ liệu gửi lên không hợp lệ", 422)

    api = "/api/v1"

    @app.get(api + "/health")
    def health():
        if online:          # never tell the internet where the files are
            return {"ok": True, "version": VERSION, "app": APP_ID, "mode": "online"}
        return {"ok": True, "version": VERSION, "app": APP_ID, "root": str(store.root()), "mode": "local"}

    # ---------- jobs ----------
    @app.get(api + "/jobs")
    def list_jobs(request: Request, status: Optional[str] = None, kind: Optional[str] = None):
        if online:
            from .api_online import queue_positions, view
            pos, a = queue_positions(), request.state.account
            out = [view(j, a, pos) for j in jobs.all_jobs(None if a["role"] == "admin" else a["id"])]
        else:
            out = [reviews.job_view(j) for j in jobs.all_jobs()]
        if status:
            out = [j for j in out if j["status"] == status]
        if kind:
            out = [j for j in out if j["kind"] == kind]
        return {"jobs": out}

    @app.get(api + "/jobs/{job_id}")
    def get_job(job_id: str, request: Request):
        if online:
            from .api_online import job_usage, view
            a = request.state.account
            j = view(jobs.load(job_id, None if a["role"] == "admin" else a["id"]), a)
            j["usage"] = job_usage(job_id)              # specs/008 US4: calls and tokens of this job
        else:
            j = reviews.job_view(jobs.load(job_id))
        j["reviews"] = [_review_out(reviews.load(r)) for r in j["review_ids"]]
        return j

    # ---------- reviews ----------
    def _review_out(r: dict) -> dict:
        r = dict(r)
        r["summary_html"] = resources.to_html(r.pop("summary_md", ""))
        return r

    @app.get(api + "/reviews")
    def list_reviews(request: Request, status: Optional[Literal["pending", "decided"]] = None):
        return {"reviews": [_review_out(r) for r in reviews.all_reviews(status, owner(request))]}

    @app.get(api + "/reviews/{rid}")
    def get_review(rid: str, request: Request):
        return _review_out(reviews.load(rid, owner(request)))

    @app.post(api + "/reviews/{rid}/decision", status_code=201)
    def post_decision(rid: str, body: DecisionIn, request: Request):
        reviews.load(rid, owner(request))             # another customer's review is not found
        return reviews.decide(rid, body.value, body.note, "ui")

    # ---------- films ----------
    @app.get(api + "/films")
    def list_films():
        return {"films": resources.films()}

    @app.get(api + "/films/{name}")
    def get_film(name: str):
        return resources.film(name)

    @app.get(api + "/films/{name}/video")
    def film_video(name: str):
        return FileResponse(resources.film_file(name, "video"), media_type="video/mp4")

    @app.get(api + "/films/{name}/poster")
    def film_poster(name: str):
        return FileResponse(resources.film_file(name, "poster"), media_type="image/jpeg")

    @app.get(api + "/films/{name}/subtitles.vtt")
    def film_subtitles(name: str):
        srt = resources.film_file(name, "srt").read_text(encoding="utf-8", errors="replace")
        return Response(resources.srt_to_vtt(srt), media_type="text/vtt; charset=utf-8")

    # ---------- publish pack (specs/011) ----------
    @app.get(api + "/films/{name}/publish")
    def film_publish(name: str):
        return resources.publish_view(name)

    @app.get(api + "/films/{name}/publish.zip")
    def film_publish_zip(name: str):
        return Response(resources.publish_zip(name), media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="{name}-publish.zip"'})

    @app.get(api + "/films/{name}/publish/{file}")
    def film_publish_file(name: str, file: str):
        p = resources.publish_file(name, file)
        if p.suffix == ".srt":
            return FileResponse(p, media_type="application/x-subrip; charset=utf-8", filename=f"{name}.srt")
        types = {".png": "image/png", ".jpg": "image/jpeg", ".md": "text/markdown; charset=utf-8"}
        return FileResponse(p, media_type=types[p.suffix])

    # ---------- reference sets ----------
    @app.get(api + "/sets")
    def list_sets():
        return {"sets": resources.sets()}

    @app.get(api + "/sets/{name}")
    def get_set(name: str):
        return resources.set_detail(name)

    @app.get(api + "/sets/{name}/sheets")
    def list_sheets(name: str):
        resources.set_detail(name)
        return resources.sheets(name)

    @app.get(api + "/sets/{name}/sheets/{file}")
    def sheet(name: str, file: str):
        return FileResponse(resources.sheet_file(name, file), media_type="image/jpeg")

    @app.get(api + "/sets/{name}/proof/{file}")
    def proof(name: str, file: str):
        return FileResponse(resources.proof_file(name, file), media_type="image/jpeg")

    # ---------- saved styles ----------
    @app.get(api + "/styles")
    def list_styles():
        return {"styles": resources.styles()}

    @app.get(api + "/styles/{slug}")
    def get_style(slug: str):
        return resources.style(slug)

    @app.get(api + "/styles/{slug}/styleframe")
    def styleframe(slug: str):
        return FileResponse(resources.styleframe(slug), media_type="image/jpeg")

    # ---------- style library (004) ----------
    @app.get(api + "/library")
    def get_library():
        return resources.library()

    @app.get(api + "/library/styles/{slug}")
    def get_library_style(slug: str):
        return resources.library_style(slug)

    @app.get(api + "/library/styles/{slug}/poster")
    def library_poster(slug: str):
        return FileResponse(resources.library_poster(slug), media_type="image/jpeg",
                            headers={"Cache-Control": "max-age=86400"})

    # ---------- live events ----------
    def snapshot(owner: str = None) -> dict:
        return store.doc_versions(owner)

    def changes(old: dict, new: dict):
        for name, t in new.items():
            if old.get(name) == t:
                continue
            if name.startswith("j-"):
                yield "job.updated", name[:-5]
            elif name.endswith(".decision.json"):
                yield "review.decided", name[: -len(".decision.json")]
            elif name not in old:
                yield "review.created", name[:-5]

    @app.get(api + "/events")
    async def events(request: Request, interval: float = Query(1.0, ge=0.05, le=5)):
        who = owner(request)

        async def gen():
            old, idle = snapshot(who), 0.0
            yield ": connected\n\n"
            while not await request.is_disconnected():
                await asyncio.sleep(interval)
                new = snapshot(who)
                for ev, ident in changes(old, new):
                    yield f"event: {ev}\ndata: {{\"id\": \"{ident}\"}}\n\n"
                    idle = 0.0
                old = new
                idle += interval
                if idle >= 15:
                    yield ": ping\n\n"
                    idle = 0.0
                if os.environ.get("STUDIO_EVENTS_ONCE"):        # tests: stop after one round
                    break
        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    if online:
        from . import api_online, db
        (db.data_dir() / "tmp").mkdir(exist_ok=True)        # TMPDIR of the web container (uploads)
        app.include_router(api_online.router)

        @app.get("/terms")
        def terms():
            """Terms of use and content policy (deploy/terms.md, edited by the studio owner)."""
            from fastapi.responses import HTMLResponse
            f = Path(os.environ.get("STUDIO_TERMS") or Path(__file__).resolve().parents[3] / "deploy" / "terms.md")
            text = f.read_text(encoding="utf-8") if f.is_file() else "# Terms of use\n\nNot written yet."
            return HTMLResponse('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                                '<meta name="viewport" content="width=device-width, initial-scale=1"><title>Terms · Film Studio</title>'
                                '<link rel="stylesheet" href="/style.css"></head><body><main class="md" style="max-width:760px">'
                                + resources.to_html(text) + '<p><a href="/#/signup">Back to sign-up</a></p></main></body></html>')
        def openapi_for_tokens():
            """OpenAPI without the paths no API token may use (specs/009 research R7, FR-213)."""
            if app.openapi_schema:
                return app.openapi_schema
            from fastapi.openapi.utils import get_openapi
            from . import tokens
            spec = get_openapi(title=app.title, version=app.version, routes=app.routes,
                               description="Film Studio API. Send `Authorization: Bearer <token>` (make a token on your "
                                           "account page). MCP server: /api/mcp.")
            for path in list(spec.get("paths", {})):
                for method in list(spec["paths"][path]):
                    if tokens.is_forbidden(method, path):
                        del spec["paths"][path][method]
                if not spec["paths"][path]:
                    del spec["paths"][path]
            app.openapi_schema = spec
            return spec
        app.openapi = openapi_for_tokens
        from starlette.routing import Route
        from . import mcp_server
        app.router.routes.append(Route("/api/mcp", mcp_server.Endpoint(app), include_in_schema=False))
    app.mount("/", FreshStaticFiles(directory=WEB, html=True), name="web")
    return app


app = create_app()
