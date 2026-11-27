"""Edits from the job page, the chat or the API (specs/026, research R6, contracts/cli.md "edit"). One frame for every
edit: busy lock → base check → validate (nothing is written when it fails) → write via a temp file → the step's own
command → one line in .check/edits.jsonl → a JSON result. Standard library only.

Exit codes: 0 saved and checks pass · 1 saved, checks do not pass · 2 invalid, nothing written · 4 base is not the
current fingerprint · 5 busy (a live lock on a step this edit touches)."""
import json
import os
import socket
import tempfile
import time
from pathlib import Path

from filmcheck import points, steps

LOCK_MAX = 6 * 3600


class EditError(Exception):
    """Invalid edit (exit code 2): nothing was written."""


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


# ---------- busy lock (research R13) ----------
def lock_file(d: Path) -> Path:
    return Path(d) / ".check" / "busy.json"


def host() -> str:
    return os.environ.get("STUDIO_HOST_ID") or socket.gethostname()


def _pid_alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def read_lock(d: Path):
    """The live lock {step, pid, host, since, by}, or None. Same host: the pid runs and the lock is < 6 h old. Another
    host (online: job run in the job's container): < 6 h old and, when the runner says which step the job is running
    (STUDIO_JOB_STEP; empty = not running), that step is the lock's step."""
    try:
        lk = json.loads(lock_file(d).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    try:
        age = time.time() - time.mktime(time.strptime(lk["since"], "%Y-%m-%dT%H:%M:%SZ")) + time.timezone
    except (KeyError, TypeError, ValueError):
        return None
    if age > LOCK_MAX:
        return None
    if lk.get("host") == host():
        return lk if _pid_alive(lk.get("pid")) else None
    running = os.environ.get("STUDIO_JOB_STEP")
    if running is not None and running != lk.get("step"):
        return None
    return lk


def take_lock(d: Path, step: str, by: str = "edit") -> dict:
    lk = {"step": step, "pid": os.getpid(), "host": host(), "since": now(), "by": by}
    write_atomic(lock_file(d), json.dumps(lk))
    return lk


def drop_lock(d: Path, pid: int = None) -> None:
    try:
        lk = json.loads(lock_file(d).read_text(encoding="utf-8"))
        if pid is None or lk.get("pid") == pid:
            lock_file(d).unlink()
    except (OSError, ValueError):
        pass


def blocks(lock_step: str, own: str) -> bool:
    """A lock on this step, or on a step that depends on it, blocks the edit (the work under the lock reads it)."""
    return lock_step == own or lock_step in steps.after(own)


# ---------- the operations ----------
OPS = {}


def op(name, point, fp=None):
    """fp: the fingerprint the edit's base is checked against (default: the point's)."""
    def reg(fn):
        OPS[name] = {"point": point, "fn": fn, "fp": fp}
        return fn
    return reg


def log_edit(d: Path, entry: dict) -> None:
    p = Path(d) / ".check" / "edits.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run(film_dir: Path, name: str, args: dict, base: str = None, by: str = "local", source: str = "ui") -> dict:
    """Run one edit. The op function validates (raise EditError), writes, runs its step command and returns
    {ref, old, new, ok, check, files}."""
    d = Path(film_dir)
    res = {"ok": False, "code": 2, "op": name, "point": None, "ref": None, "fingerprint": None, "check": None,
           "stale": [], "files": [], "error": None}
    spec = OPS.get(name)
    if not spec:
        res["error"] = f"unknown edit \"{name}\" (one of {', '.join(sorted(OPS))})"
        return res
    point = spec["point"]
    own = points.STEP[point] if point in points.STEP else "Shots"
    res["point"] = point
    lk = read_lock(d)
    if lk and blocks(lk["step"], own):
        res.update(code=5, error=f"busy: {lk['step']} is running ({lk.get('by', '')}); try again when it ends")
        return res
    fp = spec["fp"](d) if spec.get("fp") else points.fingerprint(d, point)
    if base is not None and base != fp:
        res.update(code=4, fingerprint=fp, error="changed since you opened it: reload")
        return res
    mine = take_lock(d, own)
    try:
        out = spec["fn"](d, dict(args or {}))
    except EditError as e:
        res.update(code=2, error=str(e), fingerprint=fp)
        return res
    finally:
        drop_lock(d, mine["pid"])
    stale = steps.impact(point, d) if point in steps.POINT_STEP and not out.get("no_stale") else []
    res.update(ok=bool(out.get("ok", True)), code=0 if out.get("ok", True) else 1, ref=out.get("ref"),
               check=out.get("check"), files=out.get("files") or [], stale=stale,
               fingerprint=spec["fp"](d) if spec.get("fp") else points.fingerprint(d, point),
               error=out.get("error"))
    res.update({k: out[k] for k in ("rebuild", "silence") if k in out})       # specs/035: what the draft builds again
    log_edit(d, {"at": now(), "by": by, "source": source, "op": name, "point": point, "ref": out.get("ref"),
                 "old": out.get("old"), "new": out.get("new"), "result": "ok" if res["ok"] else "check_failed",
                 "stale": stale})
    return res


# ---------- script (US1) ----------
@op("script-para", "script")
def script_para(d: Path, a: dict) -> dict:
    import re
    from filmcheck import script
    para, text = str(a.get("para") or (a.get("ref") or [""])[0]), a.get("text")
    if text is None and a.get("text_file"):
        try:
            text = Path(a["text_file"]).read_text(encoding="utf-8")
        except OSError as e:
            raise EditError(f"the text file cannot be read: {e}") from None
    text = " ".join(str(text or "").split())
    if not re.fullmatch(r"P\d{2,3}", para):
        raise EditError("para: a paragraph id such as P03")
    if not text:
        raise EditError("the paragraph cannot be empty")
    if len(text) > 4000:
        raise EditError("a paragraph is at most 4000 characters")
    if "[P" in text:
        raise EditError("the text cannot hold a paragraph mark such as [P04]")
    path = d / "SCRIPT.md"
    try:
        sc = script.read_script(path)
    except script.ScriptError as e:
        raise EditError(str(e)) from None
    if para not in script.para_map(sc):
        raise EditError(f"SCRIPT.md has no paragraph {para}")
    old = script.para_map(sc)[para]
    lines = path.read_text(encoding="utf-8").splitlines()
    out, skip = [], False
    for ln in lines:
        m = re.match(r"^\s*\[(P\d+)\]", ln)
        if m:
            skip = m.group(1) == para
            if skip:
                out.append(f"[{para}] {text}")
                continue
        elif skip and ln.strip() and not ln.strip().startswith(">"):
            continue                            # the old paragraph's other lines
        elif skip and not ln.strip():
            skip = False
        out.append(ln)
    write_atomic(path, "\n".join(out) + "\n")
    r = script.check(d, customer_round=True)
    from filmcheck import report

    def save(x):
        x["narration"] = True
        x["script"]["machine"].append({"round": len(x["script"]["machine"]) + 1, "score": r["score"], "hard": r["hard"],
                                       "issues": r["issues"], "est_seconds": r["est_seconds"], "at": now(),
                                       "edit": para})
    report.update(d, save)
    failed = [k for k, ok in r["hard"].items() if not ok]
    return {"ref": para, "old": old, "new": text, "ok": r["pass"],
            "check": {"score": r["score"], "pass": r["pass"], "failed": failed, "issues": r["issues"][:20],
                      "est_seconds": r["est_seconds"]}}


# ---------- shots (US2) ----------
def lib_path() -> Path:
    return Path(os.environ.get("STUDIO_LIB") or Path(__file__).resolve().parents[2] / "lib" / "lemo-opuscar")


def no_run() -> bool:
    """Tests: save and validate only; the step command (browser, TTS, mix) is not run."""
    return bool(os.environ.get("STUDIO_EDIT_NO_RUN"))


def scenecheck(d: Path, file: Path) -> dict:
    import subprocess
    p = subprocess.run(["node", str(Path(__file__).resolve().parent / "scenecheck.mjs"), str(d), str(file)],
                       capture_output=True, text=True, timeout=120)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"ok": False, "error": (p.stderr or p.stdout).strip()[-300:] or "scenecheck gave no answer"}


def ref_of(a: dict, key: str) -> str:
    return str(a.get(key) or (a.get("ref") or [""])[0])


@op("shot", "shots")
def shot(d: Path, a: dict) -> dict:
    import copy
    sid = ref_of(a, "shot")
    f = d / "scenes.json"
    if not f.is_file():
        raise EditError("no scene table: this film keeps its scenes in its page (only films with scenes.json can change a shot here)")
    try:
        doc = json.loads(f.read_text(encoding="utf-8"))
    except ValueError as e:
        raise EditError(f"scenes.json cannot be read: {e}") from None
    scenes = doc.get("scenes") if isinstance(doc, dict) else None
    s = next((x for x in scenes or [] if isinstance(x, dict) and x.get("id") == sid), None)
    if s is None:
        raise EditError(f"scenes.json has no shot \"{sid}\"")
    old = copy.deepcopy(s)
    changes = {k: str(a[k]) for k in ("set", "cam", "act") if a.get(k)}
    if not changes:
        raise EditError("say what to change: set=…, cam=… or act=…")
    if "set" in changes:
        s["set"] = changes["set"]
    if "cam" in changes:
        s["cam"] = changes["cam"]                    # a camera object (dist, yaw…) becomes the plain named camera
    if "act" in changes:
        cast = s.get("cast") or []
        if not cast:
            raise EditError(f"{sid} has nobody in it to act")
        acts = cast[0].get("act") or []
        t = acts[0][0] if acts and isinstance(acts[0], list) else 0.3
        cast[0]["act"] = [[t, changes["act"]]]
    tmp = d / ".check" / "scenes.edit.json"
    write_atomic(tmp, json.dumps(doc, ensure_ascii=False, indent=1))
    r = scenecheck(d, tmp)
    if not r.get("ok"):
        tmp.unlink(missing_ok=True)
        raise EditError(r.get("error") or "the scene table does not pass the kit's check")
    os.replace(tmp, f)
    out = {"ref": sid, "old": {k: old.get(k) if k != "act" else (old.get("cast") or [{}])[0].get("act") for k in changes},
           "new": changes, "ok": True, "check": {"scenes": "pass"}, "files": []}
    if no_run():
        return out
    from filmcheck import plancheck, shotcheck
    try:
        pr = plancheck.run(d, lib_path())
        out["check"]["plan"] = "pass" if pr["pass"] else f"{sum(1 for i in pr['issues'] if i['severity'] == 'block' and not i.get('excepted'))} problem(s)"
        out["ok"] = pr["pass"]
        out["files"] = shotcheck.preview(d, lib_path(), [sid])
    except (plancheck.PlanError, shotcheck.ShotError) as e:
        out.update(ok=False, error=str(e))
    return out


@op("shots-check", "shots")
def shots_check(d: Path, a: dict) -> dict:
    if no_run():
        return {"ref": "film", "ok": True, "check": {"skipped": True}}
    from filmcheck import plancheck, shotcheck
    try:
        pr = plancheck.run(d, lib_path())
        r = shotcheck.run(d, lib_path(), say=lambda x: None)
    except (plancheck.PlanError, shotcheck.ShotError) as e:
        return {"ref": "film", "ok": False, "error": str(e)}
    blk = sum(1 for i in r["issues"] if i["severity"] == "block" and not i.get("excepted"))
    wrn = sum(1 for i in r["issues"] if i["severity"] == "warn")
    return {"ref": "film", "ok": pr["pass"] and r["pass"],
            "check": {"plan": pr["pass"], "shots": r["pass"], "problems": blk, "warnings": wrn,
                      "accepted": bool((r.get("style_accept") or {}).get("reason"))}}


@op("except", "shots")
def except_shot(d: Path, a: dict) -> dict:
    from filmcheck import tiers
    refs = list(a.get("ref") or [])
    sid, rule = str(a.get("shot") or (refs[0] if refs else "")), str(a.get("rule") or (refs[1] if len(refs) > 1 else ""))
    if not sid or not rule:
        raise EditError("say which shot and which rule: except S012 dark --reason \"…\"")
    try:
        tiers.add_exception(d, sid, rule, a.get("reason") or "")
    except tiers.TierError as e:
        raise EditError(str(e)) from None
    t = tiers.recompute(d).get("tiers") or {}
    return {"ref": f"{sid} {rule}", "new": (a.get("reason") or "").strip(), "ok": bool((t.get("shots") or {}).get("pass")),
            "check": {k: t[k]["pass"] for k in ("plan", "shots") if t.get(k)}}


@op("accept-style", "shots")
def accept_style(d: Path, a: dict) -> dict:
    from filmcheck import shotcheck, tiers
    try:
        shotcheck.accept_style(d, a.get("reason") or "")
    except tiers.TierError as e:
        raise EditError(str(e)) from None
    return {"ref": "style", "new": (a.get("reason") or "").strip(), "ok": True}


# ---------- voice (US3) ----------
def studio_cli(*args) -> tuple:
    """Run a filmcheck command of the studio (voice make, voice asr, qc voice); (code, output)."""
    import subprocess
    import sys
    p = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "cli.py"), *args], capture_output=True,
                       text=True, timeout=3600, env={**os.environ, "STUDIO_LIB": str(lib_path())})
    return p.returncode, (p.stdout + p.stderr).strip()


def read_lines(d: Path) -> list:
    try:
        rows = json.loads((d / "lines.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise EditError(f"lines.json cannot be read: {e}") from None
    return rows


def line_of(rows: list, lid: str) -> dict:
    r = next((x for x in rows if isinstance(x, dict) and x.get("id") == lid), None)
    if r is None:
        raise EditError(f"lines.json has no line \"{lid}\"")
    return r


def voice_after(d: Path, ids=None, yes: bool = False) -> dict:
    """Make the voice of these lines again (all when None), stamp them and run the voice check. yes: the person
    confirmed the ElevenLabs characters (specs/036 FR-005); one line never asks."""
    if no_run():
        return {"ok": True, "check": {"skipped": True}}
    only = ["--only", ",".join(ids)] if ids else []
    code, txt = studio_cli("voice-make", str(d), *only, *(["--yes"] if yes else []))
    if code:
        return {"ok": False, "error": txt.splitlines()[-1] if txt else "voice make failed"}
    code, txt = studio_cli("voice-asr", str(d), *only)
    if code == 2:
        return {"ok": False, "error": txt.splitlines()[-1] if txt else "voice asr failed"}
    code, txt = studio_cli("qc-voice", str(d), "--json")
    try:
        r = json.loads(txt.splitlines()[-1])
        mine = [i for i in r.get("issues", []) if not ids or i.get("ref") in ids]
        return {"ok": not mine, "check": {"pass": r.get("pass"), "issues": mine[:10]}}
    except (ValueError, IndexError):
        return {"ok": False, "error": txt[-300:]}


@op("voice-say", "voice")
def voice_say(d: Path, a: dict) -> dict:
    lid = ref_of(a, "line")
    say = str(a.get("say") or "").strip()
    if len(say) > 400:
        raise EditError("\"say\" is at most 400 characters")
    rows = read_lines(d)
    r = line_of(rows, lid)
    old = r.get("say")
    if say:
        r["say"] = say
    else:
        r.pop("say", None)
    write_atomic(d / "lines.json", json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
    return {"ref": lid, "old": old, "new": say or None, "ok": True}


@op("voice-remake", "voice")
def voice_remake(d: Path, a: dict) -> dict:
    lid = ref_of(a, "line")
    line_of(read_lines(d), lid)
    out = voice_after(d, [lid])
    out.update(ref=lid)
    return out


@op("voice-tone", "voice")
def voice_tone(d: Path, a: dict) -> dict:
    """specs/036 FR-030: one line's emotion and sound effect; the line is made again (an effect alone does not read
    the line again, research R5)."""
    from filmcheck import speakers
    lid = ref_of(a, "line")
    emo, fx = a.get("emotion") or "neutral", a.get("fx") or "none"
    if emo not in speakers.EMOTIONS:
        raise EditError(f"emotion is one of {', '.join(speakers.EMOTIONS)}")
    if fx not in speakers.FXS:
        raise EditError(f"fx is one of {', '.join(speakers.FXS)}")
    rows = read_lines(d)
    r = line_of(rows, lid)
    old = {"emotion": r.get("emotion") or "neutral", "fx": r.get("fx") or "none"}
    if old == {"emotion": emo, "fx": fx}:
        raise EditError("nothing to change")
    for k, v, none in (("emotion", emo, "neutral"), ("fx", fx, "none")):
        if v == none:
            r.pop(k, None)
        else:
            r[k] = v
    write_atomic(d / "lines.json", json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
    out = voice_after(d, [lid])
    out.update(ref=lid, old=old, new={"emotion": emo, "fx": fx})
    return out


@op("voice-set", "voice")
def voice_set(d: Path, a: dict) -> dict:
    from filmcheck import channels
    voice, speed = a.get("voice"), a.get("speed")
    if a.get("confirm") != "all":
        raise EditError("changing the voice or speed makes every line again: confirm with --confirm all")
    if not voice and not speed:
        raise EditError("say voice=… and/or speed=…")
    if voice and not (channels.voice_ok(voice) and voice_known(voice)):
        raise EditError(f"\"{voice}\" is not a voice of the library")
    if speed is not None:
        try:
            speed = float(speed)
        except ValueError:
            raise EditError("speed: a number from 0.7 to 1.3") from None
        if not 0.7 <= speed <= 1.3:
            raise EditError("speed: a number from 0.7 to 1.3")
    rows = read_lines(d)
    first = next((r for r in rows if isinstance(r, dict)), {})
    old = {"voice": first.get("voice"), "speed": first.get("speed")}
    for r in rows:
        if isinstance(r, dict):
            if voice:
                r["voice"] = voice
            if speed is not None:
                r["speed"] = speed
    write_atomic(d / "lines.json", json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
    out = voice_after(d, yes=True)                  # "confirm all" is the person's yes to the characters shown
    out.update(ref="all lines", old=old, new={"voice": voice or old["voice"], "speed": speed if speed is not None else old["speed"]})
    return out


@op("voice-speaker", "voice")
def voice_speaker(d: Path, a: dict) -> dict:
    """specs/036 FR-012/FR-042: one speaker's voice — film.json → voices.<speaker> (the narrator: film.json → narrator,
    or the channel's narrator with scope=channel). Only that speaker's lines are made again."""
    from filmcheck import speakers
    sp = (a.get("speaker") or "").strip()
    if sp != "narrator" and not speakers.SPEAKER.match(sp):
        raise EditError("speaker: narrator or a character id")
    st = {"mode": a.get("mode") or "own"}
    if a.get("voice"):
        st["voice"] = a["voice"]
    for k in ("pitch", "speed"):
        if a.get(k) not in (None, ""):
            try:
                st[k] = float(a[k])
            except ValueError:
                raise EditError(f"{k}: a number") from None
    if st["mode"] == "own" and st.get("voice") and not voice_known(st["voice"]):
        raise EditError(f"\"{st['voice']}\" is not a voice of the library")
    if sp == "narrator" and st["mode"] == "narrator":
        raise EditError("the narrator needs its own voice")
    errs = speakers.check_setting(st, sp)
    if errs:
        raise EditError("; ".join(errs))
    rows = read_lines(d)
    mine = [r for r in rows if isinstance(r, dict) and r.get("id") and (r.get("speaker") or "narrator") == sp]
    if not mine:
        raise EditError(f"no line is said by \"{sp}\"")
    if len(mine) > 1 and a.get("confirm") != "speaker":
        raise EditError(f"this makes the {len(mine)} lines of {sp} again: confirm with confirm=speaker")
    film_p = d / "film.json"
    try:
        film = json.loads(film_p.read_text(encoding="utf-8")) if film_p.is_file() else {}
    except ValueError:
        raise EditError("film.json cannot be read") from None
    old = None
    if sp == "narrator" and a.get("scope") == "channel":
        slug = speakers.channel_of(d)
        if not slug:
            raise EditError("this film has no channel")
        old = speakers.channel_voice(store_root(d), slug)["narrator"]
        try:
            speakers.save_channel_voice(store_root(d), slug, narrator=st, by=a.get("by") or "local")
        except speakers.SpeakerError as e:
            raise EditError(str(e)) from None
    elif sp == "narrator":
        old, film["narrator"] = film.get("narrator"), st
    elif cast_char(d, sp) is not None:               # a cast character (specs/034): its voice lives in cast.json and
        from filmcheck import cast                  # wins there; the change asks for the character's approval again
        doc = cast.load(d)
        c = cast.find(doc, sp)
        old, c["voice"] = c.get("voice"), st
        cast.save(d, doc)
    else:
        film.setdefault("voices", {})
        old, film["voices"][sp] = film["voices"].get(sp), st
    if not (sp == "narrator" and a.get("scope") == "channel") and cast_char(d, sp) is None:
        write_atomic(film_p, json.dumps(film, ensure_ascii=False, indent=1) + "\n")
    for r in mine:                                   # the speaker's voice now speaks these lines
        r.pop("voice", None)
        if sp == "narrator":
            r.pop("speed", None)
    write_atomic(d / "lines.json", json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
    out = voice_after(d, [r["id"] for r in mine], yes=True)
    out.update(ref=f"speaker {sp}", old=old, new=st)
    return out


def cast_char(d: Path, sp: str):
    """The cast character with this id when the film has cast/cast.json (specs/034), else None."""
    from filmcheck import cast
    if sp == "narrator" or not cast.exists(d):
        return None
    try:
        return cast.find(cast.load(d), sp)
    except cast.CastError:
        return None


def store_root(d: Path) -> Path:
    """Where the film's channels live: the film's own root when it has channels/, else STUDIO_ROOT."""
    own = Path(d).resolve().parent.parent
    return own if (own / "channels").is_dir() else Path(os.environ.get("STUDIO_ROOT") or own)


def voice_known(v: str) -> bool:
    """A Kokoro voice in the library's voices-v1.0.bin (a zip of .npy files); edge-tts names pass when they look right."""
    import zipfile
    if v.endswith("Neural") or v.startswith("el:"):   # specs/036: ElevenLabs ids are checked by their form
        return True
    v = v[7:] if v.startswith("kokoro:") else v
    try:
        with zipfile.ZipFile(lib_path() / "core" / "tts" / "voices-v1.0.bin") as z:
            return f"{v}.npy" in z.namelist()
    except (OSError, zipfile.BadZipFile):
        return True                                  # no model here: the name's form was checked


# ---------- mix (US4) ----------
def mix_ranges(d: Path) -> dict:
    """research R11: music under the voice within the style's measured range ± 3 dB, duck and sfx fixed."""
    try:
        t = json.loads((d / "kit" / "template.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        t = {}
    lo, hi = ((t.get("sound") or {}).get("music_under_voice_db")) or [-8.5, -3.3]
    return {"music_under_voice_db": (round(lo - 3, 1), round(hi + 3, 1)), "duck_db": (-20.0, 0.0), "sfx_db": (-24.0, 6.0)}


@op("mix", "mix")
def mix_edit(d: Path, a: dict) -> dict:
    import re
    import subprocess
    if not (d / "kit" / "sound" / "mix.py").is_file():
        raise EditError("this film has no kit mix (kit/sound/mix.py): the mix cannot be changed here")
    try:
        cur = json.loads((d / "mix.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cur = {}
    new = dict(cur)
    if a.get("music"):
        if not re.fullmatch(r"seed:\d{1,4}|none", str(a["music"])):
            raise EditError("music: seed:N or none")
        new["music"] = str(a["music"])
    rng = mix_ranges(d)
    for key, field in (("under", "music_under_voice_db"), ("duck", "duck_db"), ("sfx", "sfx_db")):
        val = a.get(key, a.get(field))
        if val is None or val == "":
            continue
        try:
            x = float(val)
        except ValueError:
            raise EditError(f"{key}: a number of dB") from None
        lo, hi = rng[field]
        if not lo <= x <= hi:
            raise EditError(f"{key}: {x:g} dB is outside {lo:g} … {hi:g} dB")
        new[field] = round(x, 1)
    if new == cur:
        raise EditError("nothing to change: music=…, under=…, duck=… or sfx=…")
    write_atomic(d / "mix.json", json.dumps(new, indent=1) + "\n")
    out = {"ref": "mix", "old": cur, "new": new, "ok": True}
    if no_run():
        return out
    lib = lib_path()
    py = lib / ".venv" / "bin" / "python"
    p = subprocess.run([str(py if py.is_file() else "python3"), str(d / "kit" / "sound" / "mix.py"), str(d)], cwd=str(lib),
                       capture_output=True, text=True, timeout=3600)
    if p.returncode:
        return {**out, "ok": False, "error": (p.stderr or p.stdout).strip()[-300:]}
    video = d / "out" / "video.mp4"
    if video.is_file():                                # the picture is kept: only the sound goes back on
        final = d / f"{d.name}.mp4"
        m = subprocess.run(["sh", str(lib / "core" / "render" / "mux.sh"), str(video), str(d / "out" / "mix.wav"), str(final)],
                           cwd=str(lib), capture_output=True, text=True, timeout=3600)
        out["check"] = {"muxed": m.returncode == 0}
        if m.returncode:
            return {**out, "ok": False, "error": (m.stderr or m.stdout).strip()[-300:]}
    return out


# ---------- cast of an AE film (specs/034) ----------
@op("cast-approve", "cast")
def cast_approve(d: Path, a: dict) -> dict:
    """Approve one character (args: character=<id>, or ref=[id]); approving changes no picture (nothing goes stale)."""
    from filmcheck import cast
    cid = a.get("character") or (a.get("ref") or [None])[0]
    if not cid:
        raise EditError("cast-approve: character=<id>")
    try:
        why = cast.approve(d, [cid], "ui" if a.get("source", "ui") != "chat" else "chat", a.get("by") or "local")
    except cast.CastError as e:
        raise EditError(e.message) from None
    if why:
        return {"ok": False, "ref": cid, "error": "; ".join(why), "no_stale": True}
    from filmcheck import castlib                   # FR-015: the app's approval saves to the channel's cast too
    saved = castlib.save_if_wanted(d, [cid], a.get("by"))
    return {"ok": True, "ref": cid, "old": None, "new": "approved", "files": ["cast/cast.json"], "no_stale": True,
            **({"saved": saved} if saved else {})}


@op("cast-voice", "cast")
def cast_voice(d: Path, a: dict) -> dict:
    """specs/036 FR-013: a character's voice (args: character, option=1..3 | voice=<id>, mode=own|narrator, pitch,
    speed; cloned_ok=1 the first time a cloned voice is chosen). An approved character must be approved again."""
    from filmcheck import cast, speakers
    cid = a.get("character") or (a.get("ref") or [None])[0]
    if not cid:
        raise EditError("cast-voice: character=<id>")
    try:
        doc = cast.load(d)
        c = cast.find(doc, cid)
    except cast.CastError as e:
        raise EditError(e.message) from None
    opts = c.get("voice_options") or []
    if a.get("option") not in (None, ""):
        try:
            n = int(a["option"])
        except ValueError:
            raise EditError("option: 1 to 3") from None
        if not 1 <= n <= len(opts):
            raise EditError(f"{cid} has {len(opts)} voice choice(s)")
        st = dict(opts[n - 1]["setting"])
    else:
        st = {"mode": a.get("mode") or "own"}
        if a.get("voice"):
            st["voice"] = a["voice"]
    for k in ("pitch", "speed"):
        if a.get(k) not in (None, ""):
            try:
                st[k] = float(a[k])
            except ValueError:
                raise EditError(f"{k}: a number") from None
    if st.get("mode", "own") == "own" and st.get("voice") and not voice_known(st["voice"]):
        raise EditError(f"\"{st['voice']}\" is not a voice of the library")
    if str(a.get("cloned_ok", "")).lower() in ("1", "true", "yes"):
        st["cloned_ok"] = {"at": cast.now(), "by": a.get("by") or "local"}
    elif (c.get("voice") or {}).get("cloned_ok") and (c.get("voice") or {}).get("voice") == st.get("voice"):
        st["cloned_ok"] = c["voice"]["cloned_ok"]
    errs = speakers.check_setting(st, "voice")
    if errs:
        raise EditError("; ".join(errs))
    old = c.get("voice")
    c["voice"] = st
    cast.save(d, doc)
    return {"ok": True, "ref": cid, "old": old, "new": st, "files": ["cast/cast.json"], "no_stale": True}


@op("cast-save", "cast")
def cast_save(d: Path, a: dict) -> dict:
    """Turn "save approved characters to the channel's cast library" on or off (args: on=true|false)."""
    from filmcheck import cast
    v = str(a.get("on", "-")).lower()
    if v not in ("true", "false", "1", "0", "on", "off", "yes", ""):
        raise EditError("cast-save: on=true|false")
    try:
        doc = cast.load(d)
    except cast.CastError as e:
        raise EditError(e.message) from None
    old = doc.get("save_to_library", True)
    doc["save_to_library"] = v in ("true", "1", "on", "yes")
    cast.save(d, doc)
    return {"ok": True, "ref": "save_to_library", "old": old, "new": doc["save_to_library"], "files": ["cast/cast.json"],
            "no_stale": True}


def _notes_base(d: Path) -> str:
    from filmcheck import castnotes
    return castnotes.base(d)


def _note_text(a: dict):
    if a.get("text") is not None:
        return a["text"]
    if a.get("text_file"):
        try:
            return Path(a["text_file"]).read_text(encoding="utf-8")
        except OSError as e:
            raise EditError(f"cannot read the note text: {e}") from None
    return None


def _note_call(fn, *args, **kw):
    from filmcheck import castnotes
    try:
        return fn(*args, **kw)
    except castnotes.CastNoteError as e:
        raise EditError(f"{e.code}: {e.message}") from None


@op("cast-note-add", "cast", _notes_base)
def cast_note_add(d: Path, a: dict) -> dict:
    """A note on the cast sheet: character, kind (note|view), frame (none = the whole character), x, y (%), text."""
    from filmcheck import castnotes
    cid = a.get("character") or (a.get("ref") or [None])[0]
    if not cid:
        raise EditError("cast-note-add: character=<id>")
    x, y = a.get("x") or None, a.get("y") or None
    n = _note_call(castnotes.add, d, cid, a.get("kind") or "note", a.get("frame") or None, x, y, _note_text(a),
                   a.get("by") or "owner")
    return {"ok": True, "ref": n["id"], "new": n["text"], "files": ["cast-notes.json"], "no_stale": True}


@op("cast-note-edit", "cast", _notes_base)
def cast_note_edit(d: Path, a: dict) -> dict:
    """Change a note's words or move its pin: character, note, text?, x?, y?."""
    from filmcheck import castnotes
    a.setdefault("character", (a.get("ref") or [None])[0])
    if not a.get("character") or not a.get("note"):
        raise EditError("cast-note-edit: character=<id> note=<id>")
    n = _note_call(castnotes.edit, d, a["character"], a["note"], _note_text(a), a.get("x") or None, a.get("y") or None)
    return {"ok": True, "ref": n["id"], "new": n["text"], "files": ["cast-notes.json"], "no_stale": True}


@op("cast-note-delete", "cast", _notes_base)
def cast_note_delete(d: Path, a: dict) -> dict:
    from filmcheck import castnotes
    a.setdefault("character", (a.get("ref") or [None])[0])
    if not a.get("character") or not a.get("note"):
        raise EditError("cast-note-delete: character=<id> note=<id>")
    _note_call(castnotes.delete, d, a["character"], a["note"])
    return {"ok": True, "ref": a["note"], "files": ["cast-notes.json"], "no_stale": True}


@op("cast-view-toggle", "cast", _notes_base)
def cast_view_toggle(d: Path, a: dict) -> dict:
    """"Request this view" / "Undo" on a picture the sheet lacks: character, frame."""
    from filmcheck import castnotes
    a.setdefault("character", (a.get("ref") or [None])[0])
    if not a.get("character") or not a.get("frame"):
        raise EditError("cast-view-toggle: character=<id> frame=<key>")
    n = _note_call(castnotes.toggle_view, d, a["character"], a["frame"])
    return {"ok": True, "ref": n["id"] if n else a["frame"], "new": "requested" if n else "undone",
            "files": ["cast-notes.json"], "no_stale": True}

# ---------- the Animatic of an AE film (specs/035) ----------
def _timing_base(d: Path) -> str:
    from filmcheck import timing
    return timing.base(d)


def _anim_call(fn, *args, **kw):
    from filmcheck import animatic
    try:
        return fn(*args, **kw)
    except animatic.AnimaticError as e:
        raise EditError(f"{e.code}: {e.message}") from None


def _changed(before: dict, after: dict) -> list:
    return [s for s in after if before.get(s) != after.get(s)]


@op("animatic-fit-accept", "animatic", _timing_base)
def animatic_fit_accept(d: Path, a: dict) -> dict:
    """Accept fit suggestions: shots=S2,S6 or all. The result's `rebuild` lists the shots the draft must build again."""
    from filmcheck import animatic, timing
    want = a.get("shots") or ",".join(a.get("ref") or [])
    if not want:
        raise EditError("animatic-fit-accept: shots=S2,S6 or shots=all")
    before = dict(timing.require(d)["frames"])
    r = _anim_call(animatic.accept, d, "all" if want == "all" else [x for x in want.split(",") if x], by=a.get("by") or "local")
    return {"ok": True, "ref": ",".join(r["accepted"]), "old": before, "new": timing.load(d)["frames"],
            "files": ["timing.json", "narration.json"], "rebuild": _changed(before, timing.load(d)["frames"]),
            "silence": r["silence"]}


@op("animatic-fit-skip", "animatic", _timing_base)
def animatic_fit_skip(d: Path, a: dict) -> dict:
    from filmcheck import animatic
    shot = a.get("shot") or (a.get("ref") or [None])[0]
    if not shot:
        raise EditError("animatic-fit-skip: shot=S2")
    _anim_call(animatic.skip, d, shot)
    return {"ok": True, "ref": shot.upper(), "new": "skipped", "files": ["animatic/fit.json"], "no_stale": True}


@op("animatic-fit-undo", "animatic", _timing_base)
def animatic_fit_undo(d: Path, a: dict) -> dict:
    from filmcheck import animatic, timing
    before = dict(timing.require(d)["frames"])
    r = _anim_call(animatic.undo, d)
    after = timing.load(d)["frames"]
    return {"ok": True, "ref": "undo", "old": before, "new": after, "files": ["timing.json", "narration.json"],
            "rebuild": _changed(before, after), "silence": r["silence"]}


def _anim_notes_base(d: Path) -> str:
    from filmcheck import animatic
    return animatic.notes_base(d)


@op("animatic-note-add", "animatic", _anim_notes_base)
def animatic_note_add(d: Path, a: dict) -> dict:
    """A note on a shot of the draft: shot, text, at? (s), x?, y? (%) — no x/y: a general note on the shot."""
    from filmcheck import animatic
    shot = a.get("shot") or (a.get("ref") or [None])[0]
    if not shot:
        raise EditError("animatic-note-add: shot=S2")
    num = lambda k: None if a.get(k) in (None, "") else a.get(k)
    n = _anim_call(animatic.note_add, d, shot, _note_text(a), num("at"), num("x"), num("y"), by=a.get("by") or "owner")
    return {"ok": True, "ref": n["id"], "new": n["text"], "files": ["animatic/notes.json"], "no_stale": True}


@op("animatic-note-delete", "animatic", _anim_notes_base)
def animatic_note_delete(d: Path, a: dict) -> dict:
    from filmcheck import animatic
    shot = a.get("shot") or (a.get("ref") or [None])[0]
    if not shot or not a.get("note"):
        raise EditError("animatic-note-delete: shot=S2 note=<id>")
    _anim_call(animatic.note_delete, d, shot, a["note"])
    return {"ok": True, "ref": a["note"], "files": ["animatic/notes.json"], "no_stale": True}


@op("animatic-draft", "animatic", _timing_base)
def animatic_draft(d: Path, a: dict) -> dict:
    """Build the draft again (shots=S2,S6: those and every shot whose length changed; none: the whole film)."""
    import subprocess
    cmd = ["sh", str(Path(__file__).resolve().parents[2] / "bin" / "studio"), "ae", "draft", d.name, "--dir", str(d)]
    shots = a.get("shots") or ",".join(a.get("ref") or [])
    if shots:
        cmd += ["--shots", shots]
    from filmcheck import animatic
    before = (animatic.draft_info(d) or {}).get("built_at")
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    after = animatic.draft_info(d) or {}
    if p.returncode not in (0, 1) or not after or after.get("built_at") == before and p.returncode:
        raise EditError((p.stderr or p.stdout).strip()[-300:] or f"ae draft ended with {p.returncode}")
    return {"ok": True, "ref": shots or "all", "new": (p.stdout.strip().splitlines() or [""])[-1],
            "files": ["animatic/draft.mp4"], "no_stale": True}
# ---------- Sound of an AE film (specs/037 US3) ----------
def _plan_base(d: Path) -> str:
    from filmcheck import soundplan
    return soundplan.base(d)


def _sound_notes_base(d: Path) -> str:
    from filmcheck import soundnotes
    return soundnotes.base(d)


def _num(a: dict, key: str, kind=float):
    v = a.get(key)
    if v in (None, ""):
        return None
    try:
        return kind(v)
    except ValueError:
        raise EditError(f"{key}: a number") from None


def _plan_call(fn, *args, **kw):
    from filmcheck import soundplan
    try:
        return fn(*args, **kw)
    except soundplan.PlanError as e:
        raise EditError(f"{e.code}: {e.message}") from None


def _remix(d: Path, out: dict) -> dict:
    """Mix again after a cue edit (FR-026: ≤ 30 s) and put the sound back on a rendered film; nothing else goes stale."""
    out["no_stale"] = True
    if no_run():
        return out
    import time as _t
    from filmcheck import soundmix, soundplan
    t = _t.time()
    try:
        r = soundmix.run(d)
    except soundplan.PlanError as e:
        return {**out, "ok": False, "error": f"the mix failed: {e.message}"}
    out["check"] = {k: r.get(k) for k in ("placed", "dropped", "missing", "off", "muxed")} | {"secs": round(_t.time() - t, 1)}
    return out


def _cue_of(a: dict) -> str:
    cue = a.get("cue") or (a.get("ref") or [None])[0]
    if not cue:
        raise EditError("cue=<id> (c01 …)")
    return cue


@op("cue-set", "mix", _plan_base)
def cue_set(d: Path, a: dict) -> dict:
    """Change one sound: entry (another library sound), offset_f (frames), gain_db, cut, fade_s, len_s."""
    from filmcheck import soundplan
    cue = _cue_of(a)
    fields = {k: v for k, v in (("entry", a.get("entry") or None), ("offset_f", _num(a, "offset_f", int)),
                                ("gain_db", _num(a, "gain_db")), ("cut", a.get("cut") or None), ("fade_s", _num(a, "fade_s")),
                                ("len_s", _num(a, "len_s"))) if v is not None}
    if not fields:
        raise EditError("nothing to change: entry=…, offset_f=…, gain_db=…, cut=…, fade_s=… or len_s=…")
    old = next((c for c in soundplan.load(d)["cues"] if c["id"] == cue), None)
    c = _plan_call(soundplan.set_cue, d, cue, fields, by=a.get("by") or "user")
    return _remix(d, {"ok": True, "ref": cue, "old": {k: (old or {}).get(k) for k in fields}, "new": {k: c.get(k) for k in fields},
                      "files": ["sound/plan.json", "out/mix.wav"]})


@op("cue-rm", "mix", _plan_base)
def cue_rm(d: Path, a: dict) -> dict:
    from filmcheck import soundplan
    cue = _cue_of(a)
    _plan_call(soundplan.rm_cue, d, cue)
    return _remix(d, {"ok": True, "ref": cue, "files": ["sound/plan.json", "out/mix.wav"]})


@op("cue-add", "mix", _plan_base)
def cue_add(d: Path, a: dict) -> dict:
    """A new sound on a shot: shot, action, query (what to look for), entry (optional: a sound picked from a search),
    and where: motion, line (+ word), at (seconds into the shot) or nothing (the whole shot)."""
    from filmcheck import soundplan
    shot = a.get("shot") or (a.get("ref") or [None])[0]
    if not shot or not (a.get("action") or "").strip() or not (a.get("query") or "").strip():
        raise EditError("cue-add: shot, action=… and query=…")
    if a.get("motion"):
        anchor = {"motion": a["motion"], "edge": a.get("edge") or "start", "offset_f": _num(a, "offset_f", int) or 0}
    elif a.get("line"):
        anchor = {"line": a["line"], **({"word": a["word"]} if a.get("word") else {}), "offset_f": _num(a, "offset_f", int) or 0}
    elif a.get("at") not in (None, ""):                 # seconds into the shot → the plan's fraction of the shot
        tm = _plan_call(soundplan.timing, d)
        frames = tm["frames"].get(shot.upper())
        if not frames:
            raise EditError(f"no shot {shot} in this film")
        anchor = {"shot_at": round(min(max(_num(a, "at") / (frames / tm["fps"]), 0.0), 0.999), 4)}
    else:
        anchor = {"span": "shot"}
    c = _plan_call(soundplan.add_cue, d, shot.upper(), a["action"].strip()[:80], anchor, a["query"].strip()[:120],
                   gain_db=_num(a, "gain_db"), by=a.get("by") or "user", entry=a.get("entry") or None)
    return _remix(d, {"ok": True, "ref": c["id"], "new": {"shot": c["shot"], "action": c["action"], "entry": c.get("entry"),
                                                          "state": c["state"]}, "files": ["sound/plan.json", "out/mix.wav"]})


@op("shot-set", "mix", _plan_base)
def shot_set(d: Path, a: dict) -> dict:
    """Turn the sound effects of shots on or off (shot=S2,S3 on=yes|no)."""
    from filmcheck import soundplan
    shots = [x.strip().upper() for x in (a.get("ref") or []) + str(a.get("shot") or "").split(",") if x.strip()]
    if not shots or a.get("on") not in ("yes", "no", "true", "false", "on", "off", ""):
        raise EditError("shot-set: shot=S2[,S3] on=yes|no")
    on = a.get("on") in ("yes", "true", "on")
    p = _plan_call(soundplan.set_shots, d, shots, on)
    return _remix(d, {"ok": True, "ref": ",".join(shots), "new": {"on": on, "off": p["off"]},
                      "files": ["sound/plan.json", "out/mix.wav"]})


def _snote_call(fn, *args, **kw):
    from filmcheck import soundnotes
    try:
        return fn(*args, **kw)
    except soundnotes.SoundNoteError as e:
        raise EditError(f"{e.code}: {e.message}") from None


@op("sound-note-add", "mix", _sound_notes_base)
def sound_note_add(d: Path, a: dict) -> dict:
    from filmcheck import soundnotes
    shot = a.get("shot") or (a.get("ref") or [None])[0]
    if not shot:
        raise EditError("sound-note-add: shot=<S2> and the text")
    n = _snote_call(soundnotes.add, d, shot, _note_text(a), a.get("by") or "owner")
    return {"ok": True, "ref": n["id"], "new": n["text"], "files": ["sound/notes.json"], "no_stale": True}


@op("sound-note-delete", "mix", _sound_notes_base)
def sound_note_delete(d: Path, a: dict) -> dict:
    from filmcheck import soundnotes
    shot = a.get("shot") or (a.get("ref") or [None])[0]
    if not shot or not a.get("note"):
        raise EditError("sound-note-delete: shot=<S2> note=<id>")
    _snote_call(soundnotes.delete, d, shot, a["note"])
    return {"ok": True, "ref": a["note"], "files": ["sound/notes.json"], "no_stale": True}


# ---------- camera (specs/039 US3) ----------
def _cam_notes_base(d: Path) -> str:
    from filmcheck import camnotes
    return camnotes.base(d)


def _cam_call(fn, *args, **kw):
    from filmcheck import camnotes, camsuggest
    try:
        return fn(*args, **kw)
    except camnotes.CamNoteError as e:
        raise EditError(f"{e.code}: {e.message}") from None
    except camsuggest.CameraError as e:
        raise EditError(str(e)) from None


def _cam_shot(a: dict, name: str) -> str:
    shot = a.get("shot") or (a.get("ref") or [None])[0]
    if not shot:
        raise EditError(f"{name}: shot=<S2>")
    return str(shot).strip().upper()


@op("camera-choose", "camera")
def camera_choose(d: Path, a: dict) -> dict:
    """Use one option of a shot: shot, n (1–3)."""
    from filmcheck import camsuggest
    shot = _cam_shot(a, "camera-choose")
    n = _num(a, "n", int)
    if n is None:
        raise EditError("camera-choose: n=<1–3>")
    old = ((camsuggest.load(d) or {}).get("shots", {}).get(shot) or {}).get("choice", {}).get("n")
    _cam_call(camsuggest.choose, d, shot, n, by=a.get("by") or "owner", source="user")
    return {"ok": True, "ref": shot, "old": old, "new": n, "files": ["camera/options.json", "film.json"]}


@op("camera-note-add", "camera", _cam_notes_base)
def camera_note_add(d: Path, a: dict) -> dict:
    """A pin on one option's still: shot, option, x, y (%), text."""
    from filmcheck import camnotes
    shot = _cam_shot(a, "camera-note-add")
    n = _cam_call(camnotes.add, d, shot, a.get("option") or a.get("n") or 1, _num(a, "x"), _num(a, "y"),
                  _note_text(a), by=a.get("by") or "owner")
    return {"ok": True, "ref": n["id"], "new": n["text"], "files": ["camera/notes.json"], "no_stale": True}


@op("camera-note-remove", "camera", _cam_notes_base)
def camera_note_remove(d: Path, a: dict) -> dict:
    from filmcheck import camnotes
    if not a.get("note"):
        raise EditError("camera-note-remove: note=<id>")
    _cam_call(camnotes.remove, d, a["note"])
    return {"ok": True, "ref": a["note"], "files": ["camera/notes.json"], "no_stale": True}


# ---------- publish (US5) ----------
@op("publish", "publish")
def publish_edit(d: Path, a: dict) -> dict:
    import re
    f = d / "publish" / "pack.json"
    try:
        pk = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise EditError(f"publish/pack.json cannot be read: {e}") from None
    old = {k: pk.get(k) for k in ("chosen", "summary", "hashtags")}
    if a.get("chosen"):
        if str(a["chosen"]) not in ("1", "2", "3"):
            raise EditError("chosen: 1, 2 or 3")
        pk["chosen"] = int(a["chosen"])
    desc = a.get("description")
    if desc is None and a.get("description_file"):
        try:
            desc = Path(a["description_file"]).read_text(encoding="utf-8")
        except OSError as e:
            raise EditError(f"the description file cannot be read: {e}") from None
    if desc is not None:
        desc = desc.strip()
        if not desc or len(desc) > 4000:
            raise EditError("the description: 1–4000 characters")
        pk["summary"] = desc
    if a.get("hashtags"):
        tags = [("#" + t.strip().lstrip("#")) for t in str(a["hashtags"]).split(",") if t.strip()]
        if not 3 <= len(tags) <= 5 or not all(re.fullmatch(r"#\w{1,29}", t) for t in tags):
            raise EditError("hashtags: 3–5 tags such as #science (letters and digits, at most 30 characters)")
        pk["hashtags"] = tags
    new = {k: pk.get(k) for k in ("chosen", "summary", "hashtags")}
    if new == old:
        raise EditError("nothing to change: chosen=…, a description or hashtags=…")
    write_atomic(f, json.dumps(pk, ensure_ascii=False, indent=1) + "\n")
    if no_run():
        return {"ref": "pack", "old": old, "new": new, "ok": True}
    code, txt = studio_cli("publish", str(d), "--no-draw", "--json")
    try:
        r = json.loads(txt.splitlines()[-1])
    except (ValueError, IndexError):
        return {"ref": "pack", "old": old, "new": new, "ok": False, "error": txt[-300:]}
    return {"ref": "pack", "old": old, "new": new, "ok": bool(r.get("pass")), "check": {"pass": r.get("pass"),
            "problems": (r.get("problems") or [])[:10]}}
