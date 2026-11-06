"""ffprobe and the measured part of each video (research.md §2)."""
import json
import subprocess
from fractions import Fraction
from pathlib import Path

from .refset import StepError


def _rate(s: str) -> float:
    try:
        f = Fraction(s)
        return float(f) if f > 0 else 0.0
    except (ValueError, ZeroDivisionError):
        return 0.0


def probe(path: Path) -> dict:
    cmd = ["ffprobe", "-v", "error", "-show_entries",
           "stream=codec_type,width,height,avg_frame_rate,r_frame_rate,nb_frames,duration:format=duration",
           "-of", "json", str(path)]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    except FileNotFoundError:
        raise StepError("cần ffprobe (đi kèm ffmpeg)")
    except subprocess.CalledProcessError as e:
        raise StepError(f"không đọc được video: {e.stderr.strip()[:200]}")
    info = json.loads(out)
    vs = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    if not vs:
        raise StepError("file không có hình")
    v = vs[0]
    fps = _rate(v.get("avg_frame_rate", "0")) or _rate(v.get("r_frame_rate", "0"))
    dur = float(v.get("duration") or info.get("format", {}).get("duration") or 0)
    if fps <= 0 or dur <= 0:
        raise StepError("không đọc được tốc độ khung hoặc độ dài")
    w, h = int(v["width"]), int(v["height"])
    nb = v.get("nb_frames")
    return {
        "width": w, "height": h, "fps": round(fps, 4), "duration": round(dur, 4),
        "nb_frames": int(nb) if nb and str(nb).isdigit() else None,
        "orientation": orientation(w, h),
        "has_audio": any(s.get("codec_type") == "audio" for s in info.get("streams", [])),
    }


def orientation(w: int, h: int) -> str:
    if abs(w - h) <= 0.05 * max(w, h):
        return "square"
    return "landscape" if w > h else "portrait"


def segments(duration: float, max_seconds: float = 180) -> list:
    """≤ max: the whole video. Longer: the opening third of the budget plus 4 evenly spread pieces."""
    if duration <= max_seconds:
        return [[0.0, round(duration, 4)]]
    head = max_seconds / 3
    piece = (max_seconds - head) / 4
    segs = [[0.0, round(head, 4)]]
    span = duration - head
    for k in range(1, 5):
        c = head + span * k / 5
        a = max(head, min(c - piece / 2, duration - piece))
        segs.append([round(a, 4), round(a + piece, 4)])
    return segs


def is_whole(segs: list, duration: float) -> bool:
    return len(segs) == 1 and segs[0][0] == 0 and abs(segs[0][1] - duration) < 1e-3


def expected_frames(meta: dict, segs: list) -> int:
    if is_whole(segs, meta["duration"]) and meta.get("nb_frames"):
        return meta["nb_frames"]
    return sum(round((b - a) * meta["fps"]) for a, b in segs)


def scaled_height(w: int, h: int, target_w: int = 320) -> int:
    return max(2, int(round(h * target_w / w / 2)) * 2)
