"""How long a build will take (specs/038 T020, FR-009), printed before the build starts.

Blender: frames × seconds per frame measured on this machine (blender.json secPerFrame, rewritten after each real
full-size run; a quarter-size run costs about a fifth). AE: shots × the average seconds per shot of past AE builds
(blender.json aeSecPerShot, default 60 s)."""
from blender import config

QUARTER = 0.2
AE_SEC_PER_SHOT = 60.0


def blender_seconds(frames: int, quarter: bool = False, s: dict = None) -> float:
    s = s or config.settings()
    return frames * float(s["secPerFrame"]) * (QUARTER if quarter else 1.0)


def ae_seconds(shots: int) -> float:
    return shots * float(config.load().get("aeSecPerShot") or AE_SEC_PER_SHOT)


def remember_ae(shots: int, seconds: float) -> None:
    """Running average of AE seconds per shot (weight 1/3 for the newest build)."""
    if shots <= 0 or seconds <= 0:
        return
    old = float(config.load().get("aeSecPerShot") or 0)
    new = seconds / shots
    config.save({"aeSecPerShot": round(new if not old else old * 2 / 3 + new / 3, 1)})


def _mins(sec: float) -> str:
    return f"{sec / 60:.0f} min" if sec >= 90 else f"{sec:.0f} s"


def line(blender_frames: int, ae_shots: int = 0, quarter: bool = False, s: dict = None) -> str:
    parts = []
    if blender_frames:
        parts.append(f"blender {blender_frames} frames ≈ {_mins(blender_seconds(blender_frames, quarter, s))}")
    if ae_shots:
        parts.append(f"ae {ae_shots} shot(s) ≈ {_mins(ae_seconds(ae_shots))}")
    return "estimate: " + (" · ".join(parts) if parts else "nothing to build")
