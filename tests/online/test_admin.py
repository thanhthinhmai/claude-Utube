"""User story 3: the studio owner's settings, quotas, locks and costs (specs/007 tasks T035)."""
import unittest

from helpers import PASSWORD, W, Studio, account_id, film_job


class US3(unittest.TestCase):
    def setUp(self):
        from studio import accounts
        self.s = Studio()
        accounts.signup("boss@example.com", PASSWORD, True, role="admin", verified=True)
        self.admin = self.s.client()
        assert self.admin.post("/api/v1/auth/login", json={"email": "boss@example.com", "password": PASSWORD},
                               headers=W).status_code == 200
        self.c = self.s.signup_verified("cust@example.com")
        self.cid = account_id(self.c)

    def tearDown(self):
        self.s.close()

    def test_us3_customers_are_kept_out(self):
        for method, path in (("get", "/admin/settings"), ("put", "/admin/settings"), ("get", "/admin/accounts"),
                             ("put", f"/admin/accounts/{self.cid}"), ("get", "/admin/usage")):
            kw = {"json": {}, "headers": W} if method == "put" else {}
            r = getattr(self.c, method)("/api/v1" + path, **kw)
            self.assertEqual((r.status_code, r.json()["error"]["code"]), (403, "forbidden"), path)

    def test_us3_quotas(self):
        a = self.admin
        r = a.put("/api/v1/admin/settings", json={"quota_films_default": 1}, headers=W)
        self.assertEqual(r.json()["quota_films_default"], 1)
        self.assertEqual(self.c.get("/api/v1/me").json()["quota"]["films"]["limit"], 1)     # at once
        self.assertEqual(film_job(self.c).status_code, 201)
        self.assertEqual(film_job(self.c).status_code, 402)
        r = a.put(f"/api/v1/admin/accounts/{self.cid}", json={"quota_films": 5}, headers=W)
        self.assertEqual(r.json()["quota"]["films"], {"used": 1, "limit": 5})
        self.assertEqual(film_job(self.c).status_code, 201)                                 # own quota wins
        a.put(f"/api/v1/admin/accounts/{self.cid}", json={"use_default_films": True}, headers=W)
        self.assertEqual(self.c.get("/api/v1/me").json()["quota"]["films"]["limit"], 1)
        rows = a.get("/api/v1/admin/accounts?q=cust").json()["accounts"]
        self.assertEqual([x["email"] for x in rows], ["cust@example.com"])
        self.assertIn("storage_mb", rows[0])

    def test_us3_settings_ranges(self):
        for bad in ({"concurrency": 0}, {"daily_cost_cap_usd": 5}, {"film_max_seconds": 1000}, {"what": 1}, [1, 2]):
            r = self.admin.put("/api/v1/admin/settings", json=bad, headers=W)
            self.assertEqual(r.status_code, 422, bad)
        self.assertEqual(self.admin.get("/api/v1/admin/settings").json()["concurrency"], 2)

    def test_us3_signup_closed(self):
        r = self.admin.put("/api/v1/admin/settings", json={"signup_open": True}, headers=W)
        self.assertEqual(r.status_code, 422)                      # 008: no setting turns sign-up back on
        r = self.s.client().post("/api/v1/auth/signup", json={"email": "late@example.com", "password": PASSWORD,
                                                               "accept_terms": True}, headers=W)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (403, "signup_closed"))

    def test_us3_lock_stops_jobs(self):
        jid = film_job(self.c, idea="A fox [slow 30]").json()["id"]
        self.s.start()
        self.s.wait(jid, statuses=("running",))
        r = self.admin.put(f"/api/v1/admin/accounts/{self.cid}", json={"locked": True}, headers=W)
        self.assertTrue(r.json()["locked"])
        j = self.s.wait(jid, statuses=("stopped",), timeout=10)
        self.assertIn("locked", j["error"])
        self.assertEqual(self.c.get("/api/v1/me").json()["error"]["code"], "locked")
        r = self.s.client().post("/api/v1/auth/login", json={"email": "cust@example.com", "password": PASSWORD}, headers=W)
        self.assertEqual(r.json()["error"]["code"], "locked")
        import time
        time.sleep(0.5)
        self.assertNotIn(jid, self.s.worker.runs)                    # the run was taken down
        self.admin.put(f"/api/v1/admin/accounts/{self.cid}", json={"locked": False}, headers=W)
        self.assertEqual(self.c.get("/api/v1/me").status_code, 200)

    def test_us3_usage_matches_jobs(self):
        from studio import jobs, quotas
        quotas.update_settings({"quota_films_default": 5})
        other = self.s.signup_verified("cust2@example.com")
        ids = [film_job(self.c, idea="A fox [spend 2]").json()["id"], film_job(other, idea="An owl [spend 1]").json()["id"]]
        self.s.start()
        for i in ids:
            self.assertEqual(self.s.wait(i)["status"], "done")
        u = self.admin.get("/api/v1/admin/usage").json()      # 008 US4: everything from the Call table
        from studio import db
        with db.read() as con:
            in_table = con.execute("SELECT sum(tokens_in + tokens_out + cache_write + cache_read), count(*) FROM call").fetchone()
        self.assertEqual((u["tokens_total"], u["calls_total"]), tuple(in_table))                       # SC-107
        self.assertEqual(u["tokens_total"], sum(jobs.load(i)["tokens"] for i in ids))
        self.assertEqual((u["tokens_total"], u["calls_total"]), (3 * 110_000, 3))
        self.assertAlmostEqual(u["cost_usd_total"], 1.8, places=4)            # this studio runs on the API key
        self.assertEqual(sum(d["jobs"] for d in u["days"]), 2)
        self.assertEqual({x["email"]: (x["calls"], x["tokens"]) for x in u["by_account"]},
                         {"cust@example.com": (2, 220_000), "cust2@example.com": (1, 110_000)})
        self.assertEqual([(x["via"], x["calls"]) for x in u["by_claude"]], [("api", 3)])
        self.assertGreater(u["storage_mb_total"], 0)
        self.assertIn("cost_usd", self.admin.get(f"/api/v1/jobs/{ids[0]}").json())   # the admin sees cost
        self.assertEqual(self.admin.get("/api/v1/admin/usage?from=2026-13-01").status_code, 422)
        rows = {x["email"]: x for x in self.admin.get("/api/v1/admin/accounts").json()["accounts"]}
        self.assertEqual(rows["cust@example.com"]["tokens_month"], 220_000)


if __name__ == "__main__":
    unittest.main()


NODE_MODULES = __import__("helpers").REPO / "lib" / "lemo-opuscar" / "node_modules"


@unittest.skipUnless(__import__("shutil").which("node") and (NODE_MODULES / "playwright-core").is_dir(),
                     "needs node and playwright-core")
class AdminBrowser(unittest.TestCase):
    setUp, tearDown = US3.setUp, US3.tearDown

    def test_us3_admin_page(self):
        import json
        import os
        import subprocess
        from pathlib import Path
        from helpers import Server
        from studio import accounts
        from studio.server import create_app
        web = Server(create_app())
        try:
            r = subprocess.run(["node", str(Path(__file__).with_name("browser_admin.cjs")), web.url, "boss@example.com", PASSWORD],
                               capture_output=True, text=True, timeout=90, env={**os.environ, "NODE_PATH": str(NODE_MODULES)})
            if r.returncode == 77:
                self.skipTest("cannot start a browser")
            self.assertEqual(r.returncode, 0, r.stderr)
            res = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertEqual(res["errors"], [])
            from studio import quotas
            self.assertEqual(quotas.settings()["quota_films_default"], 3)
            a = accounts.get(self.cid)
            self.assertEqual((a["quota_films"], bool(a["locked_at"])), (7, True))
            self.assertNotIn("new@example.com", [u["email"] for u in accounts.users()])     # added, made owner, removed
        finally:
            web.close()
