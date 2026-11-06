import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "studio"))
PY = str(REPO / "tools" / ".venv" / "bin" / "python")
CLI = str(REPO / "tools" / "studio" / "studio_cli.py")


def jpg(path: Path, color=(30, 40, 50), size=(64, 36)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)


class Project:
    """A throwaway project (STUDIO_ROOT) with one film, one reference set and one saved style."""

    def __init__(self, ports="18800-18809"):
        self.dir = Path(tempfile.mkdtemp(prefix="ui proj."))
        self.env_old = {k: os.environ.get(k) for k in ("STUDIO_ROOT", "STUDIO_UI_PORTS", "STUDIO_HEARTBEAT")}
        os.environ.update(STUDIO_ROOT=str(self.dir), STUDIO_UI_PORTS=ports, STUDIO_HEARTBEAT="0.2")
        d = self.dir
        f = d / "films" / "demo-film"
        f.mkdir(parents=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=160x90:r=24:d=1",
                        "-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-shortest",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(f / "demo-film.mp4")], check=True)
        jpg(f / "poster.jpg")
        (f / "demo-film.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nXin chào\n", encoding="utf-8")
        (f / "CREDITS").write_text("Font: Baloo 2 (OFL)\n", encoding="utf-8")
        (f / "TREATMENT.md").write_text("# Kịch bản\n<script>alert(1)</script>\n", encoding="utf-8")
        (d / "films" / "half-done" / "out").mkdir(parents=True)          # still rendering
        s = d / "references" / "demo-set"
        (s / "videos").mkdir(parents=True)
        (s / "set.json").write_text(json.dumps({"set": "demo-set", "created": "2026-11-06", "videos": [
            {"id": "v01", "file": "v01.mp4", "origin": "https://youtube.example/v/abc", "title": "Secret title",
             "channel": "Secret Channel", "source_id": "abc", "state": "transcribed"}]}), encoding="utf-8")
        (s / "profile" / "v01").mkdir(parents=True)
        (s / "profile" / "v01" / "video.json").write_text(json.dumps({"orientation": "landscape", "duration": 60,
                                                                       "palette": [{"hex": "#102030", "share": .5}]}))
        (s / "profile" / "summary.json").write_text(json.dumps({"videos_measured": 1, "measured_seconds": 60,
            "by_orientation": {"landscape": {"videos": 1, "metrics": {"luma_p50": {"median": .33, "min": .33, "max": .33}},
                                             "palette": [{"hex": "#102030", "share": 1}]}},
            "skipped": [], "low_count_warning": True}))
        jpg(s / "profile" / "v01" / "sheets" / "v01_0000.jpg")
        jpg(s / "proof" / "out" / "ref.jpg", (10, 10, 10))
        jpg(s / "proof" / "out" / "ours_r1_0.jpg", (12, 12, 12))
        (s / "proof" / "compare.json").write_text(json.dumps({"luma_diff": .03, "sat_median_diff": .01, "dark_diff_pp": 2.7,
            "palette_matched": 5, "palette_needed": 4, "pass": True, "round": 3,
            "ref": "proof/out/ref.jpg", "ours": "proof/out/ours_r1_0.jpg"}))
        st = d / "my-styles" / "demo-style"
        st.mkdir(parents=True)
        (st / "style.json").write_text(json.dumps({"slug": "demo-style", "en": "Demo Style", "based_on": "scifi-toon",
                                                   "source": "learned", "reference": {"videos": 5, "measured_seconds": 900}}))
        (st / "STYLE.md").write_text("# Demo Style — Style Prompt\n\n| a | b |\n|---|---|\n| 1 | 2 |\n<img src=x onerror=alert(1)>\n")
        (st / "EVIDENCE.md").write_text("# Evidence\n")
        jpg(st / "styleframe.jpg")
        (d / "secret.txt").write_text("do not serve")

    def cli(self, *args, timeout=30):
        return subprocess.run([PY, CLI, *args], capture_output=True, text=True, timeout=timeout, env=os.environ.copy())

    def close(self):
        try:
            self.cli("ui", "stop", timeout=15)
        finally:
            for k, v in self.env_old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            shutil.rmtree(self.dir, ignore_errors=True)


def client():
    from fastapi.testclient import TestClient
    from studio.server import create_app
    return TestClient(create_app(), base_url="http://localhost")


W = {"X-Studio": "1"}
