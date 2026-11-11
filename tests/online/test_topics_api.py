"""The topic picker online (specs/013 T015–T016): the studio's key, topics jobs through the proxy, the per-day limit,
other people (SC-006), films from a topic, and the key never showing (SC-004)."""
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from helpers import PASSWORD, REPO, W, Studio, account_id, first_library_style

sys.path.insert(0, str(REPO / "tests" / "filmcheck"))
import youtube_samples as yt  # noqa: E402

NODE_MODULES = REPO / "lib" / "lemo-opuscar" / "node_modules"
SAMPLE = list(yt.EXPECTED)


class TopicsApi(unittest.TestCase):
    def setUp(self):
        from studio import accounts, quotas
        self.s = Studio()
        quotas.update_settings({"quota_films_default": 5})
        accounts.signup("owner@example.com", PASSWORD, True, role="admin", verified=True)
        self.admin = self.s.client()
        assert self.admin.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": PASSWORD},
                               headers=W).status_code == 200
        self.c = self.s.signup_verified("maker@example.com")
        r = self.c.post("/api/v1/channels", json={"slug": "honey", "name": "Honey", "language": "en", "seconds": 20,
                                                   "style": first_library_style()}, headers=W)
        assert r.status_code == 201, r.text

    def tearDown(self):
        self.s.close()

    def set_key(self):
        r = self.admin.put("/api/v1/admin/youtube-key", json={"key": yt.KEY}, headers=W)
        self.assertEqual((r.status_code, r.json()), (200, {"set": True, "last4": yt.KEY[-4:]}))

    def score(self, topics, suggest=False):
        r = self.c.post("/api/v1/channels/honey/topics/score", json={"topics": topics, "suggest": suggest}, headers=W)
        self.assertEqual(r.status_code, 201, r.text)
        self.s.start()
        return self.s.wait(r.json()["id"], timeout=90)

    def test_key_only_for_the_owner(self):
        self.assertEqual(self.c.put("/api/v1/admin/youtube-key", json={"key": yt.KEY}, headers=W).status_code, 403)
        bad = self.admin.put("/api/v1/admin/youtube-key", json={"key": "AIzaBAD-" + "x" * 31}, headers=W)
        self.assertEqual(bad.status_code, 422)
        self.assertNotIn("AIzaBAD-" + "x" * 31, bad.text)
        self.set_key()
        st = self.admin.get("/api/v1/admin/settings").json()
        self.assertEqual((st["youtube_key_set"], st["youtube_key_last4"]), (True, yt.KEY[-4:]))
        self.assertNotIn(yt.KEY, json.dumps(st))

    def test_score_queue_and_film(self):
        r = self.c.post("/api/v1/channels/honey/topics/score", json={"topics": ["why honey never spoils"]}, headers=W)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (503, "youtube_not_ready"))
        self.set_key()
        j = self.score(SAMPLE, suggest=True)
        self.assertEqual(j["status"], "done", j["log"][-6:])
        self.assertFalse(j["charged"])
        self.assertEqual(self.c.get("/api/v1/me").json()["quota"]["films"]["used"], 0)     # no film credit
        got = self.c.get("/api/v1/channels/honey/topics").json()
        v = {t["text"]: (t["scores"], t["verdict"]) for t in got["topics"]}
        for text, want in yt.EXPECTED.items():
            self.assertEqual(v[text], want, text)
        self.assertTrue(any(t["source"] == "suggested" for t in got["topics"]))
        self.assertNotIn("raw", got["topics"][0])
        first = got["queue"][0]
        self.assertEqual(next(t for t in got["topics"] if t["n"] == first)["verdict"], "PRIORITY")
        self.assertEqual(got["usage"]["today"], 4)
        units = self.admin.get("/api/v1/admin/settings").json()["youtube_units_today"]
        self.assertGreater(units, 0)
        self.assertLessEqual(units, 400 * 6 + 10)
        j2 = self.score(["why honey never spoils"])                  # within 24 hours: from the proxy's cache
        self.assertEqual(j2["status"], "done")
        self.assertEqual(self.admin.get("/api/v1/admin/settings").json()["youtube_units_today"], units)
        # take, then a film from the topic
        take = self.c.post("/api/v1/channels/honey/topics/take", json={}, headers=W).json()
        self.assertEqual(take["topic"]["n"], first)
        r = self.c.post("/api/v1/jobs", json={"kind": "film", "idea": take["topic"]["text"], "channel": "honey",
                                              "topic": first}, headers=W)
        self.assertEqual(r.status_code, 201, r.text)
        t = next(x for x in self.c.get("/api/v1/channels/honey/topics").json()["topics"] if x["n"] == first)
        self.assertEqual(t["status"], "in_progress")
        self.assertEqual(self.s.wait(r.json()["id"], timeout=90)["status"], "done")
        t = next(x for x in self.c.get("/api/v1/channels/honey/topics").json()["topics"] if x["n"] == first)
        self.assertEqual(t["status"], "made")
        # edits
        self.assertEqual(self.c.post(f"/api/v1/channels/honey/topics/{first}/type", json={"type": "list"}, headers=W).json()["type"], "list")
        self.assertEqual(self.c.post(f"/api/v1/channels/honey/topics/{first}/type", json={"type": "poem"}, headers=W).status_code, 422)
        bee = next(x["n"] for x in got["topics"] if x["text"] == "bee dances explained")
        self.assertEqual(self.c.post(f"/api/v1/channels/honey/topics/{bee}/fit", json={"score": 10}, headers=W).json()["scores"]["fit"], 10)

    def test_limit_per_day(self):
        from studio import quotas
        self.set_key()
        quotas.update_settings({"topics_per_day": 3})
        r = self.c.post("/api/v1/channels/honey/topics/score", json={"topics": SAMPLE}, headers=W)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (429, "topics_limit"))
        self.assertIn("retry_at", r.json()["error"])

    def test_references(self):
        self.assertEqual(self.c.put("/api/v1/channels/honey/references", json={"channels": ["nope"]}, headers=W).status_code, 422)
        r = self.c.put("/api/v1/channels/honey/references", json={"channels": [yt.REF_CHANNEL]}, headers=W)
        self.assertEqual(r.status_code, 200, r.text)
        self.set_key()
        self.score(SAMPLE)
        st = {t["text"]: t["status"] for t in self.c.get("/api/v1/channels/honey/topics").json()["topics"]}
        self.assertEqual(st["honey vs sugar"], "blocked_reference")

    def test_others_get_404(self):                                    # SC-006
        other = self.s.signup_verified("other@example.com")
        for method, path, body in (("get", "/api/v1/channels/honey/topics", None),
                                   ("post", "/api/v1/channels/honey/topics/score", {"topics": ["abc def"]}),
                                   ("post", "/api/v1/channels/honey/topics/1/type", {"type": "list"}),
                                   ("post", "/api/v1/channels/honey/topics/1/fit", {"score": 3}),
                                   ("post", "/api/v1/channels/honey/topics/take", {}),
                                   ("get", "/api/v1/channels/honey/references", None),
                                   ("put", "/api/v1/channels/honey/references", {"channels": []})):
            fn = getattr(other, method)
            r = fn(path, json=body, headers=W) if body is not None else fn(path, headers=W)
            self.assertEqual(r.status_code, 404, (method, path, r.text))

    def test_proxy_refuses_film_jobs_and_hides_the_key(self):
        import logging
        import urllib.request
        from studio import jobs
        logs = []
        h = logging.Handler()
        h.emit = lambda rec: logs.append(rec.getMessage())
        logging.getLogger("studio.proxy").addHandler(h)
        logging.getLogger("studio.proxy").setLevel(logging.INFO)
        try:
            self.set_key()
            j = self.score(["why honey never spoils"])
            sys.path.insert(0, str(REPO / "tools" / "runner"))
            import proxy
            film = jobs.create("film", "f", {}, owner=account_id(self.c), status="running")
            tok = proxy.issue(film["id"])
            req = urllib.request.Request(self.s.proxy.url + "/internal/youtube", method="POST",
                                         data=json.dumps({"endpoint": "videos", "params": {"id": "x"}}).encode(),
                                         headers={"authorization": "Bearer " + tok, "content-type": "application/json"})
            try:
                urllib.request.urlopen(req, timeout=10)
                code = 200
            except urllib.error.HTTPError as e:
                code = e.code
            self.assertEqual(code, 403)
            self.assertIn(yt.KEY, self.s.upstream_app.state.yt_keys)               # it did reach YouTube
            blobs = logs + [json.dumps(jobs.load(j["id"]))] + [json.dumps(self.c.get("/api/v1/channels/honey/topics").json())]
            for b in blobs:                                                         # SC-004
                self.assertNotIn(yt.KEY, b)
        finally:
            logging.getLogger("studio.proxy").removeHandler(h)

    @unittest.skipUnless(shutil.which("node") and (NODE_MODULES / "playwright-core").is_dir(), "needs node and playwright-core")
    def test_page_in_a_browser(self):
        from helpers import Server
        from studio.server import create_app
        self.set_key()
        self.score(SAMPLE)
        web = Server(create_app())
        try:
            r = subprocess.run(["node", str(Path(__file__).with_name("browser_topics.cjs")), web.url, "maker@example.com",
                                PASSWORD], capture_output=True, text=True, timeout=90,
                               env={**os.environ, "NODE_PATH": str(NODE_MODULES)})
            if r.returncode == 77:
                self.skipTest("cannot start a browser")
            self.assertEqual(r.returncode, 0, r.stderr)
            res = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertEqual(res["errors"], [])
            self.assertTrue(res["fits"], res)
            self.assertIn("PRIORITY", res["table"])
            self.assertEqual(res["idea"], "why honey never spoils")
            self.assertEqual(res["channel"], "honey")
        finally:
            web.close()


if __name__ == "__main__":
    unittest.main()
