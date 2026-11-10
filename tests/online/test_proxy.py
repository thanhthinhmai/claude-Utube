"""API proxy: research R3, SC-005 (specs/007 tasks T015)."""
import json
import unittest
import urllib.error
import urllib.request

from helpers import REAL_KEY, Studio, account_id, film_job


def post(url, token, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"x-api-key": token, "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


class Proxy(unittest.TestCase):
    def setUp(self):
        self.s = Studio()
        self.c = self.s.signup_verified("p@example.com")

    def tearDown(self):
        self.s.close()

    def test_cost_counted_and_real_key_hidden(self):
        jid = film_job(self.c, idea="A fox [spend 2]").json()["id"]
        self.s.start()
        j = self.s.wait(jid)
        self.assertEqual(j["status"], "done", j["log"])
        self.assertAlmostEqual(j["cost_usd"], 1.2, places=6)       # 2 × (100k in × $4 + 10k out × $20) / 1M
        self.assertIn("key kind: job token", " ".join(x["line"] for x in j["log"]))
        self.assertTrue(self.s.upstream_app.state.seen)
        self.assertTrue(all(x["key"] == REAL_KEY for x in self.s.upstream_app.state.seen))
        from studio import db
        with db.read() as con:                              # 008: every call is a row; this studio has only the key
            rows = con.execute("SELECT via, account_id, cost_usd FROM call WHERE job_id = ?", (jid,)).fetchall()
        self.assertEqual([(r[0], r[1]) for r in rows], [("api", account_id(self.c))] * 2)
        self.assertAlmostEqual(sum(r[2] for r in rows), 1.2, places=6)
        self.assertEqual(j["tokens"], 2 * 110_000)
        self.assertNotIn("cost_usd", self.c.get(f"/api/v1/jobs/{jid}").json())    # only the admin sees cost

    def test_token_rules(self):
        import proxy
        from studio import jobs, quotas
        jid = film_job(self.c).json()["id"]
        jobs.set_status(jid, "running")
        token = proxy.issue(jid)
        url = self.s.proxy.url
        self.assertEqual(post(url + "/v1/messages", "sk-job-wrong", {"model": "x"})[0], 401)
        self.assertEqual(post(url + "/v1/messages", token, {"model": "claude-opus-5-5"})[0], 200)
        other = film_job(self.s.signup_verified("o@example.com")).json()["id"]
        self.assertEqual(post(url + f"/internal/jobs/{other}/step", token, {"text": "Picture"})[0], 403)
        quotas.fail(jid, "x")
        self.assertEqual(post(url + "/v1/messages", token, {"model": "claude-opus-5-5"})[0], 401)   # job ended

    def test_job_token_cap(self):                    # 008 FR-116 replaces the cost cap of 007
        from studio import quotas
        quotas.update_settings({"job_token_cap": 1_000_000})
        jid = film_job(self.c, idea="A fox [spend 12]").json()["id"]
        self.s.start()
        j = self.s.wait(jid)
        self.assertEqual((j["status"], j["failure_kind"]), ("failed", "studio"))
        self.assertIn("token limit", j["error"])
        self.assertFalse(j["charged"])
        self.assertLess(j["tokens"], 1_000_000 + 110_000 + 1)   # stopped after the call that crossed the cap
        self.assertEqual(self.c.get("/api/v1/me").json()["quota"]["films"]["used"], 0)

    def test_no_money_caps_any_more(self):
        from studio import quotas
        from studio.store import StudioError
        for old in ({"daily_cost_cap_usd": 0.5}, {"job_cost_cap_usd": 1.0}):
            with self.assertRaises(StudioError):
                quotas.update_settings(old)
        self.assertNotIn("daily_cost_cap_usd", quotas.settings())

    def test_stream_usage(self):
        import proxy
        sse = [b'event: message_start\ndata: {"type":"message_start","message":{"model":"claude-sonnet-5-5",'
               b'"usage":{"input_tokens":1000,"cache_read_input_tokens":5000,"output_tokens":1}}}\n\n',
               b'event: message_delta\ndata: {"type":"message_delta","usage":{"output_tokens":200}}\n\n']
        model, usage = proxy.usage_of_stream(sse)
        self.assertEqual(model, "claude-sonnet-5-5")
        self.assertEqual(usage, {"input_tokens": 1000, "cache_read_input_tokens": 5000, "output_tokens": 200})
        from studio import quotas
        self.assertAlmostEqual(quotas.cost_of(model, usage), (1000 * 2 + 5000 * 0.2 + 200 * 10) / 1e6)


if __name__ == "__main__":
    unittest.main()
