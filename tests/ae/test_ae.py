"""specs/032: film.json, jsx bundle, frame-exact splice, ae uses (T006, T010)."""
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from ae import bundle, film, splice, uses  # noqa: E402

FFMPEG = ["ffmpeg", "-v", "error", "-y"]


def make_film(d: Path, shots=("S1", "S2"), files=None) -> Path:
    (d / "ae").mkdir(parents=True, exist_ok=True)
    files = files or {"shots_a.jsx": 'CU.shot1 = function () { return CU.person(1); };\n'
                                     'CU.shot2 = function () { return CU.helper(); };\n'
                                     'CU.helper = function () { return CU.monitorQ(1); };\n'}
    for k, v in files.items():
        (d / "ae" / k).write_text(v)
    (d / "film.json").write_text(json.dumps({"engine": "ae", "fps": 30, "shots": list(shots), "ae_files": sorted(files)}))
    return d


def testsrc(out: Path, seconds: float, pattern="testsrc", size="320x180", audio=True):
    cmd = FFMPEG + ["-f", "lavfi", "-i", f"{pattern}=size={size}:rate=30:duration={seconds}"]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-c:a", "aac", "-shortest"]
    subprocess.run(cmd + ["-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(out)], check=True)


def frames(video) -> int:
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_frames", "-of", "csv=p=0", str(video)], capture_output=True, text=True, check=True)
    return int(r.stdout.strip())


def psnr(a, b, start: float, dur: float) -> float:
    r = subprocess.run(["ffmpeg", "-v", "info", "-ss", str(start), "-t", str(dur), "-i", str(a), "-ss", str(start), "-t", str(dur),
                        "-i", str(b), "-lavfi", "psnr", "-f", "null", "-"], capture_output=True, text=True)
    line = [x for x in r.stderr.splitlines() if "PSNR" in x][-1]
    v = line.split("average:")[1].split()[0]
    return 99.0 if v == "inf" else float(v)


class FilmJson(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_no_film_json_is_a_page_film(self):
        self.assertEqual(film.load(self.tmp)["engine"], "page")
        with self.assertRaises(film.FilmError) as c:
            film.require_ae(self.tmp)
        self.assertEqual(c.exception.code, "not_ae")
        self.assertIn("web page engine", c.exception.message)

    def test_bad_values(self):
        d = make_film(self.tmp / "f")
        for bad in ({"engine": "blender"}, {"engine": "ae", "fps": 0}, {"engine": "ae", "shots": ["13"]},
                    {"engine": "ae", "ae_files": ["../x.jsx"]}, {"engine": "ae", "ae_files": ["gone.jsx"]}):
            (d / "film.json").write_text(json.dumps(bad))
            with self.assertRaises(film.FilmError, msg=bad):
                film.load(d)
        (d / "film.json").write_text("{nope")
        with self.assertRaises(film.FilmError):
            film.load(d)

    def test_pick_shots(self):
        doc = film.load(make_film(self.tmp / "f", ("S1", "S2", "S3")))
        self.assertEqual(film.pick_shots(doc, None), ["S1", "S2", "S3"])
        self.assertEqual(film.pick_shots(doc, ["3", "S1"]), ["S1", "S3"])
        with self.assertRaises(film.FilmError):
            film.pick_shots(doc, ["S9"])


class Bundle(unittest.TestCase):
    def test_bundle_holds_kit_film_and_entry(self):
        tmp = Path(tempfile.mkdtemp())
        d = make_film(tmp / "f")
        (d / "ae" / "data" / "motion").mkdir(parents=True)
        (d / "ae" / "data" / "motion" / "S1.json").write_text("[]")
        (d / "ae" / "notes.txt").write_text("not jsx")
        r = bundle.make(d, ["S2"], tmp / "b.tar")
        with tarfile.open(r["path"]) as t:
            names = t.getnames()
            entry = t.extractfile("entry.jsx").read().decode()
        for f in bundle.KIT_FILES:
            self.assertIn(f"kit/{f}", names)
        self.assertIn("ae/shots_a.jsx", names)
        self.assertIn("data/motion/S1.json", names)
        self.assertNotIn("ae/notes.txt", names)
        self.assertIn('CU.build(["2"]);', entry)
        self.assertIn('#include "ae/shots_a.jsx"', entry)
        self.assertLess(entry.index("kit/build_core.jsx"), entry.index("ae/shots_a.jsx"))
        self.assertIn("CU.WORK = (new File($.fileName))", entry)
        out = bundle.extract(r["path"], tmp / "work dir thư mục")
        self.assertTrue((out / "data" / "heads").is_dir())
        self.assertEqual(json.loads((out / "bundle.json").read_text())["shots"], ["S2"])

    def test_kit_has_no_fixed_paths(self):
        for f in bundle.KIT_FILES:
            t = (bundle.KIT / f).read_text()
            self.assertNotIn("E:/", t, f)
            self.assertNotIn("crayon10", t, f)

    def test_unsafe_bundle_refused(self):
        tmp = Path(tempfile.mkdtemp())
        with tarfile.open(tmp / "bad.tar", "w") as t:
            p = tmp / "x"; p.write_text("x")
            t.add(p, arcname="../escape.jsx")
        with self.assertRaises(film.FilmError):
            bundle.extract(tmp / "bad.tar", tmp / "out")


class Splice(unittest.TestCase):
    def test_two_shots_frame_exact(self):
        tmp = Path(tempfile.mkdtemp())
        old, new = tmp / "old.mp4", tmp / "master.mp4"
        testsrc(old, 6)                                         # 180 frames, shots of 1 s
        testsrc(new, 2, pattern="smptebars", size="640x360", audio=False)   # two rebuilt shots back to back
        marks = [[i, i + 1, "", f"S{i + 1}"] for i in range(6)]
        pieces = splice.pieces_from_master(new, [[0, 1, "", "S2"], [1, 2, "", "S5"]], ["S2", "S5"])
        r = splice.splice(old, marks, pieces, tmp / "fix.mp4")
        self.assertEqual(r["replaced"], ["S2", "S5"])
        self.assertEqual(frames(tmp / "fix.mp4"), 180)
        self.assertTrue(splice.has_audio(tmp / "fix.mp4"))
        for start, dur in ((0, 1), (2, 2), (5, 1)):
            self.assertGreater(psnr(old, tmp / "fix.mp4", start, dur), 40, (start, dur))
        self.assertLess(psnr(old, tmp / "fix.mp4", 1, 1), 20)

    def test_short_shot_is_padded_not_shifting(self):
        tmp = Path(tempfile.mkdtemp())
        old, new = tmp / "old.mp4", tmp / "new.mp4"
        testsrc(old, 3)
        testsrc(new, 0.5, pattern="smptebars", audio=False)
        r = splice.splice(old, [[0, 1, "", "S1"], [1, 2, "", "S2"], [2, 3, "", "S3"]], {"S2": (str(new), 0)}, tmp / "o.mp4")
        self.assertEqual(frames(r["out"]), 90)
        self.assertGreater(psnr(old, r["out"], 2, 1), 40)

    def test_unknown_shot(self):
        with self.assertRaises(splice.SpliceError):
            splice.plan([[0, 1, "", "S1"]], {"S9": ("x", 0)}, 30, 30)


class Uses(unittest.TestCase):
    def test_direct_and_indirect_calls(self):
        d = make_film(Path(tempfile.mkdtemp()) / "f")
        self.assertEqual(uses.shots_using(d, ["person"]), ["S1"])
        self.assertEqual(uses.shots_using(d, ["CU.monitorQ"]), ["S2"])    # through the film's own helper
        self.assertEqual(uses.shots_using(d, ["nothing"]), [])

    def test_kit_call_graph(self):
        g = uses.graph([(bundle.KIT / f).read_text() for f in bundle.KIT_FILES])
        self.assertIn("comp", g)                                         # lib.jsx defines CU.comp


if __name__ == "__main__":
    unittest.main()


class Cli(unittest.TestCase):
    """T010: the CLI with the fake AE (desktop/test/fake-ae.mjs)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = {**os.environ, "STUDIO_AE_CONFIG": str(self.tmp / "ae.json"), "STUDIO_AE_WORK": str(self.tmp / "thư mục thử"),
                    "STUDIO_ROOT": str(self.tmp / "root")}
        for k in ("STUDIO_JOB", "STUDIO_PROXY", "STUDIO_AE_FAKE"):
            self.env.pop(k, None)

    def ae(self, *args, fake=True, extra=None):
        env = {**self.env, **({"STUDIO_AE_FAKE": "1"} if fake else {}), **(extra or {})}
        return subprocess.run(["sh", str(ROOT / "bin" / "studio"), "ae", *args], capture_output=True, text=True, env=env, timeout=120)

    def film(self, n=3) -> Path:
        d = self.tmp / "root" / "films" / "f1"
        make_film(d, [f"S{i}" for i in range(1, n + 1)])
        return d

    def test_uses(self):
        self.film()
        r = self.ae("uses", "f1", "monitorQ")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip().splitlines()[-1], "S2")

    def test_config_saved_and_read(self):
        fx = self.tmp / "AfterFX.exe"; fx.write_text("")
        r = subprocess.run(["sh", str(ROOT / "bin" / "studio"), "config", "ae", "--afterfx", str(fx), "--work", str(self.tmp / "w")],
                           capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        cfg = json.loads((self.tmp / "ae.json").read_text())
        self.assertEqual(cfg["afterfx"], str(fx))
        self.assertIn(f"afterfx: {fx}", r.stdout)
        r = subprocess.run(["sh", str(ROOT / "bin" / "studio"), "config", "ae", "--afterfx", "/nope/AfterFX.exe"],
                           capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 2)

    def test_missing_ae_is_reported_fast(self):
        self.film()
        (self.tmp / "ae.json").write_text(json.dumps({"afterfx": "/nope/AfterFX.exe", "aerender": "/nope/aerender.exe",
                                                       "work": str(self.tmp / "w")}))
        t = time.time()
        r = self.ae("build", "f1", fake=False)
        self.assertLess(time.time() - t, 10)                     # SC-004
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("ae_missing", r.stderr)

    def test_page_film_refused(self):
        (self.tmp / "root" / "films" / "web1").mkdir(parents=True)
        r = self.ae("build", "web1")
        self.assertEqual(r.returncode, 2)
        self.assertIn("web page engine", r.stderr)

    def test_build_with_fake_ae(self):
        d = self.film()
        r = self.ae("build", "f1", "--shots", "S1,S3")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        marks = json.loads((d / "out" / "build-shots.json").read_text())
        self.assertEqual([m[3] for m in marks["shots"]], ["S1", "S3"])
        self.assertTrue((d / "out" / "build.mp4").stat().st_size > 0)

    def test_build_error_and_check(self):
        self.film()
        r = self.ae("build", "f1", extra={"FAKE_AE_MODE": "err"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("build_error", r.stderr)
        r = self.ae("build", "f1", extra={"FAKE_AE_MODE": "check"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("CHECK floor S1", r.stdout)

    def test_no_video_rendered(self):
        self.film()
        r = self.ae("build", "f1", extra={"FAKE_AE_MODE": "norender"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("render_error", r.stderr)

    def test_entry_renders_in_after_effects(self):
        d = self.film()
        from ae import bundle as b
        self.assertIn('CU.RENDER = "master.mp4";', b.entry_text(film.load(d), ["S1"], "f1"))
        self.assertIn("rq.render()", (b.KIT / "build_core.jsx").read_text())

    def test_script_never_starts(self):
        self.film()
        t = time.time()
        r = self.ae("build", "f1", extra={"FAKE_AE_MODE": "noscript", "STUDIO_AE_START_TIMEOUT": "2"})
        self.assertLess(time.time() - t, 10)
        self.assertEqual(r.returncode, 3)
        self.assertIn("Allow Scripts to Write Files and Access Network", r.stderr)

    def test_disk_low(self):
        from ae import local
        d = self.film()
        orig = local.free_bytes
        local.free_bytes = lambda p: 1024
        try:
            with self.assertRaises(local.AeError) as c:
                local.build(d, None, s={**local.settings(), "kind": "fake", "work": str(self.tmp / "w")})
            self.assertEqual(c.exception.code, "disk_low")
        finally:
            local.free_bytes = orig

    def test_fix_splices_into_the_film(self):
        d = self.film(3)
        testsrc(d / "f1.mp4", 6, size="320x180")              # the film: 3 shots of 2 s
        (d / "shots.json").write_text(json.dumps({"version": 1, "video": "f1.mp4", "duration": 6, "fps": 30,
                                                  "shots": [[0, 2, "", "S1"], [2, 4, "", "S2"], [4, 6, "", "S3"]]}))
        old = self.tmp / "old.mp4"
        old.write_bytes((d / "f1.mp4").read_bytes())
        r = self.ae("fix", "f1", "S2")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("previous kept", r.stdout)
        self.assertTrue((d / "f1.prev.mp4").is_file())
        self.assertEqual(frames(d / "f1.mp4"), 180)
        self.assertGreater(psnr(old, d / "f1.mp4", 0, 2), 40)
        self.assertGreater(psnr(old, d / "f1.mp4", 4, 2), 40)


class FakeWork(unittest.TestCase):
    """specs/035 T051: a fake run (tests) never writes into the real After Effects work folder."""

    def test_env_set_after_import_wins(self):
        from ae import local
        with tempfile.TemporaryDirectory() as t:
            cfg = Path(t) / "ae.json"
            cfg.write_text(json.dumps({"work": str(Path(t) / "real")}))
            keep = {k: os.environ.get(k) for k in ("STUDIO_AE_FAKE", "STUDIO_AE_WORK", "STUDIO_AE_CONFIG")}
            try:
                os.environ.update(STUDIO_AE_FAKE="1", STUDIO_AE_CONFIG=str(cfg), STUDIO_AE_WORK=str(Path(t) / "w"))
                self.assertEqual(local.config_path(), cfg)                  # read now, not when the module was imported
                self.assertEqual(local.settings()["work"], str(Path(t) / "w"))
            finally:
                for k, v in keep.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
