"""The private release passed on to licensed apps (specs/017 T017, research R5), with a fake GitHub."""
import http.server
import json
import os
import threading
import unittest

from helpers import admin, device, make, server, store

FILES = {"release.json": b'{"version": "0.2.0"}', "claude-Utube-Setup-0.2.0.exe": b"EXE" * 1000, "secret.txt": b"no"}


class FakeGitHub(http.server.BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *a):
        pass

    def do_GET(self):
        FakeGitHub.seen.append((self.path, self.headers.get("authorization"), self.headers.get("accept")))
        base = f"http://127.0.0.1:{self.server.server_port}"
        if self.path.startswith("/repos/o/r/releases?"):
            body = json.dumps([
                {"tag_name": "desktop-v0.3.0", "draft": True, "assets": []},
                {"tag_name": "other-v9", "draft": False, "assets": []},
                {"tag_name": "desktop-v0.2.0", "draft": False,
                 "assets": [{"name": n, "size": len(b), "url": f"{base}/assets/{n}"} for n, b in FILES.items()]}]).encode()
        elif self.path.startswith("/assets/"):
            body = FILES[self.path.split("/")[-1]]
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class Releases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gh = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeGitHub)
        threading.Thread(target=cls.gh.serve_forever, daemon=True).start()
        os.environ.update(LICENSE_GITHUB_API=f"http://127.0.0.1:{cls.gh.server_port}", GITHUB_REPO="o/r", GITHUB_TOKEN="ghp_test")

    @classmethod
    def tearDownClass(cls):
        cls.gh.shutdown()
        for k in ("LICENSE_GITHUB_API", "GITHUB_REPO", "GITHUB_TOKEN"):
            os.environ.pop(k, None)

    def setUp(self):
        self.s, self.c, self.clock, *_ = make()
        h = admin(self.c)
        r = self.c.post("/admin/api/licenses", json={"label": "An"}, headers=h)
        self.lid = r.json()["licenses"][0]["id"]
        self.h = h
        self.lease = self.c.post("/api/license/lease", json={"key": r.json()["key"], "deviceId": device(1)}).json()["lease"]

    def test_list_and_files(self):
        self.assertEqual(self.c.get("/api/license/releases").status_code, 403)
        r = self.c.get("/api/license/releases", headers={"x-cu-lease": self.lease})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["version"], "0.2.0")                       # drafts and other tags skipped
        self.assertEqual([a["name"] for a in r.json()["assets"]], ["release.json", "claude-Utube-Setup-0.2.0.exe"])
        f = self.c.get("/api/license/releases/claude-Utube-Setup-0.2.0.exe", headers={"x-cu-lease": self.lease})
        self.assertEqual((f.status_code, f.content), (200, FILES["claude-Utube-Setup-0.2.0.exe"]))
        self.assertIn(("/assets/claude-Utube-Setup-0.2.0.exe", "Bearer ghp_test", "application/octet-stream"), FakeGitHub.seen)
        self.assertEqual(self.c.get("/api/license/releases/secret.txt", headers={"x-cu-lease": self.lease}).status_code, 404)
        self.assertNotIn("ghp_test", r.text + f.headers.get("location", ""))

    def test_needs_a_good_license_now(self):
        ok = {"x-cu-lease": self.lease}
        self.c.patch(f"/admin/api/licenses/{self.lid}", json={"revoked": True}, headers=self.h)
        self.assertEqual(self.c.get("/api/license/releases", headers=ok).status_code, 403)   # signed lease, key off
        self.c.patch(f"/admin/api/licenses/{self.lid}", json={"revoked": False}, headers=self.h)
        self.c.delete(f"/admin/api/licenses/{self.lid}/devices/{device(1)}", headers=self.h)
        self.assertEqual(self.c.get("/api/license/releases", headers=ok).status_code, 403)   # computer removed
        self.assertEqual(self.c.get("/api/license/releases", headers={"x-cu-lease": self.lease[:-2] + "AA"}).status_code, 403)
        self.clock.t += 8 * 86400
        self.assertFalse(self.s.in_good_standing(self.lease))               # expired


if __name__ == "__main__":
    unittest.main()
