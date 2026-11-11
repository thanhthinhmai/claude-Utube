"""Films page: films being made, with their stages, above the finished ones (asked during the 008 live run)."""
import json
import os
import subprocess
import unittest
from pathlib import Path

from helpers import PASSWORD, REPO, OnlineProject, Server

NODE_MODULES = REPO / "lib" / "lemo-opuscar" / "node_modules"


@unittest.skipUnless(__import__("shutil").which("node") and (NODE_MODULES / "playwright-core").is_dir(),
                     "needs node and playwright-core")
class FilmsInProgress(unittest.TestCase):
    def test_stages_of_a_film_being_made(self):
        p = OnlineProject()
        try:
            from studio import accounts, jobs
            from studio.server import create_app
            accounts.signup("owner@x.test", PASSWORD, True, role="admin", verified=True)   # else login shows #/setup
            u = accounts.add_user("m@x.test", PASSWORD)
            j = jobs.create("film", "a fox", links={"film": "a-fox", "style": "tilt-shift"}, owner=u["id"], status="running")
            for st in ("Treatment", "Voice", "Look"):          # Voice reported before Look, as a real agent did
                jobs.step(j["id"], st)
            web = Server(create_app())
            try:
                r = subprocess.run(["node", str(Path(__file__).with_name("browser_films.cjs")), web.url, "m@x.test", PASSWORD],
                                   capture_output=True, text=True, timeout=90, env={**os.environ, "NODE_PATH": str(NODE_MODULES)})
                if r.returncode == 77:
                    self.skipTest("cannot start a browser")
                self.assertEqual(r.returncode, 0, r.stderr)
                res = json.loads(r.stdout.strip().splitlines()[-1])
            finally:
                web.close()
            self.assertEqual(res["errors"], [])
            self.assertEqual(res["got"], {"Treatment": "done", "Voice": "done", "Look": "now", "Render": "next"})
            self.assertEqual(res["storyboard"], 0)                # only shown when the job had one
            self.assertEqual(res["script"], 1)                    # shown from the start unless skipped (specs/010 T038)
            self.assertLessEqual(res["wide"], 360)
        finally:
            p.close()


if __name__ == "__main__":
    unittest.main()
