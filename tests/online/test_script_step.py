"""The Script step in online film jobs (specs/010 T020): SC-001, FR-010, FR-016, FR-019, FR-007b."""
import json
import time
import unittest

from helpers import W, Studio, account_id, film_job


class ScriptStep(unittest.TestCase):
    def setUp(self):
        from studio import quotas
        self.s = Studio()
        quotas.update_settings({"quota_films_default": 5})
        self.c = self.s.signup_verified("writer@example.com")

    def tearDown(self):
        self.s.close()

    def film_dir(self, j):
        from studio import store
        return store.account_dir(account_id(self.c)) / "films" / j["links"]["film"]

    def run_job(self, idea, **extra):
        jid = film_job(self.c, idea=idea, **extra).json()["id"]
        self.s.start()
        return jid, self.s.wait(jid, timeout=90)

    def test_one_fix_round_then_voice(self):                     # SC-001
        _, j = self.run_job("A fox [narration] [editor-p1 P02]")
        self.assertEqual(j["status"], "done", j["log"][-6:])
        d = self.film_dir(j)
        s = json.loads((d / "checks.json").read_text())["script"]
        self.assertEqual((s["verdict"], s["fix_rounds"], [e["p1"] for e in s["editor"]]), ("pass", 1, [1, 0]))
        passed_at = (d / ".check" / "review-r2.json").stat().st_mtime
        self.assertLessEqual(passed_at, (d / "voices" / "words.json").stat().st_mtime)
        self.assertIn("Script", [ln["line"] for ln in j["log"]])

    def test_two_fix_rounds_used_up(self):                       # FR-010
        jid, j = self.run_job("A fox [narration] [editor-low]")
        self.assertEqual((j["status"], j["failure_kind"]), ("failed", "studio"))
        self.assertIn("did not pass review", j["error"])
        self.assertEqual(self.c.get("/api/v1/me").json()["quota"]["films"]["used"], 0)      # credit given back
        self.assertFalse((self.s.data / "jobs" / jid / "films" / j["input"]["film"] / "voices").exists())

    def test_editor_calls_count_for_the_job(self):               # FR-016
        from studio import db
        jid, j = self.run_job("A fox [narration]")
        self.assertEqual(j["status"], "done", j["log"][-6:])
        with db.read() as con:
            n = con.execute("SELECT count(*) FROM call WHERE job_id = ?", (jid,)).fetchone()[0]
        self.assertGreaterEqual(n, 1)
        self.assertGreater(j.get("tokens") or 0, 0)

    def test_editor_model_from_settings(self):                   # FR-007b
        from studio import quotas
        quotas.update_settings({"editor_model": "sonnet"})
        _, j = self.run_job("A fox [narration]")
        self.assertEqual(j["status"], "done", j["log"][-6:])
        args = json.loads((self.film_dir(j) / ".check" / "editor-args.json").read_text())
        self.assertEqual(args[args.index("--model") + 1], "sonnet")

    def test_treatment_review_shows_the_script(self):           # FR-019
        from studio import jobs, reviews
        jid = film_job(self.c, idea="A fox [narration]", review_treatment=True).json()["id"]
        self.s.start()
        j = self.s.wait(jid, statuses=("waiting_review", "failed", "done"), timeout=60)
        self.assertEqual(j["status"], "waiting_review", j["log"][-6:])
        r = reviews.load(j["review_ids"][-1])
        self.assertEqual(r["kind"], "treatment")
        for s in ("[P01]", "## Scores", "Editor: 9"):
            self.assertIn(s, r["summary_md"])
        self.assertFalse((self.s.data / "jobs" / jid / "films" / j["input"]["film"] / "voices").exists())
        # the customer asks for changes: one more review round that does not count against the limit
        self.c.post(f"/api/v1/reviews/{r['id']}/decision", json={"value": "revise", "note": "brighter"}, headers=W)
        j = self.s.wait(jid, statuses=("waiting_review", "failed", "done"), timeout=60)
        end = time.time() + 30
        while len(jobs.load(jid)["review_ids"]) < 2 and time.time() < end:
            time.sleep(0.05)
        j = jobs.load(jid)
        self.assertEqual(len(j["review_ids"]), 2, j["log"][-6:])
        r2 = reviews.load(j["review_ids"][-1])
        self.assertIn("bright gold", r2["summary_md"])
        self.c.post(f"/api/v1/reviews/{r2['id']}/decision", json={"value": "approve", "note": ""}, headers=W)
        j = self.s.wait(jid, timeout=60)
        self.assertEqual(j["status"], "done", j["log"][-6:])
        s = json.loads((self.film_dir(j) / "checks.json").read_text())["script"]
        self.assertEqual(s["fix_rounds"], 0)
        self.assertTrue(s["editor"][-1]["customer_round"])

    def test_qc_problem_gets_one_fix_round(self):               # FR-013
        from studio import jobs
        _, j = self.run_job("A fox [qc-bad]")
        self.assertEqual(j["status"], "done", j["log"][-6:])
        self.assertTrue(any("stands still" in ln["line"] for ln in j["log"]))
        self.assertEqual(j["qa_retries"], 1)
        self.assertTrue(j["qa"]["film"]["pass"])
        _, j = self.run_job("A fox [qc-bad-always]")
        self.assertEqual((j["status"], j["failure_kind"]), ("failed", "studio"))
        self.assertIn("stands still", j["error"])

    def test_narration_film_is_measured(self):
        _, j = self.run_job("A fox [narration]")
        self.assertEqual(j["status"], "done", j["log"][-6:])
        m = j["qa"]["film"]["measures"]
        self.assertLessEqual(m["silence_ratio"], 0.2)
        self.assertLessEqual(m["tail_s"], 1.5)

    def test_changed_version_keeps_its_reviewed_script(self):  # spec Edge Cases: changes to a finished film, T036
        _, j = self.run_job("A fox [narration]")
        self.assertEqual(j["status"], "done", j["log"][-6:])
        r = self.c.post("/api/v1/jobs", json={"kind": "film", "revise_of": j["links"]["film"], "note": "warmer colours"},
                        headers=W)
        self.assertEqual(r.status_code, 201, r.text)
        j2 = self.s.wait(r.json()["id"], timeout=90)
        self.assertEqual(j2["status"], "done", j2["log"][-6:])
        self.assertEqual(j2["qa"]["script"]["verdict"], "pass")
        self.assertTrue(j2["qa"]["film"]["measures"]["voice_matches_script"])

    def test_film_without_narration_needs_no_script(self):
        _, j = self.run_job("A fox with no words")
        self.assertEqual(j["status"], "done", j["log"][-6:])


if __name__ == "__main__":
    unittest.main()
