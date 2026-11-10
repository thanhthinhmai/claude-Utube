"""Sliding-window rate limits in SQLite (specs/007 FR-025)."""
from . import db, store
from .store import StudioError

# kind: (max hits, window seconds)
LIMITS = {
    "signup_ip": (5, 3600),
    "setup_ip": (10, 900),
    "login_email": (10, 900),
    "login_ip": (10, 900),
    "forgot_email": (3, 3600),
    "job_account": (20, 3600),
}


def hit(kind: str, key: str, limit: int = None, window: float = None) -> None:
    """Count one hit; raise 429 rate_limited (with retry_after) when the window is full.
    `limit` and `window` override LIMITS[kind] (an API token's own rate per minute, specs/009)."""
    d_limit, d_window = LIMITS.get(kind, (60, 60))
    limit, window = limit or d_limit, window or d_window
    k, now = f"{kind}:{(key or '').lower()}", store.clock()
    with db.tx() as con:
        con.execute("DELETE FROM ratelimit WHERE key = ? AND at <= ?", (k, now - window))
        rows = [r[0] for r in con.execute("SELECT at FROM ratelimit WHERE key = ? ORDER BY at", (k,))]
        if len(rows) >= limit:
            e = StudioError("rate_limited", "quá nhiều lần thử, hãy thử lại sau", 429)
            e.retry_after = max(1, int(rows[0] + window - now) + 1)
            raise e
        con.execute("INSERT INTO ratelimit VALUES (?, ?)", (k, now))
