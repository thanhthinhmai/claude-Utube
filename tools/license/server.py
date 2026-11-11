"""The license server of the desktop app (specs/017 contracts/license-api.md): leases, the admin page, and the
private GitHub Release passed on to licensed apps. One process (the rate limits live in memory).

    LICENSE_DATA=/data LICENSE_SIGNING_KEY=… python server.py [--port 8899]
Optional: GITHUB_TOKEN (Contents: read), GITHUB_REPO (owner/name), LICENSE_SECURE_COOKIE=1 behind HTTPS."""
import argparse
import collections
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx  # noqa: E402
from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse  # noqa: E402

import store as st  # noqa: E402

HERE = Path(__file__).resolve().parent
MAX_BODY = 16 * 1024
MISSES, WINDOW_S = 10, 600
RELEASE_CACHE_S = 120
ASSET_RE = re.compile(r"^(release\.json(\.sig)?|claude-Utube-Setup-[\w.-]+\.exe|claude-Utube-[\w.-]+-arm64\.dmg)$")
COOKIE = "cu_admin"


class Limiter:
    """At most MISSES failures per address in WINDOW_S seconds."""

    def __init__(self):
        self.hits = collections.defaultdict(collections.deque)

    def blocked(self, ip: str) -> bool:
        q = self.hits[ip]
        while q and q[0] < st.now() - WINDOW_S:
            q.popleft()
        return len(q) >= MISSES

    def miss(self, ip: str):
        self.hits[ip].append(st.now())


def client_ip(request: Request) -> str:
    # Caddy sets X-Real-IP from the connection itself, so a caller cannot choose it (research R7)
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "")


def err(code: str, message: str, status: int):
    return JSONResponse({"code": code, "error": message}, status_code=status, headers={"Cache-Control": "no-store"})


def ok(body: dict, status: int = 200):
    return JSONResponse(body, status_code=status, headers={"Cache-Control": "no-store"})


def create_app(store: "st.Store" = None) -> FastAPI:
    store = store or st.Store.open()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    keys, passwords = Limiter(), Limiter()
    cache = {"at": 0.0, "release": None}
    gh_api = os.environ.get("LICENSE_GITHUB_API", "https://api.github.com").rstrip("/")
    gh_repo, gh_token = os.environ.get("GITHUB_REPO", ""), os.environ.get("GITHUB_TOKEN", "")
    secure = os.environ.get("LICENSE_SECURE_COOKIE") == "1"

    @app.middleware("http")
    async def limits(request: Request, call_next):
        if int(request.headers.get("content-length") or 0) > MAX_BODY:
            return err("too_large", "request too large", 413)
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        return resp

    async def body_of(request: Request) -> dict:
        raw = await request.body()
        if len(raw) > MAX_BODY:
            raise st.LicenseError("too_large", "request too large", 413)
        try:
            import json
            b = json.loads(raw or b"{}")
        except ValueError:
            raise st.LicenseError("invalid", "body must be JSON", 422)
        if not isinstance(b, dict):
            raise st.LicenseError("invalid", "body must be a JSON object", 422)
        return b

    @app.exception_handler(st.LicenseError)
    async def license_error(_request, e: st.LicenseError):
        return err(e.code, e.message, e.status)

    @app.get("/health")
    def health():
        return ok({"ok": True})

    # ---------- leases ----------
    @app.post("/api/license/lease")
    async def lease(request: Request):
        ip = client_ip(request)
        if keys.blocked(ip):
            return err("rate_limited", "Too many wrong keys. Try again in a few minutes.", 429)
        b = await body_of(request)
        try:
            return ok(store.lease_for(b.get("key"), b.get("deviceId"), b.get("deviceName") or "", b.get("os") or "",
                                      b.get("version") or "", ip))
        except st.LicenseError as e:
            if e.code == "unknown":
                keys.miss(ip)
            raise

    # ---------- releases (R5) ----------
    async def latest_release():
        if cache["release"] and st.now() - cache["at"] < RELEASE_CACHE_S:
            return cache["release"]
        if not gh_repo:
            return None
        headers = {"Accept": "application/vnd.github+json", **({"Authorization": f"Bearer {gh_token}"} if gh_token else {})}
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"{gh_api}/repos/{gh_repo}/releases", params={"per_page": 20}, headers=headers)
        if r.status_code != 200:
            return cache["release"]
        for rel in r.json():
            tag = rel.get("tag_name", "")
            if rel.get("draft") or not tag.startswith("desktop-v"):
                continue
            assets = [{"name": a["name"], "size": a["size"], "url": a["url"]} for a in rel.get("assets", []) if ASSET_RE.match(a["name"])]
            cache.update(at=st.now(), release={"tag": tag, "version": tag[len("desktop-v"):], "assets": assets})
            return cache["release"]
        return None

    def licensed(request: Request) -> bool:
        return store.in_good_standing(request.headers.get("x-cu-lease"))

    @app.get("/api/license/releases")
    async def releases(request: Request):
        if not licensed(request):
            return err("not_licensed", "a good license is needed", 403)
        rel = await latest_release()
        if not rel:
            return err("no_release", "no release yet", 404)
        return ok({"tag": rel["tag"], "version": rel["version"], "assets": [{"name": a["name"], "size": a["size"]} for a in rel["assets"]]})

    @app.get("/api/license/releases/{name}")
    async def release_file(name: str, request: Request):
        if not licensed(request):
            return err("not_licensed", "a good license is needed", 403)
        rel = await latest_release()
        asset = next((a for a in (rel or {}).get("assets", []) if a["name"] == name), None) if ASSET_RE.match(name) else None
        if not asset:
            return err("not_found", "no such file", 404)
        headers = {"Accept": "application/octet-stream", **({"Authorization": f"Bearer {gh_token}"} if gh_token else {})}
        client = httpx.AsyncClient(timeout=httpx.Timeout(1800, connect=30), follow_redirects=True)
        req = client.build_request("GET", asset["url"], headers=headers)
        up = await client.send(req, stream=True)
        if up.status_code != 200:
            await up.aclose()
            await client.aclose()
            return err("upstream", f"GitHub answered {up.status_code}", 502)

        async def pump():
            try:
                async for chunk in up.aiter_bytes(1 << 20):
                    yield chunk
            finally:
                await up.aclose()
                await client.aclose()
        return StreamingResponse(pump(), media_type="application/octet-stream",
                                 headers={"Content-Length": str(asset["size"]), "Cache-Control": "no-store"})

    # ---------- admin (R7) ----------
    @app.get("/admin")
    def admin_page():
        return FileResponse(HERE / "admin.html", headers={"Cache-Control": "no-store", "X-Frame-Options": "DENY",
                            "Content-Security-Policy": "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; frame-ancestors 'none'"})

    @app.post("/admin/api/login")
    async def login(request: Request):
        ip = client_ip(request)
        if passwords.blocked(ip):
            return err("rate_limited", "Too many wrong passwords. Try again in a few minutes.", 429)
        if request.headers.get("x-cu-admin") != "1":
            return err("csrf", "missing X-CU-Admin header", 403)
        b = await body_of(request)
        if not store.has_password():
            return err("no_password", "Set the admin password on the server first: python cli.py admin-password", 409)
        token = store.login(str(b.get("password") or ""))
        if not token:
            passwords.miss(ip)
            return err("wrong_password", "Wrong password.", 401)
        resp = ok({"ok": True})
        resp.set_cookie(COOKIE, token, max_age=st.SESSION_S, httponly=True, secure=secure, samesite="strict", path="/admin")
        return resp

    def admin_guard(request: Request, write: bool):
        if not store.session_ok(request.cookies.get(COOKIE)):
            raise st.LicenseError("signed_out", "sign in first", 401)
        if write and request.headers.get("x-cu-admin") != "1":
            raise st.LicenseError("csrf", "missing X-CU-Admin header", 403)

    @app.post("/admin/api/logout")
    def logout(request: Request):
        store.logout(request.cookies.get(COOKIE))
        resp = ok({"ok": True})
        resp.delete_cookie(COOKIE, path="/admin")
        return resp

    @app.get("/admin/api/licenses")
    def licenses(request: Request):
        admin_guard(request, write=False)
        return ok({"licenses": store.list_licenses(), "now": int(st.now())})

    @app.post("/admin/api/licenses")
    async def create(request: Request):
        admin_guard(request, write=True)
        key = store.create_license(await body_of(request))
        return ok({"key": key, "licenses": store.list_licenses()}, 201)

    @app.patch("/admin/api/licenses/{lid}")
    async def update(lid: str, request: Request):
        admin_guard(request, write=True)
        store.update_license(lid, await body_of(request))
        return ok({"licenses": store.list_licenses()})

    @app.delete("/admin/api/licenses/{lid}")
    def delete(lid: str, request: Request):
        admin_guard(request, write=True)
        store.delete_license(lid)
        return ok({"licenses": store.list_licenses()})

    @app.delete("/admin/api/licenses/{lid}/devices/{device_id}")
    def remove_device(lid: str, device_id: str, request: Request):
        admin_guard(request, write=True)
        store.remove_device(lid, device_id)
        return ok({"licenses": store.list_licenses()})

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def not_found(path: str):
        return Response(status_code=404)

    return app


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="claude-Utube license server")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8899)
    a = ap.parse_args(argv)
    import uvicorn
    s = st.Store.open()
    if not s.signing_key:
        print("! LICENSE_SIGNING_KEY is not set: leases are refused", file=sys.stderr)
    s.backup_daily()
    uvicorn.run(create_app(s), host=a.host, port=a.port, log_level="warning", server_header=False, proxy_headers=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
