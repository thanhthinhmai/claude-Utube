"""specs/038 T009: one queue per engine (After Effects, Blender) with the same rules as specs/032."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from ae import aequeue, enginequeue  # noqa: E402


class Clock:
    def __init__(self):
        self.t = 1_800_000_000.0

    def __call__(self):
        return self.t


class EngineQueue(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.get("STUDIO_DATA")
        os.environ["STUDIO_DATA"] = tempfile.mkdtemp()
        self.clock = Clock()
        self.bq = enginequeue.Queue("blender", clock=self.clock)
        self.aq = enginequeue.Queue("ae", clock=self.clock)

    def tearDown(self):
        if self.old is None:
            os.environ.pop("STUDIO_DATA", None)
        else:
            os.environ["STUDIO_DATA"] = self.old

    def test_separate_folders_and_ids(self):
        b = self.bq.create("o", "j", "film30", ["S3"], b"tar", kind="render")
        a = self.aq.create("o", "j", "film30", ["S1"], b"tar")
        self.assertTrue(b["id"].startswith("blender-") and a["id"].startswith("ae-"))
        self.assertEqual(b["kind"], "render")
        self.assertTrue((Path(os.environ["STUDIO_DATA"]) / "blender" / "requests" / b["id"]).is_dir())
        # one run at a time per engine, but the two engines do not block each other
        self.assertEqual(self.bq.next_request()["id"], b["id"])
        self.assertEqual(self.aq.next_request()["id"], a["id"])
        self.bq.create("o", "j", "film30", ["S4"], b"tar")
        self.assertIsNone(self.bq.next_request())

    def test_blender_rejects_master_and_ae_names(self):
        with self.assertRaises(enginequeue.QueueError):
            self.bq.create("o", "j", "film30", ["MASTER"], b"")
        r = self.bq.create("o", "j", "film30", ["S3"], b"")
        self.bq.next_request()
        with self.assertRaises(enginequeue.QueueError):
            self.bq.result_part(r["id"], "LS3-hero-34")
        self.assertEqual(self.bq.put_result(r["id"], "S3", [b"x" * 10]), 10)
        self.assertEqual(self.bq.get(r["id"])["results"]["S3"], "out/S3.tar")

    def test_ae_layer_results_are_tars(self):
        r = self.aq.create("o", "j", "film30", ["S3"], b"", kind="layers")
        self.aq.next_request()
        self.aq.put_result(r["id"], "LS3-hero-34", [b"t"])
        self.aq.put_result(r["id"], "S3", [b"m"])
        res = self.aq.get(r["id"])["results"]
        self.assertEqual(res, {"LS3-hero-34": "out/LS3-hero-34.tar", "S3": "out/S3.mp4"})
        with self.assertRaises(enginequeue.QueueError):
            self.aq.result_part(r["id"], "LS3-hero-side")

    def test_heartbeat_and_hello(self):
        r = self.bq.create("o", "j", "film30", ["S3"], b"")
        self.bq.next_request()
        self.clock.t += 61
        got = self.bq.get(r["id"])
        self.assertEqual((got["state"], got["error"]["code"]), ("failed", "bridge_lost"))
        self.assertEqual(self.bq.bridge_status()["code"], "blender_unavailable")
        self.bq.hello({"found": False, "os": "win32"})
        self.assertEqual(self.bq.bridge_status()["code"], "no_blender")
        self.bq.hello({"found": True, "os": "win32", "blender": "C:/b/blender.exe", "gpu": "Intel UHD 730", "version": "0.1"})
        st = self.bq.bridge_status()
        self.assertTrue(st["ready"])
        self.assertEqual((st["blender"], st["gpu"]), ("C:/b/blender.exe", "Intel UHD 730"))
        self.clock.t += 31
        self.assertFalse(self.bq.bridge_status()["ready"])

    def test_size_limit(self):
        q = enginequeue.Queue("blender", clock=self.clock)
        q.MAX_RESULT = 5
        r = q.create("o", "j", "film30", ["S3"], b"")
        q.next_request()
        with self.assertRaises(enginequeue.QueueError) as c:
            q.put_result(r["id"], "S3", [b"123456"])
        self.assertEqual(c.exception.status, 413)

    def test_aequeue_keeps_its_api(self):
        r = aequeue.create("o", "j", "film30", ["S1", "MASTER"], b"")
        self.assertTrue(aequeue.ID.fullmatch(r["id"]))
        real = aequeue.now
        try:
            aequeue.next_request()
            aequeue.now = lambda: real() + 61
            self.assertEqual(aequeue.get(r["id"])["error"]["code"], "bridge_lost")
        finally:
            aequeue.now = real
        self.assertEqual(aequeue.bridge_status()["code"], "ae_unavailable")


if __name__ == "__main__":
    unittest.main()
