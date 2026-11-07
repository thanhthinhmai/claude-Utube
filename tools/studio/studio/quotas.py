"""Monthly quotas (specs/007 FR-005). Phase 3 adds reserve/refund and cost (tasks T017)."""
import datetime as dt

from . import db, store

VN = dt.timezone(dt.timedelta(hours=7))
KIND_FIELD = {"film": ("quota_films", "quota_films_default"), "learn": ("quota_learns", "quota_learns_default")}


def month_start_vn(now: float = None) -> dt.datetime:
    """00:00 on the 1st of this month, Vietnam time (Clarifications 2026-11-07)."""
    t = dt.datetime.fromtimestamp(store.clock() if now is None else now, VN)
    return t.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def next_reset_vn(now: float = None) -> dt.datetime:
    m = month_start_vn(now)
    return (m.replace(year=m.year + 1, month=1) if m.month == 12 else m.replace(month=m.month + 1))


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
