"""Jobs, reviews and decisions in SQLite (T005); phase-1 behaviour is covered by tests/ui."""
import threading
import unittest

from helpers import OnlineProject


class StoreOnline(unittest.TestCase):
    def setUp(self):
        self.p = OnlineProject()
        from studio import jobs, reviews, store
        self.jobs, self.reviews, self.store = jobs, reviews, store

    def tearDown(self):
        self.p.close()

    def test_jobs_live_in_the_database_with_an_owner(self):
        j = self.jobs.create("film", "demo", owner="a-1", status="queued")
        self.assertEqual((j["status"], j["step"], j["charged"], j["cost_usd"]), ("queued", "Queued", False, 0.0))
        self.assertFalse((self.p.dir / ".studio" / "jobs" / f"{j['id']}.json").exists())     # not a file
        self.assertTrue((self.p.data / "studio.db").exists())
        self.jobs.step(j["id"], "Music")
        self.assertEqual(self.jobs.load(j["id"])["step"], "Music")
        with self.assertRaises(self.store.StudioError):
            self.jobs.load(j["id"], owner="a-2")                                            # someone else's
        self.jobs.create("film", "other", owner="a-2", status="queued")
        self.assertEqual([x["name"] for x in self.jobs.all_jobs("a-1")], ["demo"])
        self.assertEqual(len(self.jobs.all_jobs()), 2)

    def test_first_decision_wins_across_threads(self):
        j = self.jobs.create("learn", "demo", owner="a-1")
        r = self.reviews.create(j["id"], "style-1", "demo-set", "# Summary")
        self.assertEqual(r["owner"], "a-1")
        won, lost = [], []

        def go(v):
            try:
                won.append(self.reviews.decide(r["id"], v, "darker please" if v == "revise" else None))
            except self.store.StudioError as e:
                lost.append(e.code)
        ts = [threading.Thread(target=go, args=(v,)) for v in ("approve", "revise") * 4]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual((len(won), set(lost)), (1, {"already_decided"}))
        self.assertEqual(self.reviews.load(r["id"])["decision"]["value"], won[0]["value"])
        self.assertNotIn("owner", self.reviews.load(r["id"])["decision"])
        self.assertEqual(len(self.reviews.all_reviews("decided", "a-1")), 1)
        self.assertEqual(self.reviews.all_reviews(owner="a-2"), [])

    def test_versions_change_when_a_job_changes(self):
        j = self.jobs.create("film", "demo", owner="a-1", status="queued")
        before = self.store.doc_versions("a-1")
        self.jobs.step(j["id"], "Look")
        after = self.store.doc_versions("a-1")
        self.assertNotEqual(before[f"{j['id']}.json"], after[f"{j['id']}.json"])
        self.assertEqual(self.store.doc_versions("a-2"), {})


V1 = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
INSERT INTO meta VALUES ('schema', '1');
CREATE TABLE accounts (
  id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE CHECK (length(email) <= 254 AND email = lower(email)),
  password_hash TEXT NOT NULL, email_verified_at TEXT,
  role TEXT NOT NULL DEFAULT 'customer' CHECK (role IN ('customer', 'admin')), locked_at TEXT,
  quota_films INTEGER, quota_learns INTEGER, email_notify INTEGER NOT NULL DEFAULT 1,
  terms_accepted_at TEXT NOT NULL, created_at TEXT NOT NULL, deleted_at TEXT);
CREATE TABLE sessions (token_hash TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL, expires_at TEXT NOT NULL, ip TEXT);
CREATE TABLE tokens (token_hash TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  purpose TEXT NOT NULL CHECK (purpose IN ('verify', 'reset')), expires_at TEXT NOT NULL, used_at TEXT);
CREATE TABLE outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, "to" TEXT NOT NULL,
  template TEXT NOT NULL CHECK (template IN ('verify', 'reset', 'job_done', 'job_failed', 'review_needed',
                                             'review_timeout', 'account_deleted')),
  data TEXT NOT NULL, created_at TEXT NOT NULL, sent_at TEXT, tries INTEGER NOT NULL DEFAULT 0, last_error TEXT);
CREATE TABLE settings (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL);
INSERT INTO settings VALUES (1, '{"signup_open": false, "concurrency": 3}');
INSERT INTO accounts VALUES ('a-1', 'old@x.test', 'hash', '2026-11-01', 'customer', NULL, 5, NULL, 1,
                             '2026-11-01', '2026-11-01', NULL);
INSERT INTO sessions VALUES ('s-1', 'a-1', '2026-11-01', '2099-01-01', '');
INSERT INTO tokens VALUES ('t-1', 'a-1', 'reset', '2099-01-01', NULL);
INSERT INTO outbox ("to", template, data, created_at) VALUES ('old@x.test', 'verify', '{}', '2026-11-01');
"""


class Upgrade(unittest.TestCase):
    """A 007 database (schema 1) opens under 008: rows stay, the new tables and constraints are there (FR-113)."""

    def setUp(self):
        self.p = OnlineProject()

    def tearDown(self):
        self.p.close()

    def test_007_database_is_upgraded_in_place(self):
        import sqlite3
        con = sqlite3.connect(self.p.data / "studio.db")
        con.executescript(V1)
        con.close()
        from studio import db
        with db.read() as c:
            self.assertEqual(c.execute("SELECT value FROM meta WHERE key = 'schema'").fetchone()[0], "2")
            a = c.execute("SELECT * FROM accounts WHERE id = 'a-1'").fetchone()
            self.assertEqual((a["email"], a["password_hash"], a["quota_films"]), ("old@x.test", "hash", 5))
            self.assertEqual(c.execute("SELECT count(*) FROM sessions").fetchone()[0], 1)
            self.assertEqual(c.execute("SELECT count(*) FROM outbox").fetchone()[0], 1)
            self.assertEqual([tuple(r) for r in c.execute("SELECT slot, state FROM claude_account")], [(1, "signed_out")])
            self.assertEqual(c.execute("PRAGMA foreign_key_check").fetchall(), [])
        with db.tx() as c:            # the new constraints hold
            c.execute("INSERT INTO accounts (id, email, terms_accepted_at, created_at) VALUES ('a-2', 'new@x.test', 't', 't')")
            c.execute("INSERT INTO tokens VALUES ('t-2', 'a-2', 'invite', '2099-01-01', NULL)")
            c.execute("""INSERT INTO outbox ("to", template, data, created_at) VALUES ('a@x.test', 'claude_signin', '{}', 't')""")
            c.execute("INSERT INTO call (via, at) VALUES ('plan:1', 't')")
        with db.tx() as c:            # foreign keys still cascade after the rebuild
            c.execute("DELETE FROM accounts WHERE id = 'a-1'")
        with db.read() as c:
            self.assertEqual(c.execute("SELECT count(*) FROM sessions").fetchone()[0], 0)
        s = db.settings()
        self.assertEqual((s["signup_open"], s["concurrency"], s["job_token_cap"]), (False, 3, 40_000_000))


if __name__ == "__main__":
    unittest.main()
