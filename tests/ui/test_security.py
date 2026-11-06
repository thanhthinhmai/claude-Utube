import unittest

from fastapi.testclient import TestClient

from helpers import W, Project, client
from studio import jobs, reviews
from studio.server import create_app


class Security(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.c = client()

    def tearDown(self):
        self.p.close()

    def test_bad_host_rejected(self):  # DNS rebinding
        r = TestClient(create_app(), base_url="http://evil.example").get("/api/v1/jobs")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["error"]["code"], "bad_host")
        self.assertEqual(TestClient(create_app(), base_url="http://127.0.0.1:8787").get("/api/v1/health").status_code, 200)

    def test_post_needs_studio_header(self):  # CSRF
        j = jobs.create("learn", "demo", {"set": "demo-set"})
        rid = reviews.create(j["id"], "style-1", "demo-set", "x")["id"]
        r = self.c.post(f"/api/v1/reviews/{rid}/decision", json={"value": "approve"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["error"]["code"], "csrf")
        r = self.c.post(f"/api/v1/reviews/{rid}/decision", content="value=approve",
                        headers={**W, "Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.c.post(f"/api/v1/reviews/{rid}/decision", json={"value": "approve"}, headers=W).status_code, 201)

    def test_no_files_outside_project_folders(self):  # FR-019
        for path in ("/api/v1/sets/demo-set/sheets/..%2F..%2F..%2Fsecret.txt", "/api/v1/sets/demo-set/proof/..%2Fcompare.json",
                     "/api/v1/films/..%2Fsecret/video", "/api/v1/sets/DEMO/sheets/v01_0000.jpg",
                     "/api/v1/styles/demo-style%2F..%2F..%2Fsecret.txt/styleframe", "/../secret.txt", "/secret.txt"):
            r = self.c.get(path)
            self.assertIn(r.status_code, (400, 404), path)
            self.assertNotIn("do not serve", r.text)

    def test_reference_identity_not_exposed(self):  # FR-018
        body = self.c.get("/api/v1/sets/demo-set").text + self.c.get("/api/v1/sets").text
        for secret in ("Secret title", "Secret Channel", "youtube.example", '"abc"'):
            self.assertNotIn(secret, body)

    def test_markdown_scripts_neutralised(self):
        html = self.c.get("/api/v1/styles/demo-style").json()["style_html"]
        self.assertIn("<table>", html)
        self.assertNotIn("<img", html)
        self.assertNotIn("<script", self.c.get("/api/v1/films/demo-film").json()["treatment_html"])

    def test_server_binds_loopback_only(self):  # FR-017
        out = self.p.cli("ui")
        self.assertEqual(out.returncode, 0, out.stderr)
        import json as _j
        info = _j.loads((self.p.dir / ".studio" / "server.json").read_text())
        import socket
        ips = {a[4][0] for a in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)} - {"127.0.0.1", "127.0.1.1"}
        for ip in ips:                              # the same port on a LAN address must refuse
            with socket.socket() as s:
                s.settimeout(1)
                self.assertNotEqual(s.connect_ex((ip, info["port"])), 0, ip)


if __name__ == "__main__":
    unittest.main()
