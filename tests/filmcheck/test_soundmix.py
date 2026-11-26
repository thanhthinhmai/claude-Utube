"""specs/037 T020: the mix from the plan: 48 kHz stereo, cut rules at the shot end, chosen silences, a change touches
only its own stretch, no sound from outside the library, and a CREDITS line per sound used."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(HERE))

import soundfilm  # noqa: E402
import soundfix  # noqa: E402
from filmcheck import soundlib, soundmix, soundplan  # noqa: E402

LIBPY = REPO / "lib" / "lemo-opuscar" / ".venv" / "bin" / "python"


def read(path):
    """(rate, channels, samples as a list of float rows) through the library's Python (numpy lives there)."""
    code = ("import sys,json,soundfile as sf; a,sr=sf.read(sys.argv[1],dtype='float32',always_2d=True); "
            "print(json.dumps([sr,a.shape[1],a.tolist()]))")
    out = subprocess.run([str(LIBPY), "-c", code, str(path)], capture_output=True, text=True, check=True).stdout
    sr, ch, a = json.loads(out)
    return sr, ch, a


def db(rows):
    import math
    peak = max((abs(v) for r in rows for v in r), default=0)
    return 20 * math.log10(peak) if peak > 0 else -200


@unittest.skipUnless(LIBPY.is_file(), "needs the library's venv")
class Mix(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"STUDIO_DATA": str(t / "data"), "STUDIO_ROOT": str(t / "repo"),
                                                "FREESOUND_API_KEY": ""})
        self.env.start()
        self.noenv = mock.patch("filmcheck.eleven.load_env", return_value={})
        self.noenv.start()
        (t / "repo" / "references").mkdir(parents=True)
        soundlib.add_root(soundfix.make(t / "Sonniss" / "GDC2024"))
        soundlib.index()
        self.d = soundfilm.make(t / "films" / "f1")
        self.t = t

    def tearDown(self):
        self.noenv.stop()
        self.env.stop()
        self.tmp.cleanup()

    def test_mix_cut_rules_and_credits(self):
        # S1 0–2 s; a 1.0 s crowd cheer starting at 1.5 s crosses the S1→S2 cut at 2.0 s
        hard = soundplan.add_cue(self.d, "S1", "people cheer", {"shot_at": 0.75}, "small crowd cheer", cut="hard", gain_db=0)
        soundplan.add_cue(self.d, "S3", "bubbles", {"span": "shot"}, "aquarium bubbles", gain_db=-6)
        r = soundmix.run(self.d, mux=False)
        self.assertEqual((r["placed"], r["dropped"], r["missing"]), (2, 0, 0))
        sr, ch, mix = read(self.d / "out" / "mix.wav")
        self.assertEqual((sr, ch, len(mix)), (48000, 2, 7 * 48000))
        _, _, fx = read(self.d / "sound" / "stems" / "fx.wav")
        cut = int(2.0 * sr)
        self.assertLess(db(fx[cut:cut + int(0.010 * sr)]), -60)                  # hard: silent right after the cut
        self.assertGreater(db(fx[int(1.6 * sr):int(1.9 * sr)]), -30)            # but heard before it
        text = (self.d / "CREDITS").read_text()
        block = text.split(soundmix.MARK_BEGIN)[1].split(soundmix.MARK_END)[0].strip().splitlines()
        self.assertEqual(len(block), 2)
        self.assertTrue(all("Sonniss GDC 202" in ln and "sonniss-gdc-2.0" in ln for ln in block), block)
        self.assertTrue(any("Small Crowd Cheer" in ln for ln in block))
        # the cheer fades instead: still heard 50 ms after the cut, gone after fade_s
        soundplan.set_cue(self.d, hard["id"], {"cut": "fade", "fade_s": 0.2})
        soundmix.run(self.d, mux=False)
        _, _, fx = read(self.d / "sound" / "stems" / "fx.wav")
        self.assertGreater(db(fx[cut + int(0.02 * sr):cut + int(0.06 * sr)]), -40)
        self.assertLess(db(fx[cut + int(0.21 * sr):cut + int(0.4 * sr)]), -60)
        soundplan.set_cue(self.d, hard["id"], {"cut": "over"})
        soundmix.run(self.d, mux=False)
        _, _, fx = read(self.d / "sound" / "stems" / "fx.wav")
        self.assertGreater(db(fx[cut + int(0.2 * sr):cut + int(0.4 * sr)]), -40)
        # CREDITS block replaced, not added again
        soundmix.run(self.d, mux=False)
        self.assertEqual((self.d / "CREDITS").read_text().count(soundmix.MARK_BEGIN), 1)

    def test_a_change_touches_only_its_stretch(self):
        a = soundplan.add_cue(self.d, "S1", "pop", {"shot_at": 0.25}, "cork pop", gain_db=0)
        b = soundplan.add_cue(self.d, "S3", "ball", {"shot_at": 0.5}, "ball bounce", gain_db=0)
        soundmix.run(self.d, mux=False)
        sr, _, before = read(self.d / "out" / "mix.wav")
        c = soundplan.set_cue(self.d, b["id"], {"offset_f": 5})
        soundmix.run(self.d, mux=False)
        _, _, after = read(self.d / "out" / "mix.wav")
        lo = int((b["at"] - 0.06) * sr)
        hi = int((c["at"] + 0.4 + 0.06) * sr)                                   # ball bounce file is 0.4 s
        diff = [i for i in range(len(before)) if before[i] != after[i]]
        self.assertTrue(diff)
        self.assertGreaterEqual(min(diff), lo)
        self.assertLessEqual(max(diff), hi)

    def test_loudness_and_true_peak(self):
        """The studio delivers at −14 ± 1 LUFS with true peak ≤ −1 dB (runner/worker.py): one gain from voice and bed,
        then a true-peak limiter at −2.5 dB, so the AAC copy stays under −1 dB too."""
        soundplan.add_cue(self.d, "S1", "pop", {"shot_at": 0.25}, "cork pop", gain_db=6)
        soundmix.run(self.d, mux=False)
        p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(self.d / "out" / "mix.wav"), "-af", "ebur128=peak=true",
                            "-f", "null", "-"], capture_output=True, text=True)
        import re
        lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr)[-1])
        peak = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", p.stderr)[-1])
        self.assertLessEqual(abs(lufs + 14), 1.0, lufs)
        self.assertLessEqual(peak, -2.3)

    def test_silence(self):
        soundplan.add_silence(self.d, "S2", {"shot_at": 0.6}, 0.5, -57)            # 3.8–4.3 s, no voice there
        soundmix.run(self.d, mux=False)
        sr, _, mix = read(self.d / "out" / "mix.wav")
        self.assertLess(db(mix[int(3.85 * sr):int(4.25 * sr)]), -50)
        self.assertGreater(db(mix[int(4.5 * sr):int(4.9 * sr)]), -40)             # the music comes back

    def test_only_library_sounds(self):
        c = soundplan.add_cue(self.d, "S1", "pop", {"shot_at": 0.25}, "cork pop")
        idx = self.d / "sound" / "cache" / "index.json"
        data = json.loads(idx.read_text())
        data[c["entry"]]["source"] = "reference"
        idx.write_text(json.dumps(data))
        with self.assertRaises(soundplan.PlanError):
            soundmix.run(self.d, mux=False)
        data[c["entry"]]["source"] = "sonniss"
        idx.write_text(json.dumps(data))
        # a cached file that is a link into references/ is refused too
        ref = self.t / "repo" / "references" / "x.wav"
        soundfix.wav(ref, "hit", 0.2)
        f = next((self.d / "sound" / "cache").glob("*.wav"))
        f.unlink()
        f.symlink_to(ref)
        with self.assertRaises(soundplan.PlanError):
            soundmix.run(self.d, mux=False)

    def test_mix_waits_for_the_animatic(self):
        """specs/037 T056: `sound mix` is refused (exit 3) while the Animatic is not approved."""
        from filmcheck import cli, points
        import io
        from contextlib import redirect_stderr
        e = io.StringIO()
        with mock.patch.object(points, "gate", side_effect=lambda d, p: ["the animatic review is not approved"]
                               if p == "animatic" else []), redirect_stderr(e):
            self.assertEqual(cli.main(["sound", "mix", "f1", "--dir", str(self.d)]), 3)
        self.assertIn("animatic review is not approved", e.getvalue())

    def test_cli(self):
        from filmcheck import cli
        import io
        from contextlib import redirect_stdout
        o = io.StringIO()
        with redirect_stdout(o):
            code = cli.main(["sound", "cue", "add", "f1", "S2", "--action", "window breaks", "--query", "window shatter",
                             "--motion", "Window · Scale", "--dir", str(self.d), "--by", "claude"])
            code2 = cli.main(["sound", "mix", "f1", "--dir", str(self.d)])
            code3 = cli.main(["sound", "plan", "f1", "--dir", str(self.d), "--json"])
        self.assertEqual((code, code2, code3), (0, 0, 0), o.getvalue())
        self.assertRegex(o.getvalue(), r"cues 1 placed · 0 dropped · 0 missing · [\d.]+ s")
        plan = json.loads(o.getvalue().strip().splitlines()[-1])
        self.assertEqual(plan["cues"][0]["by"], "claude")
        with redirect_stdout(o):
            code4 = cli.main(["sound", "cue", "rm", "f1", plan["cues"][0]["id"], "--dir", str(self.d)])   # rm has no --by
        self.assertEqual(code4, 0, o.getvalue())
        self.assertEqual(soundplan.load(self.d)["cues"], [])
        o = io.StringIO()
        with redirect_stdout(o):
            cli.main(["sound", "cue", "add", "f1", "S2", "--action", "window breaks", "--query", "window shatter",
                      "--motion", "Window · Scale", "--dir", str(self.d)])
            code5 = cli.main(["sound", "shot", "off", "f1", "S2", "--dir", str(self.d)])
            code6 = cli.main(["sound", "mix", "f1", "--dir", str(self.d)])
            code7 = cli.main(["sound", "plan", "f1", "--dir", str(self.d)])
        self.assertEqual((code5, code6, code7), (0, 0, 0), o.getvalue())
        self.assertIn("✓ sound off: S2", o.getvalue())
        self.assertRegex(o.getvalue(), r"cues 0 placed · 0 dropped · 0 missing · 1 off · [\d.]+ s")
        self.assertIn("S2 (t0 2.00s) · sound off", o.getvalue())
        with redirect_stdout(o):
            self.assertEqual(cli.main(["sound", "shot", "on", "f1", "S2", "--dir", str(self.d)]), 0)
        self.assertEqual(soundplan.load(self.d)["off"], [])


if __name__ == "__main__":
    unittest.main()
