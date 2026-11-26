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

FIT = {"S1": 69, "S2": 103, "S3": 68, "S4": 38, "S5": 45, "S6": 99, "S7": 119, "S8": 93, "S9": 55}


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



class Fit(Base):
    """T026–T028: suggestions, accept, skip, undo, motions (R3, R5)."""

    def setUp(self):
        super().setUp()
        timing.start(self.d)

    def test_suggestions(self):
        f = {x["shot"]: x for x in animatic.fit(self.d)}
        self.assertEqual({s: x["frames_new"] for s, x in f.items()}, FIT)
        self.assertEqual(f["S1"]["head"], 0)                                # the film's first shot keeps its head
        self.assertGreater(f["S3"]["head"], 0.3)
        self.assertTrue(all(x["state"] == "new" for x in f.values()))

    def test_accept_all_brings_silence_under_the_limit(self):
        self.assertGreater(animatic.silence(self.d), rhythm.SILENCE_MAX)
        r = animatic.accept(self.d, "all", by="test")
        self.assertEqual(sorted(r["accepted"]), sorted(FIT))
        self.assertLessEqual(r["silence"], rhythm.SILENCE_MAX)
        self.assertEqual(timing.load(self.d)["frames"], FIT)
        self.assertEqual(animatic.fit(self.d), [])                          # nothing left to suggest
        doc = timing.load(self.d)
        self.assertEqual(len(doc["history"]), 1)                            # one Undo gives it all back
        for r in timing.lines(self.d, doc):                                  # every line still in its own shot
            b = next(x for x in timing.bounds(doc, exact=True) if x["id"] == r["shot"])
            self.assertGreaterEqual(r["first_word_at"] + 1e-3, b["t0"])
            self.assertLessEqual(r["last_word_end"], b["t1"] + 1e-3)

    def test_skip_hides_until_the_shot_changes(self):
        animatic.skip(self.d, "S9")
        self.assertNotIn("S9", [x["shot"] for x in animatic.fit(self.d)])
        self.assertEqual([x["state"] for x in animatic.fit(self.d, all_states=True) if x["shot"] == "S9"], ["skipped"])
        timing.shift(self.d, {"S9": 100})                                    # the shot changed: its suggestion is back
        self.assertIn("S9", [x["shot"] for x in animatic.fit(self.d)])
        with self.assertRaises(animatic.AnimaticError) as e:
            animatic.skip(self.d, "S99")
        self.assertEqual(e.exception.exit_code(), 1)

    def test_undo_gives_back_the_exact_bytes(self):
        before = {n: (self.d / n).read_bytes() for n in ("timing.json", "narration.json")}
        self.assertFalse(animatic.can_undo(self.d))
        animatic.accept(self.d, ["S2", "S5"])
        self.assertTrue(animatic.can_undo(self.d))
        self.assertNotEqual((self.d / "narration.json").read_bytes(), before["narration.json"])
        animatic.undo(self.d)
        self.assertEqual({n: (self.d / n).read_bytes() for n in before}, before)
        with self.assertRaises(animatic.AnimaticError) as e:                 # at the origin: nothing to undo
            animatic.undo(self.d)
        self.assertEqual((e.exception.code, e.exception.exit_code()), ("origin", 1))

    def test_stale_base_is_refused(self):
        base = timing.base(self.d)
        timing.shift(self.d, {"S1": 80})
        for go in (lambda: animatic.accept(self.d, ["S2"], expect=base), lambda: animatic.skip(self.d, "S2", expect=base),
                   lambda: animatic.undo(self.d, expect=base)):
            with self.assertRaises(animatic.AnimaticError) as e:
                go()
            self.assertEqual(e.exception.exit_code(), 4)
        animatic.accept(self.d, ["S2"], expect=timing.base(self.d))

    def test_motions(self):
        keys = [{"layer": "Hero", "prop": "Position", "t0": 0.2, "t1": 1.0},     # inside: kept
                {"layer": "Hero", "prop": "Scale", "t0": 0.5, "t1": 2.0},        # 1.5 s into 1.0 s: squeeze ×1.5
                {"layer": "Bg", "prop": "Opacity", "t0": 1.4, "t1": 3.0},        # 1.6 s into 0.1 s: clip
                {"layer": "Bg", "prop": "Rotation", "t0": 1.6, "t1": 2.0}]       # starts after the end: drop
        m = {x["prop"]: x for x in animatic.motions(keys, 1.5)}
        self.assertNotIn("Position", m)
        self.assertEqual((m["Scale"]["effect"], m["Scale"]["ratio"]), ("squeeze", 1.5))
        self.assertEqual(m["Opacity"]["effect"], "clip")
        self.assertEqual(m["Rotation"]["effect"], "drop")
        (self.d / "animatic").mkdir(exist_ok=True)
        (self.d / "animatic" / "keys.json").write_text(json.dumps({"S5": keys}))
        s5 = next(x for x in animatic.fit(self.d) if x["shot"] == "S5")
        self.assertTrue(s5["motions"])                                       # S5 gets 1.1 s shorter

    def test_cli(self):
        def run(*a):
            return subprocess.run(["sh", str(REPO / "bin" / "studio"), "animatic", *a, str(self.d)] if not a[1:] else
                                  ["sh", str(REPO / "bin" / "studio"), "animatic", a[0], str(self.d), *a[1:]],
                                  capture_output=True, text=True)
        r = run("accept", "--all")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("silence 19% (limit 20%)", r.stdout)
        v = json.loads(run("status", "--json").stdout)
        self.assertEqual((v["fit"], v["can_undo"]), ([], True))
        self.assertEqual(run("undo", "--base", "0" * 16).returncode, 4)
        self.assertEqual(run("undo").returncode, 0)
        self.assertEqual(run("undo").returncode, 1)


if __name__ == "__main__":
    unittest.main()
