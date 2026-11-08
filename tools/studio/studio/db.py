"""SQLite store for online mode (specs/007-online-studio data-model.md, research R6).

One file `$STUDIO_DATA/studio.db` in WAL mode. Every change that must stay correct under concurrent requests
(quotas, queue, cost) runs inside `tx()`, which takes the write lock up front (BEGIN IMMEDIATE).
Jobs, reviews and decisions keep the JSON shape of phase 1: they are stored whole in `docs`, with the
columns needed for filtering copied next to them."""
import contextlib
import json
import os
import sqlite3
from pathlib import Path

SCHEMA_VERSION = 2           # 2: Claude plan accounts, calls, invites (specs/008 data-model)

SETTINGS_DEFAULT = {
    "signup_open": True,
    "quota_films_default": 2,
    "quota_learns_default": 1,
    "film_max_seconds": 60,
    "learn_max_videos": 5,
    "upload_max_mb": 500,
    "upload_max_minutes": 20,
    "daily_cost_cap_usd": 20.0,
    "job_cost_cap_usd": 5.0,
    "job_token_cap": 40_000_000,          # specs/008 FR-116
    "concurrency": 2,
    "review_timeout_days": 7,
    "model": "claude-opus-5-5",
    # USD per million tokens: input, output, cache write, cache read
    "price_table": {
        "claude-opus-5-5": {"in": 4.0, "out": 20.0, "cache_write": 5.0, "cache_read": 0.2},
        "claude-sonnet-5-5": {"in": 2.0, "out": 10.0, "cache_write": 2.5, "cache_read": 0.2},
    },
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS accounts (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE CHECK (length(email) <= 254 AND email = lower(email)),
  password_hash TEXT,                      -- null: an invite not used yet (specs/008 R8)
  email_verified_at TEXT,
  role TEXT NOT NULL DEFAULT 'customer' CHECK (role IN ('customer', 'admin')),
  locked_at TEXT,
  quota_films INTEGER,
  quota_learns INTEGER,
  email_notify INTEGER NOT NULL DEFAULT 1,
  terms_accepted_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  deleted_at TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL, expires_at TEXT NOT NULL, ip TEXT
);
CREATE TABLE IF NOT EXISTS tokens (
  token_hash TEXT PRIMARY KEY,
  account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  purpose TEXT NOT NULL CHECK (purpose IN ('verify', 'reset', 'invite')),
  expires_at TEXT NOT NULL, used_at TEXT
);
CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS docs (
  kind TEXT NOT NULL CHECK (kind IN ('job', 'review', 'decision')),
  id TEXT NOT NULL,
  owner TEXT NOT NULL,
  status TEXT,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_ns INTEGER NOT NULL,
  PRIMARY KEY (kind, id)
);
CREATE INDEX IF NOT EXISTS docs_owner ON docs (kind, owner);
CREATE INDEX IF NOT EXISTS docs_status ON docs (kind, status);
CREATE TABLE IF NOT EXISTS rights (
  account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  job_id TEXT NOT NULL, channel_url TEXT NOT NULL, confirmed_at TEXT NOT NULL, text_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS usage_day (
  day TEXT NOT NULL, account_id TEXT NOT NULL, cost_usd REAL NOT NULL DEFAULT 0, jobs INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (day, account_id)
);
CREATE TABLE IF NOT EXISTS outbox (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  "to" TEXT NOT NULL,
  template TEXT NOT NULL CHECK (template IN ('verify', 'reset', 'job_done', 'job_failed', 'review_needed',
                                             'review_timeout', 'account_deleted', 'invite', 'claude_signin')),
  data TEXT NOT NULL, created_at TEXT NOT NULL, sent_at TEXT, tries INTEGER NOT NULL DEFAULT 0, last_error TEXT
);
CREATE TABLE IF NOT EXISTS job_tokens (
  token_hash TEXT PRIMARY KEY, job_id TEXT NOT NULL, created_at TEXT NOT NULL, revoked_at TEXT, last_ok_at REAL
);
CREATE INDEX IF NOT EXISTS job_tokens_job ON job_tokens (job_id);
CREATE TABLE IF NOT EXISTS ratelimit (key TEXT NOT NULL, at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS ratelimit_key ON ratelimit (key, at);
CREATE TABLE IF NOT EXISTS claude_account (
  slot INTEGER PRIMARY KEY CHECK (slot BETWEEN 1 AND 5),
  email TEXT, plan TEXT,
  state TEXT NOT NULL DEFAULT 'signed_out' CHECK (state IN ('signed_out', 'signed_in', 'limited', 'needs_signin')),
  rest_until TEXT, rest_step INTEGER NOT NULL DEFAULT 0, signin_mailed_at TEXT, checked_at TEXT,
  usage TEXT                             -- JSON: the plan's 5-hour and weekly windows (FR-119)
);
INSERT OR IGNORE INTO claude_account (slot) VALUES (1);
CREATE TABLE IF NOT EXISTS call (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT, account_id TEXT, via TEXT NOT NULL, model TEXT,
  tokens_in INTEGER NOT NULL DEFAULT 0, tokens_out INTEGER NOT NULL DEFAULT 0,
  cache_write INTEGER NOT NULL DEFAULT 0, cache_read INTEGER NOT NULL DEFAULT 0,
  cost_usd REAL NOT NULL DEFAULT 0, at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS call_via ON call (via, at);
CREATE INDEX IF NOT EXISTS call_account ON call (account_id, at);
"""


def data_dir() -> Path:
    d = Path(os.environ.get("STUDIO_DATA") or "/data").resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def path() -> Path:
    return data_dir() / "studio.db"


_ready = set()


def connect() -> sqlite3.Connection:
    """A new connection (cheap; one per request or task). Creates and migrates the schema once per file."""
    p = path()
    con = sqlite3.connect(p, timeout=30, isolation_level=None)   # autocommit; tx() opens transactions
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 30000")
    if str(p) not in _ready:
        con.execute("PRAGMA journal_mode = WAL")
        _migrate(con)
        _ready.add(str(p))
    return con


# Tables whose CHECK or NOT NULL changed in version 2: rebuilt from SCHEMA, rows kept (specs/008 FR-113)
REBUILT_V2 = ("accounts", "tokens", "outbox")


def _table_sql(name: str) -> str:
    for stmt in SCHEMA.split(";"):
        if f"CREATE TABLE IF NOT EXISTS {name} (" in stmt:
            return stmt.strip()
    raise KeyError(name)


def _upgrade_to_2(con: sqlite3.Connection) -> None:
    """Version 1 (007) → 2. SQLite cannot change a column's constraints, so each changed table is copied into a
    new one built from SCHEMA, the old one dropped and the copy renamed (the order SQLite documents).
    The caller has turned foreign keys off for this."""
    for name in REBUILT_V2:
        cols = [r[1] for r in con.execute(f'PRAGMA table_info("{name}")')]
        con.execute(_table_sql(name).replace(f"CREATE TABLE IF NOT EXISTS {name} (", f"CREATE TABLE {name}_new (", 1))
        quoted = ", ".join(f'"{c}"' for c in cols)
        con.execute(f'INSERT INTO {name}_new ({quoted}) SELECT {quoted} FROM "{name}"')
        con.execute(f'DROP TABLE "{name}"')
        con.execute(f"ALTER TABLE {name}_new RENAME TO {name}")
    if con.execute("PRAGMA foreign_key_check").fetchall():
        raise RuntimeError("schema upgrade broke a foreign key")


def _migrate(con: sqlite3.Connection) -> None:
    con.execute("PRAGMA foreign_keys = OFF")          # only takes effect outside a transaction
    con.execute("BEGIN IMMEDIATE")
    try:
        row = con.execute("SELECT value FROM meta WHERE key = 'schema'").fetchone() if con.execute(
            "SELECT 1 FROM sqlite_master WHERE name = 'meta'").fetchone() else None
        old = int(row[0]) if row else None             # read under the lock: another process may have upgraded
        if old == 1:
            _upgrade_to_2(con)
        for stmt in [s for s in SCHEMA.split(";") if s.strip()]:
            con.execute(stmt)
        if "usage" not in [r[1] for r in con.execute("PRAGMA table_info(claude_account)")]:
            con.execute("ALTER TABLE claude_account ADD COLUMN usage TEXT")     # early 008 databases
        con.execute("INSERT OR REPLACE INTO meta VALUES ('schema', ?)", (str(SCHEMA_VERSION),))
        con.execute("INSERT OR IGNORE INTO settings VALUES (1, ?)", (json.dumps(SETTINGS_DEFAULT),))
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.execute("PRAGMA foreign_keys = ON")


@contextlib.contextmanager
def tx():
    """A write transaction that holds the lock from the start: read-check-write is safe across processes."""
    con = connect()
    con.execute("BEGIN IMMEDIATE")
    try:
        yield con
        con.execute("COMMIT")
    except BaseException:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()


@contextlib.contextmanager
def read():
    con = connect()
    try:
        yield con
    finally:
        con.close()


def settings() -> dict:
    with read() as con:
        data = json.loads(con.execute("SELECT data FROM settings WHERE id = 1").fetchone()[0])
    return {**SETTINGS_DEFAULT, **data}


def save_settings(data: dict) -> None:
    with tx() as con:
        con.execute("UPDATE settings SET data = ? WHERE id = 1", (json.dumps(data),))
