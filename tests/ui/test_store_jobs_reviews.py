import multiprocessing as mp
import os
import unittest

from helpers import Project
from studio import jobs, reviews, store
from studio.store import StudioError


def _decide(args):
    root, rid, src = args
    os.environ["STUDIO_ROOT"] = root
    try:
        reviews.decide(rid, "approve", None, src)
        return "won"
    except StudioError as e:
        return e.code


class StoreJobsReviews(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.real_clock = store.clock

    def tearDown(self):
        store.clock = self.real_clock
        self.p.close()

    def test_job_lifecycle_and_log_limit(self):
        j = jobs.create("learn", "demo", {"set": "demo-set"})
        self.assertEqual(j["owner"], "local")
        for i in range(70):
            jobs.log(j["id"], f"dòng {i} " + "x" * 400)
        j2 = jobs.load(j["id"])
        self.assertEqual(len(j2["log"]), 50)
        self.assertLessEqual(max(len(x["line"]) for x in j2["log"]), 300)
        jobs.step(j["id"], "Đo video", jobs.parse_progress("3/5"))
        self.assertEqual(jobs.load(j["id"])["progress"], {"done": 3, "total": 5})
        for bad in ("6/5", "a/b", "1/0"):
            with self.assertRaises(StudioError):
                jobs.parse_progress(bad)
        jobs.finish(j["id"], "done", links={"style": "demo-style"})
        with self.assertRaises(StudioError):
            jobs.step(j["id"], "sau khi xong")

    def test_inactive_after_ten_minutes(self):  # FR-005
        j = jobs.create("film", "phim")
        self.assertEqual(jobs.shown_status(jobs.load(j["id"])), "running")
        t = store.clock()
        store.clock = lambda: t + 601
        self.assertEqual(jobs.shown_status(jobs.load(j["id"])), "inactive")

    def test_review_rules(self):  # FR-007, FR-010
        j = jobs.create("learn", "demo", {"set": "demo-set"})
        r1 = reviews.create(j["id"], "style-1", "demo-set", "# Tóm tắt")
        self.assertEqual(jobs.load(j["id"])["status"], "waiting_review")
        with self.assertRaises(StudioError) as e:
            reviews.decide(r1["id"], "revise", "")
        self.assertEqual(e.exception.code, "note_required")
        with self.assertRaises(StudioError) as e:
            reviews.decide(r1["id"], "accept_anyway")
        self.assertEqual(e.exception.code, "value_not_allowed")
        reviews.decide(r1["id"], "revise", "đổi màu nền")
        with self.assertRaises(StudioError) as e:
            reviews.decide(r1["id"], "approve")
        self.assertEqual(e.exception.code, "already_decided")
        r2 = reviews.create(j["id"], "style-2", "demo-set", "ghi chú", final_round=True)
        self.assertEqual(r2["compare"]["palette_matched"], 5)
        reviews.decide(r2["id"], "accept_anyway")

    def test_first_decision_wins_across_processes(self):  # FR-010
        j = jobs.create("learn", "demo", {"set": "demo-set"})
        r = reviews.create(j["id"], "style-1", "demo-set", "x")
        with mp.get_context("fork").Pool(8) as pool:
            res = pool.map(_decide, [(str(self.p.dir), r["id"], "ui" if i % 2 else "chat") for i in range(16)])
        self.assertEqual(res.count("won"), 1, res)
        self.assertEqual(res.count("already_decided"), 15)

    def test_waiting_resume_when_nobody_waits(self):  # edge case: session closed
        j = jobs.create("learn", "demo", {"set": "demo-set"})
        r = reviews.create(j["id"], "style-1", "demo-set", "x")
        reviews.decide(r["id"], "approve")
        self.assertEqual(reviews.job_view(jobs.load(j["id"]))["status"], "waiting_resume")
        self.assertIsNotNone(reviews.poll(r["id"]))                    # a waiter picks it up
        self.assertEqual(reviews.job_view(jobs.load(j["id"]))["status"], "waiting_review")
        reviews.resume(r["id"], {"value": "approve"})
        self.assertEqual(jobs.load(j["id"])["status"], "running")

    def test_atomic_write_never_partial(self):
        p = store.state_dir() / "x.json"
        store.write_json(p, {"a": 1})
        self.assertFalse([f for f in p.parent.iterdir() if f.name.endswith(".tmp")])
        self.assertTrue(store.create_exclusive(store.state_dir() / "y.json", {}))
        self.assertFalse(store.create_exclusive(store.state_dir() / "y.json", {}))


if __name__ == "__main__":
    unittest.main()
