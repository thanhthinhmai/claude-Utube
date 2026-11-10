"""User story 2: learn a style from YouTube or uploads, two reviews on the web (specs/007 tasks T028)."""
import unittest

from helpers import TMP, W, Studio, account_id, film_job


def upload(c, path, name="clip.mp4"):
    with open(path, "rb") as fh:
        return c.post("/api/v1/uploads", files={"file": (name, fh, "video/mp4")}, headers=W)


def learn_job(c, **body):
    return c.post("/api/v1/jobs", json={"kind": "learn", **body}, headers=W)


def approve(c, rid):
    r = c.post(f"/api/v1/reviews/{rid}/decision", json={"value": "approve"}, headers=W)
    assert r.status_code == 201, r.text


class US2(unittest.TestCase):
    def setUp(self):
        self.s = Studio()
        self.c = self.s.signup_verified("learn@example.com")

    def tearDown(self):
        self.s.close()

    def test_us2_youtube_needs_rights(self):
        from studio import db
        r = learn_job(self.c, source="youtube", channel="https://www.youtube.com/@some-channel", count=3)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "rights_required"))
        self.assertEqual(learn_job(self.c, source="youtube", channel="https://evil.example/@x", count=3,
                                   rights_confirmed=True).status_code, 422)
        self.assertEqual(learn_job(self.c, source="youtube", channel="@some-channel", count=6,
                                   rights_confirmed=True).json()["error"]["code"], "too_many_videos")
        r = learn_job(self.c, source="youtube", channel="@some-channel", count=3, rights_confirmed=True)
        self.assertEqual(r.status_code, 201, r.text)
        with db.read() as con:
            row = con.execute("SELECT * FROM rights WHERE job_id = ?", (r.json()["id"],)).fetchone()
        self.assertEqual((row["account_id"], row["channel_url"], row["text_version"]),
                         (account_id(self.c), "https://www.youtube.com/@some-channel", "2.1.0"))
        self.assertTrue(row["confirmed_at"])
        self.assertEqual(self.c.get("/api/v1/me").json()["quota"]["learns"]["used"], 1)

    def test_uploads(self):
        bad = TMP / "not-a-video.mp4"
        bad.write_text("hello")
        self.assertEqual(upload(self.c, bad).json()["error"]["code"], "bad_video")
        self.assertEqual(upload(self.c, TMP / "good.mp4", "clip.txt").json()["error"]["code"], "bad_video")
        r = upload(self.c, TMP / "good.mp4")
        self.assertEqual(r.status_code, 201, r.text)
        self.assertAlmostEqual(r.json()["seconds"], 3, delta=0.2)
        uid = r.json()["upload_id"]
        other = self.s.signup_verified("other@example.com")       # another customer cannot use it
        self.assertEqual(learn_job(other, source="upload", uploads=[uid]).status_code, 404)
        from studio import quotas
        quotas.update_settings({"upload_max_mb": 1})
        big = TMP / "big.mp4"
        big.write_bytes((TMP / "good.mp4").read_bytes() + b"\0" * (1024 * 1024))
        self.assertEqual(upload(self.c, big).status_code, 413)
        self.assertFalse(any(p.name.startswith("u-") and p.suffix == ".mp4" and p.stat().st_size > 1024 * 1024
                             for p in (self.s.data / "uploads").rglob("*")))

    def test_us2_learn_from_uploads_two_reviews(self):
        uid = upload(self.c, TMP / "good.mp4").json()["upload_id"]
        r = learn_job(self.c, source="upload", uploads=[uid])
        self.assertEqual(r.status_code, 201, r.text)
        jid, set_name = r.json()["id"], r.json()["links"]["set"]
        self.s.start()
        j = self.s.wait(jid, statuses=("waiting_review", "failed"))
        self.assertEqual(j["status"], "waiting_review", j["log"])
        # while learning: the contact sheets can be reviewed, the videos never
        sh = self.c.get(f"/api/v1/sets/{set_name}/sheets").json()
        self.assertFalse(sh["removed"])
        self.assertEqual(sh["sheets"]["v01"][0], "v01_0001.jpg")
        self.assertEqual(self.c.get(f"/api/v1/sets/{set_name}/sheets/v01/v01_0001.jpg").status_code, 404)
        self.assertEqual(self.c.get(f"/api/v1/sets/{set_name}/sheets/v01_0001.jpg").status_code, 200)
        r1 = self.c.get(f"/api/v1/reviews/{j['review_ids'][-1]}").json()
        self.assertEqual((r1["kind"], r1["set"]), ("style-1", set_name))
        approve(self.c, r1["id"])
        import time
        from studio import jobs
        end = time.time() + 30
        while time.time() < end:                         # resumed, then asks for review 2
            j = jobs.load(jid)
            if j["status"] in ("waiting_review", "failed") and len(j["review_ids"]) >= 2:
                break
            time.sleep(0.05)
        r2 = self.c.get(f"/api/v1/reviews/{j['review_ids'][-1]}").json()
        self.assertEqual(r2["kind"], "style-2")
        self.assertTrue(r2["compare"]["pass"])
        approve(self.c, r2["id"])
        j = self.s.wait(jid)
        self.assertEqual(j["status"], "done", j["log"])
        slug = j["links"]["style"]
        self.assertIn(slug, [x["slug"] for x in self.c.get("/api/v1/styles").json()["styles"]])
        self.assertEqual(film_job(self.c, style=slug).status_code, 201)       # usable for a film right away
        self.assertIn(f"| {slug} |", (self.s.data / "accounts" / account_id(self.c) / "my-styles" / "README.md").read_text())
        # another customer does not see it
        other = self.s.signup_verified("o2@example.com")
        self.assertEqual(other.get(f"/api/v1/styles/{slug}").status_code, 404)
        # delete it
        self.assertEqual(self.c.delete(f"/api/v1/styles/{slug}", headers=W).status_code, 409)   # the film job uses it
        jobs_ = [x for x in self.c.get("/api/v1/jobs").json()["jobs"] if x["kind"] == "film"]
        self.c.post(f"/api/v1/jobs/{jobs_[0]['id']}/stop", headers=W)
        self.assertEqual(self.c.delete(f"/api/v1/styles/{slug}", headers=W).status_code, 204)
        self.assertEqual(self.c.get(f"/api/v1/styles/{slug}").status_code, 404)


if __name__ == "__main__":
    unittest.main()
