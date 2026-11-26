"""`ae draft`: the Animatic's quick draft of an AE film (specs/035 research R6, R7, R8).

AE builds the shots at quarter resolution with draft settings (CU.DRAFT); each built shot becomes its own 480×270 segment
(animatic/shots/S#.mp4, encoded once) and the draft is the segments copied back to back (splice.by_shot), so a shot
that was not rebuilt keeps its exact frames; the voice is laid on from narration.json with
ffmpeg (adelay + amix, −16 LUFS; no music, no effects), and the result is cut into one clip and one picture per shot.

Files (animatic/): draft.mp4, draft.prev.mp4 (one previous), draft.json, clips/S#.mp4, frames/S#.jpg, keys.json."""
import json
import os
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ae import splice

SIZE = (480, 270)
FRAME_MAX = 60 * 1024
WORKERS = max(2, min(8, (os.cpu_count() or 4) // 2))   # ffmpeg runs side by side (SC-001)


class DraftError(Exception):
    """code: voice (3: the voice is not approved) · ae (3) · bad (2) · build (1)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message

    def exit_code(self) -> int:
        return {"voice": 3, "ae": 3, "bad": 2}.get(self.code, 1)


def _ff(args: list, what: str) -> None:
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", *args], capture_output=True, text=True)
    if r.returncode:
        raise DraftError("build", f"{what}: {r.stderr.strip()[-300:]}")


def adir(code: Path) -> Path:
    return Path(code) / "animatic"


def voice_ready(code: Path):
    """None when the draft may be made; else why not (the voice comes first and must be approved when reviewed)."""
    from filmcheck import points
    st = points.state(code, "voice")
    if st in ("approved", "off", "skipped"):
        if points.narrated(code) and not any((Path(code) / "voices").glob("*.wav")):
            return "the film has no voice yet: make the voice first"
        return None
    return f"the voice is {st.replace('_', ' ')}: approve the voice first (sh bin/studio point approve {Path(code).name} voice)"


def voice_track(code: Path, seconds: float, out: Path) -> Path:
    """The narration alone: every voices/<line>.wav at its narration.json start, −16 LUFS, `seconds` long (R8)."""
    code = Path(code)
    nar = json.loads((code / "narration.json").read_text(encoding="utf-8"))
    lines = [ln for ln in nar.get("lines") or [] if (code / "voices" / f"{ln['id']}.wav").is_file()]
    if not lines:
        _ff(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{seconds:.3f}", str(out)], "silent voice")
        return out
    args, parts = [], []
    for i, ln in enumerate(lines):
        args += ["-i", str(code / "voices" / f"{ln['id']}.wav")]
        ms = max(0, int(round(float(ln["at"]) * 1000)))
        parts.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[a{i}]")
    mix = "".join(f"[a{i}]" for i in range(len(lines)))
    parts.append(f"{mix}amix=inputs={len(lines)}:normalize=0:dropout_transition=0,loudnorm=I=-16:TP=-1.5:LRA=11,"
                 f"aresample=48000,apad,atrim=0:{seconds:.4f}[v]")
    _ff(args + ["-filter_complex", ";".join(parts), "-map", "[v]", "-ar", "48000", "-ac", "2", str(out)], "voice mix")
    return out


def seg_path(code: Path, shot: str) -> Path:
    return adir(code) / "shots" / f"{shot}.mp4"


def cut(code: Path, voice: Path, frames: dict, fps: float) -> None:
    """clips/S#.mp4 (the shot's segment, copied, with its part of the voice) and frames/S#.jpg (middle, ≤ 60 KB)."""
    a = adir(code)
    for sub in ("clips", "frames"):
        (a / sub).mkdir(parents=True, exist_ok=True)
    starts, t = {}, 0
    for s, n in frames.items():
        starts[s], t = t, t + n

    def one(s):
        n = frames[s]
        t0, t1 = starts[s] / fps, (starts[s] + n) / fps
        part = a / "clips" / f"{s}.part.mp4"
        _ff(["-i", str(seg_path(code, s)), "-i", str(voice), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
             "-af", f"atrim=start={t0:.4f}:end={t1:.4f},asetpts=PTS-STARTPTS", "-c:a", "aac", "-b:a", "96k",
             str(part)], f"clip {s}")
        os.replace(part, a / "clips" / f"{s}.mp4")
        jpg = a / "frames" / f"{s}.jpg"
        for q in (5, 9, 14, 20, 31):
            _ff(["-i", str(seg_path(code, s)), "-vf", f"select=eq(n\\,{n // 2})", "-frames:v", "1", "-q:v", str(q),
                 str(jpg)], f"frame {s}")
            if jpg.stat().st_size <= FRAME_MAX:
                break

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(one, frames))


def make(code: Path, shots=None, build=None, progress=None, say=print) -> dict:
    """Build the draft (all shots, or these shots plus every shot whose length changed since the last draft, FR-016).
    build(code, shots, progress=, draft=True) → {master, marks, keys, checks}. Returns draft.json."""
    from filmcheck import animatic, timing
    code = Path(code)
    why = voice_ready(code)
    if why:
        raise DraftError("voice", why)
    if not (code / "narration.json").is_file() and any((code / "voices").glob("*.wav")):
        raise DraftError("voice", "the voice has no narration.json yet")
    a = adir(code)
    a.mkdir(exist_ok=True)
    old = animatic.draft_info(code) or {}
    segs = old.get("segments") or {}
    doc = timing.load(code)
    all_shots = timing.film(code)["shots"]
    if shots and doc is not None:          # these shots, and every shot whose segment is missing or of another length
        want = [s for s in all_shots if s in set(shots) or segs.get(s) != doc["frames"].get(s)
                or not seg_path(code, s).is_file()]
    else:
        want = list(all_shots)
    t_start = time.time()
    steps, tick = {}, [t_start]

    def step(name):                                   # how long each part took (draft.json "steps", SC-001)
        now = time.time()
        steps[name] = round(now - tick[0], 2)
        tick[0] = now

    r = build(code, want, progress=progress, draft=True)
    step("ae")
    if doc is None:                                   # an old film: the first whole build measures its shots
        doc = timing.from_marks(code, r["marks"])
    fps = float(doc["fps"])
    built = {str(m[3]): int(round((float(m[1]) - float(m[0])) * fps)) for m in r["marks"]}
    off = {s: n for s, n in built.items() if abs(n - doc["frames"][s]) > 1}
    if off:
        s = next(iter(off))
        say(f"CHECK timing {s}: built {off[s]} frames but timing.json says {doc['frames'][s]}: the film's code must "
            f"read CU.shotFrames(\"{s}\") (tools/ae/ANIMATIC.md)")
    frames = dict(doc["frames"])
    master = splice.probe(r["master"])
    todo = [(str(m[3]), float(m[0])) for m in r["marks"] if str(m[3]) in want]
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:   # each shot decodes only its own part of the master
        list(pool.map(lambda x: splice.segment(r["master"], x[1], frames[x[0]], seg_path(code, x[0]), SIZE,
                                               master["fps_text"]), todo))
    for sid, _ in todo:
        segs[sid] = frames[sid]
    step("segments")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        silent = tmp / "video.mp4"
        splice.by_shot([(s, seg_path(code, s)) for s in all_shots], silent)
        step("join")
        seconds = sum(frames.values()) / fps
        voice = voice_track(code, seconds, tmp / "voice.wav")
        step("voice")
        out = tmp / "draft.mp4"
        _ff(["-i", str(silent), "-i", str(voice), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a",
             "128k", str(out)], "draft mux")     # no -shortest: AAC ends a little early and would drop the last frames
        if (a / "draft.mp4").is_file():
            os.replace(a / "draft.mp4", a / "draft.prev.mp4")
        shutil.move(str(out), a / "draft.mp4")
        step("mux")
        cut(code, voice, frames, fps)
        step("cut")
    keys = {}
    try:
        keys = json.loads((a / "keys.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        keys = {}
    keys.update({s: v for s, v in (r.get("keys") or {}).items() if s in want})
    (a / "keys.json").write_text(json.dumps(keys, ensure_ascii=False, indent=1))
    info = {"frames": frames, "narration_sha": animatic.narration_sha(code), "code_sha": animatic.code_sha(code),
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "shots_built": want,
            "seconds": round(time.time() - t_start, 1), "fps": doc["fps"], "size": list(SIZE),
            "checks": list(r.get("checks") or []), "steps": steps, "segments": {k: segs[k] for k in all_shots if k in segs}}
    (a / "draft.json").write_text(json.dumps(info, ensure_ascii=False, indent=1))
    return info
