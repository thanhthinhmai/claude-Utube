"""specs/023 T033: the motion rules (still_person, style_person_motion, style_depth) and the tier-4 film measures."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import motioncheck, shotcheck  # noqa: E402

HAVE_VENV = motioncheck.VENV_PY.exists()
TPL = {"motion": {"still_person_min_s": 2.0, "dead_share_max": 0.055, "still_ratio": [0.24, 0.84],
                  "motion720_p50": [0.008, 0.176]},
       "framing": {"by_scale": {"cu": {"focused_share": [0.417, 0.667]}}}, "transitions": {"fade_max_per_film": 2}}


def frames(tmp: Path, kind: str, n=4):
    """Four 640×360 frames: still, a moving hand, or a camera drift over a still world."""
    import numpy as np
    from PIL import Image
    import importlib.util
    spec = importlib.util.spec_from_file_location("learn_synth", REPO / "tests" / "learn" / "synth.py")
    synth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(synth)                      # loaded by path: tests/learn must not shadow these tests
    wld = synth.world()
    out = []
    for k in range(n):
        t = k * 0.6
        if kind == "drift":
            img = synth.view(wld, 700 + 25 * t, 500, 1.0)
        else:
            img = synth.view(wld, 700, 500, 1.0)
        if kind == "hand":
            y = int(200 - 25 * k)
            img[y:y + 50, 400:428] = (225, 190, 160)
        p = tmp / f"{kind}-{k}.jpg"
        Image.fromarray(np.clip(img, 0, 255).astype("uint8")).save(p, quality=92)
        out.append(str(p))
    return out


@unittest.skipUnless(HAVE_VENV, "needs the learning tools (sh bin/studio deps learn)")
class Motion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="motion."))
        cls.f = {k: frames(cls.tmp, k) for k in ("still", "hand", "drift")}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_shot_motion(self):
        self.assertEqual(motioncheck.shot_motion(self.f["still"])["moving"], False)
        self.assertEqual(motioncheck.shot_motion(self.f["still"])["cam"], "still")
        self.assertTrue(motioncheck.shot_motion(self.f["hand"])["moving"])
        d = motioncheck.shot_motion(self.f["drift"], gap=0.6)
        self.assertNotEqual(d["cam"], "still")
        self.assertFalse(d["moving"])                            # the drift is the camera, not movement

    def rules(self, kinds, cast=None, labels=None, focus=None):
        shots = [{"id": f"S{i:02d}", "t0": i * 3.0, "t1": (i + 1) * 3.0} for i in range(len(kinds))]
        mf = [{"shot": s["id"], "file": f} for s, k in zip(shots, kinds) for f in self.f[k]]
        return shotcheck.motion_rules(TPL, shots, mf, cast if cast is not None else {s["id"]: 1 for s in shots},
                                      labels or {}, focus or {}, 3.0 * len(kinds))

    def test_still_person_blocks(self):
        iss, meas, _ = self.rules(["still", "hand", "drift"])
        dead = [i for i in iss if i["rule"] == "still_person"]
        self.assertEqual([i["ref"] for i in dead], ["S00"])
        self.assertEqual(dead[0]["severity"], "block")
        self.assertEqual(meas["motion"]["dead_share"], 0.333)
        self.assertTrue(any(i["rule"] == "style_person_motion" for i in iss))

    def test_no_people_no_block(self):
        iss, _, _ = self.rules(["still"], cast={"S00": 0})
        self.assertFalse([i for i in iss if i["rule"] == "still_person"])

    def test_people_estimated_from_labels(self):
        iss, meas, skipped = self.rules(["still", "still"], cast={}, labels={"S00": {"scale": "insert"}, "S01": {"scale": "med"}})
        self.assertEqual([i["ref"] for i in iss if i["rule"] == "still_person"], ["S01"])
        self.assertEqual(meas["motion"]["people"], "estimated")
        self.assertTrue(any("CAST" in x for x in skipped))

    def test_depth_by_scale(self):
        iss, _, _ = self.rules(["hand"], labels={"S00": {"scale": "cu"}}, focus={"S00": {"focused_share": 1.0}})
        self.assertTrue(any(i["rule"] == "style_depth" and i["severity"] == "warn" for i in iss))

    def test_no_template_skips(self):
        iss, meas, skipped = shotcheck.motion_rules(None, [], [], {}, {}, {}, 10)
        self.assertEqual((iss, meas), ([], {}))
        self.assertIn("template.json", skipped[0])


class FilmMeasures(unittest.TestCase):
    def test_film_measures(self):
        rows = [{"id": "A", "t0": 0, "t1": 4, "cam": {"type": "still", "px_s": 0}, "trans_in": None},
                {"id": "B", "t0": 4, "t1": 10, "cam": {"type": "push", "px_s": 2}, "trans_in": {"type": "cut"}},
                {"id": "C", "t0": 10, "t1": 12, "cam": {"type": "drift-h", "px_s": 40}, "trans_in": {"type": "fade"}}]
        m = motioncheck.film_measures(rows, 12.0)
        self.assertEqual(m["still_ratio"], 0.333)
        self.assertAlmostEqual(m["motion720_p50"], 2 * 720 / 1280 / 60, places=4)
        self.assertEqual(m["transitions"], {"fade": 1})

    def test_missing_venv_is_an_error(self):
        old = motioncheck.VENV_PY
        motioncheck.VENV_PY = Path("/nonexistent/python")
        try:
            with self.assertRaises(motioncheck.MotionError):
                motioncheck.shot_motion(["a.jpg", "b.jpg"])
        finally:
            motioncheck.VENV_PY = old

    def test_template_of_film(self):
        d = Path(tempfile.mkdtemp(prefix="tpl."))
        try:
            self.assertIsNone(motioncheck.template_of(d))       # no channel snapshot, no style
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
