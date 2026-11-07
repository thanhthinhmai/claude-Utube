"""Online-only API: accounts (specs/007 contracts/api-online.md). Phase 3+ adds jobs, uploads, admin."""
import os
from typing import Optional

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from . import accounts, quotas
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
    return {**accounts.public(a), "quota": quotas.summary(a)}


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
