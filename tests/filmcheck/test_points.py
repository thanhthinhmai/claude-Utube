"""Review points: fingerprints by part, approvals, states, gates (specs/026 T003)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from filmcheck import points, report, tiers  # noqa: E402
import samples  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"


class Points(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(exist_ok=True)
        self.d = samples.review_film(Path(tempfile.mkdtemp(dir=TMP)), kit=False)

    def edit(self, rel, old, new):
        p = self.d / rel
        p.write_text(p.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

    def test_fingerprint_by_part(self):
        s, sh = points.fingerprint(self.d, "script"), points.fingerprint(self.d, "shots")
        (self.d / "mix.json").write_text('{"music": "seed:2"}')
        self.assertEqual(points.fingerprint(self.d, "script"), s)
        self.assertEqual(points.fingerprint(self.d, "shots"), sh)        # the mix is not the picture
        self.assertEqual(sh, tiers.fingerprint(self.d))
        self.edit("SCRIPT.md", "eleven days", "eleven whole days")
        self.assertNotEqual(points.fingerprint(self.d, "script"), s)

    def test_default_on_and_states(self):
        st = points.status(self.d)
        self.assertEqual([p for p in points.POINTS if st[p]["on"]], ["script", "shots"])
        self.assertEqual(st["script"]["state"], "ready")
        self.assertEqual(st["shots"]["state"], "not_reached")
        self.assertEqual(st["voice"]["state"], "off")
        self.assertEqual(points.state(self.d, "script", pending=True), "waiting")

    def test_approve_records_and_goes_stale(self):
        code, why = points.approve(self.d, "script", base=points.fingerprint(self.d, "script"), source="ui", by="me",
                                   review_id="r-1")
        self.assertEqual((code, why), (0, []))
        a = report.load(self.d)["reviews"]["approved"]["script"]
        self.assertEqual({k for k in a}, {"fingerprint", "at", "by", "source", "review_id"})
        self.assertEqual((a["by"], a["source"], a["review_id"]), ("me", "ui", "r-1"))
        self.assertEqual(points.state(self.d, "script"), "approved")
        self.assertEqual(points.gate(self.d, "script"), [])
        self.edit("SCRIPT.md", "eleven days", "eleven whole days")
        self.assertEqual(points.state(self.d, "script"), "stale")
        self.assertIn("changed since", points.gate(self.d, "script")[0])

    def test_old_base_and_failed_checks(self):
        code, why = points.approve(self.d, "script", base="0" * 16)
        self.assertEqual(code, 4)
        self.edit("SCRIPT.md", "Target: 20s", "Target: 90s")             # the length rule fails
        code, why = points.approve(self.d, "script")
        self.assertEqual(code, 1)
        self.assertIn("script check", why[0])
        self.assertFalse(((report.load(self.d).get("reviews") or {}).get("approved") or {}).get("script"))

    def test_set_on_refuses_locked(self):
        points.approve(self.d, "script")
        with self.assertRaises(points.PointError):
            points.set_on(self.d, "shots")                               # turning off an approved point
        self.assertEqual(points.set_on(self.d, "script,shots,voice"), ["script", "voice", "shots"])
        with self.assertRaises(points.PointError):
            points.set_on(self.d, "script", pending={"shots"})           # shots is waiting
        with self.assertRaises(points.PointError):
            points.set_on(self.d, "script,bogus")

    def test_off_point_and_skip(self):
        points.set_on(self.d, "none")
        self.assertEqual(points.gate(self.d, "script"), [])
        points.set_on(self.d, "script")
        self.assertTrue(points.gate(self.d, "script"))
        points.skip(self.d, "script", "a test run")
        self.assertEqual(points.gate(self.d, "script"), [])
        self.assertEqual(report.load(self.d)["reviews"]["skipped"]["script"]["reason"], "a test run")
        with self.assertRaises(points.PointError):
            points.skip(self.d, "script", " ")

    def test_no_narration_is_skipped(self):
        report.update(self.d, lambda x: x["script"].update({"verdict": "skipped", "skip_reason": "no narration"}))
        self.assertEqual(points.state(self.d, "script"), "skipped")
        self.assertEqual(points.state(self.d, "voice"), "skipped")
        self.assertEqual(points.gate(self.d, "script"), [])

    def test_shots_gate_follows_tiers(self):
        why = points.checks_pass(self.d, "shots")
        self.assertTrue(any("plan check" in w for w in why))
        fp = tiers.fingerprint(self.d)
        for t in ("plan", "shots"):
            tiers.save_tier(self.d, t, tiers.result(t, [], {}, [], 0.0, fp))
        self.assertEqual(points.checks_pass(self.d, "shots"), [])
        self.assertEqual(points.approve(self.d, "shots")[0], 0)
        self.assertEqual(points.gate(self.d, "shots"), [])


if __name__ == "__main__":
    unittest.main()
