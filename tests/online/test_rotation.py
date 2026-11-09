"""Several Claude accounts (specs/008 US2): a plan that reaches its limit in the middle of a job hands the rest of
the job to another account (SC-104), and calls spread evenly over the accounts (SC-105)."""
import json
import unittest

from helpers import PASSWORD, W, Studio, film_job, sign_in

A = "/api/v1/admin/claude"


class Rotation(unittest.TestCase):
    def setUp(self):
        self.s = Studio(plan=True)
        from studio import accounts
        accounts.signup("boss@x.test", PASSWORD, True, role="admin", verified=True)
        self.a = self.s.client()
        assert self.a.post("/api/v1/auth/login", json={"email": "boss@x.test", "password": PASSWORD}, headers=W).status_code == 200
        sign_in(self.a, 1, "one@x.test")
        self.a.post(f"{A}/accounts", headers=W)
        sign_in(self.a, 2, "two@x.test")

    def tearDown(self):
        self.s.close()

    def token(self, slot: int) -> str:
        f = self.s.data / "claude" / f"slot-{slot}" / ".credentials.json"
        return json.loads(f.read_text())["claudeAiOauth"]["accessToken"]

    def calls(self):
        from studio import db
        with db.read() as con:
            return [dict(r) for r in con.execute("SELECT * FROM call ORDER BY id")]

    def test_sc104_limit_in_the_middle_of_a_job(self):
        self.s.upstream_app.state.plan[self.token(1)] = "limit-after:1:900"       # one good answer, then the limit
        c = self.s.signup_verified("m@x.test")
        jid = film_job(c, idea="A fox [spend 6]").json()["id"]
        self.s.start()
        j = self.s.wait(jid)
        self.assertEqual(j["status"], "done", j["log"])                           # the job never saw the limit
        vias = [x["via"] for x in self.calls()]
        self.assertEqual(len(vias), 6)
        self.assertEqual(vias[:2], ["plan:1", "plan:2"])
        self.assertEqual(vias.count("plan:1"), 1)                                 # after its limit, never again
        acc = {x["slot"]: x for x in self.a.get(A).json()["accounts"]}
        self.assertEqual(acc[1]["state"], "limited")
        self.assertTrue(acc[1]["rest_until"])
        self.assertEqual(acc[1]["usage"]["five_hour"]["percent"], 100.0)          # the bar shows it full

    def test_manual_order_uses_the_top_account_until_its_limit(self):     # FR-120
        self.a.post("/api/v1/admin/claude/accounts/2/top", headers=W)           # e.g. the Max account first
        self.s.upstream_app.state.plan[self.token(2)] = "limit-after:2:900"
        c = self.s.signup_verified("m@x.test")
        jid = film_job(c, idea="A fox [spend 4]").json()["id"]
        self.s.start()
        self.assertEqual(self.s.wait(jid)["status"], "done")
        self.assertEqual([x["via"] for x in self.calls()], ["plan:2", "plan:2", "plan:1", "plan:1"])

    def test_sc105_ten_jobs_spread_evenly(self):
        from studio import quotas
        quotas.update_settings({"quota_films_default": 20, "concurrency": 2})
        clients = [self.s.signup_verified(f"m{i}@x.test") for i in range(5)]      # 3 open jobs at most per member
        ids = [film_job(clients[i % 5], idea=f"Fox {i} [spend 2]").json()["id"] for i in range(10)]
        self.s.start()
        for jid in ids:
            self.assertEqual(self.s.wait(jid, timeout=120)["status"], "done")
        from studio import db
        with db.read() as con:
            per = dict(con.execute("SELECT via, sum(tokens_in + tokens_out + cache_write + cache_read) FROM call "
                                   "GROUP BY via").fetchall())
        self.assertEqual(set(per), {"plan:1", "plan:2"})
        lo, hi = sorted(per.values())
        self.assertLessEqual((hi - lo) / hi, 0.20, per)                           # SC-105: within 20%


if __name__ == "__main__":
    unittest.main()
