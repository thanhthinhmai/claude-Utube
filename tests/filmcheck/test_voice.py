"""Tier 0, the voice check, and the studio's recogniser model (specs/020 T029, T030; US3; FR-001, FR-002; SC-007)."""
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import voicecheck  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"
LIB = REPO / "lib" / "lemo-opuscar"
PY = str(REPO / "tools" / ".venv" / "bin" / "python") if (REPO / "tools" / ".venv" / "bin" / "python").is_file() else sys.executable
SR = 16000


def wav(path: Path, parts):
    """parts: [(seconds, sound?)] → a mono 16 kHz file."""
    frames = bytearray()
    for sec, on in parts:
        for i in range(int(sec * SR)):
            v = int(9000 * math.sin(2 * math.pi * 220 * i / SR)) if on else 0
            frames += struct.pack("<h", v)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(frames))


def stamps(n, start=0.0, word=0.32, gap=0.04):
    out, t = [], start
    for k in range(n):
        out.append([f"w{k}", round(t, 3), round(t + word, 3)])
        t += word + gap
    return out


def voice_film(root: Path, name="voice-pause", n=70):
    d = root / "films" / name
    (d / "voices").mkdir(parents=True)
    rows, words, durs = [], {}, {}
    for i in range(1, n + 1):
        lid = f"l{i:02d}"
        if lid == "l17":                   # a real 0.9 s pause inside the line
            ws = stamps(4) + stamps(4, start=4 * 0.36 - 0.04 + 0.9)
            wav(d / "voices" / f"{lid}.wav", [(1.4, True), (0.9, False), (1.42, True)])
        elif lid == "l30":                 # the recogniser left a gap, but the voice never stops: not a pause
            ws = stamps(4) + stamps(4, start=4 * 0.36 - 0.04 + 0.85)
            wav(d / "voices" / f"{lid}.wav", [(ws[-1][2], True)])
        else:
            ws = stamps(8)
            wav(d / "voices" / f"{lid}.wav", [(ws[-1][2], True)])
        words[lid] = ws
        durs[lid] = ws[-1][2]
        rows.append({"id": lid, "para": f"P{i:02d}", "text": " ".join(w[0] for w in ws)})
    (d / "lines.json").write_text(json.dumps(rows))
    (d / "voices" / "words.json").write_text(json.dumps(words))
    (d / "voices" / "dur.json").write_text(json.dumps(durs))
    return d


@unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
class VoiceCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TMP.mkdir(exist_ok=True)
        cls.root = Path(tempfile.mkdtemp(dir=TMP))

    def test_sc007_pause_in_a_line(self):
        d = voice_film(self.root)
        t = time.time()
        r = voicecheck.run(d, LIB)
        self.assertLessEqual(time.time() - t, 30.0)
        self.assertEqual([(i["rule"], i["ref"]) for i in r["issues"]], [("pause_in_line", "l17")], r["issues"])
        self.assertAlmostEqual(r["issues"][0]["measure"], 0.9, delta=0.05)
        self.assertIn("regenerate l17", r["issues"][0]["fix"])
        self.assertEqual(r["measures"]["lines"], 70)

    def test_recorded_line_mismatch_and_tail(self):
        d = voice_film(self.root, "voice-mix", n=3)
        rows = json.loads((d / "lines.json").read_text())
        rows[0]["recorded"] = True
        rows[0]["text"] = "a completely different sentence that was never said here"
        (d / "lines.json").write_text(json.dumps(rows))
        durs = json.loads((d / "voices" / "dur.json").read_text())
        durs["l02"] += 0.7
        (d / "voices" / "dur.json").write_text(json.dumps(durs))
        r = voicecheck.run(d, LIB)
        got = [(i["rule"], i["ref"]) for i in r["issues"]]
        self.assertEqual(got, [("asr_mismatch", "l01"), ("tail_mismatch", "l02")])
        self.assertIn("check the recording", r["issues"][0]["fix"])
        self.assertFalse(r["pass"])

    def test_line_asr_text_is_expected(self):  # a line's "asr" field overrides its text, as in asr_check.py
        d = voice_film(self.root, "voice-asr", n=3)
        rows = json.loads((d / "lines.json").read_text())
        words = json.loads((d / "voices" / "words.json").read_text())
        heard = " ".join(w[0] for w in words["l01"])
        rows[0]["text"] = "Your mum calls on a Sunday about the colour of the neighbour's car."
        rows[0]["asr"] = heard
        (d / "lines.json").write_text(json.dumps(rows))
        r = voicecheck.run(d, LIB)
        self.assertNotIn(("asr_mismatch", "l01"), [(i["rule"], i["ref"]) for i in r["issues"]])

    def test_spoken_dollars_folded_into_a_dollar_sign(self):   # "$104 billion." then the voice still says "dollars"
        d = voice_film(self.root, "voice-dollars", n=3)
        rows = json.loads((d / "lines.json").read_text())
        words = json.loads((d / "voices" / "words.json").read_text())
        durs = json.loads((d / "voices" / "dur.json").read_text())
        ws = stamps(6) + [["$104", 2.2, 2.8], ["billion.", 2.8, 3.2]]
        words["l02"] = ws
        durs["l02"] = 3.2 + 0.75                                    # "dollars" is spoken after the last stamp
        rows[1]["text"] = "w0 w1 w2 w3 w4 w5 one hundred four billion dollars."
        rows[1]["asr"] = "w0 w1 w2 w3 w4 w5 $104 billion."
        wav(d / "voices" / "l02.wav", [(3.95, True)])
        ws3 = stamps(3) + [["$83,", 1.2, 1.7], ["raising", 2.6, 3.0]] + stamps(2, start=3.04)
        words["l03"] = ws3
        durs["l03"] = ws3[-1][2]
        rows[2]["text"] = "w0 w1 w2 eighty-three dollars, raising w0 w1"
        rows[2]["asr"] = "w0 w1 w2 $83, raising w0 w1"
        wav(d / "voices" / "l03.wav", [(1.7 + 0.6, True), (0.3, False), (ws3[-1][2] - 2.6, True)])
        for f, x in (("lines.json", rows), ("voices/words.json", words), ("voices/dur.json", durs)):
            (d / f).write_text(json.dumps(x))
        r = voicecheck.run(d, LIB)
        self.assertEqual([(i["rule"], i["ref"]) for i in r["issues"]], [], r["issues"])
        durs["l02"] = 3.2 + 1.6                                     # far more than one spoken word: still a tail
        (d / "voices" / "dur.json").write_text(json.dumps(durs))
        self.assertIn(("tail_mismatch", "l02"), [(i["rule"], i["ref"]) for i in voicecheck.run(d, LIB)["issues"]])

    def test_percent_sign_is_a_word(self):
        self.assertGreaterEqual(voicecheck.similar("Your jumps go eleven percent higher.", "Your jumps go 11% higher."), 0.99)
        self.assertLess(voicecheck.similar("Your jumps go eleven percent higher.", "Your jumps go 11 higher."), 0.92)

    def test_accents_fold(self):
        self.assertGreaterEqual(voicecheck.similar("At the café, the barista squints.", "At the cafe, the barista squints."), 0.99)

    def test_cli(self):
        voice_film(self.root, "voice-cli", n=2)
        env = {**os.environ, "STUDIO_LIB": str(LIB), "STUDIO_ROOT": str(self.root)}
        p = subprocess.run([PY, str(REPO / "tools/filmcheck/cli.py"), "qc", "voice", "voice-cli"], capture_output=True,
                           text=True, env=env, cwd=str(self.root))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("✓ voice: 2 lines", p.stdout)


class StudioModel(unittest.TestCase):
    """FR-002: one recogniser model per language, from tools/asr.json (T030)."""

    def run_asr(self, root, lang_line):
        d = root / "films" / "m"
        d.mkdir(parents=True, exist_ok=True)
        (d / "CHANNEL_BRIEF.md").write_text(lang_line)
        env = {**os.environ, "STUDIO_ASR_DRY": "1", "STUDIO_LIB": str(LIB), "STUDIO_ROOT": str(root)}
        p = subprocess.run(["sh", str(REPO / "bin/studio"), "voice", "asr", "m"], capture_output=True, text=True, env=env,
                           cwd=str(root))
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout

    def test_model_by_language(self):
        TMP.mkdir(exist_ok=True)
        root = Path(tempfile.mkdtemp(dir=TMP))
        cfg = json.loads((REPO / "tools" / "asr.json").read_text())
        out = self.run_asr(root, "- Language: en\n")
        self.assertIn(f"--model {cfg['en']}", out)
        self.assertIn("--lang en", out)
        out = self.run_asr(root, "- Language: zh\n")
        self.assertIn(f"--model {cfg['*']}", out)
        self.assertEqual(cfg["en"], "small.en")


if __name__ == "__main__":
    unittest.main()
