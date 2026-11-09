"""API tokens: each user makes tokens for their own agents (specs/009-settings-worker-tokens, research R1-R3, R9, R10).

A token is "fs_" + 32 random bytes. Only its sha256 and its first 8 characters are kept; the whole token is shown
once, when it is made. A token acts as its owner, never with more than the owner's current role. Every request made
with a token is one row of its log (kept 30 days; never the request's content). One-time tickets for uploads and
downloads, and the Idempotency-Key records of job creation, live here too."""
import datetime as dt
import hashlib
import json
import secrets

from . import accounts, db, quotas, store
from .store import StudioError

PREFIX = "fs_"
RATES = (10, 30, 60, 120, 300)
EXPIRES = {"7d": 7, "30d": 30, "90d": 90, "1y": 365, "never": None}
MAX_ACTIVE = 20                      # per person (research R9)
LOG_DAYS = 30
TICKET_MINUTES = 30
IDEMPOTENCY_HOURS = 24
BLOCKED = ("forbidden", "token_forbidden", "no_spend", "rate_limit")
# Paths no token may use, with any method (FR-213); matched against the path without the /api/v1 prefix
FORBIDDEN = ("/me/tokens", "/admin/tokens", "/admin/users", "/admin/claude")
FORBIDDEN_EXACT = {("PUT", "/me"), ("DELETE", "/me")}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _iso(t: float) -> str:
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat(timespec="seconds")


def _now() -> str:
    return store.now_iso()


def status(row) -> str:
    if row["revoked_at"]:
        return "revoked"
    if row["expires_at"] and row["expires_at"] <= _now():
        return "ended"
    return "active"


def is_forbidden(method: str, path: str) -> bool:
    """A path no token may use (FR-213). `path` is the full URL path."""
    p = path[len("/api/v1"):] if path.startswith("/api/v1") else path
    p = p.rstrip("/") or "/"
    return (method.upper(), p) in FORBIDDEN_EXACT or any(p == f or p.startswith(f + "/") for f in FORBIDDEN)


# ---------- making, finding, listing, revoking ----------
def create(owner, name: str, role: str = "customer", can_spend: bool = False, rate_per_min: int = 60,
           expires: str = "90d") -> tuple:
    """(token as listed, the secret). The secret is never stored or shown again (FR-210)."""
    name = (name or "").strip()
    if not 1 <= len(name) <= 60:
        raise StudioError("invalid", "tên mã cần 1–60 ký tự", 422)
    if role not in ("customer", "admin") or rate_per_min not in RATES or expires not in EXPIRES:
        raise StudioError("invalid", "giá trị không hợp lệ", 422)
    if role == "admin" and owner["role"] != "admin":
        raise StudioError("forbidden", "chỉ Owner tạo được mã Owner", 403)
    secret = PREFIX + secrets.token_urlsafe(32)
    tid, now = f"tok-{secrets.token_hex(6)}", store.clock()
    days = EXPIRES[expires]
    with db.tx() as con:
        active = [r for r in con.execute("SELECT * FROM api_token WHERE owner_id = ?", (owner["id"],))
                  if status(r) == "active"]
        if len(active) >= MAX_ACTIVE:
            raise StudioError("too_many_tokens", f"mỗi người tối đa {MAX_ACTIVE} mã đang dùng", 409)
        con.execute("INSERT INTO api_token (id, owner_id, name, prefix, hash, role, can_spend, rate_per_min, created_at, "
                    "expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (tid, owner["id"], name, secret[:8], sha(secret), role, 1 if can_spend else 0, rate_per_min,
                     _iso(now), _iso(now + days * 86400) if days else None))
    return get(tid), secret


def resolve(secret: str):
    """(owner account, token row, effective role) for a live token, else None (FR-214)."""
    if not secret or not secret.startswith(PREFIX) or not 30 <= len(secret) <= 100:
        return None
    with db.read() as con:
        t = con.execute("SELECT * FROM api_token WHERE hash = ?", (sha(secret),)).fetchone()
    if not t or status(t) != "active":
        return None
    owner = accounts.get(t["owner_id"])              # None once deleted
    if not owner or owner["locked_at"]:
        return None
    role = "admin" if t["role"] == "admin" and owner["role"] == "admin" else "customer"
    return owner, t, role


def _view(con, row) -> dict:
    today = dt.datetime.fromtimestamp(store.clock(), quotas.VN).replace(hour=0, minute=0, second=0, microsecond=0)
    since = today.astimezone(dt.timezone.utc).isoformat(timespec="seconds")      # "today" in Vietnam time
    n, blocked = con.execute(
        "SELECT count(*), coalesce(sum(outcome IN ('forbidden', 'token_forbidden', 'no_spend', 'rate_limit')), 0) "
        "FROM token_request WHERE token_id = ? AND at >= ?", (row["id"], since)).fetchone()
    owner = con.execute("SELECT id, email FROM accounts WHERE id = ?", (row["owner_id"],)).fetchone()
    return {"id": row["id"], "name": row["name"], "prefix": row["prefix"],
            "owner": {"id": row["owner_id"], "email": owner["email"] if owner else None},
            "role": row["role"], "can_spend": bool(row["can_spend"]), "rate_per_min": row["rate_per_min"],
            "created_at": row["created_at"], "expires_at": row["expires_at"], "revoked_at": row["revoked_at"],
            "last_used_at": row["last_used_at"], "requests_today": n, "blocked_today": blocked, "status": status(row)}


def get(token_id: str, owner_id: str = None) -> dict:
    with db.read() as con:
        row = con.execute("SELECT * FROM api_token WHERE id = ?", (token_id,)).fetchone()
        if not row or (owner_id and row["owner_id"] != owner_id):
            raise StudioError("not_found", "không có mã này", 404)
        return _view(con, row)


def list_tokens(owner_id: str = None) -> list:
    with db.read() as con:
        rows = con.execute("SELECT * FROM api_token " + ("WHERE owner_id = ? " if owner_id else "")
                           + "ORDER BY created_at DESC", (owner_id,) if owner_id else ()).fetchall()
        return [_view(con, r) for r in rows]


def revoke(token_id: str, owner_id: str = None) -> None:
    """Revoke a token: the owner (owner_id) or an Owner of the studio (owner_id None). The very next request fails."""
    get(token_id, owner_id)
    with db.tx() as con:
        con.execute("UPDATE api_token SET revoked_at = coalesce(revoked_at, ?) WHERE id = ?", (_now(), token_id))


# ---------- the log of a token (FR-218) ----------
_pruned = {"at": 0.0}


def record(token, method: str, path: str, outcome: str, ip: str = "") -> None:
    """One row per request made with a token; never its content."""
    now = store.clock()
    with db.tx() as con:
        con.execute("INSERT INTO token_request (token_id, at, method, path, outcome, ip) VALUES (?, ?, ?, ?, ?, ?)",
                    (token["id"], _iso(now), method.upper(), path[:300], outcome, (ip or "")[:64]))
        last = con.execute("SELECT last_used_at FROM api_token WHERE id = ?", (token["id"],)).fetchone()
        if last and (not last[0] or store.age_seconds(last[0]) >= 300):        # at most every 5 minutes
            con.execute("UPDATE api_token SET last_used_at = ? WHERE id = ?", (_iso(now), token["id"]))
        if now - _pruned["at"] >= 3600:                                          # at most once an hour
            _pruned["at"] = now
            con.execute("DELETE FROM token_request WHERE at < ?", (_iso(now - LOG_DAYS * 86400),))
            con.execute("DELETE FROM ticket WHERE expires_at < ?", (_iso(now - 86400),))
            con.execute("DELETE FROM idempotency WHERE created_at < ?", (_iso(now - IDEMPOTENCY_HOURS * 3600),))


def log(token_id: str, owner_id: str = None, limit: int = 200) -> list:
    get(token_id, owner_id)
    limit = max(1, min(int(limit or 200), 500))
    with db.read() as con:
        return [dict(r) for r in con.execute("SELECT at, method, path, outcome, ip FROM token_request WHERE token_id = ? "
                                             "ORDER BY id DESC LIMIT ?", (token_id, limit))]


# ---------- one-time tickets for uploads and downloads (research R6) ----------
def make_ticket(kind: str, account_id: str, filename: str, size: int = None, token=None) -> tuple:
    """(ticket secret, expires_at). Only its sha256 is kept."""
    secret = secrets.token_urlsafe(32)
    expires = _iso(store.clock() + TICKET_MINUTES * 60)
    with db.tx() as con:
        con.execute("INSERT INTO ticket (hash, kind, account_id, token_id, filename, size, expires_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (sha(secret), kind, account_id, token["id"] if token else None, filename, size, expires))
    return secret, expires


def use_ticket(kind: str, secret: str) -> dict:
    """The ticket, marked used; 404 when wrong, used or expired."""
    with db.tx() as con:
        t = con.execute("SELECT * FROM ticket WHERE hash = ? AND kind = ?", (sha(secret or ""), kind)).fetchone()
        if not t or t["used_at"] or t["expires_at"] <= _now():
            raise StudioError("not_found", "link không đúng, đã dùng hoặc đã hết hạn", 404)
        con.execute("UPDATE ticket SET used_at = ? WHERE hash = ?", (_now(), t["hash"]))
        return dict(t)


# ---------- Idempotency-Key for job creation (FR-221, research R10) ----------
def request_hash(body: dict) -> str:
    return sha(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def replayed(account_id: str, key: str, body_hash: str):
    """The job id made earlier with this key and the same request, or None for a new key.
    409 idempotency_conflict when the key was used for a different request."""
    if not key:
        return None
    if len(key) > 100:
        raise StudioError("invalid", "Idempotency-Key tối đa 100 ký tự", 422)
    since = _iso(store.clock() - IDEMPOTENCY_HOURS * 3600)
    with db.read() as con:
        r = con.execute("SELECT * FROM idempotency WHERE account_id = ? AND key_hash = ? AND created_at >= ?",
                        (account_id, sha(key), since)).fetchone()
    if not r:
        return None
    if r["request_hash"] != body_hash:
        raise StudioError("idempotency_conflict", "Idempotency-Key này đã dùng cho một yêu cầu khác", 409)
    return r["job_id"]


def remember(con, account_id: str, key: str, body_hash: str, job_id: str) -> None:
    """Called inside the transaction that creates the job, so racing requests with one key make one job.
    Raises sqlite3.IntegrityError when another request with this key won the race."""
    con.execute("DELETE FROM idempotency WHERE account_id = ? AND key_hash = ? AND created_at < ?",
                (account_id, sha(key), _iso(store.clock() - IDEMPOTENCY_HOURS * 3600)))
    con.execute("INSERT INTO idempotency VALUES (?, ?, ?, ?, ?)", (account_id, sha(key), body_hash, job_id, _now()))
