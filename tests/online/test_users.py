"""Settings → Users, like neb-creative-tool: no public sign-up; the owner adds and manages people
(specs/008 US3, FR-111, FR-112, SC-106)."""
import unittest

from helpers import PASSWORD, W, Studio, film_job

U = "/api/v1/admin/users"


class Users(unittest.TestCase):
    def setUp(self):
        self.p = Studio()                     # fake moderation, so members can order
        from studio import accounts
        accounts.signup("boss@x.test", PASSWORD, True, role="admin", verified=True)
        self.a = self.login("boss@x.test")
        self.me = self.a.get(U).json()["me"]

    def tearDown(self):
        self.p.close()

    def login(self, email, password=PASSWORD):
        c = self.p.client()
        r = c.post("/api/v1/auth/login", json={"email": email, "password": password}, headers=W)
        assert r.status_code == 200, r.text
        return c

    def add(self, email, role="customer", password=PASSWORD):
        return self.a.post(U, json={"email": email, "password": password, "role": role}, headers=W)

    def find(self, email):
        return next(u for u in self.a.get(U).json()["users"] if u["email"] == email)

    def test_no_public_sign_up(self):                                   # SC-106
        for body in ({"email": "x@x.test", "password": PASSWORD, "accept_terms": True}, {}):
            r = self.p.client().post("/api/v1/auth/signup", json=body, headers=W)
            self.assertEqual(r.status_code, 403 if body else 422)
        r = self.a.put("/api/v1/admin/settings", json={"signup_open": True}, headers=W)
        self.assertEqual(r.status_code, 422)

    def test_add_a_member_and_make_them_owner(self):
        r = self.add("Mem@X.test")
        self.assertEqual(r.status_code, 201, r.text)
        u = r.json()
        self.assertEqual((u["email"], u["role"], u["disabled"], u["last_login_at"], u["sessions"]),
                         ("mem@x.test", "customer", False, None, 0))
        self.assertEqual(self.add("mem@x.test").json()["error"]["code"], "email_taken")
        self.assertEqual(self.add("weak@x.test", password="short").json()["error"]["code"], "weak_password")
        self.assertEqual(self.add("r@x.test", role="god").status_code, 422)
        m = self.login("mem@x.test")
        me = m.get("/api/v1/me").json()
        self.assertEqual((me["role"], me["verified"]), ("customer", True))
        self.assertEqual(film_job(m).status_code, 201)                    # can order at once
        self.assertEqual(m.get(U).status_code, 403)                       # members do not see Settings
        self.assertEqual(m.get("/api/v1/admin/claude").status_code, 403)
        u = self.find("mem@x.test")
        self.assertTrue(u["last_login_at"])
        self.assertEqual(u["sessions"], 1)
        r = self.a.put(f"{U}/{u['id']}", json={"role": "admin"}, headers=W)
        self.assertEqual(r.json()["role"], "admin")
        self.assertEqual(m.get(U).status_code, 200)                       # an owner now

    def test_password_signout_and_turn_off(self):
        u = self.add("m@x.test").json()
        m1, m2 = self.login("m@x.test"), self.login("m@x.test")
        self.assertEqual(self.find("m@x.test")["sessions"], 2)
        self.assertEqual(self.a.post(f"{U}/{u['id']}/signout", headers=W).status_code, 204)
        self.assertEqual(m1.get("/api/v1/me").status_code, 401)
        self.assertEqual(m2.get("/api/v1/me").status_code, 401)
        m = self.login("m@x.test")
        r = self.a.put(f"{U}/{u['id']}", json={"password": "a brand new password"}, headers=W)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(m.get("/api/v1/me").status_code, 401)             # signed out by the new password
        m = self.login("m@x.test", "a brand new password")
        jid = film_job(m).json()["id"]
        r = self.a.put(f"{U}/{u['id']}", json={"disabled": True}, headers=W)
        self.assertEqual(r.json()["disabled"], True)
        self.assertEqual(m.get("/api/v1/me").status_code, 401)
        r = self.p.client().post("/api/v1/auth/login", json={"email": "m@x.test", "password": "a brand new password"}, headers=W)
        self.assertEqual(r.json()["error"]["code"], "locked")
        from studio import jobs
        self.assertEqual(jobs.load(jid)["status"], "stopped")             # running and queued jobs stop
        self.a.put(f"{U}/{u['id']}", json={"disabled": False}, headers=W)
        self.login("m@x.test", "a brand new password")

    def test_always_one_owner_and_not_oneself(self):
        for change in ({"role": "customer"}, {"disabled": True}):
            r = self.a.put(f"{U}/{self.me}", json=change, headers=W)
            self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "self"))
        r = self.a.delete(f"{U}/{self.me}", headers=W)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "self"))
        r = self.a.put(f"{U}/{self.me}", json={"password": "my own new password"}, headers=W)
        self.assertEqual(r.status_code, 200)                              # resetting one's own password is fine
        self.a = self.login("boss@x.test", "my own new password")
        o = self.add("o2@x.test", role="admin").json()
        o2 = self.login("o2@x.test")
        self.assertEqual(o2.put(f"{U}/{self.me}", json={"role": "customer"}, headers=W).status_code, 200)
        r = o2.put(f"{U}/{self.me}", json={"disabled": True}, headers=W)  # boss is a member now; fine
        self.assertEqual(r.status_code, 200)
        from studio import accounts
        with self.assertRaises(Exception) as e:                           # o2 is the last owner on
            accounts.update_user(o["id"], "someone-else", role="customer")
        self.assertEqual(e.exception.code, "last_owner")
        with self.assertRaises(Exception) as e:
            accounts.remove_user(o["id"], "someone-else")
        self.assertEqual(e.exception.code, "last_owner")
        with self.assertRaises(Exception) as e:
            accounts.update_user(o["id"], "someone-else", disabled=True)
        self.assertEqual(e.exception.code, "last_owner")

    def test_remove(self):
        u = self.add("gone@x.test").json()
        m = self.login("gone@x.test")
        self.assertEqual(self.a.delete(f"{U}/{u['id']}", headers=W).status_code, 204)
        self.assertEqual(m.get("/api/v1/me").status_code, 401)
        self.assertNotIn("gone@x.test", [x["email"] for x in self.a.get(U).json()["users"]])
        self.assertEqual(self.a.delete(f"{U}/{u['id']}", headers=W).status_code, 404)
        self.assertEqual(self.a.put(f"{U}/nope", json={"disabled": True}, headers=W).status_code, 404)

    def test_007_customers_still_sign_in_as_members(self):              # US3 #5
        from studio import accounts
        accounts.signup("old@x.test", PASSWORD, True, verified=True)    # how a 007 sign-up was stored
        self.login("old@x.test")
        self.assertEqual(self.find("old@x.test")["role"], "customer")


if __name__ == "__main__":
    unittest.main()
