"""Tier results, fingerprints, exceptions and the render gate (specs/020 T011, T013 part; FR-009, FR-015, FR-021)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import report, tiers  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"


def issue(rule, ref, severity="block"):
    return {"tier": None, "ref": ref, "at": 1.0, "rule": rule, "severity": severity, "measure": 1, "limit": 0,
            "text": "", "fix": "", "excepted": None}


class Tiers(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(exist_ok=True)
        self.d = Path(tempfile.mkdtemp(dir=TMP)) / "films" / "f"
        (self.d / "voices").mkdir(parents=True)
        (self.d / "index.html").write_text("<p>a</p>")
        (self.d / "lines.json").write_text("[]")
        (self.d / "voices" / "l01.wav").write_bytes(b"RIFF")
        (self.d / ".check").mkdir()
        (self.d / ".check" / "plan-input.json").write_text(json.dumps({"shots": [{"id": "P01.0", "t0": 0, "t1": 2}]}))

    def test_fingerprint(self):
        a = tiers.fingerprint(self.d)
        v = tiers.fingerprint(self.d, "voice")
        for f in ("qc-exceptions.json", "checks.json", "CHECKS.md", "render.log"):
            (self.d / f).write_text("x")
        (self.d / ".check" / "more.json").write_text("{}")
        self.assertEqual(tiers.fingerprint(self.d), a)
        (self.d / "index.html").write_text("<p>b</p>")
        self.assertNotEqual(tiers.fingerprint(self.d), a)
        self.assertEqual(tiers.fingerprint(self.d, "voice"), v)            # the page is not part of the voice
        (self.d / "voices" / "l01.wav").write_bytes(b"RIFF2")
        self.assertNotEqual(tiers.fingerprint(self.d, "voice"), v)

    def test_exceptions_are_checked(self):
        with self.assertRaises(tiers.TierError):
            tiers.add_exception(self.d, "P99.0", "flat", "why")            # no such shot
        with self.assertRaises(tiers.TierError):
            tiers.add_exception(self.d, "P01.0", "cut_in_sentence", "why")  # not exceptable
        with self.assertRaises(tiers.TierError):
            tiers.add_exception(self.d, "P01.0", "flat", "  ")             # no reason
        with self.assertRaises(tiers.TierError):
            tiers.add_exception(self.d, "P01.0", "flat", "x" * 201)
        e = tiers.add_exception(self.d, "P01.0", "flat", "title card on purpose")
        self.assertEqual(tiers.load_exceptions(self.d), [e])
        self.assertTrue(tiers.remove_exception(self.d, "P01.0", "flat"))
        self.assertEqual(tiers.load_exceptions(self.d), [])

    def test_exception_recomputes_pass(self):
        fp = tiers.fingerprint(self.d)
        tiers.save_tier(self.d, "shots", tiers.result("shots", [issue("flat", "P01.0")], {}, [], 1.0, fp))
        self.assertFalse(tiers.load_tier(self.d, "shots")["pass"])
        tiers.add_exception(self.d, "P01.0", "flat", "title card on purpose")
        tiers.recompute(self.d)
        r = tiers.load_tier(self.d, "shots")
        self.assertTrue(r["pass"])
        self.assertEqual(r["issues"][0]["excepted"]["reason"], "title card on purpose")
        self.assertEqual(tiers.fingerprint(self.d), fp)
        self.assertIn("title card on purpose", (self.d / "CHECKS.md").read_text())

    def test_gate(self):
        name = self.d.name
        why = tiers.gate(self.d)
        self.assertEqual(len(why), 2)
        self.assertIn(f"sh bin/studio qc plan {name}", why[0])
        fp = tiers.fingerprint(self.d)
        tiers.save_tier(self.d, "plan", tiers.result("plan", [], {}, [], 1.0, fp))
        tiers.save_tier(self.d, "shots", tiers.result("shots", [issue("style_luma", "film", "warn")], {}, [], 1.0, fp))
        why = tiers.gate(self.d)
        self.assertEqual(len(why), 1)
        self.assertIn("accept-style", why[0])
        report.update(self.d, lambda x: x["tiers"]["shots"].update(style_accept={"reason": "night film", "at": "t"}))
        self.assertEqual(tiers.gate(self.d), [])
        (self.d / "index.html").write_text("<p>changed</p>")               # US1 AC4: a changed film is not checked
        self.assertEqual(len(tiers.gate(self.d)), 2)

    def test_skip_is_recorded(self):
        tiers.record_skip(self.d, "a test render")
        self.assertEqual(tiers.load_tier(self.d, "render")["skipped_checks"]["reason"], "a test render")


if __name__ == "__main__":
    unittest.main()
