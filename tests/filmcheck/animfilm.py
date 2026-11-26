"""The ae-sleepless-test data (specs/035 T002) copied into a temp film folder, with silent voice files of the right
lengths when a test needs audio, and timing.json from its build marks."""
import json
import shutil
import subprocess
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "animatic-sleepless"


def make(d: Path, timing: bool = True, wavs: bool = False, ae: bool = True) -> Path:
    d = Path(d)
    shutil.copytree(DATA, d)
    if ae:
        (d / "ae").mkdir(exist_ok=True)
        (d / "ae" / "shots.jsx").write_text("// test\n")
    if timing:
        import sys
        sys.path.insert(0, str(DATA.parents[3] / "tools"))
        from filmcheck import timing as tm
        tm.from_marks(d, d / "out" / "build-shots.json")
    if wavs:
        for lid, sec in json.loads((d / "voices" / "dur.json").read_text()).items():
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t",
                            str(sec), str(d / "voices" / f"{lid}.wav")], check=True)
    return d


def fake_draft(d: Path) -> None:
    """A draft built from the film's current state (no After Effects)."""
    import sys
    sys.path.insert(0, str(DATA.parents[3] / "tools"))
    from filmcheck import animatic, timing as tm
    a = Path(d) / "animatic"
    a.mkdir(exist_ok=True)
    (a / "draft.mp4").write_bytes(b"mp4")
    doc = tm.require(d)
    (a / "draft.json").write_text(json.dumps({"frames": doc["frames"], "narration_sha": animatic.narration_sha(d),
                                              "code_sha": animatic.code_sha(d), "built_at": "2026-11-26T00:00:00Z",
                                              "shots_built": list(doc["frames"]), "seconds": 1.0, "fps": doc["fps"],
                                              "size": [480, 270]}))
