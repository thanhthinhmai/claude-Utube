"""The step graph and step states (specs/026 T005)."""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from filmcheck import steps, tiers  # noqa: E402
import samples  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"


class Steps(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(exist_ok=True)
        self.d = samples.review_film(Path(tempfile.mkdtemp(dir=TMP)), kit=False)

    def state(self, name, **kw):
        return next(s for s in steps.status(self.d, **kw) if s["name"] == name)

    def test_order_and_impact(self):
        self.assertEqual([s["name"] for s in steps.status(self.d)],
                         ["Treatment", "Script", "Voice", "Look", "Picture", "Shots", "Mix", "Render", "Self-check", "Publish"])
        self.assertEqual(steps.impact("script", self.d), ["Voice", "Picture", "Shots", "Mix", "Render", "Self-check", "Publish"])
        # specs/034, 035: without a film, every step of either kind of film
        self.assertEqual(steps.impact("script"), ["Cast", "Camera", "Voice", "Animatic", "Picture", "Shots", "Mix", "Render", "Self-check",
                                                  "Publish"])
        self.assertEqual(steps.impact("cast"), ["Camera", "Animatic", "Picture", "Shots", "Mix", "Render", "Self-check", "Publish"])
        self.assertEqual(steps.impact("voice"), ["Animatic", "Picture", "Shots", "Mix", "Render", "Self-check", "Publish"])
        self.assertEqual(steps.impact("voice", self.d), ["Picture", "Shots", "Mix", "Render", "Self-check", "Publish"])
        self.assertEqual(steps.impact("shots"), ["Render", "Self-check", "Publish"])
        self.assertEqual(steps.impact("mix"), ["Self-check", "Publish"])
        self.assertEqual(steps.impact("publish"), [])

    def test_voice_stale_when_script_changes(self):
        self.assertEqual(self.state("Voice")["state"], "done")
        p = self.d / "SCRIPT.md"
        p.write_text(p.read_text().replace("nothing happens", "the night goes on"))
        self.assertEqual(self.state("Voice")["state"], "stale")

    def test_voice_stale_when_a_file_is_missing(self):
        (self.d / "voices" / "L03.wav").unlink()
        v = self.state("Voice")
        self.assertEqual(v["state"], "stale")
        self.assertIn("1 line", v["note"])

    def test_shots_stale_with_old_fingerprint(self):
        self.assertEqual(self.state("Shots")["state"], "todo")
        tiers.save_tier(self.d, "shots", tiers.result("shots", [], {}, [], 0.0, tiers.fingerprint(self.d)))
        self.assertEqual(self.state("Shots")["state"], "done")
        (self.d / "index.html").write_text("<p>changed</p>")
        self.assertEqual(self.state("Shots")["state"], "stale")

    def test_mix_stale_when_older_than_mix_json(self):
        (self.d / "out").mkdir()
        mix = self.d / "out" / "mix.wav"
        samples._silent_wav(mix)
        old = time.time() - 100
        for w in (self.d / "voices").glob("*.wav"):
            os.utime(w, (old, old))
        os.utime(mix, (old + 10, old + 10))
        self.assertEqual(self.state("Mix")["state"], "done")
        (self.d / "mix.json").write_text(json.dumps({"music": "seed:2"}))
        self.assertEqual(self.state("Mix")["state"], "stale")

    def test_overlays(self):
        self.assertEqual(self.state("Script", pending={"script"})["state"], "waiting")
        self.assertEqual(self.state("Voice", busy={"step": "Voice"})["state"], "running")
        self.assertEqual(self.state("Voice")["note"], "Not reviewed")        # voice is off by default


class AeSteps(unittest.TestCase):
    """specs/035 T009: AE films show Script, Cast, Voice, Animatic, Sound, Final render; a voice, script or cast change
    makes the Animatic run again."""
    def setUp(self):
        import animfilm
        self.tmp = tempfile.TemporaryDirectory()
        self.d = animfilm.make(Path(self.tmp.name) / "f1", wavs=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_order_labels_and_impact(self):
        rail = steps.status(self.d)
        self.assertEqual([s["name"] for s in rail], ["Treatment", "Script", "Cast", "Camera", "Voice", "Animatic", "Mix", "Render",
                                                     "Self-check", "Publish"])
        self.assertEqual([s["label"] for s in rail][6:8], ["Sound", "Final render"])
        self.assertEqual(next(s for s in rail if s["name"] == "Animatic")["point"], "animatic")
        self.assertEqual(steps.impact("animatic", self.d), ["Mix", "Render", "Self-check", "Publish"])   # FR-004
        self.assertEqual(steps.impact("mix", self.d), ["Render", "Self-check", "Publish"])   # specs/037 FR-029
        self.assertEqual(steps.impact("mix"), ["Self-check", "Publish"])                     # web films: unchanged
        for p in ("script", "voice", "cast"):
            self.assertIn("Animatic", steps.impact(p, self.d))                                         # FR-005

    def test_sound_stale_when_the_animatic_or_plan_changes(self):
        """specs/037 T029 / FR-029: the Sound must run again after a new shot length or a plan edit, and its approval
        no longer holds."""
        import os
        import time as _t
        from filmcheck import points
        st = lambda: next(s for s in steps.status(self.d) if s["name"] == "Mix")["state"]      # noqa: E731
        (self.d / "out").mkdir(exist_ok=True)
        (self.d / "sound").mkdir(exist_ok=True)
        (self.d / "sound" / "plan.json").write_text('{"version": 1, "cues": []}')
        mix = self.d / "out" / "mix.wav"
        mix.write_bytes(b"RIFF")
        old = _t.time() - 100
        for f in [self.d / "mix.json", self.d / "narration.json", self.d / "timing.json", self.d / "sound" / "plan.json",
                  *(self.d / "voices").glob("*.wav")]:
            if f.exists():
                os.utime(f, (old, old))
        self.assertEqual(st(), "done")
        fp = points.fingerprint(self.d, "mix")
        for rel in ("timing.json", "sound/plan.json"):
            f = self.d / rel
            if not f.exists():
                f.write_text("{}")
            os.utime(f, None)
            self.assertEqual(st(), "stale", rel)
            os.utime(f, (old, old))
        t = self.d / "timing.json"
        t.write_text(t.read_text() + " ")
        self.assertNotEqual(points.fingerprint(self.d, "mix"), fp)

    def test_animatic_step_state(self):
        from filmcheck import animatic
        st = lambda: next(s for s in steps.status(self.d) if s["name"] == "Animatic")      # noqa: E731
        self.assertEqual(st()["state"], "todo")
        import animfilm
        animfilm.fake_draft(self.d)
        self.assertEqual(st()["state"], "done")
        p = self.d / "ae" / "shots.jsx"
        p.write_text("// changed\n")
        self.assertEqual((st()["state"], st()["note"]), ("stale", "the film's code changed"))
        animfilm.fake_draft(self.d)
        n = self.d / "narration.json"
        n.write_text(n.read_text().replace('"at": 0.3', '"at": 0.4'))
        self.assertEqual((st()["state"], st()["note"]), ("stale", "the voice changed"))
        self.assertFalse(animatic.draft_current(self.d))


if __name__ == "__main__":
    unittest.main()
