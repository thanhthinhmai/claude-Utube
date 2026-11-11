"""The test vectors the desktop app checks are still good for the Python side (specs/017 T005)."""
import json
import unittest

from helpers import REPO, signing

V = REPO / "desktop" / "test" / "vectors"


class Vectors(unittest.TestCase):
    def test_vectors(self):
        v = json.loads((V / "vectors.json").read_text())
        self.assertEqual(signing.verify_lease(v["public"], v["lease"]), v["payload"])
        self.assertTrue(signing.verify_bytes(v["public"], (V / "release.json").read_bytes(), (V / "release.json.sig").read_text()))
        self.assertEqual(signing.public_of(v["private_test_only"]), v["public"])


if __name__ == "__main__":
    unittest.main()
