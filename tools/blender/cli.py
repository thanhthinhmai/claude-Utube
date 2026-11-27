"""sh bin/studio blender status|config|build|plate (specs/038 contracts/cli.md).

Exit codes: 0 done · 1 build error · 2 bad input · 3 no Blender, software GPU or lost bridge."""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from blender import bundle, config, estimate, local, remote  # noqa: E402
from blender.config import BlenderError  # noqa: E402


def fail(e) -> int:
    from ae import film as filmdoc
    if isinstance(e, filmdoc.FilmError):
        print(f"✗ {e.message}", file=sys.stderr)
        return 2
    if isinstance(e, BlenderError):
        print(f"✗ blender {e.code}: {e.message}", file=sys.stderr)
        if e.log_tail:
            print(e.log_tail, file=sys.stderr)
        return 2 if e.code == "bad_plan" else e.exit_code()
    raise e


def runner():
    return remote.build if remote.active() and os.environ.get("STUDIO_BLENDER_LOCAL") != "1" else local.build


def progress(p: dict) -> None:
    if p.get("frame", 0) % 24 == 0 or p.get("frame") == p.get("frames"):
        print(f"… {p.get('shot')} frame {p.get('frame')}/{p.get('frames')}", flush=True)


def film(a):
    from ae import cli as aecli
    from ae import film as filmdoc
    code, _ = aecli.film_dirs(a.film, getattr(a, "dir", None))
    doc = filmdoc.require_ae(code)
    return code, doc


def cmd_status(a) -> int:
    if remote.active():
        st = remote.status()
        print(f"bridge: {'ready' if st.get('ready') else 'not ready'}" + (f" · {st.get('blender')}" if st.get("blender") else ""))
        if st.get("gpu"):
            print(f"gpu: {st['gpu']}")
        return 0 if st.get("ready") else 3
    s = config.settings()
    print(f"config: {config.config_path()}")
    print(f"blender: {s['exe'] or 'not set'}")
    print(f"work: {s['work'] or 'not set'}")
    try:
        config.check(s)
    except BlenderError as e:
        return fail(e)
    probe = Path(local.work_root(s, Path(s["work"] or "."))) / "_probe"
    probe.mkdir(parents=True, exist_ok=True)
    (probe / "blender").mkdir(exist_ok=True)
    try:
        r = local.build(probe, {"kind": "probe", "film": "_probe", "fps": 24, "size": [64, 64], "quarter": False, "shots": []},
                        s=s)
    except BlenderError as e:
        if e.code == "gpu_software":
            print("gpu: software (blocked)")
        return fail(e)
    print(f"version: {r['version']}")
    print(f"gpu: {r['gpu']}")
    print(f"seconds per frame: {s['secPerFrame']}")
    return 0


def cmd_config(a) -> int:
    changes = {}
    if a.exe:
        loc = config.local_path(a.exe)
        if not Path(loc).exists():
            print(f"✗ {a.exe} not found", file=sys.stderr)
            return 2
        changes["blender"] = a.exe
    if a.work:
        Path(config.local_path(a.work)).mkdir(parents=True, exist_ok=True)
        changes["work"] = a.work
    if a.timeout:
        changes["shotTimeoutSec"] = int(a.timeout)
    cfg = config.save(changes) if changes else config.load()
    for k in ("blender", "work", "shotTimeoutSec", "secPerFrame"):
        print(f"{k}: {cfg.get(k, '-')}")
    return 0


def cmd_build(a) -> int:
    from ae import film as filmdoc
    try:
        code, doc = film(a)
        shots = filmdoc.pick_shots(doc, a.shots)
        bad = [s for s in shots if filmdoc.engine_of(doc, s) != "blender"]
        if bad:
            print(f"✗ {', '.join(bad)} not a Blender shot (shot_plan.<id>.engine); use sh bin/studio ae build", file=sys.stderr)
            return 2
        filmdoc.validate_plan(code, doc, shots)
        still = {s: a.still for s in shots} if a.still else None
        req = bundle.request(code, doc, shots, quarter=a.quarter, still=still)
        n = sum(1 if a.still else x["frames"] for x in req["shots"])
        print(estimate.line(n, quarter=a.quarter), flush=True)
        r = runner()(code, req, progress=progress)
    except (filmdoc.FilmError, BlenderError) as e:
        return fail(e)
    print(f"gpu: {r['gpu']}")
    for s, p in r["shots"].items():
        if a.still:
            dst = code / "out" / "blender" / f"{s}-still-{a.still:04d}.png"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dst)
            p = dst
        print(f"✓ {s} → {p}")
    return 0


def cmd_plate(a) -> int:
    """A background plate without characters: the set of --from, the camera planned for the shot."""
    from ae import film as filmdoc
    try:
        code, doc = film(a)
        src = a.src if a.src.startswith("S") else "S" + a.src
        shot = a.shot if a.shot.startswith("S") else "S" + a.shot
        filmdoc.pick_shots(doc, [src, shot])
        if not (code / "blender" / f"{src}.py").is_file():
            raise BlenderError("bad_plan", f"{src}: blender/{src}.py is missing")
        doc = json.loads(json.dumps(doc))
        plan = dict(doc.get("shot_plan", {}).get(src) or {})
        plan.update({k: v for k, v in (doc.get("shot_plan", {}).get(shot) or {}).items()
                     if k in ("size", "cam_height", "lens", "move")})
        doc.setdefault("shot_plan", {})[src] = plan
        req = bundle.request(code, doc, [src], kind="plate")
        r = runner()(code, req)
    except (filmdoc.FilmError, BlenderError) as e:
        return fail(e)
    dst = code / "ae" / "data" / "plates" / f"{shot}.png"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(r["shots"][src], dst)
    print(f"✓ plate {shot} (set of {src}) → {dst}")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sh bin/studio blender")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status")
    s.set_defaults(fn=cmd_status)
    s = sub.add_parser("config")
    s.add_argument("--exe")
    s.add_argument("--work")
    s.add_argument("--timeout", type=int)
    s.set_defaults(fn=cmd_config)
    s = sub.add_parser("build")
    s.add_argument("film")
    s.add_argument("shots", nargs="+")
    s.add_argument("--still", type=int)
    s.add_argument("--quarter", action="store_true")
    s.add_argument("--dir")
    s.set_defaults(fn=cmd_build)
    s = sub.add_parser("plate")
    s.add_argument("film")
    s.add_argument("shot")
    s.add_argument("--from", dest="src", required=True)
    s.add_argument("--dir")
    s.set_defaults(fn=cmd_plate)
    return p


def main(argv=None) -> int:
    a = parser().parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
