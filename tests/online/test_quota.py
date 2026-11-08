"""Quotas: FR-005, FR-006, FR-006a, SC-008 (specs/007 tasks T013)."""
import datetime as dt
import threading
import unittest

from helpers import W, OnlineProject, account_id, film_job


class Quota(unittest.TestCase):
    def setUp(self):
        import os
        self.old_mod = os.environ.get("STUDIO_MODERATION")
        self.old_key = os.environ.get("ANTHROPIC_API_KEY")
        os.environ["STUDIO_MODERATION"] = "fake"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"      # a ready studio (008 FR-110); nothing calls Claude here
        self.p = OnlineProject()
        self.c = self.p.signup_verified("q@example.com")

    def tearDown(self):
        import os
        self.p.close()
        if self.old_mod is None:
            os.environ.pop("STUDIO_MODERATION", None)
        else:
            os.environ["STUDIO_MODERATION"] = self.old_mod
        if self.old_key is None:
            os.environ.pop("ANTHROPIC_API_KEY", None)
        else:
            os.environ["ANTHROPIC_API_KEY"] = self.old_key

    def test_ten_at_once_only_two_pass(self):
        from studio import quotas
        quotas.update_settings({"quota_films_default": 2})
        cookies = dict(self.c.cookies)
        codes, bodies = [], []

        def one():
            c = self.p.client()
            c.cookies.update(cookies)
            r = film_job(c)
            codes.append(r.status_code)
            bodies.append(r.json())
        ts = [threading.Thread(target=one) for _ in range(10)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(codes.count(201), 2, codes)
        self.assertEqual(codes.count(402) + codes.count(409), 8, codes)
        # beyond the 2 credits: quota_exceeded, with the reset time 00:00 on the 1st, Vietnam time
        r = film_job(self.c)
        self.assertEqual(r.status_code, 402)
        when = dt.datetime.fromisoformat(r.json()["error"]["resets_at"])
        self.assertEqual((when.day, when.hour, when.minute), (1, 0, 0))
        self.assertEqual(when.utcoffset(), dt.timedelta(hours=7))
        self.assertEqual(self.c.get("/api/v1/me").json()["quota"]["films"]["used"], 2)

    def test_refund_only_for_studio_failures(self):
        from studio import jobs, quotas
        ids = [film_job(self.c).json()["id"] for _ in range(2)]
        quotas.fail(ids[0], "tool broke", "studio")
        self.assertEqual(self.c.get("/api/v1/me").json()["quota"]["films"]["used"], 1)
        quotas.fail(ids[1], "bad idea", "customer")
        self.assertEqual(self.c.get("/api/v1/me").json()["quota"]["films"]["used"], 1)
        self.assertEqual(jobs.load(ids[0])["failure_kind"], "studio")
        self.assertEqual(jobs.load(ids[1])["failure_kind"], "customer")

    def test_customer_stop_keeps_the_charge(self):
        jid = film_job(self.c).json()["id"]
        r = self.c.post(f"/api/v1/jobs/{jid}/stop", headers=W)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "stopped")
        self.assertEqual(self.c.get("/api/v1/me").json()["quota"]["films"]["used"], 1)
        self.assertEqual(self.c.post(f"/api/v1/jobs/{jid}/stop", headers=W).status_code, 409)

    def test_rejected_idea_costs_nothing(self):
        r = film_job(self.c, idea="A film full of gore")
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json()["error"]["code"], "content_rejected")
        self.assertTrue(r.json()["error"]["reason"])
        self.assertEqual(self.c.get("/api/v1/me").json()["quota"]["films"]["used"], 0)

    def test_form_checks(self):
        from studio import quotas
        self.assertEqual(film_job(self.c, style="no-such-style").status_code, 404)
        self.assertEqual(film_job(self.c, seconds=61).json()["error"]["code"], "too_long")
        quotas.update_settings({"quota_films_default": 10})
        for _ in range(3):
            self.assertEqual(film_job(self.c).status_code, 201)
        self.assertEqual(film_job(self.c).json()["error"]["code"], "too_many_queued")

    def test_unverified_cannot_order(self):
        from studio import accounts
        c = self.p.client()
        accounts.signup("u@example.com", "correct horse battery", True)      # an unverified account from 007
        c.post("/api/v1/auth/login", json={"email": "u@example.com", "password": "correct horse battery"}, headers=W)
        r = film_job(c)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (403, "unverified"))

    def test_settings_ranges(self):
        from studio import quotas
        from studio.store import StudioError
        for bad in ({"concurrency": 0}, {"concurrency": 17}, {"job_cost_cap_usd": 0}, {"film_max_seconds": 301},
                    {"nope": 1}, {"concurrency": "2"}):
            with self.assertRaises(StudioError, msg=bad):
                quotas.update_settings(bad)
        self.assertEqual(quotas.update_settings({"concurrency": 16})["concurrency"], 16)

    def test_daily_cap(self):
        from studio import db, quotas
        with db.tx() as con:
            con.execute("INSERT INTO usage_day VALUES (?, ?, ?, 0)", (quotas.today_vn(), account_id(self.c), 25.0))
        r = film_job(self.c)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (503, "daily_cap"))


if __name__ == "__main__":
    unittest.main()
