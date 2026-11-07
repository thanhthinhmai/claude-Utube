"""Accounts, sessions, one-time links, rate limits and isolation between customers (T012; FR-001–004, FR-025, SC-003)."""
import unittest

from helpers import PASSWORD, W, OnlineProject, account_id


class Accounts(unittest.TestCase):
    def setUp(self):
        self.p = OnlineProject()

    def tearDown(self):
        self.p.close()

    def post(self, c, path, body):
        return c.post("/api/v1" + path, json=body, headers=W)

    def test_signup_verify_login_logout(self):
        c = self.p.client()
        self.assertEqual(c.get("/api/v1/me").status_code, 401)
        self.assertEqual(self.post(c, "/auth/signup", {"email": "A@Example.com", "password": "short", "accept_terms": True}).json()["error"]["code"], "weak_password")
        self.assertEqual(self.post(c, "/auth/signup", {"email": "a@example.com", "password": PASSWORD}).json()["error"]["code"], "terms_required")
        self.assertEqual(self.post(c, "/auth/signup", {"email": "A@Example.com", "password": PASSWORD, "accept_terms": True}).status_code, 201)
        self.assertEqual(self.post(c, "/auth/signup", {"email": "a@example.com", "password": PASSWORD, "accept_terms": True}).status_code, 409)
        token = self.p.last_link("a@example.com", "verify")
        self.assertEqual(self.post(c, "/auth/login", {"email": "a@example.com", "password": "wrong password!"}).json()["error"]["code"], "bad_login")
        self.assertEqual(self.post(c, "/auth/login", {"email": "nobody@example.com", "password": "wrong password!"}).json()["error"]["code"], "bad_login")
        self.assertEqual(self.post(c, "/auth/login", {"email": "a@example.com", "password": PASSWORD}).status_code, 200)
        me = c.get("/api/v1/me").json()
        self.assertEqual((me["email"], me["verified"], me["role"]), ("a@example.com", False, "customer"))
        self.assertEqual(me["quota"]["films"], {"used": 0, "limit": 2})
        self.assertRegex(me["quota"]["resets_at"], r"-\d\d-01T00:00:00\+07:00$")
        self.assertEqual(self.post(c, "/auth/verify", {"token": token}).status_code, 200)
        self.assertEqual(self.post(c, "/auth/verify", {"token": token}).status_code, 410)      # used once
        self.assertTrue(c.get("/api/v1/me").json()["verified"])
        cookie = c.cookies.get("studio_session")
        self.assertTrue(cookie)
        self.assertEqual(c.post("/api/v1/auth/logout", headers=W).status_code, 204)
        c.cookies.set("studio_session", cookie)                                              # old cookie is dead
        self.assertEqual(c.get("/api/v1/me").status_code, 401)

    def test_expired_link(self):
        from studio import store
        c = self.p.client()
        self.post(c, "/auth/signup", {"email": "b@example.com", "password": PASSWORD, "accept_terms": True})
        token = self.p.last_link("b@example.com", "verify")
        real = store.clock
        try:
            store.clock = lambda: real() + 25 * 3600
            self.assertEqual(self.post(c, "/auth/verify", {"token": token}).status_code, 410)
        finally:
            store.clock = real

    def test_reset_password_ends_old_sessions(self):
        c = self.p.signup_verified("c@example.com")
        self.assertEqual(self.post(self.p.client(), "/auth/forgot", {"email": "nobody@example.com"}).status_code, 202)
        self.assertEqual(self.post(self.p.client(), "/auth/forgot", {"email": "c@example.com"}).status_code, 202)
        token = self.p.last_link("c@example.com", "reset")
        self.assertEqual(self.post(self.p.client(), "/auth/reset", {"token": token, "password": "new password 123"}).status_code, 200)
        self.assertEqual(c.get("/api/v1/me").status_code, 401)
        c2 = self.p.client()
        self.assertEqual(self.post(c2, "/auth/login", {"email": "c@example.com", "password": PASSWORD}).status_code, 401)
        self.assertEqual(self.post(c2, "/auth/login", {"email": "c@example.com", "password": "new password 123"}).status_code, 200)

    def test_signup_closed_and_locked(self):
        from studio import db
        c = self.p.signup_verified("d@example.com")
        s = db.settings()
        s["signup_open"] = False
        db.save_settings(s)
        r = self.post(self.p.client(), "/auth/signup", {"email": "e@example.com", "password": PASSWORD, "accept_terms": True})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (403, "signup_closed"))
        with db.tx() as con:
            con.execute("UPDATE accounts SET locked_at = '2026-01-01T00:00:00+00:00' WHERE email = 'd@example.com'")
        self.assertEqual(c.get("/api/v1/me").json()["error"]["code"], "locked")
        self.assertEqual(self.post(self.p.client(), "/auth/login", {"email": "d@example.com", "password": PASSWORD}).json()["error"]["code"], "locked")

    def test_rate_limits(self):
        c = self.p.client()
        codes = [self.post(c, "/auth/login", {"email": "x@example.com", "password": "wrong password!"}).status_code for _ in range(11)]
        self.assertEqual(codes[:10], [401] * 10)
        r = self.post(c, "/auth/login", {"email": "x@example.com", "password": "wrong password!"})
        self.assertEqual(r.status_code, 429)
        self.assertGreater(int(r.headers["retry-after"]), 0)

    def test_csrf(self):
        c = self.p.client()
        body = {"email": "f@example.com", "password": PASSWORD, "accept_terms": True}
        self.assertEqual(c.post("/api/v1/auth/signup", json=body).json()["error"]["code"], "csrf")
        self.assertEqual(c.post("/api/v1/auth/signup", json=body, headers={**W, "Origin": "https://evil.test"}).json()["error"]["code"], "csrf")
        self.assertEqual(c.post("/api/v1/auth/signup", json=body, headers={**W, "Origin": "https://studio.test"}).status_code, 201)

    def test_health_hides_paths(self):
        h = self.p.client().get("/api/v1/health").json()
        self.assertEqual(h["mode"], "online")
        self.assertNotIn("root", h)

    def test_admin_create(self):
        import os
        import subprocess
        from helpers import REPO
        env = dict(os.environ, STUDIO_ADMIN_PASSWORD=PASSWORD)
        cli = [str(REPO / "tools" / ".venv" / "bin" / "python"), str(REPO / "tools" / "studio" / "studio_cli.py"), "admin", "create", "Boss@Example.com"]
        r = subprocess.run(cli, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(subprocess.run(cli[:-1] + ["other@example.com"], env=env, capture_output=True, text=True).returncode, 1)  # only one admin
        c = self.p.client()
        self.post(c, "/auth/login", {"email": "boss@example.com", "password": PASSWORD})
        me = c.get("/api/v1/me").json()
        self.assertEqual((me["role"], me["verified"]), ("admin", True))
        local = dict(env, STUDIO_MODE="local")
        self.assertEqual(subprocess.run(cli, env=local, capture_output=True, text=True).returncode, 1)

    def test_delete_account(self):
        c = self.p.signup_verified("g@example.com")
        self.assertEqual(c.request("DELETE", "/api/v1/me", json={"password": "wrong password!"}, headers=W).status_code, 401)
        self.assertEqual(c.request("DELETE", "/api/v1/me", json={"password": PASSWORD}, headers=W).status_code, 202)
        self.assertEqual(c.get("/api/v1/me").status_code, 401)
        self.assertEqual(self.post(self.p.client(), "/auth/login", {"email": "g@example.com", "password": PASSWORD}).status_code, 401)
        self.assertTrue(any("being deleted" in p.read_text() for p in self.p.flush_mail()))


class TwoCustomers(unittest.TestCase):
    """SC-003: no customer sees or downloads another customer's data, on every phase-1 path."""

    def setUp(self):
        self.p = OnlineProject()
        self.a = self.p.signup_verified("alice@example.com")
        self.b = self.p.signup_verified("bob@example.com")
        self.p.copy_fixtures_to(account_id(self.a))          # only Alice has a film, a set and a style
        from studio import jobs, reviews
        self.job = jobs.create("learn", "alice job", owner=account_id(self.a))
        self.rid = None
        from studio import store
        with store.as_account(account_id(self.a)):
            self.rid = reviews.create(self.job["id"], "style-2", "demo-set", "# Alice summary")["id"]

    def tearDown(self):
        self.p.close()

    PATHS = ["/films/demo-film", "/films/demo-film/video", "/films/demo-film/poster", "/films/demo-film/subtitles.vtt",
             "/sets/demo-set", "/sets/demo-set/sheets", "/sets/demo-set/sheets/v01_0000.jpg", "/sets/demo-set/proof/ref.jpg",
             "/styles/demo-style", "/styles/demo-style/styleframe"]

    def test_isolation(self):
        api = "/api/v1"
        for path in self.PATHS + [f"/jobs/{self.job['id']}", f"/reviews/{self.rid}"]:
            self.assertEqual(self.a.get(api + path).status_code, 200, path)
            self.assertEqual(self.b.get(api + path).status_code, 404, path)
        for path, key in (("/jobs", "jobs"), ("/reviews", "reviews"), ("/films", "films"), ("/sets", "sets"), ("/styles", "styles")):
            self.assertGreater(len(self.a.get(api + path).json()[key]), 0, path)
            self.assertEqual(self.b.get(api + path).json()[key], [], path)
        r = self.b.post(f"{api}/reviews/{self.rid}/decision", json={"value": "approve"}, headers=W)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.a.post(f"{api}/reviews/{self.rid}/decision", json={"value": "approve"}, headers=W).status_code, 201)
        self.assertEqual(self.b.get(api + "/library").status_code, 200)       # the shared library is for everyone
        for c in (self.a, self.b):
            c.cookies.clear()
            for path in self.PATHS:
                self.assertEqual(c.get(api + path).status_code, 401, path)


if __name__ == "__main__":
    unittest.main()
