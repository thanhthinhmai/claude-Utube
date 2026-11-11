"""The Publish step in online film jobs (specs/011 T019): qa.publish, a failing pack never stops delivery, and a job
stopped during Publish keeps its film (FR-010, R7, SC-001)."""
import unittest

from helpers import PASSWORD, W, Studio, account_id, film_job, sign_in


class PublishStep(unittest.TestCase):
    def setUp(self):
        from studio import quotas
        self.s = Studio()
        quotas.update_settings({"quota_films_default": 5})
        self.c = self.s.signup_verified("maker@example.com")

    def tearDown(self):
        self.s.close()

    def run_job(self, idea):
        jid = film_job(self.c, idea=idea).json()["id"]
        self.s.start()
        return jid, self.s.wait(jid, timeout=90)

    def film_dir(self, j):
        from studio import store
        return store.account_dir(account_id(self.c)) / "films" / j["links"]["film"]

    def test_pack_is_checked_and_shown(self):                      # (a)
        _, j = self.run_job("A fox and a lantern")
        self.assertEqual(j["status"], "done", j["log"][-6:])
        p = j["qa"]["publish"]
        self.assertTrue(p["pass"], p["problems"])
        self.assertEqual(len(p["titles"]), 3)
        self.assertIn("PUBLISH.md", p["files"])
        self.assertIn("thumbnail-1.png", p["files"])
        self.assertIn("Publish", [x["line"] for x in j["log"]])
        self.assertIn("Publish check: pass", [x["line"] for x in j["log"]])
        self.assertTrue((self.film_dir(j) / "publish" / "PUBLISH.md").is_file())

    def test_failing_pack_still_delivers(self):                     # (b)
        _, j = self.run_job("A fox [publish-bad]")
        self.assertEqual(j["status"], "done", j["log"][-6:])
        self.assertFalse(j["qa"]["publish"]["pass"])
        self.assertTrue(any(x.startswith("title_length") for x in j["qa"]["publish"]["problems"]))
        self.assertTrue(j["qa"]["pass"])                               # the film's own gate is not touched
        self.assertTrue(j["charged"])
        self.assertEqual(self.c.get("/api/v1/me").json()["quota"]["films"]["used"], 1)


class PublishCut(unittest.TestCase):
    def setUp(self):
        from studio import accounts
        self.s = Studio(plan=True)
        accounts.signup("boss@x.test", PASSWORD, True, role="admin", verified=True)
        self.a = self.s.client()
        assert self.a.post("/api/v1/auth/login", json={"email": "boss@x.test", "password": PASSWORD}, headers=W).status_code == 200
        sign_in(self.a, 1, "owner@x.test")

    def tearDown(self):
        from studio import claude_plan
        claude_plan.cancel_login()
        self.s.close()

    def test_token_limit_during_publish_keeps_the_film(self):      # (c)
        from studio import quotas
        quotas.update_settings({"job_token_cap": 1_000_000})
        c = self.s.signup_verified("m@x.test")
        jid = film_job(c, idea="A fox [publish-cap]").json()["id"]
        self.s.start()
        j = self.s.wait(jid, timeout=90)
        self.assertEqual(j["status"], "done", j["log"][-6:])
        self.assertIn("token", j["qa"]["publish"]["cut"])
        self.assertFalse(j["qa"]["publish"]["pass"])
        self.assertTrue(j["charged"])

    def test_token_limit_before_publish_still_fails(self):          # (e) the old rule for every other step
        from studio import quotas
        quotas.update_settings({"job_token_cap": 1_000_000})
        c = self.s.signup_verified("n@x.test")
        jid = film_job(c, idea="A fox [spend 12]").json()["id"]
        self.s.start()
        j = self.s.wait(jid, timeout=90)
        self.assertEqual((j["status"], j["failure_kind"]), ("failed", "studio"))
        self.assertIn("token limit", j["error"])


class PublishWatchdog(unittest.TestCase):
    def setUp(self):
        from studio import quotas
        self.s = Studio()
        quotas.update_settings({"quota_films_default": 5})
        self.c = self.s.signup_verified("slow@example.com")

    def tearDown(self):
        self.s.close()

    def test_watchdog_during_publish_keeps_the_film(self):          # (d)
        from studio import jobs
        self.s.worker.watchdog = 4
        jid = film_job(self.c, idea="A fox [529-publish]").json()["id"]
        self.s.start()
        j = self.s.wait(jid, timeout=60)
        self.assertEqual(j["status"], "done", j["log"][-6:])
        self.assertIn("did not answer", j["qa"]["publish"]["cut"])
        self.assertEqual(jobs.load(jid)["publish_cut"], j["publish_cut"])


if __name__ == "__main__":
    unittest.main()
