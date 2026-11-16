"""specs/023 T005, SC-003: craft.py on a synthetic film with known camera moves, movement and transitions."""
import shutil
import tempfile
import unittest
from pathlib import Path

import helpers  # noqa: F401  (puts tools/style-learn on the path)
import synth
from sl import craft

TOL = 0.2


class Craft(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="craft."))
        cls.key = synth.make(cls.tmp / "s.mp4")
        cls.got = [craft.measure_shot(cls.tmp / "s.mp4", {"id": f"S{i:02d}", "t0": s["t0"], "t1": s["t1"]})
                   for i, s in enumerate(cls.key["shots"])]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_camera_types(self):
        ok = sum(g["cam"]["type"] == k["cam"] for g, k in zip(self.got, self.key["shots"]))
        print(f"\n  camera: {ok}/{len(self.got)}")
        self.assertGreaterEqual(ok / len(self.got), 0.9)

    def test_camera_speed(self):
        for g, k in zip(self.got, self.key["shots"]):
            if k["cam"] in ("drift-h", "drift-v"):
                self.assertAlmostEqual(g["cam"]["px_s"], k["px_s"], delta=0.15 * k["px_s"], msg=g["id"])
            if k["cam"] in ("push", "pull"):
                self.assertAlmostEqual(abs(g["cam"]["zoom_pct_s"]), 2.96, delta=0.6, msg=g["id"])

    def test_inner_movement(self):
        ok, late = 0, []
        for g, k in zip(self.got, self.key["shots"]):
            spans = g["inner"]["spans"]
            if bool(spans) == bool(k["inner"]):
                ok += 1
            for want in k["inner"]:                      # every known movement is found, on time
                near = [s for s in spans if abs(s[0] - want[0]) <= TOL and abs(s[1] - want[1]) <= TOL]
                if not near:
                    late.append((g["id"], want, [s[:2] for s in spans]))
        print(f"\n  movement: {ok}/{len(self.got)}")
        self.assertGreaterEqual(ok / len(self.got), 0.9)
        self.assertEqual(late, [])

    def test_camera_drift_is_not_movement(self):
        g = self.got[7]                                  # the camera drifts over a block fixed in the world
        self.assertEqual(g["inner"]["spans"], [])

    def test_transitions(self):
        soft = [(g, k) for g, k in zip(self.got, self.key["shots"]) if k["trans_in"] and k["trans_in"][0] != "cut"]
        ok = sum(g["trans_in"]["type"] == k["trans_in"][0] for g, k in soft)
        print(f"\n  transitions: {ok}/{len(soft)}")
        self.assertGreaterEqual(ok / len(soft), 0.9)
        for g, k in soft:
            if k["trans_in"][0] != "dissolve":
                self.assertAlmostEqual(g["trans_in"]["dur"], k["trans_in"][1], delta=0.12, msg=g["id"])
        cuts = [g for g, k in zip(self.got, self.key["shots"]) if k["trans_in"] and k["trans_in"][0] == "cut"]
        self.assertTrue(all(g["trans_in"]["type"] == "cut" for g in cuts))

    def test_frames_entry(self):
        fr = craft.sample(self.tmp / "s.mp4", 2.65, 4.85)   # the shot with the rising hand
        m = craft.measure_frames(fr, 2.65)
        self.assertEqual(m["cam"]["type"], "still")
        self.assertTrue(m["inner"]["spans"])


if __name__ == "__main__":
    unittest.main()
