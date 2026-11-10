"""Settings, monthly quotas and cost (specs/007 FR-005, FR-006, FR-006a, FR-008a, research R3)."""
import datetime as dt
import json

from . import db, jobs, store
from .store import StudioError

VN = dt.timezone(dt.timedelta(hours=7))
KIND_FIELD = {"film": ("quota_films", "quota_films_default"), "learn": ("quota_learns", "quota_learns_default")}
EDITOR_MODELS = ("inherit", "opus", "sonnet", "haiku")     # specs/010 FR-007b
MAX_OPEN = 3            # jobs not finished yet, per customer
OPEN = ("queued", "running", "waiting_review", "waiting_resume")

# name: (type, low, high); None means no bound
RANGES = {
    "quota_films_default": (int, 0, 1000),
    "quota_learns_default": (int, 0, 1000),
    "film_max_seconds": (int, 5, 300),
    "learn_max_videos": (int, 1, 20),
    "upload_max_mb": (int, 1, 4000),
    "upload_max_minutes": (int, 1, 120),
    "job_token_cap": (int, 1_000_000, 500_000_000),
    "claude_order": (str, None, None),
    "concurrency": (int, 1, 16),
    "review_timeout_days": (int, 1, 90),
    "model": (str, None, None),
    "editor_model": (str, None, None),
}


# ---------- settings ----------
def settings() -> dict:
    return db.settings()


def update_settings(changes: dict) -> dict:
    s = settings()
    for k, v in (changes or {}).items():
        if k == "price_table":
            if not isinstance(v, dict) or not all(
                    isinstance(p, dict) and all(isinstance(p.get(f), (int, float)) and p.get(f) >= 0
                                                for f in ("in", "out", "cache_write", "cache_read"))
                    for p in v.values()):
                raise StudioError("invalid", "bảng giá không hợp lệ", 422)
            s[k] = v
            continue
        if k not in RANGES:
            raise StudioError("invalid", f"không có cài đặt \"{k}\"", 422)
        typ, lo, hi = RANGES[k]
        ok = isinstance(v, bool) if typ is bool else (
            isinstance(v, str) and 0 < len(v) <= 80 if typ is str else
            isinstance(v, (int, float)) and not isinstance(v, bool) and (typ is float or float(v).is_integer()))
        if not ok or (lo is not None and not lo <= v <= hi):
            raise StudioError("invalid", f"giá trị của {k} ngoài khoảng cho phép", 422)
        s[k] = typ(v)
    if s.get("editor_model", "inherit") not in EDITOR_MODELS:
        raise StudioError("invalid", "editor_model phải là " + ", ".join(EDITOR_MODELS), 422)
    if s.get("claude_order", "auto") not in ("auto", "manual"):
        raise StudioError("invalid", "claude_order phải là auto hoặc manual", 422)
    if s["model"] not in s["price_table"]:
        raise StudioError("invalid", "model chưa có trong bảng giá", 422)
    db.save_settings(s)
    return s


# ---------- months (Vietnam time) ----------
def month_start_vn(now: float = None) -> dt.datetime:
    """00:00 on the 1st of this month, Vietnam time (Clarifications 2026-11-07)."""
    t = dt.datetime.fromtimestamp(store.clock() if now is None else now, VN)
    return t.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def next_reset_vn(now: float = None) -> dt.datetime:
    m = month_start_vn(now)
    return (m.replace(year=m.year + 1, month=1) if m.month == 12 else m.replace(month=m.month + 1))


def today_vn() -> str:
    return dt.datetime.fromtimestamp(store.clock(), VN).strftime("%Y-%m-%d")


def limit(account, kind: str) -> int:
    own, default = KIND_FIELD[kind]
    return account[own] if account[own] is not None else db.settings()[default]


def used(account_id: str, kind: str, con=None) -> int:
    """Charged jobs of this kind since the month started (data-model: Quota usage)."""
    since = month_start_vn().astimezone(dt.timezone.utc).isoformat(timespec="seconds")
    q = ("SELECT count(*) FROM docs WHERE kind = 'job' AND owner = ? AND json_extract(data, '$.kind') = ?"
         " AND json_extract(data, '$.charged') = 1 AND created_at >= ?")
    if con is not None:
        return con.execute(q, (account_id, kind, since)).fetchone()[0]
    with db.read() as c:
        return c.execute(q, (account_id, kind, since)).fetchone()[0]


def summary(account) -> dict:
    return {"films": {"used": used(account["id"], "film"), "limit": limit(account, "film")},
            "learns": {"used": used(account["id"], "learn"), "limit": limit(account, "learn")},
            "resets_at": next_reset_vn().isoformat(timespec="seconds")}


# ---------- reserve, refund, cost ----------
def reserve(account, kind: str, name: str, links: dict, job_input: dict) -> dict:
    """Charge one credit and create the queued job in the same transaction, so 10 requests at once
    can never use more than the quota (SC-008)."""
    s = settings()
    j = jobs.build(kind, name, links, owner=account["id"], status="queued",
                   extra={"input": job_input, "charged": True})
    from . import claude_plan
    if not claude_plan.ready():                       # specs/008 FR-110: no Claude account and no API key
        raise StudioError("studio_not_ready", "xưởng chưa có tài khoản Claude nào dùng được", 503)
    with db.tx() as con:
        open_jobs = con.execute(
            "SELECT count(*) FROM docs WHERE kind = 'job' AND owner = ? AND status IN (?, ?, ?, ?)",
            (account["id"], *OPEN)).fetchone()[0]
        if open_jobs >= MAX_OPEN:
            raise StudioError("too_many_queued", f"mỗi tài khoản chỉ có tối đa {MAX_OPEN} việc chưa xong", 409)
        if used(account["id"], kind, con) >= limit(account, kind):
            e = StudioError("quota_exceeded", "đã hết lượt của tháng này", 402)
            e.extra = {"resets_at": next_reset_vn().isoformat(timespec="seconds")}
            raise e
        store.doc_insert(con, "job", j["id"], j)
        from . import tokens
        idem = tokens.current_idem.get()
        if idem:                                   # same transaction: racing requests with one key make one job
            tokens.remember(con, idem[0], idem[1], idem[2], j["id"])
    return j


def refund(job_id: str, why: str = "Credit refunded") -> dict:
    def f(j):
        if j.get("charged"):
            j["charged"] = False
            j["log"].append(jobs._line(why))
    return jobs.update(job_id, f)


def fail(job_id: str, error: str, by: str = "studio") -> dict:
    """End a job as failed. A studio failure gives the credit back; a customer one does not (FR-006a)."""
    by = by if by in ("studio", "customer") else "studio"
    try:
        return jobs.finish(job_id, "failed", error=error, failure_kind=by, refund=by == "studio")
    except StudioError as e:
        if e.code != "finished":
            raise
        return jobs.load(job_id)


def price(model: str) -> dict:
    s = settings()
    table = s["price_table"]
    if model in table:
        return table[model]
    return max(table.values(), key=lambda p: p["out"])     # unknown model: the dearest price, never undercount


def cost_of(model: str, usage: dict) -> float:
    p = price(model)
    return ((usage.get("input_tokens") or 0) * p["in"] + (usage.get("output_tokens") or 0) * p["out"]
            + (usage.get("cache_creation_input_tokens") or 0) * p["cache_write"]
            + (usage.get("cache_read_input_tokens") or 0) * p["cache_read"]) / 1_000_000


TOKEN_FIELDS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def tokens_of(usage: dict) -> int:
    return int(sum((usage.get(k) or 0) for k in TOKEN_FIELDS))


def record_call(job_id, via: str, model: str, usage: dict) -> dict:
    """One Claude call (specs/008 data-model: Call): a row in `call`, the job's tokens, and cost only through the
    API key (`via` = "api"; a plan call costs nothing per call). Returns the job's totals {tokens, cost_usd}."""
    usd = cost_of(model or "", usage) if via == "api" else 0.0
    n = tokens_of(usage)
    with db.tx() as con:
        owner, totals = None, {"tokens": 0, "cost_usd": 0.0}
        if job_id:
            r = con.execute("SELECT data FROM docs WHERE kind = 'job' AND id = ?", (job_id,)).fetchone()
            if r:
                j = json.loads(r[0])
                owner = j["owner"]
                j["tokens"] = int(j.get("tokens") or 0) + n
                j["cost_usd"] = round((j.get("cost_usd") or 0.0) + usd, 6)
                store.doc_insert(con, "job", job_id, j)
                totals = {"tokens": j["tokens"], "cost_usd": j["cost_usd"]}
        con.execute("INSERT INTO call (job_id, account_id, via, model, tokens_in, tokens_out, cache_write, cache_read, "
                    "cost_usd, at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (job_id, owner, via, model, *(int(usage.get(k) or 0) for k in TOKEN_FIELDS), usd, store.now_iso()))
    return totals
