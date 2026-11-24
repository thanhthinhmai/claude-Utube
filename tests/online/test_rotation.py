"""Several Claude accounts (specs/008 US2): a plan that reaches its limit in the middle of a job hands the rest of
the job to another account (SC-104), and calls spread evenly over the accounts (SC-105)."""
import json
import unittest

from helpers import PASSWORD, W, Studio, film_job, sign_in

A = "/api/v1/admin/claude"


class Accounts(unittest.TestCase):
    """Two signed-in Claude accounts (no tests of its own)."""

    def setUp(self):
        self.s = Studio(plan=True)
        import proxy
        proxy.HELD.clear()
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


class Rotation(Accounts):

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


class OneAccountPerJob(Accounts):
    """specs/030 US1: a job stays on the account it started on, so the prompt cache stays warm."""

    def vias_of(self, jid):
        return [x["via"] for x in self.calls() if x["job_id"] == jid]

    def test_sc001_a_job_keeps_its_account(self):
        c = self.s.signup_verified("m@x.test")
        jid = film_job(c, idea="A fox [spend 6]").json()["id"]
        self.s.start()
        self.assertEqual(self.s.wait(jid)["status"], "done")
        # plan:1 gets busier after the first call (least-used would now pick plan:2), yet the job stays
        self.assertEqual(self.vias_of(jid), ["plan:1"] * 6)

    def test_sc002_limit_moves_the_job_and_it_stays(self):
        self.s.upstream_app.state.plan[self.token(1)] = "limit-after:2:900"
        c = self.s.signup_verified("m@x.test")
        jid = film_job(c, idea="A fox [spend 6]").json()["id"]
        self.s.start()
        self.assertEqual(self.s.wait(jid)["status"], "done")            # the agent never saw the limit
        self.assertEqual(self.vias_of(jid), ["plan:1", "plan:1"] + ["plan:2"] * 4)

    def test_sc003_jobs_starting_together_get_different_accounts(self):
        c1, c2 = self.s.signup_verified("m1@x.test"), self.s.signup_verified("m2@x.test")
        a = film_job(c1, idea="Fox A [spend 3]").json()["id"]
        b = film_job(c2, idea="Fox B [spend 3]").json()["id"]
        self.s.start()
        for jid in (a, b):
            self.assertEqual(self.s.wait(jid)["status"], "done")
        va, vb = self.vias_of(a), self.vias_of(b)
        self.assertEqual(len(set(va)), 1, va)
        self.assertEqual(len(set(vb)), 1, vb)
        self.assertNotEqual(va[0], vb[0])

    def test_fr004_ended_jobs_are_forgotten(self):
        import proxy
        c = self.s.signup_verified("m@x.test")
        jid = film_job(c, idea="A fox [spend 2]").json()["id"]
        self.s.start()
        self.assertEqual(self.s.wait(jid)["status"], "done")
        self.assertIn(jid, proxy.HELD)
        proxy.prune_held(force=True)
        self.assertNotIn(jid, proxy.HELD)

    def test_order_slots(self):
        import proxy
        proxy.HELD.clear()
        proxy.HELD.update({"j1": 2, "j2": 1, "j3": 1})
        self.assertEqual(proxy.order_slots("j1", [1, 2, 3]), [2, 1, 3])      # held first
        self.assertEqual(proxy.order_slots("j1", [1, 3]), [3, 1])            # held slot gone: chosen like a new job
        self.assertEqual(proxy.order_slots("new", [1, 2, 3]), [3, 2, 1])     # fewest jobs first
        proxy.HELD.clear()


if __name__ == "__main__":
    unittest.main()
