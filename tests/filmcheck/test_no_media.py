"""specs/037 T049 (SC-005): no sound files in git (the test library is made up while a test runs), the reference audio,
the sound library and a film's sound copies stay out of git, and the desktop core does not install the sound learning
tools (torch, demucs, transformers) or carry a sound library."""
import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AUDIO = re.compile(r"\.(wav|mp3|flac|ogg|oga|opus|aif|aiff|aifc|m4a|wma|caf)$", re.I)


def git(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)


@unittest.skipUnless((REPO / ".git").exists(), "needs the git checkout")
class NoMedia(unittest.TestCase):
    def test_no_sound_file_is_tracked(self):
        files = git("ls-files").stdout.splitlines()
        self.assertTrue(files)
        self.assertEqual([f for f in files if AUDIO.search(f)], [])

    def test_sound_places_are_ignored(self):
        for p in ("references/voice-check/a.wav", "films/f1/sound/cache/s_0123456789ab.wav", "films/f1/out/mix.wav",
                  "films/f1/sound/stems/fx.wav", ".env"):
            self.assertEqual(git("check-ignore", "-q", "--no-index", p).returncode, 0, f"{p} is not ignored")

    def test_core_does_not_install_sound_learning(self):
        docker = (REPO / "deploy" / "core.Dockerfile").read_text(encoding="utf-8")
        self.assertNotRegex(docker, r"deps\s+[^\n&]*\bsound\b")
        self.assertNotIn("requirements-sound", docker.replace("tools/requirements-*.txt", ""))
        studio = (REPO / "bin" / "studio").read_text(encoding="utf-8")
        setup = studio[studio.index("cmd_setup() {"):]
        setup = setup[:setup.index("\n}\n")]
        self.assertNotRegex(setup, r"deps_tiers\s+sound|deps\s+sound|requirements-sound")

    def test_core_carries_no_sound_library(self):
        docker = (REPO / "deploy" / "core.Dockerfile").read_text(encoding="utf-8")
        for word in ("SoundLibrary", "Sonniss", "freesound", "/sound/"):
            self.assertNotIn(word, docker)


if __name__ == "__main__":
    unittest.main()
