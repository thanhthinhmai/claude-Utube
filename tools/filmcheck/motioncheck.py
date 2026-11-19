"""Motion against the style's template (specs/023 US4; research R11; contracts/cli.md).

One measure for learning and checking: this module runs tools/style-learn/sl/craft.py with the learning venv
(tools/.venv, numpy), the same code that measured the reference films.
- shot_motion(frames): per shot, the camera type and whether anything moves inside the shot, from frames rendered
  before the film is recorded (tier 2, `qc shots`).
- film_motion(mp4, shots): per shot camera, movement and transition of the recorded film (tier 4, `qc`).
A style without template.json skips these rules; a missing venv is an error (exit 3), never a silent pass."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VENV_PY = ROOT / "tools" / ".venv" / "bin" / "python"
CRAFT = ROOT / "tools" / "style-learn" / "sl" / "craft.py"
INNER_BLOCKS = 162          # inner blocks of craft.py's 320×180 grid (9 × 18)
ACTIVE_BLOCKS = 2


class MotionError(Exception):
    """The measure cannot run (exit code 3)."""


def template_of(film_dir: Path):
    """The template.json of the film's style, or None (the motion rules are then skipped)."""
    from filmcheck import stylerefs
    slug = stylerefs.slug_of(Path(film_dir))
    if not slug:
        return None
    p = stylerefs.style_dir(Path(film_dir), slug) / "template.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _craft(args, timeout=3600) -> dict:
    if not VENV_PY.exists():
        raise MotionError("the motion check needs the learning tools: sh bin/studio deps learn")
    p = subprocess.run([str(VENV_PY), "-I", str(CRAFT), *map(str, args)], capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise MotionError(f"craft.py failed: {(p.stderr or p.stdout).strip()[-300:]}")
    return json.loads(p.stdout.strip().splitlines()[-1])


def shot_motion(frames: list, gap: float = 1 / 12) -> dict:
    """{cam, moving, peak} for frames of one shot taken in order, `gap` seconds apart."""
    m = _craft(["frames", "--fps", f"{1 / gap:.4f}", *frames], timeout=300)
    peak = float(m["inner"]["peak"])
    return {"cam": m["cam"]["type"], "moving": peak * INNER_BLOCKS >= ACTIVE_BLOCKS, "peak": round(peak, 4)}


def film_motion(mp4: Path, shots: list, work: Path) -> list:
    work.mkdir(parents=True, exist_ok=True)
    f = work / "motion-shots.json"
    f.write_text(json.dumps([{"id": s["id"], "t0": s["t0"], "t1": s["t1"]} for s in shots]), encoding="utf-8")
    return _craft(["video", mp4, f])["shots"]


def dead(row, min_s: float) -> bool:
    """A shot with people, a still camera and nothing moving, long enough to read as dead."""
    return row.get("cast", 0) > 0 and row["cam"] == "still" and not row["moving"] and row["t1"] - row["t0"] >= min_s


def film_measures(rows: list, dur: float) -> dict:
    """still_ratio (time with a truly still camera), motion720 (≈ median camera shift, px/frame at 720 wide, 60 fps),
    dead_share (time of dead person shots), transitions."""
    still = sum(r["t1"] - r["t0"] for r in rows if r["cam"]["type"] == "still")
    px = sorted(((r["cam"]["px_s"] * 720 / 1280 / 60), r["t1"] - r["t0"]) for r in rows)
    acc, half, m720 = 0.0, sum(w for _, w in px) / 2, 0.0
    for v, w in px:
        acc += w
        if acc >= half:
            m720 = v
            break
    tr = {}
    for r in rows:
        t = (r.get("trans_in") or {}).get("type")
        if t and t != "cut":
            tr[t] = tr.get(t, 0) + 1
    return {"still_ratio": round(still / dur, 3) if dur else None, "motion720_p50": round(m720, 4), "transitions": tr}
