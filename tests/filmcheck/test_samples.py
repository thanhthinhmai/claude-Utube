"""The samples themselves (T003): good scripts have the length they claim, sample films have the cuts, length and
stills they were asked for. Later tests rely on this."""
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import samples

TMP = Path(__file__).resolve().parent / ".tmp"


def words(script):
    return sum(len(re.sub(r"^\[P\d+\]", "", ln).split()) for ln in script.splitlines() if ln.startswith("[P"))


def probe_duration(mp4):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


class Scripts(unittest.TestCase):
    def test_good_en_fits_its_target(self):
        n = words(samples.GOOD_EN)
        self.assertTrue(45 * 0.85 <= n / 150 * 60 <= 45 * 1.15, n)

    def test_every_bad_script_differs_from_the_good_one(self):
        for rule, (script, sources) in samples.BAD.items():
            self.assertNotEqual((script, sources), (samples.GOOD_EN, samples.GOOD_EN_SOURCES), rule)

    def test_long_script(self):
        s = samples.long_script(200)
        self.assertGreater(words(s) / 150 * 60, 150)


class Films(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(exist_ok=True)
        self.root = Path(tempfile.mkdtemp(dir=TMP))

    def test_good_film(self):
        d = samples.make_film(self.root, "good")
        narr = json.loads((d / "narration.json").read_text())
        last = narr["lines"][-1]
        words = json.loads((d / "voices/words.json").read_text())
        end = last["at"] + words[last["id"]][-1][2]
        self.assertAlmostEqual(probe_duration(d / "good.mp4"), end + 1.1, delta=0.1)
        self.assertEqual(len(narr["cuts"]), 3)

    def test_still_shot_has_its_length(self):
        d = samples.make_film(self.root, "still", still_shot=1)
        out = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-i", str(d / "still.mp4"), "-vf",
                              "freezedetect=n=0.003:d=6", "-map", "0:v", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        self.assertIn("freeze_duration", out)


if __name__ == "__main__":
    unittest.main()
