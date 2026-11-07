"""Reference media never outlive learning: FR-018, FR-019, SC-004 (specs/007 tasks T029)."""
import datetime as dt
import time
import unittest

from helpers import TMP, W, Studio
from test_us2 import approve, learn_job, upload

MEDIA = {".mp4", ".mkv", ".webm", ".mov", ".m4a", ".wav", ".mp3", ".opus"}


class MediaGone(unittest.TestCase):
    def setUp(self):
        self.s = Studio()
        self.c = self.s.signup_verified("m@example.com")

    def tearDown(self):
        self.s.close()

    def assert_clean(self, jid, set_name):
        data = self.s.data
        left = [p for base in (data / "jobs" / jid, *data.glob("accounts/*/references"), data / "uploads")
                for p in (base.rglob("*") if base.exists() else []) if p.suffix.lower() in MEDIA]
        self.assertEqual(left, [])
        refs = list(data.glob(f"accounts/*/references/{set_name}"))
        self.assertEqual(len(refs), 1)
        ref = refs[0]
        self.assertEqual(list(ref.glob("profile/*/sheets/*")), [])
        self.assertEqual(list(ref.rglob("transcripts")) + list(ref.rglob("words.json")), [])
        self.assertLessEqual(len(list((ref / "proof").rglob("*.jpg"))), 6)
        self.assertTrue((ref / "profile" / "summary.json").is_file())          # the measurements stay
        self.assertNotIn("Secret", (ref / "set.json").read_text())
        self.assertEqual(self.c.get(f"/api/v1/sets/{set_name}/sheets").json(), {"removed": True, "sheets": {}})
        for path in (f"/sets/{set_name}/videos/v01.mp4", f"/sets/{set_name}/v01.mp4", f"/sets/{set_name}/sheets/v01.mp4",
                     f"/sets/{set_name}/proof/v01.mp4", "/uploads/v01.mp4", f"/sets/{set_name}/proof/../videos/v01.mp4"):
            r = self.c.get("/api/v1" + path)
            self.assertIn(r.status_code, (400, 404, 405), path)
            self.assertNotIn("video", r.headers.get("content-type", ""), path)

    def run_learn(self, channel):
        r = learn_job(self.c, source="youtube", channel=channel, count=1, rights_confirmed=True)
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["id"], r.json()["links"]["set"]

    def test_after_done(self):
        uid = upload(self.c, TMP / "good.mp4").json()["upload_id"]
        r = learn_job(self.c, source="upload", uploads=[uid])
        jid, set_name = r.json()["id"], r.json()["links"]["set"]
        self.s.start()
        for _ in range(2):
            j = self.s.wait(jid, statuses=("waiting_review",))
            n = len(j["review_ids"])
            approve(self.c, j["review_ids"][-1])
            end = time.time() + 30
            while time.time() < end:
                from studio import jobs
                j = jobs.load(jid)
                if j["status"] == "done" or (j["status"] == "waiting_review" and len(j["review_ids"]) > n):
                    break
                time.sleep(0.05)
        j = self.s.wait(jid)
        self.assertEqual(j["status"], "done", j["log"])
        self.assertTrue(j["media_removed_at"])
        self.assert_clean(jid, set_name)

    def test_after_failure(self):
        jid, set_name = self.run_learn("https://www.youtube.com/@will-fail")
        self.s.start()
        j = self.s.wait(jid)
        self.assertEqual(j["status"], "failed")
        time.sleep(0.3)
        self.assert_clean(jid, set_name)

    def test_after_stop(self):
        jid, set_name = self.run_learn("https://www.youtube.com/@will-hang")
        self.s.start()
        self.s.wait(jid, statuses=("running",))
        from studio import store
        end = time.time() + 20
        while time.time() < end and not list(store.account_dir(self.c.get("/api/v1/me").json()["id"])
                                              .glob(f"references/{set_name}/videos/*.mp4")):
            time.sleep(0.05)
        sh = self.c.get(f"/api/v1/sets/{set_name}/sheets").json()
        self.assertFalse(sh["removed"])                  # shown while learning runs
        self.assertEqual(self.c.post(f"/api/v1/jobs/{jid}/stop", headers=W).status_code, 200)
        end = time.time() + 20
        from studio import jobs
        while time.time() < end and not jobs.load(jid).get("media_removed_at"):
            time.sleep(0.05)
        self.assert_clean(jid, set_name)

    def test_cleaner_removes_leftovers_and_old_reviews(self):
        from studio import jobs, quotas, reviews, store
        quotas.update_settings({"quota_learns_default": 5})
        jid, set_name = self.run_learn("https://www.youtube.com/@leftover")
        jobs.finish(jid, "failed", error="worker died", failure_kind="studio")
        work = self.s.data / "jobs" / jid
        (work / "references" / set_name / "videos").mkdir(parents=True)
        (work / "references" / set_name / "videos" / "x.webm").write_bytes(b"v")
        (work / "a.wav").write_bytes(b"a")
        old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=2)).isoformat(timespec="seconds")
        jobs.update(jid, lambda j: None)
        store.doc_update("job", jid, lambda j: j.__setitem__("updated_at", old))
        # a job that waited for a review for too long
        wid, _ = self.run_learn("https://www.youtube.com/@waits")
        jobs.set_status(wid, "running")
        (TMP / "r.md").write_text("draft")
        with store.as_account(jobs.load(wid)["owner"]):
            rid = reviews.create(wid, "question", None, "draft")["id"]
        long_ago = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=8)).isoformat(timespec="seconds")
        store.doc_update("review", rid, lambda r: r.__setitem__("created_at", long_ago))
        self.s.worker.clean()
        self.assertFalse(work.exists())
        self.assertTrue(jobs.load(jid)["media_removed_at"])
        w = jobs.load(wid)
        self.assertEqual(w["status"], "stopped")
        self.assertTrue(any("waited 7 days" in p.read_text() for p in self.s.flush_mail()))


if __name__ == "__main__":
    unittest.main()
