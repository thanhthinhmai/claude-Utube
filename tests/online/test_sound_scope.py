"""specs/037 T009: a job reaches the sound library through the proxy, with its owner's scope (FR-013a): the studio
owner's films may use Sonniss sounds, a member's films CC0 sounds only. The same rule holds for app previews."""
import os
import sys
import unittest

import httpx

from helpers import PASSWORD, REPO, W, Studio, film_job

sys.path.insert(0, str(REPO / "tests" / "filmcheck"))
import soundfix  # noqa: E402


class SoundScope(unittest.TestCase):
    def setUp(self):
        from studio import accounts, db
        self.s = Studio()
        accounts.signup("owner@example.com", PASSWORD, True, role="admin", verified=True)
        self.admin = self.s.client()
        assert self.admin.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": PASSWORD},
                               headers=W).status_code == 200
        self.c = self.s.signup_verified("maker@example.com")
        self.old = os.environ.get("STUDIO_DATA")
        from filmcheck import soundlib
        self.lib = soundfix.make(db.data_dir() / "packs" / "GDC2024")
        soundlib.add_root(self.lib)
        soundlib.index()
        import shutil
        cc0 = soundlib.sound_root() / "freesound" / "9.wav"
        cc0.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(next(self.lib.rglob("GLASBrk_Bottle*.wav")), cc0)
        c = soundlib.connect()
        soundlib.put(c, {"id": "fs:9", "path": str(cc0), "size": 1, "mtime_ns": 1,
                         "name": "window glass breaking cc0", "category": "", "subcategory": "", "description": "",
                         "keywords": "glass shatter", "duration": 0.5, "rate": 22050, "channels": 1,
                         "source": "freesound", "credit": "Freesound #9 by z", "url": "https://freesound.org/s/9/",
                         "license": "cc0-1.0", "fetched_at": "t", "ok": 1, "root": ""})
        c.commit()
        c.close()
        self.sonniss = soundlib.search("window shatter large")[0]["id"]
        assert self.sonniss.startswith("s:")

    def tearDown(self):
        self.s.close()

    def token(self, client):
        import proxy
        from studio import db
        jid = film_job(client).json()["id"]
        (db.data_dir() / "jobs" / jid / "films" / "f1").mkdir(parents=True)
        return jid, proxy.issue(jid)

    def call(self, what, body, token):
        return httpx.post(f"{self.s.proxy.url}/internal/sound/{what}", json=body,
                          headers={"authorization": f"Bearer {token}"}, timeout=30)

    def test_owner_job_sees_sonniss(self):
        from studio import db
        jid, t = self.token(self.admin)
        r = self.call("search", {"query": "window shatter"}, t)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["scope"], "all")
        self.assertIn(self.sonniss, [h["id"] for h in r.json()["results"]])
        self.assertNotIn("path", r.json()["results"][0])
        r = self.call("fetch", {"entry": self.sonniss, "film": "f1"}, t)
        self.assertEqual(r.status_code, 200, r.text)
        f = db.data_dir() / "jobs" / jid / "films" / "f1" / r.json()["path"]
        self.assertTrue(f.is_file() and f.parent.name == "cache")

    def test_member_job_sees_cc0_only(self):
        jid, t = self.token(self.c)
        r = self.call("search", {"query": "window shatter"}, t)
        self.assertEqual(r.json()["scope"], "cc0")
        self.assertEqual([h["id"] for h in r.json()["results"]], ["fs:9"])
        r = self.call("fetch", {"entry": self.sonniss, "film": "f1"}, t)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (403, "scope"))
        self.assertEqual(self.call("fetch", {"entry": "fs:9", "film": "f1"}, t).status_code, 200)
        self.assertEqual(self.call("fetch", {"entry": "fs:9", "film": "../x"}, t).status_code, 400)
        self.assertEqual(self.call("search", {"query": "x"}, "nope").status_code, 401)

    def test_app_preview_and_settings(self):
        self.assertEqual(self.admin.get(f"/api/v1/sound/preview/{self.sonniss}").status_code, 200)
        r = self.c.get(f"/api/v1/sound/preview/{self.sonniss}")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.c.get("/api/v1/sound/preview/fs:9").status_code, 200)
        st = self.admin.get("/api/v1/admin/sound").json()
        self.assertEqual(st["by_source"]["sonniss"], 11)
        self.assertFalse(st["freesound"]["set"])
        self.assertEqual(self.c.get("/api/v1/admin/sound").status_code, 403)
        from filmcheck import soundlib
        ref = soundlib.repo() / "references" / "set1"
        ref.mkdir(parents=True, exist_ok=True)
        r = self.admin.post("/api/v1/admin/sound", json={"path": str(ref)}, headers=W)
        self.assertEqual(r.status_code, 422)


class FreesoundKey(unittest.TestCase):
    """T004: a second named key (freesound) kept like the ElevenLabs one: tried first, 0600, last 4 characters only."""
    KEY = "fs_live_0123456789abcdefKEY7"

    def setUp(self):
        from fake_freesound import FakeFreesound
        from studio import accounts
        self.fake = FakeFreesound(key=self.KEY).start()
        self.old = os.environ.get("STUDIO_FREESOUND_URL")
        os.environ["STUDIO_FREESOUND_URL"] = self.fake.url
        self.s = Studio()
        accounts.signup("owner@example.com", PASSWORD, True, role="admin", verified=True)
        self.admin = self.s.client()
        assert self.admin.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": PASSWORD},
                               headers=W).status_code == 200

    def tearDown(self):
        self.s.close()
        self.fake.stop()
        if self.old is None:
            os.environ.pop("STUDIO_FREESOUND_URL", None)
        else:
            os.environ["STUDIO_FREESOUND_URL"] = self.old

    def test_key_is_tried_kept_and_never_answered(self):
        import stat
        from studio import db, voicekeys
        r = self.admin.put("/api/v1/admin/sound/freesound-key", json={"key": "fs_bad_" + "x" * 20}, headers=W)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "freesound_key_invalid"))
        self.assertFalse(voicekeys.status("freesound")["set"])
        r = self.admin.put("/api/v1/admin/sound/freesound-key", json={"key": self.KEY}, headers=W)
        self.assertEqual((r.status_code, r.json()["last4"]), (200, "KEY7"))
        self.assertNotIn(self.KEY, r.text + self.admin.get("/api/v1/admin/sound").text)
        f = db.data_dir() / "secrets" / "freesound.json"
        self.assertEqual(stat.S_IMODE(f.stat().st_mode), 0o600)
        self.assertNotIn(self.KEY.encode(), f.read_bytes())
        self.assertEqual(voicekeys.secret("freesound")["key"], self.KEY)
        self.assertIsNone(voicekeys.secret())                                  # ElevenLabs untouched
        self.assertEqual(self.admin.delete("/api/v1/admin/sound/freesound-key", headers=W).status_code, 204)
        self.assertIsNone(voicekeys.secret("freesound"))


if __name__ == "__main__":
    unittest.main()
