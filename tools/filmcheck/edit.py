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
