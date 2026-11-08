"""Films run on the owner's Claude plan, with the fake Claude Code and the fake Claude API (specs/008 US1, US2 core,
T016, T017): no API key; calls go through the least used account; 429 and 401 move the call on; secrets stay out."""
import json
import logging
import os
import time
import unittest

from helpers import PASSWORD, W, Studio, film_job, sign_in

A = "/api/v1/admin/claude"


class PlanRun(unittest.TestCase):
    def setUp(self):
        self.s = Studio(plan=True)
        from studio import accounts
        accounts.signup("boss@x.test", PASSWORD, True, role="admin", verified=True)
        self.a = self.s.client()
        assert self.a.post("/api/v1/auth/login", json={"email": "boss@x.test", "password": PASSWORD}, headers=W).status_code == 200
        self.logs = []
        self.handler = logging.Handler()
        self.handler.emit = lambda rec: self.logs.append(rec.getMessage())
        for name in ("studio.proxy", "studio.worker"):
            logging.getLogger(name).addHandler(self.handler)
            logging.getLogger(name).setLevel(logging.INFO)

    def tearDown(self):
        for name in ("studio.proxy", "studio.worker"):
            logging.getLogger(name).removeHandler(self.handler)
        from studio import claude_plan
        claude_plan.cancel_login()
        self.s.close()

    def token(self, slot: int) -> str:
        """The fake Claude Code's real-looking access token of a slot (never shown by the studio)."""
        f = self.s.data / "claude" / f"slot-{slot}" / ".credentials.json"
        return json.loads(f.read_text())["claudeAiOauth"]["accessToken"]

    def calls(self):
        from studio import db
        with db.read() as con:
            return [dict(r) for r in con.execute("SELECT * FROM call ORDER BY id")]

    def two_accounts(self):
        sign_in(self.a, 1, "one@x.test")
        self.a.post(f"{A}/accounts", headers=W)
        sign_in(self.a, 2, "two@x.test")

    # ---------- US1 ----------
    def test_film_runs_on_the_plan_without_an_api_key(self):
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ)
        sign_in(self.a, 1, "owner@x.test")
        c = self.s.signup_verified("m@x.test")
        jid = film_job(c, idea="A fox [spend 2]").json()["id"]
        self.s.start()
        j = self.s.wait(jid)
        self.assertEqual(j["status"], "done", j["log"])
        self.assertIn("key kind: job token", " ".join(x["line"] for x in j["log"]))   # plan mode, no API key inside
        seen = self.s.upstream_app.state.seen
        self.assertEqual(len(seen), 2)
        self.assertTrue(all(x["bearer"] == self.token(1) and x["key"] is None for x in seen))
        self.assertTrue(all("oauth-2025-04-20" in (x["beta"] or "") for x in seen))     # Claude Code's headers kept
        calls = self.calls()
        self.assertEqual([(x["via"], x["job_id"], x["cost_usd"]) for x in calls], [("plan:1", jid, 0.0)] * 2)
        self.assertEqual(j["tokens"], 2 * 110_000)
        self.assertEqual(j["cost_usd"], 0.0)
        acc = self.a.get(A).json()["accounts"][0]
        self.assertEqual((acc["tokens_5h"], acc["usage"]["five_hour"]["percent"], acc["usage"]["seven_day"]["percent"]),
                         (220_000, 25.0, 10.0))                                         # FR-119 from the headers
        u = self.a.get("/api/v1/admin/usage").json()                                    # US4 without an API key
        self.assertEqual((u["tokens_total"], u["calls_total"], u["cost_usd_total"]), (220_000, 2, 0.0))
        self.assertEqual([(x["via"], x["tokens"], x["cost_usd"]) for x in u["by_claude"]], [("plan:1", 220_000, 0.0)])
        usage = self.a.get(f"/api/v1/jobs/{jid}").json()["usage"]
        self.assertEqual((usage["calls"], usage["tokens_in"], usage["tokens_out"]), (2, 200_000, 20_000))
        self.assertEqual(c.get(f"/api/v1/jobs/{jid}").json()["tokens"], 220_000)          # members see their tokens

    def test_not_ready_rejects_new_jobs_and_holds_queued_ones(self):
        c = self.s.signup_verified("m@x.test")
        r = film_job(c)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (503, "studio_not_ready"))
        self.assertEqual(c.get("/api/v1/me").json()["quota"]["films"]["used"], 0)      # no credit used
        sign_in(self.a, 1, "owner@x.test")
        jid = film_job(c).json()["id"]
        self.a.post(f"{A}/accounts/1/logout", headers=W)                              # the only account goes away
        self.s.worker.tick()
        from studio import jobs
        j = jobs.load(jid)
        self.assertEqual((j["status"], j["step"]), ("queued", "Waiting for a Claude account"))
        sign_in(self.a, 1, "owner@x.test")
        self.s.start()
        self.assertEqual(self.s.wait(jid)["status"], "done")

    def test_unknown_paths_are_closed(self):
        import urllib.error
        import urllib.request
        for path in ("/v1/models", "/api/oauth/usage", "/v1/files"):
            try:
                urllib.request.urlopen(self.s.proxy.url + path, timeout=5)
                code = 200
            except urllib.error.HTTPError as e:
                code, body = e.code, json.loads(e.read())
            self.assertEqual((code, body["error"]["type"]), (404, "not_found_error"), path)

    def test_token_cap_stops_the_job(self):
        from studio import quotas
        sign_in(self.a, 1, "owner@x.test")
        quotas.update_settings({"job_token_cap": 1_000_000})
        c = self.s.signup_verified("m@x.test")
        jid = film_job(c, idea="A fox [spend 12]").json()["id"]
        self.s.start()
        j = self.s.wait(jid)
        self.assertEqual((j["status"], j["failure_kind"], j["charged"]), ("failed", "studio", False))
        self.assertIn("token limit", j["error"])
        self.assertLessEqual(len(self.calls()), 10)            # 10 × 110k = 1.1M: stopped at the cap

    # ---------- US2 core: limits and broken sign-ins move the call on ----------
    def test_a_limited_account_hands_the_call_on(self):
        self.two_accounts()
        self.s.upstream_app.state.plan[self.token(1)] = "limit:600"
        c = self.s.signup_verified("m@x.test")
        jid = film_job(c, idea="A fox [spend 3]").json()["id"]
        self.s.start()
        self.assertEqual(self.s.wait(jid)["status"], "done")
        self.assertEqual([x["via"] for x in self.calls()], ["plan:2"] * 3)
        acc = {x["slot"]: x for x in self.a.get(A).json()["accounts"]}
        self.assertEqual(acc[1]["state"], "limited")
        self.assertAlmostEqual(time.mktime(time.strptime(acc[1]["rest_until"][:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone,
                               time.time() + 600, delta=5)             # rests until the plan's own reset time
        self.assertEqual(acc[2]["state"], "signed_in")

    def test_least_used_account_first(self):
        self.two_accounts()
        c = self.s.signup_verified("m@x.test")
        jid = film_job(c, idea="A fox [spend 4]").json()["id"]
        self.s.start()
        self.assertEqual(self.s.wait(jid)["status"], "done")
        vias = [x["via"] for x in self.calls()]
        self.assertEqual(vias, ["plan:1", "plan:2", "plan:1", "plan:2"])               # equal use, equal turns

    def test_401_refreshes_once_then_needs_sign_in(self):
        sign_in(self.a, 1, "owner@x.test")
        old = self.token(1)
        self.s.upstream_app.state.plan[old] = "401"
        c = self.s.signup_verified("m@x.test")
        jid = film_job(c, idea="A fox [spend 1]").json()["id"]
        self.s.start()
        self.assertEqual(self.s.wait(jid)["status"], "done")
        self.assertNotEqual(self.token(1), old)                                        # refreshed by Claude Code
        self.assertEqual(self.calls()[0]["via"], "plan:1")
        # now the refresh itself fails: the account needs signing in, one mail, the job fails as the studio's fault
        self.s.upstream_app.state.plan[self.token(1)] = "401"
        os.environ["FAKE_CLAUDE_REFRESH"] = "fail"
        try:
            jid = film_job(c, idea="A fox [spend 1]").json()["id"]
            j = self.s.wait(jid)
        finally:
            os.environ.pop("FAKE_CLAUDE_REFRESH")
        self.assertEqual((j["status"], j["failure_kind"], j["charged"]), ("failed", "studio", False))
        self.assertIn("No Claude account is available", j["error"])
        self.assertEqual(self.a.get(A).json()["accounts"][0]["state"], "needs_signin")
        mails = [p.read_text() for p in self.s.flush_mail() if "needs to sign in again" in p.read_text()]
        self.assertEqual(len(mails), 1)
        self.assertIn("To: boss@x.test", mails[0])

    def test_short_rest_is_waited_for_long_rest_fails(self):
        """While a job runs, its only account gets limited: back within 15 s → wait; later → fail, credit back."""
        import urllib.error
        import urllib.request
        import proxy
        from studio import claude_plan, jobs
        sign_in(self.a, 1, "owner@x.test")
        c = self.s.signup_verified("m@x.test")

        def call(token):
            req = urllib.request.Request(self.s.proxy.url + "/v1/messages", method="POST",
                                         data=json.dumps({"model": "claude-opus-5-5", "messages": []}).encode(),
                                         headers={"authorization": f"Bearer {token}", "content-type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    return r.status
            except urllib.error.HTTPError as e:
                return e.code
        jid = film_job(c).json()["id"]
        jobs.set_status(jid, "running")
        token = proxy.issue(jid)
        claude_plan.mark_limited(1, time.time() + 1.5)
        t = time.time()
        self.assertEqual(call(token), 200)
        self.assertGreater(time.time() - t, 1.0)                          # it waited for the account
        self.assertEqual([x["via"] for x in self.calls()], ["plan:1"])
        claude_plan.mark_limited(1, time.time() + 3600)
        self.assertEqual(call(token), 429)
        j = jobs.load(jid)
        self.assertEqual((j["status"], j["failure_kind"], j["charged"]), ("failed", "studio", False))
        self.assertRegex(j["error"], r"No Claude account is available until \d\d:\d\d UTC")

    def test_api_key_is_the_fallback(self):
        from helpers import REAL_KEY
        sign_in(self.a, 1, "owner@x.test")
        self.s.upstream_app.state.plan[self.token(1)] = "limit:600"
        os.environ["ANTHROPIC_API_KEY"] = REAL_KEY
        c = self.s.signup_verified("m@x.test")
        jid = film_job(c, idea="A fox [spend 1]").json()["id"]
        self.s.start()
        j = self.s.wait(jid)
        self.assertEqual(j["status"], "done")
        last = self.s.upstream_app.state.seen[-1]
        self.assertEqual((last["key"], last["bearer"]), (REAL_KEY, None))
        self.assertNotIn("oauth-", last["beta"] or "")                   # plan-only beta flags removed for the key
        self.assertEqual(self.calls()[-1]["via"], "api")
        self.assertGreater(j["cost_usd"], 0)                              # cost only through the key

    def test_restart_keeps_accounts(self):                                # FR-105
        sign_in(self.a, 1, "owner@x.test")
        import proxy
        from studio.server import create_app
        from fastapi.testclient import TestClient
        proxy.create_app()
        c = TestClient(create_app(), base_url="https://studio.test")
        c.post("/api/v1/auth/login", json={"email": "boss@x.test", "password": PASSWORD}, headers=W)
        self.assertEqual(c.get(A).json()["accounts"][0]["state"], "signed_in")

    # ---------- T017, SC-103: the sign-in never leaves the studio ----------
    def test_sign_in_never_reaches_jobs_logs_or_pages(self):
        self.two_accounts()
        secrets = {self.token(1), self.token(2)}
        c = self.s.signup_verified("m@x.test")
        started = []
        real_start = self.s.worker.runner.start

        def spy(job_id, work, env, mounts=None, network=None):
            started.append((env, mounts or {}))
            return real_start(job_id, work, env, mounts, network)
        self.s.worker.runner.start = spy
        jid = film_job(c, idea="A fox [spend 2]").json()["id"]
        self.s.start()
        self.assertEqual(self.s.wait(jid)["status"], "done")
        seen = []
        for p in (self.s.data / "jobs").rglob("*"):
            if p.is_file():
                seen.append(p.read_bytes().decode("utf-8", "replace"))
        seen += self.logs
        seen += [json.dumps(e) + json.dumps({k: str(v) for k, v in m.items()}) for e, m in started]
        seen += [self.a.get(A).text, self.a.get(f"/api/v1/jobs/{jid}").text, c.get(f"/api/v1/jobs/{jid}").text,
                 self.a.get("/api/v1/admin/users").text]
        text = "\n".join(seen)
        for t in secrets:
            self.assertNotIn(t, text)
        self.assertNotIn("tok-", text)
        self.assertNotIn("refresh-", text)
        for env, mounts in started:
            self.assertNotIn("ANTHROPIC_API_KEY", env)
            self.assertTrue(env["CLAUDE_CODE_OAUTH_TOKEN"].startswith("sk-job-"))
            self.assertEqual(env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"], "1")
            for target in mounts.values():
                self.assertNotIn("claude", str(target))
                self.assertNotIn("studio.db", str(target))

    def test_docker_command_mounts_only_the_job(self):
        """The real container command (with a stand-in docker) gets the job folder only (contracts/runner.md)."""
        import stat
        import worker
        sign_in(self.a, 1, "owner@x.test")
        fake = self.s.data / "fake-docker"
        out = self.s.data / "docker-args.json"
        fake.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" > '{out}'\necho studio-x\n")
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        os.environ["DOCKER_BIN"] = str(fake)
        try:
            w = worker.Worker(worker.DockerRunner(), self.s.proxy.url)
            c = self.s.signup_verified("m@x.test")
            film_job(c)
            j = w.claim()
            w.start(j)
        finally:
            os.environ.pop("DOCKER_BIN")
        args = out.read_text().splitlines()
        vols = [args[i + 1] for i, a in enumerate(args) if a == "-v"]
        self.assertTrue(vols and all(v.endswith(":/work") or ":/work/" in v for v in vols), vols)
        self.assertFalse(any("claude" in v or "studio.db" in v for v in vols))
        envs = [args[i + 1] for i, a in enumerate(args) if a == "-e"]
        self.assertFalse(any(e.startswith("ANTHROPIC_API_KEY=") for e in envs))
        self.assertTrue(any(e.startswith("CLAUDE_CODE_OAUTH_TOKEN=sk-job-") for e in envs))
        self.assertNotIn(self.token(1), "\n".join(args))


if __name__ == "__main__":
    unittest.main()
