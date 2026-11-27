"""specs/038 T017: ae build / fix / status of a film mixing After Effects and Blender shots (fake AE, fake Blender)."""
import hashlib
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
sys.path.insert(0, str(ROOT / "tests" / "ae"))

from ae import bundle  # noqa: E402
from test_ae import frames, make_film, psnr, testsrc  # noqa: E402

LENGTHS = {"S1": 60, "S2": 45, "S3": 60, "S4": 30}


def md5_frames(video, start: int, count: int) -> list:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"select=between(n\\,{start}\\,{start + count - 1})",
                        "-vsync", "0", "-f", "framemd5", "-"], capture_output=True, text=True, check=True)
    return [x.split(",")[-1].strip() for x in r.stdout.splitlines() if x and not x.startswith("#")]


class Mixed(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = {**os.environ, "STUDIO_AE_CONFIG": str(self.tmp / "ae.json"), "STUDIO_AE_WORK": str(self.tmp / "aework"),
                    "STUDIO_ROOT": str(self.tmp / "root"), "STUDIO_AE_FAKE": "1", "STUDIO_BLENDER_FAKE": "1",
                    "STUDIO_BLENDER_WORK": str(self.tmp / "bwork"), "STUDIO_BLENDER_CONFIG": str(self.tmp / "blender.json")}
        for k in ("STUDIO_JOB", "STUDIO_PROXY", "FAKE_BLENDER_MODE", "FAKE_BLENDER_STOP"):
            self.env.pop(k, None)
        self.d = self.tmp / "root" / "films" / "f1"
        make_film(self.d, list(LENGTHS), files={"shots_a.jsx": 'CU.shot1 = function () { return CU.person(1); };\n'
                                                               'CU.shot3 = function () { return CU.person(2); };\n'})
        doc = json.loads((self.d / "film.json").read_text())
        doc["size"] = [320, 180]
        doc["shot_plan"] = {"S2": {"engine": "blender", "set": "hallway", "size": "wide"},
                            "S4": {"engine": "blender", "set": "auditorium", "transition": "dip"}}
        (self.d / "film.json").write_text(json.dumps(doc))
        (self.d / "timing.json").write_text(json.dumps({"version": 1, "fps": 30, "frames": LENGTHS}))
        (self.d / "blender").mkdir()
        for s in ("S2", "S4"):
            (self.d / "blender" / f"{s}.py").write_text('def shot(k):\n    k.set("hallway")\n    k.cam(size="wide")\n')

    def ae(self, *args, extra=None):
        return subprocess.run(["sh", str(ROOT / "bin" / "studio"), "ae", *args], capture_output=True, text=True,
                              env={**self.env, **(extra or {})}, timeout=300)

    def blender_runs(self):
        return sorted(p.name for p in (self.tmp / "bwork" / "f1").iterdir()) if (self.tmp / "bwork" / "f1").exists() else []

    def test_build_mixed_film(self):
        r = self.ae("build", "f1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("estimate: blender 75 frames", r.stdout)
        out = self.d / "out" / "build.mp4"
        self.assertEqual(frames(out), sum(LENGTHS.values()))
        marks = json.loads((self.d / "out" / "build-shots.json").read_text())
        self.assertEqual(marks["source"], "mixed")
        self.assertEqual([m[3] for m in marks["shots"]], list(LENGTHS))
        self.assertEqual(marks["shots"][1][:2], [2.0, 3.5])
        self.assertEqual(marks["engines"]["S2"]["engine"], "blender")
        self.assertTrue(marks["engines"]["S2"]["version"])
        self.assertIn("Fake GPU", marks["engines"]["S2"]["gpu"])
        self.assertEqual(marks["engines"]["S1"]["engine"], "ae")
        # built again with nothing changed: Blender shots are kept, not drawn again
        r = self.ae("build", "f1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("S2, S4 unchanged, kept", r.stdout)
        self.assertIn("estimate: ae 2 shot(s)", r.stdout)

    def test_status_marks_changed_shots(self):
        self.assertEqual(self.ae("build", "f1").returncode, 0)
        (self.d / "blender" / "S4.py").write_text('def shot(k):\n    k.set("auditorium")\n    k.cam(size="huge")\n')
        r = self.ae("status", "f1")
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = {x.split("\t")[0]: x.split("\t")[1:] for x in r.stdout.splitlines() if x.startswith("S")}
        self.assertEqual(rows["S1"], ["ae"])
        self.assertEqual(rows["S2"][:2], ["blender", "built"])
        self.assertEqual(rows["S4"][:2], ["blender", "Must run again"])

    def test_fix_one_blender_shot_keeps_other_frames(self):
        testsrc(self.d / "f1.mp4", 6.5, size="320x180")
        rows, t = [], 0
        for s, n in LENGTHS.items():
            rows.append([t / 30, (t + n) / 30, "", s])
            t += n
        (self.d / "shots.json").write_text(json.dumps({"version": 1, "video": "f1.mp4", "duration": 6.5, "fps": 30,
                                                       "shots": rows}))
        before = self.tmp / "before.mp4"
        before.write_bytes((self.d / "f1.mp4").read_bytes())
        r = self.ae("fix", "f1", "S4")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.blender_runs().__len__(), 1)
        req = json.loads(next((self.tmp / "bwork" / "f1").glob("*/request.json")).read_text())
        self.assertEqual([s["id"] for s in req["shots"]], ["S4"])           # only S4 went to Blender
        self.assertNotIn("AE request", r.stdout)
        self.assertEqual(frames(self.d / "f1.mp4"), 195)
        self.assertGreater(psnr(before, self.d / "f1.mp4", 0, 5.4), 40)     # S1–S3 untouched
        fx = json.loads((self.d / "out" / "fix-shots.json").read_text())
        self.assertEqual(fx["engines"]["S4"]["engine"], "blender")

    def test_old_film_identical(self):
        """SC-009: a film without shot_plan makes the same bundle as in 032."""
        old = self.tmp / "old"
        make_film(old, ["S1", "S2"])
        a = bundle.make(old, None, self.tmp / "a.tar")
        doc = json.loads((old / "film.json").read_text())
        self.assertNotIn("shot_plan", doc)
        b = bundle.make(old, None, self.tmp / "b.tar")
        def members(p):
            with tarfile.open(p) as t:
                return [(m.name, m.size, t.extractfile(m).read() if m.isfile() else b"") for m in t.getmembers()]
        self.assertEqual([m[:2] for m in members(a["path"])], [m[:2] for m in members(b["path"])])
        self.assertFalse([m[0] for m in members(a["path"]) if b"shot_plan" in m[2]])
        self.assertEqual(hashlib.sha1(Path(a["path"]).read_bytes()).hexdigest(),
                         hashlib.sha1(Path(b["path"]).read_bytes()).hexdigest())
        from ae import mixed
        calls = []
        orig = mixed.ae_runner
        mixed.ae_runner = lambda: (lambda code, shots, progress=None, **kw: calls.append((shots, kw)) or {"marks": []})
        try:
            mixed.build(old, None)
        finally:
            mixed.ae_runner = orig
        self.assertEqual(calls, [(None, {})])                # went to the AE runner exactly as before


if __name__ == "__main__":
    unittest.main()
