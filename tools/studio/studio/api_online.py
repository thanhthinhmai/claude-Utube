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
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from . import accounts, claude_plan, db, jobs, tokens, moderation, quotas, ratelimit, resources, reviews, store
from .store import StudioError

router = APIRouter(prefix="/api/v1")

import sys as _sys  # noqa: E402
_sys.path.insert(0, str(Path(__file__).resolve().parents[2]))     # tools/: filmcheck (channels, specs/012)
from filmcheck import channels, topics as yt_topics  # noqa: E402


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
    # film for one of the customer's channels (specs/012); for a learn job `channel` is the YouTube URL instead
    lesson: bool = False
    topic: Optional[int] = Field(default=None, ge=1)


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
    """Make a film, a revision or a learn job. With an API token, only when it may use credits (FR-212);
    an Idempotency-Key makes a repeat return the first job instead of a second one (FR-221)."""
    import sqlite3
    a = me(request)
    token = getattr(request.state, "token", None)
    if token is not None and not token["can_spend"]:
        request.state.token_outcome = "no_spend"
        raise StudioError("spend_not_allowed", "mã API này không được dùng lượt phim", 403)
    key = request.headers.get("idempotency-key")
    if not key:
        return make_job(body, a)
    body_hash = tokens.request_hash(body.model_dump())

    def replay(job_id):
        if token is not None:
            request.state.token_outcome = "replay"
        return JSONResponse(view(jobs.load(job_id, a["id"]), a), status_code=200,
                            headers={"Idempotent-Replayed": "true"})
    done = tokens.replayed(a["id"], key, body_hash)
    if done:
        return replay(done)
    mark = tokens.current_idem.set((a["id"], key, body_hash))
    try:
        return make_job(body, a)
    except sqlite3.IntegrityError:                 # another request with this key made the job a moment ago
        return replay(tokens.replayed(a["id"], key, body_hash))
    finally:
        tokens.current_idem.reset(mark)


def make_job(body: JobIn, a) -> dict:
    if not a["email_verified_at"]:
        raise StudioError("unverified", "hãy xác minh email trước khi giao việc", 403)
    if body.kind == "learn":
        return post_learn(body, a)
    if body.revise_of:
        return post_revision(body, a)
    s = quotas.settings()
    slug, note = None, None
    if body.channel:                                    # the channel's profile fills what the customer left out
        slug = body.channel
        ch = channel_or_404(slug)
        body = body.model_copy(update={"style": body.style or ch["style"], "seconds": body.seconds or ch["seconds"]})
        if body.seconds > s["film_max_seconds"] and not body.model_fields_set & {"seconds"}:
            note = f"The channel's length ({body.seconds} s) is over the studio's limit; using {s['film_max_seconds']} s."
            body = body.model_copy(update={"seconds": s["film_max_seconds"]})
        if not style_exists(body.style):
            raise StudioError("invalid", f"phong cách \"{body.style}\" của kênh không còn; hãy sửa kênh", 422)
    if not (body.style and body.idea and body.seconds):
        raise StudioError("invalid", "việc làm phim cần style, idea và seconds", 422)
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
    inp = {"kind": "film", "style": body.style, "idea": body.idea, "seconds": body.seconds,
           "review_treatment": body.review_treatment, "film": name}
    if slug:
        inp["channel"] = slug
    if body.topic is not None:                         # a topic of the channel's queue (specs/013 FR-009)
        if not slug:
            raise StudioError("invalid", "đề thuộc một kênh: hãy gửi kèm kênh", 422)
        data = yt_topics.load(store.root(), slug)
        try:
            t = yt_topics.find(data, body.topic)
        except yt_topics.TopicError:
            raise StudioError("not_found", f"không có đề #{body.topic}", 404) from None
        if t["status"] not in ("queued", "in_progress"):
            raise StudioError("invalid", f"đề #{body.topic} đang ở trạng thái {t['status']}", 409)
        inp["topic"] = body.topic
    j = quotas.reserve(a, "film", body.idea[:80], {"film": name, "style": body.style}, inp)
    if body.topic is not None:                         # only once the film is really ordered
        t["status"], t["film"], t["taken_at"] = "in_progress", name, store.now_iso()
        yt_topics.save(store.root(), slug, data)
    if note:
        j = jobs.log(j["id"], note)
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
    if body.lesson and not prev.get("channel"):
        raise StudioError("invalid", "phim này không thuộc kênh nào, nên không ghi được bài học", 422)
    inp = {"kind": "film", "style": prev["style"], "idea": prev.get("idea"), "seconds": prev.get("seconds"),
           "review_treatment": False, "film": name, "revise_of": old, "note": note}
    if prev.get("channel"):
        inp["channel"] = prev["channel"]
        inp["lesson"] = bool(body.lesson)
    j = quotas.reserve(a, "film", f"Changes to {old}"[:80], {"film": name, "style": prev["style"]}, inp)
    return view(j, a)


# ---------- channels and lessons (specs/012 contracts/api.md) ----------
CHANNEL_HTTP = {"invalid": 422, "exists": 409, "limit": 409, "not_found": 404, "not_draft": 409}


def channel_error(e) -> StudioError:
    return StudioError(e.code, str(e), CHANNEL_HTTP.get(e.code, 422))


def shared_lessons_path() -> Path:
    return db.data_dir() / "shared" / "lessons.json"


def channel_or_404(slug: str) -> dict:
    try:
        return channels.load(store.root(), slug)
    except channels.ChannelError as e:
        raise channel_error(channels.ChannelError(f"không có kênh \"{slug}\"", "not_found")) from e


class ChannelIn(BaseModel):
    slug: Optional[str] = Field(default=None, max_length=40)
    name: Optional[str] = Field(default=None, max_length=80)
    niche: Optional[str] = Field(default=None, max_length=500)
    audience: Optional[str] = Field(default=None, max_length=500)
    language: Optional[str] = Field(default=None, max_length=3)
    seconds: Optional[int] = None
    style: Optional[str] = Field(default=None, max_length=60)
    voice: Optional[str] = Field(default=None, max_length=80)
    speed: Optional[float] = None
    title_rules: Optional[str] = Field(default=None, max_length=1500)
    thumbnail_rules: Optional[str] = Field(default=None, max_length=1500)
    title_max: Optional[int] = None
    hashtags: Optional[List[str]] = Field(default=None, max_length=5)
    banned: Optional[List[str]] = Field(default=None, max_length=50)


class DecisionIn(BaseModel):
    text: str = Field(min_length=1, max_length=300)


class LessonIn(BaseModel):
    what: Optional[str] = Field(default=None, max_length=400)
    why: Optional[str] = Field(default=None, max_length=400)
    stop: Optional[str] = Field(default=None, max_length=400)
    film: Optional[str] = Field(default=None, max_length=60)
    rule: Optional[str] = Field(default=None, max_length=120)


def _ch(fn):
    try:
        return fn()
    except channels.ChannelError as e:
        raise channel_error(e) from None


@router.get("/channels")
def list_channels(request: Request):
    me(request)
    return {"channels": [{k: c.get(k) for k in ("slug", "name", "language", "seconds", "style", "lessons_active",
                                                 "lessons_draft")} for c in channels.list_channels(store.root())]}


@router.post("/channels", status_code=201)
def new_channel(body: ChannelIn, request: Request):
    me(request)
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    return _ch(lambda: channels.save(store.root(), data, resources.lib_dir(), new=True))


@router.get("/channels/{slug}")
def get_channel(slug: str, request: Request):
    me(request)
    ch = channel_or_404(slug)
    return {**ch, "lessons": channels.load_lessons(channels.lessons_file(store.root(), slug))["lessons"]}


@router.put("/channels/{slug}")
def put_channel(slug: str, body: ChannelIn, request: Request):
    me(request)
    ch = channel_or_404(slug)
    ch.update({k: v for k, v in body.model_dump(exclude_unset=True).items() if k != "slug"})
    return _ch(lambda: channels.save(store.root(), ch, resources.lib_dir()))


@router.post("/channels/{slug}/decisions", status_code=201)
def add_decision(slug: str, body: DecisionIn, request: Request):
    me(request)
    channel_or_404(slug)
    return _ch(lambda: channels.decide(store.root(), slug, body.text, resources.lib_dir()))


@router.post("/channels/{slug}/lessons", status_code=201)
def add_channel_lesson(slug: str, body: LessonIn, request: Request):
    me(request)
    channel_or_404(slug)
    return _ch(lambda: channels.add_lesson(channels.lessons_file(store.root(), slug), what=body.what or "", why=body.why or "",
                                           stop=body.stop or "", film=body.film, rule=body.rule, status="active"))


@router.put("/channels/{slug}/lessons/{n}")
def edit_channel_lesson(slug: str, n: int, body: LessonIn, request: Request):
    me(request)
    channel_or_404(slug)
    return _ch(lambda: channels.edit_draft(channels.lessons_file(store.root(), slug), n,
                                           **body.model_dump(exclude_unset=True, exclude={"film"})))


@router.post("/channels/{slug}/lessons/{n}/approve")
def approve_channel_lesson(slug: str, n: int, request: Request):
    me(request)
    channel_or_404(slug)
    return _ch(lambda: channels.approve(channels.lessons_file(store.root(), slug), n))


@router.post("/channels/{slug}/lessons/{n}/retire")
def retire_channel_lesson(slug: str, n: int, request: Request):
    me(request)
    channel_or_404(slug)
    return _ch(lambda: channels.retire(channels.lessons_file(store.root(), slug), n))


# ---------- topics (specs/013 contracts/api.md) ----------
class ScoreIn(BaseModel):
    topics: List[str] = Field(min_length=1, max_length=yt_topics.MAX_TOPICS)
    suggest: bool = False


class TypeIn(BaseModel):
    type: str = Field(max_length=20)


class FitIn(BaseModel):
    score: int = Field(ge=0, le=10)


class TakeIn(BaseModel):
    allow_stale: bool = False


class RefsIn(BaseModel):
    channels: List[str] = Field(max_length=yt_topics.MAX_REFS)


def _public(t: dict) -> dict:
    return {k: v for k, v in t.items() if k != "raw"}


def topics_today(account_id: str) -> int:
    """Topics this person asked to score today (UTC day), suggestions not counted."""
    day = store.now_iso()[:10]
    return sum(len((j.get("input") or {}).get("topics") or []) for j in jobs.all_jobs(account_id)
               if j["kind"] == "topics" and (j.get("started_at") or "")[:10] == day)


def _topics_or(fn):
    try:
        return fn()
    except yt_topics.TopicError as e:
        raise StudioError("invalid", str(e), 422) from None


@router.get("/channels/{slug}/topics")
def get_topics(slug: str, request: Request):
    a = me(request)
    channel_or_404(slug)
    data = yt_topics.load(store.root(), slug)
    return {"topics": [_public(t) for t in data["topics"]], "queue": yt_topics.queue(data),
            "stale": [t["n"] for t in data["topics"] if yt_topics.stale(t)],
            "usage": {"today": topics_today(a["id"]), "limit": quotas.settings().get("topics_per_day", 40)}}


@router.post("/channels/{slug}/topics/score", status_code=201)
def score_topics(slug: str, body: ScoreIn, request: Request):
    a = me(request)
    ch = channel_or_404(slug)
    texts = [t.strip() for t in body.topics if t.strip()]
    if not texts or any(not 3 <= len(t) <= 120 for t in texts):
        raise StudioError("invalid", "mỗi đề có 3–120 ký tự", 422)
    if not yt_topics.read_online_key(db.data_dir()):
        raise StudioError("youtube_not_ready", "xưởng chưa có khoá YouTube; chủ xưởng đặt trong Settings", 503)
    limit = quotas.settings().get("topics_per_day", 40)
    if topics_today(a["id"]) + len(texts) > limit:
        from datetime import datetime, timedelta, timezone
        e = StudioError("topics_limit", f"mỗi ngày chấm tối đa {limit} đề", 429)
        e.extra = {"retry_at": (datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                                + timedelta(days=1)).isoformat(timespec="seconds")}
        raise e
    data = yt_topics.load(store.root(), slug)
    inp = {"kind": "topics", "channel": slug, "topics": texts, "suggest": body.suggest, "channel_profile": ch,
           "references": yt_topics.load_refs(store.root(), slug), "made": yt_topics.made_items(store.root(), slug, data),
           "existing": data["topics"]}
    j = jobs.build("topics", f"Topics for {ch['name']}"[:80], {}, owner=a["id"], status="queued",
                   extra={"input": inp, "charged": False})
    store.doc_put("job", j["id"], j)
    return view(j, a)


def _save_topics(slug, data):
    ch = channel_or_404(slug)
    yt_topics.save(store.root(), slug, data, ch.get("name"))


@router.post("/channels/{slug}/topics/{n}/type")
def topic_type(slug: str, n: int, body: TypeIn, request: Request):
    me(request)
    channel_or_404(slug)
    data = yt_topics.load(store.root(), slug)
    t = _topics_or(lambda: yt_topics.set_type(data, n, body.type))
    _save_topics(slug, data)
    return _public(t)


@router.post("/channels/{slug}/topics/{n}/fit")
def topic_fit(slug: str, n: int, body: FitIn, request: Request):
    me(request)
    channel_or_404(slug)
    data = yt_topics.load(store.root(), slug)
    t = _topics_or(lambda: yt_topics.set_fit(data, n, body.score, yt_topics.made_items(store.root(), slug, data)))
    _save_topics(slug, data)
    return _public(t)


@router.post("/channels/{slug}/topics/take")
def topic_take(slug: str, body: TakeIn, request: Request):
    """The next topic to make (R4); it becomes in progress when a film is made with it."""
    me(request)
    channel_or_404(slug)
    data = yt_topics.load(store.root(), slug)
    t, skipped = yt_topics.take(json.loads(json.dumps(data)), None, body.allow_stale)    # a dry run: nothing saved
    if not t:
        e = StudioError("none_left", "không còn đề nào lấy được lúc này", 409)
        e.extra = {"skipped": skipped}
        raise e
    return {"topic": _public(yt_topics.find(data, t["n"])), "skipped": skipped}


@router.get("/channels/{slug}/references")
def get_refs(slug: str, request: Request):
    me(request)
    channel_or_404(slug)
    return {"channels": yt_topics.load_refs(store.root(), slug)}


@router.put("/channels/{slug}/references")
def put_refs(slug: str, body: RefsIn, request: Request):
    me(request)
    channel_or_404(slug)
    return {"channels": _topics_or(lambda: yt_topics.save_refs(store.root(), slug, body.channels))}


@router.get("/lessons/shared")
def list_shared_lessons(request: Request):
    admin(request)
    return channels.load_lessons(shared_lessons_path())


@router.post("/lessons/shared", status_code=201)
def add_shared_lesson(body: LessonIn, request: Request):
    admin(request)
    return _ch(lambda: channels.add_lesson(shared_lessons_path(), what=body.what or "", why=body.why or "",
                                           stop=body.stop or "", rule=body.rule, status="active", title="shared"))


@router.post("/lessons/shared/{n}/retire")
def retire_shared_lesson(n: int, request: Request):
    admin(request)
    return _ch(lambda: channels.retire(shared_lessons_path(), n, "shared"))


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


def upload_ext(filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in VIDEO_EXT:
        raise StudioError("bad_video", "chỉ nhận tệp video (mp4, mov, mkv, webm, m4v, avi)", 422)
    return ext


def new_upload(account_id: str, ext: str):
    d = upload_dir(account_id)
    d.mkdir(parents=True, exist_ok=True)
    uid = f"u-{secrets.token_hex(8)}"
    return uid, d / f"{uid}{ext}"


def too_large(dest: Path, s) -> StudioError:
    dest.unlink(missing_ok=True)
    return StudioError("too_large", f"tệp tối đa {s['upload_max_mb']} MB", 413)


def finish_upload(account_id: str, uid: str, dest: Path, size: int) -> dict:
    """Check the saved file is a video within the limits, then record it (FR-018: never served back)."""
    s = quotas.settings()
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
    store.write_json(upload_dir(account_id) / f"{uid}.json", {"id": uid, "file": dest.name, "seconds": round(seconds, 2),
                                                              "bytes": size, "created_at": store.now_iso(), "job": None})
    return {"upload_id": uid, "seconds": round(seconds, 2)}


@router.post("/uploads", status_code=201)
def post_upload(request: Request, file: UploadFile = File(...)):
    """One reference video. It is never served back (FR-018); only a learn job of the same customer uses it."""
    a = me(request)
    s = quotas.settings()
    uid, dest = new_upload(a["id"], upload_ext(file.filename))
    limit, size = s["upload_max_mb"] * 1024 * 1024, 0
    with open(dest, "wb") as out:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                out.close()
                raise too_large(dest, s)
            out.write(chunk)
    return finish_upload(a["id"], uid, dest, size)


# ---------- one-time links to upload and download (specs/009 FR-220, research R6) ----------
class UploadTicketIn(BaseModel):
    filename: str = Field(min_length=1, max_length=200)
    size_bytes: int = Field(ge=1)


def studio_url(request: Request) -> str:
    return (os.environ.get("STUDIO_URL") or str(request.base_url)).rstrip("/")


@router.post("/uploads/tickets", status_code=201)
def upload_ticket(body: UploadTicketIn, request: Request):
    """A link that takes one video with PUT, for 30 minutes: an agent uploads without the token in its shell."""
    a = me(request)
    s = quotas.settings()
    upload_ext(body.filename)
    if body.size_bytes > s["upload_max_mb"] * 1024 * 1024:
        raise StudioError("too_large", f"tệp tối đa {s['upload_max_mb']} MB", 413)
    secret, expires = tokens.make_ticket("upload", a["id"], Path(body.filename).name, body.size_bytes,
                                         getattr(request.state, "token", None))
    url = f"{studio_url(request)}/api/v1/uploads/t/{secret}"
    return {"upload_url": url, "expires_at": expires, "curl": f'curl -T "{Path(body.filename).name}" "{url}"'}


@router.put("/uploads/t/{secret}", status_code=201)
async def upload_by_ticket(secret: str, request: Request):
    """The file itself (raw body). The link is the key: no cookie, no token (a public path)."""
    t = tokens.use_ticket("upload", secret)
    s = quotas.settings()
    uid, dest = new_upload(t["account_id"], upload_ext(t["filename"]))
    limit = min(s["upload_max_mb"] * 1024 * 1024, (t["size"] or 0) + 1024 * 1024)   # declared size, some slack
    size = 0
    with open(dest, "wb") as out:
        async for chunk in request.stream():
            size += len(chunk)
            if size > limit:
                out.close()
                raise too_large(dest, s)
            out.write(chunk)
    import starlette.concurrency
    return await starlette.concurrency.run_in_threadpool(finish_upload, t["account_id"], uid, dest, size)


@router.post("/films/{name}/tickets", status_code=201)
def download_ticket(name: str, request: Request):
    """A link to download one finished film once, for 30 minutes."""
    a = me(request)
    resources.film_file(name, "video")                         # 404 unless it is a finished film of this person
    secret, expires = tokens.make_ticket("download", a["id"], name, None, getattr(request.state, "token", None))
    url = f"{studio_url(request)}/api/v1/films/t/{secret}"
    return {"download_url": url, "expires_at": expires, "curl": f'curl -o "{name}.mp4" "{url}"'}


@router.get("/films/t/{secret}")
def download_by_ticket(secret: str):
    t = tokens.use_ticket("download", secret)
    with store.as_account(t["account_id"]):
        path = resources.film_file(t["filename"], "video")
    return FileResponse(path, media_type="video/mp4", filename=f"{t['filename']}.mp4")


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
    """The Owner making this request; with an API token, its role is already capped (specs/009 FR-214)."""
    a = me(request)
    if a["role"] != "admin":
        if getattr(request.state, "token", None):
            request.state.token_outcome = "forbidden"
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
    s = quotas.settings()
    key = yt_topics.read_online_key(db.data_dir())        # specs/013: never the key itself
    return {**s, "youtube_key_set": bool(key), "youtube_key_last4": key[-4:] if key else None,
            "youtube_units_today": yt_topics.online_usage(db.data_dir(), s.get("youtube_daily_units", 9000)).today()}


class YouTubeKeyIn(BaseModel):
    key: str = Field(min_length=20, max_length=100)


@router.put("/admin/youtube-key")
def put_youtube_key(body: YouTubeKeyIn, request: Request):
    """Try the key with one 1-unit call, then keep it (specs/013 FR-011). The answer never contains it."""
    admin(request)
    key = body.key.strip()
    s = quotas.settings()
    f = yt_topics.Fetcher.local(key, yt_topics.online_usage(db.data_dir(), s.get("youtube_daily_units", 9000)),
                                yt_topics.Cache(db.data_dir() / "youtube" / "check", hours=0))
    try:
        f.get("videos", {"part": "id", "id": "dQw4w9WgXcQ"})
    except (yt_topics.TopicError, yt_topics.QuotaError) as e:
        raise StudioError("youtube_key_invalid", "khoá YouTube không dùng được: " + yt_topics.redact(str(e), key), 422) from None
    yt_topics.save_online_key(db.data_dir(), key)
    return {"set": True, "last4": key[-4:]}


@router.delete("/admin/youtube-key", status_code=204)
def delete_youtube_key(request: Request):
    admin(request)
    yt_topics.online_key_file(db.data_dir()).unlink(missing_ok=True)
    return Response(status_code=204)


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
            "ready": claude_plan.ready(), "order": claude_plan.order(), "waiting": claude_plan.waiting_jobs()}


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


# ---------- Settings → Worker (specs/009 FR-201-FR-206, contracts/api-tokens-worker.md) ----------
WORKER_ALIVE_S, WORKER_HIDE_S, LATEST = 30, 600, 20


@router.get("/admin/worker")
def worker_status(request: Request):
    """Each worker process from its heartbeat, the four counts, and the 20 latest jobs of everyone."""
    admin(request)
    with db.read() as con:
        workers = []
        for r in con.execute("SELECT * FROM worker_beat ORDER BY started_at"):
            ago = store.age_seconds(r["beat_at"])
            if ago > WORKER_HIDE_S:
                continue
            workers.append({"id": r["id"], "state": "running" if ago <= WORKER_ALIVE_S else "not_responding",
                            "busy_with": json.loads(r["busy"] or "[]"), "beat_ago_s": int(ago),
                            "started_at": r["started_at"]})
        waiting_claude = claude_plan.waiting_jobs()
        n = dict(con.execute("SELECT status, count(*) FROM docs WHERE kind = 'job' GROUP BY status").fetchall())
        rows = con.execute("SELECT d.data, a.email FROM docs d LEFT JOIN accounts a ON a.id = d.owner "
                           "WHERE d.kind = 'job' ORDER BY d.updated_ns DESC LIMIT ?", (LATEST,)).fetchall()
    latest = []
    for data, email in rows:
        j = json.loads(data)
        err_text = j.get("error")
        latest.append({"id": j["id"], "status": jobs.shown_status(j), "kind": j["kind"], "name": j["name"],
                       "email": email, "step": j.get("step"), "updated_at": j.get("updated_at"),
                       "error": err_text[:300] if err_text else None})
    mode = os.environ.get("STUDIO_RENDER_MODE")      # specs/019: set by the desktop host for every part
    render = {"mode": mode, "renderer": os.environ.get("STUDIO_RENDER_RENDERER"),
              "reason": os.environ.get("STUDIO_RENDER_REASON")} if mode else None
    return {"workers": workers, "latest": latest, "render": render,
            "counts": {"queued": max(0, n.get("queued", 0) - waiting_claude), "running": n.get("running", 0),
                       "waiting_review": n.get("waiting_review", 0), "waiting_claude": waiting_claude}}


# ---------- API tokens of one's own (specs/009 FR-208-FR-218, contracts/api-tokens-worker.md) ----------
class TokenIn(BaseModel):
    name: str = Field(max_length=60)
    role: Literal["customer", "admin"] = "customer"
    can_spend: bool = False
    rate_per_min: Literal[10, 30, 60, 120, 300] = 60
    expires: Literal["7d", "30d", "90d", "1y", "never"] = "90d"


@router.get("/me/tokens")
def my_tokens(request: Request):
    return {"tokens": tokens.list_tokens(me(request)["id"])}


@router.post("/me/tokens", status_code=201)
def make_token(body: TokenIn, request: Request):
    """The secret is in this answer only (FR-210)."""
    t, secret = tokens.create(me(request), body.name, body.role, body.can_spend, body.rate_per_min, body.expires)
    return {"token": t, "secret": secret}


@router.delete("/me/tokens/{token_id}", status_code=204)
def revoke_my_token(token_id: str, request: Request):
    tokens.revoke(token_id, me(request)["id"])
    return Response(status_code=204)


@router.get("/me/tokens/{token_id}/log")
def my_token_log(token_id: str, request: Request, limit: int = Query(200, ge=1, le=500)):
    return {"requests": tokens.log(token_id, me(request)["id"], limit)}


# ---------- every token, for the Owner (specs/009 FR-208, FR-216) ----------
@router.get("/admin/tokens")
def all_tokens(request: Request):
    admin(request)
    return {"tokens": tokens.list_tokens()}


@router.delete("/admin/tokens/{token_id}", status_code=204)
def revoke_any_token(token_id: str, request: Request):
    admin(request)
    tokens.revoke(token_id)
    return Response(status_code=204)


@router.get("/admin/tokens/{token_id}/log")
def any_token_log(token_id: str, request: Request, limit: int = Query(200, ge=1, le=500)):
    admin(request)
    return {"requests": tokens.log(token_id, None, limit)}
