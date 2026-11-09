"""API tokens (specs/009): a token acts as its owner with a capped role, some paths are closed to every token, a rate
per minute, a log row per request; only the hash is kept (FR-210-FR-215, FR-218, SC-205)."""
import os
import unittest

from helpers import PASSWORD, W, Studio, film_job


class TokenBase(unittest.TestCase):
    def setUp(self):
        self.s = Studio()
        from studio import accounts
        accounts.signup("boss@x.test", PASSWORD, True, role="admin", verified=True)
        self.boss = accounts.get(next(u["id"] for u in accounts.users() if u["email"] == "boss@x.test"))
        self.m = accounts.add_user("m@x.test", PASSWORD)
        self.member = accounts.get(self.m["id"])

    def tearDown(self):
        self.s.close()

    def make(self, owner, **kw):
        from studio import tokens
        return tokens.create(owner, kw.pop("name", "agent"), **kw)

    def call(self, secret, method, path, **kw):
        c = self.s.client()
        c.cookies.clear()
        return c.request(method, "/api/v1" + path, headers={"Authorization": f"Bearer {secret}"}, **kw)

    def logged(self, token_id):
        from studio import db
        with db.read() as con:
            return [r[0] for r in con.execute("SELECT outcome FROM token_request WHERE token_id = ? ORDER BY id", (token_id,))]


class Foundation(TokenBase):
    def test_secret_is_shown_once_and_only_its_hash_is_kept(self):
        from studio import db, tokens
        t, secret = self.make(self.member)
        self.assertRegex(secret, r"^fs_[A-Za-z0-9_-]{40,}$")
        self.assertEqual(t["prefix"], secret[:8])
        self.assertNotIn("secret", t)
        with db.read() as con:
            row = con.execute("SELECT * FROM api_token WHERE id = ?", (t["id"],)).fetchone()
        self.assertEqual(row["hash"], tokens.sha(secret))
        self.assertNotIn(secret, " ".join(str(v) for v in dict(row).values()))

    def test_a_token_acts_as_its_owner_without_cookie_or_studio_header(self):
        t, secret = self.make(self.member)
        r = self.call(secret, "GET", "/me")
        self.assertEqual((r.status_code, r.json()["email"], r.json()["role"]), (200, "m@x.test", "customer"))
        self.assertEqual(self.call(secret, "POST", "/jobs/nope/stop").json()["error"]["code"], "not_found")   # no csrf
        boss_cookie = self.s.client()
        boss_cookie.post("/api/v1/auth/login", json={"email": "boss@x.test", "password": PASSWORD}, headers=W)
        r = boss_cookie.get("/api/v1/me", headers={"Authorization": f"Bearer {secret}"})
        self.assertEqual(r.json()["email"], "m@x.test")                            # the token wins over the cookie
        self.assertEqual(self.logged(t["id"]), ["allowed", "allowed", "allowed"])

    def test_role_is_capped_by_the_owner_now(self):
        from studio import accounts
        t, secret = self.make(self.boss, role="admin")
        self.assertEqual(self.call(secret, "GET", "/admin/usage").status_code, 200)
        o2 = accounts.add_user("o2@x.test", PASSWORD, "admin")
        accounts.update_user(self.boss["id"], o2["id"], role="customer")          # the owner becomes a member
        r = self.call(secret, "GET", "/admin/usage")
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (403, "forbidden"))
        self.assertEqual(self.logged(t["id"])[-1], "forbidden")
        from studio.store import StudioError
        with self.assertRaises(StudioError) as e:                                 # a member cannot make an Owner token
            self.make(self.member, role="admin")
        self.assertEqual(e.exception.code, "forbidden")

    def test_dead_tokens_are_refused_alike(self):
        from studio import accounts, db, tokens
        t1, s1 = self.make(self.member)
        tokens.revoke(t1["id"])
        t2, s2 = self.make(self.member, expires="7d")
        with db.tx() as con:
            con.execute("UPDATE api_token SET expires_at = '2000-01-01T00:00:00+00:00' WHERE id = ?", (t2["id"],))
        t3, s3 = self.make(self.member)
        for secret in (s1, s2, "fs_" + "x" * 43, "not-a-token"):
            r = self.call(secret, "GET", "/me")
            self.assertEqual((r.status_code, r.json()["error"]["code"]), (401, "bad_token"), secret[:6])
        self.assertEqual(self.call(s3, "GET", "/me").status_code, 200)
        accounts.update_user(self.m["id"], self.boss["id"], disabled=True)        # the owner turned off
        self.assertEqual(self.call(s3, "GET", "/me").status_code, 401)
        accounts.update_user(self.m["id"], self.boss["id"], disabled=False)
        accounts.remove_user(self.m["id"], self.boss["id"])                        # the owner removed
        self.assertEqual(self.call(s3, "GET", "/me").status_code, 401)

    def test_closed_paths_for_every_token(self):                                 # FR-213
        t, secret = self.make(self.boss, role="admin")
        closed = [("GET", "/me/tokens"), ("POST", "/me/tokens"), ("GET", "/admin/tokens"), ("GET", "/admin/users"),
                  ("POST", "/admin/users"), ("GET", "/admin/claude"), ("PUT", "/admin/claude/order"),
                  ("POST", "/admin/claude/accounts/1/login"), ("PUT", "/me"), ("DELETE", "/me")]
        for method, path in closed:
            r = self.call(secret, method, path, json={})
            self.assertEqual((r.status_code, r.json()["error"]["code"]), (403, "token_forbidden"), path)
        self.assertEqual(self.call(secret, "GET", "/me").status_code, 200)       # GET /me is fine
        self.assertEqual(self.call(secret, "PUT", "/admin/settings", json={"concurrency": 2}).status_code, 200)
        self.assertEqual(self.logged(t["id"]).count("token_forbidden"), len(closed))

    def test_rate_per_minute(self):
        t, secret = self.make(self.member, rate_per_min=10)
        codes = [self.call(secret, "GET", "/me").status_code for _ in range(11)]
        self.assertEqual(codes[:10], [200] * 10)
        r = self.call(secret, "GET", "/me")
        self.assertEqual(r.status_code, 429)
        self.assertGreater(int(r.headers["retry-after"]), 0)
        self.assertEqual(self.logged(t["id"])[-1], "rate_limit")

    def test_listing_counts_today_and_the_log_ages_out(self):
        from studio import db, store, tokens
        t, secret = self.make(self.member)
        self.call(secret, "GET", "/me")
        self.call(secret, "GET", "/admin/usage")                                    # forbidden: blocked
        self.call(secret, "GET", "/me/tokens")                                      # token_forbidden: blocked
        v = tokens.get(t["id"])
        self.assertEqual((v["requests_today"], v["blocked_today"], v["status"]), (3, 2, "active"))
        self.assertEqual([x["outcome"] for x in tokens.log(t["id"])], ["token_forbidden", "forbidden", "allowed"])
        with db.tx() as con:
            con.execute("UPDATE token_request SET at = '2000-01-01T00:00:00+00:00'")
        tokens._pruned["at"] = 0
        self.call(secret, "GET", "/me")
        self.assertEqual(len(tokens.log(t["id"])), 1)                              # rows over 30 days are gone

    def test_at_most_20_active_tokens_each(self):
        from studio.store import StudioError
        for i in range(20):
            self.make(self.member, name=f"t{i}")
        with self.assertRaises(StudioError) as e:
            self.make(self.member, name="one more")
        self.assertEqual(e.exception.code, "too_many_tokens")


if __name__ == "__main__":
    unittest.main()
