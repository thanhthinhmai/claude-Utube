"""Jobs: one style-learning run or one film (data-model.md: Job)."""
import datetime as dt
import re
import secrets

from . import store
from .store import StudioError

KINDS = {"learn", "film"}
STORED = {"running", "waiting_review", "waiting_resume", "done", "failed", "stopped"}
FINAL = {"done", "failed", "stopped"}
INACTIVE_AFTER = 600          # s without any update while running → shown as inactive
LOG_KEEP, LOG_LINE = 50, 300
ID = re.compile(r"^j-\d{8}-\d{6}-[0-9a-f]{4}$")
RES = re.compile(r"^[a-z0-9-]{1,60}$")


def new_id(prefix: str) -> str:
    t = dt.datetime.fromtimestamp(store.clock(), dt.timezone.utc)
    return f"{prefix}-{t:%Y%m%d-%H%M%S}-{secrets.token_hex(2)}"


def path(job_id: str):
    if not ID.match(job_id or ""):
        raise StudioError("not_found", f"không có việc \"{job_id}\"", 404)
    return store.state_dir() / "jobs" / f"{job_id}.json"


def load(job_id: str) -> dict:
    j = store.read_json(path(job_id))
    if not j:
        raise StudioError("not_found", f"không có việc \"{job_id}\"", 404)
    return j


def _line(text: str) -> dict:
    return {"t": store.now_iso(), "line": str(text).replace("\n", " ")[:LOG_LINE]}


def create(kind: str, name: str, links: dict = None) -> dict:
    if kind not in KINDS:
        raise StudioError("invalid", "loại việc phải là learn hoặc film", 422)
    if not name or len(name) > 80:
        raise StudioError("invalid", "tên việc phải có 1–80 ký tự", 422)
    links = {k: v for k, v in (links or {}).items() if v}
    for k, v in links.items():
        if k not in ("set", "film", "style") or not RES.match(v):
            raise StudioError("invalid", f"liên kết {k} không hợp lệ", 422)
    t = store.now_iso()
    j = {"id": new_id("j"), "owner": "local", "kind": kind, "name": name, "status": "running",
         "step": "Bắt đầu", "progress": None, "started_at": t, "updated_at": t,
         "log": [_line("Bắt đầu việc")], "links": links, "error": None, "review_ids": []}
    store.write_json(path(j["id"]), j)
    return j


def update(job_id: str, fn) -> dict:
    with store.lock(job_id):
        j = load(job_id)
        fn(j)
        j["updated_at"] = store.now_iso()
        j["log"] = j["log"][-LOG_KEEP:]
        store.write_json(path(job_id), j)
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
        j["step"], j["progress"] = text, progress
        if j["status"] == "waiting_resume":
            j["status"] = "running"
        j["log"].append(_line(text if not progress else f"{text} ({progress['done']}/{progress['total']})"))
    return update(job_id, f)


def log(job_id: str, *lines: str) -> dict:
    return update(job_id, lambda j: j["log"].extend(_line(x) for x in lines if x is not None))


def heartbeat(job_id: str) -> dict:
    return update(job_id, lambda j: None)


def finish(job_id: str, status: str, error: str = None, links: dict = None) -> dict:
    assert status in FINAL

    def f(j):
        j["status"], j["error"] = status, error
        j["step"] = {"done": "Xong", "failed": "Lỗi", "stopped": "Đã dừng"}[status]
        j["links"].update({k: v for k, v in (links or {}).items() if v})
        j["log"].append(_line(error or j["step"]))
    return update(job_id, f)


def set_status(job_id: str, status: str, note: str = None) -> dict:
    assert status in STORED

    def f(j):
        if j["status"] not in FINAL:
            j["status"] = status
        if note:
            j["log"].append(_line(note))
    return update(job_id, f)


def all_jobs() -> list:
    out = []
    for p in (store.state_dir() / "jobs").glob("j-*.json"):
        j = store.read_json(p)
        if j:
            out.append(j)
    out.sort(key=lambda j: j["started_at"], reverse=True)
    return out


def shown_status(j: dict) -> str:
    """Stored status plus the ones computed when read: inactive (FR-005)."""
    if j["status"] == "running" and store.age_seconds(j["updated_at"]) > INACTIVE_AFTER:
        return "inactive"
    return j["status"]
