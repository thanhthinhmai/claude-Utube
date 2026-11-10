"""The owner account made on the login page on first visit, like neb-creative-tool (specs/008 FR-118, T037)."""
import threading
import unittest

from helpers import PASSWORD, W, OnlineProject


class Setup(unittest.TestCase):
    def setUp(self):
        self.p = OnlineProject()
        self.c = self.p.client()

    def tearDown(self):
        self.p.close()

    def setup(self, email="owner@x.test", password=PASSWORD, c=None):
        return (c or self.c).post("/api/v1/auth/setup", json={"email": email, "password": password}, headers=W)

    def test_owner_is_made_once(self):
        self.assertEqual(self.c.get("/api/v1/auth/setup").json(), {"needed": True})
        r = self.setup(password="short")
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "weak_password"))
        r = self.setup()
        self.assertEqual(r.status_code, 201, r.text)
        me = self.c.get("/api/v1/me").json()                           # signed in straight away
        self.assertEqual((me["email"], me["role"]), ("owner@x.test", "admin"))
        self.assertEqual(self.c.get("/api/v1/auth/setup").json(), {"needed": False})
        r = self.setup("evil@x.test", c=self.p.client())
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "already_set_up"))
        self.assertFalse((self.p.data / "setup-code").exists())

    def test_only_one_owner_when_two_race(self):
        codes = []
        ts = [threading.Thread(target=lambda e=e: codes.append(self.setup(e, c=self.p.client()).status_code))
              for e in ("a@x.test", "b@x.test", "c@x.test")]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(sorted(codes), [201, 409, 409])

    def test_an_earlier_sign_up_becomes_the_owner_with_its_password(self):
        from studio import accounts
        accounts.signup("me@x.test", PASSWORD, True)                  # an unverified customer from 007
        r = self.setup("ME@x.test", password="another password!")
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "email_taken_password"))
        self.assertEqual(self.c.get("/api/v1/auth/setup").json(), {"needed": True})
        r = self.setup("ME@x.test")
        self.assertEqual(r.status_code, 201, r.text)
        me = self.c.get("/api/v1/me").json()
        self.assertEqual((me["email"], me["role"], me["verified"]), ("me@x.test", "admin", True))
        self.assertEqual(self.c.get("/api/v1/auth/setup").json(), {"needed": False})

    def test_cli_admin_still_works(self):
        from studio import accounts
        accounts.signup("boss@x.test", PASSWORD, True, role="admin", verified=True)
        self.assertEqual(self.c.get("/api/v1/auth/setup").json(), {"needed": False})


if __name__ == "__main__":
    unittest.main()
