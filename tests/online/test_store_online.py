"""Jobs, reviews and decisions in SQLite (T005); phase-1 behaviour is covered by tests/ui."""
import threading
import unittest

from helpers import OnlineProject


class StoreOnline(unittest.TestCase):
    def setUp(self):
        self.p = OnlineProject()
        from studio import jobs, reviews, store
        self.jobs, self.reviews, self.store = jobs, reviews, store

    def tearDown(self):
        self.p.close()

    def test_jobs_live_in_the_database_with_an_owner(self):
        j = self.jobs.create("film", "demo", owner="a-1", status="queued")
        self.assertEqual((j["status"], j["step"], j["charged"], j["cost_usd"]), ("queued", "Queued", False, 0.0))
        self.assertFalse((self.p.dir / ".studio" / "jobs" / f"{j['id']}.json").exists())     # not a file
        self.assertTrue((self.p.data / "studio.db").exists())
        self.jobs.step(j["id"], "Music")
        self.assertEqual(self.jobs.load(j["id"])["step"], "Music")
        with self.assertRaises(self.store.StudioError):
            self.jobs.load(j["id"], owner="a-2")                                            # someone else's
        self.jobs.create("film", "other", owner="a-2", status="queued")
        self.assertEqual([x["name"] for x in self.jobs.all_jobs("a-1")], ["demo"])
        self.assertEqual(len(self.jobs.all_jobs()), 2)

    def test_first_decision_wins_across_threads(self):
        j = self.jobs.create("learn", "demo", owner="a-1")
        r = self.reviews.create(j["id"], "style-1", "demo-set", "# Summary")
        self.assertEqual(r["owner"], "a-1")
        won, lost = [], []

        def go(v):
            try:
                won.append(self.reviews.decide(r["id"], v, "darker please" if v == "revise" else None))
            except self.store.StudioError as e:
                lost.append(e.code)
        ts = [threading.Thread(target=go, args=(v,)) for v in ("approve", "revise") * 4]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual((len(won), set(lost)), (1, {"already_decided"}))
        self.assertEqual(self.reviews.load(r["id"])["decision"]["value"], won[0]["value"])
        self.assertNotIn("owner", self.reviews.load(r["id"])["decision"])
        self.assertEqual(len(self.reviews.all_reviews("decided", "a-1")), 1)
        self.assertEqual(self.reviews.all_reviews(owner="a-2"), [])

    def test_versions_change_when_a_job_changes(self):
        j = self.jobs.create("film", "demo", owner="a-1", status="queued")
        before = self.store.doc_versions("a-1")
        self.jobs.step(j["id"], "Look")
        after = self.store.doc_versions("a-1")
        self.assertNotEqual(before[f"{j['id']}.json"], after[f"{j['id']}.json"])
        self.assertEqual(self.store.doc_versions("a-2"), {})


if __name__ == "__main__":
    unittest.main()
