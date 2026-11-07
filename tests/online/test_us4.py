"""User story 4: customers manage their own account and data (specs/007 tasks T038)."""
import datetime as dt
import unittest

from helpers import PASSWORD, TMP, W, Studio, account_id, film_job
from test_us2 import learn_job, upload

NEW = "another long password"


class US4(unittest.TestCase):
    def setUp(self):
        self.s = Studio()
        self.c = self.s.signup_verified("me@example.com")
        self.aid = account_id(self.c)

    def tearDown(self):
        self.s.close()

    def login(self, password):
        return self.s.client().post("/api/v1/auth/login", json={"email": "me@example.com", "password": password}, headers=W)

    def test_us4_change_password(self):
        r = self.c.put("/api/v1/me", json={"password": NEW, "old_password": "wrong one!!"}, headers=W)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (401, "bad_login"))
        self.assertEqual(self.c.put("/api/v1/me", json={"password": "short", "old_password": PASSWORD},
                                    headers=W).json()["error"]["code"], "weak_password")
        self.assertEqual(self.c.put("/api/v1/me", json={"password": NEW, "old_password": PASSWORD}, headers=W).status_code, 200)
        self.assertEqual(self.login(PASSWORD).status_code, 401)
        self.assertEqual(self.login(NEW).status_code, 200)

    def test_us4_email_switch(self):
        r = self.c.put("/api/v1/me", json={"email_notify": False}, headers=W)
        self.assertFalse(r.json()["email_notify"])
        jid = film_job(self.c).json()["id"]
        self.s.start()
        self.assertEqual(self.s.wait(jid)["status"], "done")
        self.assertFalse(any("Your job is ready" in p.read_text() for p in self.s.flush_mail()))

    def test_us4_delete_account_then_erase(self):
        from studio import db, store
        # some data of every kind: a done film, a learn job with a rights record, an upload, a review
        film = film_job(self.c).json()["id"]
        self.s.start()
        self.assertEqual(self.s.wait(film)["status"], "done")
        learn = learn_job(self.c, source="youtube", channel="@some-channel", count=1, rights_confirmed=True).json()["id"]
        self.s.wait(learn, statuses=("waiting_review",))
        upload(self.c, TMP / "good.mp4")
        other = self.s.signup_verified("keep@example.com")
        keep = film_job(other).json()["id"]
        # wrong password: nothing happens
        self.assertEqual(self.c.request("DELETE", "/api/v1/me", json={"password": "wrong one!!"}, headers=W).status_code, 401)
        r = self.c.request("DELETE", "/api/v1/me", json={"password": PASSWORD}, headers=W)
        self.assertEqual(r.status_code, 202)
        self.assertEqual(self.c.get("/api/v1/me").status_code, 401)               # logged out at once
        self.assertEqual(self.login(PASSWORD).status_code, 401)
        from studio import jobs
        self.assertEqual(jobs.load(learn)["status"], "stopped")
        self.assertTrue(any("being deleted" in p.read_text() for p in self.s.flush_mail()))
        # within 30 days nothing is erased yet
        self.s.worker.clean()
        self.assertTrue(store.account_dir(self.aid).exists())
        # 31 days later
        old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=31)).isoformat(timespec="seconds")
        with db.tx() as con:
            con.execute("UPDATE accounts SET deleted_at = ? WHERE id = ?", (old, self.aid))
        self.s.worker.clean()
        with db.read() as con:
            for table, col in (("accounts", "id"), ("sessions", "account_id"), ("tokens", "account_id"),
                               ("rights", "account_id"), ("usage_day", "account_id"), ("docs", "owner")):
                n = con.execute(f"SELECT count(*) FROM {table} WHERE {col} = ?", (self.aid,)).fetchone()[0]
                self.assertEqual(n, 0, table)
            n = con.execute('SELECT count(*) FROM outbox WHERE "to" = ?', ("me@example.com",)).fetchone()[0]
            self.assertEqual(n, 0)
            kept = con.execute("SELECT sum(jobs) FROM usage_day WHERE account_id = 'deleted'").fetchone()[0]
        self.assertEqual(kept, 2)                                   # the studio's daily totals stay, anonymous
        for d in (store.account_dir(self.aid), self.s.data / "uploads" / self.aid, self.s.data / "jobs" / film,
                  self.s.data / "jobs" / learn):
            self.assertFalse(d.exists(), d)
        self.assertEqual(jobs.load(keep)["owner"], account_id(other))            # other customers untouched
        # the email can sign up again
        r = self.s.client().post("/api/v1/auth/signup", json={"email": "me@example.com", "password": PASSWORD,
                                                               "accept_terms": True}, headers=W)
        self.assertEqual(r.status_code, 201)


if __name__ == "__main__":
    unittest.main()


NODE_MODULES = __import__("helpers").REPO / "lib" / "lemo-opuscar" / "node_modules"


@unittest.skipUnless(__import__("shutil").which("node") and (NODE_MODULES / "playwright-core").is_dir(),
                     "needs node and playwright-core")
class AccountBrowser(unittest.TestCase):
    setUp, tearDown = US4.setUp, US4.tearDown

    def test_us4_account_page(self):
        import json
        import os
        import subprocess
        from pathlib import Path
        from helpers import Server
        from studio import db
        from studio.server import create_app
        web = Server(create_app())
        try:
            r = subprocess.run(["node", str(Path(__file__).with_name("browser_account.cjs")), web.url, "me@example.com",
                                PASSWORD, NEW], capture_output=True, text=True, timeout=90,
                               env={**os.environ, "NODE_PATH": str(NODE_MODULES)})
            if r.returncode == 77:
                self.skipTest("cannot start a browser")
            self.assertEqual(r.returncode, 0, r.stderr)
            res = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertEqual(res["errors"], [])
            self.assertLessEqual(res["wide"], 360)
            with db.read() as con:
                row = con.execute("SELECT email_notify, deleted_at FROM accounts WHERE id = ?", (self.aid,)).fetchone()
            self.assertEqual(row["email_notify"], 0)
            self.assertTrue(row["deleted_at"])
        finally:
            web.close()
