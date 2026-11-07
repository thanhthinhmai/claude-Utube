"""User story 1, end to end with RUNNER=local and the fake agent (specs/007 tasks T027)."""
import time
import unittest

from helpers import PASSWORD, W, Studio, account_id, film_job


class US1(unittest.TestCase):
    def setUp(self):
        self.s = Studio()

    def tearDown(self):
        self.s.close()

    def test_us1_signup_to_download(self):
        c = self.s.client()
        r = c.post("/api/v1/auth/signup", json={"email": "new@example.com", "password": PASSWORD, "accept_terms": True},
                   headers=W)
        self.assertEqual(r.status_code, 201)
        c.post("/api/v1/auth/login", json={"email": "new@example.com", "password": PASSWORD}, headers=W)
        self.assertEqual(film_job(c).json()["error"]["code"], "unverified")
        token = self.s.last_link("new@example.com", "verify")          # read from the .eml file
        self.assertEqual(c.post("/api/v1/auth/verify", json={"token": token}, headers=W).status_code, 200)
        r = film_job(c, idea="A small fox finds a lantern")
        self.assertEqual(r.status_code, 201, r.text)
        job = r.json()
        self.assertEqual((job["status"], job["queue_position"]), ("queued", 1))
        self.s.start()
        seen = set()
        end = time.time() + 60
        while time.time() < end:
            st = c.get(f"/api/v1/jobs/{job['id']}").json()["status"]
            seen.add(st)
            if st == "done":
                break
            time.sleep(0.02)
        self.assertIn("running", seen)
        j = c.get(f"/api/v1/jobs/{job['id']}").json()
        self.assertEqual(j["status"], "done", j["log"])
        film = j["links"]["film"]
        self.assertTrue(j["qa"]["pass"])
        self.assertAlmostEqual(j["qa"]["lufs"], -14, delta=1)
        r = c.get(f"/api/v1/films/{film}/download")
        self.assertEqual(r.status_code, 200)
        self.assertIn("attachment", r.headers["content-disposition"])
        self.assertGreater(len(r.content), 1000)
        self.assertEqual(c.get("/api/v1/me").json()["quota"]["films"]["used"], 1)
        self.assertIn(film, [f["name"] for f in c.get("/api/v1/films").json()["films"]])
        mails = [p.read_text() for p in self.s.flush_mail()]
        self.assertTrue(any("Your job is ready" in m for m in mails))
        # out of credits (2 a month by default)
        film_job(c)
        self.assertEqual(film_job(c).status_code, 409 if False else 402)
        # another customer cannot download it
        other = self.s.signup_verified("other@example.com")
        self.assertEqual(other.get(f"/api/v1/films/{film}/download").status_code, 404)
        # delete the film
        self.assertEqual(c.delete(f"/api/v1/films/{film}", headers=W).status_code, 204)
        self.assertEqual(c.get(f"/api/v1/films/{film}/download").status_code, 404)

    def test_quality_gate(self):
        from studio import quotas
        quotas.update_settings({"quota_films_default": 5})
        c = self.s.signup_verified("qa@example.com")
        fixed = film_job(c, idea="Loud at first [loud]").json()["id"]
        never = film_job(c, idea="Always loud [loud-always]").json()["id"]
        self.s.start()
        j = self.s.wait(fixed)
        self.assertEqual(j["status"], "done", j["log"])
        self.assertEqual(j["qa_retries"], 1)                 # the session was resumed once with the numbers
        j = self.s.wait(never)
        self.assertEqual((j["status"], j["failure_kind"]), ("failed", "studio"), j["log"])
        self.assertIn("LUFS", j["error"])
        self.assertFalse(j["charged"])
        self.assertEqual(c.get("/api/v1/me").json()["quota"]["films"]["used"], 1)

    def test_failure_kinds(self):
        from studio import quotas
        quotas.update_settings({"quota_films_default": 5})
        c = self.s.signup_verified("fk@example.com")
        cust = film_job(c, idea="Cannot be filmed [fail-customer]").json()["id"]
        stud = film_job(c, idea="Tool broke [fail]").json()["id"]
        crash = film_job(c, idea="Crash [crash]").json()["id"]
        self.s.start()
        self.assertEqual(self.s.wait(cust)["failure_kind"], "customer")
        self.assertEqual(self.s.wait(stud)["failure_kind"], "studio")
        self.assertEqual(self.s.wait(crash)["failure_kind"], "studio")
        self.assertEqual(c.get("/api/v1/me").json()["quota"]["films"]["used"], 1)    # only the customer's one
        mails = [p.read_text() for p in self.s.flush_mail()]
        self.assertEqual(sum("could not finish" in m for m in mails), 3)

    def test_overloaded_api_hits_the_watchdog(self):
        self.s.worker.watchdog = 1.5
        c = self.s.signup_verified("ov@example.com")
        jid = film_job(c, idea="Busy [529]").json()["id"]
        self.s.start()
        j = self.s.wait(jid, timeout=30)
        self.assertEqual((j["status"], j["failure_kind"]), ("failed", "studio"))
        self.assertIn("did not answer", j["error"])
        self.assertTrue(any(x["model"] == "overloaded" for x in self.s.upstream_app.state.seen))

    def test_question_review_then_resume(self):
        c = self.s.signup_verified("ask@example.com")
        jid = film_job(c, idea="A fox [ask]").json()["id"]
        self.s.start()
        j = self.s.wait(jid, statuses=("waiting_review",))
        time.sleep(0.5)                                      # the worker sees the agent exit with code 10
        mails = [p.read_text() for p in self.s.flush_mail()]
        self.assertTrue(any("needs your answer" in m for m in mails))
        rid = j["review_ids"][-1]
        r = c.get(f"/api/v1/reviews/{rid}").json()
        self.assertEqual((r["kind"], r["set"]), ("question", None))
        self.assertEqual(c.post(f"/api/v1/reviews/{rid}/decision", json={"value": "approve", "note": "Orange, please"},
                                headers=W).status_code, 201)
        j = self.s.wait(jid)
        self.assertEqual(j["status"], "done", j["log"])
        self.assertTrue(any("Orange, please" in x["line"] for x in j["log"]))
        self.assertEqual(j["agent_session"], f"sess-{jid}")

    def test_restart_runs_again_once(self):
        from studio import jobs
        c = self.s.signup_verified("rs@example.com")
        jid = film_job(c).json()["id"]
        jobs.set_status(jid, "running")              # as if a worker died while it ran
        self.s.worker.recover()
        self.assertEqual(jobs.load(jid)["status"], "queued")
        jobs.set_status(jid, "running")
        self.s.worker.recover()
        j = jobs.load(jid)
        self.assertEqual((j["status"], j["failure_kind"], j["charged"]), ("failed", "studio", False))
        self.assertEqual(account_id(c), j["owner"])


if __name__ == "__main__":
    unittest.main()


NODE_MODULES = __import__("helpers").REPO / "lib" / "lemo-opuscar" / "node_modules"


@unittest.skipUnless(__import__("shutil").which("node") and (NODE_MODULES / "playwright-core").is_dir(),
                     "needs node and playwright-core")
class BrowserUS1(unittest.TestCase):
    def test_us1_in_browser(self):
        import datetime as dt
        import json
        import os
        import subprocess
        from pathlib import Path
        from helpers import Server
        s = Studio()
        try:
            from studio.server import create_app
            web = Server(create_app())
            s.start()
            p = subprocess.Popen(["node", str(Path(__file__).with_name("browser_us1.cjs")), web.url, "b@example.com", PASSWORD],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                 env={**os.environ, "NODE_PATH": str(NODE_MODULES)})
            first = p.stdout.readline().strip()
            if p.poll() == 77 or not first:
                p.wait()
                if p.returncode == 77:
                    self.skipTest("cannot start a browser")
            self.assertEqual(first, "NEED-TOKEN", p.stderr.read() if p.poll() is not None else first)
            p.stdin.write(s.last_link("b@example.com", "verify") + "\n")
            p.stdin.flush()
            out, err = p.communicate(timeout=120)
            self.assertEqual(p.returncode, 0, err)
            res = json.loads(out.strip().splitlines()[-1])
            self.assertEqual(res["errors"], [])
            self.assertLessEqual(res["wide"], 360)                        # no sideways scrolling on a phone
            print(f"\n  SC-001: ordering took {res['order_ms'] / 1000:.1f} s of browser time (not counting the mail)")
            self.assertLess(res["order_ms"], 180_000)
            from studio import jobs
            j = [x for x in jobs.all_jobs() if x["owner"] != "local"][0]
            step_at = next(dt.datetime.fromisoformat(x["t"]).timestamp() for x in j["log"] if x["line"] == "Render")
            lag = res["render_seen"] - step_at
            print(f"  SC-007: the Render step showed on the page {lag:.1f} s after it was written")
            self.assertLessEqual(lag, 5 + 1)                                 # log times have 1 s resolution
            self.assertIn("/download", res["href"])
            web.close()
        finally:
            s.close()
