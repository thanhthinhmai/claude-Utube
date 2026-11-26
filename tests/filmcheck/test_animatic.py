"""specs/035: the Animatic of an AE film: timeline, silence measured as the film check does, the animatic review point
(approve anyway, the final render gate), per-shot fit suggestions, accept/skip/undo, motions cut or squeezed."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(HERE))

import animfilm  # noqa: E402
from filmcheck import animatic, points, qc, rhythm, timing  # noqa: E402

FIT = {"S1": 69, "S2": 103, "S3": 68, "S4": 38, "S5": 45, "S6": 99, "S7": 119, "S8": 93, "S9": 56}


class Base(unittest.TestCase):
    wavs = False

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = animfilm.make(Path(self.tmp.name) / "f1", wavs=self.wavs)

    def tearDown(self):
        self.tmp.cleanup()


class Timeline(Base):
    def test_timeline(self):
        t = animatic.timeline(self.d)
        self.assertEqual([s["id"] for s in t["shots"]], [f"S{i}" for i in range(1, 10)])
        self.assertEqual(sum(len(s["lines"]) for s in t["shots"]), 14)
        self.assertAlmostEqual(t["duration"], 28.5667, places=3)
        s2 = t["shots"][1]
        self.assertEqual(([x["id"] for x in s2["lines"]], s2["frames"]), (["l02", "l03"], 117))
        self.assertTrue(s2["lines"][0]["text"])

    def test_silence_is_the_film_checks(self):
        nar = qc.load_narration(self.d)
        doc = timing.load(self.d)
        m, _, _ = qc.narration_measures(nar, timing.duration(doc), None, qc.line_texts(self.d, nar),
                                        shots=timing.bounds(doc))
        self.assertEqual(animatic.silence(self.d), m["silence_ratio"])                # R4, SC-003
        self.assertAlmostEqual(animatic.silence(self.d), 0.329, places=3)
        self.assertGreater(animatic.silence(self.d), rhythm.SILENCE_MAX)
        gaps = animatic.longest_gaps(self.d)
        self.assertEqual(len(gaps), 3)
        self.assertEqual((gaps[0]["shot"], gaps[0]["length"]), ("S5", 1.59))
        self.assertGreaterEqual(gaps[0]["length"], gaps[1]["length"])

    def test_no_timing(self):
        timing.path(self.d).unlink()
        with self.assertRaises(animatic.AnimaticError) as e:
            animatic.timeline(self.d)
        self.assertEqual(e.exception.code, "missing")


class Point(Base):
    wavs = True

    def test_reached_after_the_voice(self):
        self.assertEqual(points.state(self.d, "voice"), "off")                           # AE films: voice off by default
        self.assertEqual(points.state(self.d, "animatic"), "ready")
        self.assertEqual(points.state(self.d, "shots"), "skipped")                        # R10
        self.assertIn("animatic", points.load(self.d)["on"])
        for w in (self.d / "voices").glob("*.wav"):
            w.unlink()
        self.assertEqual(points.state(self.d, "animatic"), "not_reached")

    def test_approve_needs_a_draft_and_anyway(self):
        code, why = points.approve(self.d, "animatic")
        self.assertEqual(code, 1)
        self.assertIn("ae draft", why[0])
        self.assertTrue(points.gate(self.d, "animatic"))                                  # FR-003
        animfilm.fake_draft(self.d)
        code, why = points.approve(self.d, "animatic")
        self.assertEqual((code, why), (1, ["silence 33% > 20%: approve anyway?"]))
        code, why = points.approve(self.d, "animatic", anyway=True, source="ui", by="owner")
        self.assertEqual((code, why), (0, []))
        a = points.load(self.d)["approved"]["animatic"]
        self.assertEqual((a["anyway"], a["silence"], a["source"]), (True, 0.329, "ui"))
        self.assertEqual(points.gate(self.d, "animatic"), [])
        timing.shift(self.d, {"S2": 100})                                                 # R11: lengths change
        self.assertEqual(points.state(self.d, "animatic"), "stale")
        self.assertTrue(points.gate(self.d, "animatic"))

    def test_open_note_blocks(self):
        animfilm.fake_draft(self.d)
        (self.d / "animatic" / "notes.json").write_text(json.dumps(
            {"version": 1, "shots": {"S2": [{"id": "n1", "text": "faster", "state": "open"}]}}))
        code, why = points.approve(self.d, "animatic", anyway=True)
        self.assertEqual((code, why), (1, ["S2: 1 open note(s)"]))

    def test_cli_anyway(self):
        animfilm.fake_draft(self.d)

        def cli(*a, env=None):
            e = {k: v for k, v in os.environ.items() if k != "STUDIO_JOB"}
            e.update(env or {})
            return subprocess.run(["sh", str(REPO / "bin" / "studio"), "point", "approve", str(self.d), "animatic", *a],
                                  capture_output=True, text=True, cwd=REPO, env=e)
        r = cli()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("approve anyway?", r.stdout + r.stderr)
        r = cli("--anyway", env={"STUDIO_JOB": "j1"})
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("only the owner can approve anyway, on the job page", r.stdout + r.stderr)
        self.assertNotIn("animatic", points.load(self.d)["approved"])
        r = cli("--anyway")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(points.load(self.d)["approved"]["animatic"]["anyway"])


if __name__ == "__main__":
    unittest.main()
