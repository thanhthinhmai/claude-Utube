"""Review requests and decisions: first decision wins (data-model.md: Review, Decision)."""
import re

from . import jobs, resources, store
from .store import StudioError

# job log text is English (005); question and treatment are for online film jobs (007 FR-014)
KINDS = {"style-1": "review 1", "style-2": "review 2", "question": "question", "treatment": "treatment review"}
VALUES = {"approve", "revise", "accept_anyway", "stop"}
LABEL = {"approve": "Approve", "revise": "Request changes", "accept_anyway": "Accept anyway", "stop": "Stop"}   # = DECISION in web/app.js
SOURCES = {"ui", "chat"}
ID = re.compile(r"^r-\d{8}-\d{6}-[0-9a-f]{4}$")
RESUME_AFTER = 60       # decided, but nobody waited for this long → the job waits to be resumed
MAX_SUMMARY = 200_000


def check_id(rid: str) -> str:
    if not ID.match(rid or ""):
        raise StudioError("not_found", f"không có yêu cầu duyệt \"{rid}\"", 404)
    return rid


def load(rid: str, owner: str = None) -> dict:
    r = store.doc_get("review", check_id(rid))
    if not r or (owner and r.get("owner") != owner):
        raise StudioError("not_found", f"không có yêu cầu duyệt \"{rid}\"", 404)
    r["decision"] = _decision(rid)
    return r


def create(job_id: str, kind: str, set_name: str, summary_md: str, final_round: bool = False) -> dict:
    job = jobs.load(job_id)
    if kind not in KINDS:
        raise StudioError("invalid", "loại duyệt phải là " + ", ".join(sorted(KINDS)), 422)
    if len(summary_md.encode()) > MAX_SUMMARY:
        raise StudioError("invalid", "bản tóm tắt quá dài (tối đa 200 KB)", 422)
    if kind.startswith("style-") or set_name:         # question and treatment reviews have no reference set
        resources.check_name(set_name)
    compare = None
    if kind == "style-2":
        compare = store.read_json(resources.set_dir(set_name) / "proof" / "compare.json")
        if not compare:
            raise StudioError("invalid", f"chưa có references/{set_name}/proof/compare.json: chạy learn compare trước", 422)
        compare = {k: compare.get(k) for k in ("luma_diff", "sat_median_diff", "dark_diff_pp", "palette_matched",
                                                "palette_needed", "pass", "round", "ref", "ours",
                                                "ref_palette", "our_palette")}
    r = {"id": jobs.new_id("r"), "owner": job.get("owner", "local"), "job_id": job_id, "kind": kind, "created_at": store.now_iso(),
         "summary_md": summary_md, "set": set_name or None, "compare": compare,
         "final_round": bool(final_round and kind == "style-2"), "waiting": {"last_poll_at": None}}
    store.doc_put("review", r["id"], r)

    def f(j):
        if j["status"] in jobs.FINAL:
            raise StudioError("finished", "việc đã kết thúc", 409)
        j["status"] = "waiting_review"
        j["step"] = f"Waiting for {KINDS[kind]}"
        j["review_ids"].append(r["id"])
        j["log"].append(jobs._line(f"{KINDS[kind].capitalize()} requested"))
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
    if not store.doc_create("decision", rid, {**d, "owner": r.get("owner", "local")}):
        raise StudioError("already_decided", "yêu cầu này đã được duyệt", 409)
    where = "UI" if source == "ui" else "chat"
    jobs.log(r["job_id"], f"{KINDS[r['kind']].capitalize()}: {LABEL[value]} (via {where})" + (f": {note[:200]}" if note else ""))
    return d


def poll(rid: str):
    """One check by `review wait`: records that someone is waiting, returns the decision or None."""
    check_id(rid)
    with store.lock(rid):
        r = store.doc_get("review", rid)
        if not r:
            raise StudioError("not_found", f"không có yêu cầu duyệt \"{rid}\"", 404)
        r["waiting"] = {"last_poll_at": store.now_iso()}
        store.doc_put("review", rid, r)
    return _decision(rid)


def _decision(rid: str):
    d = store.doc_get("decision", rid)
    if d:
        d.pop("owner", None)
    return d


def resume(rid: str, d: dict) -> None:
    r = load(rid)
    jobs.set_status(r["job_id"], "running", f"Resumed after {KINDS[r['kind']]}: {LABEL[d['value']]}")


def all_reviews(status: str = None, owner: str = None) -> list:
    out = []
    for r in store.doc_list("review", owner):
        r["decision"] = _decision(r["id"])
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
