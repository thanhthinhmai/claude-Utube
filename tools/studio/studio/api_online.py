"""Online-only API: accounts and film jobs (specs/007 contracts/api-online.md). Later phases add uploads, admin."""
import os
import re
import secrets
import shutil
from typing import Literal, Optional

from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import accounts, jobs, moderation, quotas, ratelimit, resources, reviews
from .store import StudioError

router = APIRouter(prefix="/api/v1")


class SignupIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)
    accept_terms: bool = False


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)


class TokenIn(BaseModel):
    token: str = Field(max_length=200)


class ResetIn(TokenIn):
    password: str = Field(max_length=200)


class ForgotIn(BaseModel):
    email: str = Field(max_length=254)


class MeIn(BaseModel):
    email_notify: Optional[bool] = None
    password: Optional[str] = Field(default=None, max_length=200)
    old_password: Optional[str] = Field(default=None, max_length=200)


class DeleteIn(BaseModel):
    password: str = Field(max_length=200)


def client_ip(request: Request) -> str:
    """The caller; behind Caddy the real address is in X-Forwarded-For (only trusted when STUDIO_PROXIED=1)."""
    if os.environ.get("STUDIO_PROXIED") == "1":
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""


def me(request: Request):
    a = getattr(request.state, "account", None)
    if not a:
        raise StudioError("auth_required", "cần đăng nhập", 401)
    return a


def _set_cookie(request: Request, response: Response, token: str) -> None:
    secure = request.url.scheme == "https" or os.environ.get("STUDIO_SECURE_COOKIE") == "1"
    response.set_cookie(accounts.COOKIE, token, max_age=accounts.SESSION_DAYS * 86400, httponly=True,
                        secure=secure, samesite="lax", path="/")


@router.post("/auth/signup", status_code=201)
def signup(body: SignupIn, request: Request):
    a = accounts.signup(body.email, body.password, body.accept_terms, ip=client_ip(request))
    return {"email": a["email"], "verified": False}


@router.post("/auth/verify")
def verify(body: TokenIn):
    accounts.verify(body.token)
    return {"verified": True}


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response):
    token = accounts.login(body.email, body.password, ip=client_ip(request))
    _set_cookie(request, response, token)
    return {"ok": True}


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response):
    accounts.logout(request.cookies.get(accounts.COOKIE))
    response.delete_cookie(accounts.COOKIE, path="/")
    response.status_code = 204
    return response


@router.post("/auth/forgot", status_code=202)
def forgot(body: ForgotIn):
    accounts.forgot(body.email)
    return {"ok": True}


@router.post("/auth/reset")
def reset(body: ResetIn):
    accounts.reset(body.token, body.password)
    return {"ok": True}


@router.get("/me")
def get_me(request: Request):
    a = me(request)
    return {**accounts.public(a), "quota": quotas.summary(a),
            "limits": {"film_max_seconds": quotas.settings()["film_max_seconds"]}}


@router.put("/me")
def put_me(body: MeIn, request: Request):
    a = me(request)
    accounts.change(a["id"], body.email_notify, body.password, body.old_password)
    return {**accounts.public(accounts.get(a["id"])), "quota": quotas.summary(a)}


@router.delete("/me", status_code=202)
def delete_me(body: DeleteIn, request: Request, response: Response):
    a = me(request)
    accounts.delete(a["id"], body.password)
    response.delete_cookie(accounts.COOKIE, path="/")
    return {"ok": True}


# ---------- film jobs ----------
class JobIn(BaseModel):
    kind: Literal["film"]
    style: str = Field(max_length=60)
    idea: str = Field(min_length=3, max_length=2000)
    seconds: int = Field(ge=1, le=3600)
    review_treatment: bool = False


def film_name(idea: str) -> str:
    """A short folder name from the idea: lower-case words, then 4 random hex digits."""
    words = re.findall(r"[a-z0-9]+", idea.lower())
    base = "-".join(words)[:40].strip("-") or "film"
    return f"{base}-{secrets.token_hex(2)}"


def style_exists(slug: str) -> bool:
    if resources.in_library(slug):
        return True
    try:
        resources.style(slug)           # the customer's own styles (my-styles of this account)
        return True
    except StudioError:
        return False


@router.post("/jobs", status_code=201)
def post_job(body: JobIn, request: Request):
    a = me(request)
    if not a["email_verified_at"]:
        raise StudioError("unverified", "hãy xác minh email trước khi giao việc", 403)
    s = quotas.settings()
    if not resources.NAME.match(body.style or "") or not style_exists(body.style):
        raise StudioError("style_not_found", f"không có phong cách \"{body.style}\"", 404)
    if body.seconds > s["film_max_seconds"]:
        raise StudioError("too_long", f"phim dài tối đa {s['film_max_seconds']} giây", 422)
    ratelimit.hit("job_account", a["id"])
    ok, reason = moderation.check(body.idea)
    if not ok:
        e = StudioError("content_rejected", "ý tưởng này xưởng không làm được", 422)
        e.extra = {"reason": reason}
        raise e
    name = film_name(body.idea)
    j = quotas.reserve(a, "film", body.idea[:80], {"film": name, "style": body.style},
                       {"kind": "film", "style": body.style, "idea": body.idea, "seconds": body.seconds,
                        "review_treatment": body.review_treatment, "film": name})
    return view(j, a)


def queue_positions() -> dict:
    """{job id: place in the studio queue, 1 = next}."""
    from . import db
    with db.read() as con:
        rows = con.execute("SELECT id FROM docs WHERE kind = 'job' AND status = 'queued' "
                           "ORDER BY json_extract(data, '$.queue_seq'), id").fetchall()
    return {r[0]: i + 1 for i, r in enumerate(rows)}


def view(j: dict, account, positions: dict = None) -> dict:
    """A job as a customer sees it: queue place; the cost only for the admin."""
    v = reviews.job_view(j)
    if v["status"] == "waiting_resume":          # online the worker resumes it by itself, within seconds
        v["status"] = j["status"]
    if j["status"] == "queued":
        v["queue_position"] = (positions if positions is not None else queue_positions()).get(j["id"])
    else:
        v["queue_position"] = None
    if account["role"] != "admin":
        v.pop("cost_usd", None)
    return v


@router.post("/jobs/{job_id}/stop")
def stop_job(job_id: str, request: Request):
    a = me(request)
    jobs.load(job_id, None if a["role"] == "admin" else a["id"])
    return view(jobs.finish(job_id, "stopped", error="Stopped by the customer"), a)


@router.get("/films/{name}/download")
def download(name: str):
    return FileResponse(resources.film_file(name, "video"), media_type="video/mp4", filename=f"{name}.mp4")


@router.delete("/films/{name}", status_code=204)
def delete_film(name: str, request: Request):
    a = me(request)
    d = resources.film_dir(name)
    if not d.is_dir():
        raise StudioError("not_found", f"không có phim \"{name}\"", 404)
    for j in jobs.all_jobs(a["id"]):
        if j["status"] not in jobs.FINAL and j["links"].get("film") == name:
            raise StudioError("in_use", "phim đang được một việc dùng", 409)
    shutil.rmtree(d)
    return Response(status_code=204)
