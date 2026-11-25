"""specs/036 T042: the Voice step with speakers (local mode): speakers grouped, one picker for both providers, the
summary and the picker show the same narrator (FR-041), emotion "not applied", a line's tone saved from the page."""
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from helpers import REPO, Project, client

sys.path.insert(0, str(REPO / "tests" / "filmcheck"))
sys.path.insert(0, str(REPO / "tools"))
import samples  # noqa: E402

NODE_MODULES = REPO / "lib" / "lemo-opuscar" / "node_modules"


class VoiceCastPage(unittest.TestCase):
    def setUp(self):
        self.p = Project(ports="18870-18879")
        self.film = samples.review_film(self.p.dir, "night", kit=False)
        rows = json.loads((self.film / "lines.json").read_text())
        for r in rows:
            r.pop("voice", None)
        rows[1].update(speaker="kid", role="boy", emotion="whisper")
        (self.film / "lines.json").write_text(json.dumps(rows, indent=1))
        (self.film / "film.json").write_text(json.dumps({"narrator": {"mode": "own", "voice": "bm_george", "speed": 1.0}}))
        (self.film / "voices" / "speakers.json").write_text(json.dumps(
            {"emotions": {rows[1]["id"]: {"emotion": "whisper", "emotion_applied": False}}}))
        out = self.p.cli("job", "start", "--kind", "film", "--name", "night", "--film", "night")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.jid, self.url = out.stdout.splitlines()[:2]
        self.c = client()

    def tearDown(self):
        self.p.close()

    def test_steps_data(self):
        v = self.c.get(f"/api/v1/jobs/{self.jid}/steps").json()
        self.assertEqual(v["narrator_voice"], {"voice": "bm_george", "speed": 1.0})
        self.assertEqual(v["emotions"]["L02"]["emotion_applied"], False)
        self.assertEqual(sorted(s["id"] for s in v["speakers"]), ["kid", "narrator"])
        d = self.c.get(f"/api/v1/jobs/{self.jid}/done").json()
        self.assertEqual(d["sections"]["voice"]["voice"], "bm_george")        # FR-041: the same narrator

    @unittest.skipUnless(shutil.which("node") and (NODE_MODULES / "playwright-core").is_dir(), "no node / playwright-core")
    def test_in_browser(self):
        summary = self.p.dir / "s.md"
        summary.write_text("Voice ready")
        self.p.cli("review", "request", self.jid, "--kind", "voice", "--film", "night", "--summary", str(summary))
        base = self.url.split("URL: ", 1)[1].split("/#", 1)[0]
        r = subprocess.run(["node", str(Path(__file__).with_name("browser_voice_cast.cjs")), base, self.jid],
                           capture_output=True, text=True, timeout=120, env={**os.environ, "NODE_PATH": str(NODE_MODULES)})
        if r.returncode == 77:
            self.skipTest("no browser")
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(o["errors"], [])
        self.assertEqual(sorted(o["speakers"]), ["kid", "narrator"])
        self.assertIn("Kokoro (free, on this machine)", o["groups"])
        self.assertEqual(o["picker"], "bm_george")
        self.assertIn("bm_george", o["facts"])
        self.assertEqual(o["notApplied"], 1)
        self.assertEqual(o["tones"], len(json.loads((self.film / "lines.json").read_text())))
        self.assertTrue(o["toneLogged"])
        self.assertEqual(json.loads((self.film / "lines.json").read_text())[2].get("fx"), "phone")


if __name__ == "__main__":
    unittest.main()
