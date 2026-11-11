"""Jobs: one style-learning run or one film (data-model.md: Job)."""
import datetime as dt
import re
import secrets
import time

from . import store
from .store import StudioError

KINDS = {"learn", "film"}
STORED = {"queued", "running", "waiting_review", "waiting_resume", "done", "failed", "stopped"}
FINAL = {"done", "failed", "stopped"}
INACTIVE_AFTER = 600          # s without any update while running → shown as inactive
LOG_KEEP, LOG_LINE = 50, 300
ID = re.compile(r"^j-\d{8}-\d{6}-[0-9a-f]{4}$")
RES = re.compile(r"^[a-z0-9-]{1,60}$")


def new_id(prefix: str) -> str:
    t = dt.datetime.fromtimestamp(store.clock(), dt.timezone.utc)
    return f"{prefix}-{t:%Y%m%d-%H%M%S}-{secrets.token_hex(2)}"


def check_id(job_id: str) -> str:
    if not ID.match(job_id or ""):
        raise StudioError("not_found", f"không có việc \"{job_id}\"", 404)
    return job_id


def load(job_id: str, owner: str = None) -> dict:
    """The job; online, `owner` limits it to one customer (another customer's job is simply not found)."""
    j = store.doc_get("job", check_id(job_id))
    if not j or (owner and j.get("owner") != owner):
        raise StudioError("not_found", f"không có việc \"{job_id}\"", 404)
    return j


def _line(text: str) -> dict:
    return {"t": store.now_iso(), "line": str(text).replace("\n", " ")[:LOG_LINE]}


def build(kind: str, name: str, links: dict = None, owner: str = "local", status: str = "running",
          extra: dict = None) -> dict:
    """A new job, not saved yet. Online jobs start `queued` with the order fields of data-model.md (Job)."""
    if kind not in KINDS:
        raise StudioError("invalid", "loại việc phải là learn hoặc film", 422)
    if not name or len(name) > 80:
        raise StudioError("invalid", "tên việc phải có 1–80 ký tự", 422)
    links = {k: v for k, v in (links or {}).items() if v}
    for k, v in links.items():
        if k not in ("set", "film", "style") or not RES.match(v):
            raise StudioError("invalid", f"liên kết {k} không hợp lệ", 422)
    t = store.now_iso()
    assert status in ("running", "queued")
    j = {"id": new_id("j"), "owner": owner, "kind": kind, "name": name, "status": status,
         "step": "Starting", "progress": None, "started_at": t, "updated_at": t,
         "log": [_line("Job started")], "links": links, "error": None, "review_ids": []}
    if status == "queued":
        j.update(step="Queued", input=None, charged=False, cost_usd=0.0, queued_at=t, queue_seq=time.time_ns(), run_count=0,
                 agent_session=None, failure_kind=None, restarts=0, qa=None)
        j["log"] = [_line("Queued")]
    j.update(extra or {})
    return j


def create(kind: str, name: str, links: dict = None, owner: str = "local", status: str = "running",
           extra: dict = None) -> dict:
    j = build(kind, name, links, owner, status, extra)
    store.doc_put("job", j["id"], j)
    return j


def update(job_id: str, fn) -> dict:
    check_id(job_id)

    def f(j):
        fn(j)
        j["updated_at"] = store.now_iso()
        j["log"] = j["log"][-LOG_KEEP:]
    j = store.doc_update("job", job_id, f)
    if j is None:
        raise StudioError("not_found", f"không có việc \"{job_id}\"", 404)
    return j


def parse_progress(text: str):
    m = re.fullmatch(r"(\d+)/(\d+)", text or "")
    if not m or int(m.group(2)) < 1 or int(m.group(1)) > int(m.group(2)):
        raise StudioError("invalid", "tiến độ phải có dạng done/total với 0 ≤ done ≤ total, total ≥ 1", 422)
    return {"done": int(m.group(1)), "total": int(m.group(2))}


def step(job_id: str, text: str, progress: dict = None) -> dict:
    if not text or len(text) > 120:
        raise StudioError("invalid", "bước phải có 1–120 ký tự", 422)

    def f(j):
        if j["status"] in FINAL:
            raise StudioError("finished", "việc đã kết thúc", 409)
        same = j["step"] == text and j["progress"] == progress     # e.g. `job step X` then `job run --step X`
        j["step"], j["progress"] = text, progress
        if j["status"] == "waiting_resume":
            j["status"] = "running"
        if not same:
            j["log"].append(_line(text if not progress else f"{text} ({progress['done']}/{progress['total']})"))
    return update(job_id, f)


def publish_cut(job_id: str, reason: str) -> bool:
    """A film job stopped during its Publish step keeps its film (specs/011 R7): note why, change nothing else.
    True when the job was in that step."""
    got = []

    def f(j):
        if j.get("kind") == "film" and j["status"] not in FINAL and j.get("step") == "Publish":
            if not j.get("publish_cut"):
                j["publish_cut"] = reason
                j["log"].append(_line("Publish step stopped: " + reason))
            got.append(True)
    try:
        update(job_id, f)
    except StudioError:
        return False
    return bool(got)


def log(job_id: str, *lines: str) -> dict:
    return update(job_id, lambda j: j["log"].extend(_line(x) for x in lines if x is not None))


def heartbeat(job_id: str) -> dict:
    return update(job_id, lambda j: None)


def finish(job_id: str, status: str, error: str = None, links: dict = None, failure_kind: str = None,
           refund: bool = False) -> dict:
    """Final state. Online, a failed job records who caused it (spec FR-006a): `studio` or `customer`;
    `refund` gives the credit back in the same write."""
    assert status in FINAL

    def f(j):
        if "charged" in j and j["status"] in FINAL:        # online jobs end once (local keeps phase-1 behaviour)
            raise StudioError("finished", "việc đã kết thúc", 409)
        j["status"], j["error"] = status, error
        if "failure_kind" in j and status == "failed":
            j["failure_kind"] = failure_kind or "studio"
        j["step"] = {"done": "Done", "failed": "Failed", "stopped": "Stopped"}[status]
        j["links"].update({k: v for k, v in (links or {}).items() if v})
        j["log"].append(_line(error or j["step"]))
        if refund and j.get("charged"):
            j["charged"] = False
            j["log"].append(_line("Credit refunded"))
    return update(job_id, f)


def set_status(job_id: str, status: str, note: str = None) -> dict:
    assert status in STORED

    def f(j):
        if j["status"] not in FINAL:
            j["status"] = status
        if note:
            j["log"].append(_line(note))
    return update(job_id, f)


def all_jobs(owner: str = None) -> list:
    out = store.doc_list("job", owner)
    out.sort(key=lambda j: j["started_at"], reverse=True)
    return out


def shown_status(j: dict) -> str:
    """Stored status plus the ones computed when read: inactive (FR-005)."""
    if j["status"] == "running" and store.age_seconds(j["updated_at"]) > INACTIVE_AFTER:
        return "inactive"
    return j["status"]
