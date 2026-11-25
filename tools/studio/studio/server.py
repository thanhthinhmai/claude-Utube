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

from . import APP_ID, VERSION, actions, aebridge, donesofar, filmsteps, gate, jobs, resources, reviews, store
from .resources import shotnotes
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
    base: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{16}$")      # review points: the content shown (026)


class ActionIn(BaseModel):                     # specs/026 contracts/api.md
    point: Literal["script", "cast", "voice", "shots", "mix", "publish"]
    op: str = Field(max_length=30)
    args: dict = Field(default_factory=dict)
    base: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{16}$")


class NotesIn(BaseModel):                      # specs/029 contracts/api.md
    base: str = Field(pattern=r"^[0-9a-f]{64}$")
    doc: dict


WRITE_ROLES = {"customer", "admin"}            # a token limited to reading (any other role) may not change notes


class PointsIn(BaseModel):
    on: list[Literal["script", "cast", "voice", "shots", "mix", "publish"]] = Field(max_length=6)


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
        if request.url.path.startswith("/api/v1/ae/bridge/"):           # the desktop app's AE bridge (specs/032 R2)
            client = request.client.host if request.client else ""
            if not aebridge.allowed(client, request.headers.get("x-cu-bridge")):
                return err("forbidden", "the AE bridge needs the desktop app's key", 403)
            resp = await call_next(request)
            resp.headers["X-Content-Type-Options"] = "nosniff"
            return resp
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
            multipart = ctype.startswith("multipart/form-data") and request.url.path.endswith("/notes/images")
            if request.headers.get("x-studio") != "1" or not (ctype.startswith("application/json") or multipart):
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

    # ---------- the parts of a film already done (specs/025) ----------
    def _film_job(job_id: str, request: Request) -> dict:
        """The job as get_job allows it (online: its owner or the studio owner); only film jobs."""
        if online:
            a = request.state.account
            j = jobs.load(job_id, None if a["role"] == "admin" else a["id"])
        else:
            j = jobs.load(job_id)
        if j.get("kind") != "film":
            raise StudioError("not_found", "không phải việc làm phim", 404)
        return j

    @app.get(api + "/jobs/{job_id}/done")
    def job_done(job_id: str, request: Request):
        return donesofar.summary(_film_job(job_id, request))

    @app.get(api + "/jobs/{job_id}/files/{path:path}")
    def job_file(job_id: str, path: str, request: Request):
        p = donesofar.file(_film_job(job_id, request), path)
        return FileResponse(p, media_type=donesofar.content_type(path), headers={"Cache-Control": "no-cache"})

    # ---------- review points and edits (specs/026) ----------
    @app.get(api + "/jobs/{job_id}/steps")
    def job_steps(job_id: str, request: Request):
        v = filmsteps.view(_film_job(job_id, request))
        tag = filmsteps.etag(v)
        if request.headers.get("if-none-match") == tag:
            from fastapi.responses import Response
            return Response(status_code=304, headers={"ETag": tag})
        return JSONResponse(v, headers={"ETag": tag, "Cache-Control": "no-cache"})

    @app.post(api + "/jobs/{job_id}/actions", status_code=202)
    def job_action(job_id: str, body: ActionIn, request: Request):
        j = _film_job(job_id, request)
        a = actions.create(j, body.point, body.op, body.args, body.base, owner(request) or "local")
        return {"id": a["id"], "status": a["status"]}

    @app.get(api + "/jobs/{job_id}/actions/{aid}")
    def job_action_get(job_id: str, aid: str, request: Request):
        _film_job(job_id, request)
        return actions.load(aid, job_id)

    @app.put(api + "/jobs/{job_id}/points")
    def job_points(job_id: str, body: PointsIn, request: Request):
        from filmcheck import points
        j = _film_job(job_id, request)
        d = donesofar.film_dir(j)
        if d is None:
            raise StudioError("not_found", "this job has no film folder yet", 404)
        rv = filmsteps.pending_review(j)
        try:
            on = points.set_on(d, body.on, origin="this film", pending={rv["kind"]} if rv and not rv["decision"] else set())
        except points.PointError as e:
            raise StudioError("point_locked", str(e), 409) from None
        jobs.log(job_id, f"Review points: {', '.join(on) or 'none'}")
        return {"on": on}

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
        r = reviews.load(rid, owner(request))         # another customer's review is not found
        via_token = getattr(request.state, "token", None) is not None      # specs/009: an API token or MCP
        if r["kind"] in reviews.POINT_KINDS and body.value == "approve" and not body.base and not via_token:
            raise StudioError("invalid", "approving a review point needs base (the fingerprint shown)", 422)
        return reviews.decide(rid, body.value, body.note, "api" if via_token else "ui", body.base, owner(request) or "local")

    # ---------- films ----------
    # ---------- After Effects bridge: the desktop app pulls build requests (specs/032 contracts/bridge-api.md) ----------
    from ae import aequeue

    def q(fn, *a):
        try:
            return fn(*a)
        except aequeue.QueueError as e:
            raise StudioError(e.code, e.message, e.status) from None

    @app.get(api + "/ae/bridge/next")
    def ae_next():
        r = q(aequeue.next_request)
        return r if r else Response(status_code=204)

    @app.post(api + "/ae/bridge/hello")
    async def ae_hello(request: Request):
        try:
            body = await request.json()
        except ValueError:
            body = {}
        aequeue.hello(body if isinstance(body, dict) else {})
        return {"ok": True}

    @app.get(api + "/ae/bridge/{rid}/bundle")
    def ae_bundle(rid: str):
        return FileResponse(q(aequeue.bundle_path, rid), media_type="application/x-tar", filename="bundle.tar")

    @app.post(api + "/ae/bridge/{rid}/progress")
    async def ae_progress(rid: str, request: Request):
        try:
            body = await request.json()
        except ValueError:
            body = {}
        return q(aequeue.progress, rid, body if isinstance(body, dict) else {})

    @app.put(api + "/ae/bridge/{rid}/result/{name}", status_code=201)
    async def ae_result(rid: str, name: str, request: Request):
        part = q(aequeue.result_part, rid, name)
        n = 0
        with open(part, "wb") as f:
            async for c in request.stream():
                n += len(c)
                if n > aequeue.MAX_RESULT:
                    break
                f.write(c)
        if n > aequeue.MAX_RESULT:
            part.unlink(missing_ok=True)
            raise StudioError("too_big", "a result may be at most 500 MB", 413)
        return {"bytes": q(aequeue.commit_result, rid, name)}

    @app.post(api + "/ae/bridge/{rid}/finish")
    async def ae_finish(rid: str, request: Request):
        try:
            body = await request.json()
        except ValueError:
            raise StudioError("invalid", "finish needs a JSON body", 422) from None
        return q(aequeue.finish, rid, body if isinstance(body, dict) else {})

    @app.get(api + "/films")
    def list_films():
        return {"films": resources.films()}

    @app.get(api + "/films/{name}")
    def get_film(name: str):
        return resources.film(name)

    @app.get(api + "/films/{name}/video")
    def film_video(name: str, prev: Optional[str] = None):
        if prev:                                    # the one previous video kept by `film replace` (specs/029)
            p = resources.film_path(name, "video_prev")
            if not p.is_file():
                raise StudioError("not_found", "phim chưa có bản trước", 404)
            return FileResponse(p, media_type="video/mp4")
        return FileResponse(resources.film_file(name, "video"), media_type="video/mp4")

    # ---------- shots and shot notes (specs/029 contracts/api.md) ----------
    @app.get(api + "/films/{name}/shots")
    def film_shots(name: str, prev: Optional[str] = None):
        resources.film_path(name, "shots")                 # bad name 400, no film 404
        d = resources.film_dir(name)
        r = resources.shot_call(shotnotes.load_shots, d, bool(prev))
        video = resources.film_path(name, "video_prev" if prev else "video")
        r["video_stamp"] = shotnotes.video_stamp(video) if video.is_file() else None
        r["thumbs"] = None
        if r["valid"] and not prev and video.is_file():
            r["thumbs"], r["video_stamp"] = shotnotes.thumbs_state(d, r["shots"])
        return r

    @app.get(api + "/films/{name}/shots/thumbs/{n}/{which}.jpg")
    def film_shot_thumb(name: str, n: str, which: str):
        resources.film_path(name, "thumbs")
        f, state = resources.shot_call(shotnotes.thumb, resources.film_dir(name), n, which)
        if f is None and state == "building":
            return JSONResponse({"status": "building"}, status_code=202, headers={"Cache-Control": "no-store"})
        if f is None:
            raise StudioError("not_found", "không cắt được ảnh này", 404)
        return FileResponse(f, media_type="image/jpeg", headers={"Cache-Control": "max-age=86400"})

    @app.get(api + "/films/{name}/poster")
    def film_poster(name: str):
        return FileResponse(resources.film_file(name, "poster"), media_type="image/jpeg")

    @app.get(api + "/films/{name}/subtitles.vtt")
    def film_subtitles(name: str):
        srt = resources.film_file(name, "srt").read_text(encoding="utf-8", errors="replace")
        return Response(resources.srt_to_vtt(srt), media_type="text/vtt; charset=utf-8")

    def _note_writer(request: Request) -> str:
        """Who writes (online: the account's email, else "local"); 403 for a read-only token (FR-016)."""
        a = getattr(request.state, "account", None)
        if a is None:
            return "local"
        if a["role"] not in WRITE_ROLES:
            raise StudioError("forbidden", "mã này chỉ được đọc, không sửa được ghi chú", 403)
        return a["email"]

    @app.post(api + "/films/{name}/fix", status_code=201)
    def film_fix(name: str, request: Request):
        """"Fix with Claude" (specs/032 FR-010, FR-011): a fix job on the film's open notes (≤ 10, film order)."""
        _note_writer(request)
        d = resources.film_dir(name)
        if not d.is_dir():
            raise StudioError("not_found", f"không có phim \"{name}\"", 404)
        from ae import aequeue, film as aefilm
        if aefilm.engine(d) != "ae":
            raise StudioError("not_ae", "only After Effects films can be fixed with Claude from their notes", 422)
        if not online:
            raise StudioError("app_only", "Fix with Claude runs in the app (sh bin/studio app start)", 409)
        st = aequeue.bridge_status()
        if not st["ready"]:
            raise StudioError(st["code"], st["message"], 409)
        a = request.state.account
        j = jobs.build("fix", f"Fix notes of {name}"[:80], {"film": name}, owner=a["id"], status="queued",
                       extra={"charged": False})
        lot = resources.shot_call(shotnotes.start_lot, d, j["id"], shotnotes.LOT_LIMIT, jobs.is_live)
        j["input"] = {"kind": "fix", "film": name, "notes": lot["lot"]["notes"], "left": lot["left"]}
        try:
            store.doc_put("job", j["id"], j)
        except Exception:
            shotnotes.end_lot(d, j["id"])
            raise
        return {"job": j["id"], "notes": lot["lot"]["notes"], "left": lot["left"]}

    @app.get(api + "/films/{name}/notes")
    def film_notes(name: str):
        resources.film_path(name, "notes")
        return resources.shot_call(shotnotes.read_notes, resources.film_dir(name))

    @app.put(api + "/films/{name}/notes")
    def film_notes_put(name: str, body: NotesIn, request: Request):
        resources.film_path(name, "notes")
        by = _note_writer(request)
        return resources.shot_call(shotnotes.save_notes, resources.film_dir(name), body.base, body.doc, by, store.clock())

    @app.post(api + "/films/{name}/notes/images", status_code=201)
    async def film_note_image(name: str, request: Request):
        resources.film_path(name, "images")
        _note_writer(request)
        try:                                       # refuse a body far over the limit before reading it
            too_big = int(request.headers.get("content-length") or 0) > shotnotes.MAX_IMAGE_BYTES + 64 * 1024
        except ValueError:
            too_big = False
        if too_big:
            raise StudioError("too_large", f"ảnh tối đa {shotnotes.MAX_IMAGE_BYTES // (1024 * 1024)} MB", 413)
        form = await request.form(max_files=1, max_fields=4)
        f = form.get("file")
        if f is None or isinstance(f, str):
            raise StudioError("invalid", "cần trường file (multipart/form-data)", 422)
        data = await f.read(shotnotes.MAX_IMAGE_BYTES + 1)
        await f.close()
        name_ = resources.shot_call(shotnotes.save_image, resources.film_dir(name), data, store.clock())
        return {"file": name_}

    @app.get(api + "/films/{name}/notes/images/{file}")
    def film_note_image_get(name: str, file: str):
        resources.film_path(name, "images")
        p = resources.shot_call(shotnotes.image_path, resources.film_dir(name), file)
        if not p.is_file():
            raise StudioError("not_found", "không có ảnh này", 404)
        types = {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp"}
        return FileResponse(p, media_type=types[p.suffix], headers={"Cache-Control": "max-age=86400"})

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
    def film_stamps(owner: str = None) -> dict:
        """specs/029: one stamp per film (video, shot marks, notes book) so an open film page follows changes made
        elsewhere (Claude replacing the video or answering notes from the command line)."""
        base = (store.account_dir(owner) if owner else store.root()) / "films"
        out = {}
        try:
            dirs = [d for d in base.iterdir() if d.is_dir() and resources.NAME.match(d.name)]
        except OSError:
            return out
        for d in dirs:
            parts = []
            for f in (d / f"{d.name}.mp4", d / "shots.json", d / "shot-notes.json"):
                try:
                    st = f.stat()
                    parts.append(f"{st.st_size}-{st.st_mtime_ns}")
                except OSError:
                    parts.append("-")
            out["film:" + d.name] = "|".join(parts)
        return out

    def snapshot(owner: str = None) -> dict:
        return {**store.doc_versions(owner), **film_stamps(owner)}

    def changes(old: dict, new: dict):
        for name, t in new.items():
            if old.get(name) == t:
                continue
            if name.startswith("film:"):
                if name in old:
                    yield "film.updated", name[5:]
            elif name.startswith("j-"):
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

    from . import castapi                                   # the channel's cast library (specs/034 US3)
    app.include_router(castapi.router)

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
