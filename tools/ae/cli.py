"""sh bin/studio ae build|render|fix|uses|status|new|sheet|rigs and config ae (specs/032, 034 contracts/cli.md).

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

from ae import film as filmdoc, local, rigs, sheet, splice, uses  # noqa: E402
from blender.config import BlenderError  # noqa: E402

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
    """specs/038: mixed.build sends AE shots to the AE runner (bridge in a job, else this machine) and Blender shots to
    Blender; a film without Blender shots goes to the AE runner unchanged."""
    from ae import mixed
    return mixed.build


def progress(p: dict) -> None:
    if "frames" in p:                                  # Blender: frames drawn of the run (a line every 24)
        if p.get("frame", 0) % 24 and p.get("frame") != p.get("frames"):
            return
        print(f"… blender {p.get('shot')} frame {p.get('frame')}/{p.get('frames')}", flush=True)
        return
    print(f"… {p.get('shot')} ({p.get('index')}/{p.get('total')})", flush=True)


def do_build(code: Path, shots, draft: bool = False, plain: bool = False) -> dict:
    """plain: AE only (ae fix builds Blender shots itself)."""
    from ae import mixed
    run = mixed.ae_runner() if plain else runner()
    r = run(code, shots, progress=progress, draft=draft) if draft else run(code, shots, progress=progress)
    for c in r["checks"]:
        print(c)
    remember_timing(code, r)
    return r


def remember_timing(code: Path, r: dict) -> None:
    """specs/035: a film without timing.json gets one from the real lengths of its first whole build (old films)."""
    from filmcheck import timing
    try:
        if timing.load(code) is None and r.get("marks"):
            have = {str(m[3]) for m in r["marks"] if len(m) > 3}
            if set(timing.film(code)["shots"]) <= have:
                timing.from_marks(code, r["marks"])
                print(f"✓ timing.json written from this build's shot lengths", flush=True)
    except timing.TimingError as e:
        print(f"timing.json: {e.message}", file=sys.stderr)


def fail(e) -> int:
    from blender.config import BlenderError
    if isinstance(e, BlenderError):
        print(f"✗ blender {e.code}: {e.message}", file=sys.stderr)
        if e.log_tail:
            print(e.log_tail, file=sys.stderr)
        return 2 if e.code == "bad_plan" else e.exit_code()
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
    except (filmdoc.FilmError, local.AeError, splice.SpliceError, BlenderError) as e:
        return fail(e)
    out = code / "out"
    out.mkdir(exist_ok=True)
    shutil.copyfile(r["master"], out / "build.mp4")
    (out / "build-shots.json").write_text(json.dumps(marks_doc(r, "build.mp4", doc)))
    print(f"✓ built {', '.join(shots)} · {r['duration']:.2f} s → {out / 'build.mp4'}"
          + (f" · {len(r['checks'])} CHECK" if r["checks"] else ""))
    return 1 if r["checks"] else 0


def marks_doc(r: dict, video: str, doc: dict) -> dict:
    """build-shots.json / render-shots.json: source "ae", or "mixed" with engines {shot: {engine, version, gpu}}."""
    m = {"version": 1, "video": video, "duration": r["duration"], "fps": doc["fps"], "source": r.get("source", "ae"),
         "shots": r["marks"]}
    if r.get("engines"):
        m["engines"] = r["engines"]
    return m


def _mux(master: Path, audio, out: Path, starts=()) -> None:
    """The film's video: a key frame on every shot start, so ae fix can copy the shots it does not rebuild (038 SC-002)."""
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(master)]
    if audio:
        cmd += ["-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += splice.VCODEC + splice.key_args(starts) + ["-video_track_timescale", "15360", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)


def cmd_draft(a) -> int:
    """specs/035: the Animatic's quarter-size draft with the real voice."""
    from ae import draft
    from filmcheck import animatic, rhythm
    code, _ = film_dirs(a.film, a.dir)
    try:
        doc = filmdoc.require_ae(code)
        shots = filmdoc.pick_shots(doc, a.shots.split(",")) if a.shots else None
        info = draft.make(code, shots, build=runner(), progress=progress)
    except (filmdoc.FilmError, local.AeError, splice.SpliceError, BlenderError) as e:
        return fail(e)
    except draft.DraftError as e:
        print(f"✗ {e.message}", file=sys.stderr)
        return e.exit_code()
    for c in info.get("checks") or []:
        print(c)
    try:
        sil = f"{round(animatic.silence(code) * 100)}% (limit {round(rhythm.SILENCE_MAX * 100)}%)"
    except animatic.AnimaticError as e:
        sil = f"not measured ({e.message})"
    print(f"✓ draft of {', '.join(info['shots_built'])} → {code / 'animatic' / 'draft.mp4'}")
    print(f"draft: {info['seconds']:.1f} s · silence {sil}")
    return 1 if info.get("checks") else 0


def cmd_render(a) -> int:
    code, video = film_dirs(a.film, a.dir)
    from filmcheck import points
    why = points.gate(code, "animatic")                    # specs/035 FR-003: the final render waits for the animatic
    why = why or points.gate(code, "mix")                  # specs/037 FR-028: … and for the Sound review when it is on
    if why:
        for w in why:
            print(f"✗ {w}", file=sys.stderr)
        return 3
    from filmcheck import depthcheck
    why = depthcheck.gate(code)                            # specs/038 FR-014: no shot closer or shallower than the reference
    if why:
        for w in why:
            print(f"✗ depth: {w}", file=sys.stderr)
        return 1
    try:
        doc = filmdoc.require_ae(code)
        r = do_build(code, None)
    except (filmdoc.FilmError, local.AeError, splice.SpliceError, BlenderError) as e:
        return fail(e)
    audio = (code / doc["audio"]) if doc.get("audio") else None
    if audio is not None and not audio.is_file():
        print(f"✗ film.json audio not found: {audio}", file=sys.stderr)
        return 2
    out = code / "out"
    out.mkdir(exist_ok=True)
    full = out / "render.mp4"
    _mux(Path(r["master"]), audio, full, splice.shot_starts(r["marks"], float(doc["fps"])))
    marks = marks_doc(r, f"{code.name}.mp4", doc)
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
        from ae import mixed
        pieces, r = mixed.fix_pieces(code, doc, shots, lambda c, s: do_build(c, s, plain=True), progress=progress)
        film_len = {m[3]: m[1] - m[0] for m in marks["shots"]}
        for m in r["marks"]:
            if m[3] in film_len and abs((m[1] - m[0]) - film_len[m[3]]) > 0.5 / doc["fps"]:
                print(f"! {m[3]} is now {m[1] - m[0]:.2f} s, the film keeps {film_len[m[3]]:.2f} s "
                      "(cut, or the last frame held); timing of the film is unchanged")
        out = code / "out"
        out.mkdir(exist_ok=True)
        res = splice.splice(cur, marks["shots"], pieces, out / "fix.mp4")
        bl = filmdoc.blender_shots(doc, shots)
        if bl:
            st = mixed.load_state(code, False)
            marks["source"] = "mixed"
            eng = marks.setdefault("engines", {})
            for s in shots:
                eng[s] = ({"engine": "blender", "version": st[s]["version"], "gpu": st[s].get("gpu", "")} if s in bl
                          else {"engine": "ae", "version": mixed.ae_version(code)})
        (out / "fix-shots.json").write_text(json.dumps(marks))
    except (filmdoc.FilmError, local.AeError, splice.SpliceError, BlenderError) as e:
        return fail(e)
    print(f"✓ rebuilt {', '.join(res['replaced'])} · {res['frames']} frames → {out / 'fix.mp4'}"
          + (" · other shots copied bit for bit" if res.get("exact") else
             " · encoded once more (the old video had no key frame on each shot); the next fix copies"))
    if in_job():
        print("the job's end puts out/fix.mp4 in place of the film's video (the previous one is kept)")
    else:
        from filmcheck import shotnotes
        rr = shotnotes.replace_video(video, out / "fix.mp4", out / "fix-shots.json")
        print(f"✓ video replaced ({rr['new']:.2f} s) · previous kept")
    return 1 if r["checks"] else 0


def cmd_sheet(a) -> int:
    """Draw the cast sheet (specs/034): every character, or only --only ids; the old sheet is kept as <id>.prev/."""
    code, _ = film_dirs(a.film, a.dir)
    only = [x.strip() for x in a.only.split(",") if x.strip()] if a.only else None
    keep, carry = {}, {}
    try:
        from filmcheck import castlib
        keep, carry = castlib.library_frames(code, only)
    except ImportError:
        pass
    try:
        filmdoc.require_ae(code)
        res = sheet.build(code, runner(), only, keep, carry, progress=progress)
    except sheet.SheetError as e:
        print(f"✗ {e.code}: {e.message}", file=sys.stderr)
        return 2 if e.code in ("no_cast", "bad_cast", "no_character") else 1
    except local.AeError as e:
        if e.exit_code() == 3:
            print("✗ After Effects is not ready: " + e.message + "\n  turn it on: open After Effects (or the desktop app's "
                  "tray → After Effects… → Test), then run this again", file=sys.stderr)
            return 3
        return fail(e)
    except filmdoc.FilmError as e:
        return fail(e)
    for r in res:
        print(f"✓ {r['character']}: {r['pictures']} picture(s)" + (f" · {len(r['missing'])} not drawn" if r["missing"] else ""))
        for key, why in r["missing"]:
            print(f"  ! {r['character']}/{key}: {why}")
    print(f"sheets: {code / 'cast' / 'sheets'}")
    return 0


def cmd_rigs(a) -> int:
    """List the locked rig versions; --check fails when a locked folder changed; --lock adds a new version."""
    if a.lock:
        try:
            h = rigs.lock(a.lock)
        except (ValueError, FileNotFoundError) as e:
            print(f"✗ {e}", file=sys.stderr)
            return 2
        print(f"✓ locked {a.lock} · {h[:16]}")
        return 0
    bad = rigs.check()
    for rid in rigs.versions():
        print(f"{rid}  {'CHANGED' if rid in bad else 'ok'}  {rigs.folder(rid).relative_to(HERE.parents[1])}")
    if a.check and bad:
        print(f"✗ locked rig folder changed: {', '.join(bad)} (a change is a new version: copy the folder to "
              "v<N+1>/ and run sh bin/studio ae rigs --lock <family>@<N+1>)", file=sys.stderr)
        return 1
    return 0


def cmd_uses(a) -> int:
    code, _ = film_dirs(a.film, a.dir)
    from blender import uses as buses
    found = uses.shots_using(code, a.funcs) + buses.shots_using(code, a.funcs)
    found = sorted(set(found), key=lambda x: (int("".join(c for c in x if c.isdigit()) or 0), x))
    print(" ".join(found) if found else "(no shot uses " + ", ".join(a.funcs) + ")")
    return 0


def film_status(a) -> int:
    """specs/038 T021: one row per shot with its engine; a Blender shot built with another version must run again."""
    from ae import mixed
    code, _ = film_dirs(a.film, a.dir)
    try:
        doc = filmdoc.require_ae(code)
    except filmdoc.FilmError as e:
        return fail(e)
    bl = mixed.plan_status(code, doc)
    for s in doc["shots"]:
        eng = filmdoc.engine_of(doc, s)
        if eng == "blender":
            b = bl.get(s) or {}
            state = "Must run again" if b.get("stale") else ("built" if b.get("built") else "not built")
            print(f"{s}\tblender\t{state}" + (f"\t{b['version']}" if b.get("version") else ""))
        else:
            print(f"{s}\tae")
    return 0


def cmd_status(a) -> int:
    if getattr(a, "film", None):
        return film_status(a)
    if in_job():
        from ae import remote
        st = remote.status()
        print(f"bridge: {'ready' if st.get('ready') else 'not ready'}" + (f" · {st.get('afterfx')}" if st.get("afterfx") else ""))
        if st.get("message"):
            print(st["message"])
        print(f"queue: {st.get('queued', 0)} waiting · {st.get('running', 0)} running")
        return 0
    s = local.settings()
    print(f"config: {local.config_path()}")
    for k in ("afterfx", "aerender", "work"):
        v = s[k]
        v = " ".join(v) if isinstance(v, list) else v
        ok = "" if s["kind"] == "fake" or not v else ("" if Path(v).exists() else "  (missing)")
        print(f"{k}: {v or '-'}{ok}")
    print(f"batch: {s.get('batchShots', local.BATCH_SHOTS)} shots per After Effects project (ae.json batchShots)")
    try:
        local.check(s)
        print(f"After Effects: ready ({s['kind']})")
    except local.AeError as e:
        print(f"After Effects: {e.code}: {e.message}")
    return 0


SHOTS_TEMPLATE = """// shots.jsx: this film's own shots (specs/032). One function per shot id of film.json, returning its comp.
// The shared kit (tools/ae/kit: lib, chars, scene, persp, build_core) is loaded first: use CU.comp, CU.person, …
// Shot lengths come from the film's timing.json (the Animatic, specs/035): CU.shotFrames("S1") || <frames before it>.
CU.shot1 = function () {
  var c = CU.comp("S01 title", (CU.shotFrames("S1") || 90) / CU.FPS);
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
    s = sub.add_parser("draft"); s.add_argument("film"); s.add_argument("--shots"); s.add_argument("--dir"); s.set_defaults(fn=cmd_draft)
    s = sub.add_parser("fix"); s.add_argument("film"); s.add_argument("shots", nargs="+"); s.add_argument("--dir"); s.set_defaults(fn=cmd_fix)
    s = sub.add_parser("uses"); s.add_argument("film"); s.add_argument("funcs", nargs="+"); s.add_argument("--dir"); s.set_defaults(fn=cmd_uses)
    s = sub.add_parser("status"); s.add_argument("film", nargs="?"); s.add_argument("--dir"); s.set_defaults(fn=cmd_status)
    s = sub.add_parser("sheet"); s.add_argument("film"); s.add_argument("--only"); s.add_argument("--dir"); s.set_defaults(fn=cmd_sheet)
    s = sub.add_parser("rigs"); s.add_argument("--check", action="store_true"); s.add_argument("--lock"); s.set_defaults(fn=cmd_rigs)
    s = sub.add_parser("new"); s.add_argument("film"); s.add_argument("--fps", type=int, default=30); s.add_argument("--dir"); s.set_defaults(fn=cmd_new)
    s = sub.add_parser("config"); s.add_argument("--afterfx"); s.add_argument("--aerender"); s.add_argument("--work"); s.set_defaults(fn=cmd_config)
    return p


def main(argv=None) -> int:
    a = parser().parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
