"""qc camera (specs/039 T036, SC-005): three synthetic shots — the chosen camera, a linear zoom instead of the eased
one, a moving foreground layer (parallax) — are measured with the real camera track: exactly the two wrong ones are
reported. Exceptions are refused inside a job and kept per shot outside one."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import camcheck, tiers  # noqa: E402

W, H, FPS, DUR = 640, 360, 30, 3.0
A = np.log(0.64) / np.log(0.5)                       # progress t**A: 0.64 at the half of the shot
EASE = [round(0.25 ** A, 3), 0.64, round(0.75 ** A, 3)]
CAM = {"size": "med", "move": "push", "zoom_pct": 6.0, "rate_pct_s": 2.0, "ease": EASE, "drift_px": [0.0, 0.0], "transition": "cut",
       "start": {"scale": 1.0, "cx": 50.0, "cy": 50.0}}


def texture(seed, w, h):
    rng = np.random.default_rng(seed)
    small = rng.integers(0, 255, (h // 8, w // 8), dtype=np.uint8)
    img = np.kron(small, np.ones((8, 8), dtype=np.uint8))
    return np.stack([img, (img * 0.7).astype(np.uint8), 255 - img], axis=2)


def write_clip(path: Path, progress, parallax=False):
    import cv2
    bg = texture(1, W * 2, H * 2)
    fg = texture(2, W, H * 2)
    n = int(DUR * FPS)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "12", str(path)],
                         stdin=subprocess.PIPE)
    for i in range(n):
        t = i / (n - 1)
        s = 1 + 0.06 * progress(t)
        M = np.float32([[s, 0, W / 2 - s * W], [0, s, H / 2 - s * H]])        # zoom about the middle of bg
        fr = cv2.warpAffine(bg, M, (W, H))
        if parallax:                       # the lower 40 % is a near layer: twice the zoom, its own drift (camsynth)
            sn = 1 + 0.12 * progress(t)
            M2 = np.float32([[sn, 0, W / 2 - sn * W / 2 + 30 * progress(t)], [0, sn, H / 2 - sn * H]])
            lay = cv2.warpAffine(fg, M2, (W, H))
            cut = int(H * 0.6)
            fr[cut:] = lay[cut:]
        p.stdin.write(fr.tobytes())
    p.stdin.close()
    p.wait()


@unittest.skipUnless(shutil.which("ffmpeg"), "no ffmpeg")
class CamCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import cv2  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("no opencv (sh bin/studio deps learn)")
        cls.root = Path(tempfile.mkdtemp(prefix="camchk."))
        d = cls.d = cls.root / "films" / "f1"
        (d / "ae").mkdir(parents=True)
        (d / "ae" / "shots.jsx").write_text("// shots\n")
        shots = ["S1", "S2", "S3"]
        (d / "film.json").write_text(json.dumps({"engine": "ae", "shots": shots, "ae_files": ["shots.jsx"],
                                                 "shot_plan": {s: {"size": "med", "camera": CAM} for s in shots}}))
        (d / "animatic" / "shots").mkdir(parents=True)
        write_clip(d / "animatic" / "shots" / "S1.mp4", lambda t: t ** A)
        write_clip(d / "animatic" / "shots" / "S2.mp4", lambda t: t)
        write_clip(d / "animatic" / "shots" / "S3.mp4", lambda t: t ** A, parallax=True)
        cls.r = camcheck.run(d)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def test_two_of_three_reported(self):
        bad = sorted({i["shot"] for i in self.r["issues"]})
        self.assertEqual(bad, ["S2", "S3"], json.dumps(self.r["measures"]["shots"], indent=1))
        rules = {(i["shot"], i["rule"]) for i in self.r["issues"]}
        self.assertIn(("S2", "cam_ease"), rules)
        self.assertIn(("S3", "cam_parallax"), rules)
        self.assertFalse(self.r["pass"])
        s1 = self.r["measures"]["shots"]["S1"]
        self.assertLess(abs(s1["zoom_pct"] - 6.0), camcheck.ZOOM_TOL)

    def test_exception_by_user_only(self):
        os.environ["STUDIO_JOB"] = "j-1"
        try:
            with self.assertRaises(tiers.TierError):
                tiers.add_exception(self.d, "S3", "cam_parallax", "the window is meant to slide")
        finally:
            os.environ.pop("STUDIO_JOB")
        e = tiers.add_exception(self.d, "S3", "cam_parallax", "the window is meant to slide")
        self.assertEqual(e["by"], "user")
        r = camcheck.recompute(self.d)
        s3 = [i for i in r["issues"] if i["shot"] == "S3"]
        self.assertTrue(all(i.get("excepted") for i in s3 if i["rule"] == "cam_parallax"), s3)
        tiers.remove_exception(self.d, "S3", "cam_parallax")
        camcheck.recompute(self.d)


class Rules(unittest.TestCase):
    def test_direction_static_and_user_request(self):
        plan = {"S1": {"camera": {**CAM}}, "S2": {"camera": {**CAM, "move": "static", "zoom_pct": 0.0}},
                "S3": {"camera": {**CAM, "by_user_request": True}},
                "S4": {"camera": {**CAM, "transition": "cut"}, "transition": "dissolve"}}
        m = {"S1": {"move": "pull", "zoom_pct": -5.0, "ease": EASE}, "S2": {"move": "push", "zoom_pct": 4.0, "ease": EASE},
             "S3": {"move": "pull", "zoom_pct": -9.0}, "S4": {"move": "push", "zoom_pct": 6.2, "ease": EASE}}
        issues, _ = camcheck.rules(plan, m)
        self.assertEqual(sorted((i["shot"], i["rule"]) for i in issues),
                         [("S1", "cam_dir"), ("S2", "cam_dir"), ("S4", "cam_transition")])

    def test_zoom_tolerance(self):
        plan = {"S1": {"camera": CAM}}
        self.assertEqual(camcheck.rules(plan, {"S1": {"move": "push", "zoom_pct": 6.9, "ease": EASE}})[0], [])
        got = camcheck.rules(plan, {"S1": {"move": "push", "zoom_pct": 7.2, "ease": EASE}})[0]
        self.assertEqual([i["rule"] for i in got], ["cam_zoom"])


class Fit(unittest.TestCase):
    """camera fit: the track reads flat art 25 % short; one round scales the keyed zoom, the next measure passes."""
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="camfit."))
        d = self.d = self.root / "films" / "f2"
        (d / "ae").mkdir(parents=True)
        (d / "ae" / "shots.jsx").write_text("// shots\n")
        (d / "animatic" / "shots").mkdir(parents=True)
        for s in ("S1", "S2", "S3", "S4"):
            (d / "animatic" / "shots" / f"{s}.mp4").write_bytes(b"x")
        plan = {"S1": {"camera": CAM}, "S2": {"camera": {**CAM, "zoom_pct": 0.5}},
                "S3": {"camera": {**CAM, "zoom_pct": 8.0}}, "S4": {"camera": {**CAM, "zoom_pct": 6.0}}}
        (d / "film.json").write_text(json.dumps({"engine": "ae", "shots": list(plan), "ae_files": ["shots.jsx"],
                                                 "shot_plan": plan}))
        self.drafts = []
        self.length = camcheck._length
        camcheck._length = lambda p: 3.0

    def tearDown(self):
        camcheck._length = self.length
        shutil.rmtree(self.root, ignore_errors=True)

    def measure(self, path, t0, t1, a, b):
        sid = Path(path).stem
        cam = json.loads((self.d / "film.json").read_text())["shot_plan"][sid]["camera"]
        z = cam["zoom_pct"] * cam.get("fit_k", 1.0) * 0.75
        if sid == "S4":
            z = -z                                           # going the wrong way: cam_dir, never fitted
        return {"move": "push" if z > 0 else "pull", "zoom_pct": z, "ease": EASE, "reliable": True}

    def draft(self, d, shots):
        self.drafts.append(shots)
        return 0

    def test_one_round_fixes_the_zoom(self):
        f = camcheck.fit(self.d, measure=self.measure, draft=self.draft)
        self.assertEqual(self.drafts, [["S1", "S3"]])
        self.assertEqual(sorted(f["rounds"][0]), ["S1", "S3"])
        plan = json.loads((self.d / "film.json").read_text())["shot_plan"]
        self.assertAlmostEqual(plan["S1"]["camera"]["fit_k"], 1.333, places=3)
        self.assertNotIn("fit_k", plan["S2"]["camera"])        # within 1 point: left alone
        self.assertNotIn("fit_k", plan["S4"]["camera"])
        off = {i["shot"] for i in f["result"]["issues"]}
        self.assertEqual(off, {"S4"})
        self.assertEqual(f["own_camera"], [])

    def test_failed_draft_stops(self):
        with self.assertRaises(camcheck.CameraCheckError) as e:
            camcheck.fit(self.d, measure=self.measure, draft=lambda d, s: 3)
        self.assertEqual(e.exception.code, 3)

    def test_factor_is_clamped(self):
        plan = {"S1": {"camera": {**CAM, "zoom_pct": 9.0}}}
        issues = [{"shot": "S1", "rule": "cam_zoom"}]
        self.assertEqual(camcheck.fit_factors(plan, issues, {"S1": {"zoom_pct": 1.0}}), ({"S1": 3.0}, []))

    def test_secant_and_own_camera(self):
        plan = {"S1": {"camera": {**CAM, "zoom_pct": 8.0, "fit_k": 1.3}}}
        issues = [{"shot": "S1", "rule": "cam_zoom"}]
        ks, own = camcheck.fit_factors(plan, issues, {"S1": {"zoom_pct": 10.0}}, {"S1": [(1.0, 6.0)]})
        self.assertEqual((ks, own), ({"S1": 1.15}, []))                  # through (1.0, 6) and (1.3, 10): 8 at 1.15
        ks, own = camcheck.fit_factors(plan, issues, {"S1": {"zoom_pct": 6.1}}, {"S1": [(1.0, 6.0)]})
        self.assertEqual((ks, own), ({}, ["S1"]))


if __name__ == "__main__":
    unittest.main()
