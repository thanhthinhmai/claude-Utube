"""specs/034 T063: a film job that failed or stopped during a cast redraw keeps its notes open; "Send notes again"
reopens the same job at the Cast step (no new credit) and the worker resumes Claude's session."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock
from pathlib import Path

from helpers import W, Studio, account_id

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "tests" / "filmcheck"))
import castfilm  # noqa: E402


class CastResend(unittest.TestCase):
    def setUp(self):
        self.s = Studio()
        self.c = self.s.signup_verified("resend@example.com")
        from studio import jobs, store
        j = jobs.build("film", "Night film", {}, owner=account_id(self.c), status="queued", extra={"charged": True})
        j["input"] = {"kind": "film", "film": "f1"}
        self.work = self.s.worker.work_dir(j["id"])
        self.film = castfilm.make(self.work / "films" / "f1")
        j["film_dir"] = str(self.film)
        j["status"], j["agent_session"] = "running", "sess-1"
        store.doc_put("job", j["id"], j)
        self.jid = j["id"]

    def tearDown(self):
        self.s.close()

    def test_resend_after_failure(self):
        from filmcheck import castnotes
        from studio import jobs, store
        url = f"/api/v1/jobs/{self.jid}/cast/resend"
        self.assertEqual(self.c.post(url, headers=W, json={}).status_code, 409)          # still running
        castnotes.add(self.film, "hero", text="bigger hair")
        castnotes.start_lot(self.film, self.jid)
        jobs.finish(self.jid, "failed", "AE crashed", refund=True)              # a studio failure: credit given back
        self.assertEqual(castnotes.load(self.film)["failed_lot"]["job"], self.jid)
        # the work folder outlives the usual hour while the notes can be sent again (jobs.update sets updated_at)
        old = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(timespec="seconds")
        with mock.patch.object(store, "now_iso", lambda: old):
            jobs.update(self.jid, lambda x: None)
        self.assertGreater(store.age_seconds(jobs.load(self.jid)["updated_at"]), 3600)
        self.s.worker.clean()
        self.assertTrue(self.film.is_dir())
        r =self.c.post(url, headers=W, json={})
        self.assertEqual(r.status_code, 200, r.text)
        j = jobs.load(self.jid)
        self.assertEqual((j["status"], j["error"], j["charged"]), ("waiting_review", None, True))   # charged again
        doc = castnotes.load(self.film)
        self.assertNotIn("failed_lot", doc)
        self.assertEqual(len(doc["lot"]["notes"]), 1)
        self.s.worker.resume_answered()
        j = jobs.load(self.jid)
        self.assertEqual(j["status"], "queued")
        self.assertIn("cast notes show f1", j["resume"])
        self.assertEqual(self.c.post(url, headers=W, json={}).status_code, 409)          # not failed any more

    def test_no_open_notes_or_other_job(self):
        from filmcheck import castnotes
        from studio import jobs
        castnotes.start_lot(self.film, self.jid)
        jobs.finish(self.jid, "stopped", "Stopped by the customer")
        r = self.c.post(f"/api/v1/jobs/{self.jid}/cast/resend", headers=W, json={})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "no_notes"))
        other = self.s.signup_verified("other@example.com")
        self.assertEqual(other.post(f"/api/v1/jobs/{self.jid}/cast/resend", headers=W, json={}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
