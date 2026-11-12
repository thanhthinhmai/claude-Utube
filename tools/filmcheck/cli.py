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
def cmd_editor_model(a) -> int:
    editor.set_editor_model(a.value)
    print(f"✓ script editor model: {a.value}" + (" (same as the film)" if a.value == "inherit" else ""))
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
        shotcheck.accept_style(d, a.reason)
    except tiers.TierError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    print(f"✓ style warnings accepted: {a.reason.strip()}")
    return 0


def cmd_qc_except(a) -> int:
    from filmcheck import tiers
    d = film_dir(a.film)
    if a.list or not a.shot:
        for e in tiers.load_exceptions(d):
            print(f"  {e['shot']} {e['rule']} — {e['reason']} ({e.get('at', '')})")
        return 0
    if not a.rule:
        print("✗ usage: qc except <film> <shot> <rule> --reason \"…\" | --remove", file=sys.stderr)
        return 2
    try:
        if a.remove:
            if not tiers.remove_exception(d, a.shot, a.rule):
                print(f"✗ no exception for {a.shot} {a.rule}", file=sys.stderr)
                return 2
            print(f"✓ removed: {a.shot} {a.rule}")
        else:
            tiers.add_exception(d, a.shot, a.rule, a.reason)
            print(f"✓ exception: {a.shot} {a.rule} — {a.reason.strip()}")
    except tiers.TierError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    t = tiers.recompute(d).get("tiers") or {}
    for k in ("plan", "shots"):
        if t.get(k):
            print(f"  {k}: {'pass' if t[k]['pass'] else 'fail'}")
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


def cmd_voice_asr(a) -> int:
    d = film_dir(a.film)
    lang = film_lang(d, a.lang)
    model = asr_model(lang)
    lib = Path(lib_dir())
    py = lib / ".venv" / "bin" / "python"
    cmd = [str(py if py.is_file() else "python3"), str(lib / "core" / "tts" / "asr_check.py"), str(d / "lines.json"),
           str(d / "voices"), "--lang", lang, "--model", model]
    print(f"model: {model} ({lang})")
    if os.environ.get("STUDIO_ASR_DRY"):
        print(" ".join(cmd))
        return 0
    import subprocess
    return subprocess.run(cmd).returncode


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
    for w in why:
        print(f"✗ render: {w}", file=sys.stderr)
    return 1 if why else 0


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
    s.add_argument("film")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("qc-accept-style", help="accept the style warnings with a reason (specs/020)")
    s.add_argument("film")
    s.add_argument("--reason", default="")
    s = sub.add_parser("qc-except", help="mark one shot as an exception to one rule (specs/020)")
    s.add_argument("film")
    s.add_argument("shot", nargs="?")
    s.add_argument("rule", nargs="?")
    s.add_argument("--reason", default="")
    s.add_argument("--list", action="store_true")
    s.add_argument("--remove", action="store_true")
    s = sub.add_parser("qc-voice", help="tier 0: check the voice lines (specs/020)")
    s.add_argument("film")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("voice-asr", help="word stamps with the studio's recogniser model (specs/020)")
    s.add_argument("film")
    s.add_argument("--lang", default=None)
    s = sub.add_parser("render-gate", help="may this film be rendered? (specs/020)")
    s.add_argument("film")
    s.add_argument("--skip-checks", default=None)

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

    c = sub.add_parser("config", help="local settings").add_subparsers(dest="cmd", required=True)
    c.add_parser("youtube-key", help="save your YouTube Data API key (typed in, not shown)")
    s = c.add_parser("editor-model")
    s.add_argument("value", choices=list(editor.MODELS))
    s = c.add_parser("render", help="auto: GPU when the machine can (specs/019); software: never the GPU")
    s.add_argument("value", choices=list(editor.RENDER_SETTINGS))
    return p


COMMANDS = {("script", "check"): cmd_check, ("script", "review"): cmd_review, ("script", "status"): cmd_status,
            ("script", "skip"): cmd_skip, ("web", "fetch"): cmd_fetch, ("config", "editor-model"): cmd_editor_model, ("config", "render"): cmd_render_setting,
            ("qc", "qc"): cmd_qc, ("publish", "publish"): cmd_publish,
            ("qc-plan", "qc-plan"): cmd_qc_plan, ("render-gate", "render-gate"): cmd_render_gate,
            ("qc-shots", "qc-shots"): cmd_qc_shots, ("qc-accept-style", "qc-accept-style"): cmd_qc_accept_style,
            ("qc-except", "qc-except"): cmd_qc_except, ("qc-voice", "qc-voice"): cmd_qc_voice,
            ("voice-asr", "voice-asr"): cmd_voice_asr,
            ("channel", "list"): cmd_channel_list, ("channel", "new"): cmd_channel_new,
            ("channel", "show"): cmd_channel_show, ("channel", "set"): cmd_channel_set,
            ("channel", "decide"): cmd_channel_decide, ("channel", "attach"): cmd_channel_attach,
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
