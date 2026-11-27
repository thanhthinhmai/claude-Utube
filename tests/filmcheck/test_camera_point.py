"""The Camera review point (specs/039 T028): order, on by default for AE films, skipped without a camera library,
approve refused while a still or a note is missing, a new choice → review again, retime keeps the fingerprint,
voice make blocked then let through."""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from filmcheck import camnotes, camsuggest, points, steps  # noqa: E402
import test_camsuggest as ts  # noqa: E402


def stills(d: Path):
    """A still file for every option, as `camera stills` would write."""
    o = camsuggest.load(d)
    (d / "camera" / "stills").mkdir(parents=True, exist_ok=True)
    for s, row in o["shots"].items():
        for x in row["options"]:
            rel = f"camera/stills/{s}-o{x['n']}.jpg"
            (d / rel).write_bytes(b"jpg")
            x["still"] = rel
    (d / "camera" / "options.json").write_bytes(camsuggest._dump(o))


class CameraPoint(ts.Base):
    def setUp(self):
        super().setUp()
        self.d = ts.make_film(self.root, plan=ts.PLAN)

    def test_order_and_step(self):
        self.assertEqual(points.POINTS.index("camera"), points.POINTS.index("cast") + 1)
        self.assertLess(points.POINTS.index("camera"), points.POINTS.index("voice"))
        self.assertIn("camera", points.AE_ON)
        names = [s["name"] for s in steps.status(self.d)]
        self.assertEqual(names.index("Camera"), names.index("Cast") + 1)

    def test_on_by_default_and_not_reached_blocks(self):
        self.assertIsNone(points.skip_reason(self.d, "camera"))
        self.assertEqual(points.state(self.d, "camera"), "not_reached")
        why = points.gate(self.d, "camera")
        self.assertTrue(why and "camera suggest" in why[0])

    def test_skipped_without_library(self):
        (self.root / "my-styles" / "camstyle" / "camera.json").unlink()
        self.assertIn("no camera library", points.skip_reason(self.d, "camera"))
        self.assertEqual(points.gate(self.d, "camera"), [])

    def test_page_film_skipped(self):
        d = ts.make_film(self.root, name="pg", page=True)
        self.assertEqual(points.skip_reason(d, "camera"), "not an After Effects film")

    def test_approve_refused_without_stills_then_ok(self):
        camsuggest.suggest(self.d)
        self.assertFalse(points.reached(self.d, "camera"))
        stills(self.d)
        self.assertTrue(points.reached(self.d, "camera"))
        self.assertEqual(points.state(self.d, "camera"), "ready")
        code, _ = points.approve(self.d, "camera", source="chat")
        self.assertEqual(code, 0)
        plan = json.loads((self.d / "film.json").read_text())["shot_plan"]
        self.assertTrue(all("camera" in plan[s] for s in ("S1", "S2", "S3")))      # ★ taken for untouched shots
        self.assertEqual(points.gate(self.d, "camera"), [])

    def test_open_note_blocks_approve(self):
        camsuggest.suggest(self.d)
        stills(self.d)
        camnotes.add(self.d, "S2", 1, 0.5, 0.5, "less zoom")
        code, why = points.approve(self.d, "camera", source="chat")
        self.assertEqual(code, 1)
        self.assertTrue(any("S2" in w and "note" in w for w in why))

    def test_new_choice_is_stale_and_retime_is_not(self):
        camsuggest.suggest(self.d)
        stills(self.d)
        self.assertEqual(points.approve(self.d, "camera", source="chat")[0], 0)
        fp = points.fingerprint(self.d, "camera")
        (self.d / "timing.json").write_text(json.dumps({"version": 1, "fps": 30, "frames": {"S1": 120, "S2": 90, "S3": 60}}))
        ch = camsuggest.retime(self.d)
        self.assertEqual([c["shot"] for c in ch], ["S1"])
        self.assertEqual(points.fingerprint(self.d, "camera"), fp)
        self.assertEqual(points.state(self.d, "camera"), "approved")
        n2 = camsuggest.load(self.d)["shots"]["S1"]["options"][1]["n"]
        camsuggest.choose(self.d, "S1", n2)
        self.assertEqual(points.state(self.d, "camera"), "stale")

    def test_voice_make_blocked_then_runs(self):
        r = self.cli("voice-make", "f1")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("camera", r.stderr)
        camsuggest.suggest(self.d)
        stills(self.d)
        self.assertEqual(self.cli("point", "approve", "f1", "camera", "--source", "chat").returncode, 0)
        r = self.cli("voice-make", "f1")
        self.assertNotIn("camera", r.stderr)
        self.assertNotEqual(r.returncode, 1, r.stderr)              # past the gates: no lines.json → 2


if __name__ == "__main__":
    unittest.main()
