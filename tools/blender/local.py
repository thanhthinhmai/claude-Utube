"""Run Blender on this machine (specs/038 T012): stage the kit and shot scripts in the work folder, run
blender -b --factory-startup -P kit/entry.py -- request.json, watch log.txt, pack PNG frames into S<n>.mp4.

The run folder is <work>/<film>/<key>, where key is a hash of everything the frames depend on (kit, scripts, layers,
size, fps, kind). The same inputs land in the same folder, so a run cut off mid-shot goes on from the frames already
there (FR-008); a changed script gets a new folder and never mixes old frames in."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from blender import config
from blender.config import BlenderError

KIT = Path(__file__).resolve().parent / "kit"
SHOT_ID = re.compile(r"^S\d+$")


def _tail(text: str, n: int = 20) -> str:
    return "\n".join(text.strip().splitlines()[-n:])


def _files(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            yield p


def run_key(film_dir: Path, req: dict) -> str:
    h = hashlib.sha1()
    h.update(json.dumps({k: req.get(k) for k in ("kind", "fps", "size", "quarter", "shots")}, sort_keys=True).encode())
    for p in _files(KIT):
        h.update(str(p.relative_to(KIT)).encode())
        h.update(p.read_bytes())
    for s in req["shots"]:
        for rel in (s.get("script"), s.get("layers")):
            p = film_dir / rel if rel else None
            if p and p.is_file():
                h.update(p.read_bytes())
            elif p and p.is_dir():
                for q in _files(p):
                    h.update(str(q.relative_to(p)).encode())
                    h.update(q.read_bytes())
    return h.hexdigest()[:12]


def work_root(s: dict, film_dir: Path) -> Path:
    if s.get("work"):
        return Path(config.local_path(s["work"]))
    if s["kind"] == "fake":
        return film_dir / "out" / ".blender"
    raise BlenderError("bad_work", "no Blender work folder; set one with: sh bin/studio blender config --work <folder>")


def stage(s: dict, film_dir: Path, req: dict) -> Path:
    """Copy kit, shot scripts and layers into the run folder and write request.json there."""
    run = work_root(s, film_dir) / film_dir.name / run_key(film_dir, req)
    run.mkdir(parents=True, exist_ok=True)
    if (run / "kit").exists():
        shutil.rmtree(run / "kit")
    shutil.copytree(KIT, run / "kit", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for sh in req["shots"]:
        for rel in (sh.get("script"), sh.get("layers")):
            if not rel:
                continue
            src, dst = film_dir / rel, run / rel
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            elif src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            elif rel == sh.get("script"):
                raise BlenderError("bad_plan", f"{sh['id']}: {rel} is missing")
    log = run / "log.txt"
    if log.exists():
        log.unlink()
    req["id"] = run.name
    (run / "request.json").write_text(json.dumps(req, indent=1))
    return run


def _kill(proc) -> None:
    if proc and proc.poll() is None:
        proc.kill()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass


def wait_log(s: dict, log: Path, shots: list, proc, progress=None, sleep: float = 0.2) -> str:
    """Wait for START (start timeout), then a new line at least every shot timeout, until DONE, ERR or exit."""
    t0 = time.time()
    last, seen, text = t0, 0, ""
    total = sum(int(x["frames"]) for x in shots) or 1
    while True:
        text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        err = next((x for x in lines if x.startswith("ERR ")), None)
        if err:
            _kill(proc)
            parts = err.split(" ", 2)
            raise BlenderError(parts[1] if len(parts) > 1 else "script", parts[2] if len(parts) > 2 else err, _tail(text))
        if len(lines) > seen:
            seen, last = len(lines), time.time()
            if progress:
                fr = [x for x in lines if x.startswith("frame ")]
                if fr:
                    sid, pos = fr[-1].split()[1:3]
                    before = sum(int(x["frames"]) for x in shots[:[x["id"] for x in shots].index(sid)]) if sid in [x["id"] for x in shots] else 0
                    progress({"state": "running", "shot": sid, "frame": int(pos.split("/")[0]) + before, "frames": total})
        if "DONE" in lines:
            proc.wait(timeout=60)
            return text
        code = proc.poll()
        if code is not None and "DONE" not in lines:
            text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
            if "DONE" in text.split():
                return text
            if any(x.startswith("ERR ") for x in text.splitlines()):
                continue
            raise BlenderError("stopped", f"Blender stopped (exit {code}) before the run finished; run again to go on "
                                          "from the frames already drawn", _tail(text))
        now = time.time()
        if not lines and now - t0 > s["startTimeoutSec"]:
            _kill(proc)
            raise BlenderError("timeout", f"Blender did not start the kit in {s['startTimeoutSec']} s", _tail(text))
        if lines and now - last > s["shotTimeoutSec"]:
            _kill(proc)
            raise BlenderError("timeout", f"Blender made no progress for {int(s['shotTimeoutSec'])} s", _tail(text))
        time.sleep(sleep)


def pack(frames_dir: Path, fps: int, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp.mp4")
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", str(frames_dir / "f%04d.png"),
                        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                        str(tmp)], capture_output=True, text=True)
    if r.returncode:
        raise BlenderError("pack", f"ffmpeg could not pack {frames_dir.name}: {_tail(r.stderr, 5)}")
    tmp.replace(out)
    return out


def build(film_dir, req: dict, progress=None, s: dict = None) -> dict:
    """req: bundle.request(…) (contracts/bridge-api.md). Returns {"run", "log", "gpu", "version", "shots": {id: path}}."""
    d = Path(film_dir)
    s = s or config.settings()
    config.check(s)
    for sh in req["shots"]:
        if not SHOT_ID.match(sh["id"]):
            raise BlenderError("bad_plan", f"bad shot id {sh['id']!r}")
    kind, quarter, fps = req["kind"], bool(req.get("quarter")), int(req["fps"])
    shots = req["shots"]
    run = stage(s, d, req)
    entry, reqp = run / "kit" / "entry.py", run / "request.json"
    argv = s["argv"] + ["-b", "--factory-startup", "--python-exit-code", "1",
                        "-P", config.host_path(s, entry) if s["kind"] != "fake" else str(entry),
                        "--", config.host_path(s, reqp) if s["kind"] != "fake" else str(reqp)]
    have = sum(len(list((run / sh["id"]).glob("f*.png"))) for sh in shots if (run / sh["id"]).is_dir())
    t0 = time.time()
    try:
        proc = subprocess.Popen(argv, cwd=run, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as e:
        raise BlenderError("no_blender", f"Blender could not be started: {e}") from None
    text = wait_log(s, run / "log.txt", req["shots"], proc, progress)
    took = time.time() - t0
    gpu = next((x[4:].strip() for x in text.splitlines() if x.startswith("GPU ")), "")
    version = next((x[8:].strip() for x in text.splitlines() if x.startswith("VERSION ")), "")
    out = {"run": str(run), "log": text, "gpu": gpu, "version": version, "shots": {}, "seconds": round(took, 1)}
    if kind == "render":
        drawn = 0
        for sh in req["shots"]:
            if sh.get("still"):
                out["shots"][sh["id"]] = str(run / sh["id"] / f"still-{sh['still']:04d}.png")
                continue
            n = len([p for p in (run / sh["id"]).glob("f*.png") if p.stat().st_size])
            if n < sh["frames"]:
                raise BlenderError("script", f"{sh['id']}: {n}/{sh['frames']} frames after DONE", _tail(text))
            name = f"{sh['id']}-quarter.mp4" if quarter else f"{sh['id']}.mp4"
            out["shots"][sh["id"]] = str(pack(run / sh["id"], fps, d / "out" / "blender" / name))
            drawn += sh["frames"]
        drawn -= have
        if drawn > 0 and not quarter and s["kind"] != "fake":
            config.save({"secPerFrame": round(took / drawn, 2)})
    elif kind == "plate":
        out["shots"] = {sh["id"]: str(run / sh["id"] / "plate.png") for sh in req["shots"]}
    elif kind == "plan":
        out["shots"] = {sh["id"]: str(run / sh["id"] / "plan.json") for sh in req["shots"]}
    return out
