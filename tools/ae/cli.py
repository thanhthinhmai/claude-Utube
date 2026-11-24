"""sh bin/studio ae build|render|fix|uses|status|new and config ae (specs/032 contracts/cli.md).

Inside a job (STUDIO_JOB and STUDIO_PROXY set) builds go through the desktop app's bridge (remote.py); elsewhere AE
runs on this machine (local.py). Exit codes: 0 done · 1 build error or CHECK lines · 2 bad input · 3 no AE / bridge."""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from ae import film as filmdoc, local, splice, uses  # noqa: E402

ROOT = Path(os.environ.get("STUDIO_ROOT") or HERE.parents[1])


def in_job() -> bool:
    return bool(os.environ.get("STUDIO_JOB") and os.environ.get("STUDIO_PROXY")) and os.environ.get("STUDIO_AE_LOCAL") != "1"


def film_dirs(name: str, folder=None) -> tuple:
    """(code folder with film.json + ae/, video folder with <name>.mp4 + shots.json + notes). Prints `film: …`."""
    if folder:
        d = Path(folder).expanduser().resolve()
        code = video = d
    else:
        if not re.fullmatch(r"[a-z0-9-]{1,60}", name or ""):
            print(f"✗ bad film name: {name!r}", file=sys.stderr)
            raise SystemExit(2)
        here = Path.cwd() / "films" / name             # a job works in its own folder (like filmcheck's film_dir)
        proj = (here if (here / "film.json").is_file() else ROOT / "films" / name).resolve()
        video = None
        if not in_job():
            from filmcheck.cli import app_film
            video = app_film(name)
        video = video or proj
        code = video if (video / "film.json").is_file() or not (proj / "film.json").is_file() else proj
    if not code.is_dir():
        print(f"✗ film folder not found: {code}", file=sys.stderr)
        raise SystemExit(2)
    print(f"film: {code}" + (f" (video: {video})" if video != code else ""), flush=True)
    return code, video


def runner():
    if in_job():
        from ae import remote
        return remote.build
    return local.build


def progress(p: dict) -> None:
    print(f"… {p.get('shot')} ({p.get('index')}/{p.get('total')})", flush=True)


def do_build(code: Path, shots) -> dict:
    r = runner()(code, shots, progress=progress)
    for c in r["checks"]:
        print(c)
    return r


def fail(e) -> int:
    if isinstance(e, filmdoc.FilmError):
        print(f"✗ {e.message}", file=sys.stderr)
        return 2
    if isinstance(e, local.AeError):
        print(f"✗ {e.code}: {e.message}", file=sys.stderr)
        if e.log_tail:
            print(e.log_tail, file=sys.stderr)
        return e.exit_code()
    if isinstance(e, splice.SpliceError):
        print(f"✗ splice: {e}", file=sys.stderr)
        return 1
    raise e


def cmd_build(a) -> int:
    code, _ = film_dirs(a.film, a.dir)
    try:
        doc = filmdoc.require_ae(code)
        shots = filmdoc.pick_shots(doc, a.shots.split(",") if a.shots else None)
        r = do_build(code, shots)
    except (filmdoc.FilmError, local.AeError) as e:
        return fail(e)
    out = code / "out"
    out.mkdir(exist_ok=True)
    shutil.copyfile(r["master"], out / "build.mp4")
    (out / "build-shots.json").write_text(json.dumps({"version": 1, "video": "build.mp4", "duration": r["duration"],
                                                      "fps": doc["fps"], "source": "ae", "shots": r["marks"]}))
    print(f"✓ built {', '.join(shots)} · {r['duration']:.2f} s → {out / 'build.mp4'}"
          + (f" · {len(r['checks'])} CHECK" if r["checks"] else ""))
    return 1 if r["checks"] else 0


def _mux(master: Path, audio, out: Path) -> None:
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(master)]
    if audio:
        cmd += ["-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)


def cmd_render(a) -> int:
    code, video = film_dirs(a.film, a.dir)
    try:
        doc = filmdoc.require_ae(code)
        r = do_build(code, None)
    except (filmdoc.FilmError, local.AeError) as e:
        return fail(e)
    audio = (code / doc["audio"]) if doc.get("audio") else None
    if audio is not None and not audio.is_file():
        print(f"✗ film.json audio not found: {audio}", file=sys.stderr)
        return 2
    out = code / "out"
    out.mkdir(exist_ok=True)
    full = out / "render.mp4"
    _mux(Path(r["master"]), audio, full)
    marks = {"version": 1, "video": f"{code.name}.mp4", "duration": r["duration"], "fps": doc["fps"], "source": "ae",
             "shots": r["marks"]}
    (out / "render-shots.json").write_text(json.dumps(marks))
    if in_job():
        shutil.copyfile(full, code / f"{code.name}.mp4")
        (code / "shots.json").write_text(json.dumps(marks))
    else:
        from filmcheck import shotnotes
        shotnotes.replace_video(video, full, out / "render-shots.json")
    print(f"✓ rendered {len(r['marks'])} shots · {r['duration']:.2f} s → {video / (code.name + '.mp4')}")
    return 1 if r["checks"] else 0


def cmd_fix(a) -> int:
    code, video = film_dirs(a.film, a.dir)
    try:
        doc = filmdoc.require_ae(code)
        shots = filmdoc.pick_shots(doc, a.shots)
        cur, marks_file = video / f"{video.name}.mp4", video / "shots.json"
        if not cur.is_file() or not marks_file.is_file():
            print(f"✗ the film has no video and shots.json yet ({video}); run sh bin/studio ae render {a.film}", file=sys.stderr)
            return 2
        marks = json.loads(marks_file.read_text(encoding="utf-8"))
        r = do_build(code, shots)
        film_len = {m[3]: m[1] - m[0] for m in marks["shots"]}
        for m in r["marks"]:
            if m[3] in film_len and abs((m[1] - m[0]) - film_len[m[3]]) > 0.5 / doc["fps"]:
                print(f"! {m[3]} is now {m[1] - m[0]:.2f} s, the film keeps {film_len[m[3]]:.2f} s "
                      "(cut, or the last frame held); timing of the film is unchanged")
        out = code / "out"
        out.mkdir(exist_ok=True)
        res = splice.splice(cur, marks["shots"], splice.pieces_from_master(r["master"], r["marks"], shots), out / "fix.mp4")
        (out / "fix-shots.json").write_text(json.dumps(marks))
    except (filmdoc.FilmError, local.AeError, splice.SpliceError) as e:
        return fail(e)
    print(f"✓ rebuilt {', '.join(res['replaced'])} · {res['frames']} frames → {out / 'fix.mp4'}")
    if in_job():
        print("the job's end puts out/fix.mp4 in place of the film's video (the previous one is kept)")
    else:
        from filmcheck import shotnotes
        rr = shotnotes.replace_video(video, out / "fix.mp4", out / "fix-shots.json")
        print(f"✓ video replaced ({rr['new']:.2f} s) · previous kept")
    return 1 if r["checks"] else 0


def cmd_uses(a) -> int:
    code, _ = film_dirs(a.film, a.dir)
    found = uses.shots_using(code, a.funcs)
    print(" ".join(found) if found else "(no shot uses " + ", ".join(a.funcs) + ")")
    return 0


def cmd_status(a) -> int:
    if in_job():
        from ae import remote
        st = remote.status()
        print(f"bridge: {'ready' if st.get('ready') else 'not ready'}" + (f" · {st.get('afterfx')}" if st.get("afterfx") else ""))
        if st.get("message"):
            print(st["message"])
        print(f"queue: {st.get('queued', 0)} waiting · {st.get('running', 0)} running")
        return 0
    s = local.settings()
    print(f"config: {local.CONFIG}")
    for k in ("afterfx", "aerender", "work"):
        v = s[k]
        v = " ".join(v) if isinstance(v, list) else v
        ok = "" if s["kind"] == "fake" or not v else ("" if Path(v).exists() else "  (missing)")
        print(f"{k}: {v or '-'}{ok}")
    try:
        local.check(s)
        print(f"After Effects: ready ({s['kind']})")
    except local.AeError as e:
        print(f"After Effects: {e.code}: {e.message}")
    return 0


SHOTS_TEMPLATE = """// shots.jsx: this film's own shots (specs/032). One function per shot id of film.json, returning its comp.
// The shared kit (tools/ae/kit: lib, chars, scene, persp, build_core) is loaded first: use CU.comp, CU.person, …
CU.shot1 = function () {
  var c = CU.comp("S01 title", 3);
  return c;
};
"""


def cmd_new(a) -> int:
    if not re.fullmatch(r"[a-z0-9-]{1,60}", a.film):
        print(f"✗ bad film name: {a.film!r}", file=sys.stderr)
        return 2
    d = Path(a.dir).expanduser().resolve() if a.dir else ROOT / "films" / a.film
    if (d / "film.json").exists():
        print(f"✗ {d / 'film.json'} already exists", file=sys.stderr)
        return 2
    (d / "ae").mkdir(parents=True, exist_ok=True)
    if not (d / "ae" / "shots.jsx").exists():
        (d / "ae" / "shots.jsx").write_text(SHOTS_TEMPLATE)
    (d / "film.json").write_text(json.dumps({"engine": "ae", "fps": a.fps, "size": [1920, 1080], "shots": ["S1"],
                                             "ae_files": ["shots.jsx"]}, indent=2) + "\n")
    print(f"✓ {d / 'film.json'} · {d / 'ae' / 'shots.jsx'}")
    return 0


def cmd_config(a) -> int:
    changes = {"afterfx": a.afterfx, "aerender": a.aerender, "work": a.work}
    for k in ("afterfx", "aerender"):
        if changes[k] and not Path(changes[k]).exists():
            print(f"✗ {k}: {changes[k]} does not exist", file=sys.stderr)
            return 2
    if any(v is not None for v in changes.values()):
        if a.work:
            Path(a.work).mkdir(parents=True, exist_ok=True)
        local.save_config(changes)
    return cmd_status(a)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="studio ae", description="After Effects films (specs/032)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("build"); s.add_argument("film"); s.add_argument("--shots"); s.add_argument("--dir"); s.set_defaults(fn=cmd_build)
    s = sub.add_parser("render"); s.add_argument("film"); s.add_argument("--dir"); s.set_defaults(fn=cmd_render)
    s = sub.add_parser("fix"); s.add_argument("film"); s.add_argument("shots", nargs="+"); s.add_argument("--dir"); s.set_defaults(fn=cmd_fix)
    s = sub.add_parser("uses"); s.add_argument("film"); s.add_argument("funcs", nargs="+"); s.add_argument("--dir"); s.set_defaults(fn=cmd_uses)
    s = sub.add_parser("status"); s.set_defaults(fn=cmd_status)
    s = sub.add_parser("new"); s.add_argument("film"); s.add_argument("--fps", type=int, default=30); s.add_argument("--dir"); s.set_defaults(fn=cmd_new)
    s = sub.add_parser("config"); s.add_argument("--afterfx"); s.add_argument("--aerender"); s.add_argument("--work"); s.set_defaults(fn=cmd_config)
    return p


def main(argv=None) -> int:
    a = parser().parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
