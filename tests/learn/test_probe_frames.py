import unittest

from helpers import FX, need_fixtures
from sl import frames, probe


class ProbeFrames(unittest.TestCase):
    def setUp(self):
        need_fixtures(self)

    def count(self, name):
        m = probe.probe(FX / name)
        segs = probe.segments(m["duration"])
        per = {}
        for si, t, f in frames.iter_frames(FX / name, m, segs):
            per[si] = per.get(si, 0) + 1
            shape = f.shape
        return m, segs, per, shape

    def test_whole_video_exact(self):  # SC-001
        m, segs, per, shape = self.count("cuts.mp4")
        self.assertEqual(sum(per.values()), probe.expected_frames(m, segs))
        self.assertEqual(shape, (180, 320, 3))

    def test_long_video_segments(self):  # FR-005, SC-001 (±1 per segment)
        m, segs, per, _ = self.count("long.mp4")
        self.assertEqual(len(segs), 5)
        self.assertAlmostEqual(sum(b - a for a, b in segs), 180, places=3)
        self.assertEqual(segs[0], [0.0, 60.0])
        for si, (a, b) in enumerate(segs):
            self.assertLessEqual(abs(per[si] - round((b - a) * m["fps"])), 1)

    def test_portrait(self):
        m, _, _, shape = self.count("portrait.mp4")
        self.assertEqual(m["orientation"], "portrait")
        self.assertEqual(shape, (568, 320, 3))


if __name__ == "__main__":
    unittest.main()
