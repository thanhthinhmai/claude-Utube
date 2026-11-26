"""Script review, film checks and the publish pack (specs/010, 011): sh bin/studio script|web|qc|publish|config …

Runs the same way locally and inside an online job container. Only `script review` calls Claude (contracts/cli.md)."""
import argparse
import json
import tempfile
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from filmcheck import editor, eleven, report, script, speakers, voicecat, voicefx, webfetch  # noqa: E402

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

    r["shots_file"] = qc.film_shots(d, lib)                    # specs/029: shots.json beside the film (not a check)

    def save(x):
        x["film"] = {"pass": r["pass"], "measures": r["measures"], "problems": r["problems"],
                     "warnings": r.get("warnings", []), "shots_file": r["shots_file"], "at": now()}
        if x.get("narration") is None:
            x["narration"] = r["narration"]
    report.update(d, save)
    from filmcheck import tiers
    fin = [{"tier": "final", "ref": "film", "at": None, "rule": "qc", "severity": "block", "measure": p, "limit": "",
            "text": "", "fix": "", "excepted": None} for p in r["problems"]]
    warns = [w if isinstance(w, dict) else {"rule": "loudness_range", "text": w, "measure": w, "limit": ""}
             for w in r.get("warnings", [])]
    fin += [{"tier": "final", "ref": "film", "at": None, "rule": w["rule"], "severity": "warn", "measure": w.get("measure"),
             "limit": w.get("limit", ""), "text": w.get("text", ""), "fix": "", "excepted": None} for w in warns]
    fin += [{"tier": "final", "ref": x["ref"], "at": None, "rule": x["rule"], "severity": "block", "measure": x["text"],
             "limit": "", "text": "", "fix": "", "excepted": {"reason": x["reason"]}} for x in r["measures"].get("excepted", [])]
    tiers.save_tier(d, "final", tiers.result("final", fin, {k: r["measures"].get(k) for k in
                                                           ("silence_ratio", "tail_s", "av_sync", "loudness_range", "motion")},
                                             [], 0.0, tiers.fingerprint(d)))
    m = r["measures"]
    lines = [f"  ✗ {p}" for p in r["problems"]] + [f"  ! {w['text']}" for w in warns]
    lines += [f"  · {x['text']}  (excepted: {x['reason']})" for x in m.get("excepted", [])]
    shots = tiers.load_tier(d, "shots") or {}
    open_style = [i for i in shots.get("issues", []) if i["severity"] == "warn"]
    acc = (shots.get("style_accept") or {}).get("reason")
    for i in open_style:                                       # FR-013: every open style warning, with its reason
        lines.append(f"  ! style (shots): {i['rule']} {i['measure']} outside {i['limit']}"
                     + (f" — accepted: {acc}" if acc else " — not accepted"))
    if r["narration"]:
        lines.append(f"  silence {m['silence_ratio']:.0%} · tail {m['tail_s']:.1f} s · {len(m.get('cuts', []))} cuts")
    if not m["texts_checked"]:
        lines.append("  on-screen text not checked (the film has no window.TEXTS); subtitles checked")
    lines.append(f"  {r['shots_file']}")
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
    if r["pass"]:                     # the film of a taken topic is made (specs/013 R4)
        from filmcheck import channels, topics
        snap = channels.snapshot(d)
        if snap and snap.get("topic"):
            try:
                data = topics.load(root(), snap["channel"])
                topics.mark_made(data, snap["topic"], d.name)
                topics.save(root(), snap["channel"], data)
            except topics.TopicError:
                pass
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
    elif f == "reviews":                                         # specs/026: reviews script,shots | none
        from filmcheck import points
        try:
            ch[f] = points.parse_list(",".join(vals))
            ch["cast_chosen"] = ch["animatic_chosen"] = True     # specs/034, 035: left out on purpose stays off
        except points.PointError as e:
            raise channels.ChannelError(str(e)) from None
    elif f == "hero":                                            # specs/022: hero hoodie=#d9b23a hair=bald …
        hero = dict(ch.get("hero") or {})
        for v in vals:
            k, eq, x = v.partition("=")
            if not eq or k not in channels.HERO_KEYS:
                raise channels.ChannelError(f"hero: use key=value with keys {', '.join(channels.HERO_KEYS)}")
            if k == "glasses":
                if x not in ("yes", "no"):
                    raise channels.ChannelError("hero.glasses: yes or no")
                hero[k] = x == "yes"
            elif k == "hat" and x in ("none", ""):
                hero[k] = None
            else:
                hero[k] = x
        ch[f] = hero
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
    over = {k: getattr(a, k) for k in ("style", "seconds", "language", "voice", "speed", "topic") if getattr(a, k) is not None}
    r = channels.attach(root(), film_dir(a.film) if not a.new else Path(root()) / "films" / a.film, a.slug,
                        lib=lib_dir(), **over)
    if r["warning"]:
        print(f"! {r['warning']}")
    print(f"✓ films/{a.film}: channel {a.slug} attached; read films/{a.film}/CHANNEL_BRIEF.md before the treatment")


def cmd_kit_use(a):
    """Copy the style's film kit into the film folder (specs/022 R1)."""
    from filmcheck import kit
    d = Path(root()) / "films" / a.film
    if not d.is_dir():
        d = film_dir(a.film)
    try:
        r = kit.use(root(), d, a.style, a.update)
    except kit.KitError as e:
        print(f"✗ kit: {e}", file=sys.stderr)
        return 2
    lines = ["kit: up to date" if r["status"] == "up_to_date" else
             f"✓ kit: {r['style']} ({r['sha256'][:8]}) → films/{d.name}/kit/"]
    if r["hint"]:
        lines.append(f"hint: {r['hint']}")
    out(a, r, lines)
    return 0


# ---------- people library (specs/028 US3) ----------
def _people_root():
    from filmcheck import people
    return people, Path(root())


def cmd_people_list(a):
    people, r = _people_root()
    rows = people.listing(r)
    out(a, rows, [f"{x['slug']:22s} {x['status']:24s} {x['name']} — {x['role']}" for x in rows] or ["(no people yet)"])
    return 0


def cmd_people_new(a):
    people, r = _people_root()
    try:
        d = people.new(a.slug, a.name, a.role or "", a.ref_url or "", a.license or "", a.author or "", a.from_file or "", r,
                       fetch=not a.ref_file, ref_file=a.ref_file or "")
    except (people.PeopleError, OSError) as e:
        print(f"✗ people: {e}", file=sys.stderr)
        return 1
    out(a, {"dir": str(d)}, [f"✓ people/{a.slug}/ (not approved): draw it, run people sheet, then ask the user"])
    return 0


def cmd_people_sheet(a):
    people, r = _people_root()
    try:
        p = people.sheet(a.slug, lib_dir(), r)
    except people.PeopleError as e:
        print(f"✗ people: {e}", file=sys.stderr)
        return 1
    out(a, {"sheet": str(p)}, [f"✓ sheet: {p}"])
    return 0


def cmd_people_approve(a):
    people, r = _people_root()
    try:
        ap = people.approve(a.slug, a.note or "", a.source, r)
    except people.PeopleError as e:
        print(f"✗ people: {e}", file=sys.stderr)
        return 2
    out(a, ap, [f"✓ {a.slug}: approved ({ap['hash']})"])
    return 0


def cmd_people_use(a):
    people, r = _people_root()
    try:
        d = people.use(a.film, a.slugs, r)
    except people.PeopleError as e:
        print(f"✗ people: {e}", file=sys.stderr)
        return 3 if "not approved" in str(e) else 2
    out(a, {"dir": str(d)}, [f"✓ films/{a.film}/people/: " + ", ".join(a.slugs)])
    return 0


def cmd_people_check(a):
    people, r = _people_root()
    probs = people.check_film(Path(r) / "films" / a.film, None, r)
    out(a, probs, [f"✗ {p['slug']}: {p['problem']}" for p in probs] or ["✓ every real person in the film is approved"])
    return 3 if probs else 0


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


# ---------- topics (specs/013) ----------
DAILY_UNITS = 9000


def topic_cmd(fn):
    def run(a):
        from filmcheck import channels, topics
        try:
            return fn(a, topics, channels) or 0
        except (topics.TopicError, channels.ChannelError) as e:
            print(f"✗ {e}", file=sys.stderr)
            return 2
        except topics.QuotaError as e:
            print(f"✗ {e}", file=sys.stderr)
            return 3
    return run


def usage_obj(topics):
    return topics.Usage(root() / ".studio" / "youtube-usage.json", int(os.environ.get("STUDIO_YOUTUBE_DAILY") or DAILY_UNITS))


def local_fetcher(topics):
    key = topics.read_key()
    if not key:
        raise topics.TopicError("no YouTube key yet: run `sh bin/studio config youtube-key` in your own terminal "
                                "(never paste the key into a chat)")
    return topics.Fetcher.local(key, usage_obj(topics), topics.Cache(root() / ".studio" / "youtube-cache")), key


def topic_line(t):
    s = t["scores"]
    tv = (t.get("evidence") or {}).get("top_video")
    line = (f"#{t['n']} {t['verdict']} {t['total']}/50  demand {s['demand']} · heat {s['heat']} · competition "
            f"{s['competition']} · overlap {s['overlap']} · fit {s['fit'] if s['fit'] is not None else '–'}  [{t['type']}]"
            f"  \"{t['text']}\"")
    if tv:
        line += f"\n   top: \"{tv['title'][:70]}\" · {tv['views']:,} views · {tv['age_days']} days"
    if t.get("note"):
        line += f"\n   note: {t['note']}"
    return line


def save_topics(topics, channels, slug, data):
    ch = channels.load(root(), slug)
    u = usage_obj(topics)
    topics.save(root(), slug, data, ch.get("name"), u.today(), u.limit)


def _score(a, topics, channels, texts):
    from filmcheck import topics_fit
    ch = channels.load(root(), a.channel)
    fetcher, key = local_fetcher(topics)
    refs = [r["id"] for r in topics.load_refs(root(), a.channel)]
    try:
        r = topics.score_batch(root(), a.channel, ch, texts, fetcher, suggest=getattr(a, "suggest", False), refs=refs,
                               fit=topics_fit.fit_for(ch))
    except topics.TopicError as e:
        raise topics.TopicError(topics.redact(str(e), key)) from None
    save_topics(topics, channels, a.channel, r["data"])
    rows = [x for x in r["data"]["topics"] if x["n"] in r["scored"] or x["status"] == "unscored"]
    lines = [topic_line(x) for x in rows]
    lines.append(f"{'✓' if not r['stopped'] else '!'} {len(r['scored'])} topic(s) scored · {r['units']} YouTube units · "
                 f"channels/{a.channel}/TOPICS.md" + (f" · stopped: {r['stopped']}" if r["stopped"] else ""))
    out(a, {"scored": r["scored"], "units": r["units"], "stopped": r["stopped"],
            "topics": [{k: v for k, v in x.items() if k != "raw"} for x in rows]}, [topics.redact(x, key) for x in lines])
    return 3 if r["stopped"] else 0


@topic_cmd
def cmd_topics_score(a, topics, channels):
    texts = list(a.topics or [])
    if a.file:
        texts += [ln.strip() for ln in Path(a.file).read_text(encoding="utf-8").splitlines() if ln.strip()]
    return _score(a, topics, channels, texts)


@topic_cmd
def cmd_topics_recheck(a, topics, channels):
    data = topics.load(root(), a.channel)
    pick = [topics.find(data, n) for n in a.n] if a.n else [t for t in data["topics"] if t["status"] in ("queued", "unscored", "blocked_reference")]
    if not pick:
        raise topics.TopicError("nothing to check again")
    a.suggest = False
    return _score(a, topics, channels, [t["text"] for t in pick])


@topic_cmd
def cmd_topics_queue(a, topics, channels):
    data = topics.load(root(), a.channel)
    order = topics.queue(data)
    rows = [topics.find(data, n) for n in order]
    if a.all:
        rows += [t for t in data["topics"] if t["n"] not in order]
    out(a, {"queue": order, "topics": [{k: v for k, v in t.items() if k != "raw"} for t in rows]},
        [topic_line(t) + ("  (stale)" if topics.stale(t) else "") for t in rows] or ["  the queue is empty: topics score …"])


@topic_cmd
def cmd_topics_take(a, topics, channels):
    data = topics.load(root(), a.channel)
    t, skipped = topics.take(data, a.film, a.allow_stale)
    for s in skipped:
        print(f"  skipped #{s['n']}: {s['reason']}")
    if not t:
        print("✗ no topic can be taken now", file=sys.stderr)
        return 1
    save_topics(topics, channels, a.channel, data)
    print(f"✓ topic #{t['n']} is in progress: {t['text']}")
    print(f"  make the film with: sh bin/studio channel attach <film> {a.channel} --new --topic {t['n']}")
    return 0


@topic_cmd
def cmd_topics_made(a, topics, channels):
    data = topics.load(root(), a.channel)
    topics.mark_made(data, a.n)
    save_topics(topics, channels, a.channel, data)
    print(f"✓ topic #{a.n} made")


@topic_cmd
def cmd_topics_type(a, topics, channels):
    data = topics.load(root(), a.channel)
    topics.set_type(data, a.n, a.type)
    save_topics(topics, channels, a.channel, data)
    print(f"✓ topic #{a.n}: {a.type}")


@topic_cmd
def cmd_topics_fit(a, topics, channels):
    data = topics.load(root(), a.channel)
    t = topics.set_fit(data, a.n, a.score, topics.made_items(root(), a.channel, data))
    save_topics(topics, channels, a.channel, data)
    print(topic_line(t))


@topic_cmd
def cmd_topics_refs(a, topics, channels):
    channels.load(root(), a.channel)
    ids = [r["id"] for r in topics.load_refs(root(), a.channel)]
    if a.add or a.remove:
        ids = [i for i in ids + (a.add or []) if i not in (a.remove or [])]
        topics.save_refs(root(), a.channel, ids)
    rows = topics.load_refs(root(), a.channel)
    print("\n".join(f"  {r['id']} (added {r['added']})" for r in rows) or "  no reference channels")


@topic_cmd
def cmd_topics_usage(a, topics, channels):
    u = usage_obj(topics)
    print(f"YouTube units used today: {u.today()} of {u.limit}")


@topic_cmd
def cmd_youtube_key(a, topics, channels):
    import getpass
    key = (getpass.getpass("YouTube Data API key (not shown): ") if sys.stdin.isatty() else sys.stdin.readline()).strip()
    if not key:
        raise topics.TopicError("no key given")
    f = topics.Fetcher.local(key, usage_obj(topics), topics.Cache(root() / ".studio" / "youtube-cache-check", hours=0))
    try:
        f.get("videos", {"part": "id", "id": "dQw4w9WgXcQ"})
    except topics.TopicError as e:
        raise topics.TopicError("the key does not work: " + topics.redact(str(e), key)) from None
    topics.save_key(key)
    print(f"✓ YouTube key saved (…{key[-4:]}) in {topics.KEY_FILE}")


# ---------- config ----------
def cmd_model(a) -> int:
    """specs/024: the studio's one Claude model; no value prints it."""
    from filmcheck import models
    if a.value is None:
        print(models.current())
        return 0
    try:
        models.set_model(a.value)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"model: {a.value}")
    return 0


def cmd_render_setting(a) -> int:
    editor.set_render_setting(a.value)
    print(f"✓ render: {a.value}" + (" (GPU when the machine can)" if a.value == "auto" else " (software only)"))
    return 0


# ---------- QC tiers (specs/020) ----------
QC_SUBS = ("voice", "plan", "shots", "except", "accept-style", "final")


def lib_dir() -> str:
    return os.environ.get("STUDIO_LIB") or str(HERE.parents[1] / "lib" / "lemo-opuscar")


def tier_lines(res: dict, name: str) -> list:
    from filmcheck import rhythm
    lines = [f"  ! {s}" for s in res.get("skipped") or []]
    for i in res["issues"]:
        mark = "·" if i.get("excepted") else ("!" if i["severity"] == "warn" else "✗")
        lines.append(f"  {mark} {rhythm.line(i)}")
    return lines


def cmd_qc_plan(a) -> int:
    from filmcheck import plancheck
    d = film_dir(a.film)
    try:
        r = plancheck.run(d, lib_dir())
    except plancheck.PlanError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    blk = [i for i in r["issues"] if i["severity"] == "block" and not i.get("excepted")]
    m = r["measures"]
    lines = tier_lines(r, d.name)
    summary = f"{m['shots']} shots" + (f" · silence {m['silence_ratio']:.0%}" if "silence_ratio" in m else "") \
        + f" · {r['seconds']:.1f} s"
    lines.append(f"{'✓' if r['pass'] else '✗'} plan: " + ("all rules pass" if r["pass"] else f"{len(blk)} problem(s)")
                 + f" · {summary}")
    out(a, r, lines)
    return 0 if r["pass"] else 1


def cmd_qc_shots(a) -> int:
    from filmcheck import shotcheck
    d = film_dir(a.film)
    if a.only:                                     # specs/026: frames of a few shots, no tier result
        try:
            files = shotcheck.preview(d, lib_dir(), [x for x in a.only.split(",") if x])
        except shotcheck.ShotError as e:
            print(f"✗ {e}", file=sys.stderr)
            return 2
        out(a, {"files": files}, [f"✓ {f}" for f in files] + ["  (no tier result: run qc shots on the whole film before the review)"])
        return 0
    try:
        r = shotcheck.run(d, lib_dir(), say=(lambda x: None) if a.json else print)
    except shotcheck.ShotError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    blk = [i for i in r["issues"] if i["severity"] == "block" and not i.get("excepted")]
    wrn = [i for i in r["issues"] if i["severity"] == "warn"]
    m = r["measures"]
    lines = tier_lines(r, d.name)
    lines.append(f"  luma {m['luma_p50']:.2f} · saturation {m['saturation_p50']:.2f} · {m['cuts_per_min']} cuts/min"
                 + (f" · style from {m['style_source']}" if m.get("style_source") else ""))
    g = m.get("shot_grammar")                                  # specs/021
    if g:
        pct = lambda d: " ".join(f"{k} {v:.0%}" for k, v in d.items() if v)  # noqa: E731
        lines.append(f"  scale: {pct(g['scale_share'])} · angle: {pct(g['angle_share'])} · longest same-scale run "
                     f"{g['longest_same_scale']} · focus p50 {g['focused_share_p50']}")
    acc = (r.get("style_accept") or {}).get("reason")
    lines.append(f"{'✓' if r['pass'] else '✗'} shots: {len(blk)} frame problem(s) · {len(wrn)} style warning(s)"
                 + (f" (accepted: {acc})" if acc and wrn else "")
                 + (f" · sheet {m['sheets'][0]}" if m.get("sheets") else "") + f" · {r['seconds']:.0f} s")
    out(a, r, lines)
    return 0 if r["pass"] else 1


def cmd_qc_accept_style(a) -> int:
    from filmcheck import shotcheck, tiers
    d = film_dir(a.film)
    try:
        r = shotcheck.accept_style(d, a.reason)
    except tiers.TierError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    out(a, r, [f"✓ style warnings accepted: {a.reason.strip()}"])
    return 0


def cmd_qc_except(a) -> int:
    from filmcheck import tiers
    d = film_dir(a.film)
    if a.list or not a.shot:
        exc = tiers.load_exceptions(d)
        out(a, {"exceptions": exc}, [f"  {e['shot']} {e['rule']} — {e['reason']} ({e.get('at', '')})" for e in exc])
        return 0
    if not a.rule:
        print("✗ usage: qc except <film> <shot> <rule> --reason \"…\" | --remove", file=sys.stderr)
        return 2
    try:
        if a.remove:
            if not tiers.remove_exception(d, a.shot, a.rule):
                print(f"✗ no exception for {a.shot} {a.rule}", file=sys.stderr)
                return 2
            lines = [f"✓ removed: {a.shot} {a.rule}"]
        else:
            tiers.add_exception(d, a.shot, a.rule, a.reason)
            lines = [f"✓ exception: {a.shot} {a.rule} — {a.reason.strip()}"]
    except tiers.TierError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    t = tiers.recompute(d).get("tiers") or {}
    lines += [f"  {k}: {'pass' if t[k]['pass'] else 'fail'}" for k in ("plan", "shots") if t.get(k)]
    out(a, {"exceptions": tiers.load_exceptions(d), "tiers": {k: t[k] for k in ("plan", "shots") if t.get(k)}}, lines)
    return 0


def film_lang(d: Path, given=None) -> str:
    if given:
        return given
    try:
        lang = json.loads((d / "channel.json").read_text(encoding="utf-8")).get("rules", {}).get("language")
        if lang:
            return lang
    except (OSError, ValueError, AttributeError):
        pass
    import re
    for f in ("CHANNEL_BRIEF.md", "SCRIPT.md"):
        try:
            m = re.search(r"^\W*Language\W*:?\s*([a-z]{2})\b", (d / f).read_text(encoding="utf-8"), re.M | re.I)
            if m:
                return m.group(1).lower()
        except OSError:
            continue
    return "en"


def asr_model(lang: str) -> str:
    """The studio's one recogniser model for a language (tools/asr.json, specs/020 FR-002)."""
    cfg = json.loads((HERE.parent / "asr.json").read_text(encoding="utf-8"))
    return cfg.get(lang) or cfg["*"]


def say_file(d: Path) -> Path:
    """voices/.say.json: lines.json with "text" replaced by "say" where a line has one (specs/023 FR-017, research R7).
    The library's tts.py reads only "text"; the script's text in lines.json stays as approved (qc checks it)."""
    rows = json.loads((d / "lines.json").read_text(encoding="utf-8"))
    out = [dict(r, text=r["say"]) if isinstance(r, dict) and r.get("say") else r for r in rows]
    for r in out:
        if isinstance(r, dict):
            r.pop("say", None)
    f = d / "voices" / ".say.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return f


def made_key(r: dict) -> dict:
    """What a voice file was made from (specs/026 R7, specs/036 data-model): the spoken text, voice and speed, plus
    pitch, formant, emotion, fx and the ElevenLabs model when they are not the default (old .made.json still match)."""
    k = {"text": r.get("say") or r.get("text", ""), "voice": r.get("voice"), "speed": r.get("speed")}
    for f, default in (("pitch", 0), ("formant", None), ("emotion", "neutral"), ("fx", "none")):
        if r.get(f) not in (None, default):
            k[f] = r[f]
    if voicecat.parse(r.get("voice") or "")[0] == "elevenlabs":
        k["model"] = r.get("model") or eleven.model()
    return k


def raw_key(k: dict) -> dict:
    """The part of a made key that needs the provider again; the rest (pitch, formant, fx) is redone from voices/.raw/."""
    return {f: v for f, v in k.items() if f not in ("pitch", "formant", "fx")}


def lines_to_make(d: Path, rows: list, only=None, changed=False) -> list:
    """The line ids to make: --only ids, --changed (spoken text, voice or speed differ from voices/.made.json, or no
    file yet), else all."""
    ids = [r["id"] for r in rows if isinstance(r, dict) and r.get("id")]
    if only:
        want = [x for x in only.split(",") if x]
        bad = [x for x in want if x not in ids]
        if bad:
            raise ValueError(f"lines.json has no line {', '.join(bad)}")
        return want
    if changed:
        try:
            made = json.loads((d / "voices" / ".made.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            made = {}
        return [r["id"] for r in rows if isinstance(r, dict) and r.get("id") and
                (made.get(r["id"]) != made_key(r) or not (d / "voices" / f"{r['id']}.wav").is_file())]
    return ids


def fake_tts(lines_file: Path, out: Path) -> int:
    """Tests (STUDIO_TTS_FAKE): one second of silence per line, as tts.py lays its files out."""
    import wave
    out.mkdir(parents=True, exist_ok=True)
    dur = {}
    for r in json.loads(lines_file.read_text(encoding="utf-8")):
        with wave.open(str(out / f"{r['id']}.wav"), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(b"\0\0" * 24000)
        dur[r["id"]] = 1.0
    (out / "dur.json").write_text(json.dumps(dur), encoding="utf-8")
    return 0


KOKORO_FALLBACK = {"female": "af_heart", "male": "am_michael", None: "am_michael"}


def kokoro_for(voice: str, el_rows: list) -> str:
    """The Kokoro voice that stands in for an ElevenLabs voice (same gender) when the film is read with Kokoro."""
    row = next((v for v in el_rows if v["id"] == voice), {})
    return KOKORO_FALLBACK.get(row.get("gender"), "am_michael")


def emotion_acted(provider: str, model: str) -> bool:
    """Only ElevenLabs v3 acts an emotion (research R2); elsewhere a small gain stands in for whisper and shout."""
    return provider == "elevenlabs" and model.startswith("eleven_v3")


EMOTION_TAG = {"whisper": "[whispers]", "shout": "[shouts]", "laugh": "[laughs]", "cry": "[crying]",
               "sarcastic": "[sarcastic]"}


def spoken(r: dict, model: str = "") -> str:
    """The text sent to the provider: "say" or "text", with the emotion tag in front for ElevenLabs v3."""
    t = r.get("say") or r.get("text", "")
    tag = EMOTION_TAG.get(r.get("emotion") or "")
    return f"{tag} {t}" if tag and emotion_acted("elevenlabs", model) else t


def _load(f: Path, default):
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def cmd_voice_make(a) -> int:
    d = film_dir(a.film)
    from filmcheck import points                   # specs/026: the voice is made from an approved script
    if a.skip_review is not None:
        try:
            points.skip(d, "script", a.skip_review)
        except points.PointError as e:
            print(f"✗ voice make: --skip-review {e}", file=sys.stderr)
            return 2
        print(f"! voice make: script review skipped — {a.skip_review.strip()}")
    why = points.gate(d, "script")
    why = why or points.gate(d, "cast")             # specs/034: an AE film's characters are approved first
    for w in why:
        print(f"✗ voice make: {w}", file=sys.stderr)
    if why:
        return 1
    try:
        rows = json.loads((d / "lines.json").read_text(encoding="utf-8"))
        rows = [r for r in rows if isinstance(r, dict) and r.get("id")]
    except (OSError, ValueError) as e:
        print(f"✗ lines.json cannot be read: {e}", file=sys.stderr)
        return 2
    try:                                            # specs/036 US2: each line's voice comes from its speaker
        rows = speakers.apply(d, rows, root=root(), write=not os.environ.get("STUDIO_TTS_DRY"))
    except speakers.SpeakerError as e:
        for w in str(e).splitlines():
            print(f"✗ voice make: {w}", file=sys.stderr)
        return 1
    vdir = d / "voices"
    fallback = {}
    if getattr(a, "provider", None) == "kokoro":    # the whole film with Kokoro (FR-006), never a part of it
        el_rows = []
        if any(voicecat.parse(r.get("voice") or "")[0] == "elevenlabs" for r in rows):
            try:
                el_rows = eleven.voices()
            except eleven.ElevenError:
                pass
        for r in rows:
            if voicecat.parse(r.get("voice") or "")[0] == "elevenlabs":
                fallback[r["voice"]] = r["voice"] = kokoro_for(r["voice"], el_rows)
    try:
        ids = lines_to_make(d, rows, a.only, a.changed)
    except ValueError as e:
        print(f"✗ lines.json: {e}", file=sys.stderr)
        return 2
    if not ids:
        print("voice: every line is up to date")
        return 0
    by_id = {r["id"]: r for r in rows}
    made = _load(vdir / ".made.json", {})
    keys = {i: made_key(by_id[i]) for i in ids}
    fx_only = [i for i in ids if isinstance(made.get(i), dict) and raw_key(made[i]) == raw_key(keys[i])
               and (vdir / ".raw" / f"{i}.wav").is_file()]
    read = [i for i in ids if i not in fx_only]
    k_ids = [i for i in read if voicecat.parse(by_id[i].get("voice") or "")[0] == "kokoro"]
    e_ids = [i for i in read if i not in k_ids]
    model = eleven.model()
    said = [i for i in read if by_id[i].get("say")]
    print(f"voice: {len(ids)} line(s)" + (f" ({', '.join(ids[:12])}{' …' if len(ids) > 12 else ''})" if len(ids) < len(rows) else "")
          + (f"; Kokoro {len(k_ids)}, ElevenLabs {len(e_ids)}" if e_ids else "")
          + (f"; effects only {len(fx_only)}" if fx_only else "")
          + (f"; spoken as written in \"say\": {', '.join(said)}" if said else ""))
    if fallback:
        print("voice: read with Kokoro: " + ", ".join(f"{k} → {v}" for k, v in sorted(set(fallback.items()))))

    chars = sum(len(spoken(by_id[i], model)) for i in e_ids)
    if e_ids and not os.environ.get("STUDIO_TTS_DRY"):
        try:
            left = eleven.subscription()["left"]
        except eleven.ElevenError as e:
            print(f"✗ voice make: {e.message}", file=sys.stderr)
            return 3
        print(f"elevenlabs: {chars} characters for {len(e_ids)} line(s); {left} left")
        if chars > left:
            print(f"✗ not enough characters: need {chars}, have {left} — use --provider kokoro for this film",
                  file=sys.stderr)
            return 3
        if len(e_ids) > 1 and not getattr(a, "yes", False):
            print("✗ voice make: add --yes to spend these characters", file=sys.stderr)
            return 1

    lib = Path(lib_dir())
    py = lib / ".venv" / "bin" / "python"
    import subprocess
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / ".raw").mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="voice.", dir=vdir))
    rc, k_ok, e_ok = 0, [], []
    try:
        if k_ids:                                  # Kokoro through the library's tts.py, as before (FR-007)
            f = say_file(d)
            raw = [r for r in json.loads(f.read_text(encoding="utf-8")) if isinstance(r, dict) and r.get("id") in k_ids]
            sub = []
            for r in raw:                          # the resolved voice and speed (speaker, fallback), without prefix
                eff = by_id[r["id"]]
                r2 = dict(r)
                if eff.get("voice"):
                    r2["voice"] = voicecat.parse(eff["voice"])[1]
                if eff.get("speed") is not None:
                    r2["speed"] = eff["speed"]
                sub.append(r2)
            if len(k_ids) < len(rows) or sub != raw:
                f = tmp / ".say.json"
                f.write_text(json.dumps(sub, ensure_ascii=False, indent=1), encoding="utf-8")
            cmd = [str(py if py.is_file() else "python3"), str(lib / "core" / "tts" / "tts.py"), str(f), str(tmp)]
            if os.environ.get("STUDIO_TTS_DRY"):
                print(" ".join(cmd))
            else:
                rc = fake_tts(f, tmp) if os.environ.get("STUDIO_TTS_FAKE") else subprocess.run(cmd, cwd=str(lib)).returncode
                if rc == 0:
                    for i in k_ids:
                        os.replace(tmp / f"{i}.wav", vdir / ".raw" / f"{i}.wav")
                    k_ok = k_ids
        if e_ids and os.environ.get("STUDIO_TTS_DRY"):
            print(f"elevenlabs {model}: {', '.join(e_ids)} ({chars} characters)")
        elif e_ids and rc == 0:
            rc, e_ok = read_eleven(d, [by_id[i] for i in e_ids], model, chars)
        if os.environ.get("STUDIO_TTS_DRY"):
            return 0
        done = []
        for i in [i for i in ids if i in fx_only or i in k_ok or i in e_ok]:   # the lines read keep their files
            r = by_id[i]
            prov = voicecat.parse(r.get("voice") or "")[0]
            emo = r.get("emotion") if r.get("emotion") in ("whisper", "shout") and not emotion_acted(prov, model) else None
            voicefx.apply(vdir / ".raw" / f"{i}.wav", vdir / f"{i}.wav", r.get("pitch") or 0, r.get("formant"),
                          r.get("fx") or "none", emo)
            done.append(i)
        if done:
            dur = _load(vdir / "dur.json", {})
            dur.update({i: round(voicefx.duration(vdir / f"{i}.wav"), 3) for i in done})
            (vdir / "dur.json").write_text(json.dumps(dur, indent=1), encoding="utf-8")
            made.update({i: keys[i] for i in done})
            (vdir / ".made.json").write_text(json.dumps(made, ensure_ascii=False, indent=1), encoding="utf-8")
        emos = {r["id"]: {"emotion": r["emotion"], "emotion_applied": emotion_acted(
                    voicecat.parse(r.get("voice") or "")[0], model)}
                for r in rows if r.get("emotion") not in (None, "", "neutral")}
        if fallback or emos or (vdir / "speakers.json").is_file():
            sp = _load(vdir / "speakers.json", {})
            if fallback:
                sp["fallback"] = {"provider": "kokoro", "voices": fallback}
            if emos:                               # FR-031: the Voice page says which emotions were not acted
                sp["emotions"] = emos
            else:
                sp.pop("emotions", None)
            (vdir / "speakers.json").write_text(json.dumps(sp, ensure_ascii=False, indent=1), encoding="utf-8")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return rc


def read_eleven(d: Path, rows: list, model: str, estimated: int):
    """Read lines with ElevenLabs (at most 3 at once: the Starter plan's limit; a 429 is tried again) into voices/.raw/;
    align.json and usage.json.
    (0 or 3 on a provider error, the ids read: those stay)."""
    from concurrent.futures import ThreadPoolExecutor
    vdir = d / "voices"
    align = _load(vdir / "align.json", {})
    charged, ok, errors = 0, [], []

    def one(r):
        vs = dict(r.get("el") or {})
        if r.get("speed") is not None:
            vs["speed"] = r["speed"]
        for wait in (1, 2, 4, 8, 0):
            try:
                pcm, al, n = eleven.speak(r["voice"], spoken(r, model), model, vs)
                break
            except eleven.ElevenError as e:
                if e.code != "busy" or not wait:
                    raise
                time.sleep(wait * float(os.environ.get("STUDIO_ELEVEN_BACKOFF", "1")))
        eleven.write_wav(vdir / ".raw" / f"{r['id']}.wav", pcm)
        return r["id"], al, n
    with ThreadPoolExecutor(max_workers=int(os.environ.get("STUDIO_ELEVEN_PARALLEL", "3"))) as ex:
        futs = [ex.submit(one, r) for r in rows]
        for r, fu in zip(rows, futs):
            try:
                i, al, n = fu.result()
            except eleven.ElevenError as e:
                errors.append((r["id"], e))
                continue
            charged += n
            ok.append(i)
            if al:
                align[i] = {"chars": al.get("characters") or [], "start": al.get("character_start_times_seconds") or [],
                            "end": al.get("character_end_times_seconds") or [], "source": "el"}
            else:                                  # research R2: v3 may send no alignment; the recogniser's stamps
                align[i] = {"source": "asr"}       # (voice asr) time this line
    if ok:
        (vdir / "align.json").write_text(json.dumps(align, ensure_ascii=False), encoding="utf-8")
        u = _load(vdir / "usage.json", {"provider": "elevenlabs", "total": 0, "runs": []})
        u["total"] = int(u.get("total") or 0) + charged
        u.setdefault("runs", []).append({"at": now(), "chars_estimated": estimated, "chars": charged, "lines": ok,
                                         **({"job": os.environ["STUDIO_JOB"]} if os.environ.get("STUDIO_JOB") else {})})
        (vdir / "usage.json").write_text(json.dumps(u, ensure_ascii=False, indent=1), encoding="utf-8")
    for i, e in errors:
        print(f"✗ elevenlabs {i}: {e.message}", file=sys.stderr)
    return (3 if errors else 0), ok


def cmd_voice_usage(a) -> int:
    d = film_dir(a.film)
    u = _load(d / "voices" / "usage.json", None)
    if a.json:
        print(json.dumps(u or {"provider": "elevenlabs", "total": 0, "runs": []}, indent=1))
        return 0
    if not u:
        print("elevenlabs: no characters used by this film")
        return 0
    print(f"elevenlabs: {u.get('total', 0)} characters in {len(u.get('runs') or [])} run(s)")
    for r in u.get("runs") or []:
        print(f"  {r.get('at')}  {r.get('chars')} (estimated {r.get('chars_estimated')})  {len(r.get('lines') or [])} line(s)")
    return 0


def _setting_text(s: dict) -> str:
    if not s:
        return "—"
    parts = [s.get("voice") or ("narrator plays it" if s.get("mode") == "narrator" else "?")]
    if s.get("pitch"):
        parts.append(f"pitch {s['pitch']:+g}")
    if s.get("speed") not in (None, 1, 1.0):
        parts.append(f"speed {s['speed']:g}")
    if s.get("emotion") not in (None, "neutral"):
        parts.append(s["emotion"])
    return ", ".join(parts)


def cmd_voice_check(a) -> int:
    """specs/036 contracts/cli.md: the speaker ↔ voice table and its problems; exit 1 when there is one."""
    d = film_dir(a.film)
    try:
        rows = [r for r in json.loads((d / "lines.json").read_text(encoding="utf-8")) if isinstance(r, dict) and r.get("id")]
    except (OSError, ValueError) as e:
        print(f"✗ lines.json cannot be read: {e}", file=sys.stderr)
        return 2
    res = speakers.resolve(d, rows, root())
    errs = list(res["errors"]) + [f"line {r['id']}: {e}" for r in rows for e in speakers.line_errors(r)]
    if a.json:
        print(json.dumps({"speakers": res["speakers"], "errors": errs}, ensure_ascii=False, indent=1))
    else:
        for sp, e in res["speakers"].items():
            print(f"{sp:<14} {e['source']:<9} {_setting_text(e['setting']):<40} {len(e['lines'])} line(s)"
                  + (f"  [{e['role']}]" if e.get("role") else ""))
        for w in errs:
            print(f"✗ {w}", file=sys.stderr)
        if not errs:
            print("voice check: ok")
    return 1 if errs else 0


def cmd_voice_channel(a) -> int:
    from filmcheck import channels
    r = root()
    try:
        if a.what == "narrator":
            if not a.voice:
                print("✗ voice channel: --voice is needed", file=sys.stderr)
                return 2
            st = {"voice": a.voice, "speed": a.speed if a.speed is not None else 1.0}
            if a.pitch:
                st["pitch"] = a.pitch
            speakers.save_channel_voice(r, a.slug, narrator=st)
        elif a.what == "role":
            if not a.role:
                print(f"✗ voice channel: give a role ({', '.join(speakers.ROLES)})", file=sys.stderr)
                return 2
            st = {"mode": a.mode or ("own" if a.voice else "narrator")}
            for k in ("voice", "pitch", "speed"):
                if getattr(a, k) is not None:
                    st[k] = getattr(a, k)
            cur = speakers.channel_voice(r, a.slug)["roles"].get(a.role, []) if a.add else []
            speakers.save_channel_voice(r, a.slug, role=a.role, settings=cur + [st])
        doc = speakers.channel_voice(r, a.slug)
    except (speakers.SpeakerError, channels.ChannelError) as e:
        print(f"✗ voice channel: {e}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(doc, ensure_ascii=False, indent=1))
        return 0
    print(f"narrator   {_setting_text(doc['narrator']) if doc['narrator'] else 'not chosen yet'}")
    for k, v in doc["roles"].items():
        print(f"{k:<10} " + " | ".join(_setting_text(x) for x in v))
    return 0


def sample_line(d: Path, cid: str) -> str:
    """The test sentence of a character: its longest line of at most 120 characters (specs/036 contracts/cli.md)."""
    try:
        rows = json.loads((d / "lines.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rows = []
    said = [(r.get("say") or r.get("text") or "").strip() for r in rows if isinstance(r, dict) and r.get("speaker") == cid]
    said = [t for t in said if t]
    if not said:
        return ""
    fit = [t for t in said if len(t) <= 120]
    if fit:
        return max(fit, key=len)
    t = said[0][:120]
    return t.rsplit(" ", 1)[0] if " " in t else t


def cmd_voice_cast(a) -> int:
    """voice cast <film> sample <character> [--option n] | set <character> --option n | --voice … (specs/036 US2)."""
    from filmcheck import cast
    d = film_dir(a.film)
    try:
        doc = cast.load(d)
        c = cast.find(doc, a.character)
    except cast.CastError as e:
        print(f"✗ voice cast: {e}", file=sys.stderr)
        return 2
    opts = c.get("voice_options") or []
    if a.option is not None and not 1 <= a.option <= len(opts):
        print(f"✗ voice cast: {a.character} has {len(opts)} voice choice(s)", file=sys.stderr)
        return 2
    if a.action == "set":
        if a.option is not None:
            st = dict(opts[a.option - 1]["setting"])
        elif a.voice or a.mode == "narrator":
            st = {"mode": a.mode or "own", **({"voice": a.voice} if a.voice else {})}
        else:
            print("✗ voice cast set: give --option n or --voice <id> (or --mode narrator)", file=sys.stderr)
            return 2
        for k in ("pitch", "speed"):
            if getattr(a, k) is not None:
                st[k] = getattr(a, k)
        errs = speakers.check_setting(st, "voice")
        if errs:
            print("✗ voice cast: " + "; ".join(errs), file=sys.stderr)
            return 2
        was = cast.state(d, c)
        c["voice"] = st
        cast.save(d, doc)
        now_st = cast.state(d, cast.find(cast.load(d), a.character))
        print(f"✓ {a.character}: {_setting_text(st)}" + (" (approved before: now changed, approve again)"
                                                         if was == "approved" and now_st != "approved" else ""))
        return 0
    # sample: read the test sentence with each choice (or one) into cast/voices/<id>/<n>.wav
    line = sample_line(d, a.character)
    if not line:
        print(f"✗ voice cast: {a.character} has no line in lines.json", file=sys.stderr)
        return 2
    picks = [a.option] if a.option is not None else list(range(1, len(opts) + 1))
    if not picks:
        print(f"✗ voice cast: {a.character} has no voice_options; write them in cast/cast.json", file=sys.stderr)
        return 2
    narr = speakers.resolve(d, [{"id": "_", "text": "x"}], root())["speakers"].get("narrator", {}).get("setting")
    rows = []
    for n in picks:
        s = speakers._real(opts[n - 1]["setting"], narr)
        if not s.get("voice"):
            print(f"✗ voice cast: choice {n} is played by the narrator, and the channel has no narrator voice yet", file=sys.stderr)
            return 2
        rows.append({"id": f"{a.character}-{n}", "n": n, "text": line, **s})
    chars = speakers.estimate_chars(rows)
    print(f"sample: \"{line}\" × {len(rows)}" + (f" · ElevenLabs {chars} characters" if chars else " · Kokoro, free"))
    if chars and not a.yes:
        print("✗ voice cast: add --yes to spend these characters", file=sys.stderr)
        return 1
    out = cast.path(d).parent / "voices" / a.character
    out.mkdir(parents=True, exist_ok=True)
    raw = Path(tempfile.mkdtemp(prefix="sample.", dir=out))
    try:
        k_rows = [r for r in rows if voicecat.parse(r["voice"])[0] == "kokoro"]
        if k_rows:
            f = raw / ".say.json"
            f.write_text(json.dumps([{"id": r["id"], "text": r["text"], "voice": voicecat.parse(r["voice"])[1],
                                      "speed": r.get("speed") or 1.0} for r in k_rows], ensure_ascii=False), encoding="utf-8")
            if os.environ.get("STUDIO_TTS_FAKE"):
                rc = fake_tts(f, raw)
            else:
                import subprocess
                lib = Path(lib_dir())
                py = lib / ".venv" / "bin" / "python"
                rc = subprocess.run([str(py if py.is_file() else "python3"), str(lib / "core" / "tts" / "tts.py"), str(f), str(raw)],
                                    cwd=str(lib)).returncode
            if rc:
                print("✗ voice cast: Kokoro could not read the sample", file=sys.stderr)
                return 1
        spent = 0
        for r in rows:
            if voicecat.parse(r["voice"])[0] == "elevenlabs":
                vs = dict(r.get("el") or {})
                if r.get("speed") is not None:
                    vs["speed"] = r["speed"]
                try:
                    pcm, _, n = eleven.speak(r["voice"], r["text"], eleven.model(), vs)
                except eleven.ElevenError as e:
                    print(f"✗ elevenlabs {r['id']}: {e.message}", file=sys.stderr)
                    return 3
                spent += n
                eleven.write_wav(raw / f"{r['id']}.wav", pcm)
            voicefx.apply(raw / f"{r['id']}.wav", out / f"{r['n']}.wav", r.get("pitch") or 0, r.get("formant"), "none", None)
            opts[r["n"] - 1]["sample_line"], opts[r["n"] - 1]["sample"] = line, f"voices/{a.character}/{r['n']}.wav"
            print(f"✓ choice {r['n']}: {_setting_text(r)} → cast/voices/{a.character}/{r['n']}.wav")
        if spent:
            u = _load(d / "voices" / "usage.json", {"provider": "elevenlabs", "total": 0, "runs": []})
            u["total"] = int(u.get("total") or 0) + spent
            u.setdefault("runs", []).append({"at": now(), "chars_estimated": chars, "chars": spent, "sample": a.character})
            (d / "voices").mkdir(exist_ok=True)
            (d / "voices" / "usage.json").write_text(json.dumps(u, ensure_ascii=False, indent=1), encoding="utf-8")
        cast.save(d, doc)
    finally:
        shutil.rmtree(raw, ignore_errors=True)
    return 0


def cmd_eleven(a) -> int:
    """eleven test | eleven voices (contracts/cli.md). Never prints the key."""
    try:
        if a.cmd == "test":
            s = eleven.subscription()
            reset = datetime.fromtimestamp(s["reset_at"], timezone.utc).strftime("%Y-%m-%d") if s.get("reset_at") else "?"
            print(f"ok · tier {s.get('tier')} · {s['left']}/{s['limit']} characters left · resets {reset}"
                  f" · model {eleven.model()}")
            return 0
        rows = eleven.voices(refresh=a.refresh)
    except eleven.ElevenError as e:
        print(f"✗ {e.message}", file=sys.stderr)
        return 3
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0
    for v in rows:
        print(f"{v['id']:<26} {v['name'][:28]:<28} {v.get('gender') or '-'}/{v.get('age') or '-':<12} "
              f"{(v.get('accent') or '')[:14]:<14}{' [cloned]' if v.get('cloned') else ''}")
    return 0


def cmd_voice_asr(a) -> int:
    d = film_dir(a.film)
    lang = film_lang(d, a.lang)
    model = asr_model(lang)
    lib = Path(lib_dir())
    py = lib / ".venv" / "bin" / "python"
    lines_f, vdir, tmp = d / "lines.json", d / "voices", None
    if a.only:                                     # specs/026: stamps of a few lines, merged into words.json
        import shutil
        want = [x for x in a.only.split(",") if x]
        rows = [r for r in json.loads(lines_f.read_text(encoding="utf-8")) if isinstance(r, dict) and r.get("id") in want]
        tmp = Path(tempfile.mkdtemp(prefix="asr.", dir=d / "voices"))
        lines_f, vdir = tmp / "lines.json", tmp
        lines_f.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        for r in rows:
            shutil.copy2(d / "voices" / f"{r['id']}.wav", tmp / f"{r['id']}.wav")
    cmd = [str(py if py.is_file() else "python3"), str(lib / "core" / "tts" / "asr_check.py"), str(lines_f),
           str(vdir), "--lang", lang, "--model", model]
    print(f"model: {model} ({lang})")
    if os.environ.get("STUDIO_ASR_DRY"):
        print(" ".join(cmd))
        if tmp:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
        return 0
    import subprocess
    try:
        rc = subprocess.run(cmd).returncode
        if tmp and (tmp / "words.json").is_file():
            wf = d / "voices" / "words.json"
            try:
                words = json.loads(wf.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                words = {}
            words.update(json.loads((tmp / "words.json").read_text(encoding="utf-8")))
            wf.write_text(json.dumps(words, indent=0, ensure_ascii=False), encoding="utf-8")
    finally:
        if tmp:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
    return rc


def cmd_qc_voice(a) -> int:
    from filmcheck import voicecheck
    d = film_dir(a.film)
    try:
        r = voicecheck.run(d, lib_dir(), film_lang(d))
    except voicecheck.VoiceError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    lines = tier_lines(r, d.name)
    n = len(r["issues"])
    lines.append(f"{'✓' if r['pass'] else '✗'} voice: {r['measures']['lines']} lines · "
                 + ("all pass" if r["pass"] else f"{n} problem(s)") + f" · {r['seconds']:.1f} s")
    out(a, r, lines)
    return 0 if r["pass"] else 1


def cmd_qc_limits(a) -> int:
    """JSON for tools/render/record.mjs (tier 3): the style's still limit and the film's exceptions."""
    from filmcheck import qc, tiers
    d = film_dir(a.film)
    print(json.dumps({"still_max": qc.still_limit(d),
                      "exceptions": [{"shot": e["shot"], "rule": e["rule"]} for e in tiers.load_exceptions(d)]}))
    return 0


def cmd_render_done(a) -> int:
    """Save tiers.render from out/render-qc.json written by record.mjs (specs/020 FR-021)."""
    from filmcheck import tiers
    d = film_dir(a.film)
    try:
        q = json.loads((d / "out" / "render-qc.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    issues = [{"tier": "render", "ref": f.get("shot") or f"chunk {f.get('chunk')}", "at": f.get("at"), "rule": f["rule"],
               "severity": "block", "measure": f.get("measure"), "limit": f.get("limit"), "text": f"chunk {f.get('chunk')}",
               "fix": "fix the shot and render again (earlier chunks are kept)", "excepted": None} for f in q.get("faults") or []]
    old = tiers.load_tier(d, "render") or {}
    skipped = old.get("skipped_checks") if q.get("skipped_checks") else None
    res = tiers.result("render", issues, {"no_stop": q.get("no_stop")}, [], 0.0, tiers.fingerprint(d),
                       stopped=q.get("stopped") and {k: q["stopped"].get(k) for k in ("first_bad", "shot", "rule", "at")},
                       reused_chunks=q.get("reused", 0), skipped_checks=skipped)
    tiers.save_tier(d, "render", res)
    return 0


def cmd_render_gate(a) -> int:
    from filmcheck import tiers
    d = film_dir(a.film)
    if a.skip_checks is not None:
        if not a.skip_checks.strip():
            print("✗ render: --skip-checks needs a reason", file=sys.stderr)
            return 2
        tiers.record_skip(d, a.skip_checks.strip())
        print(f"! render: checks skipped — {a.skip_checks.strip()}")
        return 0
    why = tiers.gate(d)
    from filmcheck import points                   # specs/026: the shots review point, after the tier checks
    why += points.gate(d, "shots") if not why else []
    for w in why:
        print(f"✗ render: {w}", file=sys.stderr)
    return 1 if why else 0


# ---------- review points and edits (specs/026) ----------
def cmd_point_status(a) -> int:
    from filmcheck import points, steps
    d = film_dir(a.film)
    st, rail = points.status(d), steps.status(d)
    data = {"film": d.name, "points": st, "steps": rail, "impact": {p: steps.impact(p, d) for p in points.POINTS}}
    lines = [f"{p:8} {'on ' if v['on'] else 'off'} {v['state']}" + (f" · approved {v['approved_at']} ({v['source']})"
                                                                    if v["approved_at"] else "") for p, v in st.items()]
    lines += ["", "  ".join(f"{s['name']}: {s['state']}" for s in rail)]
    out(a, data, lines)
    return 0


def cmd_point_set(a) -> int:
    from filmcheck import points
    try:
        on = points.set_on(film_dir(a.film), a.points)
    except points.PointError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    print(f"✓ review points: {', '.join(on) or 'none'}")
    return 0


def cmd_point_approve(a) -> int:
    from filmcheck import points
    d = film_dir(a.film)
    if getattr(a, "anyway", False) and os.environ.get("STUDIO_JOB"):     # specs/035 FR-010: never Claude inside a job
        print(f"✗ {a.point}: only the owner can approve anyway, on the job page", file=sys.stderr)
        return 1
    try:
        code, why = points.approve(d, a.point, a.base, a.source, a.by, a.review, anyway=getattr(a, "anyway", False))
    except points.PointError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps({"code": code, "reasons": why, "fingerprint": points.fingerprint(d, a.point)}))
    elif code:
        for w in why:
            print(f"✗ {a.point}: {w}", file=sys.stderr)
    else:
        print(f"✓ {a.point} approved ({a.source})")
    return code


# ---------- the Animatic of an AE film (specs/035) ----------
def animatic_view(d: Path) -> dict:
    from filmcheck import animatic, rhythm, timing
    t = animatic.timeline(d)
    sil = animatic.silence(d)
    return {"film": d.name, **t, "silence": sil, "limit": rhythm.SILENCE_MAX, "gaps": animatic.longest_gaps(d) if sil > rhythm.SILENCE_MAX else [],
            "draft": {"current": animatic.draft_current(d), "info": animatic.draft_info(d)}, "fit": animatic.fit(d),
            "can_undo": animatic.can_undo(d), "notes_open": animatic.open_notes(d), "timing_base": timing.base(d)}


def _anim(a, fn) -> int:
    from filmcheck import animatic
    d = film_dir(a.film)
    try:
        return fn(d)
    except animatic.AnimaticError as e:
        print(f"✗ {e.message}", file=sys.stderr)
        return e.exit_code()


def _sil_line(d: Path) -> str:
    from filmcheck import animatic, rhythm, timing
    doc = timing.require(d)
    return (f"silence {round(animatic.silence(d) * 100)}% (limit {round(rhythm.SILENCE_MAX * 100)}%) · "
            f"{timing.duration(doc):.2f} s")


def cmd_animatic_status(a) -> int:
    def go(d):
        v = animatic_view(d)
        lines = [f"{s['id']:4} {s['t0']:6.2f}–{s['t1']:6.2f} s  {s['frames']:4} fr  " + " ".join(x["id"] for x in s["lines"])
                 for s in v["shots"]]
        lines += [f"silence {round(v['silence'] * 100)}% (limit {round(v['limit'] * 100)}%) · {v['duration']:.2f} s · draft "
                  + ("current" if v["draft"]["current"] else ("old" if v["draft"]["info"] else "none"))]
        lines += [f"fit {x['shot']}: {x['delta_s']:+.2f} s" + (f" (head {x['head']:.2f} s)" if x["head"] else "") for x in v["fit"]]
        out(a, v, lines)
        return 0
    return _anim(a, go)


def cmd_animatic_start(a) -> int:
    from filmcheck import timing

    def go(d):
        try:
            doc = timing.start(d)
        except timing.TimingError as e:
            print(f"✗ {e.message}", file=sys.stderr)
            return e.exit_code()
        print(f"✓ animatic started · origin {doc['origin']['at']} · {_sil_line(d)}")
        return 0
    return _anim(a, go)


def cmd_animatic_fit(a) -> int:
    from filmcheck import animatic

    def go(d):
        f = animatic.fit(d)
        out(a, {"fit": f}, [f"{x['shot']}: {x['delta_s']:+.2f} s → "
                            + (f"holds 2.5 s: the last words of {x['hold']}" if x.get("hold") else
                               f"ends {animatic.PAD} s after its last line")
                            + (f", lines start at the cut (−{x['head']:.2f} s)" if x["head"] else "")
                            + (" · very short shot" if x["very_short"] else "")
                            + "".join(f"\n    {m['name']}: {m['effect']}" + (f" ×{m['ratio']}" if m.get("ratio") else "")
                                      for m in x["motions"]) for x in f] or ["no suggestion"])
        return 0
    return _anim(a, go)


def cmd_animatic_accept(a) -> int:
    from filmcheck import animatic

    def go(d):
        shots = "all" if a.all else [x for x in (a.shots or "").split(",") if x]
        if not shots:
            print("✗ give the shots (S2,S6) or --all", file=sys.stderr)
            return 2
        r = animatic.accept(d, shots, by=os.environ.get("STUDIO_USER") or "claude", expect=a.base)
        print(f"✓ accepted {', '.join(r['accepted'])} · {_sil_line(d)}")
        return 0
    return _anim(a, go)


def cmd_animatic_skip(a) -> int:
    from filmcheck import animatic

    def go(d):
        animatic.skip(d, a.shot, expect=a.base)
        print(f"✓ {a.shot.upper()} stays as it is · {_sil_line(d)}")
        return 0
    return _anim(a, go)


def cmd_animatic_undo(a) -> int:
    from filmcheck import animatic

    def go(d):
        animatic.undo(d, expect=a.base)
        print(f"✓ undone · {_sil_line(d)}")
        return 0
    return _anim(a, go)


def cmd_animatic_notes(a) -> int:
    """animatic notes <film> add <S2> [--at 1.2 --x 40 --y 30] --text "…" · delete <S2> <note> · show [--all] ·
    reply <note> --text "…" [--done|--open]; every write takes --base (exit 4 when the notes changed)."""
    from filmcheck import animatic

    def go(d):
        if a.ncmd == "add":
            n = animatic.note_add(d, a.shot, a.text, a.at, a.x, a.y, by=os.environ.get("STUDIO_USER") or "claude", b=a.base)
            print(f"✓ {n['id']} on {a.shot.upper()}")
            return 0
        if a.ncmd == "delete":
            animatic.note_delete(d, a.shot, a.note_id, a.base)
            print(f"✓ {a.note_id} deleted")
            return 0
        if a.ncmd == "reply":
            done = True if a.done else False if a.open else None
            n = animatic.note_reply(d, a.note_id, a.text, done, a.base)
            print(f"✓ {n['id']}: replied" + (" · done" if n["done"] else ""))
            return 0
        doc, b = animatic.notes_load(d), animatic.notes_base(d)
        lot = set((doc.get("lot") or {}).get("notes") or []) if doc.get("lot") else None
        rows, waiting = [], 0
        for shot, n in animatic.NOTES.all_notes(doc):
            if n.get("done") and not a.all:
                continue
            if lot is not None and not a.all and n["id"] not in lot:      # FR-022: written during the round: next round
                waiting += 1
                continue
            clip = d / "animatic" / "clips" / f"{shot}.mp4"
            rows.append({"shot": shot, **n, "clip": str(clip) if clip.is_file() else None})
        lines = [f"{r['shot']} {r['id']}" + (f" at {r['at']:.2f} s ({r['x']}%, {r['y']}%)" if r.get("frame") else " (general)")
                 + f": {r['text']}" + (f"\n    ↳ {r['reply']}" if r.get("reply") else "") + (" ✓" if r.get("done") else "")
                 for r in rows] or ["no open notes"]
        if waiting:
            lines.append(f"{waiting} note(s) written during this round wait for the next one")
        lines.append(f"base {b}")
        out(a, {"base": b, "notes": rows, "waiting": waiting, "lot": doc.get("lot"), "failed_lot": doc.get("failed_lot")}, lines)
        return 0
    return _anim(a, go)


def cmd_point_gate(a) -> int:
    from filmcheck import points
    try:
        why = points.gate(film_dir(a.film), a.point)
    except points.PointError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    for w in why:
        print(w)
    return 1 if why else 0


# ---------- cast of an AE film (specs/034 contracts/cli.md) ----------
def _cast_film(a):
    from filmcheck import cast
    d = film_dir(a.film)
    if not cast.is_ae(d):
        print(f"✗ {d.name} is not an After Effects film: the cast review is for AE films (film.json engine \"ae\")",
              file=sys.stderr)
        return None
    return d


def cmd_cast_check(a) -> int:
    from filmcheck import cast
    d = _cast_film(a)
    if d is None:
        return 2
    try:
        doc = cast.load(d)
    except cast.CastError as e:
        print(f"✗ {e.code}: {e.message}", file=sys.stderr)
        return 2
    errs = cast.validate(doc)
    for cid, code, msg in errs:
        print(f"✗ {cid or '-'}: {code}: {msg}", file=sys.stderr)
    for cid, msg in cast.catalog_warnings(d, doc):
        print(f"! {cid}: {msg}")
    if errs:
        return 2
    print(f"✓ cast/cast.json: {len(doc['characters'])} character(s)")
    return 0


def cmd_cast_status(a) -> int:
    from filmcheck import cast, points
    d = _cast_film(a)
    if d is None:
        return 2
    try:
        doc = cast.load(d)
        st = cast.states(d, doc)
    except cast.CastError as e:
        print(f"✗ {e.code}: {e.message}", file=sys.stderr)
        return 2
    notes = cast.open_notes(d)
    pst = points.state(d, "cast")
    rows = [{"id": c["id"], "name": c.get("name"), "role": c.get("role"), "kind": c.get("kind", "one"),
             "state": st.get(c["id"]), "notes_open": notes.get(c["id"], 0), "source": cast.source(c), "rig": c.get("rig")}
            for c in doc["characters"] if isinstance(c, dict) and c.get("id")]
    if a.json:
        print(json.dumps({"characters": rows, "point": pst, "fingerprint": cast.fingerprint(d),
                          "save_to_library": doc.get("save_to_library", True)}, ensure_ascii=False))
        return 0
    for r in rows:
        print(f"{r['id']:<16} {r['state']:<9} notes {r['notes_open']:<3} {r['source']:<12} {r['rig']}")
    print(f"point cast: {pst}")
    return 0


def cmd_cast_approve(a) -> int:
    from filmcheck import cast, points
    d = _cast_film(a)
    if d is None:
        return 2
    if not a.all and not a.ids:
        print("✗ cast approve: name the characters, or --all", file=sys.stderr)
        return 2
    try:
        doc = cast.load(d)
        bad = cast.validate(doc)
        if bad:
            for cid, code, msg in bad:
                print(f"✗ {cid or '-'}: {code}: {msg}", file=sys.stderr)
            return 2
        if a.base and a.base != cast.fingerprint(d):
            print("✗ the cast changed since you looked (base is old): reload and approve again", file=sys.stderr)
            return 4
        if a.all:
            code, why = points.approve(d, "cast", source=a.source, by=os.environ.get("STUDIO_USER") or "local")
        else:
            why = cast.approve(d, a.ids, a.source, os.environ.get("STUDIO_USER") or "local")
            code = 1 if why else 0
    except cast.CastError as e:
        print(f"✗ {e.code}: {e.message}", file=sys.stderr)
        return 2
    except points.PointError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    for w in why:
        print(f"✗ cast approve: {w}", file=sys.stderr)
    if code:
        return code
    ids = [c["id"] for c in cast.load(d)["characters"]] if a.all else a.ids
    print(f"✓ approved: {', '.join(ids)} ({a.source})")
    save = doc.get("save_to_library", True) if a.save is None else a.save
    if save:
        try:
            from filmcheck import castlib
            for line in castlib.save_approved(d, ids):
                print(line)
        except ImportError:
            pass
        except Exception as e:                    # noqa: BLE001 — the approval stands; the library copy can be redone
            print(f"! not saved to the cast library: {e}", file=sys.stderr)
    return 0


def cmd_cast_use(a) -> int:
    """cast use <film> <channel>/<id>[@v]: a character of the channel's cast into this film (exit 3: no app / no character)."""
    from filmcheck import cast, castlib
    d = _cast_film(a)
    if d is None:
        return 2
    try:
        r = castlib.use(d, a.ref, os.environ.get("STUDIO_USER") or "local")
    except cast.CastError as e:
        print(f"✗ {e.code}: {e.message}", file=sys.stderr)
        return 3 if e.code in ("no_app", "no_character") else 2
    if r["approved"]:
        print(f"✓ {r['id']}: approved (library v{r['v']})")
    else:
        print(f"✓ {r['id']}: from library v{r['v']} · {len(r['lacking'])} picture(s) to draw: {', '.join(r['lacking'])}\n"
              f"  run: sh bin/studio ae sheet {d.name} --only {r['id']}, then review the cast")
    return 0


def cmd_cast_library(a) -> int:
    """cast library [<channel>] [--json]."""
    from filmcheck import cast, castlib
    acc = castlib.root()
    if acc is None:
        print("✗ the app is not running: the channel's cast lives in the studio app (sh bin/studio app start)", file=sys.stderr)
        return 3
    try:
        rows = castlib.listing(acc, a.channel)
    except cast.CastError as e:
        print(f"✗ {e.code}: {e.message}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps({"channels": rows}, ensure_ascii=False))
        return 0
    for ch in rows:
        print(f"{ch['channel']}:")
        for c in ch["characters"] or []:
            print(f"  {c['id']:<12} v{c['latest']}  {c['rig'] or '-':<8} {(c['approved_at'] or '')[:10]}  "
                  f"{len(c['films'])} film(s)" + (f"  new rig version: {c['new_rig']}" if c["new_rig"] else ""))
        if not ch["characters"]:
            print("  (empty)")
    if not rows:
        print("(no characters saved yet)")
    return 0


def cmd_cast_lib_change(a) -> int:
    """cast preview <ch>/<id> --rig ball@N (draws in AE) · cast update <ch>/<id> --from-preview · cast library-approve <ch>/<id>."""
    import shutil
    import subprocess
    import tempfile
    from filmcheck import cast, castlib
    acc = castlib.root()
    if acc is None:
        print("✗ the app is not running: the channel's cast lives in the studio app (sh bin/studio app start)", file=sys.stderr)
        return 3
    try:
        ch, cid, _ = castlib.parse_ref(a.ref)
        if a.cmd == "update":
            print(f"✓ {ch}/{cid}: v{castlib.update_from_preview(acc, ch, cid)} waits for approval (cast library-approve {ch}/{cid})")
            return 0
        if a.cmd == "library-approve":
            print(f"✓ {ch}/{cid}: v{castlib.approve_latest(acc, ch, cid, os.environ.get('STUDIO_USER') or 'local')} approved")
            return 0
        work = Path(tempfile.mkdtemp(prefix=f"cast-{ch}-{cid}-", dir=acc))
        try:
            d = castlib.work_film(acc, ch, cid, work / "films" / f"cast-{cid}", a.rig)
            r = subprocess.run(["sh", str(HERE.parents[1] / "bin" / "studio"), "ae", "sheet", str(d.name), "--dir", str(d)])
            if r.returncode:
                return r.returncode
            print(f"✓ {ch}/{cid}: preview v{castlib.store_result(acc, ch, cid, d, 'preview')} with {a.rig} "
                  f"(look at it in the app's Cast page; keep it: cast update {ch}/{cid} --from-preview)")
            return 0
        finally:
            shutil.rmtree(work, ignore_errors=True)
    except (cast.CastError, ValueError) as e:
        print(f"✗ {getattr(e, 'code', 'bad_rig')}: {getattr(e, 'message', e)}", file=sys.stderr)
        return 3 if getattr(e, "code", "") == "no_character" else 2


def cmd_cast_notes(a) -> int:
    """cast notes show <film> [--all] [--json] · cast notes reply <film> <id> "<text>" [--done|--open] --base <b>."""
    from filmcheck import cast, castnotes
    d = _cast_film(a)
    if d is None:
        return 2
    try:
        if a.ncmd == "reply":
            done = True if a.done else False if a.open else None
            n = castnotes.reply(d, a.note_id, a.text, done, a.base)
            print(f"✓ {n['id']}: replied" + (" · done" if n["done"] else ""))
            return 0
        doc = castnotes.load(d)
        b = castnotes.base(d)
        rows, waiting = [], 0
        lot = set((doc.get("lot") or {}).get("notes") or []) if doc.get("lot") else None
        for cid, n in castnotes.all_notes(doc):
            if n.get("done") and not a.all:
                continue
            if lot is not None and not a.all and n["id"] not in lot:   # FR-013: written during the redraw: next round
                waiting += 1
                continue
            pic = None
            if n.get("frame"):
                f = castnotes._frames(d, cid).get(n["frame"]) or {}
                if f.get("file"):
                    pic = str(cast.sheet_dir(d, cid) / f["file"])
            rows.append({"character": cid, **n, "picture": pic})
    except castnotes.CastNoteError as e:
        print(f"✗ {e.code}: {e.message}", file=sys.stderr)
        return e.exit_code()
    if a.json:
        print(json.dumps({"notes": rows, "base": b, "lot": doc.get("lot"), "waiting": waiting}, ensure_ascii=False))
        return 0
    if waiting:
        print(f"(this round: {len(rows)} note(s); {waiting} written since wait for the next round)")
    last = None
    for i, r in enumerate(rows, 1):
        if r["character"] != last:
            print(f"{r['character']}:")
            last = r["character"]
        where = "whole character" if not r.get("frame") else (f"{r['frame']} (request: draw it)" if r["kind"] == "view"
                else r["frame"] + (f" pin {r['x']},{r['y']}" if r.get("x") is not None else ""))
        print(f"  {i}. {r['id']} · {where}{' · done' if r.get('done') else ''}: {r['text']}")
        if r.get("picture"):
            print(f"     picture: {r['picture']}")
        if r.get("reply"):
            print(f"     reply: {r['reply']}")
    if not rows:
        print("(no open notes)")
    print(f"base: {b}")
    return 0


def edit_args(a) -> dict:
    args = {"ref": []}
    for t in a.args:
        k, eq, v = t.partition("=")
        if eq and k:
            args[k.replace("-", "_")] = v
        else:
            args["ref"].append(t)
    for k in ("text_file", "say", "reason", "confirm"):
        if getattr(a, k) is not None:
            args[k] = getattr(a, k)
    return args


def cmd_edit(a) -> int:
    from filmcheck import edit
    d = film_dir(a.film)
    r = edit.run(d, a.op, edit_args(a), a.base, a.by, a.source)
    if a.json:
        print(json.dumps(r, ensure_ascii=False))
    else:
        mark = {0: "✓", 1: "!"}.get(r["code"], "✗")
        print(f"{mark} edit {a.op} {r.get('ref') or ''}".rstrip() + (f": {r['error']}" if r.get("error") else "")
              + (f" · check {json.dumps(r['check'], ensure_ascii=False)[:300]}" if r.get("check") else ""))
        if r["code"] in (0, 1) and r["stale"]:
            print(f"  run again: {', '.join(r['stale'])}")
    return r["code"]


# ---------- shot marks, shot notes, the previous video (specs/029 contracts/cli.md) ----------
def app_film(name: str):
    """The film in the studio owner's library when the app runs for this project and has it (research R8), else None."""
    try:
        sys.path.insert(0, str(HERE.parent / "studio"))
        from studio import host
        project = Path(os.environ.get("STUDIO_ROOT") or HERE.parents[1])
        ptr = host.running_pointer(project)
        if not ptr:
            return None
        owner = host.owner_id(Path(ptr["data"]))
        d = Path(ptr["data"]) / "accounts" / owner / "films" / name if owner else None
        return d if d and d.is_dir() else None
    except Exception:                       # never let the app's state stop a command on the project's own film
        return None


def shot_film(a, quiet=False) -> Path:
    """--dir, else the app owner's copy of the film, else films/<film> of the project. Prints `film: <folder>`."""
    import re
    if getattr(a, "dir", None):
        d = Path(a.dir).expanduser().resolve()
    else:
        if not re.fullmatch(r"[a-z0-9-]{1,60}", a.film or ""):
            print(f"✗ bad film name: {a.film!r}", file=sys.stderr)
            raise SystemExit(2)
        d = app_film(a.film) or (Path(os.environ.get("STUDIO_ROOT") or HERE.parents[1]) / "films" / a.film).resolve()
    if not d.is_dir():
        print(f"✗ film folder not found: {d}", file=sys.stderr)
        raise SystemExit(2)
    print(f"film: {d}", file=sys.stderr if quiet else sys.stdout, flush=True)
    return d


def cmd_shots_export(a) -> int:
    from filmcheck import shotsexport
    d = shot_film(a)
    code, lines = shotsexport.export(d, os.environ.get("STUDIO_LIB"))
    print("\n".join(lines), file=sys.stdout if code == 0 else sys.stderr)
    return code


def cmd_notes_show(a) -> int:
    from filmcheck import shotnotes
    d = shot_film(a, quiet=a.json)
    try:
        if a.json:
            g = shotnotes.read_notes(d)
            print(json.dumps({"film": str(d), "base": g["base"], "doc": g["doc"], "orphans": g["orphans"],
                              "shots": shotnotes.load_shots(d)["shots"]}, ensure_ascii=False))
        else:
            print("\n".join(shotnotes.show_lines(d, a.all)[0]))
    except shotnotes.ShotError as e:
        print(f"✗ {e.message}", file=sys.stderr)
        return 2
    return 0


def cmd_notes_reply(a) -> int:
    from filmcheck import shotnotes
    d = shot_film(a)
    done = True if a.done else False if a.open else None
    try:
        r = shotnotes.reply(d, a.note_id, a.text, done, a.base)
    except shotnotes.ShotError as e:
        print(f"✗ {e.message}", file=sys.stderr)
        return {"changed": 4, "not_found": 1}.get(e.code, 2)
    n = next(n for sh in r["doc"]["shots"].values() for n in sh["notes"] if n["id"] == a.note_id)
    print(f"✓ {a.note_id}: {'fixed' if n['done'] else 'open'} · reply saved")
    print(f"base: {r['base']}")
    return 0


def cmd_film_replace(a) -> int:
    from filmcheck import shotnotes
    d = shot_film(a)
    try:
        r = shotnotes.replace_video(d, a.video, a.shots)
    except shotnotes.ShotError as e:
        print(f"✗ {e.message}; nothing was changed", file=sys.stderr)
        return 1
    old = f"{r['old']:.2f} s" if r["old"] is not None else "none"
    marks = (f"{r['shots']} shots" + (" (kept from before)" if r["kept_marks"] else "")) if r["shots"] else \
        "no shots.json: the old marks do not fit the new video (give --shots)"
    print(f"✓ video replaced: {old} → {r['new']:.2f} s · {marks}" + (" · previous kept" if r["prev"] else ""))
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

    s = sub.add_parser("qc-plan", help="tier 1: check the plan before rendering (specs/020)")
    s.add_argument("film")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("qc-shots", help="tier 2: one frame per shot, frame faults and the style (specs/020)")
    s.add_argument("--only", default=None, help="S012,S013: draw these shots again, write no tier result (specs/026)")
    s.add_argument("film")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("qc-accept-style", help="accept the style warnings with a reason (specs/020)")
    s.add_argument("film")
    s.add_argument("--reason", default="")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("qc-except", help="mark one shot as an exception to one rule (specs/020)")
    s.add_argument("film")
    s.add_argument("shot", nargs="?")
    s.add_argument("rule", nargs="?")
    s.add_argument("--reason", default="")
    s.add_argument("--list", action="store_true")
    s.add_argument("--remove", action="store_true")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("qc-voice", help="tier 0: check the voice lines (specs/020)")
    s.add_argument("film")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("voice-make", help="make the voice files, with each line's \"say\" spelling (specs/023)")
    s.add_argument("film")
    s.add_argument("--skip-review", default=None, help="make the voice without an approved script review (recorded)")
    s.add_argument("--only", default=None, help="L03,L07: make only these lines (specs/026)")
    s.add_argument("--changed", action="store_true", help="make only the lines whose text, say, voice or speed changed (specs/026)")
    s.add_argument("--yes", action="store_true", help="spend the ElevenLabs characters shown (specs/036)")
    s.add_argument("--provider", choices=["kokoro"], default=None, help="read the whole film with Kokoro (specs/036)")
    s = sub.add_parser("voice-usage", help="ElevenLabs characters used by a film (specs/036)")
    s.add_argument("film")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("voice-check", help="who says each line and with which voice (specs/036)")
    s.add_argument("film")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("voice-cast", help="a character's voice: listen to the choices, set one (specs/036)")
    s.add_argument("film")
    s.add_argument("action", choices=["sample", "set"])
    s.add_argument("character")
    s.add_argument("--option", type=int, default=None, help="1–3: one of the character's voice_options")
    s.add_argument("--voice", default=None, help="set: kokoro name or el:<id>")
    s.add_argument("--mode", choices=["own", "narrator"], default=None)
    s.add_argument("--pitch", type=float, default=None)
    s.add_argument("--speed", type=float, default=None)
    s.add_argument("--yes", action="store_true", help="sample: spend the ElevenLabs characters shown")
    s = sub.add_parser("voice-channel", help="a channel's narrator and side-part voices (specs/036)")
    s.add_argument("slug")
    s.add_argument("what", choices=["show", "narrator", "role"])
    s.add_argument("role", nargs="?", default=None, help="boy|girl|woman|man|old_man|old_woman (with role)")
    s.add_argument("--voice", default=None, help="kokoro name or el:<id>")
    s.add_argument("--mode", choices=["own", "narrator"], default=None, help="role: own voice or the narrator plays it")
    s.add_argument("--pitch", type=float, default=None)
    s.add_argument("--speed", type=float, default=None)
    s.add_argument("--add", action="store_true", help="role: add this choice instead of replacing the list")
    s.add_argument("--json", action="store_true")
    el = sub.add_parser("eleven", help="the ElevenLabs account (specs/036)").add_subparsers(dest="cmd", required=True)
    s = el.add_parser("test", help="is the key good, and how many characters are left")
    s = el.add_parser("voices", help="the account's voices")
    s.add_argument("--json", action="store_true")
    s.add_argument("--refresh", action="store_true")
    s = sub.add_parser("voice-asr", help="word stamps with the studio's recogniser model (specs/020)")
    s.add_argument("film")
    s.add_argument("--only", default=None, help="L03,L07: stamp only these lines, merged into words.json (specs/026)")
    s.add_argument("--lang", default=None)
    for name in ("qc-limits", "render-done"):
        s = sub.add_parser(name, help="used by sh bin/studio render (specs/020)")
        s.add_argument("film")
    s = sub.add_parser("render-gate", help="may this film be rendered? (specs/020)")
    s.add_argument("film")
    s.add_argument("--skip-checks", default=None)

    pt = sub.add_parser("point", help="review points of a film (specs/026)").add_subparsers(dest="cmd", required=True)
    s = pt.add_parser("status")
    s.add_argument("film")
    s.add_argument("--json", action="store_true")
    s = pt.add_parser("set")
    s.add_argument("film")
    s.add_argument("points", help="script,shots,… or none")
    s = pt.add_parser("approve")
    s.add_argument("film")
    s.add_argument("point")
    s.add_argument("--base")
    s.add_argument("--source", default="chat", choices=["ui", "chat", "api"])
    s.add_argument("--by", default="local")
    s.add_argument("--review", default=None)
    s.add_argument("--anyway", action="store_true", help="animatic: approve with more silence than the limit (owner only)")
    s.add_argument("--json", action="store_true")
    s = pt.add_parser("gate")
    s.add_argument("film")
    s.add_argument("point")

    an = sub.add_parser("animatic", help="the Animatic of an AE film (specs/035)").add_subparsers(dest="cmd", required=True)
    for name in ("status", "start", "fit", "undo"):
        s = an.add_parser(name)
        s.add_argument("film")
        s.add_argument("--json", action="store_true")
        if name == "undo":
            s.add_argument("--base")
    s = an.add_parser("accept")
    s.add_argument("film")
    s.add_argument("shots", nargs="?", help="S2,S6")
    s.add_argument("--all", action="store_true")
    s.add_argument("--base")
    s = an.add_parser("skip")
    s.add_argument("film")
    s.add_argument("shot")
    s.add_argument("--base")
    s = an.add_parser("notes", help="notes pinned on the draft's shots (US3)")
    s.add_argument("film")
    ns = s.add_subparsers(dest="ncmd", required=True)
    x = ns.add_parser("add")
    x.add_argument("shot")
    x.add_argument("--text", required=True)
    x.add_argument("--at", type=float)
    x.add_argument("--x", type=float)
    x.add_argument("--y", type=float)
    x.add_argument("--base")
    x = ns.add_parser("delete")
    x.add_argument("shot")
    x.add_argument("note_id")
    x.add_argument("--base")
    x = ns.add_parser("show")
    x.add_argument("--all", action="store_true")
    x.add_argument("--json", action="store_true")
    x = ns.add_parser("reply")
    x.add_argument("note_id")
    x.add_argument("--text", required=True)
    x.add_argument("--done", action="store_true")
    x.add_argument("--open", action="store_true")
    x.add_argument("--base")

    s = sub.add_parser("edit", help="change one part of a film from the job page, the chat or the API (specs/026)")
    s.add_argument("film")
    s.add_argument("op")
    s.add_argument("args", nargs="*", help="a reference (P03, L17, S012, a rule) and key=value pairs")
    s.add_argument("--base")
    s.add_argument("--by", default="local")
    s.add_argument("--source", default="chat", choices=["ui", "chat", "api"])
    s.add_argument("--text-file")
    s.add_argument("--say")
    s.add_argument("--reason")
    s.add_argument("--confirm")
    s.add_argument("--json", action="store_true")

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
    s.add_argument("--topic", type=int, help="the topic this film makes (specs/013)")

    kt = sub.add_parser("kit", help="the film kit of a learned style (specs/022)").add_subparsers(dest="cmd", required=True)
    s = kt.add_parser("use", help="copy my-styles/<style>/kit/ into films/<film>/kit/")
    s.add_argument("film")
    s.add_argument("--style")
    s.add_argument("--update", action="store_true", help="replace a kit copied from an older version")
    s.add_argument("--json", action="store_true")

    pe = sub.add_parser("people", help="the real-person library (specs/028)").add_subparsers(dest="cmd", required=True)
    s = pe.add_parser("list"); s.add_argument("--json", action="store_true")
    s = pe.add_parser("new"); s.add_argument("slug"); s.add_argument("--name", required=True); s.add_argument("--role")
    s.add_argument("--ref-url"); s.add_argument("--license"); s.add_argument("--author"); s.add_argument("--from", dest="from_file")
    s.add_argument("--ref-file", help="a reference photo already on the machine"); s.add_argument("--json", action="store_true")
    s = pe.add_parser("sheet"); s.add_argument("slug"); s.add_argument("--json", action="store_true")
    s = pe.add_parser("approve", help="only after the user approved the model sheet"); s.add_argument("slug"); s.add_argument("--note")
    s.add_argument("--source", choices=["chat", "ui"], default="chat"); s.add_argument("--json", action="store_true")
    s = pe.add_parser("use"); s.add_argument("film"); s.add_argument("slugs", nargs="+"); s.add_argument("--json", action="store_true")
    s = pe.add_parser("check"); s.add_argument("film"); s.add_argument("--json", action="store_true")

    tp = sub.add_parser("topics", help="score topics with YouTube numbers (specs/013)").add_subparsers(dest="cmd", required=True)
    s = tp.add_parser("score")
    s.add_argument("channel")
    s.add_argument("topics", nargs="*")
    s.add_argument("--file")
    s.add_argument("--suggest", action="store_true")
    s.add_argument("--json", action="store_true")
    s = tp.add_parser("recheck")
    s.add_argument("channel")
    s.add_argument("n", nargs="*", type=int)
    s.add_argument("--json", action="store_true")
    s = tp.add_parser("queue")
    s.add_argument("channel")
    s.add_argument("--all", action="store_true")
    s.add_argument("--json", action="store_true")
    s = tp.add_parser("take")
    s.add_argument("channel")
    s.add_argument("--film")
    s.add_argument("--allow-stale", action="store_true")
    for name in ("made",):
        s = tp.add_parser(name)
        s.add_argument("channel")
        s.add_argument("n", type=int)
    s = tp.add_parser("type")
    s.add_argument("channel")
    s.add_argument("n", type=int)
    s.add_argument("type")
    s = tp.add_parser("fit")
    s.add_argument("channel")
    s.add_argument("n", type=int)
    s.add_argument("score", type=int)
    s = tp.add_parser("refs")
    s.add_argument("channel")
    s.add_argument("--add", nargs="+")
    s.add_argument("--remove", nargs="+")
    tp.add_parser("usage")

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

    sh = sub.add_parser("shots", help="the shot marks of a film (specs/029)").add_subparsers(dest="cmd", required=True)
    s = sh.add_parser("export", help="write shots.json from the page's window.SHOTS (no frames drawn)")
    s.add_argument("film"); s.add_argument("--dir")

    nt = sub.add_parser("notes", help="shot notes written on the film page (specs/029)").add_subparsers(dest="cmd", required=True)
    s = nt.add_parser("show", help="the open notes, grouped by shot")
    s.add_argument("film"); s.add_argument("--all", action="store_true"); s.add_argument("--json", action="store_true")
    s.add_argument("--dir")
    s = nt.add_parser("reply", help="answer a note; --done ticks it, --open opens it again")
    s.add_argument("film"); s.add_argument("note_id"); s.add_argument("text")
    g = s.add_mutually_exclusive_group(); g.add_argument("--done", action="store_true"); g.add_argument("--open", action="store_true")
    s.add_argument("--base", required=True); s.add_argument("--dir")
    ca = sub.add_parser("cast", help="the characters of an After Effects film (specs/034)").add_subparsers(dest="cmd", required=True)
    s = ca.add_parser("check", help="check cast/cast.json and the rig catalog"); s.add_argument("film")
    s = ca.add_parser("status", help="the characters, their states and open notes"); s.add_argument("film")
    s.add_argument("--json", action="store_true")
    s = ca.add_parser("approve", help="approve characters (--all approves the cast review point)")
    s.add_argument("film"); s.add_argument("ids", nargs="*"); s.add_argument("--all", action="store_true")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--save", dest="save", action="store_true", default=None); g.add_argument("--no-save", dest="save", action="store_false")
    s.add_argument("--source", choices=["chat", "ui"], default="chat"); s.add_argument("--base")
    s = ca.add_parser("use", help="put a character of the channel's cast in this film"); s.add_argument("film"); s.add_argument("ref")
    s = ca.add_parser("library", help="the channel's cast (in the studio app)"); s.add_argument("channel", nargs="?")
    s.add_argument("--json", action="store_true")
    s = ca.add_parser("preview", help="draw a library character with a newer rig (After Effects)"); s.add_argument("ref")
    s.add_argument("--rig", required=True)
    s = ca.add_parser("update", help="the preview becomes a new version waiting for approval"); s.add_argument("ref")
    s.add_argument("--from-preview", action="store_true", required=True)
    s = ca.add_parser("library-approve", help="approve the library version waiting for approval"); s.add_argument("ref")
    s = ca.add_parser("notes", help="notes pinned on the cast sheet").add_subparsers(dest="ncmd", required=True)
    n = s.add_parser("show"); n.add_argument("film"); n.add_argument("--all", action="store_true"); n.add_argument("--json", action="store_true")
    n = s.add_parser("reply"); n.add_argument("film"); n.add_argument("note_id"); n.add_argument("text")
    g = n.add_mutually_exclusive_group(); g.add_argument("--done", action="store_true"); g.add_argument("--open", action="store_true")
    n.add_argument("--base")
    fm = sub.add_parser("film", help="the film's video (specs/029)").add_subparsers(dest="cmd", required=True)
    s = fm.add_parser("replace", help="put a new video in place, keeping one previous")
    s.add_argument("film"); s.add_argument("video"); s.add_argument("--shots"); s.add_argument("--dir")

    c = sub.add_parser("config", help="local settings").add_subparsers(dest="cmd", required=True)
    c.add_parser("youtube-key", help="save your YouTube Data API key (typed in, not shown)")
    s = c.add_parser("model", help="the studio's one Claude model (specs/024); no value prints it")
    s.add_argument("value", nargs="?")
    s = c.add_parser("render", help="auto: GPU when the machine can (specs/019); software: never the GPU")
    s.add_argument("value", choices=list(editor.RENDER_SETTINGS))
    return p


COMMANDS = {("script", "check"): cmd_check, ("script", "review"): cmd_review, ("script", "status"): cmd_status,
            ("script", "skip"): cmd_skip, ("web", "fetch"): cmd_fetch, ("config", "model"): cmd_model, ("config", "render"): cmd_render_setting,
            ("qc", "qc"): cmd_qc, ("publish", "publish"): cmd_publish,
            ("qc-plan", "qc-plan"): cmd_qc_plan, ("render-gate", "render-gate"): cmd_render_gate,
            ("qc-shots", "qc-shots"): cmd_qc_shots, ("qc-accept-style", "qc-accept-style"): cmd_qc_accept_style,
            ("qc-except", "qc-except"): cmd_qc_except, ("qc-voice", "qc-voice"): cmd_qc_voice,
            ("voice-asr", "voice-asr"): cmd_voice_asr, ("voice-make", "voice-make"): cmd_voice_make,
            ("voice-usage", "voice-usage"): cmd_voice_usage, ("eleven", "test"): cmd_eleven, ("eleven", "voices"): cmd_eleven,
            ("voice-check", "voice-check"): cmd_voice_check, ("voice-channel", "voice-channel"): cmd_voice_channel,
            ("voice-cast", "voice-cast"): cmd_voice_cast,
            ("qc-limits", "qc-limits"): cmd_qc_limits,
            ("render-done", "render-done"): cmd_render_done,
            ("point", "status"): cmd_point_status, ("point", "set"): cmd_point_set, ("point", "approve"): cmd_point_approve,
            ("point", "gate"): cmd_point_gate,
            ("animatic", "status"): cmd_animatic_status, ("animatic", "start"): cmd_animatic_start,
            ("animatic", "fit"): cmd_animatic_fit, ("animatic", "accept"): cmd_animatic_accept,
            ("animatic", "skip"): cmd_animatic_skip, ("animatic", "notes"): cmd_animatic_notes, ("animatic", "undo"): cmd_animatic_undo, ("edit", "edit"): cmd_edit,
            ("channel", "list"): cmd_channel_list, ("channel", "new"): cmd_channel_new,
            ("channel", "show"): cmd_channel_show, ("channel", "set"): cmd_channel_set,
            ("channel", "decide"): cmd_channel_decide, ("channel", "attach"): cmd_channel_attach, ("kit", "use"): cmd_kit_use,
            ("shots", "export"): cmd_shots_export,
            ("notes", "show"): cmd_notes_show, ("notes", "reply"): cmd_notes_reply, ("film", "replace"): cmd_film_replace,
            ("cast", "check"): cmd_cast_check, ("cast", "status"): cmd_cast_status, ("cast", "approve"): cmd_cast_approve, ("cast", "notes"): cmd_cast_notes, ("cast", "use"): cmd_cast_use, ("cast", "preview"): cmd_cast_lib_change, ("cast", "update"): cmd_cast_lib_change, ("cast", "library-approve"): cmd_cast_lib_change, ("cast", "library"): cmd_cast_library,
            ("people", "list"): cmd_people_list, ("people", "new"): cmd_people_new, ("people", "sheet"): cmd_people_sheet,
            ("people", "approve"): cmd_people_approve, ("people", "use"): cmd_people_use, ("people", "check"): cmd_people_check,
            ("lesson", "list"): cmd_lesson_list, ("lesson", "draft"): cmd_lesson_draft, ("lesson", "add"): cmd_lesson_add,
            ("lesson", "approve"): cmd_lesson_approve, ("lesson", "retire"): cmd_lesson_retire,
            ("topics", "score"): cmd_topics_score, ("topics", "recheck"): cmd_topics_recheck,
            ("topics", "queue"): cmd_topics_queue, ("topics", "take"): cmd_topics_take, ("topics", "made"): cmd_topics_made,
            ("topics", "type"): cmd_topics_type, ("topics", "fit"): cmd_topics_fit, ("topics", "refs"): cmd_topics_refs,
            ("topics", "usage"): cmd_topics_usage, ("config", "youtube-key"): cmd_youtube_key}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) > 1 and argv[0] == "qc" and argv[1] in QC_SUBS:      # qc plan <film> → qc-plan <film>
        argv = (["qc"] if argv[1] == "final" else [f"qc-{argv[1]}"]) + argv[2:]
    a = parser().parse_args(argv)
    if "cmd" not in a or a.cmd is None:
        a.cmd = a.group
    return COMMANDS.get((a.group, a.cmd), not_yet)(a)


if __name__ == "__main__":
    sys.exit(main())
