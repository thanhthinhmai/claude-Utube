"""Settings → Worker (specs/009 US1, FR-201-FR-206, SC-202, SC-203): heartbeats, the four counts, the latest jobs."""
import json
import os
import subprocess
import time
import unittest
from pathlib import Path

from helpers import PASSWORD, REPO, W, Server, Studio, film_job

NODE_MODULES = REPO / "lib" / "lemo-opuscar" / "node_modules"


class WorkerStatus(unittest.TestCase):
    def setUp(self):
        self.s = Studio()
        from studio import accounts
        accounts.signup("boss@x.test", PASSWORD, True, role="admin", verified=True)
        self.a = self.s.client()
        assert self.a.post("/api/v1/auth/login", json={"email": "boss@x.test", "password": PASSWORD}, headers=W).status_code == 200
        self.c = self.s.signup_verified("m@x.test")

    def tearDown(self):
        self.s.close()

    def status(self):
        r = self.a.get("/api/v1/admin/worker")
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_heartbeat_states(self):
        from studio import store
        w = self.s.worker
        self.assertEqual(self.status()["workers"], [])                       # no worker yet
        w.beat(force=True)
        st = self.status()["workers"]
        self.assertEqual((len(st), st[0]["id"], st[0]["state"], st[0]["busy_with"]), (1, w.beat_id, "running", []))
        real = store.clock
        try:
            store.clock = lambda: real() + 31                                 # SC-202: stopped within 40 s
            self.assertEqual(self.status()["workers"][0]["state"], "not_responding")
            store.clock = lambda: real() + 601                                # gone after 10 minutes
            self.assertEqual(self.status()["workers"], [])
        finally:
            store.clock = real
        w.unbeat()
        self.assertEqual(self.status()["workers"], [])

    def test_busy_with_and_counts(self):                                     # SC-203
        quotas = __import__("studio.quotas", fromlist=["x"])
        quotas.update_settings({"quota_films_default": 10, "concurrency": 1})
        c2 = self.s.signup_verified("m2@x.test")
        slow = film_job(self.c, idea="A fox [slow 30]").json()["id"]
        queued = film_job(c2, idea="An owl").json()["id"]
        self.s.start()
        self.s.wait(slow, statuses=("running",))
        end = time.time() + 10
        while time.time() < end and slow not in (self.status()["workers"] or [{"busy_with": []}])[0]["busy_with"]:
            time.sleep(0.1)
        st = self.status()
        self.assertEqual(st["workers"][0]["busy_with"], [slow])
        self.assertEqual(st["counts"], {"queued": 1, "running": 1, "waiting_review": 0, "waiting_claude": 0})
        self.assertEqual({j["id"] for j in st["latest"][:2]}, {slow, queued})       # the two newest jobs
        self.assertEqual({j["email"] for j in st["latest"]}, {"m@x.test", "m2@x.test"})

    def test_latest_is_20_newest_with_errors_cut(self):
        from studio import jobs
        ids = [jobs.create("film", f"f{i}", owner="x", status="queued")["id"] for i in range(25)]
        jobs.finish(ids[0], "failed", error="E" * 500)
        st = self.status()
        self.assertEqual(len(st["latest"]), 20)
        self.assertEqual(st["latest"][0]["id"], ids[0])                      # changed last: first
        self.assertEqual(len(st["latest"][0]["error"]), 300)

    def test_owner_only(self):
        from studio import tokens, accounts
        self.assertEqual(self.c.get("/api/v1/admin/worker").status_code, 403)
        member = accounts.get(self.c.get("/api/v1/me").json()["id"])
        _, ms = tokens.create(member, "m")
        boss = accounts.get(self.a.get("/api/v1/me").json()["id"])
        _, os_ = tokens.create(boss, "o", role="admin")
        t = self.s.client()
        t.cookies.clear()
        self.assertEqual(t.get("/api/v1/admin/worker", headers={"Authorization": f"Bearer {ms}"}).status_code, 403)
        self.assertEqual(t.get("/api/v1/admin/worker", headers={"Authorization": f"Bearer {os_}"}).status_code, 200)

    @unittest.skipUnless(__import__("shutil").which("node") and (NODE_MODULES / "playwright-core").is_dir(),
                         "needs node and playwright-core")
    def test_worker_tab_in_a_browser(self):
        self.s.worker.beat(force=True)
        film_job(self.c, idea="A fox")
        from studio.server import create_app
        web = Server(create_app())
        try:
            r = subprocess.run(["node", str(Path(__file__).with_name("browser_worker.cjs")), web.url, "boss@x.test", PASSWORD],
                               capture_output=True, text=True, timeout=90, env={**os.environ, "NODE_PATH": str(NODE_MODULES)})
            if r.returncode == 77:
                self.skipTest("cannot start a browser")
            self.assertEqual(r.returncode, 0, r.stderr)
            res = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertEqual(res["errors"], [])
            self.assertLessEqual(res["wide"], 360)
            self.assertTrue(res["refreshed"])                                # read again after 5 s
        finally:
            web.close()


if __name__ == "__main__":
    unittest.main()
