"""The publish pack on the job page (specs/011 T025, US3, FR-013, FR-014; contracts/api.md)."""
import io
import json
import os
import shutil
import subprocess
import unittest
import zipfile
from pathlib import Path

from helpers import PASSWORD, REPO, W, Studio, film_job

NODE_MODULES = REPO / "lib" / "lemo-opuscar" / "node_modules"


class PublishView(unittest.TestCase):
    def setUp(self):
        from studio import accounts, quotas
        self.s = Studio()
        quotas.update_settings({"quota_films_default": 5})
        accounts.signup("owner@example.com", PASSWORD, True, role="admin", verified=True)
        self.c = self.s.client()
        assert self.c.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": PASSWORD}, headers=W).status_code == 200
        self.jid = film_job(self.c, idea="A fox and a lantern").json()["id"]
        self.s.start()
        self.job = self.s.wait(self.jid, timeout=90)
        self.film = self.job["links"]["film"]

    def tearDown(self):
        self.s.close()

    def test_api(self):
        self.assertEqual(self.job["status"], "done", self.job["log"][-6:])
        v = self.c.get(f"/api/v1/films/{self.film}/publish").json()
        self.assertEqual([t["angle"] for t in v["titles"]], ["curiosity", "number", "question"])
        self.assertEqual(v["titles"][0]["thumbnail"], "thumbnail-1.png")
        self.assertTrue(v["check"]["pass"], v["check"])
        self.assertIn("#fox", v["description"])
        r = self.c.get(f"/api/v1/films/{self.film}/publish/thumbnail-2.png")
        self.assertEqual((r.status_code, r.headers["content-type"]), (200, "image/png"))
        for bad in ("pack.json", "thumbs.json", "x.png"):
            self.assertEqual(self.c.get(f"/api/v1/films/{self.film}/publish/{bad}").status_code, 404, bad)
        z = zipfile.ZipFile(io.BytesIO(self.c.get(f"/api/v1/films/{self.film}/publish.zip").content))
        self.assertIn("PUBLISH.md", z.namelist())
        self.assertNotIn("pack.json", z.namelist())

    def test_someone_else_cannot_see_it(self):                     # FR-014
        other = self.s.signup_verified("other@example.com")
        self.assertEqual(other.get(f"/api/v1/films/{self.film}/publish").status_code, 404)
        self.assertEqual(other.get(f"/api/v1/films/{self.film}/publish.zip").status_code, 404)
        self.assertEqual(other.get(f"/api/v1/films/{self.film}/publish/thumbnail-1.png").status_code, 404)

    @unittest.skipUnless(shutil.which("node") and (NODE_MODULES / "playwright-core").is_dir(), "needs node and playwright-core")
    def test_job_page_in_a_browser(self):
        from helpers import Server
        from studio.server import create_app
        web = Server(create_app())
        try:
            r = subprocess.run(["node", str(Path(__file__).with_name("browser_publish.cjs")), web.url, "owner@example.com",
                                PASSWORD, self.jid], capture_output=True, text=True, timeout=90,
                               env={**os.environ, "NODE_PATH": str(NODE_MODULES)})
            if r.returncode == 77:
                self.skipTest("cannot start a browser")
            self.assertEqual(r.returncode, 0, r.stderr)
            res = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertEqual(res["errors"], [])
            self.assertEqual(res["cards"], 3)
            self.assertEqual(res["copied"], "The Fox Who Found a Lantern in the Snow")
            self.assertTrue(res["fits"], res)
            self.assertIn("Publish check: pass", res["text"])
        finally:
            web.close()


if __name__ == "__main__":
    unittest.main()
