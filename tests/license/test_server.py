"""License server: keys, leases, seats, revoking, limits, admin (specs/017 T009; SC-005, SC-006)."""
import sqlite3
import unittest

from helpers import T0, admin, device, make, signing, store


class Leases(unittest.TestCase):
    def setUp(self):
        self.s, self.c, self.clock, self.priv, self.pub = make()
        self.h = admin(self.c)
        r = self.c.post("/admin/api/licenses", json={"label": "An", "maxDevices": 1}, headers=self.h)
        self.assertEqual(r.status_code, 201, r.text)
        self.key, self.lid = r.json()["key"], r.json()["licenses"][0]["id"]

    def lease(self, n=1, key=None, ip="1.2.3.4"):
        return self.c.post("/api/license/lease", json={"key": key or self.key, "deviceId": device(n), "deviceName": "PC",
                                                       "os": "win32", "version": "0.2.0"}, headers={"x-real-ip": ip})

    def test_activate_and_renew(self):
        r = self.lease()
        self.assertEqual(r.status_code, 200, r.text)
        b = r.json()
        p = signing.verify_lease(self.pub, b["lease"])
        self.assertEqual((p["did"], p["label"], p["lid"]), (device(1), "An", self.lid))
        self.assertEqual(p["exp"] - p["iat"], 7 * 86400)
        self.assertIsNone(signing.lease_problem(p, device(1), T0))
        self.assertEqual(signing.lease_problem(p, device(2), T0), "device")
        self.assertEqual(signing.lease_problem(p, device(1), T0 + 7 * 86400), "expired")
        self.assertEqual(signing.lease_problem(p, device(1), T0 - 3600), "clock")
        self.assertEqual(signing.lease_problem(p, device(1), T0, clock=T0 + 3600), "clock")
        d = self.c.get("/admin/api/licenses").json()["licenses"][0]["devices"][0]
        self.assertEqual((d["name"], d["os"], d["version"], d["lastIp"]), ("PC", "win32", "0.2.0", "1.2.3.4"))
        self.clock.t += 900
        self.assertEqual(self.lease().status_code, 200)                      # renew: same seat
        self.assertEqual(self.lease(key=self.key.lower().replace("-", " ")).status_code, 200)   # typed loosely

    def test_seats_and_removing(self):
        self.assertEqual(self.lease(1).status_code, 200)
        r = self.lease(2)
        self.assertEqual((r.status_code, r.json()["code"]), (403, "device_limit"))
        self.c.delete(f"/admin/api/licenses/{self.lid}/devices/{device(1)}", headers=self.h)
        self.assertEqual(self.lease(1).json()["code"], "device_removed")
        self.assertEqual(self.lease(2).status_code, 200)                     # the seat is free
        self.c.patch(f"/admin/api/licenses/{self.lid}", json={"maxDevices": 2}, headers=self.h)
        self.c.delete(f"/admin/api/licenses/{self.lid}/devices/{device(1)}", headers=self.h)   # second time: forgotten
        self.assertEqual(self.lease(1).status_code, 200)

    def test_revoke_expire_delete(self):
        self.lease()
        self.c.patch(f"/admin/api/licenses/{self.lid}", json={"revoked": True}, headers=self.h)
        self.assertEqual(self.lease().json()["code"], "revoked")
        self.c.patch(f"/admin/api/licenses/{self.lid}", json={"revoked": False, "expiresAt": T0 + 86400}, headers=self.h)
        p = signing.verify_lease(self.pub, self.lease().json()["lease"])
        self.assertEqual(p["exp"], int(T0 + 86400))                          # never past the key's end
        self.clock.t = T0 + 86400
        self.assertEqual(self.lease().json()["code"], "expired")
        self.h = admin(self.c)                                               # the clock jumped past the session
        self.c.delete(f"/admin/api/licenses/{self.lid}", headers=self.h)
        self.assertEqual(self.lease().json()["code"], "unknown")

    def test_key_shown_once_only_hash_stored(self):                         # SC-005
        listed = self.c.get("/admin/api/licenses").text
        self.assertNotIn(self.key, listed)
        self.assertNotIn(store.normalize_key(self.key), listed)
        raw = (self.s.data / "license.db").read_bytes()
        self.assertNotIn(store.normalize_key(self.key).encode(), raw)
        con = sqlite3.connect(self.s.data / "license.db")
        self.assertEqual(con.execute("SELECT key_hash FROM licenses").fetchone()[0], store.sha(store.normalize_key(self.key)))

    def test_wrong_keys_are_limited(self):                                  # SC-006
        for _ in range(10):
            self.assertEqual(self.lease(key="CU-TEST-TEST-TEST-TEST").json()["code"], "unknown")
        r = self.lease(key="CU-TEST-TEST-TEST-TEST")
        self.assertEqual((r.status_code, r.json()["code"]), (429, "rate_limited"))
        self.assertEqual(self.lease(ip="5.6.7.8").status_code, 200)          # another address
        self.clock.t += 601
        self.assertEqual(self.lease().status_code, 200)

    def test_bad_requests(self):
        r = self.c.post("/api/license/lease", json={"key": self.key, "deviceId": "short"})
        self.assertEqual(r.status_code, 422)
        r = self.c.post("/api/license/lease", content=b"x" * 20000, headers={"content-type": "application/json"})
        self.assertEqual(r.status_code, 413)
        self.assertEqual(self.c.get("/anything").status_code, 404)
        self.assertEqual(self.c.get("/health").json(), {"ok": True})


class Admin(unittest.TestCase):
    def setUp(self):
        self.s, self.c, self.clock, *_ = make()

    def test_needs_sign_in_and_header(self):
        self.assertEqual(self.c.get("/admin/api/licenses").status_code, 401)
        self.assertEqual(self.c.post("/admin/api/login", json={"password": "a-good-admin-password"}).status_code, 403)
        h = admin(self.c)
        self.assertEqual(self.c.get("/admin/api/licenses").status_code, 200)
        self.assertEqual(self.c.post("/admin/api/licenses", json={"label": "x"}).status_code, 403)     # no header
        self.assertEqual(self.c.post("/admin/api/licenses", json={"label": ""}, headers=h).status_code, 422)
        self.assertEqual(self.c.post("/admin/api/licenses", json={"label": "x", "maxDevices": 21}, headers=h).status_code, 422)
        self.c.post("/admin/api/logout")
        self.assertEqual(self.c.get("/admin/api/licenses").status_code, 401)
        self.assertEqual(self.c.get("/admin").status_code, 200)

    def test_wrong_passwords_are_limited(self):
        for _ in range(10):
            r = self.c.post("/admin/api/login", json={"password": "nope"}, headers={"x-cu-admin": "1"})
            self.assertEqual(r.status_code, 401)
        r = self.c.post("/admin/api/login", json={"password": "a-good-admin-password"}, headers={"x-cu-admin": "1"})
        self.assertEqual(r.status_code, 429)

    def test_session_ends(self):
        admin(self.c)
        self.clock.t += store.SESSION_S + 1
        self.assertEqual(self.c.get("/admin/api/licenses").status_code, 401)

    def test_backup_keeps_30(self):
        for i in range(32):
            self.clock.t += 86400
            self.s.backup()
        self.assertEqual(len(list((self.s.data / "backup").glob("license-*.db"))), 30)


class Keys(unittest.TestCase):
    def test_format(self):
        k = store.new_key()
        self.assertRegex(k, r"^CU-([A-HJ-NP-Z2-9]{4}-){3}[A-HJ-NP-Z2-9]{4}$")
        self.assertEqual(store.normalize_key(k.lower().replace("-", "")), k.replace("-", "")[2:])
        self.assertIsNone(store.normalize_key("CU-0000-0000-0000-0000"))     # 0 is not in the alphabet
        self.assertIsNone(store.normalize_key("short"))

    def test_signing(self):
        priv, pub = signing.new_keypair()
        self.assertEqual(signing.public_of(priv), pub)
        sig = signing.sign_bytes(priv, b"hello")
        self.assertTrue(signing.verify_bytes(pub, b"hello", sig))
        self.assertFalse(signing.verify_bytes(pub, b"hellp", sig))
        self.assertFalse(signing.verify_bytes(signing.new_keypair()[1], b"hello", sig))
        self.assertIsNone(signing.verify_lease(pub, "not-a-lease"))


if __name__ == "__main__":
    unittest.main()
