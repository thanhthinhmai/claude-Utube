"""Pages opened for a job through the proxy (specs/010 T014, T020; research R4)."""
import os
import subprocess
import unittest

import httpx

from helpers import REPO, Studio, film_job


class WebFetch(unittest.TestCase):
    def setUp(self):
        self.s = Studio()
        import proxy
        self.c = self.s.signup_verified("pages@example.com")
        self.jid = film_job(self.c).json()["id"]          # queued, worker not started: its token is live
        self.token = proxy.issue(self.jid)

    def tearDown(self):
        self.s.close()

    def fetch(self, url, token=None):
        return httpx.post(self.s.proxy.url + "/internal/web/fetch", json={"url": url},
                          headers={"authorization": f"Bearer {token or self.token}"}, timeout=30)

    def test_internal_addresses_are_refused(self):
        for url in ("http://127.0.0.1:8790/", "http://localhost:8780/", "http://10.0.0.1/", "http://169.254.169.254/",
                    "http://[::1]/", "file:///etc/passwd", "http://example.org:8080/"):
            r = self.fetch(url)
            self.assertEqual((r.status_code, r.json()["error"]["code"]), (400, "blocked_address"), url)

    def test_needs_a_job_token(self):
        self.assertEqual(self.fetch("http://10.0.0.1/", token="sk-job-nope").status_code, 401)

    def test_at_most_60_pages(self):
        from studio import jobs
        jobs.update(self.jid, lambda j: j.__setitem__("web_fetches", 60))
        r = self.fetch("http://10.0.0.1/")
        self.assertEqual(r.status_code, 429)

    def test_log_has_the_host_only(self):
        with self.assertLogs("studio.proxy", "INFO") as logs:
            self.fetch("http://10.0.0.1/secret/path?q=customer+data")
        text = "\n".join(logs.output)
        self.assertIn("10.0.0.1", text)
        self.assertNotIn("secret", text)
        self.assertNotIn("customer", text)

    def test_cli_goes_through_the_proxy(self):
        env = {**os.environ, "STUDIO_MODE": "online", "STUDIO_JOB": self.jid, "STUDIO_PROXY": self.s.proxy.url,
               "STUDIO_JOB_TOKEN": self.token}
        env.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
        p = subprocess.run(["sh", str(REPO / "bin/studio"), "web", "fetch", "http://10.0.0.1/"], env=env,
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 1)
        self.assertIn("blocked_address", p.stderr)
        from studio import jobs
        self.assertEqual(jobs.load(self.jid).get("web_fetches"), 1)     # counted by the proxy, so it went there


if __name__ == "__main__":
    unittest.main()
