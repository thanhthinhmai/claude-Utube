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
        self.assertEqual(steps.impact("script"), ["Voice", "Picture", "Shots", "Mix", "Render", "Self-check", "Publish"])
        self.assertEqual(steps.impact("voice"), ["Picture", "Shots", "Mix", "Render", "Self-check", "Publish"])
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


if __name__ == "__main__":
    unittest.main()
