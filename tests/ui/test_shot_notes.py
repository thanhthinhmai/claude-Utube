"""Per-shot notes on the film page (specs/029): shot marks, notes book, pictures, the previous video, the CLI."""
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

from helpers import REPO, W, Project, client

sys.path.insert(0, str(REPO / "tools"))
from filmcheck import shotnotes  # noqa: E402

PY = str(REPO / "tools" / ".venv" / "bin" / "python")
STUDIO = str(REPO / "bin" / "studio")
API = "/api/v1/films"


def make_video(path: Path, seconds: float, fps: int = 30, size="160x90", color=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    src = f"color=c={color}:s={size}:r={fps}:d={seconds}" if color else f"testsrc=s={size}:r={fps}:d={seconds}"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", src, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    str(path)], check=True)
    return path


def shots_doc(rows, duration, fps=30, video="x.mp4", source="page"):
    return {"version": 1, "video": video, "duration": duration, "fps": fps, "source": source, "shots": rows}


def even_rows(n, duration, prefix="S"):
    step = duration / n
    return [[round(i * step, 3), round((i + 1) * step, 3) if i < n - 1 else duration, "", f"{prefix}{i + 1}"]
            for i in range(n)]


def make_film(root: Path, name: str, seconds=3.0, n=3, fps=30, write_shots=True) -> Path:
    d = root / "films" / name
    make_video(d / f"{name}.mp4", seconds, fps)
    if write_shots:
        (d / "shots.json").write_text(json.dumps(shots_doc(even_rows(n, seconds), seconds, fps, f"{name}.mp4")))
    return d


PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\0" * 64
WEBP = b"RIFF\x24\0\0\0WEBPVP8 " + b"\0" * 64
PDF = b"%PDF-1.4\n" + b"\0" * 64


def tree(root: Path) -> dict:
    out = {}
    for p in root.rglob("*"):
        if ".studio" in p.parts or not p.is_file():
            continue
        out[str(p.relative_to(root))] = p.stat().st_mtime_ns
    return out


def _online_helpers():
    spec = importlib.util.spec_from_file_location("online_helpers", REPO / "tests" / "online" / "helpers.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _have_online():
    try:
        import argon2  # noqa: F401
        return True
    except ImportError:
        return False


# ---------- T006: paths and access (FR-010, FR-016, SC-007) ----------
class PathSafety(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.c = client()
        make_film(self.p.dir, "demo-film", 3.0, 3)

    def tearDown(self):
        self.p.close()

    def routes(self, name, img="img-0a1b2c3d4e5f.png"):
        b = f"{API}/{name}"
        return [("GET", f"{b}/shots", None), ("GET", f"{b}/shots?prev=1", None), ("GET", f"{b}/shots/thumbs/1/a.jpg", None),
                ("GET", f"{b}/video?prev=1", None), ("GET", f"{b}/notes", None),
                ("PUT", f"{b}/notes", {"base": shotnotes.EMPTY_SHA, "doc": {"version": 1, "shots": {}}}),
                ("POST", f"{b}/notes/images", "file"), ("GET", f"{b}/notes/images/{img}", None)]

    def call(self, method, url, body):
        if body == "file":
            return self.c.post(url, files={"file": ("a.png", PNG, "image/png")}, headers=W)
        if method == "PUT":
            return self.c.put(url, json=body, headers=W)
        return self.c.get(url)

    def test_bad_film_names_and_image_names(self):
        before = tree(self.p.dir)
        for name in ("Bad_Name", "..", "%2e%2e", "a.b", "x%20y", "-" * 61):        # reach the handler: 400 bad_name
            for method, url, body in self.routes(name):
                r = self.call(method, url, body)
                self.assertEqual(r.status_code, 400, (method, url, r.text))
                self.assertEqual(r.json()["error"]["code"], "bad_name", url)
        for name in ("..%2Fx", "a%2Fb", "%2e%2e%2fsecret.txt", "..%2F..%2Fetc"):          # never served, never written
            for method, url, body in self.routes(name):
                r = self.call(method, url, body)
                self.assertIn(r.status_code, (400, 404, 405), (method, url))
                self.assertNotIn("do not serve", r.text)
        for img in ("img-zz.png", "img-0a1b2c3d4e5f.gif", "IMG-0a1b2c3d4e5f.png", "img-0a1b2c3d4e5f.png.x",
                    "%2e%2e%2f%2e%2e%2fsecret.txt"):
            r = self.c.get(f"{API}/demo-film/notes/images/{img}")
            self.assertIn(r.status_code, (400, 404), img)
            if r.status_code == 400:
                self.assertEqual(r.json()["error"]["code"], "bad_name")
            self.assertNotIn("do not serve", r.text)
        r = self.c.get(f"{API}/demo-film/notes/images/img-zz.png")
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (400, "bad_name"))
        self.assertEqual(tree(self.p.dir), before)                     # nothing made anywhere

    def test_no_film_is_not_found(self):
        for method, url, body in self.routes("no-such-film"):
            r = self.call(method, url, body)
            self.assertEqual(r.status_code, 404, (method, url))
        self.assertFalse((self.p.dir / "films" / "no-such-film").exists())

    def test_film_paths_stay_inside(self):
        d = self.p.dir / "films" / "demo-film"
        for k, p in shotnotes.film_paths(d).items():
            self.assertTrue(p.is_relative_to(d.resolve()), k)
        with self.assertRaises(shotnotes.ShotError):
            shotnotes.image_path(d, "../../secret.txt")
        with self.assertRaises(shotnotes.ShotError):
            shotnotes.film_paths(self.p.dir / "films" / "Bad")


@unittest.skipUnless(_have_online(), "needs sh bin/studio deps online")
class OnlineAccess(unittest.TestCase):
    def setUp(self):
        self.h = _online_helpers()
        self.s = self.h.OnlineProject()
        self.a = self.s.signup_verified("a@example.com")
        self.b = self.s.signup_verified("b@example.com")
        aid = self.h.account_id(self.a)
        self.s.copy_fixtures_to(aid)
        from studio import store
        make_film(store.account_dir(aid), "demo-film", 3.0, 3)

    def tearDown(self):
        self.s.close()

    def test_only_the_owner_reads_and_writes(self):
        base = self.a.get(f"{API}/demo-film/notes").json()["base"]
        doc = {"version": 1, "shots": {"S1": {"status": "none", "status_by": "auto",
                                               "notes": [{"at": None, "text": "secret note", "images": [], "done": False}]}}}
        r = self.a.put(f"{API}/demo-film/notes", json={"base": base, "doc": doc}, headers=W)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["doc"]["shots"]["S1"]["notes"][0]["by"], "a@example.com")
        for method, url in (("GET", "/notes"), ("GET", "/shots"), ("PUT", "/notes"), ("POST", "/notes/images")):
            if method == "GET":
                rb = self.b.get(f"{API}/demo-film{url}")
            elif method == "PUT":
                rb = self.b.put(f"{API}/demo-film{url}", json={"base": base, "doc": doc}, headers=W)
            else:
                rb = self.b.post(f"{API}/demo-film{url}", files={"file": ("a.png", PNG, "image/png")}, headers=W)
            self.assertEqual(rb.status_code, 404, (method, url, rb.text))
            self.assertNotIn("secret note", rb.text)

    def test_read_only_token_cannot_write(self):
        from studio import tokens
        from studio import accounts
        owner = accounts.current(self.a.cookies.get(accounts.COOKIE))
        secret = tokens.create(owner, "reader")[1]
        real = tokens.resolve

        def as_reader(s):
            got = real(s)
            return (got[0], got[1], "viewer") if got else got
        tokens.resolve = as_reader
        try:
            c = self.s.client()
            hdr = {"Authorization": f"Bearer {secret}"}
            r = c.get(f"{API}/demo-film/notes", headers=hdr)
            self.assertEqual(r.status_code, 200, r.text)
            put = c.put(f"{API}/demo-film/notes", json={"base": r.json()["base"], "doc": {"version": 1, "shots": {}}},
                        headers=hdr)
            self.assertEqual((put.status_code, put.json()["error"]["code"]), (403, "forbidden"))
            img = c.post(f"{API}/demo-film/notes/images", files={"file": ("a.png", PNG, "image/png")}, headers=hdr)
            self.assertEqual((img.status_code, img.json()["error"]["code"]), (403, "forbidden"))
        finally:
            tokens.resolve = real


if __name__ == "__main__":
    unittest.main()
