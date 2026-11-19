"""Tier 1 rules for kit pages (specs/028 T023; FR-004, FR-017, FR-018, FR-024, SC-006)."""
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import people, plancheck  # noqa: E402


class KitIssues(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.film = self.root / "films" / "f"
        self.film.mkdir(parents=True)
        people.new("test-person", "Test Person", root=self.root, fetch=False)
        (self.film / "SOURCES.md").write_text('- [P03] "we will keep building for the long term": Example News, 2026, https://example.com\n')

    def issues(self, inp):
        return plancheck.kit_issues(self.film, inp, self.root)

    def test_page_without_kit_exports_is_unchanged(self):                   # FR-024
        self.assertEqual(self.issues({"shots": [], "cards": []}), [])

    def test_kit_name(self):
        r = self.issues({"shots": [{"id": "S014", "t0": 12.5, "t1": 15}], "kit_errors": [{"shot": "S014", "kind": "unknown_pose", "name": "hold-lamp", "hint": "hold"}]})
        self.assertEqual(r[0]["rule"], "kit_name")
        self.assertEqual(r[0]["ref"], "S014")
        self.assertEqual(r[0]["at"], 12.5)
        self.assertIn("'hold'", r[0]["fix"])

    def test_unapproved_person_blocks(self):                                  # FR-017
        r = self.issues({"people": [{"slug": "test-person", "hash": "x"}]})
        self.assertEqual(r[0]["rule"], "person_unapproved")
        self.assertEqual(r[0]["severity"], "block")
        people.approve("test-person", "", "chat", self.root)
        people.use("f", ["test-person"], self.root)
        self.assertEqual(self.issues({"people": [{"slug": "test-person"}]}), [])

    def test_words_of_real_people(self):                                      # FR-018
        b = lambda text, person=True: {"bubbles": [[2.0, 4.0, "S003", "person:test-person" if person else "narrator", text, person]]}
        self.assertEqual(self.issues(b("!")), [])
        self.assertEqual(self.issues(b("?!")), [])
        self.assertEqual(self.issues(b("$")), [])
        self.assertEqual(self.issues(b("We will keep building")), [])          # a part of a sourced quote
        r = self.issues(b("We will win this market"))
        self.assertEqual(r[0]["rule"], "person_words")
        self.assertEqual(r[0]["ref"], "S003")
        self.assertEqual(self.issues(b("It works!", person=False)), [])       # generic roles may speak


if __name__ == "__main__":
    unittest.main()
