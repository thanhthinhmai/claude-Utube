"""Edits from the job page (specs/026, data-model "Action", research R12): a queue of actions per job, run one at a time
by `sh bin/studio edit … --json`. Locally (and in the desktop app) a thread of the web server runs them; online the
worker runs them in the job's container (tools/runner/worker.py). The page never writes a film file itself."""
import json
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from . import jobs, store
from .store import StudioError

OPS = {"script": ("script-para",), "cast": ("cast-approve", "cast-voice", "cast-save", "cast-note-add", "cast-note-edit", "cast-note-delete", "cast-view-toggle"), "animatic": ("animatic-fit-accept", "animatic-fit-skip", "animatic-fit-undo", "animatic-draft", "animatic-note-add", "animatic-note-delete"), "voice": ("voice-say", "voice-remake", "voice-tone", "voice-set", "voice-speaker"),
       "shots": ("shot", "shots-check", "except", "accept-style"), "mix": ("mix", "cue-set", "cue-rm", "cue-add", "shot-set", "sound-note-add", "sound-note-delete"), "publish": ("publish",)}
STATUS = ("queued", "running", "done", "failed", "invalid", "conflict", "busy")
BY_CODE = {0: "done", 1: "done", 2: "invalid", 4: "conflict", 5: "busy"}
PER_MINUTE = 30
TEXT_MAX = 4000
ROOT = Path(__file__).resolve().parents[3]
_queues: dict = {}
_qlock = threading.Lock()


def check_args(point: str, op: str, args: dict) -> dict:
    """Types and lengths (422 on a bad value); the meaning is checked by `edit` (exit code 2)."""
    if point not in OPS or op not in OPS[point]:
        raise StudioError("invalid", f"\"{op}\" is not an edit of the {point} step", 422)
    if not isinstance(args, dict) or len(args) > 12:
        raise StudioError("invalid", "args: an object of at most 12 values", 422)
    clean = {}
    for k, v in args.items():
        if not isinstance(k, str) or not k.replace("_", "").isalnum() or len(k) > 30:
            raise StudioError("invalid", f"args: bad name {k!r}", 422)
        if isinstance(v, bool) or v is None:
            v = "yes" if v else ""
        if isinstance(v, (int, float)):
            v = str(v)
        if isinstance(v, list):
            v = ",".join(str(x) for x in v)
        if not isinstance(v, str) or len(v) > TEXT_MAX:
            raise StudioError("invalid", f"args.{k}: text of at most {TEXT_MAX} characters", 422)
        clean[k] = v
    return clean


def create(job: dict, point: str, op: str, args: dict, base: str, by: str) -> dict:
    if job.get("kind") != "film":
        raise StudioError("invalid", "only a film job has edits", 422)
    if job["status"] in jobs.FINAL:
        raise StudioError("finished", "the job has ended", 409)
    args = check_args(point, op, args or {})
    if base is not None and (not isinstance(base, str) or len(base) != 16):
        raise StudioError("invalid", "base: the 16-character fingerprint shown", 422)
    recent = [a for a in store.doc_list("action", job.get("owner")) if a["job_id"] == job["id"]
              and store.age_seconds(a["created_at"]) < 60]
    if len(recent) >= PER_MINUTE:
        raise StudioError("too_many", f"at most {PER_MINUTE} edits a minute for one job", 429)
    if op == "animatic-draft":                        # one rebuild waits at a time: a new one joins it (FR-016)
        for q in queued(job["id"]):
            if q["op"] == "animatic-draft":
                old, new = q["args"].get("shots", ""), args.get("shots", "")
                both = "" if not old or not new else ",".join(dict.fromkeys(old.split(",") + new.split(",")))

                def join(x):
                    x["args"]["shots"] = both
                return store.doc_update("action", q["id"], join) or q
    a = {"id": jobs.new_id("a"), "job_id": job["id"], "owner": job.get("owner", "local"), "point": point, "op": op,
         "args": args, "base": base, "by": by or job.get("owner") or "local", "status": "queued", "result": None,
         "created_at": store.now_iso(), "started_at": None, "ended_at": None}
    store.doc_put("action", a["id"], a)
    jobs.log(job["id"], f"Edit {op} {args.get('ref') or args.get('para') or args.get('line') or args.get('shot') or ''}: queued".rstrip())
    if store.mode() != "online":
        start_local(job["id"])
    return a


def load(aid: str, job_id: str) -> dict:
    a = store.doc_get("action", aid) if aid.startswith("a-") else None
    if not a or a["job_id"] != job_id:
        raise StudioError("not_found", f"no edit \"{aid}\"", 404)
    return a


def queued(job_id: str) -> list:
    return sorted((a for a in store.doc_list("action") if a["job_id"] == job_id and a["status"] == "queued"),
                  key=lambda a: a["created_at"] + a["id"])


def command(a: dict, film: str, tmpdir: str, studio: str = None, seen: str = None) -> list:
    """`sh bin/studio edit <film> <op> <ref…> key=value … --base F --by X --source ui --json`; long text goes in a file
    written to `tmpdir` (`seen` is that folder as the command sees it, inside a job container online)."""
    args = dict(a["args"])
    seen = seen or tmpdir
    cmd = ["sh", studio or str(ROOT / "bin" / "studio"), "edit", film, a["op"]]
    for k in ("ref", "para", "line", "shot", "rule", "character"):
        if args.get(k):
            cmd += [x for x in args.pop(k).split(",") if x]
    opts = []                               # options after every key=value (argparse stops the list at an option)
    for k in ("text", "description"):
        if k in args:
            f = Path(tmpdir) / f"{k}.txt"
            f.write_text(args.pop(k), encoding="utf-8")
            if k == "text":
                opts += ["--text-file", f"{seen}/{k}.txt"]
            else:
                cmd.append(f"description-file={seen}/{k}.txt")
    for k in ("say", "reason", "confirm"):
        if k in args:
            opts += [f"--{k}", args.pop(k)]
    cmd += [f"{k.replace('_', '-')}={v}" for k, v in args.items()] + opts
    if a.get("base"):
        cmd += ["--base", a["base"]]
    return cmd + ["--by", a["by"], "--source", "ui", "--json"]


def finish(a: dict, code: int, out: str) -> dict:
    try:
        res = json.loads(out.strip().splitlines()[-1]) if out.strip() else None
    except (ValueError, IndexError):
        res = None
    status = BY_CODE.get(code, "failed")

    def f(x):
        x.update(status=status, result=res or {"code": code, "error": out.strip()[-500:] or "no output"},
                 ended_at=store.now_iso())
    a = store.doc_update("action", a["id"], f) or a
    r = a["result"] or {}
    if status == "done" and r.get("rebuild"):          # specs/035: a fit change builds the changed shots again
        try:
            create(jobs.load(a["job_id"]), "animatic", "animatic-draft", {"shots": ",".join(r["rebuild"])}, None, a["by"])
        except StudioError as e:
            jobs.log(a["job_id"], f"Draft rebuild not queued: {e}")
    what = f"Edit {a['op']} {r.get('ref') or ''}".rstrip()
    if status == "done":
        chk = r.get("check") or {}
        extra = f" · score {chk['score']}/10" if "score" in chk else ""
        jobs.log(a["job_id"], f"{what}: {'saved' if code == 0 else 'saved, check does not pass'}{extra}"
                 + (f" · run again: {', '.join(r['stale'])}" if r.get("stale") else ""))
    else:
        jobs.log(a["job_id"], f"{what}: {status} — {(r.get('error') or '')[:200]}")
    return a


def run_one(a: dict, film: str, env: dict = None) -> dict:
    store.doc_update("action", a["id"], lambda x: x.update(status="running", started_at=store.now_iso()))
    with tempfile.TemporaryDirectory(prefix="cu-edit-") as tmp:
        cmd = command(a, film, tmp)
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), env={**os.environ, **(env or {})},
                           timeout=3600)
    return finish(a, p.returncode, p.stdout or p.stderr)


def _runner(job_id: str) -> None:
    from . import donesofar
    try:
        while True:
            todo = queued(job_id)
            if not todo:
                return
            j = jobs.load(job_id)
            d = donesofar.film_dir(j)
            if d is None:
                for a in todo:
                    finish(a, 2, json.dumps({"code": 2, "error": "the film folder of this job is gone"}))
                return
            step = j.get("step") if j["status"] == "running" else ""
            run_one(todo[0], str(d), {"STUDIO_JOB_STEP": step or "", "STUDIO_ROOT": str(ROOT)})
    finally:
        with _qlock:
            _queues.pop(job_id, None)
        if queued(job_id):                 # an edit added while the thread was ending
            start_local(job_id)


def start_local(job_id: str) -> None:
    with _qlock:
        t = _queues.get(job_id)
        if t and t.is_alive():
            return
        t = threading.Thread(target=_runner, args=(job_id,), daemon=True, name=f"edits-{job_id}")
        _queues[job_id] = t
    t.start()


def wait_idle(job_id: str, timeout: float = 60) -> bool:
    """Tests: until the job's queue is empty and its thread ended."""
    end = time.time() + timeout
    while time.time() < end:
        with _qlock:
            t = _queues.get(job_id)
        if not (t and t.is_alive()) and not queued(job_id):
            return True
        time.sleep(0.05)
    return False
