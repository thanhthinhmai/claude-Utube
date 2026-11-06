"""Local web server: API v1, live events, files by id, the web UI (contracts/api-v1.md)."""
import asyncio
import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import APP_ID, VERSION, jobs, resources, reviews, store
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


def create_app() -> FastAPI:
    app = FastAPI(title="claude-Utube studio API", version=VERSION,
                  openapi_url="/api/v1/openapi.json", docs_url="/api/v1/docs", redoc_url=None)

    @app.middleware("http")
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
        return err(e.code, e.message, e.status)

    @app.exception_handler(RequestValidationError)
    async def invalid(_, e: RequestValidationError):
        return err("invalid", "dữ liệu gửi lên không hợp lệ", 422)

    api = "/api/v1"

    @app.get(api + "/health")
    def health():
        return {"ok": True, "version": VERSION, "app": APP_ID, "root": str(store.root())}

    # ---------- jobs ----------
    @app.get(api + "/jobs")
    def list_jobs(status: Optional[str] = None, kind: Optional[str] = None):
        out = [reviews.job_view(j) for j in jobs.all_jobs()]
        if status:
            out = [j for j in out if j["status"] == status]
        if kind:
            out = [j for j in out if j["kind"] == kind]
        return {"jobs": out}

    @app.get(api + "/jobs/{job_id}")
    def get_job(job_id: str):
        j = reviews.job_view(jobs.load(job_id))
        j["reviews"] = [_review_out(reviews.load(r)) for r in j["review_ids"]]
        return j

    # ---------- reviews ----------
    def _review_out(r: dict) -> dict:
        r = dict(r)
        r["summary_html"] = resources.to_html(r.pop("summary_md", ""))
        return r

    @app.get(api + "/reviews")
    def list_reviews(status: Optional[Literal["pending", "decided"]] = None):
        return {"reviews": [_review_out(r) for r in reviews.all_reviews(status)]}

    @app.get(api + "/reviews/{rid}")
    def get_review(rid: str):
        return _review_out(reviews.load(rid))

    @app.post(api + "/reviews/{rid}/decision", status_code=201)
    def post_decision(rid: str, body: DecisionIn):
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
    def snapshot() -> dict:
        snap = {}
        for sub in ("jobs", "reviews"):
            for p in (store.state_dir() / sub).glob("[jr]-*.json"):
                try:
                    snap[p.name] = p.stat().st_mtime_ns
                except FileNotFoundError:
                    pass
        return snap

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
        async def gen():
            old, idle = snapshot(), 0.0
            yield ": connected\n\n"
            while not await request.is_disconnected():
                await asyncio.sleep(interval)
                new = snapshot()
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

    app.mount("/", FreshStaticFiles(directory=WEB, html=True), name="web")
    return app


app = create_app()
