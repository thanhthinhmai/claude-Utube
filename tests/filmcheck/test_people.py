"""The real-person library (specs/028 T022; FR-016, SC-010)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import people  # noqa: E402


class People(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "films" / "one").mkdir(parents=True)
        (self.root / "films" / "two").mkdir(parents=True)
        people.new("test-person", "Test Person", "a test", root=self.root, fetch=False)

    def fig(self):
        return self.root / "people" / "test-person" / "figure.js"

    def test_new_is_not_approved(self):
        d = people.load("test-person", self.root)
        self.assertIsNone(d["approved"])
        self.assertEqual(d["figure_hash"], people.figure_hash(self.fig()))
        self.assertEqual(people.status("test-person", self.root), "not approved")

    def test_use_blocks_until_approved(self):
        with self.assertRaises(people.PeopleError):
            people.use("one", ["test-person"], self.root)
        people.approve("test-person", "looks right", "chat", self.root)
        out = people.use("one", ["test-person"], self.root)
        idx = json.loads((out / "index.json").read_text())
        self.assertEqual(idx["people"][0]["slug"], "test-person")
        self.assertTrue((out / "test-person" / "figure.js").is_file())

    def test_second_film_needs_no_new_approval(self):                       # SC-010
        people.approve("test-person", "", "chat", self.root)
        people.use("one", ["test-person"], self.root)
        people.use("two", ["test-person"], self.root)
        self.assertEqual(people.check_film(self.root / "films" / "two", None, self.root), [])

    def test_editing_the_drawing_needs_approval_again(self):
        people.approve("test-person", "", "chat", self.root)
        people.use("one", ["test-person"], self.root)
        self.fig().write_text(self.fig().read_text() + "\n// a change\n")
        self.assertEqual(people.status("test-person", self.root), "changed since approval")
        self.assertEqual(people.check_film(self.root / "films" / "one", None, self.root)[0]["problem"], "changed since approval")
        with self.assertRaises(people.PeopleError):
            people.use("two", ["test-person"], self.root)
        people.approve("test-person", "second look", "ui", self.root)
        d = people.load("test-person", self.root)
        self.assertEqual(len(d["history"]), 1)                                # the old approval is kept
        self.assertEqual(d["approved"]["by"], "ui")
        problems = people.check_film(self.root / "films" / "one", None, self.root)
        self.assertIn("copy differs", problems[0]["problem"])                 # the film still has the old copy

    def test_unknown_person_in_a_film(self):
        probs = people.check_film(self.root / "films" / "one", [{"slug": "nobody"}], self.root)
        self.assertEqual(probs[0]["problem"], "not in the people library")

    def test_bad_slug(self):
        with self.assertRaises(people.PeopleError):
            people.new("Bad Slug", "x", root=self.root, fetch=False)

    def test_listing(self):
        rows = people.listing(self.root)
        self.assertEqual([(r["slug"], r["status"]) for r in rows], [("test-person", "not approved")])


if __name__ == "__main__":
    unittest.main()
