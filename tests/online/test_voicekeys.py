"""specs/036 T010, T011: the owner's ElevenLabs key in Settings, and ElevenLabs for a job through the proxy.

The key is tried before it is kept, stored encrypted (0600 in a 0700 folder), never answered back or logged, and a job
reaches ElevenLabs only through the proxy with its job token."""
import json
import logging
import os
import stat
import sys
import threading
import time
import unittest
from pathlib import Path

import httpx

from helpers import PASSWORD, REPO, W, Studio, film_job

sys.path.insert(0, str(REPO / "tests" / "filmcheck"))
from fake_eleven import FakeEleven  # noqa: E402

KEY = "sk_live_0123456789abcdefKEY9"


class VoiceKeys(unittest.TestCase):
    def setUp(self):
        from studio import accounts
        self.fake = FakeEleven(key=KEY, left=500).start()
        self.old = os.environ.get("STUDIO_ELEVEN_URL")
        os.environ["STUDIO_ELEVEN_URL"] = self.fake.url
        self.s = Studio()
        accounts.signup("owner@example.com", PASSWORD, True, role="admin", verified=True)
        self.admin = self.s.client()
        assert self.admin.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": PASSWORD},
                               headers=W).status_code == 200
        self.c = self.s.signup_verified("maker@example.com")
        self.logs = []
        h = logging.Handler()
        h.emit = lambda rec: self.logs.append(rec.getMessage())
        self.h = h
        for name in ("studio.proxy",):
            logging.getLogger(name).addHandler(h)
            logging.getLogger(name).setLevel(logging.INFO)

    def tearDown(self):
        for name in ("studio.proxy",):
            logging.getLogger(name).removeHandler(self.h)
        self.s.close()
        self.fake.stop()
        if self.old is None:
            os.environ.pop("STUDIO_ELEVEN_URL", None)
        else:
            os.environ["STUDIO_ELEVEN_URL"] = self.old

    def put_key(self, key=KEY, client=None):
        return (client or self.admin).put("/api/v1/admin/elevenlabs-key", json={"key": key}, headers=W)

    # ---------- Settings (T010) ----------
    def test_good_key_is_kept_and_never_answered(self):
        r = self.put_key()
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((r.json()["set"], r.json()["last4"], r.json()["left"], r.json()["status"]), (True, "KEY9", 500, "ok"))
        st = self.admin.get("/api/v1/admin/settings").json()
        self.assertEqual(st["elevenlabs"]["last4"], "KEY9")
        self.assertNotIn(KEY, json.dumps(st))
        from studio import db, voicekeys
        d = db.data_dir() / "secrets"
        self.assertEqual(stat.S_IMODE(d.stat().st_mode), 0o700)
        for f in ("elevenlabs.json", ".key"):
            self.assertEqual(stat.S_IMODE((d / f).stat().st_mode), 0o600, f)
        self.assertNotIn(KEY.encode(), (d / "elevenlabs.json").read_bytes())       # encrypted at rest
        self.assertEqual(voicekeys.secret()["key"], KEY)

    def test_bad_key_is_not_kept(self):
        bad = "sk_bad_" + "x" * 30
        r = self.put_key(bad)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "elevenlabs_key_invalid"))
        self.assertNotIn(bad, r.text)
        from studio import db
        self.assertFalse((db.data_dir() / "secrets" / "elevenlabs.json").exists())
        self.assertFalse(self.admin.get("/api/v1/admin/settings").json()["elevenlabs"]["set"])

    def test_only_the_owner(self):
        self.assertEqual(self.put_key(client=self.c).status_code, 403)
        self.assertEqual(self.c.delete("/api/v1/admin/elevenlabs-key", headers=W).status_code, 403)

    def test_test_model_and_remove(self):
        self.put_key()
        self.fake.used = 120
        r = self.admin.post("/api/v1/admin/elevenlabs-key/test", headers=W)
        self.assertEqual(r.json()["left"], 380)
        r = self.admin.put("/api/v1/admin/elevenlabs-model", json={"model": "eleven_v3"}, headers=W)
        self.assertEqual(r.json()["model"], "eleven_v3")
        self.assertEqual(self.admin.delete("/api/v1/admin/elevenlabs-key", headers=W).status_code, 204)
        self.assertEqual(self.admin.get("/api/v1/admin/settings").json()["elevenlabs"]["status"], "none")

    # ---------- proxy (T011) ----------
    def proxy_call(self, what, body=None, token=None):
        return httpx.post(f"{self.s.proxy.url}/internal/tts/elevenlabs/{what}", json=body or {},
                          headers={"authorization": f"Bearer {token or self.token}"}, timeout=30)

    def job(self):
        import proxy
        jid = film_job(self.c).json()["id"]
        self.jid, self.token = jid, proxy.issue(jid)

    def test_proxy_needs_a_key_and_a_token(self):
        self.job()
        r = self.proxy_call("subscription")
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "no_key"))
        self.put_key()
        self.assertEqual(self.proxy_call("subscription", token="nope").status_code, 401)
        self.assertEqual(self.proxy_call("subscription").json()["left"], 500)
        self.assertEqual(len(self.proxy_call("voices").json()["voices"]), 4)

    def test_proxy_speaks_and_counts(self):
        from studio import jobs
        self.put_key()
        self.job()
        r = self.proxy_call("speak", {"voice_id": "v_narr", "text": "Secret words here.", "voice_settings": {"speed": 1}})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["chars"], 18)
        self.assertEqual(self.fake.calls[-1][2]["model_id"], "eleven_multilingual_v2")
        self.assertEqual(jobs.load(self.jid)["tts_chars"], 18)
        self.assertEqual(self.proxy_call("speak", {"voice_id": "v_narr", "text": "x" * 1001}).status_code, 400)
        blob = "\n".join(self.logs) + json.dumps(jobs.load(self.jid))
        self.assertNotIn(KEY, blob)
        self.assertNotIn("Secret words here", "\n".join(self.logs))                # logs: characters and voice only
        self.assertTrue(any("v_narr: 18 characters" in m for m in self.logs), self.logs[-5:])

    def test_proxy_maps_errors(self):
        self.put_key()
        self.job()
        self.fake.limit = 5
        r = self.proxy_call("speak", {"voice_id": "v_narr", "text": "too many characters"})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (402, "quota"))
        self.fake.key = "rotated-elsewhere-000000"
        r = self.proxy_call("subscription")
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (502, "invalid_key"))
        self.assertNotIn(KEY, r.text)

    def test_at_most_four_calls_at_once(self):
        self.put_key()
        self.job()
        live, peak, lock = [0], [0], threading.Lock()
        handler = self.fake.srv.RequestHandlerClass
        orig = handler.handle_any

        def slow(h, method):
            with lock:
                live[0] += 1
                peak[0] = max(peak[0], live[0])
            time.sleep(0.3)
            try:
                orig(h, method)
            finally:
                with lock:
                    live[0] -= 1
        handler.handle_any = slow
        try:
            ts = [threading.Thread(target=self.proxy_call, args=("speak", {"voice_id": "v_narr", "text": f"line {i}"}))
                  for i in range(8)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
        finally:
            handler.handle_any = orig
        self.assertLessEqual(peak[0], 4)
        self.assertGreaterEqual(peak[0], 2)


if __name__ == "__main__":
    unittest.main()
