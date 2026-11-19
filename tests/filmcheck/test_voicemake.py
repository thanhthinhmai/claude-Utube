"""specs/023 T050: voice make writes the say spellings for the voice, the script stays; mispronounced words are named."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import cli, voicecheck  # noqa: E402


class VoiceMake(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="vm."))
        self.d = self.root / "films" / "demo"
        self.d.mkdir(parents=True)
        (self.d / "lines.json").write_text(json.dumps([
            {"id": "l1", "text": "It does not hurt.", "say": "It does not hert.", "voice": "am_michael", "speed": 1.1},
            {"id": "l2", "text": "Sixteen thousand words.", "voice": "am_michael", "speed": 1.1}]))

    def test_say_file(self):
        f = cli.say_file(self.d)
        rows = json.loads(f.read_text())
        self.assertEqual(rows[0]["text"], "It does not hert.")
        self.assertNotIn("say", rows[0])
        self.assertEqual(rows[1]["text"], "Sixteen thousand words.")
        self.assertEqual(json.loads((self.d / "lines.json").read_text())[0]["text"], "It does not hurt.")   # the script stays

    def test_command_runs_the_library_tts_on_the_say_file(self):
        r = subprocess.run(["sh", str(REPO / "bin" / "studio"), "voice", "make", "demo"], capture_output=True, text=True,
                           env={**os.environ, "STUDIO_ROOT": str(self.root), "STUDIO_TTS_DRY": "1"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("core/tts/tts.py", r.stdout)
        self.assertIn("voices/.say.json", r.stdout)
        self.assertIn("l1", r.stdout)

    def test_script_review_gate(self):                            # specs/026 T019
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import samples
        from filmcheck import points, report
        d = samples.review_film(self.root, "night", kit=False)
        env = {**os.environ, "STUDIO_ROOT": str(self.root), "STUDIO_TTS_DRY": "1"}
        run = lambda *x: subprocess.run(["sh", str(REPO / "bin" / "studio"), "voice", "make", "night", *x],   # noqa: E731
                                        capture_output=True, text=True, env=env)
        r = run()
        self.assertEqual(r.returncode, 1)
        self.assertIn("point approve night script", r.stderr)
        r = run("--skip-review", "a quick test")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(report.load(d)["reviews"]["skipped"]["script"]["reason"], "a quick test")
        p = d / "SCRIPT.md"
        p.write_text(p.read_text().replace("eleven days", "eleven whole days"))     # the skip was for the old script
        self.assertEqual(run().returncode, 1)
        points.set_on(d, "shots")                                   # script review off: no gate
        self.assertEqual(run().returncode, 0)
        points.set_on(d, "script,shots")
        p.write_text(p.read_text().replace("eleven whole days", "eleven days"))
        self.assertEqual(points.approve(d, "script")[0], 0)
        self.assertEqual(run().returncode, 0)

    def test_misheard(self):
        self.assertEqual(voicecheck.misheard("It does not hurt.", "It does not hut."), [("hurt", "hut")])
        self.assertEqual(voicecheck.misheard("Sixteen thousand words.", "16,000 words."), [])
        self.assertEqual(voicecheck.misheard("A café.", "A cafe."), [])


if __name__ == "__main__":
    unittest.main()
