"""The After Effects bridge (specs/031 T020): the desktop app's key, one request at a time, heartbeats, the proxy."""
import io
import json
import os
import tarfile
import tempfile
import time
import unittest
from pathlib import Path

import httpx

from helpers import Studio, film_job

KEY = "k" * 43


def tar_bytes() -> bytes:
    b = io.BytesIO()
    with tarfile.open(fileobj=b, mode="w") as t:
        data = b"// entry"
        ti = tarfile.TarInfo("entry.jsx"); ti.size = len(data)
        t.addfile(ti, io.BytesIO(data))
    return b.getvalue()


class Bridge(unittest.TestCase):
    def setUp(self):
        self.s = Studio()
        f = Path(tempfile.mkdtemp()) / "bridge.json"
        f.write_text(json.dumps({"key": KEY}))
        self.old = os.environ.get("STUDIO_AE_BRIDGE")
        os.environ["STUDIO_AE_BRIDGE"] = str(f)
        self.web = self.s.client()
        import proxy
        self.c = self.s.signup_verified("ae@example.com")
        self.jid = film_job(self.c).json()["id"]
        self.token = proxy.issue(self.jid)

    def tearDown(self):
        if self.old is None:
            os.environ.pop("STUDIO_AE_BRIDGE", None)
        else:
            os.environ["STUDIO_AE_BRIDGE"] = self.old
        self.s.close()

    def b(self, method, path, key=KEY, **kw):
        h = {"x-cu-bridge": key} if key is not None else {}
        return self.web.request(method, "/api/v1/ae/bridge/" + path, headers=h, **kw)

    def hello(self, found=True):
        return self.b("POST", "hello", json={"version": "1.0", "os": "win32", "afterfx": "C:/AE/AfterFX.exe", "found": found})

    def submit(self, shots=("S1",), token=None):
        return httpx.post(self.s.proxy.url + "/internal/ae/requests", headers={"authorization": f"Bearer {token or self.token}"},
                          files={"meta": (None, json.dumps({"film": "demo-film", "shots": list(shots)}), "application/json"),
                                 "bundle": ("bundle.tar", tar_bytes(), "application/x-tar")}, timeout=30)

    def test_key_wrong_missing_or_not_loopback(self):                      # SC-006
        self.assertEqual(self.b("GET", "next", key=None).status_code, 403)
        self.assertEqual(self.b("GET", "next", key="x" * 43).status_code, 403)
        self.assertEqual(self.b("GET", "next").status_code, 204)
        from studio import aebridge
        self.assertFalse(aebridge.allowed("10.0.0.5", KEY))
        self.assertTrue(aebridge.allowed("127.0.0.1", KEY))
        os.environ.pop("STUDIO_AE_BRIDGE")
        self.assertEqual(self.b("GET", "next").status_code, 403)          # no key file: the bridge is closed

    def test_proxy_refuses_without_hello(self):                            # FR-009
        r = self.submit()
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "ae_unavailable"))
        self.hello(found=False)
        r = self.submit()
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "ae_missing"))

    def test_one_request_at_a_time_and_results(self):
        self.hello()
        a = self.submit(["S1", "S2"]).json()["id"]
        b = self.submit(["S3"]).json()["id"]
        r = self.b("GET", "next")
        self.assertEqual(r.json()["id"], a)
        self.assertEqual(self.b("GET", "next").status_code, 204)            # a is claimed: b waits
        st = httpx.get(self.s.proxy.url + f"/internal/ae/requests/{b}", headers={"authorization": f"Bearer {self.token}"}).json()
        self.assertEqual((st["state"], st["ahead"]), ("queued", 1))
        self.assertEqual(self.b("GET", f"{a}/bundle").content, tar_bytes())
        self.b("POST", f"{a}/progress", json={"state": "running", "shot": "S1", "index": 1, "total": 2})
        self.assertEqual(self.b("PUT", f"{a}/result/MASTER", content=b"mp4-bytes").status_code, 201)
        self.assertEqual(self.b("PUT", f"{a}/result/evil.sh", content=b"x").status_code, 422)
        r = self.b("POST", f"{a}/finish", json={"ok": True, "checks": ["CHECK x"], "marks": [[0, 2, "", "S1"], [2, 4, "", "S2"]],
                                                "duration": 4})
        self.assertEqual(r.json()["state"], "done")
        h = {"authorization": f"Bearer {self.token}"}
        st = httpx.get(self.s.proxy.url + f"/internal/ae/requests/{a}", headers=h).json()
        self.assertEqual((st["state"], st["marks"][1][3]), ("done", "S2"))
        self.assertEqual(httpx.get(self.s.proxy.url + f"/internal/ae/requests/{a}/result/MASTER", headers=h).content, b"mp4-bytes")
        self.assertEqual(self.b("GET", "next").json()["id"], b)              # now b
        self.assertEqual(self.b("POST", f"{a}/progress", json={}).status_code, 409)   # a is finished

    def test_other_job_cannot_read(self):
        import proxy
        self.hello()
        a = self.submit().json()["id"]
        other = proxy.issue(film_job(self.s.signup_verified("other@example.com")).json()["id"])
        r = httpx.get(self.s.proxy.url + f"/internal/ae/requests/{a}", headers={"authorization": f"Bearer {other}"})
        self.assertEqual(r.status_code, 404)

    def test_lost_heartbeat_fails_the_request(self):
        from ae import aequeue
        self.hello()
        a = self.submit().json()["id"]
        self.b("GET", "next")
        real = aequeue.now
        aequeue.now = lambda: real() + 61
        try:
            r = aequeue.get(a)
        finally:
            aequeue.now = real
        self.assertEqual((r["state"], r["error"]["code"]), ("failed", "bridge_lost"))

    def test_status_for_jobs(self):
        h = {"authorization": f"Bearer {self.token}"}
        self.assertFalse(httpx.get(self.s.proxy.url + "/internal/ae/status", headers=h).json()["ready"])
        self.hello()
        st = httpx.get(self.s.proxy.url + "/internal/ae/status", headers=h).json()
        self.assertTrue(st["ready"])
        self.assertEqual(st["afterfx"], "C:/AE/AfterFX.exe")


if __name__ == "__main__":
    unittest.main()
