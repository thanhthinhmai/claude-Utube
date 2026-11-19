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


def op(name, point):
    def reg(fn):
        OPS[name] = {"point": point, "fn": fn}
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
    fp = points.fingerprint(d, point)
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
    stale = steps.impact(point) if point in steps.POINT_STEP else []
    res.update(ok=bool(out.get("ok", True)), code=0 if out.get("ok", True) else 1, ref=out.get("ref"),
               check=out.get("check"), files=out.get("files") or [], stale=stale, fingerprint=points.fingerprint(d, point),
               error=out.get("error"))
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


def voice_after(d: Path, ids=None) -> dict:
    """Make the voice of these lines again (all when None), stamp them and run the voice check."""
    if no_run():
        return {"ok": True, "check": {"skipped": True}}
    only = ["--only", ",".join(ids)] if ids else []
    code, txt = studio_cli("voice-make", str(d), *only)
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
    out = voice_after(d)
    out.update(ref="all lines", old=old, new={"voice": voice or old["voice"], "speed": speed if speed is not None else old["speed"]})
    return out


def voice_known(v: str) -> bool:
    """A Kokoro voice in the library's voices-v1.0.bin (a zip of .npy files); edge-tts names pass when they look right."""
    import zipfile
    if v.endswith("Neural"):
        return True
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
