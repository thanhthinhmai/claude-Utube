"""specs/039 T004: camtrack on a synthetic film with known zoom, ease, drift and parallax."""
import shutil
import tempfile
import unittest
from pathlib import Path

import helpers  # noqa: F401  (puts tools/style-learn on the path)
import camsynth
from sl import camtrack


class CamTrack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="camtrack."))
        cls.key = camsynth.make(cls.tmp / "c.mp4")
        cls.got = [camtrack.measure(cls.tmp / "c.mp4", s["t0"], s["t1"]) for s in cls.key["shots"]]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def pairs(self):
        return list(zip(self.got, self.key["shots"]))

    def test_move_kind(self):
        for i, (g, k) in enumerate(self.pairs()):
            self.assertEqual(g["move"], k["move"], f"shot {i}")

    def test_total_zoom(self):
        for i, (g, k) in enumerate(self.pairs()):
            self.assertAlmostEqual(g["zoom_pct"], k["zoom_pct"], delta=0.3, msg=f"shot {i}")

    def test_drift(self):
        for i, (g, k) in enumerate(self.pairs()):
            for a, b in zip(g["drift_px"], k["drift_px"]):
                self.assertAlmostEqual(a, b, delta=2.0, msg=f"shot {i}")

    def test_ease(self):
        for i, (g, k) in enumerate(self.pairs()):
            if k["ease"] is None:
                self.assertIsNone(g["ease"], f"shot {i}")
                continue
            for a, b in zip(g["ease"], k["ease"]):
                self.assertAlmostEqual(a, b, delta=0.05, msg=f"shot {i}")

    def test_parallax(self):
        for i, (g, k) in enumerate(self.pairs()):
            self.assertEqual(g["parallax"], k["parallax"], f"shot {i}: {g['parallax_px']} px")

    def test_actor_does_not_change_zoom(self):
        g, k = self.pairs()[7]
        self.assertAlmostEqual(g["zoom_pct"], k["zoom_pct"], delta=0.3)
        self.assertTrue(g["reliable"])

    def test_rate_and_reliability(self):
        g = self.got[0]
        self.assertAlmostEqual(g["rate_pct_s"], g["zoom_pct"] / (g["dur"] - 0.3), delta=0.2)
        self.assertTrue(all(x["reliable"] for x in self.got))


if __name__ == "__main__":
    unittest.main()
