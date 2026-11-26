"""specs/038 T014: tools/blender/local.py with the fake Blender (desktop/test/fake-blender.mjs)."""
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from blender import config, local  # noqa: E402
from blender.config import BlenderError  # noqa: E402

ENV = ("STUDIO_BLENDER_FAKE", "STUDIO_BLENDER_WORK", "FAKE_BLENDER_MODE", "FAKE_BLENDER_STOP",
       "STUDIO_BLENDER_SHOT_TIMEOUT", "STUDIO_BLENDER_START_TIMEOUT", "STUDIO_BLENDER_CONFIG")


def frames_of(mp4: str) -> int:
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_frames", "-of", "csv=p=0", mp4], capture_output=True, text=True)
    return int(r.stdout.strip())


class LocalRun(unittest.TestCase):
    def setUp(self):
        self.old = {k: os.environ.get(k) for k in ENV}
        for k in ENV:
            os.environ.pop(k, None)
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["STUDIO_BLENDER_FAKE"] = "1"
        os.environ["STUDIO_BLENDER_WORK"] = str(self.tmp / "work")
        os.environ["STUDIO_BLENDER_CONFIG"] = str(self.tmp / "blender.json")
        self.film = self.tmp / "film30"
        (self.film / "blender").mkdir(parents=True)
        (self.film / "blender" / "S2.py").write_text('def shot(k):\n    k.set("hallway")\n    k.cam(size="wide")\n')

    def tearDown(self):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def build(self, **kw):
        return local.build(self.film, [{"id": "S2", "frames": 12}], 24, (320, 180), **kw)

    def test_mp4_has_every_frame(self):
        out = self.build()
        mp4 = out["shots"]["S2"]
        self.assertTrue(mp4.endswith("out/blender/S2.mp4"))
        self.assertEqual(frames_of(mp4), 12)
        self.assertIn("Fake GPU", out["gpu"])
        req = json.loads((Path(out["run"]) / "request.json").read_text())
        self.assertEqual(req["shots"][0]["script"], "blender/S2.py")
        self.assertTrue((Path(out["run"]) / "kit" / "entry.py").exists())
        self.assertTrue((Path(out["run"]) / "blender" / "S2.py").exists())

    def test_resume_after_a_stop(self):
        os.environ["FAKE_BLENDER_STOP"] = "5"
        with self.assertRaises(BlenderError) as e:
            self.build()
        self.assertEqual(e.exception.code, "stopped")
        runs = list((self.tmp / "work" / "film30").iterdir())
        self.assertEqual(len(runs), 1)
        self.assertEqual(len(list((runs[0] / "S2").glob("f*.png"))), 5)
        del os.environ["FAKE_BLENDER_STOP"]
        out = self.build()
        self.assertEqual(Path(out["run"]), runs[0])                 # same inputs → same folder → goes on
        self.assertIn("frame S2 12/12", out["log"])
        self.assertNotIn("frame S2 5/12", out["log"])               # the first 5 frames were not drawn again
        self.assertEqual(frames_of(out["shots"]["S2"]), 12)

    def test_changed_script_gets_a_new_run(self):
        a = self.build()["run"]
        (self.film / "blender" / "S2.py").write_text('def shot(k):\n    k.set("classroom")\n    k.cam(size="wide")\n')
        self.assertNotEqual(self.build()["run"], a)

    def test_software_gpu_stops_with_exit_3_and_no_frames(self):
        os.environ["FAKE_BLENDER_MODE"] = "gpu_software"
        with self.assertRaises(BlenderError) as e:
            self.build()
        self.assertEqual(e.exception.code, "gpu_software")
        self.assertEqual(e.exception.exit_code(), 3)
        self.assertFalse(list((self.tmp / "work").rglob("f*.png")))
        self.assertFalse((self.film / "out" / "blender" / "S2.mp4").exists())

    def test_hang_times_out(self):
        os.environ["FAKE_BLENDER_MODE"] = "hang"
        os.environ["STUDIO_BLENDER_START_TIMEOUT"] = "1"
        with self.assertRaises(BlenderError) as e:
            self.build()
        self.assertEqual(e.exception.code, "timeout")

    def test_script_error_reports_its_code(self):
        os.environ["FAKE_BLENDER_MODE"] = "err"
        with self.assertRaises(BlenderError) as e:
            self.build()
        self.assertEqual(e.exception.code, "script")
        self.assertIn("NameError", e.exception.message)
        self.assertEqual(e.exception.exit_code(), 1)

    def test_missing_script_is_bad_plan(self):
        with self.assertRaises(BlenderError) as e:
            local.build(self.film, [{"id": "S9", "frames": 4}], 24, (320, 180))
        self.assertEqual(e.exception.code, "bad_plan")

    def test_quarter_size(self):
        out = self.build(quarter=True)
        self.assertTrue(out["shots"]["S2"].endswith("S2-quarter.mp4"))
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width", "-of", "csv=p=0",
                            out["shots"]["S2"]], capture_output=True, text=True)
        self.assertEqual(int(r.stdout.strip()), 80)

    def test_progress_counts_frames(self):
        seen = []
        self.build(progress=seen.append)
        self.assertTrue(seen)
        self.assertEqual(seen[-1]["frames"], 12)


class NoBlender(unittest.TestCase):
    def test_missing_exe_is_exit_3(self):
        s = {"kind": "windows", "argv": ["/nope/blender.exe"], "exe": "/nope/blender.exe", "work": "/tmp"}
        with self.assertRaises(BlenderError) as e:
            config.check(s)
        self.assertEqual(e.exception.exit_code(), 3)

    def test_software_names(self):
        for n in ("llvmpipe (LLVM 15)", "Microsoft Basic Render Driver", "SwiftShader", "softpipe"):
            self.assertTrue(config.SOFTWARE.search(n), n)
        self.assertFalse(config.SOFTWARE.search("Intel(R) UHD Graphics 730"))


class ShotScripts(unittest.TestCase):
    """kit/entry.py rules that run without Blender (bpy stubbed)."""

    @classmethod
    def setUpClass(cls):
        sys.modules.setdefault("bpy", types.ModuleType("bpy"))
        sys.path.insert(0, str(ROOT / "tools" / "blender"))
        from kit import entry
        cls.entry = entry

    def write(self, src):
        p = Path(tempfile.mkdtemp()) / "S1.py"
        p.write_text(src)
        return str(p)

    def test_imports_are_refused(self):
        with self.assertRaises(self.entry.KitError) as e:
            self.entry.load_shot(self.write("import bpy\ndef shot(k):\n    pass\n"))
        self.assertIn("line 1", str(e.exception))

    def test_needs_shot_function(self):
        with self.assertRaises(self.entry.KitError):
            self.entry.load_shot(self.write("x = 1\n"))

    def test_unknown_kit_call_is_a_script_error(self):
        k = self.entry.K("/tmp", {"fps": 24}, {"id": "S1", "frames": 48})
        with self.assertRaises(self.entry.KitError) as e:
            k.set("moonbase")
        self.assertIn("sets/moonbase.py", str(e.exception))
        with self.assertRaises(self.entry.KitError):
            k.set("../x")
        self.assertEqual(k.f(1.0), 25)
        self.assertEqual(k.f(99), 48)


if __name__ == "__main__":
    unittest.main()
