"""sh bin/studio sound … (specs/037 contracts/cli.md): the sound library, a film's sound plan, the mix, Sound notes.

Exit codes as 034/035: 0 done · 1 not done/blocked · 2 bad arguments · 3 missing condition · 4 changed (--base)."""
import json
import os
import sys
import time
from pathlib import Path


def _out(a, data, lines):
    if getattr(a, "json", False):
        print(json.dumps(data, ensure_ascii=False))
    else:
        print("\n".join(lines))


def _dur(d):
    return f"{d:.2f}s" if isinstance(d, (int, float)) else "?"


def add_parser(sub) -> None:
    so = sub.add_parser("sound", help="sound effects per shot (specs/037)").add_subparsers(dest="cmd", required=True)

    lib = so.add_parser("lib", help="the sound library on this machine").add_subparsers(dest="lcmd", required=True)
    s = lib.add_parser("add", help="add a Sonniss folder, then index it"); s.add_argument("folder")
    s = lib.add_parser("remove", help="forget a folder (its entries go at the next index)"); s.add_argument("folder")
    s = lib.add_parser("index", help="index again: only new or changed files"); s.add_argument("--full", action="store_true")
    s = lib.add_parser("status", help="folders, entries by source, broken files"); s.add_argument("--json", action="store_true")
    s = lib.add_parser("search", help="8 hits for a text query"); s.add_argument("query")
    s.add_argument("--cat"); s.add_argument("--dur", type=float); s.add_argument("--scope", choices=["all", "cc0"], default="all")
    s.add_argument("--online", action="store_true", help="fill a gap from Freesound (CC0) like the Sound step does")
    s.add_argument("--json", action="store_true")

    s = so.add_parser("key", help="save a service key (typed in, not shown)"); s.add_argument("service", choices=["freesound"])

    cue = so.add_parser("cue", help="a film's sounds").add_subparsers(dest="ccmd", required=True)
    s = cue.add_parser("add"); s.add_argument("film"); s.add_argument("shot")
    s.add_argument("--action", required=True); s.add_argument("--query", required=True); s.add_argument("--cat")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--motion"); g.add_argument("--line"); g.add_argument("--at", type=float); g.add_argument("--span", action="store_true")
    s.add_argument("--edge", choices=["start", "end"], default="start"); s.add_argument("--word")
    s.add_argument("--offset-f", type=int, default=0); s.add_argument("--len", type=float)
    s.add_argument("--gain", type=float); s.add_argument("--cut", choices=["hard", "fade", "over"]); s.add_argument("--fade", type=float)
    s.add_argument("--by", choices=["auto", "claude", "user"]); s.add_argument("--dir")
    s = cue.add_parser("set"); s.add_argument("film"); s.add_argument("cue")
    s.add_argument("--entry"); s.add_argument("--offset-f", type=int); s.add_argument("--gain", type=float)
    s.add_argument("--cut", choices=["hard", "fade", "over"]); s.add_argument("--fade", type=float); s.add_argument("--len", type=float)
    s.add_argument("--by", choices=["auto", "claude", "user"]); s.add_argument("--base"); s.add_argument("--dir")
    s = cue.add_parser("rm"); s.add_argument("film"); s.add_argument("cue"); s.add_argument("--base"); s.add_argument("--dir")

    si = so.add_parser("silence", help="a chosen moment of silence").add_subparsers(dest="scmd", required=True)
    s = si.add_parser("add"); s.add_argument("film"); s.add_argument("shot")
    g = s.add_mutually_exclusive_group(required=True); g.add_argument("--line"); g.add_argument("--at", type=float)
    s.add_argument("--word"); s.add_argument("--len", type=float, required=True); s.add_argument("--db", type=float, default=-57.0)
    s.add_argument("--dir")

    s = so.add_parser("shot", help="turn a shot's sound effects off or back on")
    s.add_argument("onoff", choices=["on", "off"]); s.add_argument("film"); s.add_argument("shots", nargs="+")
    s.add_argument("--base"); s.add_argument("--dir")

    s = so.add_parser("plan", help="the sounds by shot, resolved"); s.add_argument("film"); s.add_argument("--json", action="store_true")
    s.add_argument("--dir")
    s = so.add_parser("mix", help="resolve, copy, mix out/mix.wav, stems and CREDITS"); s.add_argument("film")
    s.add_argument("--json", action="store_true"); s.add_argument("--dir")

    no = so.add_parser("notes", help="Sound notes, one list per shot").add_subparsers(dest="ncmd", required=True)
    s = no.add_parser("add"); s.add_argument("film"); s.add_argument("shot"); s.add_argument("--text", required=True)
    s.add_argument("--base"); s.add_argument("--dir")
    s = no.add_parser("delete"); s.add_argument("film"); s.add_argument("shot"); s.add_argument("note")
    s.add_argument("--base"); s.add_argument("--dir")
    s = no.add_parser("show"); s.add_argument("film"); s.add_argument("--json", action="store_true"); s.add_argument("--dir")
    s = no.add_parser("reply"); s.add_argument("film"); s.add_argument("note"); s.add_argument("--text", required=True)
    g = s.add_mutually_exclusive_group(); g.add_argument("--done", action="store_true"); g.add_argument("--open", action="store_true")
    s.add_argument("--base"); s.add_argument("--dir")


def _fd(a):
    from filmcheck import cli
    if getattr(a, "dir", None):
        return Path(a.dir).resolve()
    return cli.film_dir(a.film)


def _scope() -> str:
    return "all"                       # the command line is the studio owner (R5); app jobs go through the proxy


# ---------- library ----------
def cmd_lib(a) -> int:
    from filmcheck import freesound, soundlib
    try:
        if a.lcmd == "add":
            row = soundlib.add_root(a.folder)
            print(f"✓ added {row['path']}")
            return _index(False)
        if a.lcmd == "remove":
            soundlib.remove_root(a.folder)
            print("✓ removed; run: sh bin/studio sound lib index")
            return 0
        if a.lcmd == "index":
            return _index(a.full)
        if a.lcmd == "status":
            st = soundlib.status()
            st["freesound_key"] = freesound.has_key()
            lines = [f"library: {st['folder']}"] + [f"  {r['path']} ({r['kind']})" for r in st["roots"]]
            lines += [f"  {k}: {v} sounds" for k, v in sorted(st["by_source"].items())] or ["  no sounds yet"]
            lines += [f"  broken files: {st['broken']}"] + [f"    {p}" for p in st["broken_files"][:10]]
            lines.append(f"  Freesound key: {'yes' if st['freesound_key'] else 'no'}")
            _out(a, st, lines)
            return 0
        if a.lcmd == "search":
            hits = (soundlib.find if a.online else soundlib.search)(a.query, a.cat, a.dur, a.scope)
            _out(a, {"results": hits}, [f"{h['id']}  {h['name']}  [{h['category'] or '-'}]  {_dur(h['duration'])}  "
                                         f"{h['source']}" for h in hits] or ["no sound found"])
            return 0 if hits else 1
    except soundlib.LibraryError as e:
        print(f"✗ {e.message}", file=sys.stderr)
        return 3 if e.code in ("forbidden", "not_found") else 1
    return 2


def _index(full: bool) -> int:
    from filmcheck import soundlib
    r = soundlib.index(full=full, progress=lambda c: print(f"  … {c['new'] + c['changed']} files", flush=True))
    print(f"indexed {r['new']} new · {r['changed']} changed · {r['gone']} gone · {r['broken']} broken · {r['secs']} s")
    return 0


def cmd_key(a) -> int:
    """Read the key from stdin, try it once, keep it in .env (the app keeps its own in Settings)."""
    from filmcheck import eleven, freesound
    import getpass
    k = (sys.stdin.readline() if not sys.stdin.isatty() else getpass.getpass("Freesound API key: ")).strip()
    if not k:
        print("✗ no key given", file=sys.stderr)
        return 2
    try:
        freesound.check(k)
    except freesound.FreesoundError as e:
        print(f"✗ {freesound.redact(e.message, k)}", file=sys.stderr)
        return 1
    env = eleven.root() / ".env"
    lines = env.read_text(encoding="utf-8").splitlines() if env.is_file() else []
    lines = [ln for ln in lines if not ln.strip().startswith(("FREESOUND_API_KEY=", "export FREESOUND_API_KEY="))]
    lines.append(f"FREESOUND_API_KEY={k}")
    fd = os.open(env, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"✓ Freesound key saved in .env (…{k[-4:]})")
    return 0


# ---------- a film's sounds ----------
def _plan_err(e) -> int:
    print(f"✗ {e.message}", file=sys.stderr)
    return {"changed": 4, "bad": 2, "missing": 3, "off": 5}.get(e.code, 1)


def cmd_cue(a) -> int:
    from filmcheck import soundplan
    d = _fd(a)
    by = getattr(a, "by", None) or ("claude" if os.environ.get("STUDIO_JOB") else "user")   # rm has no --by
    try:
        if a.ccmd == "add":
            anchor = ({"motion": a.motion, "edge": a.edge, "offset_f": a.offset_f} if a.motion else
                      {"line": a.line, **({"word": a.word} if a.word else {}), "offset_f": a.offset_f} if a.line else
                      {"shot_at": a.at} if a.at is not None else {"span": "shot"})
            c = soundplan.add_cue(d, a.shot, a.action, anchor, a.query, cat=a.cat, len_s=a.len, gain_db=a.gain,
                                  cut=a.cut, fade_s=a.fade, by=by, scope=_scope())
        elif a.ccmd == "set":
            fields = {k: v for k, v in (("entry", a.entry), ("offset_f", a.offset_f), ("gain_db", a.gain), ("cut", a.cut),
                                        ("fade_s", a.fade), ("len_s", a.len)) if v is not None}
            c = soundplan.set_cue(d, a.cue, fields, by=by, base=a.base)
        else:
            soundplan.rm_cue(d, a.cue, base=a.base)
            print(f"✓ {a.cue} removed")
            return 0
    except soundplan.PlanError as e:
        return _plan_err(e)
    at = f"{c['at']:.2f}s" if c.get("at") is not None else "-"
    extra = f" ({c['why']})" if c.get("why") else ""
    print(f"✓ {c['id']} {c['shot']} {c['action']} @ {at} → {c.get('entry') or 'missing'} [{c['state']}]{extra}")
    return 0


def cmd_silence(a) -> int:
    from filmcheck import soundplan
    anchor = {"line": a.line, **({"word": a.word} if a.word else {})} if a.line else {"shot_at": a.at}
    try:
        s = soundplan.add_silence(_fd(a), a.shot, anchor, a.len, a.db)
    except soundplan.PlanError as e:
        return _plan_err(e)
    print(f"✓ silence {s['shot']} {a.len:.2f}s at {s.get('at', 0):.2f}s, {a.db:g} dB")
    return 0


def cmd_shot(a) -> int:
    from filmcheck import soundplan
    try:
        p = soundplan.set_shots(_fd(a), a.shots, on=a.onoff == "on", base=a.base)
    except soundplan.PlanError as e:
        return _plan_err(e)
    print(f"✓ sound {a.onoff}: {', '.join(a.shots)}" + (f"  (off now: {', '.join(p['off'])})" if p["off"] else ""))
    return 0


def cmd_plan(a) -> int:
    from filmcheck import soundplan
    d = _fd(a)
    try:
        p = soundplan.resolve(d, save=True)
    except soundplan.PlanError as e:
        return _plan_err(e)
    lines = []
    for shot in p["shots"]:
        lines.append(f"{shot} (t0 {p['t0'][shot]:.2f}s)" + (" · sound off" if shot in p.get("off", []) else ""))
        for c in [c for c in p["cues"] if c["shot"] == shot]:
            at = f"{c['at']:.2f}s" if c.get("at") is not None else "  -  "
            why = f"  ({c['why']})" if c.get("why") else ""
            lines.append(f"  {c['id']} {at} {c['action']} → {c.get('entry') or '-'} [{c['state']}, {c['by']}]{why}")
        for s in [s for s in p["silences"] if s["shot"] == shot]:
            lines.append(f"  silence {s.get('at', 0):.2f}s {s['len_s']:.2f}s {s['db']:g} dB")
    _out(a, p, lines or ["no sounds yet"])
    return 0


def cmd_mix(a) -> int:
    from filmcheck import soundmix, soundplan
    d = _fd(a)
    t = time.time()
    try:
        r = soundmix.run(d)
    except soundplan.PlanError as e:
        return _plan_err(e)
    r["secs"] = round(time.time() - t, 1)
    _out(a, r, [f"cues {r['placed']} placed · {r['dropped']} dropped · {r['missing']} missing · "
                + (f"{r['off']} off · " if r.get("off") else "") + f"{r['secs']} s",
                f"  {r['mix']}"])
    return 0


def cmd_notes(a) -> int:
    from filmcheck import soundnotes as sn
    d = _fd(a)
    try:
        if a.ncmd == "add":
            n = sn.add(d, a.shot, a.text, by="claude" if os.environ.get("STUDIO_JOB") else "owner", b=a.base)
            print(f"✓ note {n['id']} on {n['shot']}")
        elif a.ncmd == "delete":
            sn.delete(d, a.shot, a.note, b=a.base)
            print(f"✓ note {a.note} deleted")
        elif a.ncmd == "reply":
            n = sn.reply(d, a.note, a.text, True if a.done else False if a.open else None, b=a.base)
            print(f"✓ {n['id']} on {n['shot']}: {'done' if n['done'] else 'open'}")
        elif getattr(a, "json", False):
            print(json.dumps({"base": sn.base(d), **sn.load(d)}, ensure_ascii=False))
        else:
            print(sn.show(d))
    except sn.SoundNoteError as e:
        print(f"✗ {e.code}: {e.message}", file=sys.stderr)
        return e.exit_code()
    return 0


def cmd_sound(a) -> int:
    return {"lib": cmd_lib, "key": cmd_key, "cue": cmd_cue, "silence": cmd_silence, "plan": cmd_plan,
            "mix": cmd_mix, "shot": cmd_shot, "notes": cmd_notes}[a.cmd](a)


COMMANDS = {("sound", k): cmd_sound for k in ("lib", "key", "cue", "silence", "plan", "mix", "shot", "notes")}
