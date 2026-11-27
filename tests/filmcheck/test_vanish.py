"""Vanishing point and horizon from straight lines (specs/038 T029, contracts/style-depth.md)."""
import sys
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import vanish  # noqa: E402

try:
    import cv2
except ImportError:            # vanish needs OpenCV (tools/.venv)
    cv2 = None


def hallway(w=960, h=540, vy=0.42, vx=0.5):
    """A one-point-perspective hallway drawn by code: walls, floor tiles, lockers all run to (vx, vy)."""
    img = np.full((h, w, 3), 235, np.uint8)
    vp = (int(w * vx), int(h * vy))
    back = (int(w * 0.38), int(h * 0.30), int(w * 0.62), int(h * 0.56))
    cv2.rectangle(img, back[:2], back[2:], (200, 210, 230), -1)
    for i in range(-12, 13):
        x = int(w / 2 + i * w / 10)
        for y in (h, 0):
            p0 = (x, y)
            t = 0.75
            p1 = (int(p0[0] + (vp[0] - p0[0]) * t), int(p0[1] + (vp[1] - p0[1]) * t))
            cv2.line(img, p0, p1, (60, 70, 90), 2)
    for y in range(0, h, h // 9):
        for x in (0, w):
            t = 0.7
            cv2.line(img, (x, y), (int(x + (vp[0] - x) * t), int(y + (vp[1] - y) * t)), (90, 60, 50), 2)
    for k in range(1, 8):                                   # tile rows: horizontal lines
        y = int(vp[1] + (h - vp[1]) * (1 - 0.7 ** k))
        cv2.line(img, (0, y), (w, y), (120, 120, 140), 1)
    return img


@unittest.skipIf(cv2 is None, "OpenCV is not installed")
class Vanish(unittest.TestCase):
    def test_horizon_of_a_hallway(self):
        for vy in (0.42, 0.30, 0.60):
            r = vanish.measure(hallway(vy=vy))
            self.assertGreaterEqual(r["lines"], 20)
            self.assertIsNotNone(r["horizon"], vy)
            self.assertAlmostEqual(r["horizon"], vy, delta=0.03)
            self.assertTrue(r["vps"])

    def test_few_lines_give_none(self):
        img = np.full((540, 960, 3), 240, np.uint8)
        cv2.circle(img, (480, 270), 120, (40, 120, 200), -1)
        r = vanish.measure(img)
        self.assertLess(r["lines"], 20)
        self.assertEqual((r["horizon"], r["hfov_deg"], r["vps"]), (None, None, []))

    def test_reads_a_file(self):
        p = Path(__file__).resolve().parent / ".tmp" / "hall.png"
        p.parent.mkdir(exist_ok=True)
        cv2.imwrite(str(p), hallway())
        self.assertAlmostEqual(vanish.measure(str(p))["horizon"], 0.42, delta=0.03)


if __name__ == "__main__":
    unittest.main()
