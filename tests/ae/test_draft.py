"""specs/035 T016, T029: `ae draft` with the fake AE: quarter-size draft with the voice from narration.json, one clip and
one picture per shot, draft.json, one previous draft kept; a rebuild of some shots keeps the other shots' frames."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests" / "filmcheck"))

import animfilm  # noqa: E402
from ae import splice  # noqa: E402


def probe(video) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,nb_frames:format=duration",
                        "-of", "json", str(video)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def level(video, t0, t1) -> float:
    """Mean volume (dB) of the audio between t0 and t1."""
    r = subprocess.run(["ffmpeg", "-v", "info", "-ss", str(t0), "-t", str(t1 - t0), "-i", str(video), "-af", "volumedetect",
                        "-f", "null", "-"], capture_output=True, text=True)
    line = [x for x in r.stderr.splitlines() if "mean_volume" in x]
    return float(line[-1].split("mean_volume:")[1].split()[0]) if line else -99.0


def framemd5(video, f0, f1) -> list:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"trim=start_frame={f0}:end_frame={f1},setpts=PTS-STARTPTS",
                        "-an", "-f", "framemd5", "-"], capture_output=True, text=True, check=True)
    return [x.split(",")[-1].strip() for x in r.stdout.splitlines() if x and not x.startswith("#")]


class Draft(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = {**os.environ, "STUDIO_AE_CONFIG": str(self.tmp / "ae.json"), "STUDIO_AE_WORK": str(self.tmp / "w"),
                    "STUDIO_ROOT": str(self.tmp / "root"), "STUDIO_AE_FAKE": "1"}
        for k in ("STUDIO_JOB", "STUDIO_PROXY"):
            self.env.pop(k, None)
        self.d = animfilm.make(self.tmp / "root" / "films" / "f1", wavs=True, tones=True)

    def ae(self, *args):
        return subprocess.run(["sh", str(ROOT / "bin" / "studio"), "ae", *args], capture_output=True, text=True,
                              env=self.env, timeout=300)

    def test_whole_draft(self):
        r = self.ae("draft", "f1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("draft: ", r.stdout.splitlines()[-1])
        self.assertIn("silence 33% (limit 20%)", r.stdout)
        a = self.d / "animatic"
        p = probe(a / "draft.mp4")
        v = next(s for s in p["streams"] if s["codec_type"] == "video")
        self.assertEqual((v["width"], v["height"]), (480, 270))
        self.assertTrue(any(s["codec_type"] == "audio" for s in p["streams"]))
        self.assertAlmostEqual(float(p["format"]["duration"]), 28.567, delta=0.1)
        self.assertGreater(level(a / "draft.mp4", 2.70, 3.50), -40)          # l02 speaks from 2.65 s
        self.assertLess(level(a / "draft.mp4", 6.10, 6.70), -60)             # the gap after l03 is silent
        info = json.loads((a / "draft.json").read_text())
        self.assertEqual(info["frames"]["S2"], 117)
        self.assertEqual(int(v["nb_frames"]), sum(info["frames"].values()))   # every frame, none cut by the sound
        self.assertEqual(set(info["steps"]), {"ae", "segments", "join", "voice", "mux", "cut"})
        for k in ("narration_sha", "built_at", "shots_built", "seconds", "fps", "size"):
            self.assertIn(k, info)
        self.assertEqual(len(list((a / "clips").glob("S*.mp4"))), 9)
        self.assertEqual(int(probe(a / "clips" / "S2.mp4")["streams"][0]["nb_frames"]), 117)
        jpgs = list((a / "frames").glob("S*.jpg"))
        self.assertEqual(len(jpgs), 9)
        self.assertTrue(all(j.stat().st_size <= 60 * 1024 for j in jpgs))
        self.assertEqual(json.loads((a / "keys.json").read_text())["S2"][0]["prop"], "Position")
        r = self.ae("draft", "f1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((a / "draft.prev.mp4").is_file())
        self.assertEqual(len(list(a.glob("draft*.mp4"))), 2)                  # exactly one previous draft

    def test_voice_not_approved(self):
        from filmcheck import points
        points.set_on(self.d, ["script", "voice", "cast", "animatic"])
        r = self.ae("draft", "f1")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("approve the voice first", r.stderr)

    def test_render_waits_for_the_animatic(self):
        r = self.ae("render", "f1")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("point approve f1 animatic", r.stderr)

    def test_rebuild_some_shots_keeps_the_others(self):
        self.assertEqual(self.ae("draft", "f1").returncode, 0)
        a = self.d / "animatic"
        before = {"S1": framemd5(a / "draft.mp4", 0, 75), "S9": framemd5(a / "draft.mp4", 767, 857)}
        from filmcheck import timing
        timing.shift(self.d, {"S2": 84})                                       # S2 shorter: every later shot moves
        r = self.ae("draft", "f1", "--shots", "S5")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        info = json.loads((a / "draft.json").read_text())
        self.assertEqual(info["shots_built"], ["S2", "S5"])                    # S2 changed length: rebuilt too (FR-016)
        self.assertEqual(framemd5(a / "draft.mp4", 0, 75), before["S1"])
        self.assertEqual(framemd5(a / "draft.mp4", 734, 824), before["S9"])    # same frames, 33 frames earlier
        self.assertEqual(int(probe(a / "clips" / "S2.mp4")["streams"][0]["nb_frames"]), 84)

    def test_by_shot_needs_every_segment(self):
        with self.assertRaises(splice.SpliceError) as e:
            splice.by_shot([("S1", self.tmp / "gone.mp4")], self.tmp / "o.mp4")
        self.assertIn("S1", str(e.exception))


if __name__ == "__main__":
    unittest.main()
