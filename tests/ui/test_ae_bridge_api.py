"""The AE bridge paths of API v1 in local mode (specs/031 T020; the full flow with jobs is tests/online/test_ae_bridge.py)."""
import json
import os
import tempfile
import unittest
from pathlib import Path

from helpers import Project, client

KEY = "b" * 43


class AeBridgeApi(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        f = Path(tempfile.mkdtemp()) / "bridge.json"
        f.write_text(json.dumps({"key": KEY}))
        self.old = {k: os.environ.get(k) for k in ("STUDIO_AE_BRIDGE", "STUDIO_DATA")}
        os.environ["STUDIO_AE_BRIDGE"] = str(f)
        os.environ["STUDIO_DATA"] = tempfile.mkdtemp()
        self.c = client()

    def tearDown(self):
        for k, v in self.old.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.p.close()

    def test_paths(self):
        h = {"x-cu-bridge": KEY}
        self.assertEqual(self.c.get("/api/v1/ae/bridge/next").status_code, 403)                     # no key
        self.assertEqual(self.c.post("/api/v1/ae/bridge/hello", json={"found": True}, headers=h).status_code, 200)
        self.assertEqual(self.c.get("/api/v1/ae/bridge/next", headers=h).status_code, 204)
        from ae import aequeue
        rid = aequeue.create("local", "j-1", "demo-film", ["S1"], b"tar")["id"]
        self.assertEqual(self.c.get("/api/v1/ae/bridge/next", headers=h).json()["id"], rid)
        self.assertEqual(self.c.get(f"/api/v1/ae/bridge/{rid}/bundle", headers=h).content, b"tar")
        self.assertEqual(self.c.post(f"/api/v1/ae/bridge/{rid}/progress", json={"state": "running", "shot": "S1"}, headers=h).json()["state"],
                         "running")
        self.assertEqual(self.c.put(f"/api/v1/ae/bridge/{rid}/result/MASTER", content=b"mp4", headers=h).status_code, 201)
        r = self.c.post(f"/api/v1/ae/bridge/{rid}/finish", json={"ok": True, "marks": [[0, 1, "", "S1"]], "duration": 1}, headers=h)
        self.assertEqual(r.json()["state"], "done")
        self.assertEqual(self.c.get(f"/api/v1/ae/bridge/{rid}/bundle", headers=h).status_code, 409)        # finished
        self.assertEqual(self.c.get("/api/v1/ae/bridge/nope/bundle", headers=h).status_code, 404)

    def test_fix_needs_an_ae_film_and_the_app(self):
        r = self.c.post("/api/v1/films/demo-film/fix", json={}, headers={"X-Studio": "1"})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "not_ae"))
        d = self.p.dir / "films" / "demo-film"
        (d / "ae").mkdir()
        (d / "ae" / "s.jsx").write_text("")
        (d / "film.json").write_text(json.dumps({"engine": "ae", "shots": ["S1"], "ae_files": ["s.jsx"]}))
        r = self.c.post("/api/v1/films/demo-film/fix", json={}, headers={"X-Studio": "1"})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "app_only"))     # local mode has no worker
        f = self.c.get("/api/v1/films/demo-film").json()
        self.assertEqual((f["engine"], f["ae_ready"]), ("ae", False))


if __name__ == "__main__":
    unittest.main()
