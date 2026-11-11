"""Accounts, sessions and one-time links (specs/007 FR-001, FR-002, FR-004, research R7)."""
import os
import datetime as dt
import hashlib
import re
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from . import db, jobs, mail, ratelimit, store
from .store import StudioError

COOKIE = "studio_session"
SESSION_DAYS = 30
TOKEN_HOURS = {"verify": 24, "reset": 1}
MIN_PASSWORD = 10
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
_ph = PasswordHasher()


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _at(seconds: float = 0) -> str:
    return dt.datetime.fromtimestamp(store.clock() + seconds, dt.timezone.utc).isoformat(timespec="seconds")


def _clean_email(email: str) -> str:
    email = (email or "").strip().lower()
    if len(email) > 254 or not EMAIL.match(email):
        raise StudioError("invalid", "email không hợp lệ", 422)
    return email


def _check_password(password: str) -> None:
    if len(password or "") < MIN_PASSWORD:
        raise StudioError("weak_password", f"mật khẩu cần ít nhất {MIN_PASSWORD} ký tự", 422)


def _new_token(con, account_id: str, purpose: str) -> str:
    token = secrets.token_urlsafe(32)
    con.execute("INSERT INTO tokens VALUES (?, ?, ?, ?, NULL)",
                (_hash(token), account_id, purpose, _at(TOKEN_HOURS[purpose] * 3600)))
    return token


def public(row) -> dict:
    return {"id": row["id"], "email": row["email"], "verified": bool(row["email_verified_at"]),
            "role": row["role"], "locked": bool(row["locked_at"]), "email_notify": bool(row["email_notify"])}


def get(account_id: str):
    with db.read() as con:
        return con.execute("SELECT * FROM accounts WHERE id = ? AND deleted_at IS NULL", (account_id,)).fetchone()


# ---------- the owner account on first visit (specs/008 FR-118) ----------
def setup_needed() -> bool:
    with db.read() as con:
        return not con.execute("SELECT 1 FROM accounts WHERE role = 'admin'").fetchone()


def setup(email: str, password: str, ip: str = "") -> dict:
    """Create the first admin, like neb-creative-tool: whoever opens the studio first while it has no admin.
    An email that already has an account (signed up earlier) becomes the owner when its password matches."""
    if not setup_needed():
        raise StudioError("already_set_up", "xưởng đã có tài khoản quản trị", 409)
    ratelimit.hit("setup_ip", ip)
    clean = _clean_email(email)
    with db.read() as con:
        row = con.execute("SELECT * FROM accounts WHERE email = ? AND deleted_at IS NULL", (clean,)).fetchone()
    if row:
        try:
            ok = bool(row["password_hash"]) and _ph.verify(row["password_hash"], password or "")
        except (VerificationError, InvalidHashError):
            ok = False
        if not ok:
            raise StudioError("email_taken_password", "email này đã có tài khoản với mật khẩu khác", 409)
        with db.tx() as con:
            if con.execute("SELECT 1 FROM accounts WHERE role = 'admin'").fetchone():
                raise StudioError("already_set_up", "xưởng đã có tài khoản quản trị", 409)
            con.execute("UPDATE accounts SET role = 'admin', email_verified_at = COALESCE(email_verified_at, ?), "
                        "locked_at = NULL WHERE id = ?", (store.now_iso(), row["id"]))
        return {"id": row["id"], "email": clean}
    try:
        a = signup(clean, password, True, role="admin", verified=True)
        if os.environ.get("STUDIO_OWNER_UNLIMITED") == "1":    # the studio on one machine: the owner pays (specs/014 R4)
            with db.tx() as con:
                con.execute("UPDATE accounts SET quota_films = 1000, quota_learns = 1000 WHERE id = ?", (a["id"],))
        return a
    except StudioError as e:
        if e.code == "admin_exists":          # someone else finished a moment earlier
            raise StudioError("already_set_up", "xưởng đã có tài khoản quản trị", 409)
        raise


# ---------- sign up and verify ----------
def signup(email: str, password: str, accept_terms: bool, ip: str = "", role: str = "customer",
           verified: bool = False) -> dict:
    email = _clean_email(email)
    if role == "customer" and ip:
        ratelimit.hit("signup_ip", ip)
    if not accept_terms:
        raise StudioError("terms_required", "cần đồng ý điều khoản sử dụng", 422)
    _check_password(password)
    aid = jobs.new_id("a")
    with db.tx() as con:
        if con.execute("SELECT 1 FROM accounts WHERE email = ?", (email,)).fetchone():
            raise StudioError("email_taken", "email này đã có tài khoản", 409)
        if role == "admin" and con.execute("SELECT 1 FROM accounts WHERE role = 'admin'").fetchone():
            raise StudioError("admin_exists", "đã có tài khoản quản trị", 409)
        t = store.now_iso()
        con.execute("INSERT INTO accounts (id, email, password_hash, email_verified_at, role, terms_accepted_at,"
                    " created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (aid, email, _ph.hash(password), t if verified else None, role, t, t))
        token = None if verified else _new_token(con, aid, "verify")
    if token:
        mail.queue(email, "verify", {"token": token})
    return {"id": aid, "email": email}


def verify(token: str) -> None:
    with db.tx() as con:
        row = con.execute("SELECT * FROM tokens WHERE token_hash = ? AND purpose = 'verify'", (_hash(token or ""),)).fetchone()
        if not row:
            raise StudioError("not_found", "liên kết không đúng", 404)
        if row["used_at"] or row["expires_at"] < _at():
            raise StudioError("token_expired", "liên kết đã dùng hoặc đã hết hạn", 410)
        con.execute("UPDATE tokens SET used_at = ? WHERE token_hash = ?", (_at(), row["token_hash"]))
        con.execute("UPDATE accounts SET email_verified_at = COALESCE(email_verified_at, ?) WHERE id = ?",
                    (_at(), row["account_id"]))


# ---------- log in ----------
def login(email: str, password: str, ip: str = "") -> str:
    """Returns a new session token (set as a cookie). Wrong email and wrong password give the same answer."""
    email = (email or "").strip().lower()
    ratelimit.hit("login_email", email)
    ratelimit.hit("login_ip", ip)
    with db.read() as con:
        row = con.execute("SELECT * FROM accounts WHERE email = ? AND deleted_at IS NULL", (email,)).fetchone()
    ok = False
    if row:
        try:
            ok = _ph.verify(row["password_hash"], password or "")
        except (VerificationError, InvalidHashError):
            ok = False
    else:
        try:
            _ph.verify(_ph.hash("x" * MIN_PASSWORD), password or "")     # same time whether the email exists or not
        except VerificationError:
            pass
    if not ok:
        raise StudioError("bad_login", "email hoặc mật khẩu không đúng", 401)
    if row["locked_at"]:
        raise StudioError("locked", "tài khoản đã bị khoá", 403)
    token = secrets.token_urlsafe(32)
    with db.tx() as con:
        con.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
                    (_hash(token), row["id"], _at(), _at(SESSION_DAYS * 86400), ip))
        con.execute("UPDATE accounts SET last_login_at = ? WHERE id = ?", (_at(), row["id"]))
    return token


def logout(token: str) -> None:
    with db.tx() as con:
        con.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash(token or ""),))


def current(token: str):
    """The account of a session token, or None. Raises 403 locked for a locked account."""
    if not token:
        return None
    with db.read() as con:
        row = con.execute("SELECT a.* FROM sessions s JOIN accounts a ON a.id = s.account_id "
                          "WHERE s.token_hash = ? AND s.expires_at > ? AND a.deleted_at IS NULL",
                          (_hash(token), _at())).fetchone()
    if row and row["locked_at"]:
        raise StudioError("locked", "tài khoản đã bị khoá", 403)
    return row


# ---------- passwords ----------
def forgot(email: str) -> None:
    """Always quiet (202): never tells whether an email has an account."""
    email = (email or "").strip().lower()
    ratelimit.hit("forgot_email", email)
    with db.tx() as con:
        row = con.execute("SELECT id FROM accounts WHERE email = ? AND deleted_at IS NULL", (email,)).fetchone()
        token = _new_token(con, row["id"], "reset") if row else None
    if token:
        mail.queue(email, "reset", {"token": token})


def reset(token: str, password: str) -> None:
    _check_password(password)
    with db.tx() as con:
        row = con.execute("SELECT * FROM tokens WHERE token_hash = ? AND purpose = 'reset'", (_hash(token or ""),)).fetchone()
        if not row:
            raise StudioError("not_found", "liên kết không đúng", 404)
        if row["used_at"] or row["expires_at"] < _at():
            raise StudioError("token_expired", "liên kết đã dùng hoặc đã hết hạn", 410)
        con.execute("UPDATE tokens SET used_at = ? WHERE token_hash = ?", (_at(), row["token_hash"]))
        con.execute("UPDATE accounts SET password_hash = ? WHERE id = ?", (_ph.hash(password), row["account_id"]))
        con.execute("DELETE FROM sessions WHERE account_id = ?", (row["account_id"],))   # every old session ends


def change(account_id: str, email_notify=None, password=None, old_password=None) -> None:
    row = get(account_id)
    if password is not None:
        try:
            _ph.verify(row["password_hash"], old_password or "")
        except (VerificationError, InvalidHashError):
            raise StudioError("bad_login", "mật khẩu cũ không đúng", 401) from None
        _check_password(password)
    with db.tx() as con:
        if password is not None:
            con.execute("UPDATE accounts SET password_hash = ? WHERE id = ?", (_ph.hash(password), account_id))
        if email_notify is not None:
            con.execute("UPDATE accounts SET email_notify = ? WHERE id = ?", (1 if email_notify else 0, account_id))


def delete(account_id: str, password: str) -> None:
    """Ask for deletion: log out everywhere now; data is removed for good within 30 days (FR-026)."""
    row = get(account_id)
    try:
        _ph.verify(row["password_hash"], password or "")
    except (VerificationError, InvalidHashError):
        raise StudioError("bad_login", "mật khẩu không đúng", 401) from None
    with db.tx() as con:
        con.execute("UPDATE accounts SET deleted_at = ? WHERE id = ?", (_at(), account_id))
        con.execute("DELETE FROM sessions WHERE account_id = ?", (account_id,))
    for j in jobs.all_jobs(account_id):
        if j["status"] not in jobs.FINAL:
            jobs.finish(j["id"], "stopped")
    mail.queue(row["email"], "account_deleted", {})


# ---------- people who can sign in: Settings → Users, like neb-creative-tool (specs/008 FR-111, FR-112) ----------
ROLES = ("admin", "customer")          # shown as Owner and Member


def user_row(con, row) -> dict:
    sessions = con.execute("SELECT count(*) FROM sessions WHERE account_id = ? AND expires_at > ?",
                           (row["id"], _at())).fetchone()[0]
    return {"id": row["id"], "email": row["email"], "role": row["role"], "disabled": bool(row["locked_at"]),
            "created_at": row["created_at"], "last_login_at": row["last_login_at"], "sessions": sessions}


def users() -> list:
    with db.read() as con:
        rows = con.execute("SELECT * FROM accounts WHERE deleted_at IS NULL ORDER BY role = 'customer', created_at").fetchall()
        return [user_row(con, r) for r in rows]


def user(account_id: str) -> dict:
    with db.read() as con:
        row = con.execute("SELECT * FROM accounts WHERE id = ? AND deleted_at IS NULL", (account_id,)).fetchone()
        if not row:
            raise StudioError("not_found", "không có người dùng này", 404)
        return user_row(con, row)


def add_user(email: str, password: str, role: str = "customer") -> dict:
    """The owner adds someone: verified at once, the owner hands over the password."""
    if role not in ROLES:
        raise StudioError("invalid", "vai trò không hợp lệ", 422)
    email = _clean_email(email)
    _check_password(password)
    aid, t = jobs.new_id("a"), store.now_iso()
    with db.tx() as con:
        if con.execute("SELECT 1 FROM accounts WHERE email = ?", (email,)).fetchone():
            raise StudioError("email_taken", "email này đã có tài khoản", 409)
        con.execute("INSERT INTO accounts (id, email, password_hash, email_verified_at, role, terms_accepted_at, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)", (aid, email, _ph.hash(password), t, role, t, t))
    return user(aid)


def _keeps_an_owner(con, account_id: str, role: str, disabled: bool, removed: bool = False) -> bool:
    """Would at least one owner who is switched on remain after this change?"""
    others = con.execute("SELECT count(*) FROM accounts WHERE role = 'admin' AND locked_at IS NULL AND deleted_at IS NULL "
                         "AND id != ?", (account_id,)).fetchone()[0]
    return others > 0 or (not removed and role == "admin" and not disabled)


def update_user(account_id: str, by: str, role: str = None, disabled: bool = None, password: str = None) -> dict:
    row = get(account_id)
    if not row:
        raise StudioError("not_found", "không có người dùng này", 404)
    if role is not None and role not in ROLES:
        raise StudioError("invalid", "vai trò không hợp lệ", 422)
    if password is not None:
        _check_password(password)
    if account_id == by and ((role is not None and role != row["role"]) or disabled):
        raise StudioError("self", "không tự đổi vai trò hay tự tắt tài khoản của mình", 409)
    new_role = row["role"] if role is None else role
    new_off = bool(row["locked_at"]) if disabled is None else disabled
    with db.tx() as con:
        if not _keeps_an_owner(con, account_id, new_role, new_off):
            raise StudioError("last_owner", "xưởng cần ít nhất một Owner đang bật", 409)
        if role is not None:
            con.execute("UPDATE accounts SET role = ? WHERE id = ?", (role, account_id))
        if disabled is not None:
            con.execute("UPDATE accounts SET locked_at = ? WHERE id = ?", (_at() if disabled else None, account_id))
        if password is not None:
            con.execute("UPDATE accounts SET password_hash = ? WHERE id = ?", (_ph.hash(password), account_id))
        if disabled or password is not None:
            con.execute("DELETE FROM sessions WHERE account_id = ?", (account_id,))
    if disabled:                             # stop what runs now, as locking did in 007
        for j in jobs.all_jobs(account_id):
            if j["status"] not in jobs.FINAL:
                try:
                    jobs.finish(j["id"], "stopped", error="Stopped: the account was turned off by the studio")
                except StudioError:
                    pass
    return user(account_id)


def signout_all(account_id: str) -> None:
    if not get(account_id):
        raise StudioError("not_found", "không có người dùng này", 404)
    with db.tx() as con:
        con.execute("DELETE FROM sessions WHERE account_id = ?", (account_id,))


def remove_user(account_id: str, by: str) -> None:
    """Like deleting one's own account in 007: signed out now, data erased within 30 days."""
    row = get(account_id)
    if not row:
        raise StudioError("not_found", "không có người dùng này", 404)
    if account_id == by:
        raise StudioError("self", "không tự xoá tài khoản của mình ở đây", 409)
    with db.tx() as con:
        if not _keeps_an_owner(con, account_id, row["role"], bool(row["locked_at"]), removed=True):
            raise StudioError("last_owner", "xưởng cần ít nhất một Owner đang bật", 409)
        con.execute("UPDATE accounts SET deleted_at = ? WHERE id = ?", (_at(), account_id))
        con.execute("DELETE FROM sessions WHERE account_id = ?", (account_id,))
    for j in jobs.all_jobs(account_id):
        if j["status"] not in jobs.FINAL:
            jobs.finish(j["id"], "stopped")
