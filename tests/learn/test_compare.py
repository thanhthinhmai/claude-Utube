import json
import unittest

import numpy as np
from PIL import Image

from helpers import Project
from sl import compare, refset


def scene(seed, shift=0):
    r = np.random.default_rng(seed)
    blocks = r.integers(0, 4, (9, 16))
    cols = np.array([(200, 60, 40), (40, 90, 160), (230, 210, 150), (30, 30, 40)])
    img = cols[np.repeat(np.repeat(blocks, 40, 0), 40, 1)] + shift
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


class Compare(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        refset.save("cmp-set", refset.new_set("cmp-set", "files", []))
        self.d = refset.set_dir("cmp-set")
        scene(1).save(self.d / "ref.jpg", quality=95)

    def tearDown(self):
        self.p.close()

    def test_close_passes(self):  # SC-004
        scene(1).transpose(0).save(self.d / "ours.jpg", quality=95)   # same colours, mirrored layout
        r = compare.compare(self.d / "ref.jpg", self.d / "ours.jpg")
        self.assertTrue(r["pass"], r)
        self.assertGreaterEqual(r["palette_matched"], 4)

    def test_brighter_fails(self):
        scene(1, shift=26).save(self.d / "ours.jpg", quality=95)   # +0.1 luma
        r = compare.compare(self.d / "ref.jpg", self.d / "ours.jpg")
        self.assertFalse(r["pass"])
        self.assertAlmostEqual(r["luma_diff"], 0.1, delta=0.02)

    def test_cli_writes_files(self):
        scene(1).transpose(0).save(self.d / "ours.jpg", quality=95)
        rc = compare.cli("cmp-set", str(self.d / "ref.jpg"), str(self.d / "ours.jpg"), 2)
        self.assertEqual(rc, 0)
        j = json.loads((self.d / "proof" / "compare.json").read_text())
        self.assertEqual(j["round"], 2)
        self.assertTrue((self.d / "proof" / "compare.jpg").exists())


if __name__ == "__main__":
    unittest.main()
