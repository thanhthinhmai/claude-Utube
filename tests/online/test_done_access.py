"""specs/025 FR-010, SC-004: online, only the film's owner and the studio owner see the parts already done."""
import unittest

from helpers import PASSWORD, W, Studio, film_job


class DoneAccess(unittest.TestCase):
    def setUp(self):
        from studio import accounts
        self.s = Studio()
        accounts.signup("boss@example.com", PASSWORD, True, role="admin", verified=True)
        self.admin = self.s.client()
        assert self.admin.post("/api/v1/auth/login", json={"email": "boss@example.com", "password": PASSWORD},
                               headers=W).status_code == 200
        self.c = self.s.signup_verified("cust@example.com")
        self.other = self.s.signup_verified("other@example.com")

    def tearDown(self):
        self.s.close()

    def test_owner_and_studio_owner_only(self):
        from studio import jobs
        jid = film_job(self.c).json()["id"]
        film = jobs.load(jid)["links"]["film"]
        d = self.s.data / "jobs" / jid / "films" / film                  # where the worker makes it
        d.mkdir(parents=True)
        (d / "SCRIPT.md").write_text("Title: t\n\n[P01] One two three.\n")
        jobs.update(jid, lambda j: j.__setitem__("film_dir", str(d)))
        for who, code in ((self.c, 200), (self.admin, 200), (self.other, 404)):
            self.assertEqual(who.get(f"/api/v1/jobs/{jid}/done").status_code, code)
            r = who.get(f"/api/v1/jobs/{jid}/files/SCRIPT.md")
            self.assertEqual(r.status_code, code)
            if code == 404:
                self.assertNotIn("One two three", r.text)
        self.assertEqual(self.c.get(f"/api/v1/jobs/{jid}/done").json()["sections"]["script"]["paragraphs"], 1)
        view = self.c.get(f"/api/v1/jobs/{jid}").json()
        self.assertNotIn("film_dir", view)                              # never tell the internet where files are
        self.assertNotIn("runs", view)

    def test_worker_records_the_film_folder(self):
        from studio import jobs
        jid = film_job(self.c).json()["id"]
        self.s.start()
        j = self.s.wait(jid, timeout=90)
        self.assertEqual(j["film_dir"], str((self.s.data / "jobs" / jid / "films" / j["links"]["film"]).resolve()))
        self.assertEqual(self.c.get(f"/api/v1/jobs/{jid}/done").status_code, 200)
        self.assertEqual(self.other.get(f"/api/v1/jobs/{jid}/done").status_code, 404)


if __name__ == "__main__":
    unittest.main()
