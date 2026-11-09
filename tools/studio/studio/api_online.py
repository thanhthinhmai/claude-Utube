"""Online-only API: accounts, film and learn jobs, uploads (specs/007 contracts/api-online.md). Later phases add admin."""
import json
import os
import subprocess
import re
import secrets
import shutil
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import APIRouter, File, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import accounts, claude_plan, db, jobs, moderation, quotas, ratelimit, resources, reviews, store
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
    """No public sign-up (specs/008 FR-111): the owner adds people in Settings → Users."""
    raise StudioError("signup_closed", "chỉ chủ xưởng thêm được người dùng", 403)


class SetupIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)


@router.get("/auth/setup")
def get_setup():
    """First visit (FR-118): is there an owner yet?"""
    return {"needed": accounts.setup_needed()}


@router.post("/auth/setup", status_code=201)
def post_setup(body: SetupIn, request: Request, response: Response):
    a = accounts.setup(body.email, body.password, ip=client_ip(request))
    _set_cookie(request, response, accounts.login(body.email, body.password, ip=client_ip(request)))
    return {"email": a["email"], "role": "admin"}


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
            "limits": limits()}


def limits() -> dict:
    s = quotas.settings()
    return {"film_max_seconds": s["film_max_seconds"], "learn_max_videos": s["learn_max_videos"],
            "upload_max_mb": s["upload_max_mb"], "upload_max_minutes": s["upload_max_minutes"],
            "rights_text": RIGHTS_TEXT}


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
    kind: Literal["film", "learn"]
    # film
    style: Optional[str] = Field(default=None, max_length=60)
    idea: Optional[str] = Field(default=None, min_length=3, max_length=2000)
    seconds: Optional[int] = Field(default=None, ge=1, le=3600)
    review_treatment: bool = False
    revise_of: Optional[str] = Field(default=None, max_length=60)
    note: Optional[str] = Field(default=None, max_length=2000)
    # learn
    source: Optional[Literal["youtube", "upload"]] = None
    channel: Optional[str] = Field(default=None, max_length=300)
    count: Optional[int] = Field(default=None, ge=1, le=100)
    rights_confirmed: bool = False
    uploads: Optional[List[str]] = Field(default=None, max_length=20)


# what the customer ticks before a YouTube fetch (constitution 2.1.0, "Bản quyền và nội dung")
RIGHTS_TEXT = ("I confirm that I have the right to use the videos of this channel, or that I use them only to study "
               "their style. The studio keeps them private, never shows or shares them, and deletes them after learning.")
RIGHTS_VERSION = "2.1.0"
CHANNEL = re.compile(r"^https://(www\.|m\.)?youtube\.com/(@[\w.-]{1,100}|channel/[\w-]{10,40}|c/[\w.-]{1,100})/?$")
UPLOAD_ID = re.compile(r"^u-[0-9a-f]{16}$")
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}


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
    if body.kind == "learn":
        return post_learn(body, a)
    if body.revise_of:
        return post_revision(body, a)
    if not (body.style and body.idea and body.seconds):
        raise StudioError("invalid", "việc làm phim cần style, idea và seconds", 422)
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


def post_revision(body: JobIn, a) -> dict:
    """A new version of a finished film, from the customer's note (FR-015): 1 film credit; the old one stays."""
    old = body.revise_of
    if not resources.NAME.match(old) or not (resources.film_dir(old) / f"{old}.mp4").is_file():
        raise StudioError("not_found", f"không có phim \"{old}\"", 404)
    note = (body.note or "").strip()
    if len(note) < 3:
        raise StudioError("note_required", "hãy ghi điều muốn sửa (ít nhất 3 ký tự)", 422)
    first = next((j for j in jobs.all_jobs(a["id"]) if j["status"] == "done" and j["kind"] == "film"
                  and j["links"].get("film") == old), None)
    if not first or not (first.get("input") or {}).get("style"):
        raise StudioError("not_found", f"không tìm thấy việc đã làm ra phim \"{old}\"", 404)
    for j in jobs.all_jobs(a["id"]):
        if j["status"] not in jobs.FINAL and (j.get("input") or {}).get("revise_of") == old:
            raise StudioError("in_use", "phim này đang được sửa", 409)
    ratelimit.hit("job_account", a["id"])
    ok, reason = moderation.check(note)
    if not ok:
        e = StudioError("content_rejected", "góp ý này xưởng không làm được", 422)
        e.extra = {"reason": reason}
        raise e
    base = re.sub(r"-r\d+$", "", old)
    n = 1
    while (resources.film_dir(f"{base}-r{n}")).exists() or any(
            (j.get("input") or {}).get("film") == f"{base}-r{n}" for j in jobs.all_jobs(a["id"])):
        n += 1
    name, prev = f"{base}-r{n}", first["input"]
    j = quotas.reserve(a, "film", f"Changes to {old}"[:80], {"film": name, "style": prev["style"]},
                       {"kind": "film", "style": prev["style"], "idea": prev.get("idea"), "seconds": prev.get("seconds"),
                        "review_treatment": False, "film": name, "revise_of": old, "note": note})
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
    v["tokens"] = int(j.get("tokens") or 0)
    if account["role"] != "admin":
        v.pop("cost_usd", None)                   # only the API-key part costs money; the owner sees it
        v.pop("agent_runs", None)                 # what the agent read: for the owner only
    return v


def job_usage(job_id: str) -> dict:
    """Calls and tokens of one job from the Call table (specs/008 US4 #1)."""
    with db.read() as con:
        r = con.execute("SELECT count(*), coalesce(sum(tokens_in), 0), coalesce(sum(tokens_out), 0), "
                        f"{TOKENS_SQL} FROM call WHERE job_id = ?", (job_id,)).fetchone()
        via = [x[0] for x in con.execute("SELECT DISTINCT via FROM call WHERE job_id = ? ORDER BY via", (job_id,))]
    return {"calls": r[0], "tokens_in": r[1], "tokens_out": r[2], "tokens": r[3], "via": via}


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


# ---------- learning a style (US2) ----------
def channel_url(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("@"):
        t = "https://www.youtube.com/" + t
    if not CHANNEL.match(t):
        raise StudioError("invalid", "hãy nhập địa chỉ kênh YouTube, ví dụ https://www.youtube.com/@ten-kenh", 422)
    return t.rstrip("/")


def upload_dir(owner: str) -> Path:
    return db.data_dir() / "uploads" / owner


def upload_meta(owner: str, upload_id: str) -> dict:
    """An upload of this customer; another customer's is simply not found."""
    if not UPLOAD_ID.match(upload_id or ""):
        raise StudioError("not_found", "không có tệp tải lên này", 404)
    meta = store.read_json(upload_dir(owner) / f"{upload_id}.json")
    if not meta or not (upload_dir(owner) / meta["file"]).is_file() or meta.get("job"):
        raise StudioError("not_found", "không có tệp tải lên này", 404)
    return meta


def post_learn(body: JobIn, a) -> dict:
    s = quotas.settings()
    set_name = f"learn-{secrets.token_hex(3)}"
    if body.source == "youtube":
        if not body.rights_confirmed:
            raise StudioError("rights_required", "hãy xác nhận quyền dùng video của kênh trước khi học", 422)
        url = channel_url(body.channel)
        count = body.count or 5
        if count > s["learn_max_videos"]:
            raise StudioError("too_many_videos", f"học tối đa {s['learn_max_videos']} video mỗi lần", 422)
        inp, name = {"kind": "learn", "source": "youtube", "channel": url, "count": count, "set": set_name}, \
            f"Learn a style from {count} videos of a channel"
    elif body.source == "upload":
        ids = list(dict.fromkeys(body.uploads or []))
        if not ids or len(ids) > s["learn_max_videos"]:
            raise StudioError("too_many_videos", f"cần 1–{s['learn_max_videos']} video tải lên", 422)
        for u in ids:
            upload_meta(a["id"], u)
        inp, name = {"kind": "learn", "source": "upload", "uploads": ids, "set": set_name}, \
            f"Learn a style from {len(ids)} uploaded video{'s' if len(ids) > 1 else ''}"
    else:
        raise StudioError("invalid", "nguồn phải là youtube hoặc upload", 422)
    ratelimit.hit("job_account", a["id"])
    j = quotas.reserve(a, "learn", name, {"set": set_name}, inp)
    if body.source == "youtube":
        with db.tx() as con:
            con.execute("INSERT INTO rights VALUES (?, ?, ?, ?, ?)", (a["id"], j["id"], inp["channel"], store.now_iso(),
                                                                     RIGHTS_VERSION))
    else:
        for u in inp["uploads"]:          # an upload belongs to one job from now on
            mp = upload_dir(a["id"]) / f"{u}.json"
            meta = store.read_json(mp)
            meta["job"] = j["id"]
            store.write_json(mp, meta)
    return view(j, a)


@router.post("/uploads", status_code=201)
def post_upload(request: Request, file: UploadFile = File(...)):
    """One reference video. It is never served back (FR-018); only a learn job of the same customer uses it."""
    a = me(request)
    s = quotas.settings()
    ext = Path(file.filename or "").suffix.lower()
    if ext not in VIDEO_EXT:
        raise StudioError("bad_video", "chỉ nhận tệp video (mp4, mov, mkv, webm, m4v, avi)", 422)
    d = upload_dir(a["id"])
    d.mkdir(parents=True, exist_ok=True)
    uid = f"u-{secrets.token_hex(8)}"
    dest, limit, size = d / f"{uid}{ext}", s["upload_max_mb"] * 1024 * 1024, 0
    with open(dest, "wb") as out:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                out.close()
                dest.unlink(missing_ok=True)
                raise StudioError("too_large", f"tệp tối đa {s['upload_max_mb']} MB", 413)
            out.write(chunk)
    try:
        p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "json",
                            str(dest)], capture_output=True, text=True, timeout=60)
        info = json.loads(p.stdout or "{}")
        seconds = float(info.get("format", {}).get("duration") or 0)
        has_video = any(x.get("codec_type") == "video" for x in info.get("streams", []))
    except (OSError, ValueError, subprocess.TimeoutExpired):
        seconds, has_video = 0, False
    if not has_video or seconds <= 0:
        dest.unlink(missing_ok=True)
        raise StudioError("bad_video", "không đọc được video trong tệp này", 422)
    if seconds > s["upload_max_minutes"] * 60:
        dest.unlink(missing_ok=True)
        raise StudioError("too_long", f"mỗi video dài tối đa {s['upload_max_minutes']} phút", 422)
    store.write_json(d / f"{uid}.json", {"id": uid, "file": dest.name, "seconds": round(seconds, 2), "bytes": size,
                                         "created_at": store.now_iso(), "job": None})
    return {"upload_id": uid, "seconds": round(seconds, 2)}


@router.delete("/styles/{slug}", status_code=204)
def delete_style(slug: str, request: Request):
    a = me(request)
    d = resources.style_dir(slug)
    if not (d / "style.json").is_file():
        raise StudioError("not_found", f"không có phong cách \"{slug}\"", 404)
    for j in jobs.all_jobs(a["id"]):
        if j["status"] not in jobs.FINAL and (j.get("input") or {}).get("style") == slug:
            raise StudioError("in_use", "phong cách đang được một việc dùng", 409)
    shutil.rmtree(d)
    readme = d.parent / "README.md"
    if readme.is_file():                  # drop its line from the catalog the film agent reads
        lines = [x for x in readme.read_text(encoding="utf-8").splitlines(True) if not x.startswith(f"| {slug} |")]
        readme.write_text("".join(lines), encoding="utf-8")
    return Response(status_code=204)


# ---------- admin (US3) ----------
class AccountIn(BaseModel):
    quota_films: Optional[int] = Field(default=None, ge=0, le=1000)
    quota_learns: Optional[int] = Field(default=None, ge=0, le=1000)
    use_default_films: bool = False          # back to the studio default
    use_default_learns: bool = False
    locked: Optional[bool] = None


def admin(request: Request):
    a = me(request)
    if a["role"] != "admin":
        raise StudioError("forbidden", "chỉ quản trị viên mới dùng được", 403)
    return a


_sizes: dict = {}          # account id: (time, MB) — walking folders is slow, so cache it 10 minutes


def storage_mb(account_id: str) -> float:
    import time
    hit = _sizes.get(account_id)
    if hit and time.time() - hit[0] < 600:
        return hit[1]
    total = 0
    for base in (store.account_dir(account_id), db.data_dir() / "uploads" / account_id):
        if base.exists():
            total += sum(f.stat().st_size for f in base.rglob("*") if f.is_file() and not f.is_symlink())
    mb = round(total / 1e6, 1)
    _sizes[account_id] = (time.time(), mb)
    return mb


TOKENS_SQL = "coalesce(sum(tokens_in + tokens_out + cache_write + cache_read), 0)"
VN_DAY_SQL = "date(at, '+7 hours')"            # Call times are UTC; days are Vietnam days (007)


def month_tokens(con, account_id: str) -> int:
    since = quotas.month_start_vn().astimezone(dt_utc()).isoformat(timespec="seconds")
    return con.execute(f"SELECT {TOKENS_SQL} FROM call WHERE account_id = ? AND at >= ?", (account_id, since)).fetchone()[0]


def dt_utc():
    import datetime as dt
    return dt.timezone.utc


def account_row(con, row) -> dict:
    return {**accounts.public(row), "quota_films": row["quota_films"], "quota_learns": row["quota_learns"],
            "created_at": row["created_at"], "quota": quotas.summary(row), "tokens_month": month_tokens(con, row["id"]),
            "storage_mb": storage_mb(row["id"])}


@router.get("/admin/settings")
def get_settings(request: Request):
    admin(request)
    return quotas.settings()


@router.put("/admin/settings")
async def put_settings(request: Request):
    admin(request)
    try:
        body = await request.json()
    except ValueError:
        body = None
    if not isinstance(body, dict):
        raise StudioError("invalid", "cần một đối tượng JSON", 422)
    return quotas.update_settings(body)


@router.get("/admin/accounts")
def list_accounts(request: Request, q: str = ""):
    admin(request)
    q = (q or "").strip().lower()[:254]
    with db.read() as con:
        rows = con.execute("SELECT * FROM accounts WHERE deleted_at IS NULL AND instr(email, ?) > 0 "
                           "ORDER BY created_at DESC LIMIT 200", (q,)).fetchall()
        return {"accounts": [account_row(con, r) for r in rows]}


@router.put("/admin/accounts/{account_id}")
def put_account(account_id: str, body: AccountIn, request: Request):
    me_ = admin(request)
    row = accounts.get(account_id)
    if not row:
        raise StudioError("not_found", "không có tài khoản này", 404)
    if body.locked and account_id == me_["id"]:
        raise StudioError("invalid", "không tự khoá tài khoản quản trị", 422)
    with db.tx() as con:
        for field, default in (("quota_films", body.use_default_films), ("quota_learns", body.use_default_learns)):
            value = getattr(body, field)
            if default:
                con.execute(f"UPDATE accounts SET {field} = NULL WHERE id = ?", (account_id,))
            elif value is not None:
                con.execute(f"UPDATE accounts SET {field} = ? WHERE id = ?", (value, account_id))
        if body.locked is not None:
            con.execute("UPDATE accounts SET locked_at = ? WHERE id = ?",
                        (store.now_iso() if body.locked else None, account_id))
    if body.locked:                  # stop what runs now; the worker sees it and removes the containers
        for j in jobs.all_jobs(account_id):
            if j["status"] not in jobs.FINAL:
                try:
                    jobs.finish(j["id"], "stopped", error="Stopped: the account was locked by the studio")
                except StudioError:
                    pass
    with db.read() as con:
        return account_row(con, con.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone())


DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@router.get("/admin/usage")
def usage(request: Request, start: Optional[str] = Query(None, alias="from"), end: Optional[str] = Query(None, alias="to")):
    """Calls, tokens and jobs per day (Vietnam days), per member and per Claude account, all from the Call table
    (specs/008 FR-115); USD only for calls through the API key; total storage. Default: the last 30 days."""
    import datetime as dt
    admin(request)
    today = dt.date.fromisoformat(quotas.today_vn())
    end = end or today.isoformat()
    start = start or (today - dt.timedelta(days=29)).isoformat()
    try:
        ok = bool(DAY.match(start) and DAY.match(end)) and dt.date.fromisoformat(start) <= dt.date.fromisoformat(end)
    except ValueError:
        ok = False
    if not ok:
        raise StudioError("invalid", "ngày phải có dạng YYYY-MM-DD và from ≤ to", 422)
    cols = f"count(*), {TOKENS_SQL}, coalesce(sum(cost_usd), 0), count(DISTINCT job_id)"
    where = f"{VN_DAY_SQL} BETWEEN ? AND ?"
    row = lambda r: {"calls": r[0], "tokens": r[1], "cost_usd": round(r[2], 4), "jobs": r[3]}      # noqa: E731
    with db.read() as con:
        days = [{"day": r[4], **row(r)} for r in con.execute(
            f"SELECT {cols}, {VN_DAY_SQL} AS d FROM call WHERE {where} GROUP BY d ORDER BY d", (start, end))]
        by = [{"account_id": r[4], "email": r[5], **row(r)} for r in con.execute(
            f"SELECT {cols}, c.account_id, a.email FROM call c LEFT JOIN accounts a ON a.id = c.account_id "
            f"WHERE {where} AND c.account_id IS NOT NULL GROUP BY c.account_id ORDER BY 2 DESC", (start, end))]
        claude = [{"via": r[4], **row(r)} for r in con.execute(
            f"SELECT {cols}, via FROM call WHERE {where} GROUP BY via ORDER BY via", (start, end))]
        ids = [r[0] for r in con.execute("SELECT id FROM accounts WHERE deleted_at IS NULL")]
    return {"from": start, "to": end, "days": days, "by_account": by, "by_claude": claude,
            "calls_total": sum(d["calls"] for d in days), "tokens_total": sum(d["tokens"] for d in days),
            "cost_usd_total": round(sum(d["cost_usd"] for d in days), 4),
            "storage_mb_total": round(sum(storage_mb(i) for i in ids), 1)}


# ---------- Claude accounts (specs/008 contracts/api-admin-claude.md) ----------
class CodeIn(BaseModel):
    code: str = Field(min_length=1, max_length=500)


def claude_overview() -> dict:
    return {"accounts": claude_plan.accounts(), "login": claude_plan.pending(), "api_key": claude_plan.api_key(),
            "ready": claude_plan.ready(), "order": claude_plan.order()}


class OrderIn(BaseModel):
    mode: Literal["auto", "manual"]


@router.put("/admin/claude/order")
def put_claude_order(body: OrderIn, request: Request):
    """auto: least used first; manual: top of the list first (FR-120)."""
    admin(request)
    claude_plan.set_order(body.mode)
    return claude_overview()


@router.post("/admin/claude/accounts/{slot}/top")
def top_claude(slot: int, request: Request):
    admin(request)
    claude_plan.move_to_top(slot)
    return claude_overview()


@router.get("/admin/claude")
def get_claude(request: Request):
    admin(request)
    return claude_overview()


@router.post("/admin/claude/refresh")
def refresh_claude(request: Request):
    admin(request)
    claude_plan.refresh_all()
    return claude_overview()


@router.post("/admin/claude/accounts", status_code=201)
def add_claude(request: Request):
    admin(request)
    return claude_plan.add_account()


@router.delete("/admin/claude/accounts/{slot}", status_code=204)
def remove_claude(slot: int, request: Request):
    admin(request)
    claude_plan.remove_account(slot)
    return Response(status_code=204)


@router.post("/admin/claude/accounts/{slot}/login")
def login_claude(slot: int, request: Request):
    admin(request)
    return claude_plan.start_login(slot)


@router.post("/admin/claude/accounts/{slot}/code")
def code_claude(slot: int, body: CodeIn, request: Request):
    admin(request)
    return claude_plan.submit_code(slot, body.code)


@router.post("/admin/claude/accounts/{slot}/logout")
def logout_claude(slot: int, request: Request):
    admin(request)
    return claude_plan.logout(slot)


# ---------- people who can sign in: Settings → Users (specs/008 FR-111, FR-112) ----------
class UserIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)
    role: Literal["admin", "customer"] = "customer"


class UserChange(BaseModel):
    role: Optional[Literal["admin", "customer"]] = None
    disabled: Optional[bool] = None
    password: Optional[str] = Field(default=None, max_length=200)


@router.get("/admin/users")
def list_users(request: Request):
    a = admin(request)
    return {"users": accounts.users(), "me": a["id"]}


@router.post("/admin/users", status_code=201)
def add_user(body: UserIn, request: Request):
    admin(request)
    return accounts.add_user(body.email, body.password, body.role)


@router.put("/admin/users/{account_id}")
def change_user(account_id: str, body: UserChange, request: Request):
    a = admin(request)
    return accounts.update_user(account_id, a["id"], role=body.role, disabled=body.disabled, password=body.password)


@router.post("/admin/users/{account_id}/signout", status_code=204)
def signout_user(account_id: str, request: Request):
    admin(request)
    accounts.signout_all(account_id)
    return Response(status_code=204)


@router.delete("/admin/users/{account_id}", status_code=204)
def remove_user(account_id: str, request: Request):
    a = admin(request)
    accounts.remove_user(account_id, a["id"])
    return Response(status_code=204)
