"""Idempotency-Key on job creation (specs/009 FR-221, SC-209): a repeat returns the first job, never a second credit."""
import threading
import unittest

from helpers import PASSWORD, W, Studio


class Idempotency(unittest.TestCase):
    def setUp(self):
        self.s = Studio()
        from studio import accounts, quotas
        quotas.update_settings({"quota_films_default": 10})
        accounts.add_user("m@x.test", PASSWORD)
        self.c = self.s.client()
        assert self.c.post("/api/v1/auth/login", json={"email": "m@x.test", "password": PASSWORD}, headers=W).status_code == 200
        self.style = self.c.get("/api/v1/library").json()["styles"][0]["slug"]

    def tearDown(self):
        self.s.close()

    def body(self, idea="A fox"):
        return {"kind": "film", "style": self.style, "idea": idea, "seconds": 20}

    def used(self):
        return self.c.get("/api/v1/me").json()["quota"]["films"]["used"]

    def test_five_at_once_make_one_job(self):                                    # SC-209
        cookies = dict(self.c.cookies)
        out = []

        def go():
            c = self.s.client()
            c.cookies.update(cookies)
            r = c.post("/api/v1/jobs", json=self.body(), headers={**W, "Idempotency-Key": "k-1"})
            out.append((r.status_code, r.json().get("id"), r.headers.get("idempotent-replayed")))
        ts = [threading.Thread(target=go) for _ in range(5)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len({x[1] for x in out}), 1, out)
        self.assertEqual(sorted(x[0] for x in out), [200, 200, 200, 200, 201])
        self.assertEqual(sum(x[2] == "true" for x in out), 4)
        self.assertEqual(self.used(), 1)

    def test_same_key_other_request_and_expiry(self):
        from studio import store
        r1 = self.c.post("/api/v1/jobs", json=self.body(), headers={**W, "Idempotency-Key": "k-2"})
        self.assertEqual(r1.status_code, 201)
        r = self.c.post("/api/v1/jobs", json=self.body("An owl"), headers={**W, "Idempotency-Key": "k-2"})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "idempotency_conflict"))
        r = self.c.post("/api/v1/jobs", json=self.body(), headers={**W, "Idempotency-Key": "k-3"})
        self.assertEqual(r.status_code, 201)                                       # another key: another job
        self.assertEqual(self.used(), 2)
        real = store.clock
        try:
            store.clock = lambda: real() + 25 * 3600                               # 24 hours later the key is free
            r = self.c.post("/api/v1/jobs", json=self.body("An owl"), headers={**W, "Idempotency-Key": "k-2"})
        finally:
            store.clock = real
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(self.c.post("/api/v1/jobs", json=self.body(), headers={**W, "Idempotency-Key": "x" * 101}).status_code, 422)

    def test_without_a_key_nothing_changes(self):
        self.assertEqual(self.c.post("/api/v1/jobs", json=self.body(), headers=W).status_code, 201)
        self.assertEqual(self.c.post("/api/v1/jobs", json=self.body(), headers=W).status_code, 201)
        self.assertEqual(self.used(), 2)


if __name__ == "__main__":
    unittest.main()
