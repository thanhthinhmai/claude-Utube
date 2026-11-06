"""Review requests and decisions: first decision wins (data-model.md: Review, Decision)."""
import re

from . import jobs, resources, store
from .store import StudioError

KINDS = {"style-1": "lần 1", "style-2": "lần 2"}
VALUES = {"approve", "revise", "accept_anyway", "stop"}
LABEL = {"approve": "Đồng ý", "revise": "Yêu cầu sửa", "accept_anyway": "Chấp nhận dù chưa đạt", "stop": "Dừng"}
SOURCES = {"ui", "chat"}
ID = re.compile(r"^r-\d{8}-\d{6}-[0-9a-f]{4}$")
RESUME_AFTER = 60       # decided, but nobody waited for this long → the job waits to be resumed
MAX_SUMMARY = 200_000


def _paths(rid: str):
    if not ID.match(rid or ""):
        raise StudioError("not_found", f"không có yêu cầu duyệt \"{rid}\"", 404)
    d = store.state_dir() / "reviews"
    return d / f"{rid}.json", d / f"{rid}.decision.json"


def load(rid: str) -> dict:
    p, dp = _paths(rid)
    r = store.read_json(p)
    if not r:
        raise StudioError("not_found", f"không có yêu cầu duyệt \"{rid}\"", 404)
    r["decision"] = store.read_json(dp)
    return r


def create(job_id: str, kind: str, set_name: str, summary_md: str, final_round: bool = False) -> dict:
    job = jobs.load(job_id)
    if kind not in KINDS:
        raise StudioError("invalid", "loại duyệt phải là style-1 hoặc style-2", 422)
    if len(summary_md.encode()) > MAX_SUMMARY:
        raise StudioError("invalid", "bản tóm tắt quá dài (tối đa 200 KB)", 422)
    resources.check_name(set_name)
    compare = None
    if kind == "style-2":
        compare = store.read_json(resources.set_dir(set_name) / "proof" / "compare.json")
        if not compare:
            raise StudioError("invalid", f"chưa có references/{set_name}/proof/compare.json: chạy learn compare trước", 422)
        compare = {k: compare.get(k) for k in ("luma_diff", "sat_median_diff", "dark_diff_pp", "palette_matched",
                                                "palette_needed", "pass", "round", "ref", "ours",
                                                "ref_palette", "our_palette")}
    r = {"id": jobs.new_id("r"), "owner": "local", "job_id": job_id, "kind": kind, "created_at": store.now_iso(),
         "summary_md": summary_md, "set": set_name, "compare": compare,
         "final_round": bool(final_round and kind == "style-2"), "waiting": {"last_poll_at": None}}
    p, _ = _paths(r["id"])
    store.write_json(p, r)

    def f(j):
        if j["status"] in jobs.FINAL:
            raise StudioError("finished", "việc đã kết thúc", 409)
        j["status"] = "waiting_review"
        j["step"] = f"Chờ duyệt {KINDS[kind]}"
        j["review_ids"].append(r["id"])
        j["log"].append(jobs._line(f"Gửi yêu cầu duyệt {KINDS[kind]}"))
    jobs.update(job["id"], f)
    r["decision"] = None
    return r


def decide(rid: str, value: str, note: str = None, source: str = "ui") -> dict:
    r = load(rid)
    note = (note or "").strip()
    if value not in VALUES:
        raise StudioError("value_not_allowed", "quyết định không hợp lệ", 422)
    if source not in SOURCES:
        raise StudioError("invalid", "nguồn phải là ui hoặc chat", 422)
    if value in ("accept_anyway", "stop") and not (r["kind"] == "style-2" and r["final_round"]):
        raise StudioError("value_not_allowed", "chỉ chọn được khi đã hết vòng sửa ở lần duyệt 2", 422)
    if value == "revise" and len(note) < 3:
        raise StudioError("note_required", "hãy ghi góp ý (ít nhất 3 ký tự) khi yêu cầu sửa", 422)
    if len(note) > 4000:
        raise StudioError("invalid", "góp ý tối đa 4000 ký tự", 422)
    d = {"value": value, "note": note, "source": source, "at": store.now_iso()}
    _, dp = _paths(rid)
    if not store.create_exclusive(dp, d):
        raise StudioError("already_decided", "yêu cầu này đã được duyệt", 409)
    where = "giao diện" if source == "ui" else "khung chat"
    jobs.log(r["job_id"], f"Duyệt {KINDS[r['kind']]}: {LABEL[value]} (qua {where})" + (f": {note[:200]}" if note else ""))
    return d


def poll(rid: str):
    """One check by `review wait`: records that someone is waiting, returns the decision or None."""
    p, dp = _paths(rid)
    with store.lock(rid):
        r = store.read_json(p)
        if not r:
            raise StudioError("not_found", f"không có yêu cầu duyệt \"{rid}\"", 404)
        r["waiting"] = {"last_poll_at": store.now_iso()}
        store.write_json(p, r)
    return store.read_json(dp)


def resume(rid: str, d: dict) -> None:
    r = load(rid)
    jobs.set_status(r["job_id"], "running", f"Tiếp tục sau khi duyệt {KINDS[r['kind']]}: {LABEL[d['value']]}")


def all_reviews(status: str = None) -> list:
    out = []
    for p in (store.state_dir() / "reviews").glob("r-*.json"):
        if p.name.endswith(".decision.json"):
            continue
        r = store.read_json(p)
        if not r:
            continue
        r["decision"] = store.read_json(p.with_name(p.stem + ".decision.json"))
        if status == "pending" and r["decision"]:
            continue
        if status == "decided" and not r["decision"]:
            continue
        out.append(r)
    out.sort(key=lambda r: r["created_at"], reverse=True)
    return out


def job_view(j: dict) -> dict:
    """A job as shown: inactive when stale; waiting_resume when its last review is decided but nobody picked it up."""
    v = dict(j)
    v["status"] = jobs.shown_status(j)
    if j["status"] == "waiting_review" and j["review_ids"]:
        try:
            last = load(j["review_ids"][-1])
        except StudioError:
            return v
        if last["decision"] and store.age_seconds(last["waiting"].get("last_poll_at")) > RESUME_AFTER:
            v["status"] = "waiting_resume"
    return v
