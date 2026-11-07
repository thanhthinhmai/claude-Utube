"""Questions, treatment review and changes to a finished film: FR-014, FR-015 (specs/007 tasks T041)."""
import time
import unittest

from helpers import W, Studio, film_job


class FilmDialog(unittest.TestCase):
    def setUp(self):
        from studio import quotas
        self.s = Studio()
        quotas.update_settings({"quota_films_default": 5})
        self.c = self.s.signup_verified("d@example.com")

    def tearDown(self):
        self.s.close()

    def next_review(self, jid, n):
        """Wait until the job waits on its n-th review (or ends); returns the job."""
        from studio import jobs
        end = time.time() + 30
        while time.time() < end:
            j = jobs.load(jid)
            if (j["status"] == "waiting_review" and len(j["review_ids"]) >= n) or j["status"] in jobs.FINAL:
                return j
            time.sleep(0.05)
        raise AssertionError(jobs.load(jid)["log"][-5:])

    def decide(self, rid, value, note=""):
        return self.c.post(f"/api/v1/reviews/{rid}/decision", json={"value": value, "note": note}, headers=W)

    def test_at_most_three_questions(self):
        jid = film_job(self.c, idea="A fox [ask 4]").json()["id"]
        self.s.start()
        for n in range(1, 4):
            j = self.next_review(jid, n)
            rid = j["review_ids"][-1]
            self.assertEqual(self.decide(rid, "revise", "no").json()["error"]["code"], "value_not_allowed")
            self.assertEqual(self.decide(rid, "approve", "").json()["error"]["code"], "note_required")
            self.assertEqual(self.decide(rid, "approve", f"Orange, answer {n}").status_code, 201)
        j = self.s.wait(jid)
        self.assertEqual(j["status"], "done", j["log"])
        lines = " ".join(x["line"] for x in j["log"])
        self.assertIn("question refused", lines)                  # the 4th one was turned down (422)
        self.assertIn("Orange, answer 3", lines)
        self.assertEqual(len(j["review_ids"]), 3)

    def test_treatment_review_with_changes(self):
        jid = film_job(self.c, idea="A fox and a lantern", review_treatment=True).json()["id"]
        self.s.start()
        j = self.next_review(jid, 1)
        r = self.c.get(f"/api/v1/reviews/{j['review_ids'][-1]}").json()
        self.assertEqual(r["kind"], "treatment")
        self.assertEqual(self.decide(r["id"], "revise", "").json()["error"]["code"], "note_required")
        self.assertEqual(self.decide(r["id"], "revise", "Make the fox braver").status_code, 201)
        j = self.next_review(jid, 2)
        r2 = self.c.get(f"/api/v1/reviews/{j['review_ids'][-1]}").json()
        self.assertIn("(changed)", r2["summary_html"])
        self.assertEqual(self.decide(r2["id"], "approve").status_code, 201)
        j = self.s.wait(jid)
        self.assertEqual(j["status"], "done", j["log"])
        self.assertEqual(self.c.get("/api/v1/me").json()["quota"]["films"]["used"], 1)   # treatment changes are free

    def test_revise_a_finished_film(self):
        jid = film_job(self.c, idea="A fox").json()["id"]
        self.s.start()
        film = self.s.wait(jid)["links"]["film"]
        r = self.c.post("/api/v1/jobs", json={"kind": "film", "revise_of": film, "note": "x"}, headers=W)
        self.assertEqual(r.json()["error"]["code"], "note_required")
        self.assertEqual(self.c.post("/api/v1/jobs", json={"kind": "film", "revise_of": "no-such-film", "note": "Brighter"},
                                     headers=W).status_code, 404)
        r = self.c.post("/api/v1/jobs", json={"kind": "film", "revise_of": film, "note": "Make it brighter"}, headers=W)
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(self.c.post("/api/v1/jobs", json={"kind": "film", "revise_of": film, "note": "Again"},
                                     headers=W).json()["error"]["code"], "in_use")
        j = self.s.wait(r.json()["id"])
        self.assertEqual(j["status"], "done", j["log"])
        self.assertEqual(j["links"]["film"], f"{film}-r1")
        names = [f["name"] for f in self.c.get("/api/v1/films").json()["films"]]
        self.assertIn(film, names)                                # the old one stays
        self.assertIn(f"{film}-r1", names)
        self.assertEqual(self.c.get("/api/v1/me").json()["quota"]["films"]["used"], 2)   # 1 credit per change
        # a change of the change is -r2, not -r1-r1
        r = self.c.post("/api/v1/jobs", json={"kind": "film", "revise_of": f"{film}-r1", "note": "Slower please"}, headers=W)
        self.assertEqual(self.s.wait(r.json()["id"])["links"]["film"], f"{film}-r2")


if __name__ == "__main__":
    unittest.main()


NODE_MODULES = __import__("helpers").REPO / "lib" / "lemo-opuscar" / "node_modules"


@unittest.skipUnless(__import__("shutil").which("node") and (NODE_MODULES / "playwright-core").is_dir(),
                     "needs node and playwright-core")
class DialogBrowser(unittest.TestCase):
    setUp, tearDown = FilmDialog.setUp, FilmDialog.tearDown

    def test_answer_and_changes_in_browser(self):
        import json
        import os
        import subprocess
        from pathlib import Path
        from helpers import PASSWORD, Server
        from studio import jobs
        from studio.server import create_app
        web = Server(create_app())
        try:
            jid = film_job(self.c, idea="A fox [ask]").json()["id"]
            self.s.start()
            r = subprocess.run(["node", str(Path(__file__).with_name("browser_dialog.cjs")), web.url, "d@example.com",
                                PASSWORD, jid], capture_output=True, text=True, timeout=150,
                               env={**os.environ, "NODE_PATH": str(NODE_MODULES)})
            if r.returncode == 77:
                self.skipTest("cannot start a browser")
            self.assertEqual(r.returncode, 0, r.stderr)
            res = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertEqual(res["errors"], [])
            self.assertTrue(any("red scarf" in x["line"] for x in jobs.load(jid)["log"]))
            nj = jobs.load(res["newJob"])
            self.assertEqual((nj["input"]["revise_of"], nj["input"]["note"]), (jobs.load(jid)["links"]["film"], "A slower ending"))
        finally:
            web.close()
