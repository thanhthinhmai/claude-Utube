"""The channel's cast library (specs/034 T035): save versions, reuse in a later film, the app-less fallback."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from filmcheck import cast, castlib  # noqa: E402
import castfilm  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"


def sheet(d: Path, cid: str, keys=("front",), tag="") -> None:
    s = cast.sheet_dir(d, cid)
    s.mkdir(parents=True, exist_ok=True)
    rows = []
    for k in keys:
        (s / f"{k}.jpg").write_bytes(b"\xff\xd8" + f"{cid}-{k}{tag}".encode())
        rows.append({"key": k, "group": "turn", "label": k, "file": f"{k}.jpg"})
    (s / "sheet.json").write_text(json.dumps({"character": cid, "rig": "ball@1", "built_at": "x", "frames": rows}))


class Library(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(dir=TMP))
        self.acc = self.tmp / "data" / "accounts" / "u1"
        self.d = castfilm.make(self.acc / "films" / "f1")
        self.env = {**os.environ, "STUDIO_ROOT": str(self.tmp)}
        for k in ("STUDIO_JOB", "STUDIO_PROXY", "STUDIO_MODE"):
            self.env.pop(k, None)

    def studio(self, *args):
        return subprocess.run(["sh", str(REPO / "bin" / "studio"), *args], capture_output=True, text=True, env=self.env,
                              cwd=self.tmp, timeout=120)

    def approve_all(self, d):
        for c in ("hero", "friend", "classmates"):
            sheet(d, c, ("front", "back", "34"))
        return self.studio("cast", "approve", str(d), "--all", "--save")

    def test_root(self):
        self.assertEqual(castlib.root(self.d), self.acc)
        out = castfilm.make(self.tmp / "films" / "f2")
        from unittest import mock
        with mock.patch.dict(os.environ, {"STUDIO_ROOT": str(self.tmp)}):   # not the app that may run for this repo
            self.assertIsNone(castlib.root(out))                    # outside the app, and no app runs for STUDIO_ROOT

    def test_app_approval_saves(self):                                # T055: FR-015, US3/AC1
        from filmcheck import edit
        sheet(self.d, "hero", ("front", "back", "34"))
        r = edit.cast_approve(self.d, {"character": "hero", "by": "owner"})
        self.assertTrue(r["ok"], r)
        self.assertIn("default/hero: v1 (new)", r["saved"][0])
        self.assertTrue((self.acc / "channels" / "default" / "cast" / "hero" / "v1").is_dir())
        doc = cast.load(self.d); doc["save_to_library"] = False; cast.save(self.d, doc)
        sheet(self.d, "friend", ("front", "back", "34"))
        r = edit.cast_approve(self.d, {"character": "friend"})
        self.assertNotIn("saved", r)
        self.assertFalse((self.acc / "channels" / "default" / "cast" / "friend").exists())

    def test_save_versions(self):
        r = self.approve_all(self.d)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("default/hero: v1 (new)", r.stdout)
        cdir = self.acc / "channels" / "default" / "cast"
        idx = json.loads((cdir / "index.json").read_text())
        self.assertEqual(sorted(idx["characters"]), ["classmates", "friend", "hero"])
        ch = json.loads((cdir / "hero" / "v1" / "character.json").read_text())
        self.assertEqual((ch["frames_approved"], ch["films"], ch["rig"]), (["34", "back", "front"], ["f1"], "ball@1"))
        self.assertTrue((cdir / "hero" / "v1" / "sheet" / "front.jpg").is_file())
        doc = cast.load(self.d)
        self.assertEqual(cast.find(doc, "hero")["from_library"], {"channel": "default", "id": "hero", "v": 1})
        self.assertEqual(cast.states(self.d)["hero"], "approved")   # saving keeps the approval
        # the same look from another film: only the film is added
        d2 = castfilm.make(self.acc / "films" / "f2")
        sheet(d2, "hero", ("front",))
        cast.approve(d2, ["hero"])
        self.assertEqual(castlib.save_approved(d2, ["hero"]), ["✓ default/hero: v1 (added film)"])
        self.assertEqual(json.loads((cdir / "hero" / "v1" / "character.json").read_text())["films"], ["f1", "f2"])
        # another look: v2, v1 untouched (FR-017)
        before = (cdir / "hero" / "v1" / "character.json").read_bytes()
        doc = cast.load(d2); cast.find(doc, "hero")["spec"]["hoodie"] = "#112233"; cast.save(d2, doc)
        cast.approve(d2, ["hero"])
        self.assertEqual(castlib.save_approved(d2, ["hero"]), ["✓ default/hero: v2 (new)"])
        self.assertEqual((cdir / "hero" / "v1" / "character.json").read_bytes(), before)
        self.assertEqual(castlib.get(self.acc, "default", "hero")["v"], 2)

    def test_new_pictures_make_a_version_with_old_and_new(self):
        self.approve_all(self.d)
        d2 = castfilm.make(self.acc / "films" / "f2")
        sheet(d2, "hero", ("front", "expr-wide"), tag="new")
        cast.approve(d2, ["hero"])
        self.assertEqual(castlib.save_approved(d2, ["hero"]), ["✓ default/hero: v2 (new)"])
        g = castlib.get(self.acc, "default", "hero")
        self.assertEqual(g["character"]["frames_approved"], ["34", "back", "expr-wide", "front"])
        self.assertEqual((g["dir"] / "sheet" / "front.jpg").read_bytes(), b"\xff\xd8hero-frontnew")

    def test_concurrent_saves(self):
        sheet(self.d, "hero")
        a, b = dict(cast.find(cast.load(self.d), "hero")), dict(cast.find(cast.load(self.d), "hero"))
        b = json.loads(json.dumps(b)); b["spec"]["hoodie"] = "#000000"
        res = []
        ts = [threading.Thread(target=lambda c=c: res.append(castlib.save(self.acc, "default", c, cast.sheet_dir(self.d, "hero"), "f1")))
              for c in (a, b)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(sorted(v for v, _ in res), [1, 2])
        idx = castlib.index(self.acc, "default")
        self.assertEqual([x["v"] for x in idx["characters"]["hero"]["versions"]], [1, 2])

    def test_no_app_still_approves(self):
        out = castfilm.make(self.tmp / "films" / "f9")
        sheet(out, "friend")
        r = self.studio("cast", "approve", str(out), "friend", "--save")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("the app is not running", r.stdout)
        self.assertEqual(cast.states(out)["friend"], "approved")
        self.assertEqual(self.studio("cast", "use", str(out), "default/hero").returncode, 3)
        self.assertEqual(self.studio("cast", "library").returncode, 3)

    def test_use(self):
        self.approve_all(self.d)
        d2 = castfilm.make(self.acc / "films" / "f2", characters=(castfilm.FRIEND, castfilm.HERO))
        r = self.studio("cast", "use", str(d2), "default/friend")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("friend: approved (library v1)", r.stdout)
        self.assertEqual(cast.states(d2)["friend"], "approved")
        self.assertEqual(cast.find(cast.load(d2), "friend")["approved"]["source"], "library")
        self.assertEqual((cast.sheet_dir(d2, "friend") / "front.jpg").read_bytes(),
                         (self.acc / "channels/default/cast/friend/v1/sheet/front.jpg").read_bytes())
        friend = next(c for c in castlib.listing(self.acc)[0]["characters"] if c["id"] == "friend")
        self.assertEqual(friend["films"], ["f1", "f2"])                 # T061: the version lists the films that used it
        # hero needs an expression the library lacks: only that picture is to draw, the rest is kept
        r = self.studio("cast", "use", str(d2), "default/hero@1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("to draw", r.stdout)
        self.assertEqual(cast.states(d2)["hero"], "ready")
        keep, carry = castlib.library_frames(d2)
        self.assertEqual(keep["hero"], ["34", "back", "front"])
        self.assertTrue(carry["hero"].endswith("hero/v1/sheet"))
        self.assertNotIn("friend", castlib.library_frames(d2, ["hero"])[0])
        # a changed look draws everything again
        doc = cast.load(d2); cast.find(doc, "hero")["spec"]["hoodie"] = "#123456"; cast.save(d2, doc)
        self.assertNotIn("hero", castlib.library_frames(d2)[0])
        self.assertEqual(self.studio("cast", "use", str(d2), "default/nobody").returncode, 3)

    def test_library_listing(self):
        self.approve_all(self.d)
        r = self.studio("cast", "use", str(self.d), "default/hero")     # a film in the app → the app's library
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = castlib.listing(self.acc)
        self.assertEqual(rows[0]["channel"], "default")
        hero = next(c for c in rows[0]["characters"] if c["id"] == "hero")
        self.assertEqual((hero["latest"], hero["rig"], hero["films"], hero["new_rig"]), (1, "ball@1", ["f1"], "ball@2"))   # specs/038: ball@2 is the newest rig


if __name__ == "__main__":
    unittest.main()
