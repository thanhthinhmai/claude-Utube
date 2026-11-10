"""The film QC (specs/010 T021–T025; FR-011, FR-012, SC-003, SC-006)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import qc  # noqa: E402

import samples  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"
L = samples.layout()


def end(line):
    return line["at"] + line["words"][-1][2]


BAD = {   # change → (measure that must fail, the second it must point at)
    "silence_ratio": ({"word": 0.2, "gap": 0.2}, None),
    "long_pauses_bad": ({"pause_in_p01": 0.85}, round(end(L[0]), 2)),
    "cuts_bad": ({"move_cut": (1, round((L[1]["at"] + end(L[1])) / 2, 2))}, round((L[1]["at"] + end(L[1])) / 2, 2)),
    "key_shots_bad": ({"extra_cuts": (round(end(L[4]) + 0.44, 2),), "tail": 0.8}, None),
    "tail_s": ({"tail": 3.0}, None),
    "stills_bad": ({"still_shot": 1}, round(end(L[1]) + 0.5, 2)),
}


class Measures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TMP.mkdir(exist_ok=True)
        cls.root = Path(tempfile.mkdtemp(dir=TMP))

    def test_good_film_has_no_problem(self):
        r = qc.measure(samples.make_film(self.root, "good"))
        self.assertEqual(r["problems"], [])
        self.assertTrue(r["pass"])
        self.assertLessEqual(r["measures"]["silence_ratio"], 0.20)

    def test_each_bad_film_fails_one_measure(self):         # SC-003
        for key, (change, at) in BAD.items():
            r = qc.measure(samples.make_film(self.root, key.replace("_", "-"), **change))
            self.assertEqual(len(r["problems"]), 1, (key, r["problems"]))
            m = r["measures"][key]
            if key == "silence_ratio":
                self.assertGreater(m, 0.20)
            elif key == "tail_s":
                self.assertAlmostEqual(m, 3.0, delta=0.1)
            else:
                self.assertEqual(len(m), 1, (key, m))
            if at is not None:
                got = m[0].get("at", m[0].get("from"))
                self.assertAlmostEqual(got, at, delta=0.1, msg=key)

    def test_cuts_found_from_the_picture(self):
        r = qc.measure(samples.make_film(self.root, "nocuts", write_cuts=False))
        want = [round(end(L[1]) + 0.5, 2), round(end(L[3]) + 0.5, 2)]
        self.assertEqual(len(r["measures"]["cuts"]), 2, r["measures"]["cuts"])
        for got, w in zip(r["measures"]["cuts"], want):
            self.assertAlmostEqual(got, w, delta=0.1)
        self.assertTrue(r["pass"], r["problems"])

    def test_film_without_narration(self):
        d = samples.make_film(self.root, "silent", still_shot=1)
        (d / "narration.json").unlink()
        shutil.rmtree(d / "voices")
        r = qc.measure(d)
        self.assertFalse(r["narration"])
        self.assertNotIn("silence_ratio", r["measures"])
        self.assertEqual(len(r["measures"]["stills_bad"]), 1)

    def test_style_may_allow_longer_stills(self):
        d = samples.make_film(self.root, "calm", still_shot=1)
        (d / "TREATMENT.md").write_text("Style: calm-style\n")
        (self.root / "my-styles" / "calm-style").mkdir(parents=True)
        (self.root / "my-styles" / "calm-style" / "qc.json").write_text(json.dumps({"still_max": 10}))
        self.assertEqual(qc.measure(d)["measures"]["stills_bad"], [])

    def test_voice_must_say_the_script(self):                 # US1/AC6, T035
        r = qc.measure(samples.make_film(self.root, "said", script=True))
        self.assertTrue(r["measures"]["voice_matches_script"], r["problems"])
        self.assertEqual(r["problems"], [])
        r = qc.measure(samples.make_film(self.root, "unsaid", script=True, lines_text={"l03": "w0 w1 other words."}))
        self.assertFalse(r["measures"]["voice_matches_script"])
        self.assertEqual(len(r["problems"]), 1)
        self.assertIn("from P02", r["problems"][0])
        d = samples.make_film(self.root, "nolines", script=True)
        n = json.loads((d / "narration.json").read_text())
        del n["lines_file"]
        (d / "narration.json").write_text(json.dumps(n))
        self.assertIn("no lines_file", qc.measure(d)["problems"][0])

    def test_line_shorter_than_its_audio(self):              # research R5, T037: both ways
        d = samples.make_film(self.root, "short")
        durs = json.loads((d / "voices" / "dur.json").read_text())
        durs["l02"] = durs["l02"] + 0.8
        (d / "voices" / "dur.json").write_text(json.dumps(durs))
        with self.assertRaises(qc.QcError):
            qc.measure(d)

    def test_voice_files_must_match(self):
        d = samples.make_film(self.root, "mismatch")
        (d / "voices" / "dur.json").write_text(json.dumps({"l01": 0.5}))
        with self.assertRaises(qc.QcError):
            qc.measure(d)

    @unittest.skipUnless(shutil.which("fc-list"), "needs fontconfig")
    def test_missing_glyph(self):
        # U+E000 (private use) counts as missing even where GNU Unifont "covers" it with a code box
        srt = "1\n00:00:01,000 --> 00:00:02,000\nHello \ue000 Xin chào\n"
        r = qc.measure(samples.make_film(self.root, "glyph", srt=srt))
        self.assertEqual([g["codepoint"] for g in r["measures"]["missing_glyphs"]], ["U+E000"])
        self.assertEqual(len(r["problems"]), 1)
        self.assertFalse(r["measures"]["texts_checked"])          # no window.TEXTS: only the subtitles

    def test_sc006_one_minute_film_under_a_minute(self):
        d = self.root / "films" / "minute"
        d.mkdir(parents=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1280x720:r=24:d=60",
                        "-f", "lavfi", "-i", "sine=duration=60", "-c:v", "libx264", "-preset", "ultrafast",
                        "-shortest", str(d / "minute.mp4")], check=True)
        t = time.time()
        qc.measure(d)
        self.assertLess(time.time() - t, 60)


class Command(unittest.TestCase):
    def test_exit_codes_and_report(self):
        TMP.mkdir(exist_ok=True)
        root = Path(tempfile.mkdtemp(dir=TMP))
        env = {**os.environ, "STUDIO_ROOT": str(root)}
        good = samples.make_film(root, "good")
        bad = samples.make_film(root, "late", tail=3.0)
        run = lambda name: subprocess.run(["sh", str(REPO / "bin/studio"), "qc", name], env=env, cwd=root,  # noqa: E731
                                          capture_output=True, text=True)
        self.assertEqual(run("good").returncode, 0)
        p = run("late")
        self.assertEqual(p.returncode, 1)
        self.assertIn("after the last word", p.stdout)
        data = json.loads((bad / "checks.json").read_text())
        self.assertFalse(data["film"]["pass"])
        self.assertRegex((bad / "CHECKS.md").read_text(), r"\| tail_s \| (2\.9|3\.0)")
        (good / "good.mp4").unlink()
        self.assertEqual(run("good").returncode, 2)


if __name__ == "__main__":
    unittest.main()
