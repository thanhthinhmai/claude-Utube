"""Rig versions (specs/034 T043): the repo's lock, a newer version beside an approved one, the bundle carries both."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ae import bundle, rigs  # noqa: E402
import castfilm  # noqa: E402


class RigVersions(unittest.TestCase):
    def test_repo_lock_matches_every_locked_folder(self):
        for rid in rigs.versions():
            self.assertEqual(rigs.digest(rid), rigs.load()[rid], rid)
            self.assertTrue((rigs.folder(rid) / "catalog.json").is_file(), rid)

    def test_a_copy_of_v1_changed_is_reported(self):
        tmp = Path(tempfile.mkdtemp())
        import shutil
        shutil.copytree(rigs.folder("ball@1"), tmp / "ball" / "v1")
        lock = tmp / "rigs.lock"
        lock.write_text(json.dumps({"ball@1": rigs.load()["ball@1"]}))
        self.assertEqual(rigs.check(lock, tmp), [])
        f = tmp / "ball" / "v1" / "catalog.json"
        f.write_text(f.read_text() + " ")
        self.assertEqual(rigs.check(lock, tmp), ["ball@1"])

    def test_bundle_carries_the_approved_and_the_newest_version(self):
        locked = {**rigs.load(), "ball@2": "0" * 64}
        with mock.patch.object(rigs, "load", lambda lock=None: locked):
            d = castfilm.make(Path(tempfile.mkdtemp()) / "f1")
            cast = bundle.load_cast(d) if hasattr(bundle, "load_cast") else json.loads((d / "cast" / "cast.json").read_text())
            top = rigs.latest("ball")                                    # ball@2, or ball@3 once that is locked
            self.assertEqual(bundle.rig_ids(cast), ["ball@1", top])
            self.assertEqual(rigs.newer("ball@1"), top)
            js = json.loads(bundle.cast_js(cast))
            self.assertEqual({c["rig"] for c in js.values()}, {"ball@1"})   # CU.char draws ball@1 characters with ball@1
        self.assertIn("CU.char = function", bundle.RIG_JS)
        self.assertIn("CU.rig = function", bundle.RIG_JS)


class Ball3(unittest.TestCase):
    """specs/040 T005: ball@3 keeps everything ball@2 offers, adds ages, and its jsx parses."""
    def cat(self, rid):
        return json.loads((ROOT / "tools/ae/kit/rigs" / rid.replace("@", "/v") / "catalog.json").read_text())

    def test_catalog_covers_ball2(self):
        c2, c3 = self.cat("ball@2"), self.cat("ball@3")
        self.assertEqual(c3["rig"], "ball@3")
        for key in ("views", "expressions", "poses"):
            self.assertTrue(set(c2[key]) <= set(c3[key]), key)
        self.assertEqual(c3["ages"], ["kid", "adult", "toddler"])
        self.assertIn("age", c3["spec"])

    def test_jsx_loads_and_offers_the_rig_interface(self):
        import shutil
        import subprocess
        if not shutil.which("node"):
            self.skipTest("no node")
        tmp = Path(tempfile.mkdtemp()) / "ball3.js"
        tmp.write_text((ROOT / "tools/ae/kit/rigs/ball/v3/ball.jsx").read_text())
        out = subprocess.run(["node", "-e", "global.CU={};require(process.argv[1]);console.log('ok')", str(tmp)],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        src = tmp.read_text()
        for name in ("make", "pose", "place", "carry", "sizeOf", "expression", "view"):
            self.assertIn(name + ":", src.replace(" :", ":"), name)

    def test_bundle_carries_ball3_when_the_cast_uses_it(self):
        locked = {**rigs.load(), "ball@3": "0" * 64}
        with mock.patch.object(rigs, "load", lambda lock=None: locked):
            cast = {"characters": [{"id": "hero", "rig": "ball@3", "spec": {"age": "kid"}}]}
            self.assertIn("ball@3", bundle.rig_ids(cast))


if __name__ == "__main__":
    unittest.main()
