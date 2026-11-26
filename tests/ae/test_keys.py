"""specs/035 T012: timing.json in the bundle (CU.shotFrames), keyframed motions per shot (keys_<proj>.json), and
timing.json written from the first whole build of an old film."""
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

from ae import bundle  # noqa: E402
from test_ae import make_film  # noqa: E402


def members(tar_path) -> dict:
    with tarfile.open(tar_path) as t:
        return {m.name: (t.extractfile(m).read() if m.isfile() else None) for m in t.getmembers()}


class Bundle(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.d = make_film(self.tmp / "f1", ("S1", "S2"))

    def test_timing_goes_in_as_data(self):
        b = members(bundle.make(self.d, out=self.tmp / "a.tar")["path"])
        self.assertNotIn("data/timing.json", b)
        self.assertNotIn("CU.DRAFT", b["entry.jsx"].decode())
        t = {"version": 1, "fps": 30, "frames": {"S1": 60, "S2": 45}, "history": []}
        (self.d / "timing.json").write_text(json.dumps(t))
        b = members(bundle.make(self.d, out=self.tmp / "b.tar")["path"])
        self.assertEqual(json.loads(b["data/timing.json"])["frames"], t["frames"])
        b = members(bundle.make(self.d, out=self.tmp / "c.tar", draft=True)["path"])
        self.assertIn("CU.DRAFT = true;", b["entry.jsx"].decode())
        self.assertEqual(json.loads(b["bundle.json"])["kind"], "draft")

    def test_kit_reads_timing_and_scans_keys(self):
        lib = (bundle.KIT / "lib.jsx").read_text()
        for want in ("CU.shotFrames = function", "data/timing.json", "CU.keyScan = function", "numKeys >= 2"):
            self.assertIn(want, lib)
        core = (bundle.KIT / "build_core.jsx").read_text()
        for want in ("CU.keyScan(sc)", "keys_", "M.resolutionFactor = [4, 4]", "CU.draftSettings(it)"):
            self.assertIn(want, core)


class Build(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = {**os.environ, "STUDIO_AE_CONFIG": str(self.tmp / "ae.json"), "STUDIO_AE_WORK": str(self.tmp / "w"),
                    "STUDIO_ROOT": str(self.tmp / "root"), "STUDIO_AE_FAKE": "1"}
        for k in ("STUDIO_JOB", "STUDIO_PROXY"):
            self.env.pop(k, None)
        self.d = make_film(self.tmp / "root" / "films" / "f1", ("S1", "S2", "S3"))

    def ae(self, *args):
        return subprocess.run(["sh", str(ROOT / "bin" / "studio"), "ae", *args], capture_output=True, text=True,
                              env=self.env, timeout=120)

    def test_first_whole_build_writes_timing(self):
        r = self.ae("build", "f1", "--shots", "S1")                     # part of the film: no timing.json
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.d / "timing.json").exists())
        r = self.ae("build", "f1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        t = json.loads((self.d / "timing.json").read_text())
        self.assertEqual(t["frames"], {"S1": 60, "S2": 60, "S3": 60})      # the fake AE's 2 s shots
        self.assertEqual(t["origin"]["frames"], t["frames"])

    def test_local_build_reads_keys_and_honours_timing(self):
        from ae import local
        (self.d / "timing.json").write_text(json.dumps({"version": 1, "fps": 30, "frames": {"S1": 45, "S2": 30, "S3": 90},
                                                         "history": []}))
        os.environ.update(STUDIO_AE_FAKE="1", STUDIO_AE_WORK=str(self.tmp / "w"), STUDIO_AE_CONFIG=str(self.tmp / "ae.json"))
        try:
            r = local.build(self.d, draft=True)
        finally:
            for k in ("STUDIO_AE_FAKE", "STUDIO_AE_WORK", "STUDIO_AE_CONFIG"):
                os.environ.pop(k, None)
        self.assertEqual([round(m[1] - m[0], 3) for m in r["marks"]], [1.5, 1.0, 3.0])
        self.assertEqual(r["keys"]["S2"], [{"layer": "Hero", "prop": "Position", "t0": 0.2, "t1": 0.8}])

    def test_final_render_keeps_the_animatic_lengths(self):
        """T036 FR-017, SC-004: the final render's shot marks match timing.json to one frame."""
        from filmcheck import timing
        t = {"version": 1, "fps": 30, "frames": {"S1": 45, "S2": 30, "S3": 90}, "history": []}
        (self.d / "timing.json").write_text(json.dumps(t))
        from filmcheck import points
        points.set_on(self.d, ["script", "voice", "cast"])                    # the animatic point off: render may run
        r = self.ae("render", "f1")
        self.assertIn(r.returncode, (0, 1), r.stdout + r.stderr)
        marks = json.loads((self.d / "out" / "render-shots.json").read_text())["shots"]
        want = timing.bounds(t)
        self.assertEqual([m[3] for m in marks], [b["id"] for b in want])
        for m, b in zip(marks, want):
            self.assertLessEqual(abs(m[0] - b["t0"]), 1 / 30 + 1e-6, m)
            self.assertLessEqual(abs(m[1] - b["t1"]), 1 / 30 + 1e-6, m)


if __name__ == "__main__":
    unittest.main()
