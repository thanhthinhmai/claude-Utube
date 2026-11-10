"""Script scores and film measures on the job page (specs/010 T028–T030, US3, FR-015, FR-016)."""
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

from helpers import PASSWORD, REPO, W, Studio, film_job

NODE_MODULES = REPO / "lib" / "lemo-opuscar" / "node_modules"


class QualityView(unittest.TestCase):
    def setUp(self):
        from studio import accounts, quotas
        self.s = Studio()
        quotas.update_settings({"quota_films_default": 5})
        accounts.signup("owner@example.com", PASSWORD, True, role="admin", verified=True)
        self.c = self.s.client()
        assert self.c.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": PASSWORD}, headers=W).status_code == 200
        self.jid = film_job(self.c, idea="A fox [narration] [editor-p1 P02]").json()["id"]
        self.s.start()
        self.job = self.s.wait(self.jid, timeout=90)

    def tearDown(self):
        self.s.close()

    def test_api_shows_scores_and_measures(self):
        self.assertEqual(self.job["status"], "done", self.job["log"][-6:])
        v = self.c.get(f"/api/v1/jobs/{self.jid}").json()
        s = v["qa"]["script"]
        self.assertEqual((s["verdict"], s["fix_rounds"], s["editor_score"], s["p1"]), ("pass", 1, 9, 0))
        self.assertEqual([r["p1"] for r in s["rounds"]], [1, 0])
        self.assertEqual(s["machine_score"], 10.0)
        m = v["qa"]["film"]["measures"]
        for k in ("silence_ratio", "tail_s", "stills_bad", "missing_glyphs", "cuts_bad"):
            self.assertIn(k, m)
        self.assertTrue(v["qa"]["film"]["pass"])

    @unittest.skipUnless(shutil.which("node") and (NODE_MODULES / "playwright-core").is_dir(), "needs node and playwright-core")
    def test_job_page_and_setting_in_a_browser(self):
        from helpers import Server
        from studio import quotas
        from studio.server import create_app
        web = Server(create_app())
        try:
            r = subprocess.run(["node", str(Path(__file__).with_name("browser_quality.cjs")), web.url, "owner@example.com",
                                PASSWORD, self.jid], capture_output=True, text=True, timeout=90,
                               env={**os.environ, "NODE_PATH": str(NODE_MODULES)})
            if r.returncode == 77:
                self.skipTest("cannot start a browser")
            self.assertEqual(r.returncode, 0, r.stderr)
            res = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertEqual(res["errors"], [])
            for s in ("Script: pass", "fix rounds 1", "Silence in the narration", "Time after the last word"):
                self.assertIn(s, res["quality"])
            self.assertEqual(quotas.settings()["editor_model"], "sonnet")
        finally:
            web.close()


if __name__ == "__main__":
    unittest.main()
