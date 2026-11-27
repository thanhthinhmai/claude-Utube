"""sh bin/studio camera … (specs/039 contracts/cli.md): camera options per shot, the choice, retime, stills, notes.

Exit codes: 0 done · 1 not done · 2 bad input (no library, not an AE film, bad value) · 3 missing engine, no GPU or
no bridge."""
import json
import sys
from pathlib import Path


def _out(a, data, lines):
    if getattr(a, "json", False):
        print(json.dumps(data, ensure_ascii=False))
    else:
        print("\n".join(lines))


def add_parser(sub) -> None:
    ca = sub.add_parser("camera", help="camera options per shot (specs/039)").add_subparsers(dest="cmd", required=True)
    s = ca.add_parser("suggest", help="2–3 camera options per shot from the style's camera library")
    s.add_argument("film"); s.add_argument("--style"); s.add_argument("--set", dest="refset")
    s.add_argument("--shots", help="only these shots, e.g. S3,S5"); s.add_argument("--keep-others", action="store_true")
    s.add_argument("--json", action="store_true")
    s = ca.add_parser("choose", help="pick an option of a shot (copied into shot_plan.<S>.camera)")
    s.add_argument("film"); s.add_argument("shot"); s.add_argument("n", type=int)
    s.add_argument("--by", choices=["owner", "claude"], default="owner")
    s.add_argument("--source", choices=["user", "note", "auto"], default="user"); s.add_argument("--json", action="store_true")
    s = ca.add_parser("retime", help="zoom and drift for the new shot lengths (rate per second kept)")
    s.add_argument("film"); s.add_argument("--json", action="store_true")
    s = ca.add_parser("show", help="options, choices and open notes")
    s.add_argument("film"); s.add_argument("--json", action="store_true")
    s = ca.add_parser("stills", help="a ¼ size first frame per option with the end-zoom box")
    s.add_argument("film"); s.add_argument("--shots"); s.add_argument("--json", action="store_true")
    no = ca.add_parser("note", help="Camera notes (pins)").add_subparsers(dest="ncmd", required=True)
    s = no.add_parser("add"); s.add_argument("film"); s.add_argument("shot"); s.add_argument("n", type=int)
    s.add_argument("x", type=float); s.add_argument("y", type=float); s.add_argument("text")
    s.add_argument("--base"); s.add_argument("--json", action="store_true")
    s = no.add_parser("remove"); s.add_argument("film"); s.add_argument("id"); s.add_argument("--base")
    s = no.add_parser("list"); s.add_argument("film"); s.add_argument("--json", action="store_true")
    s = no.add_parser("reply"); s.add_argument("film"); s.add_argument("id"); s.add_argument("--text", required=True)
    s.add_argument("--done", action="store_true"); s.add_argument("--base")


def _shots(text):
    return [x.strip() for x in text.split(",") if x.strip()] if text else None


def _claude_may_choose(d: Path, source: str) -> bool:
    """--by claude: only when the Camera point is off or skipped, or when a note is being answered."""
    if source == "note":
        return True
    from filmcheck import points
    if "camera" not in points.POINTS:
        return True
    return points.state(d, "camera") in ("off", "skipped")


def cmd_camera(a) -> int:
    from filmcheck import camsuggest
    from filmcheck.cli import film_dir
    d = film_dir(a.film)
    try:
        if a.cmd == "suggest":
            o = camsuggest.suggest(d, style=a.style, refset=a.refset, shots=_shots(a.shots), keep_others=a.keep_others)
            lines = []
            for sid, row in o["shots"].items():
                if a.shots and sid not in _shots(a.shots):
                    continue
                for x in row["options"]:
                    lines.append(camsuggest.line(sid, x, x["n"] == (row.get("choice") or {}).get("n")))
            lines.append(f"✓ camera options for {len(o['shots'])} shot(s) from {o['source']} → camera/options.json")
            _out(a, o, lines)
            return 0
        if a.cmd == "choose":
            if a.by == "claude" and not _claude_may_choose(d, a.source):
                print("✗ the Camera review is on: the owner picks (or answer a Camera note with --source note)",
                      file=sys.stderr)
                return 2
            r = camsuggest.choose(d, a.shot, a.n, by=a.by, source=a.source)
            c = r["camera"]
            _out(a, r, [f"✓ {a.shot} option {a.n}: {c['size']} {c['move']} {c['zoom_pct']:+.1f}% → shot_plan.{a.shot}.camera"])
            return 0
        if a.cmd == "retime":
            ch = camsuggest.retime(d)
            lines = [f"  {c['shot']} {c['dur0']:.1f}s→{c['dur1']:.1f}s"
                     + (f" zoom {c['zoom0']:.1f}→{c['zoom1']:.1f}%" if c.get("zoom0") is not None else "") for c in ch]
            lines.append(f"✓ retimed {len(ch)} shot(s)" if ch else "✓ shot lengths unchanged")
            _out(a, {"changes": ch}, lines)
            return 0
        if a.cmd == "show":
            o = camsuggest.load(d)
            if not o:
                print(f"✗ no camera options: run `sh bin/studio camera suggest {d.name}`", file=sys.stderr)
                return 2
            lines = []
            for sid, row in o["shots"].items():
                for x in row["options"]:
                    lines.append(camsuggest.line(sid, x, x["n"] == (row.get("choice") or {}).get("n")))
            try:
                from filmcheck import camnotes
                opn = camnotes.open_notes(d)
                o["open_notes"] = opn
                for sid, ns in opn.items():
                    for n in ns:
                        lines.append(f"  ✎ {sid} o{n.get('option')}: {n['text']}")
            except ImportError:
                pass
            try:
                from filmcheck import points
                if "camera" in points.POINTS:
                    o["point"] = points.state(d, "camera")
                    lines.append(f"Camera review: {o['point']}")
            except Exception:                     # noqa: BLE001 (show never fails on the review state)
                pass
            _out(a, o, lines)
            return 0
        if a.cmd == "stills":
            from filmcheck import camstills
            r = camstills.make(d, shots=_shots(a.shots), say=(lambda x: None) if a.json else print)
            _out(a, r, [f"✓ {len(r['stills'])} still(s) → camera/stills/ · {r['seconds']:.0f} s"])
            return 0
        if a.cmd == "note":
            from filmcheck import camnotes
            return camnotes.cli(a, d)
    except camsuggest.CameraError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    except Exception as e:                        # the stills' engine errors carry their own exit code
        code = getattr(e, "exit_code", None)
        if code:
            print(f"✗ {e}", file=sys.stderr)
            return code
        raise
    return 2


COMMANDS = {("camera", k): cmd_camera for k in ("suggest", "choose", "retime", "show", "stills", "note")}
