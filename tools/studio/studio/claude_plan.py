"""Claude Pro/Max accounts signed in on the admin page (specs/008-claude-plan-login).

Each account is a slot 1…5 with its own Claude Code config folder `$STUDIO_DATA/claude/slot-<n>` (mode 700).
The sign-in itself lives in that folder; the database only keeps what the admin page shows (data-model).
Every Claude Code command on a slot runs under that slot's file lock, so sign-in, status and refresh never overlap.

Sign-in follows neb-creative-tool (lib/claudeCode/auth.ts) with what T001 found on the real Claude Code:
the code must be typed into a terminal (a pty), and the URL is printed inside a terminal hyperlink."""
import contextlib
import datetime as dt
import fcntl
import json
import math
import os
import pty
import re
import subprocess
import threading
import time
from pathlib import Path

from . import db, store
from .store import StudioError

SLOTS = range(1, 6)
PLANS_OK = ("pro", "max")
WINDOW_S = 5 * 3600                     # the short limit window of a plan (research R4)
URL_RE = re.compile(r"https://\S+/oauth/authorize\?\S+")
TERM_CODES = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b\[[0-9;?]*[A-Za-z]")
DROP_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_BASE_URL")


def claude_bin() -> str:
    """The Claude Code binary: STUDIO_CLAUDE_BIN if set (tests use a fake), else the one bundled with claude-agent-sdk."""
    if os.environ.get("STUDIO_CLAUDE_BIN"):
        return os.environ["STUDIO_CLAUDE_BIN"]
    import claude_agent_sdk
    path = Path(claude_agent_sdk.__file__).parent / "_bundled" / "claude"
    if not path.is_file():
        raise FileNotFoundError(f"Claude Code not found at {path}; run: sh bin/studio deps online")
    return str(path)


# ---------- folders, locks, running Claude Code ----------
def base_dir() -> Path:
    d = db.data_dir() / "claude"
    d.mkdir(mode=0o700, exist_ok=True)
    os.chmod(d, 0o700)
    return d


def config_dir(slot: int) -> Path:
    d = base_dir() / f"slot-{int(slot)}"
    d.mkdir(mode=0o700, exist_ok=True)
    os.chmod(d, 0o700)
    return d


class Busy(Exception):
    """The slot's lock was not free in time (a sign-in may hold it for minutes)."""


@contextlib.contextmanager
def lock(slot: int, wait: float = None):
    """The slot's file lock (contracts/runner.md), shared by web and proxy processes.
    wait=None blocks; otherwise raise Busy after `wait` seconds."""
    with open(base_dir() / f"slot-{int(slot)}.lock", "a") as f:
        if wait is None:
            fcntl.flock(f, fcntl.LOCK_EX)
        else:
            end = time.time() + wait
            while True:
                try:
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.time() >= end:
                        raise Busy(slot) from None
                    time.sleep(0.05)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def env(slot: int) -> dict:
    """Claude Code's environment for a slot: its own config folder, never an API key, no browser."""
    e = {k: v for k, v in os.environ.items() if k not in DROP_ENV}
    e.update(CLAUDE_CONFIG_DIR=str(config_dir(slot)), BROWSER="/bin/false")
    if e.get("HOME"):
        os.makedirs(e["HOME"], exist_ok=True)        # compose points HOME at /tmp/home, a fresh tmpfs
    return e


def run(slot: int, args: list, timeout: float = 60, input: str = None, cwd: str = None,
        wait: float = None) -> subprocess.CompletedProcess:
    with lock(slot, wait):
        return subprocess.run([claude_bin(), *args], env=env(slot), capture_output=True, text=True, timeout=timeout,
                              input=input, stdin=None if input is not None else subprocess.DEVNULL, cwd=cwd)


def clean(text: str) -> str:
    """Terminal output without escape codes and without anything long enough to be a code or a token."""
    text = TERM_CODES.sub("", text or "").replace("\r", "")
    return re.sub(r"\S{24,}", "[…]", text)


# ---------- rows ----------
def _row(con, slot: int):
    return con.execute("SELECT * FROM claude_account WHERE slot = ?", (slot,)).fetchone()


def _need(slot: int):
    with db.read() as con:
        r = _row(con, slot)
    if not r:
        raise StudioError("not_found", "không có tài khoản Claude này", 404)
    return r


def _iso(t: float) -> str:
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat(timespec="seconds")


def _ts(iso):
    return dt.datetime.fromisoformat(iso).timestamp() if iso else None


def status(slot: int) -> dict:
    """Read `auth status --json` and store email, plan and state. Returns the stored row as a dict.
    A slot that is signing in right now is left alone (its lock is held by the login)."""
    _need(slot)
    if (pending() or {}).get("slot") == slot:
        return public(slot)
    try:
        p = run(slot, ["auth", "status", "--json"], timeout=60)
        info = json.loads(p.stdout or "{}")
    except (subprocess.TimeoutExpired, ValueError):
        info = None
    with db.tx() as con:
        r = _row(con, slot)
        state = r["state"]
        if info is None:
            pass                                             # could not read it; keep what we knew
        elif info.get("loggedIn"):
            email = info.get("email") or info.get("emailAddress") or (info.get("account") or {}).get("email")
            plan = info.get("subscriptionType") or info.get("plan")
            state = "signed_in" if state in ("signed_out", "needs_signin") else state
            con.execute("UPDATE claude_account SET email = ?, plan = ?, state = ? WHERE slot = ?",
                        (email, plan.lower() if isinstance(plan, str) else None, state, slot))
        else:
            state = "signed_out" if state == "signed_out" else "needs_signin"
            con.execute("UPDATE claude_account SET state = ? WHERE slot = ?", (state, slot))
        con.execute("UPDATE claude_account SET checked_at = ? WHERE slot = ?", (store.now_iso(), slot))
    return public(slot)


def tokens_5h(con, slot: int, now: float = None) -> int:
    since = _iso((now or store.clock()) - WINDOW_S)
    return con.execute("SELECT coalesce(sum(tokens_in + tokens_out + cache_write + cache_read), 0) FROM call "
                       "WHERE via = ? AND at >= ?", (f"plan:{slot}", since)).fetchone()[0]


def accounts(now: float = None) -> list:
    """Every slot as the admin page shows it (contracts: ClaudeAccount)."""
    with db.read() as con:
        rows = con.execute("SELECT * FROM claude_account ORDER BY slot").fetchall()
        out, seen = [], {}
        for r in rows:
            email = r["email"] if r["state"] != "signed_out" else None
            same = seen.get(email) if email else None
            if email and email not in seen:
                seen[email] = r["slot"]
            out.append({"slot": r["slot"], "email": email, "plan": r["plan"] if email else None, "state": r["state"],
                        "rest_until": r["rest_until"] if r["state"] == "limited" else None, "same_as": same,
                        "plan_warning": bool(email and r["plan"] and r["plan"] not in PLANS_OK),
                        "tokens_5h": tokens_5h(con, r["slot"], now),
                        "usage": json.loads(r["usage"]) if email and r["usage"] else None})
    return out


def public(slot: int) -> dict:
    return next(a for a in accounts() if a["slot"] == slot)


def usable(now: float = None) -> list:
    """Slots a call may use: signed in (or rested), not a duplicate; least tokens in 5 hours first (research R4)."""
    now = now or store.clock()
    ok = [a for a in accounts(now) if a["same_as"] is None and (
        a["state"] == "signed_in" or (a["state"] == "limited" and (_ts(a["rest_until"]) or 0) <= now))]
    return [a["slot"] for a in sorted(ok, key=lambda a: (a["tokens_5h"], a["slot"]))]


def api_key() -> bool:
    """A fallback API key is set (the worker only learns that it is, via STUDIO_API_KEY_SET)."""
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("STUDIO_API_KEY_SET"))


def ready() -> bool:
    """Jobs can run: a usable Claude account, or the fallback API key (FR-110)."""
    return bool(usable()) or api_key()


# ---------- adding and removing accounts ----------
def add_account() -> dict:
    with db.tx() as con:
        taken = {r[0] for r in con.execute("SELECT slot FROM claude_account")}
        free = [s for s in SLOTS if s >= 2 and s not in taken]
        if not free:
            raise StudioError("max_accounts", "đã đủ 5 tài khoản Claude", 409)
        con.execute("INSERT INTO claude_account (slot) VALUES (?)", (free[0],))
    return public(free[0])


def remove_account(slot: int) -> None:
    if slot == 1:
        raise StudioError("first_account", "không xoá được tài khoản đầu tiên", 409)
    _need(slot)
    cancel_login(slot)
    logout(slot)
    import shutil
    with lock(slot):
        shutil.rmtree(config_dir(slot), ignore_errors=True)
    with db.tx() as con:
        con.execute("DELETE FROM claude_account WHERE slot = ?", (slot,))


def logout(slot: int) -> dict:
    _need(slot)
    cancel_login(slot)
    try:
        run(slot, ["auth", "logout"], timeout=60)
    except subprocess.TimeoutExpired:
        pass
    cred = config_dir(slot) / ".credentials.json"
    with lock(slot):
        cred.unlink(missing_ok=True)                       # gone even if Claude Code could not reach the server
    with db.tx() as con:
        con.execute("UPDATE claude_account SET state = 'signed_out', email = NULL, plan = NULL, rest_until = NULL, "
                    "rest_step = 0, signin_mailed_at = NULL WHERE slot = ?", (slot,))
    return public(slot)


# ---------- signing in (research R1; one at a time, only in this web process) ----------
class Login:
    def __init__(self, slot: int):
        self.slot, self.started_at, self.url = slot, store.now_iso(), None
        self.out, self.done = "", threading.Event()
        self._lockf = open(base_dir() / f"slot-{slot}.lock", "a")
        fcntl.flock(self._lockf, fcntl.LOCK_EX)              # held until the login ends
        self.master, slave = pty.openpty()
        try:
            self.proc = subprocess.Popen([claude_bin(), "auth", "login", "--claudeai"], env=env(slot),
                                         stdin=slave, stdout=slave, stderr=slave, start_new_session=True, close_fds=True)
        except Exception:
            os.close(self.master)
            self._unlock()
            raise
        finally:
            os.close(slave)
        threading.Thread(target=self._read, daemon=True).start()
        ttl = float(os.environ.get("STUDIO_CLAUDE_LOGIN_TTL", "600"))
        self.timer = threading.Timer(ttl, lambda: cancel_login(slot, self))
        self.timer.daemon = True
        self.timer.start()

    def _read(self):
        while True:
            try:
                data = os.read(self.master, 4096)
            except OSError:
                break
            if not data:
                break
            self.out += data.decode(errors="replace")
            if not self.url:
                m = URL_RE.search(TERM_CODES.sub("", self.out))
                if m:
                    self.url = m.group(0)
        self.done.set()

    def wait_url(self, timeout: float) -> str:
        end = time.time() + timeout
        while time.time() < end and not self.url and self.proc.poll() is None:
            time.sleep(0.05)
        return self.url

    def send(self, code: str) -> int:
        os.write(self.master, (code.strip() + "\r").encode())
        try:
            return self.proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            return -1

    def stop(self):
        self.timer.cancel()
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(5)
        with contextlib.suppress(OSError):
            os.close(self.master)
        self._unlock()

    def _unlock(self):
        with contextlib.suppress(OSError, ValueError):
            fcntl.flock(self._lockf, fcntl.LOCK_UN)
            self._lockf.close()


_login = None
_login_mutex = threading.Lock()


def pending():
    """The login waiting for a code: {slot, url, started_at} or None."""
    lg = _login
    return {"slot": lg.slot, "url": lg.url, "started_at": lg.started_at} if lg else None


def cancel_login(slot: int = None, which: Login = None) -> None:
    global _login
    with _login_mutex:
        lg = _login
        if not lg or (slot is not None and lg.slot != slot) or (which is not None and lg is not which):
            return
        _login = None
    lg.stop()


def start_login(slot: int) -> dict:
    """Start `auth login --claudeai` for a slot and return the URL to open (FR-101). Cancels any other login."""
    global _login
    _need(slot)
    cancel_login()
    lg = Login(slot)
    url = lg.wait_url(30)
    if not url:
        tail = clean(lg.out)[-200:]
        lg.stop()
        raise StudioError("login_failed", f"Claude Code did not give a sign-in link. {tail}".strip(), 502)
    with _login_mutex:
        _login = lg
    return {"slot": slot, "url": url}


def submit_code(slot: int, code: str) -> dict:
    """Type the code the admin pasted into the waiting login. Success: the account is signed in."""
    global _login
    with _login_mutex:
        lg = _login if _login and _login.slot == slot else None
        if lg:
            _login = None
    if not lg:
        raise StudioError("no_login", "không có lần đăng nhập nào đang chờ cho tài khoản này", 409)
    try:
        rc = lg.send(code)
    finally:
        lg.stop()
    if rc != 0:
        msg = "That code was not accepted. Sign in again to get a new link." if rc > 0 else \
            "Claude Code did not finish signing in. Sign in again."
        raise StudioError("bad_code", msg, 422)
    with db.tx() as con:
        con.execute("UPDATE claude_account SET state = 'signed_in', rest_until = NULL, rest_step = 0, "
                    "signin_mailed_at = NULL WHERE slot = ?", (slot,))
    return status(slot)


def refresh_all() -> list:
    for a in accounts():
        if a["state"] != "signed_out":
            status(a["slot"])
    return accounts()


# ---------- calls through a plan (research R2, R5; T001 results) ----------
REFRESH_BEFORE_S = 300          # Claude Code's `auth status` refreshes the access token under about 5 minutes (T001)
BACKOFF_MAX_S = 300


def _credentials(slot: int):
    """claudeAiOauth of the slot's .credentials.json, or None. Never logged."""
    f = config_dir(slot) / ".credentials.json"
    for _ in range(3):                       # Claude Code may be rewriting it right now
        try:
            o = json.loads(f.read_text()).get("claudeAiOauth") or {}
            return o if o.get("accessToken") else None
        except FileNotFoundError:
            return None
        except (ValueError, OSError):
            time.sleep(0.05)
    return None


def _left(o) -> float:
    return (o.get("expiresAt") or 0) / 1000 - time.time() if o else -1


def access_token(slot: int, force: bool = False, wait: float = 20):
    """The slot's access token, refreshed through Claude Code when it has under 5 minutes left
    (or when `force`, after a 401). None when it cannot be had: the account needs signing in again."""
    o = _credentials(slot)
    if o and not force and _left(o) > REFRESH_BEFORE_S:
        return o["accessToken"]
    try:
        with lock(slot, wait):
            o = _credentials(slot)
            if o and not force and _left(o) > REFRESH_BEFORE_S:
                return o["accessToken"]          # another process refreshed it while we waited
            old = o["accessToken"] if o else None
            if o and force:                      # make Claude Code's own refresh run now
                f = config_dir(slot) / ".credentials.json"
                data = json.loads(f.read_text())
                data["claudeAiOauth"]["expiresAt"] = int((time.time() + 60) * 1000)
                tmp = f.with_name(".credentials.json.tmp")
                fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "w") as out:
                    json.dump(data, out)
                os.replace(tmp, f)
            try:
                subprocess.run([claude_bin(), "auth", "status", "--json"], env=env(slot), capture_output=True,
                               text=True, timeout=60, stdin=subprocess.DEVNULL)
            except subprocess.TimeoutExpired:
                pass
            o = _credentials(slot)
    except Busy:
        o = _credentials(slot)
        return o["accessToken"] if o and _left(o) > 0 and not force else None
    if not o or _left(o) <= 0 or (force and o["accessToken"] == old):
        return None
    return o["accessToken"]


def mark_ok(slot: int) -> None:
    with db.tx() as con:
        con.execute("UPDATE claude_account SET state = 'signed_in', rest_until = NULL, rest_step = 0 "
                    "WHERE slot = ? AND (state = 'limited' OR rest_step != 0)", (slot,))


def mark_limited(slot: int, reset_at: float = None) -> str:
    """The plan said 429: rest until its reset time, or back off 2 s → 4 s → … → 5 minutes. Returns rest_until."""
    with db.tx() as con:
        r = _row(con, slot)
        step = r["rest_step"] if r else 0
        if reset_at and reset_at > time.time():
            until, step = reset_at, step
        else:
            step += 1
            until = time.time() + min(BACKOFF_MAX_S, 2 ** step)
        until = math.ceil(until)                 # stored to the second: never call back before the reset
        con.execute("UPDATE claude_account SET state = 'limited', rest_until = ?, rest_step = ? "
                    "WHERE slot = ? AND state IN ('signed_in', 'limited')", (_iso(until), step, slot))
    return _iso(until)


def mark_needs_signin(slot: int) -> None:
    """Its sign-in stopped working (FR-109): skip it, and mail the owners once."""
    from . import mail
    with db.tx() as con:
        r = _row(con, slot)
        if not r:
            return
        con.execute("UPDATE claude_account SET state = 'needs_signin' WHERE slot = ? AND state != 'signed_out'", (slot,))
        send = r["signin_mailed_at"] is None and r["state"] != "signed_out"
        if send:
            con.execute("UPDATE claude_account SET signin_mailed_at = ? WHERE slot = ?", (store.now_iso(), slot))
        owners = [x[0] for x in con.execute("SELECT email FROM accounts WHERE role = 'admin' AND locked_at IS NULL "
                                            "AND deleted_at IS NULL")] if send else []
    for to in owners:
        mail.queue(to, "claude_signin", {"slot": slot, "email": r["email"] or f"slot {slot}"})


def _window(headers, name: str):
    try:
        u = float(headers.get(f"anthropic-ratelimit-unified-{name}-utilization"))
    except (TypeError, ValueError):
        u = None
    try:
        reset = _iso(float(headers.get(f"anthropic-ratelimit-unified-{name}-reset")))
    except (TypeError, ValueError, OverflowError, OSError):
        reset = None
    return None if u is None and reset is None else {"percent": None if u is None else round(u * 100, 1), "resets_at": reset}


def note_usage(slot: int, headers) -> None:
    """The plan's 5-hour and weekly windows from a response's rate-limit headers (FR-119, T001 R5)."""
    five, week = _window(headers, "5h"), _window(headers, "7d")
    if not five and not week:
        return
    with db.tx() as con:
        con.execute("UPDATE claude_account SET usage = ? WHERE slot = ?",
                    (json.dumps({"five_hour": five, "seven_day": week, "at": store.now_iso()}), slot))


def reset_at(headers):
    """When a plan that answered 429 can be used again (unix seconds), from its headers."""
    for k in ("anthropic-ratelimit-unified-reset", "anthropic-ratelimit-unified-5h-reset"):
        try:
            return float(headers.get(k))
        except (TypeError, ValueError):
            continue
    try:
        return time.time() + float(headers.get("retry-after"))
    except (TypeError, ValueError):
        return None


def next_free(now: float = None):
    """(slot, time) of the limited account that rests the shortest, or None."""
    now = now or store.clock()
    rest = [(_ts(a["rest_until"]), a["slot"], a["rest_until"]) for a in accounts(now)
            if a["state"] == "limited" and a["rest_until"] and a["same_as"] is None]
    if not rest:
        return None
    _, slot, iso = min(rest)
    return slot, iso
