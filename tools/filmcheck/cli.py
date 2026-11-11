"""Script review, film checks and the publish pack (specs/010, 011): sh bin/studio script|web|qc|publish|config …

Runs the same way locally and inside an online job container. Only `script review` calls Claude (contracts/cli.md)."""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from filmcheck import editor, report, script, webfetch  # noqa: E402

NORMAL_ROUNDS = 3        # the first review and at most 2 fix rounds (FR-010)
EDITOR_PASS = 8.0


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def film_dir(name: str) -> Path:
    """A folder path as given, else films/<name> in the working folder, else in STUDIO_ROOT."""
    p = Path(name)
    if p.is_dir() and (os.sep in name or name.startswith(".")):
        return p.resolve()
    for base in (Path.cwd(), Path(os.environ.get("STUDIO_ROOT") or HERE.parents[1])):
        if (base / "films" / name).is_dir():
            return (base / "films" / name).resolve()
    raise SystemExit(f"✗ film folder not found: films/{name}")


def online() -> bool:
    return os.environ.get("STUDIO_MODE") == "online" and bool(os.environ.get("STUDIO_JOB"))


def has_narration(d: Path) -> bool:
    return (d / "narration.json").is_file() or (d / "voices").is_dir() or any(d.glob("**/words.json"))


def out(a, data: dict, lines: list) -> None:
    if getattr(a, "json", False):
        print(json.dumps(data, ensure_ascii=False))
    else:
        print("\n".join(lines))


# ---------- script check ----------
def issue_line(i: dict) -> str:
    where = f"{i['para']}.{i['sentence']}" if i.get("sentence") else i["para"]
    return f"  {where} {i['rule']} {i.get('detail', '')}".rstrip()


def run_check(d: Path, customer_round: bool):
    r = script.check(d, customer_round=customer_round)

    def save(x):
        x["narration"] = True
        if x["script"]["verdict"] == "skipped":
            x["script"]["verdict"], x["script"]["skip_reason"] = "pending", None
        x["script"]["machine"].append({"round": len(x["script"]["machine"]) + 1, "score": r["score"], "hard": r["hard"],
                                       "issues": r["issues"], "est_seconds": r["est_seconds"], "at": now()})
    report.update(d, save)
    return r


def cmd_check(a) -> int:
    d = film_dir(a.film)
    try:
        r = run_check(d, a.customer_round)
    except script.ScriptError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    failed = [k for k, ok in r["hard"].items() if not ok]
    lines = [issue_line(i) for i in r["issues"]]
    lines.append(f"{'✓' if r['pass'] else '✗'} script check: {r['score']}/10 (pass ≥ {script.PASS_SCORE:g})"
                 + (f" · failed: {', '.join(failed)}" if failed else "") + f" · reads in about {r['est_seconds']:.0f} s")
    out(a, r, lines)
    return 0 if r["pass"] else 1


# ---------- script review ----------
def changed_since_pass(d: Path, data: dict) -> bool:
    """SCRIPT.md differs from the version the editor passed last."""
    eds = [e for e in data["script"]["editor"] if e.get("passed")]
    if not eds:
        return False
    snap = d / ".check" / f"script-r{eds[-1]['round']}.md"
    try:
        return script.para_map(script.read_script(snap)) != script.para_map(script.read_script(d / "SCRIPT.md"))
    except script.ScriptError:
        return True


def cmd_review(a) -> int:
    d = film_dir(a.film)
    data = report.load(d)
    normal = [e for e in data["script"]["editor"] if not e.get("customer_round")]
    if data["script"]["verdict"] == "failed" and not a.customer_round:
        print("✗ the script already failed review after 2 fix rounds; stop the film", file=sys.stderr)
        return 3
    try:
        r = run_check(d, a.customer_round)
    except script.ScriptError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    if not r["pass"]:
        print("\n".join(issue_line(i) for i in r["issues"]))
        print(f"✗ run `script check` until it passes first ({r['score']}/10)")
        return 1
    if len(normal) >= NORMAL_ROUNDS and not a.customer_round:
        print("✗ no review rounds left", file=sys.stderr)
        return 3
    n = len(data["script"]["editor"]) + 1
    chk = d / ".check"
    chk.mkdir(exist_ok=True)
    snap = chk / f"script-r{n}.md"
    shutil.copyfile(d / "SCRIPT.md", snap)
    paras = {p["id"] for p in script.read_script(d / "SCRIPT.md")["paragraphs"]}
    try:
        got = editor.run(d, paras)
    except editor.EditorError as e:
        snap.unlink(missing_ok=True)
        print(f"✗ {e}", file=sys.stderr)
        return 2
    (chk / f"review-r{n}.json").write_text(json.dumps(got, ensure_ascii=False, indent=1), encoding="utf-8")
    issues = got.get("issues", [])
    level = {k: sum(1 for i in issues if i["level"] == k) for k in ("P1", "P2", "P3")}
    passed = not got.get("bad") and got["score"] >= EDITOR_PASS and level["P1"] == 0
    rounds_after = len(normal) + (0 if a.customer_round else 1)

    def save(x):
        s = x["script"]
        s["editor"].append({"round": n, "model": got.get("model"), "score": got.get("score"), "p1": level["P1"],
                            "p2": level["P2"], "p3": level["P3"], "issues": issues, "passed": passed,
                            "bad_answer": bool(got.get("bad")), "customer_round": bool(a.customer_round), "at": now()})
        s["fix_rounds"] = max(0, len([e for e in s["editor"] if not e.get("customer_round")]) - 1)
        if passed:
            s["verdict"] = "pass"
        elif not a.customer_round and rounds_after >= NORMAL_ROUNDS:
            s["verdict"] = "failed"
        else:
            s["verdict"] = "pending"
    data = report.update(d, save)
    lines = [f"  {i['level']} {i['para']}: {i['reason']}" for i in issues]
    if got.get("bad"):
        lines.append("  the editor's answer did not follow the schema twice; this counts as a round that did not pass")
    verdict = data["script"]["verdict"]
    score = "no score" if got.get("bad") else f"{got['score']}/10"
    if verdict == "pass":
        lines.append(f"✓ script review: {score}, no P1 (round {n})")
        code = 0
    elif verdict == "failed":
        lines.append(f"✗ script review: {score} with {level['P1']} P1 after 2 fix rounds: the script did not pass; stop the film")
        code = 3
    else:
        left = "" if a.customer_round else f" · {NORMAL_ROUNDS - rounds_after} fix round(s) left"
        lines.append(f"✗ script review: {score} with {level['P1']} P1 (pass: ≥ {EDITOR_PASS:g} and no P1). "
                     f"Change only the paragraphs with P1 or P2, then run `script review` again{left}")
        code = 1
    out(a, {"verdict": verdict, "round": n, **{k: v for k, v in got.items() if k != "usage"}}, lines)
    return code


# ---------- script status / skip ----------
def cmd_status(a) -> int:
    d = film_dir(a.film)
    data = report.load(d)
    s = data["script"]
    verdict = s["verdict"]
    if verdict == "pass" and changed_since_pass(d, data):
        verdict = "pending"
    m = s["machine"][-1]["score"] if s["machine"] else None
    e = s["editor"][-1]["score"] if s["editor"] else None
    info = {"verdict": verdict, "machine_score": m, "editor_score": e, "fix_rounds": s.get("fix_rounds", 0),
            "changed_since_pass": verdict != s["verdict"], "skip_reason": s.get("skip_reason")}
    line = f"script: {verdict}" + (f" ({s['skip_reason']})" if verdict == "skipped" else "") \
        + f" · machine {m if m is not None else '–'} · editor {e if e is not None else '–'} · fix rounds {info['fix_rounds']}"
    if info["changed_since_pass"]:
        line += " · SCRIPT.md changed after the editor passed it: run `script review` again"
    out(a, info, [line])
    return {"pass": 0, "skipped": 0, "pending": 1, "failed": 3}[verdict]


def cmd_skip(a) -> int:
    d = film_dir(a.film)
    if has_narration(d):
        print("✗ the film has narration (voices/ or narration.json): its script must be reviewed", file=sys.stderr)
        return 1

    def save(x):
        x["narration"] = False
        x["script"].update(verdict="skipped", skip_reason=a.reason[:200])
    report.update(d, save)
    print(f"✓ script step skipped: {a.reason[:200]}")
    return 0


# ---------- web fetch ----------
def fetch_online(url: str) -> dict:
    import urllib.error
    import urllib.request
    base = os.environ.get("STUDIO_PROXY", "http://proxy:8780").rstrip("/")
    token = os.environ.get("STUDIO_JOB_TOKEN") or os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or ""
    req = urllib.request.Request(base + "/internal/web/fetch", data=json.dumps({"url": url}).encode(), method="POST",
                                 headers={"content-type": "application/json", "authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read())["error"]
        except Exception:     # noqa: BLE001
            err = {}
        raise webfetch.FetchError(err.get("code") or err.get("type") or "proxy",
                                  err.get("message") or f"the studio answered {e.code}", e.code) from None
    except (urllib.error.URLError, OSError) as e:
        raise webfetch.FetchError("unreachable", f"the studio proxy cannot be reached: {e}", 502) from None


def take_page() -> bool:
    """One page from the editor's budget, when `script review` set one (STUDIO_FETCH_BUDGET_FILE)."""
    f = os.environ.get("STUDIO_FETCH_BUDGET_FILE")
    if not f:
        return True
    try:
        left = int(Path(f).read_text().strip() or 0)
    except (OSError, ValueError):
        left = 0
    if left <= 0:
        return False
    Path(f).write_text(str(left - 1))
    return True


def cmd_fetch(a) -> int:
    if not take_page():
        print(f"✗ fetch_limit: the editor may open at most {editor.EDITOR_PAGES} pages per review", file=sys.stderr)
        return 1
    try:
        r = fetch_online(a.url) if online() else webfetch.fetch(a.url)
    except webfetch.FetchError as e:
        print(f"✗ {e.code}: {e.message}", file=sys.stderr)
        return 1
    if a.film:
        d = film_dir(a.film)
        chk = d / ".check"
        chk.mkdir(parents=True, exist_ok=True)
        p = chk / "opened.json"
        try:
            rows = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            rows = []
        rows.append({"url": a.url, "final_url": r["final_url"], "status": r["status"], "at": now()})
        p.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"status {r['status']} {r['final_url']}")
    print(r["text"])
    return 0


# ---------- qc ----------
def cmd_qc(a) -> int:
    from filmcheck import qc
    d = film_dir(a.film)
    lib = os.environ.get("STUDIO_LIB") or str(HERE.parents[1] / "lib" / "lemo-opuscar")
    try:
        r = qc.measure(d, lib)
    except qc.QcError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2

    def save(x):
        x["film"] = {"pass": r["pass"], "measures": r["measures"], "problems": r["problems"], "at": now()}
        if x.get("narration") is None:
            x["narration"] = r["narration"]
    report.update(d, save)
    m = r["measures"]
    lines = [f"  ✗ {p}" for p in r["problems"]]
    if r["narration"]:
        lines.append(f"  silence {m['silence_ratio']:.0%} · tail {m['tail_s']:.1f} s · {len(m.get('cuts', []))} cuts")
    if not m["texts_checked"]:
        lines.append("  on-screen text not checked (the film has no window.TEXTS); subtitles checked")
    lines.append(f"{'✓' if r['pass'] else '✗'} qc: " + ("all checks pass" if r["pass"] else f"{len(r['problems'])} problem(s)"))
    out(a, r, lines)
    return 0 if r["pass"] else 1


# ---------- publish (specs/011) ----------
def cmd_publish(a) -> int:
    from filmcheck import publish
    d = film_dir(a.film)
    lib = os.environ.get("STUDIO_LIB") or str(HERE.parents[1] / "lib" / "lemo-opuscar")
    try:
        pack = publish.read_pack(d)
        made = [] if a.check_only else publish.build(d, lib, draw=not a.no_draw)
        r = publish.check(d, pack)
    except publish.PublishError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    for p in made:                      # a thumbnail that could not be drawn is reported by the check too
        if p not in r["problems"] and not any(x.startswith(p.split(":")[0]) for x in r["problems"]):
            r["problems"].append(p)
    r["pass"] = not r["problems"]
    publish.save(d, r, now())
    if not a.check_only:
        publish.finish(d, r)
    lines = [f"  ✗ {p}" for p in r["problems"]]
    na = [k for k, v in r["applicable"].items() if not v]
    if na:
        lines.append("  not applicable: " + ", ".join(na))
    lines.append(f"{'✓' if r['pass'] else '✗'} publish: " + ("the pack passes every check" if r["pass"]
                                                             else f"{len(r['problems'])} problem(s)")
                 + f" · films/{d.name}/publish/PUBLISH.md")
    out(a, {**r}, lines)
    return 0 if r["pass"] else 1


# ---------- channels and lessons (specs/012) ----------
def root() -> Path:
    return Path(os.environ.get("STUDIO_ROOT") or HERE.parents[1])


def lib_dir() -> Path:
    return Path(os.environ.get("STUDIO_LIB") or HERE.parents[1] / "lib" / "lemo-opuscar")


def channel_cmd(fn):
    def run(a):
        from filmcheck import channels
        try:
            return fn(a, channels) or 0
        except channels.ChannelError as e:
            print(f"✗ {e}", file=sys.stderr)
            return 2
    return run


@channel_cmd
def cmd_channel_list(a, channels):
    rows = channels.list_channels(root())
    out(a, {"channels": rows}, [f"  {c['slug']:<20} {c.get('name', '')} · {c.get('language')} · {c.get('style')} · "
                                f"{c['lessons_active']} lessons" for c in rows] or ["  no channels yet: sh bin/studio channel new …"])


@channel_cmd
def cmd_channel_new(a, channels):
    ch = {"slug": a.slug, "name": a.name, "language": a.language, "seconds": a.seconds, "style": a.style,
          "voice": a.voice, "speed": a.speed}
    ch = channels.save(root(), ch, lib_dir(), new=True)
    print(f"✓ channel {ch['slug']}: channels/{ch['slug']}/CHANNEL.md")


@channel_cmd
def cmd_channel_show(a, channels):
    ch = channels.load(root(), a.slug)
    errs = channels.validate(channels.normal(ch), root(), lib_dir())
    out(a, {**ch, "problems": errs}, [channels.channel_md(channels.normal(ch)).rstrip()] + [f"  ✗ {e}" for e in errs])
    return 1 if errs else 0


LIST_FIELDS = ("hashtags", "banned")
INT_FIELDS = ("seconds", "title_max")


@channel_cmd
def cmd_channel_set(a, channels):
    ch = channels.load(root(), a.slug)
    f, vals = a.field, a.values
    if f in LIST_FIELDS:
        cur = list(ch.get(f) or [])
        if a.add:
            cur += [v for v in a.add if v not in cur]
        elif a.remove:
            cur = [v for v in cur if v not in a.remove]
        else:
            cur = vals
        ch[f] = cur
    elif f in INT_FIELDS:
        ch[f] = None if vals in ([], [""], ["none"]) else int(vals[0])
    elif f == "speed":
        ch[f] = float(vals[0])
    elif f in ("name", "niche", "audience", "language", "style", "voice", "title_rules", "thumbnail_rules"):
        ch[f] = " ".join(vals)
    else:
        raise channels.ChannelError(f"unknown field {f}")
    channels.save(root(), ch, lib_dir())
    print(f"✓ {a.slug}: {f} saved")


@channel_cmd
def cmd_channel_decide(a, channels):
    channels.decide(root(), a.slug, a.text, lib_dir())
    print(f"✓ {a.slug}: decision added")


@channel_cmd
def cmd_channel_attach(a, channels):
    over = {k: getattr(a, k) for k in ("style", "seconds", "language", "voice", "speed") if getattr(a, k) is not None}
    r = channels.attach(root(), film_dir(a.film) if not a.new else Path(root()) / "films" / a.film, a.slug,
                        lib=lib_dir(), **over)
    if r["warning"]:
        print(f"! {r['warning']}")
    print(f"✓ films/{a.film}: channel {a.slug} attached; read films/{a.film}/CHANNEL_BRIEF.md before the treatment")


def scope_path(channels, scope):
    if scope != "shared":
        channels.load(root(), scope)               # the channel must exist
    return channels.lessons_file(root(), scope)


@channel_cmd
def cmd_lesson_list(a, channels):
    rows = [x for x in channels.load_lessons(scope_path(channels, a.scope))["lessons"] if a.all or x["status"] != "retired"]
    out(a, {"lessons": rows}, [f"  #{x['n']} {x['status']:<8} {x['what']} → {x['stop']}" + (f"  [{x['rule']}"
                               + ("" if x.get("rule_valid", True) else ", invalid") + "]" if x.get("rule") else "")
                               for x in rows] or ["  no lessons"])


def _add(a, channels, status):
    x = channels.add_lesson(scope_path(channels, a.scope), what=a.what, why=a.why, stop=a.stop, film=a.film,
                            rule=a.rule, status=status, title=a.scope)
    if x.get("rule") and not x["rule_valid"]:
        print(f"! the rule \"{x['rule']}\" cannot be read, so it will not be checked (use phrase:…, "
              "max_sentence_words:N or max_title_chars:N)")
    print(f"✓ lesson #{x['n']} ({status}) for {a.scope}: {x['what']} → {x['stop']}")
    if status == "draft":
        print(f"  approve it with: sh bin/studio lesson approve {a.scope} {x['n']}")


@channel_cmd
def cmd_lesson_draft(a, channels):
    _add(a, channels, "draft")


@channel_cmd
def cmd_lesson_add(a, channels):
    _add(a, channels, "active")


@channel_cmd
def cmd_lesson_approve(a, channels):
    x = channels.approve(scope_path(channels, a.scope), a.n, a.scope)
    print(f"✓ lesson #{x['n']} is active")


@channel_cmd
def cmd_lesson_retire(a, channels):
    x = channels.retire(scope_path(channels, a.scope), a.n, a.scope)
    print(f"✓ lesson #{x['n']} retired")


# ---------- config ----------
def cmd_editor_model(a) -> int:
    editor.set_editor_model(a.value)
    print(f"✓ script editor model: {a.value}" + (" (same as the film)" if a.value == "inherit" else ""))
    return 0


def not_yet(a) -> int:
    print(f"✗ not built yet: {a.cmd}", file=sys.stderr)
    return 2


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="studio", description="Script review and film checks (specs/010)")
    sub = p.add_subparsers(dest="group", required=True)

    sc = sub.add_parser("script", help="score and review a film's SCRIPT.md").add_subparsers(dest="cmd", required=True)
    for name in ("check", "review", "status"):
        s = sc.add_parser(name)
        s.add_argument("film")
        s.add_argument("--json", action="store_true")
        if name in ("check", "review"):
            s.add_argument("--customer-round", action="store_true", help="a round the customer asked for (FR-019)")
    s = sc.add_parser("skip")
    s.add_argument("film")
    s.add_argument("--reason", required=True)

    w = sub.add_parser("web", help="open a web page").add_subparsers(dest="cmd", required=True)
    s = w.add_parser("fetch")
    s.add_argument("url")
    s.add_argument("--film")

    q = sub.add_parser("qc", help="measure a finished film")
    q.add_argument("film")
    q.add_argument("--json", action="store_true")

    pb = sub.add_parser("publish", help="make and check a film's publish pack (specs/011)")
    pb.add_argument("film")
    pb.add_argument("--check-only", action="store_true", help="check the files as they are; draw nothing")
    pb.add_argument("--no-draw", action="store_true", help="make the text files only; keep the thumbnails as they are")
    pb.add_argument("--json", action="store_true")

    ch = sub.add_parser("channel", help="the profiles of your own channels (specs/012)").add_subparsers(dest="cmd", required=True)
    s = ch.add_parser("list")
    s.add_argument("--json", action="store_true")
    s = ch.add_parser("new")
    s.add_argument("slug")
    s.add_argument("--name", required=True)
    s.add_argument("--language", required=True)
    s.add_argument("--seconds", type=int, required=True)
    s.add_argument("--style", required=True)
    s.add_argument("--voice")
    s.add_argument("--speed", type=float, default=1.0)
    s = ch.add_parser("show")
    s.add_argument("slug")
    s.add_argument("--json", action="store_true")
    s = ch.add_parser("set")
    s.add_argument("slug")
    s.add_argument("field")
    s.add_argument("values", nargs="*")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--add", nargs="+", metavar="VALUE", help="add to hashtags or banned")
    g.add_argument("--remove", nargs="+", metavar="VALUE", help="remove from hashtags or banned")
    s = ch.add_parser("decide")
    s.add_argument("slug")
    s.add_argument("text")
    s = ch.add_parser("attach")
    s.add_argument("film")
    s.add_argument("slug")
    s.add_argument("--style")
    s.add_argument("--seconds", type=int)
    s.add_argument("--language")
    s.add_argument("--voice")
    s.add_argument("--speed", type=float)
    s.add_argument("--new", action="store_true", help="the film folder does not exist yet")

    ls = sub.add_parser("lesson", help="lessons of a channel, or 'shared' (specs/012)").add_subparsers(dest="cmd", required=True)
    s = ls.add_parser("list")
    s.add_argument("scope")
    s.add_argument("--all", action="store_true")
    s.add_argument("--json", action="store_true")
    for name in ("draft", "add"):
        s = ls.add_parser(name)
        s.add_argument("scope")
        s.add_argument("--what", required=True)
        s.add_argument("--why", required=True)
        s.add_argument("--stop", required=True)
        s.add_argument("--film")
        s.add_argument("--rule")
    for name in ("approve", "retire"):
        s = ls.add_parser(name)
        s.add_argument("scope")
        s.add_argument("n", type=int)

    c = sub.add_parser("config", help="local settings").add_subparsers(dest="cmd", required=True)
    s = c.add_parser("editor-model")
    s.add_argument("value", choices=list(editor.MODELS))
    return p


COMMANDS = {("script", "check"): cmd_check, ("script", "review"): cmd_review, ("script", "status"): cmd_status,
            ("script", "skip"): cmd_skip, ("web", "fetch"): cmd_fetch, ("config", "editor-model"): cmd_editor_model,
            ("qc", "qc"): cmd_qc, ("publish", "publish"): cmd_publish,
            ("channel", "list"): cmd_channel_list, ("channel", "new"): cmd_channel_new,
            ("channel", "show"): cmd_channel_show, ("channel", "set"): cmd_channel_set,
            ("channel", "decide"): cmd_channel_decide, ("channel", "attach"): cmd_channel_attach,
            ("lesson", "list"): cmd_lesson_list, ("lesson", "draft"): cmd_lesson_draft, ("lesson", "add"): cmd_lesson_add,
            ("lesson", "approve"): cmd_lesson_approve, ("lesson", "retire"): cmd_lesson_retire}


def main(argv=None) -> int:
    a = parser().parse_args(argv)
    if a.group in ("qc", "publish"):
        a.cmd = a.group
    return COMMANDS.get((a.group, a.cmd), not_yet)(a)


if __name__ == "__main__":
    sys.exit(main())
