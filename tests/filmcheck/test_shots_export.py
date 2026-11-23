"""shots export (specs/029 T009, FR-003a): shots.json from the page's window.SHOTS, without drawing frames."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import samples  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"
LIB = REPO / "lib" / "lemo-opuscar"
PY = str(REPO / "tools" / ".venv" / "bin" / "python") if (REPO / "tools" / ".venv" / "bin" / "python").is_file() else sys.executable
HAVE_PAGE = shutil.which("node") and (LIB / "node_modules" / "playwright-core").is_dir()
SHOTS = [{"id": "S01", "t0": 0.0, "t1": 1.2}, {"id": "S02", "t0": 1.2, "t1": 2.5}, {"id": "S03", "t0": 2.5, "t1": 4.0}]


def video(path: Path, seconds: float, fps=30):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=gray:s=160x90:r={fps}:d={seconds}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)


@unittest.skipUnless(HAVE_PAGE, "needs node and the library's playwright-core")
class ShotsExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TMP.mkdir(exist_ok=True)
        cls.root = Path(tempfile.mkdtemp(dir=TMP))

    def cli(self, *args):
        env = {**os.environ, "STUDIO_LIB": str(LIB), "STUDIO_ROOT": str(self.root)}
        return subprocess.run([PY, str(REPO / "tools" / "filmcheck" / "cli.py"), *args], capture_output=True, text=True,
                              env=env, cwd=str(self.root), timeout=300)

    def test_page_shots_written(self):
        d = samples.make_tier_film(self.root, "exp-good", shots=SHOTS, dur=4.0)
        video(d / "exp-good.mp4", 4.0)
        p = self.cli("shots", "export", "exp-good", "--dir", str(d))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn(f"film: {d.resolve()}", p.stdout.splitlines()[0])
        s = json.loads((d / "shots.json").read_text())
        self.assertEqual((s["version"], s["source"], s["video"], s["fps"]), (1, "page", "exp-good.mp4", 30))
        self.assertAlmostEqual(s["duration"], 4.0, places=2)
        self.assertEqual([r[3] for r in s["shots"]], ["S01", "S02", "S03"])
        self.assertEqual(s["shots"][1][:2], [1.2, 2.5])
        self.assertFalse((d / "out" / ".chunks").exists())           # no frames drawn

    def test_page_without_shots(self):
        d = samples.make_tier_film(self.root, "exp-none", shots=SHOTS, dur=4.0, export_shots=False)
        video(d / "exp-none.mp4", 4.0)
        p = self.cli("shots", "export", "exp-none", "--dir", str(d))
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("SHOTS", p.stdout + p.stderr)
        self.assertFalse((d / "shots.json").exists())

    def test_video_length_differs(self):
        d = samples.make_tier_film(self.root, "exp-long", shots=SHOTS, dur=4.0)
        video(d / "exp-long.mp4", 4.5)
        p = self.cli("shots", "export", "exp-long", "--dir", str(d))
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertFalse((d / "shots.json").exists())

    def test_missing_video_or_film(self):
        d = samples.make_tier_film(self.root, "exp-novid", shots=SHOTS, dur=4.0)
        self.assertEqual(self.cli("shots", "export", "exp-novid", "--dir", str(d)).returncode, 2)
        self.assertEqual(self.cli("shots", "export", "no-such-film", "--dir", str(self.root / "films" / "no-such-film")).returncode, 2)


class QcCopiesRenderShots(unittest.TestCase):           # T015: tier 4 gives the muxed film its shots.json
    def test_copy_when_length_matches(self):
        from filmcheck import qc
        TMP.mkdir(exist_ok=True)
        root = Path(tempfile.mkdtemp(dir=TMP))
        d = root / "films" / "qc-shots"
        (d / "out").mkdir(parents=True)
        video(d / "qc-shots.mp4", 4.0)
        rows = [[s["t0"], s["t1"], "x", s["id"]] for s in SHOTS]
        (d / "out" / "shots.json").write_text(json.dumps({"version": 1, "video": "video.mp4", "duration": 4.0, "fps": 30,
                                                          "source": "page", "shots": rows}))
        line = qc.film_shots(d)
        self.assertIn("3 shots", line)
        s = json.loads((d / "shots.json").read_text())
        self.assertEqual((s["video"], s["source"], len(s["shots"])), ("qc-shots.mp4", "page", 3))
        self.assertIn("kept", qc.film_shots(d))
        rows[-1][1] = 5.0                                     # a render that does not match the muxed film
        (d / "shots.json").unlink()
        (d / "out" / "shots.json").write_text(json.dumps({"shots": rows}))
        self.assertTrue(qc.film_shots(d).startswith("! "))
        self.assertFalse((d / "shots.json").exists())


if __name__ == "__main__":
    unittest.main()
