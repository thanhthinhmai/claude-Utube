"""specs/026 online: a film waits at its script review point without holding a container, the owner approves on
the content shown, the job goes back in the queue and the agent goes on (T024, SC-005)."""
import time
import unittest

from helpers import W, Studio, film_job


class ReviewPointsOnline(unittest.TestCase):
    def setUp(self):
        self.s = Studio()

    def tearDown(self):
        self.s.close()

    def test_script_point_waits_then_resumes(self):
        c = self.s.signup_verified("rp@example.com")
        other = self.s.signup_verified("rp-other@example.com")
        jid = film_job(c, idea="A fox and a lantern [narration] [point-script]").json()["id"]
        self.s.start()
        j = self.s.wait(jid, statuses=("waiting_review",), timeout=90)
        end = time.time() + 10
        while jid in self.s.worker.runs and time.time() < end:      # the agent ended its turn (exit 10)
            time.sleep(0.05)
        self.assertNotIn(jid, self.s.worker.runs)                    # no container while it waits (FR-023)
        rid = j["review_ids"][-1]
        self.assertEqual(c.get(f"/api/v1/reviews/{rid}").json()["kind"], "script")
        v = c.get(f"/api/v1/jobs/{jid}/steps").json()
        self.assertEqual(v["points"]["script"]["state"], "waiting")
        self.assertEqual(other.get(f"/api/v1/jobs/{jid}/steps").status_code, 404)
        self.assertEqual(other.post(f"/api/v1/jobs/{jid}/actions", headers=W,
                                    json={"point": "script", "op": "script-para", "args": {}}).status_code, 404)
        # an edit while it waits: run by the worker in a throw-away container, no Claude call (T054, T055)
        import re
        from studio import api_online
        calls = api_online.job_usage(jid)["calls"]
        script = c.get(f"/api/v1/jobs/{jid}/files/SCRIPT.md").text
        p01 = re.search(r"^\[P01\] (.*)$", script, re.M).group(1)
        a = c.post(f"/api/v1/jobs/{jid}/actions", headers=W, json={"point": "script", "op": "script-para",
                   "args": {"para": "P01", "text": p01.replace(" a ", " one ", 1) if " a " in p01 else p01 + " Yes."},
                   "base": v["points"]["script"]["fingerprint"]}).json()
        end = time.time() + 60
        while time.time() < end:
            x = c.get(f"/api/v1/jobs/{jid}/actions/{a['id']}").json()
            if x["status"] not in ("queued", "running"):
                break
            time.sleep(0.1)
        self.assertEqual(x["status"], "done", x)
        self.assertEqual(x["result"]["ref"], "P01")
        self.assertEqual(api_online.job_usage(jid)["calls"], calls)          # no Claude call for an edit
        self.assertNotIn(jid, self.s.worker.runs)                           # and no agent started for it
        v = c.get(f"/api/v1/jobs/{jid}/steps").json()
        r = c.post(f"/api/v1/reviews/{rid}/decision", headers=W,
                   json={"value": "approve", "base": v["points"]["script"]["fingerprint"]})
        self.assertEqual(r.status_code, 201, r.text)
        t0 = time.time()
        while time.time() - t0 < 60:                                 # back in the queue and running again (SC-005)
            if any("Resumed after script review" in x["line"] for x in c.get(f"/api/v1/jobs/{jid}").json()["log"]):
                break
            time.sleep(0.1)
        self.assertLess(time.time() - t0, 60)
        j = self.s.wait(jid, timeout=90)
        self.assertEqual(j["status"], "done", j["log"])
        self.assertTrue(any("answer: The customer approved the script review" in x["line"] for x in j["log"]), j["log"])


if __name__ == "__main__":
    unittest.main()
