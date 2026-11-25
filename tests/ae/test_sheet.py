"""Cast sheet and rig versions (specs/034 T012, T028, T043) with the fake AE (desktop/test/fake-ae.mjs)."""
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ae import bundle, rigs, sheet  # noqa: E402
import castfilm  # noqa: E402


def size(p: Path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    w, h = r.stdout.strip().split(",")[:2]
    return int(w), int(h)


class Plan(unittest.TestCase):
    def setUp(self):
        self.d = castfilm.make(Path(tempfile.mkdtemp()) / "f1")

    def test_frames(self):
        p = sheet.plan(self.d)
        keys = {c: [f["key"] for f in fl] for c, fl in p["all"].items()}
        self.assertEqual(keys["hero"], ["front", "back", "34", "expr-wide", "pose-guitar", "pose-zzz", "walk"])
        self.assertEqual(keys["friend"], ["front", "back", "34"])
        self.assertEqual(keys["classmates"], ["group"])
        zzz = [f for f in p["all"]["hero"] if f["key"] == "pose-zzz"][0]
        self.assertIn("not in the ball@1 catalog", zzz["missing_reason"])
        self.assertNotIn("pose-zzz", [f["key"] for f in p["frames"]])
        self.assertEqual([f for f in p["frames"] if f["key"] == "walk"][0]["len"], 75)

    def test_only_and_keep(self):
        p = sheet.plan(self.d, only=["friend"], keep={"friend": ["back"]})
        self.assertEqual(p["characters"], ["friend"])
        self.assertEqual([f["key"] for f in p["frames"]], ["front", "34"])
        with self.assertRaises(sheet.SheetError) as c:
            sheet.plan(self.d, only=["nobody"])
        self.assertEqual(c.exception.code, "no_character")

    def test_chunks_never_split_a_character(self):
        p = {"characters": ["a", "b"], "frames": [{"character": "a"}] * 60 + [{"character": "b"}] * 60}
        parts = sheet.chunks(p)
        self.assertEqual([len(x) for x in parts], [60, 60])

    def test_bundle_in_sheet_mode(self):
        p = sheet.plan(self.d)
        out = Path(tempfile.mkdtemp())
        r = bundle.make(self.d, None, out / "b.tar", "p", sheet={"fps": 30, "cast": p["cast"], "frames": p["frames"]})
        with tarfile.open(r["path"]) as t:
            names = t.getnames()
            entry = t.extractfile("entry.jsx").read().decode()
            meta = json.loads(t.extractfile("bundle.json").read())
        self.assertIn("castsheet.jsx", " ".join(names))
        self.assertIn("data/cast_sheet.json", names)
        self.assertNotIn("shots.jsx", " ".join(names))           # the film's own shots are not drawn
        self.assertEqual(meta["shots"], [f"S{i}" for i in range(1, len(p["frames"]) + 1)])
        self.assertIn('#include "kit/rigs/ball/v1/ball.jsx"', entry)
        self.assertIn("kit/rigs/ball/v1/ball.jsx", names)
        self.assertIn("CU.char", entry)


class Rigs(unittest.TestCase):
    def test_lock_is_clean(self):
        self.assertEqual(rigs.check(), [])
        self.assertIn("ball@1", rigs.versions("ball"))

    def test_lock_refuses_a_locked_id_and_detects_changes(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "ball" / "v1").mkdir(parents=True)
        (tmp / "ball" / "v1" / "ball.jsx").write_text("// v1\n")
        lock = tmp / "rigs.lock"
        rigs.lock("ball@1", lock, tmp)
        with self.assertRaises(ValueError):
            rigs.lock("ball@1", lock, tmp)
        self.assertEqual(rigs.check(lock, tmp), [])
        (tmp / "ball" / "v1" / "ball.jsx").write_text("// changed\n")
        self.assertEqual(rigs.check(lock, tmp), ["ball@1"])
        (tmp / "ball" / "v2").mkdir()
        (tmp / "ball" / "v2" / "ball.jsx").write_text("// v2\n")
        rigs.lock("ball@2", lock, tmp)
        self.assertEqual(rigs.latest("ball", lock), "ball@2")
        self.assertEqual(rigs.newer("ball@1", lock), "ball@2")
        self.assertIsNone(rigs.newer("ball@2", lock))


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = {**os.environ, "STUDIO_AE_CONFIG": str(self.tmp / "ae.json"), "STUDIO_AE_WORK": str(self.tmp / "work"),
                    "STUDIO_ROOT": str(self.tmp / "root"), "STUDIO_AE_FAKE": "1"}
        for k in ("STUDIO_JOB", "STUDIO_PROXY"):
            self.env.pop(k, None)
        self.d = castfilm.make(self.tmp / "root" / "films" / "f1")

    def ae(self, *args):
        return subprocess.run(["sh", str(ROOT / "bin" / "studio"), "ae", *args], capture_output=True, text=True,
                              env=self.env, timeout=300)

    def test_sheet(self):
        r = self.ae("sheet", "f1")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        sh = self.d / "cast" / "sheets"
        hero = json.loads((sh / "hero" / "sheet.json").read_text())
        self.assertEqual(hero["rig"], "ball@1")
        rows = {f["key"]: f for f in hero["frames"]}
        self.assertEqual(rows["front"]["file"], "front.jpg")
        self.assertEqual(rows["expr-wide"]["para"], "P01")
        self.assertIsNone(rows["pose-zzz"]["file"])
        self.assertIn("catalog", rows["pose-zzz"]["missing_reason"])
        self.assertEqual(rows["walk"]["file"], "walk.mp4")
        for f in (sh / "hero").glob("*.jpg"):
            self.assertLessEqual(f.stat().st_size, 300 * 1024)
            self.assertEqual(max(size(f)), 720)
        self.assertLessEqual(max(size(sh / "hero" / "walk.mp4")), 400)
        self.assertTrue((sh / "classmates" / "group.jpg").is_file())
        self.assertTrue((self.d / "cast" / "catalog.json").is_file())
        self.assertIn("pose-zzz", r.stdout)
        self.assertFalse((self.d / "cast" / ".stage").exists())

        # --only redraws one character; the others stay byte-identical; one .prev only
        before = {p: p.read_bytes() for p in (sh / "hero").iterdir()}
        r = self.ae("sheet", "f1", "--only", "friend")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual({p: p.read_bytes() for p in (sh / "hero").iterdir()}, before)
        self.assertTrue((sh / "friend.prev" / "sheet.json").is_file())
        self.assertFalse((sh / "hero.prev").exists())
        r = self.ae("sheet", "f1", "--only", "friend")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(p.name for p in sh.iterdir() if p.name.startswith("friend")), ["friend", "friend.prev"])

    def test_no_cast(self):
        (self.d / "cast" / "cast.json").unlink()
        r = self.ae("sheet", "f1")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no_cast", r.stderr)

    def test_rigs(self):
        r = self.ae("rigs", "--check")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ball@1  ok", r.stdout)


if __name__ == "__main__":
    unittest.main()
