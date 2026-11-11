"""Channels and lessons online (specs/012 T020, T021; US3, FR-016, FR-017, SC-001, SC-005; contracts/api.md)."""
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

from helpers import PASSWORD, REPO, W, Studio, account_id, first_library_style

NODE_MODULES = REPO / "lib" / "lemo-opuscar" / "node_modules"


def channel_body(slug="honey-facts", **over):
    b = {"slug": slug, "name": "Honey Facts", "language": "en", "seconds": 20, "style": first_library_style(),
         "voice": "af_bella", "speed": 1.0, "hashtags": ["#honey"], "banned": ["shocking"], "title_max": 70,
         "audience": "curious adults"}
    b.update(over)
    return b


class ChannelsApi(unittest.TestCase):
    def setUp(self):
        from studio import accounts, quotas
        self.s = Studio()
        quotas.update_settings({"quota_films_default": 5})
        accounts.signup("owner@example.com", PASSWORD, True, role="admin", verified=True)
        self.admin = self.s.client()
        assert self.admin.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": PASSWORD},
                               headers=W).status_code == 200
        self.c = self.s.signup_verified("maker@example.com")

    def tearDown(self):
        self.s.close()

    def test_profile_and_lessons(self):
        c = self.c
        r = c.post("/api/v1/channels", json=channel_body(), headers=W)
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(c.post("/api/v1/channels", json=channel_body(), headers=W).status_code, 409)
        self.assertEqual(c.post("/api/v1/channels", json=channel_body("bad", hashtags=["#shocking"]), headers=W).status_code, 422)
        self.assertEqual(c.post("/api/v1/channels", json=channel_body("bad2", style="nope"), headers=W).status_code, 422)
        self.assertEqual(c.put("/api/v1/channels/honey-facts", json={"seconds": 30}, headers=W).json()["seconds"], 30)
        self.assertEqual(c.post("/api/v1/channels/honey-facts/decisions", json={"text": "No lyrics"}, headers=W).status_code, 201)
        l1 = c.post("/api/v1/channels/honey-facts/lessons", json={"what": "w", "why": "y", "stop": "s",
                                                                  "rule": "phrase:you won't believe"}, headers=W)
        self.assertEqual((l1.status_code, l1.json()["status"]), (201, "active"))
        l2 = c.post("/api/v1/channels/honey-facts/lessons", json={"what": "w2", "why": "y", "stop": "s"}, headers=W).json()
        self.assertEqual(c.post(f"/api/v1/channels/honey-facts/lessons/{l2['n']}/retire", headers=W).json()["status"], "retired")
        self.assertEqual(c.post("/api/v1/channels/honey-facts/lessons/1/approve", headers=W).status_code, 409)   # not a draft
        self.assertEqual(c.put("/api/v1/channels/honey-facts/lessons/1", json={"what": "x"}, headers=W).status_code, 409)
        got = c.get("/api/v1/channels/honey-facts").json()
        self.assertEqual([x["status"] for x in got["lessons"]], ["active", "retired"])
        self.assertEqual(got["decisions"][0]["text"], "No lyrics")
        row = c.get("/api/v1/channels").json()["channels"][0]
        self.assertEqual((row["slug"], row["lessons_active"]), ("honey-facts", 1))

    def test_others_cannot_see_or_change(self):                      # SC-005
        self.c.post("/api/v1/channels", json=channel_body(), headers=W)
        other = self.s.signup_verified("other@example.com")
        self.assertEqual(other.get("/api/v1/channels").json()["channels"], [])
        for method, path, body in (("get", "/api/v1/channels/honey-facts", None),
                                   ("put", "/api/v1/channels/honey-facts", {"seconds": 9}),
                                   ("post", "/api/v1/channels/honey-facts/decisions", {"text": "x"}),
                                   ("post", "/api/v1/channels/honey-facts/lessons", {"what": "w", "why": "y", "stop": "s"}),
                                   ("put", "/api/v1/channels/honey-facts/lessons/1", {"what": "x"}),
                                   ("post", "/api/v1/channels/honey-facts/lessons/1/approve", None),
                                   ("post", "/api/v1/channels/honey-facts/lessons/1/retire", None)):
            r = getattr(other, method)(path, json=body, headers=W) if body is not None else getattr(other, method)(path, headers=W)
            self.assertEqual(r.status_code, 404, (method, path))
        self.assertEqual(self.c.get("/api/v1/lessons/shared").status_code, 403)
        self.assertEqual(self.c.post("/api/v1/lessons/shared", json={"what": "w", "why": "y", "stop": "s"}, headers=W).status_code, 403)
        self.assertEqual(self.c.post("/api/v1/lessons/shared/1/retire", headers=W).status_code, 403)

    def test_limits(self):
        from filmcheck import channels
        old = channels.MAX_CHANNELS
        channels.MAX_CHANNELS = 1
        try:
            self.c.post("/api/v1/channels", json=channel_body(), headers=W)
            r = self.c.post("/api/v1/channels", json=channel_body("second"), headers=W)
            self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "limit"))
        finally:
            channels.MAX_CHANNELS = old

    def test_film_for_a_channel(self):                               # SC-001: only the channel and the idea
        self.c.post("/api/v1/channels", json=channel_body(), headers=W)
        self.admin.post("/api/v1/lessons/shared", json={"what": "w", "why": "y", "stop": "s", "rule": "max_title_chars:60"}, headers=W)
        self.c.post("/api/v1/channels/honey-facts/lessons", json={"what": "w", "why": "y", "stop": "s",
                                                                  "rule": "phrase:you won't believe"}, headers=W)
        r = self.c.post("/api/v1/jobs", json={"kind": "film", "idea": "A fox and a lantern", "channel": "honey-facts"}, headers=W)
        self.assertEqual(r.status_code, 201, r.text)
        jid = r.json()["id"]
        self.assertEqual(self.c.post("/api/v1/jobs", json={"kind": "film", "idea": "x y z", "channel": "nope"},
                                     headers=W).status_code, 404)
        self.s.start()
        j = self.s.wait(jid, timeout=90)
        self.assertEqual(j["status"], "done", j["log"][-6:])
        self.assertEqual((j["input"]["channel"], j["input"]["style"], j["input"]["seconds"]),
                         ("honey-facts", first_library_style(), 20))
        from studio import store
        d = store.account_dir(account_id(self.c)) / "films" / j["links"]["film"]
        snap = json.loads((d / "channel.json").read_text())
        self.assertEqual(sorted((x["n"], x["scope"]) for x in snap["lessons"]), [(1, "channel"), (1, "shared")])
        self.assertTrue((d / "CHANNEL_BRIEF.md").is_file())
        self.assertIn("channel_hashtags", " ".join(j["qa"]["publish"]["problems"]))   # the test agent's pack has no #honey
        # a change that becomes a draft lesson
        r = self.c.post("/api/v1/jobs", json={"kind": "film", "revise_of": j["links"]["film"], "note": "The ending is rushed",
                                              "lesson": True}, headers=W)
        self.assertEqual(r.status_code, 201, r.text)
        j2 = self.s.wait(r.json()["id"], timeout=90)
        self.assertEqual(j2["status"], "done", j2["log"][-6:])
        self.assertEqual(j2["lesson_draft"], {"scope": "honey-facts", "n": 2})
        les = self.c.get("/api/v1/channels/honey-facts").json()["lessons"]
        self.assertEqual((les[-1]["status"], les[-1]["what"]), ("draft", "The ending is rushed"))
        self.assertEqual(self.c.post("/api/v1/channels/honey-facts/lessons/2/approve", headers=W).json()["status"], "active")

    def test_lesson_needs_a_channel(self):
        from helpers import film_job
        jid = film_job(self.c).json()["id"]
        self.s.start()
        j = self.s.wait(jid, timeout=90)
        r = self.c.post("/api/v1/jobs", json={"kind": "film", "revise_of": j["links"]["film"], "note": "change it",
                                              "lesson": True}, headers=W)
        self.assertEqual(r.status_code, 422)

    @unittest.skipUnless(shutil.which("node") and (NODE_MODULES / "playwright-core").is_dir(), "needs node and playwright-core")
    def test_save_as_lesson_in_a_browser(self):                     # specs/012 T027, US3/AC5
        from helpers import Server, film_job
        from studio import jobs
        from studio.server import create_app
        self.c.post("/api/v1/channels", json=channel_body(), headers=W)
        chan = self.c.post("/api/v1/jobs", json={"kind": "film", "idea": "A fox and a lantern", "channel": "honey-facts"},
                           headers=W).json()["id"]
        plain = film_job(self.c).json()["id"]
        self.s.start()
        for jid in (chan, plain):
            self.assertEqual(self.s.wait(jid, timeout=90)["status"], "done")
        web = Server(create_app())
        try:
            r = subprocess.run(["node", str(Path(__file__).with_name("browser_lesson.cjs")), web.url, "maker@example.com",
                                PASSWORD, chan, plain], capture_output=True, text=True, timeout=90,
                               env={**os.environ, "NODE_PATH": str(NODE_MODULES)})
            if r.returncode == 77:
                self.skipTest("cannot start a browser")
            self.assertEqual(r.returncode, 0, r.stderr)
            res = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertEqual(res["errors"], [])
            self.assertEqual(res["plainHasBox"], 0)
            self.assertIn("honey-facts", res["label"])
            j = jobs.load(res["newJob"])
            self.assertEqual((j["input"]["lesson"], j["input"]["channel"], j["input"]["note"]),
                             (True, "honey-facts", "The ending is too fast"))
        finally:
            web.close()

    @unittest.skipUnless(shutil.which("node") and (NODE_MODULES / "playwright-core").is_dir(), "needs node and playwright-core")
    def test_pages_in_a_browser(self):
        from helpers import Server
        from studio.server import create_app
        web = Server(create_app())
        try:
            r = subprocess.run(["node", str(Path(__file__).with_name("browser_channels.cjs")), web.url, "maker@example.com",
                                PASSWORD, first_library_style()], capture_output=True, text=True, timeout=90,
                               env={**os.environ, "NODE_PATH": str(NODE_MODULES)})
            if r.returncode == 77:
                self.skipTest("cannot start a browser")
            self.assertEqual(r.returncode, 0, r.stderr)
            res = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertEqual(res["errors"], [])
            self.assertTrue(res["fits"], res)
            self.assertEqual(res["seconds"], "35")
            self.assertIn("Cheap tricks", res["lessons"])
            self.assertEqual(self.c.get("/api/v1/channels/tea-time").json()["seconds"], 35)
        finally:
            web.close()


if __name__ == "__main__":
    unittest.main()
