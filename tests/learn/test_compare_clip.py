"""specs/023 T064: learn compare --clip measures the proof clip like the reference and says in or out of its range."""
import shutil
import tempfile
import unittest
from pathlib import Path

from helpers import Project
import synth
from sl import compare, refset


class CompareClip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="clip."))
        synth.make(cls.tmp / "s.mp4")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.p = Project()
        refset.save("c-set", refset.new_set("c-set", "videos", []))
        (refset.set_dir("c-set") / "profile").mkdir(parents=True)
        (refset.set_dir("c-set") / "proof").mkdir()

    def tearDown(self):
        self.p.close()

    def summary(self, still, m720, none):
        refset.write_json(refset.set_dir("c-set") / "profile" / "craft-summary.json",
                          {"motion": {"still_ratio": still, "motion720_p50": m720, "person_still_cam": {"none_share": none}}})

    def test_measures(self):
        m = compare.clip_measures(self.tmp / "s.mp4")
        self.assertEqual(m["pieces"], 13)                       # 25 s in 2-second pieces, the last one 1 s
        self.assertGreater(m["still_ratio"], 0.1)
        self.assertLess(m["still_ratio"], 0.7)
        self.assertGreater(m["motion720_p50"], 0)

    def test_in_and_out_of_range(self):
        self.summary([0.1, 0.9], [0.0, 1.0], 0.5)
        self.assertEqual(compare.clip_cli("c-set", str(self.tmp / "s.mp4")), 0)
        self.assertTrue((refset.set_dir("c-set") / "proof" / "clip-compare.json").exists())
        self.summary([0.95, 1.0], [0.0, 1.0], 0.5)              # the clip moves more than this reference
        self.assertEqual(compare.clip_cli("c-set", str(self.tmp / "s.mp4")), 1)

    def test_needs_the_summary(self):
        with self.assertRaises(refset.StepError):
            compare.clip_cli("c-set", str(self.tmp / "s.mp4"))


if __name__ == "__main__":
    unittest.main()
