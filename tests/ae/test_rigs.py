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
            self.assertEqual(bundle.rig_ids(cast), ["ball@1", "ball@2"])
            self.assertEqual(rigs.newer("ball@1"), "ball@2")
            js = json.loads(bundle.cast_js(cast))
            self.assertEqual({c["rig"] for c in js.values()}, {"ball@1"})   # CU.char draws ball@1 characters with ball@1
        self.assertIn("CU.char = function", bundle.RIG_JS)
        self.assertIn("CU.rig = function", bundle.RIG_JS)


if __name__ == "__main__":
    unittest.main()
