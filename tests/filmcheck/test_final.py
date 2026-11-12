"""Tier 4 and the publish pack with tier results (specs/020 T042, T043; US5; FR-017 – FR-019; SC-008)."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import publish, qc, tiers  # noqa: E402

import samples  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"
LIB = REPO / "lib" / "lemo-opuscar"
HAVE_PAGE = shutil.which("node") and (LIB / "node_modules" / "playwright-core").is_dir()


def plan_files(d: Path, cues, issues=()):
    """A tier-1 result and its input as `qc plan` writes them, for the current source."""
    fp = tiers.fingerprint(d)
    (d / ".check").mkdir(exist_ok=True)
    (d / ".check" / "plan-input.json").write_text(json.dumps({"fingerprint": fp, "dur": 20.0, "shots": None, "cues": cues,
                                                             "cues_from": "cues.json", "cards": [], "cards_from": "window.CARDS"}))
    tiers.save_tier(d, "plan", tiers.result("plan", list(issues), {}, [], 0.1, fp))


class Final(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TMP.mkdir(exist_ok=True)
        cls.root = Path(tempfile.mkdtemp(dir=TMP))

    def test_loudness_range_against_the_style(self):                  # FR-017
        d = samples.make_film(self.root, "lra")
        st = self.root / "my-styles" / "loud-style"
        st.mkdir(parents=True)
        (st / "qc.json").write_text(json.dumps({"loudness_range": [2.4, 3.3], "shot_max": 10}))
        (d / "TREATMENT.md").write_text("Style: loud-style\n")
        r = qc.measure(d)
        self.assertIsNotNone(r["measures"]["loudness_range"])
        self.assertEqual(len(r["warnings"]), 1)
        self.assertIn("loudness range", r["warnings"][0])
        self.assertTrue(r["pass"], r["problems"])                       # a warning does not fail the film

    def test_sound_longer_than_picture(self):
        d = samples.make_film(self.root, "avsync")
        mp4 = d / "avsync.mp4"
        dur = qc.probe_duration(mp4)
        tmp = d / "x.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp4), "-f", "lavfi", "-i",
                        f"sine=frequency=330:sample_rate=48000:duration={dur + 0.4}", "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", str(tmp)], check=True)
        tmp.replace(mp4)
        r = qc.measure(d)
        self.assertGreater(r["measures"]["av_sync"], 0.1)
        self.assertTrue(any("the sound lasts" in p for p in r["problems"]), r["problems"])

    def test_cuts_from_the_tier1_shot_list(self):
        d = samples.make_film(self.root, "plancuts")
        nar = json.loads((d / "narration.json").read_text())
        cuts = nar["cuts"]
        dur = qc.probe_duration(d / "plancuts.mp4")
        b = [0.0, *cuts[1:], dur]
        shots = [{"id": f"S{i}", "t0": x, "t1": y, "set": ""} for i, (x, y) in enumerate(zip(b, b[1:]))]
        fp = tiers.fingerprint(d)
        (d / ".check").mkdir(exist_ok=True)
        (d / ".check" / "plan-input.json").write_text(json.dumps({"fingerprint": fp, "dur": dur, "shots": shots, "cues": None}))
        r = qc.measure(d)
        self.assertEqual(r["measures"]["cuts_from"], "shot list (tier 1)")
        self.assertTrue(r["pass"], r["problems"])
        (d / "TREATMENT.md").write_text("Style: test-style\nchanged\n")      # stale input: not used
        self.assertNotEqual(qc.measure(d)["measures"]["cuts_from"], "shot list (tier 1)")


class PublishSubtitles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TMP.mkdir(exist_ok=True)
        cls.root = Path(tempfile.mkdtemp(dir=TMP))

    def test_the_films_own_passed_subtitles(self):                      # US5 AC2, FR-018
        d = samples.make_publish_film(self.root, "own")
        cues = [[0.5, 3.0, "Archaeologists found honey in an Egyptian tomb."], [3.0, 6.0, "It was old."]]
        plan_files(d, cues)
        got = publish.subtitle_cues(d)
        self.assertEqual([(c["start"], c["end"], " ".join(c["lines"])) for c in got], [tuple(c) for c in cues])

    def test_not_passed(self):
        d = samples.make_publish_film(self.root, "short-cue")
        bad = {"tier": "plan", "ref": "cue 1", "at": 0.5, "rule": "cue_short", "severity": "block", "measure": 0.8,
               "limit": 1.8, "text": "", "fix": "", "excepted": None}
        plan_files(d, [[0.5, 1.3, "Too short"]], [bad])
        with self.assertRaises(publish.SubtitlesNotPassed):
            publish.subtitle_cues(d)
        plan_files(d, [[0.5, 3.0, "Fine"]])
        (d / "index.html").write_text((d / "index.html").read_text() + "\n<!-- changed -->\n")   # older than the film
        with self.assertRaises(publish.SubtitlesNotPassed):
            publish.subtitle_cues(d)

    def test_old_film_keeps_the_old_way(self):
        d = samples.make_publish_film(self.root, "old")
        self.assertIsNone(tiers.load_tier(d, "plan"))
        self.assertTrue(publish.subtitle_cues(d))


@unittest.skipUnless(HAVE_PAGE and shutil.which("ffmpeg"), "needs node, the library and ffmpeg")
class CleanThumbnail(unittest.TestCase):
    """SC-008: the thumbnail has no subtitle and no card of the film; the page is told window.CLEAN."""

    def test_no_subtitle_in_the_thumbnail(self):
        TMP.mkdir(exist_ok=True)
        root = Path(tempfile.mkdtemp(dir=TMP))
        shots = [{"id": "A", "t0": 0, "t1": 6, "look": "cardbg"}]
        d = samples.make_tier_film(root, "clean", shots=shots, cues=[[0.0, 6.0, "A WHITE SUBTITLE LINE"]],
                                   cards=[{"id": "c", "t0": 0.0, "t1": 6.0, "text": "A CARD", "pos": "bottom"}])
        out = d / "raw"
        out.mkdir()
        job = {"w": 640, "h": 360, "thumbs": [{"t": 3.0, "text": "TOP TEXT", "position": "top", "color": "#ffffff"}]}
        (out / "job.json").write_text(json.dumps(job))
        p = subprocess.run(["node", str(REPO / "tools/filmcheck/thumbs.mjs"), str(d), str(LIB), str(out / "job.json"), str(out)],
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(p.returncode, 0, p.stderr)
        f = subprocess.run(["ffmpeg", "-v", "error", "-i", str(out / "raw-1.png"), "-vf",
                            "crop=iw:ih*0.3:0:ih*0.7,signalstats,metadata=print:key=lavfi.signalstats.YMAX:file=-",
                            "-f", "null", "-"], capture_output=True, text=True)
        ymax = int(re.findall(r"YMAX=(\d+)", f.stdout)[-1])
        self.assertLess(ymax, 60, "white subtitle or card pixels in the bottom of the thumbnail")


if __name__ == "__main__":
    unittest.main()
