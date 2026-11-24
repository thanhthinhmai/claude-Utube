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
        for name in ("Bad_Name", "%2e%2e", "a.b", "x%20y", "-" * 61):        # reach the handler: 400 bad_name
            for method, url, body in self.routes(name):
                r = self.call(method, url, body)
                self.assertEqual(r.status_code, 400, (method, url, r.text))
                self.assertEqual(r.json()["error"]["code"], "bad_name", url)
        for name in ("..", "..%2Fx", "a%2Fb", "%2e%2e%2fsecret.txt", "..%2F..%2Fetc"):          # never served, never written
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

    def test_every_route_answers(self):            # the literal paths, for test_api's contract check
        for url in ("/api/v1/films/demo-film/shots", "/api/v1/films/demo-film/notes"):
            self.assertEqual(self.c.get(url).status_code, 200, url)
        self.assertIn(self.c.get("/api/v1/films/demo-film/shots/thumbs/1/a.jpg").status_code, (200, 202))
        up = self.c.post("/api/v1/films/demo-film/notes/images", files={"file": ("a.png", PNG, "image/png")}, headers=W)
        self.assertEqual(up.status_code, 201)
        self.assertEqual(self.c.get(f"/api/v1/films/demo-film/notes/images/{up.json()['file']}").status_code, 200)
        r = self.c.put("/api/v1/films/demo-film/notes", json={"base": shotnotes.EMPTY_SHA, "doc": {"version": 1, "shots": {}}}, headers=W)
        self.assertEqual(r.status_code, 200)

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


# ---------- T007: the shot marks file (data-model "Mốc shot") ----------
class LoadShots(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile
        cls.tmp = Path(tempfile.mkdtemp(prefix="shots."))
        cls.d = cls.tmp / "films" / "long-film"
        make_video(cls.d / "long-film.mp4", 30.0, 30, color="gray")

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def load(self, rows, **kw):
        (self.d / "shots.json").write_text(json.dumps(shots_doc(rows, 30.0, video="long-film.mp4", **kw)))
        return shotnotes.load_shots(self.d)

    def rules(self, rows):
        r = self.load(rows)
        self.assertFalse(r["valid"])
        self.assertEqual(r["shots"], [])
        for p in r["problems"]:
            self.assertEqual(set(p), {"row", "rule", "detail"})
        return {p["rule"] for p in r["problems"]}

    def test_good_files(self):
        r = self.load(even_rows(40, 30.0), source="ae")
        self.assertTrue(r["valid"], r["problems"])
        self.assertEqual(len(r["shots"]), 40)
        self.assertEqual(r["shots"][36], {"n": 37, "id": "S37", "set": "", "t0": 27.0, "t1": 27.75})
        self.assertEqual((r["source"], r["fps"], r["duration"]), ("ae", 30, 30.0))
        self.assertTrue(self.load(even_rows(300, 30.0))["valid"])
        rows = even_rows(3, 30.0)
        rows[1][0] += 0.02                                   # within one frame (1/30 s)
        rows[2][1] = 30.03
        self.assertTrue(self.load(rows)["valid"])

    def test_each_rule(self):
        self.assertIn("count", self.rules(even_rows(301, 30.0)))
        self.assertIn("count", self.rules([]))
        rows = even_rows(3, 30.0); rows[0][0] = 0.5
        self.assertIn("start", self.rules(rows))
        rows = even_rows(3, 30.0); rows[1][1] = rows[1][0]
        self.assertIn("length", self.rules(rows))
        rows = even_rows(3, 30.0); rows[2][0] += 0.5
        self.assertIn("gap", self.rules(rows))
        rows = even_rows(3, 30.0); rows[1][0] -= 0.5
        self.assertIn("gap", self.rules(rows))                # overlap
        rows = even_rows(3, 30.0); rows[2][1] = 31.0
        self.assertIn("end", self.rules(rows))
        rows = even_rows(3, 30.0); rows[2][1] = 29.0
        self.assertIn("end", self.rules(rows))
        rows = even_rows(3, 30.0); rows[2][3] = "S1"
        self.assertIn("duplicate_id", self.rules(rows))
        rows = even_rows(3, 30.0); rows[1] = "nope"
        self.assertIn("row", self.rules(rows))
        rows = even_rows(3, 30.0); rows[1][3] = ""
        self.assertIn("id", self.rules(rows))
        r = self.rules(even_rows(3, 30.0)[:2] + [[19.5, 25.0, "", "S3"], [25.0, 30.0, "", "S3"]])
        self.assertTrue({"gap", "duplicate_id"} <= r, r)

    def test_missing_and_broken(self):
        (self.d / "shots.json").unlink(missing_ok=True)
        r = shotnotes.load_shots(self.d)
        self.assertEqual((r["valid"], r["missing"], r["shots"]), (False, True, []))
        (self.d / "shots.json").write_text("{not json")
        r = shotnotes.load_shots(self.d)
        self.assertEqual((r["valid"], r["missing"]), (False, False))
        self.assertEqual(r["problems"][0]["rule"], "json")
        with self.assertRaises(shotnotes.ShotError):
            shotnotes.load_shots(self.d, prev=True)            # no previous set


# ---------- T008: GET /shots and the small pictures ----------
class ShotsApi(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.c = client()
        self.d = make_film(self.p.dir, "demo-film", 3.0, 3)

    def tearDown(self):
        self.p.close()

    def wait_thumb(self, url, timeout=30):
        t = time.time()
        while time.time() - t < timeout:
            r = self.c.get(url)
            if r.status_code != 202:
                return r
            time.sleep(0.2)
        self.fail("small pictures never came")

    def test_shots_and_thumbs(self):
        f = self.c.get(f"{API}/demo-film").json()
        self.assertEqual((f["has_shots"], f["has_prev"]), (True, False))
        self.assertEqual(f["engine"], "page")                  # specs/032: no film.json → web page engine
        r = self.c.get(f"{API}/demo-film/shots").json()
        self.assertTrue(r["valid"], r)
        self.assertEqual([s["id"] for s in r["shots"]], ["S1", "S2", "S3"])
        self.assertEqual(r["shots"][1]["n"], 2)
        self.assertIn(r["thumbs"], ("ready", "building"))
        stamp = r["video_stamp"]
        first = self.c.get(f"{API}/demo-film/shots/thumbs/2/b.jpg")
        self.assertIn(first.status_code, (200, 202))
        if first.status_code == 202:
            self.assertEqual(first.json()["status"], "building")
        got = self.wait_thumb(f"{API}/demo-film/shots/thumbs/2/b.jpg")
        self.assertEqual(got.status_code, 200)
        self.assertEqual(got.headers["content-type"], "image/jpeg")
        self.assertIn("max-age=86400", got.headers["cache-control"])
        self.assertTrue(got.content.startswith(b"\xff\xd8"))
        for n, w in ((0, "a"), (4, "a"), (2, "d"), ("x", "a")):
            self.assertEqual(self.c.get(f"{API}/demo-film/shots/thumbs/{n}/{w}.jpg").status_code, 404, (n, w))
        self.assertEqual(self.wait_thumb(f"{API}/demo-film/shots/thumbs/3/c.jpg").status_code, 200)
        self.assertEqual(self.c.get(f"{API}/demo-film/shots").json()["thumbs"], "ready")
        old = self.d / ".shots" / "thumbs" / stamp
        self.assertTrue(old.is_dir())
        time.sleep(0.05)
        make_video(self.d / "demo-film.mp4", 3.0, 30, size="192x108")       # a new video: new stamp, old cache gone
        r2 = self.c.get(f"{API}/demo-film/shots").json()
        self.assertNotEqual(r2["video_stamp"], stamp)
        self.assertEqual(self.wait_thumb(f"{API}/demo-film/shots/thumbs/1/a.jpg").status_code, 200)
        self.assertFalse(old.exists())
        self.assertTrue((self.d / ".shots" / "thumbs" / r2["video_stamp"]).is_dir())

    def test_missing_and_invalid(self):
        (self.d / "shots.json").unlink()
        r = self.c.get(f"{API}/demo-film/shots").json()
        self.assertEqual((r["valid"], r["missing"], r["shots"]), (False, True, []))
        self.assertFalse(self.c.get(f"{API}/demo-film").json()["has_shots"])
        self.assertEqual(self.c.get(f"{API}/demo-film/shots/thumbs/1/a.jpg").status_code, 404)
        (self.d / "shots.json").write_text(json.dumps(shots_doc([[0, 1, "", "S1"], [1.5, 3, "", "S2"]], 3.0)))
        r = self.c.get(f"{API}/demo-film/shots").json()
        self.assertFalse(r["valid"])
        self.assertEqual(r["problems"][0]["row"], 2)
        self.assertEqual(self.c.get(f"{API}/demo-film/shots?prev=1").status_code, 404)
        self.assertEqual(self.c.get(f"{API}/demo-film/video?prev=1").status_code, 404)


# ---------- US2: the notes book (T019–T022) ----------
def note(text="tay bị bàn che", at=None, images=(), done=False, **kw):
    return {"at": at, "text": text, "images": list(images), "done": done, **kw}


class NotesApi(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.c = client()
        self.d = make_film(self.p.dir, "demo-film", 3.0, 3)         # S1 0–1, S2 1–2, S3 2–3
        self.url = f"{API}/demo-film/notes"

    def tearDown(self):
        self.p.close()

    def get(self):
        r = self.c.get(self.url)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def put(self, doc, base=None, client=None):
        base = self.get()["base"] if base is None else base
        return (client or self.c).put(self.url, json={"base": base, "doc": doc}, headers=W)

    def shot(self, notes, status="none", by="auto"):
        return {"status": status, "status_by": by, "notes": notes}

    def image(self, data=PNG, name="a.png", client=None):
        return (client or self.c).post(f"{self.url}/images", files={"file": (name, data, "image/png")}, headers=W)

    # T019
    def test_validation(self):
        g = self.get()
        self.assertEqual((g["base"], g["doc"], g["orphans"]), (hashlib.sha256(b"").hexdigest(), {"version": 1, "shots": {}}, []))
        self.assertEqual(self.put({"version": 1, "shots": {"S1": self.shot([note("x" * 2000)])}}).status_code, 200)
        img = self.image().json()["file"]
        cases = [
            ({"S1": self.shot([note("x" * 2001)])}, "text"),
            ({"S1": self.shot([note("   ")])}, "text"),
            ({"S1": self.shot([note("", images=[img] * 5)])}, "images"),
            ({"S1": self.shot([note("a", images=["../x.png"])])}, "images"),
            ({"S1": self.shot([note("a", images=["img-000000000000.png"])])}, "images"),
            ({"S1": self.shot([note("a")], status="broken")}, "status"),
            ({"S1": self.shot([note("a", at=-0.1)])}, "at"),
            ({"S1": self.shot([note("a", at=1.5)])}, "at"),          # S1 is 1 s long
            ({"S1": self.shot([note("a", at="5")])}, "at"),
            ({"S1": self.shot([note("a", done="yes")])}, "done"),
            ({"S1": self.shot([note("a", reply="r" * 2001)])}, "reply"),
            ({"S1": {"status": "none", "status_by": "auto", "notes": "nope"}}, "notes"),
        ]
        for shots, field in cases:
            r = self.put({"version": 1, "shots": shots})
            self.assertEqual(r.status_code, 422, (field, r.text))
            e = r.json()["error"]
            self.assertEqual(e["code"], "invalid")
            self.assertIn(field, e["field"], e)
        r = self.put({"version": 1, "shots": {"S1": self.shot([note("", images=[img])])}})        # a picture only is fine
        self.assertEqual(r.status_code, 200, r.text)
        n = r.json()["doc"]["shots"]["S1"]["notes"][0]
        self.assertRegex(n["id"], r"^n-[0-9a-f]{8}$")
        self.assertEqual((n["by"], n["images"]), ("local", [img]))
        self.assertTrue(n["created"] and n["updated"])
        self.assertEqual(self.put({"version": 1, "shots": {}}, base="0" * 64).status_code, 409)

    # T020
    def test_status_rules(self):
        r = self.put({"version": 1, "shots": {"S2": self.shot([note("a"), note("b")])}}).json()
        self.assertEqual(r["doc"]["shots"]["S2"]["status"], "fix")
        ns = r["doc"]["shots"]["S2"]["notes"]
        ns[0]["done"] = True
        r = self.put(r["doc"], r["base"]).json()
        self.assertEqual(r["doc"]["shots"]["S2"]["status"], "fix")              # one still open
        r["doc"]["shots"]["S2"]["notes"][1]["done"] = True
        r = self.put(r["doc"], r["base"]).json()
        self.assertEqual((r["doc"]["shots"]["S2"]["status"], r["doc"]["shots"]["S2"]["status_by"]), ("fixed", "auto"))
        r["doc"]["shots"]["S2"]["notes"][1]["done"] = False
        r = self.put(r["doc"], r["base"]).json()
        self.assertEqual(r["doc"]["shots"]["S2"]["status"], "fix")
        r["doc"]["shots"]["S2"].update(status="ok", status_by="user")             # set by hand: kept
        r = self.put(r["doc"], r["base"]).json()
        self.assertEqual((r["doc"]["shots"]["S2"]["status"], r["doc"]["shots"]["S2"]["status_by"]), ("ok", "user"))
        r = self.put(r["doc"], r["base"]).json()                                  # saving again keeps it
        self.assertEqual(r["doc"]["shots"]["S2"]["status"], "ok")
        r["doc"]["shots"]["S2"]["notes"].append(note("c"))                        # the next note change: auto again
        r = self.put(r["doc"], r["base"]).json()
        self.assertEqual((r["doc"]["shots"]["S2"]["status"], r["doc"]["shots"]["S2"]["status_by"]), ("fix", "auto"))
        r["doc"]["shots"]["S2"]["notes"] = []
        r = self.put(r["doc"], r["base"]).json()
        self.assertEqual(r["doc"]["shots"].get("S2", {}).get("status", "none"), "none")
        r["doc"]["shots"]["S3"] = self.shot([], status="ok", by="user")           # "No issue" on a shot with no notes
        r = self.put(r["doc"], r["base"]).json()
        self.assertEqual(r["doc"]["shots"]["S3"]["status"], "ok")
        r["doc"]["shots"]["S9"] = self.shot([note("old shot")])                   # a shot no longer in shots.json
        r = self.put(r["doc"], r["base"]).json()
        self.assertEqual(self.get()["orphans"], ["S9"])
        on_disk = json.loads((self.d / "shot-notes.json").read_text())
        self.assertEqual(on_disk, self.get()["doc"])
        self.assertEqual(hashlib.sha256((self.d / "shot-notes.json").read_bytes()).hexdigest(), self.get()["base"])

    # T021
    def test_concurrent_saves_lose_nothing(self):
        c2 = client()
        lost = []
        for k in range(20):
            base = self.get()["base"]
            gate = threading.Barrier(2)
            res = {}

            def add(who, cl):
                g = cl.get(self.url).json()
                doc = g["doc"]
                gate.wait()
                doc.setdefault("shots", {}).setdefault("S1", self.shot([]))["notes"].append(note(f"{who}-{k}"))
                r = cl.put(self.url, json={"base": g["base"], "doc": doc}, headers=W)
                if r.status_code == 409:
                    cur = r.json()["error"]["current"]
                    doc = cur["doc"]
                    doc.setdefault("shots", {}).setdefault("S1", self.shot([]))["notes"].append(note(f"{who}-{k}"))
                    r = cl.put(self.url, json={"base": cur["base"], "doc": doc}, headers=W)
                res[who] = r.status_code
            ts = [threading.Thread(target=add, args=(w, cl)) for w, cl in (("a", self.c), ("b", c2))]
            [t.start() for t in ts]
            [t.join() for t in ts]
            if set(res.values()) != {200}:
                lost.append((k, res, base))
        self.assertEqual(lost, [])
        texts = [n["text"] for n in self.get()["doc"]["shots"]["S1"]["notes"]]
        self.assertEqual(len(texts), 40)
        self.assertEqual(len(set(texts)), 40)

    # T022
    def test_images(self):
        from studio import store
        got = {}
        for data, ext in ((PNG, "png"), (JPG, "jpg"), (WEBP, "webp")):
            r = self.image(data, f"x.{ext}")
            self.assertEqual(r.status_code, 201, r.text)
            self.assertRegex(r.json()["file"], rf"^img-[0-9a-f]{{12}}\.{ext}$")
            got[ext] = r.json()["file"]
            g = self.c.get(f"{self.url}/images/{got[ext]}")
            self.assertEqual((g.status_code, g.content), (200, data))
        big = self.image(PNG + b"\0" * (10 * 1024 * 1024 + 1 - len(PNG)))
        self.assertEqual((big.status_code, big.json()["error"]["code"]), (413, "too_large"))
        self.assertEqual(self.image(PNG + b"\0" * (10 * 1024 * 1024 - len(PNG))).status_code, 201)     # exactly 10 MB
        huge = self.image(PNG + b"\0" * (11 * 1024 * 1024))                    # refused from its Content-Length
        self.assertEqual((huge.status_code, huge.json()["error"]["code"]), (413, "too_large"))
        for bad in (PDF, b"GIF89a" + b"\0" * 20, b"not a png at all"):
            r = self.image(bad, "fake.png")
            self.assertEqual((r.status_code, r.json()["error"]["code"]), (415, "bad_image"))
        self.assertEqual(self.c.get(f"{self.url}/images/img-0123456789ab.png").status_code, 404)
        folder = self.d / "shot-notes"
        keep = got["png"]
        r = self.put({"version": 1, "shots": {"S1": self.shot([note("with picture", images=[keep])])}})
        self.assertEqual(r.status_code, 200, r.text)
        real = store.clock
        try:
            store.clock = lambda: real() + shotnotes.ORPHAN_IMAGE_AGE + 60      # an hour later
            fresh = self.image().json()["file"]                                  # just added, not in a note yet
            r = self.put(r.json()["doc"], r.json()["base"])
            self.assertEqual(r.status_code, 200)
            names = {f.name for f in folder.iterdir() if not f.name.endswith(".lock")}
            self.assertIn(keep, names)                                           # in a note
            self.assertIn(fresh, names)                                          # younger than an hour
            self.assertNotIn(got["jpg"], names)                                  # old and in no note
            self.assertNotIn(got["webp"], names)
            doc = r.json()["doc"]
            doc["shots"]["S1"]["notes"][0]["images"] = []                        # taken off the note: gone now
            r = self.put(doc, r.json()["base"])
            self.assertEqual(r.status_code, 200, r.text)
            self.assertFalse((folder / keep).exists())
        finally:
            store.clock = real


# ---------- US3: notes show|reply, film replace (T029, T030) ----------
def studio(*args, root: Path):
    env = {**os.environ, "STUDIO_ROOT": str(root)}
    return subprocess.run(["sh", STUDIO, *args], capture_output=True, text=True, env=env, timeout=120)


class NotesCli(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.d = make_film(self.p.dir, "demo-film", 3.0, 3)
        img = shotnotes.save_image(self.d, PNG)
        b = shotnotes.read_notes(self.d)["base"]
        doc = {"version": 1, "shots": {
            "S2": {"status": "none", "status_by": "auto", "notes": [note("tay bị bàn che", at=0.5, images=[img]),
                                                                    note("logo sai", done=True)]},
            "S3": {"status": "none", "status_by": "auto", "notes": [note("cả shot quá tối")]}}}
        self.r = shotnotes.save_notes(self.d, b, doc, "local")
        self.img = img

    def tearDown(self):
        self.p.close()

    def run_(self, *args):
        return studio(*args, "--dir", str(self.d), root=self.p.dir)

    def test_show(self):
        r = self.run_("notes", "show", "demo-film")
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.splitlines()
        self.assertEqual(lines[0], f"film: {self.d.resolve()}")
        self.assertEqual(lines[-1], f"base: {self.r['base']}")
        out = r.stdout
        self.assertIn("Shot 2 · S2 · 0:01.0–0:02.0", out)
        self.assertIn("at 0:00.5 in the shot · 0:01.5 in the film", out)
        self.assertIn("tay bị bàn che", out)
        self.assertIn(str(self.d.resolve() / "shot-notes" / self.img), out)
        self.assertIn("Shot 3 · S3", out)
        self.assertNotIn("logo sai", out)                                  # fixed notes only with --all
        self.assertIn("2 open notes", out)
        self.assertIn("logo sai", self.run_("notes", "show", "demo-film", "--all").stdout)
        j = self.run_("notes", "show", "demo-film", "--json")
        self.assertEqual(j.returncode, 0, j.stderr)
        data = json.loads(j.stdout)
        self.assertEqual(data["base"], self.r["base"])
        self.assertEqual(len(data["shots"]), 3)
        self.assertIn("S2", data["doc"]["shots"])
        self.assertEqual(studio("notes", "show", "no-such-film", root=self.p.dir).returncode, 2)

    def test_reply(self):
        nid = self.r["doc"]["shots"]["S2"]["notes"][0]["id"]
        r = self.run_("notes", "reply", "demo-film", nid, "Đã đẩy bàn xuống", "--done", "--base", self.r["base"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        g = shotnotes.read_notes(self.d)
        self.assertIn(f"base: {g['base']}", r.stdout)
        n = g["doc"]["shots"]["S2"]["notes"][0]
        self.assertEqual((n["done"], n["reply"]), (True, "Đã đẩy bàn xuống"))
        self.assertEqual(g["doc"]["shots"]["S2"]["status"], "fixed")
        r = self.run_("notes", "reply", "demo-film", nid, "x", "--done", "--base", self.r["base"])     # old base
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        r = self.run_("notes", "reply", "demo-film", "n-00000000", "x", "--base", g["base"])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        r = self.run_("notes", "reply", "demo-film", nid, "Chưa đúng, mở lại", "--open", "--base", g["base"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        g = shotnotes.read_notes(self.d)
        self.assertEqual(g["doc"]["shots"]["S2"]["status"], "fix")
        sid3 = g["doc"]["shots"]["S3"]["notes"][0]["id"]
        r = self.run_("notes", "reply", "demo-film", sid3, "Không sửa được: thiếu ánh sáng gốc", "--base", g["base"])
        self.assertEqual(r.returncode, 0)
        n3 = shotnotes.read_notes(self.d)["doc"]["shots"]["S3"]["notes"][0]
        self.assertEqual((n3["done"], n3["reply"]), (False, "Không sửa được: thiếu ánh sáng gốc"))
        self.assertEqual(self.run_("notes", "reply", "demo-film", nid, "x").returncode, 2)          # --base missing


class FilmReplace(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.c = client()
        self.d = make_film(self.p.dir, "demo-film", 3.0, 3)
        self.new = make_video(self.p.dir / "new" / "v2.mp4", 4.0, 30, color="red")
        self.new_shots = self.p.dir / "new" / "shots.json"
        self.new_shots.write_text(json.dumps(shots_doc(even_rows(2, 4.0, "N"), 4.0, source="ae")))

    def tearDown(self):
        self.p.close()

    def replace(self, *args):
        return studio("film", "replace", "demo-film", *args, "--dir", str(self.d), root=self.p.dir)

    def test_replace_keeps_one_previous(self):
        video = self.d / "demo-film.mp4"
        elsewhere = self.p.dir / "project-copy.mp4"
        os.link(video, elsewhere)                                        # like the app's hard-linked copy
        old_bytes, old_ino = video.read_bytes(), video.stat().st_ino
        shotnotes.thumbs_state(self.d, shotnotes.load_shots(self.d)["shots"])
        r = self.replace(str(self.new), "--shots", str(self.new_shots))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("2 shots", r.stdout)
        self.assertEqual(elsewhere.read_bytes(), old_bytes)               # the other copy is untouched
        self.assertNotEqual(video.stat().st_ino, old_ino)                 # a new file, not written into the old one
        self.assertEqual((self.d / "demo-film.prev.mp4").read_bytes(), old_bytes)
        self.assertEqual(video.read_bytes(), self.new.read_bytes())
        self.assertTrue(self.new.is_file())                               # the source is left where it was
        self.assertEqual([s["id"] for s in shotnotes.load_shots(self.d)["shots"]], ["N1", "N2"])
        self.assertEqual([s["id"] for s in shotnotes.load_shots(self.d, prev=True)["shots"]], ["S1", "S2", "S3"])
        self.assertFalse(any((self.d / ".shots" / "thumbs").glob("*/.done")))      # old small pictures gone
        f = self.c.get(f"{API}/demo-film").json()
        self.assertTrue(f["has_prev"])
        self.assertEqual([s["id"] for s in self.c.get(f"{API}/demo-film/shots?prev=1").json()["shots"]], ["S1", "S2", "S3"])
        pv = self.c.get(f"{API}/demo-film/video?prev=1")
        self.assertEqual((pv.status_code, pv.content), (200, old_bytes))
        third = make_video(self.p.dir / "new" / "v3.mp4", 4.0, 30, color="blue")
        r = self.replace(str(third))                                      # no --shots: the marks still fit 4 s
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.d / "demo-film.prev.mp4").read_bytes(), self.new.read_bytes())    # only one previous
        self.assertEqual([s["id"] for s in shotnotes.load_shots(self.d, prev=True)["shots"]], ["N1", "N2"])
        self.assertEqual([s["id"] for s in shotnotes.load_shots(self.d)["shots"]], ["N1", "N2"])
        self.assertEqual(sorted(p.name for p in self.d.glob("*.mp4")), ["demo-film.mp4", "demo-film.prev.mp4"])

    def test_refused_changes_nothing(self):
        before = tree(self.d)
        broken = self.p.dir / "new" / "broken.mp4"
        broken.write_bytes(b"not a video at all")
        self.assertEqual(self.replace(str(broken)).returncode, 1)
        wrong = self.p.dir / "new" / "wrong.json"
        wrong.write_text(json.dumps(shots_doc(even_rows(2, 3.0), 3.0)))  # 3 s of marks for a 4 s video
        r = self.replace(str(self.new), "--shots", str(wrong))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self.replace(str(self.p.dir / "new" / "none.mp4")).returncode, 1)
        self.assertEqual(tree(self.d), before)
        self.assertEqual(studio("film", "replace", "demo-film", root=self.p.dir).returncode, 2)


@unittest.skipUnless(__import__("shutil").which("node") and (REPO / "lib" / "lemo-opuscar" / "node_modules" / "playwright-core").is_dir(),
                     "no node / playwright-core")
class BrowserShots(unittest.TestCase):
    def test_shots_section_in_a_browser(self):
        p = Project(ports="18830-18839")
        try:
            d = make_film(p.dir, "demo-film", 3.0, 3)
            make_video(d / "demo-film.prev.mp4", 3.0, 30, color="blue")
            (d / "shots.prev.json").write_text((d / "shots.json").read_text())
            self.assertEqual(p.cli("ui").returncode, 0)
            port = json.loads((p.dir / ".studio" / "server.json").read_text())["port"]
            r = subprocess.run(["node", str(REPO / "tests" / "ui" / "browser_shots.cjs"), f"http://127.0.0.1:{port}", "demo-film", "", str(d)],
                               capture_output=True, text=True, timeout=180,
                               env={**os.environ, "NODE_PATH": str(REPO / "lib" / "lemo-opuscar" / "node_modules")})
            if r.returncode == 77:
                self.skipTest("no browser")
            out = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertNotIn("failed", out, out)
            self.assertEqual(out["errors"], [])
            self.assertEqual((out["cells"], out["rows"]), (3, 3))
            self.assertEqual((out["paneTitle"], out["nextTitle"], out["nextDisabled"]), ("Shot 2", "Shot 3", True))
            if out["playable"]:
                self.assertLessEqual(abs(out["stoppedAt"] - 2.0), 0.2, out)       # SC-003
                self.assertEqual((out["pauseShown"], out["afterStopLabel"]), ("Pause", "Play this shot"), out)   # toggle
                self.assertEqual((out["pausedByHand"], out["afterPauseLabel"]), (True, "Play this shot"), out)
            self.assertEqual((out["otherShotBox"], out["backBox"], out["unsavedMsg"]), ("", "nháp shot 2", "Saved"))   # box per shot, saved
            self.assertEqual(len(out["typedSaved"]), 1, out)                                                          # typing alone saves:
            self.assertTrue(out["typedSaved"][0].endswith("gõ là lưu"), out)                                          # one note, last text
            self.assertEqual((out["liveNote"], out["liveVideo"]), (True, True), out)   # outside changes show without a reload
            self.assertEqual(out["noteTextKept"], "tay người ngồi bị bàn che")
            self.assertIn("st-fix", out["cell2"])
            self.assertEqual((out["fixRows"], out["afterReload"], out["afterReloadImg"]), (1, 1, 1))
            self.assertEqual(out["fixedBadge"], "Fixed")
            self.assertEqual(out["copyLabel"], "Copied")
            if out["clipboard"] is not None:
                self.assertEqual(out["clipboard"], "Sửa theo ghi chú phim demo-film")
            self.assertEqual(out["prevButton"], 1)
            self.assertIn("Previous version · shot 2", out["prevNote"])
        finally:
            p.close()


if __name__ == "__main__":
    unittest.main()
