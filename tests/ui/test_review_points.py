"""specs/026: review points and edits on the film job page (local mode, API)."""
import json
import sys
import time
import unittest
from pathlib import Path

from helpers import REPO, Project, W, client

sys.path.insert(0, str(REPO / "tests" / "filmcheck"))
sys.path.insert(0, str(REPO / "tools"))
import samples  # noqa: E402


class ReviewPoints(unittest.TestCase):
    def setUp(self):
        self.p = Project(ports="18830-18839")
        self.film = samples.review_film(self.p.dir, "night", kit=True)
        out = self.p.cli("job", "start", "--kind", "film", "--name", "night", "--film", "night")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.jid = out.stdout.splitlines()[0]
        self.c = client()

    def tearDown(self):
        self.p.close()

    def steps(self):
        r = self.c.get(f"/api/v1/jobs/{self.jid}/steps")
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def wait_action(self, aid):
        from studio import actions
        self.assertTrue(actions.wait_idle(self.jid, 60))
        return self.c.get(f"/api/v1/jobs/{self.jid}/actions/{aid}").json()

    def test_steps(self):
        t0 = time.time()
        v = self.steps()
        self.assertLess(time.time() - t0, 3)
        self.assertEqual([s["name"] for s in v["steps"]][:3], ["Treatment", "Script", "Voice"])
        self.assertEqual(len(v["steps"]), 10)
        self.assertEqual(v["impact"]["shots"], ["Render", "Self-check", "Publish"])
        self.assertEqual(v["points"]["script"]["state"], "ready")
        self.assertTrue(v["editable"]["shots"])
        self.assertIn("bedroom", v["catalog"]["sets"])
        self.assertIn("left", v["catalog"]["act_prefixes"]["look"])
        r = self.c.get(f"/api/v1/jobs/{self.jid}/steps", headers={"If-None-Match": self.c.get(
            f"/api/v1/jobs/{self.jid}/steps").headers["etag"]})
        self.assertEqual(r.status_code, 304)

    def test_edit_paragraph(self):
        base = self.steps()["points"]["script"]["fingerprint"]
        r = self.c.post(f"/api/v1/jobs/{self.jid}/actions", headers=W, json={
            "point": "script", "op": "script-para", "args": {"para": "P03", "text": "By day three, you begin to see things that are not there."},
            "base": base})
        self.assertEqual(r.status_code, 202, r.text)
        a = self.wait_action(r.json()["id"])
        self.assertEqual(a["status"], "done", a)
        self.assertEqual(a["result"]["ref"], "P03")
        self.assertIn("you begin to see", (self.film / "SCRIPT.md").read_text())
        log = [x["line"] for x in self.c.get(f"/api/v1/jobs/{self.jid}").json()["log"]]
        self.assertTrue(any(x.startswith("Edit script-para P03: saved") for x in log), log)
        self.assertEqual(next(s for s in self.steps()["steps"] if s["name"] == "Voice")["state"], "stale")
        # the same base again: changed since
        r = self.c.post(f"/api/v1/jobs/{self.jid}/actions", headers=W, json={
            "point": "script", "op": "script-para", "args": {"para": "P03", "text": "Another text."}, "base": base})
        self.assertEqual(self.wait_action(r.json()["id"])["status"], "conflict")

    def test_bad_actions(self):
        for body in ({"point": "script", "op": "shot", "args": {}},
                     {"point": "bogus", "op": "script-para"},
                     {"point": "script", "op": "script-para", "args": {"text": "x" * 4001}},
                     {"point": "script", "op": "script-para", "base": "nothex"}):
            self.assertEqual(self.c.post(f"/api/v1/jobs/{self.jid}/actions", headers=W, json=body).status_code, 422, body)

    def test_approve_needs_base_and_passing_checks(self):
        summary = self.p.dir / "s.md"
        summary.write_text("Script ready")
        out = self.p.cli("review", "request", self.jid, "--kind", "script", "--film", "night", "--summary", str(summary))
        self.assertEqual(out.returncode, 0, out.stderr)
        rid = out.stdout.splitlines()[0]
        self.assertEqual(self.steps()["points"]["script"]["state"], "waiting")
        url = f"/api/v1/reviews/{rid}/decision"
        self.assertEqual(self.c.post(url, headers=W, json={"value": "approve"}).status_code, 422)
        self.assertEqual(self.c.post(url, headers=W, json={"value": "approve", "base": "0" * 16}).status_code, 409)
        p = self.film / "SCRIPT.md"
        p.write_text(p.read_text().replace("Target: 20s", "Target: 90s"))
        base = self.steps()["points"]["script"]["fingerprint"]
        r = self.c.post(url, headers=W, json={"value": "approve", "base": base})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "checks_not_passed"))
        p.write_text(p.read_text().replace("Target: 90s", "Target: 20s"))
        base = self.steps()["points"]["script"]["fingerprint"]
        self.assertEqual(self.c.post(url, headers=W, json={"value": "approve", "base": base}).status_code, 201)
        ch = json.loads((self.film / "checks.json").read_text())
        self.assertEqual(ch["reviews"]["approved"]["script"]["review_id"], rid)
        self.assertEqual(self.steps()["points"]["script"]["state"], "approved")
        # an approved point cannot be turned off
        r = self.c.put(f"/api/v1/jobs/{self.jid}/points", headers=W, json={"on": ["shots"]})
        self.assertEqual(r.status_code, 409)
        r = self.c.put(f"/api/v1/jobs/{self.jid}/points", headers=W, json={"on": ["script", "shots", "voice"]})
        self.assertEqual((r.status_code, r.json()["on"]), (200, ["script", "voice", "shots"]))

    def test_job_run_marks_the_film_busy(self):                     # FR-024, T016
        lock = self.film / ".check" / "busy.json"
        run = self.p.cli("job", "run", self.jid, "--step", "Voice", "--", "sh", "-c",
                         f"sleep 0.5; cat '{lock}'; cd '{REPO}' && sh bin/studio edit '{self.film}' script-para P03 --text-file /dev/null; echo code=$?")
        self.assertIn('"step": "Voice"', run.stdout)
        self.assertIn("busy: Voice", run.stdout)
        self.assertIn("code=5", run.stdout)
        self.assertFalse(lock.exists())
        v = self.steps()
        self.assertIsNone(v["busy"])

    def test_revise_records_rejection(self):
        summary = self.p.dir / "s.md"
        summary.write_text("Script ready")
        rid = self.p.cli("review", "request", self.jid, "--kind", "script", "--film", "night",
                         "--summary", str(summary)).stdout.splitlines()[0]
        r = self.c.post(f"/api/v1/reviews/{rid}/decision", headers=W, json={"value": "revise", "note": "Make P03 shorter."})
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(json.loads((self.film / "checks.json").read_text())["reviews"]["rejected"]["script"]["note"],
                         "Make P03 shorter.")


if __name__ == "__main__":
    unittest.main()
