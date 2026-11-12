"""QC tier results, source fingerprints, shot exceptions and the render gate (specs/020 FR-009, FR-015, FR-021;
research R7, R10; contracts/checks.md). Results live in checks.json → tiers.<tier>; exceptions in qc-exceptions.json."""
import hashlib
import json
import time
from pathlib import Path

from filmcheck import report

TIERS = ("voice", "plan", "shots", "render", "final")
EXCEPTABLE = ("flat", "dark", "blown", "still", "shot_long", "text_over_subtitle")
SKIP_DIRS = {"out", "stills", "publish", ".check", "node_modules"}          # same as tools/render/lib.mjs
SKIP_SUFFIX = (".mp4", ".log")
SKIP_NAMES = {"checks.json", "CHECKS.md", "qc-exceptions.json"}
EXC_FILE = "qc-exceptions.json"
REASON_MAX = 200


class TierError(Exception):
    """Bad input to a tier command (exit code 2)."""


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _files(d: Path, part: str) -> list:
    if part == "voice":
        out = [d / "lines.json"] if (d / "lines.json").is_file() else []
        v = d / "voices"
        return out + (sorted(p for p in v.rglob("*") if p.is_file()) if v.is_dir() else [])
    out = []
    for p in sorted(d.rglob("*")):
        rel = p.relative_to(d)
        if rel.parts[0] in SKIP_DIRS or not p.is_file():
            continue
        if p.name.endswith(SKIP_SUFFIX) or p.name in SKIP_NAMES:
            continue
        out.append(p)
    return out


def fingerprint(film_dir: Path, part: str = "all") -> str:
    """SHA-256 (16 hex) over the film's source files: sorted relative path + bytes (data-model "Tier result")."""
    d = Path(film_dir)
    h = hashlib.sha256()
    for p in sorted(_files(d, part), key=lambda p: p.relative_to(d).as_posix()):
        h.update(p.relative_to(d).as_posix().encode() + b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()[:16]


def result(tier: str, issues: list, measures: dict, skipped: list, seconds: float, fp: str, **extra) -> dict:
    for i in issues:
        i["tier"] = tier
    r = {"pass": not any(i["severity"] == "block" and not i.get("excepted") for i in issues), "fingerprint": fp,
         "at": now(), "issues": issues, "measures": measures, "skipped": skipped, "seconds": round(seconds, 2)}
    r.update(extra)
    return r


def save_tier(film_dir: Path, tier: str, res: dict) -> dict:
    def put(x):
        x.setdefault("tiers", {})
        old = x["tiers"].get(tier) or {}
        if tier == "shots" and "style_accept" not in res:      # a new run keeps the reason only for the same source
            res["style_accept"] = old.get("style_accept") if old.get("fingerprint") == res.get("fingerprint") else None
        x["tiers"][tier] = res
    report.update(film_dir, put)
    return res


def load_tier(film_dir: Path, tier: str):
    return (report.load(film_dir).get("tiers") or {}).get(tier)


# ---------- exceptions (FR-015) ----------
def load_exceptions(film_dir: Path) -> list:
    try:
        data = json.loads((Path(film_dir) / EXC_FILE).read_text(encoding="utf-8"))
        return [e for e in data if isinstance(e, dict)] if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def shot_ids(film_dir: Path):
    try:
        inp = json.loads((Path(film_dir) / ".check" / "plan-input.json").read_text(encoding="utf-8"))
        return {s["id"] for s in inp.get("shots") or []}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def add_exception(film_dir: Path, shot: str, rule: str, reason: str) -> dict:
    reason = (reason or "").strip()
    if rule not in EXCEPTABLE:
        raise TierError(f"rule \"{rule}\" cannot be excepted; only {', '.join(EXCEPTABLE)}")
    if not reason:
        raise TierError("an exception needs a reason (--reason \"…\")")
    if len(reason) > REASON_MAX:
        raise TierError(f"the reason is {len(reason)} characters; at most {REASON_MAX}")
    ids = shot_ids(film_dir)
    if ids is None:
        raise TierError("no shot list yet: run sh bin/studio qc plan <film> first")
    if shot not in ids:
        raise TierError(f"no shot \"{shot}\" in the film's shot list (window.SHOTS)")
    exc = [e for e in load_exceptions(film_dir) if not (e.get("shot") == shot and e.get("rule") == rule)]
    e = {"shot": shot, "rule": rule, "reason": reason, "at": now()}
    exc.append(e)
    report._write(Path(film_dir) / EXC_FILE, json.dumps(exc, ensure_ascii=False, indent=1))
    return e


def remove_exception(film_dir: Path, shot: str, rule: str) -> bool:
    exc = load_exceptions(film_dir)
    left = [e for e in exc if not (e.get("shot") == shot and e.get("rule") == rule)]
    if len(left) == len(exc):
        return False
    report._write(Path(film_dir) / EXC_FILE, json.dumps(left, ensure_ascii=False, indent=1))
    return True


def apply_exceptions(issues: list, exceptions: list) -> list:
    by = {(e.get("shot"), e.get("rule")): e for e in exceptions}
    for i in issues:
        e = by.get((i.get("ref"), i.get("rule"))) if i.get("rule") in EXCEPTABLE else None
        i["excepted"] = {"reason": e["reason"], "at": e.get("at")} if e else None
    return issues


def recompute(film_dir: Path) -> dict:
    """After `qc except`: the plan and shots results again from their stored issues (no new pictures)."""
    exc = load_exceptions(film_dir)

    def fix(x):
        for t in ("plan", "shots"):
            r = (x.get("tiers") or {}).get(t)
            if r:
                apply_exceptions(r["issues"], exc)
                r["pass"] = not any(i["severity"] == "block" and not i.get("excepted") for i in r["issues"])
                r["exceptions"] = exc
    return report.update(film_dir, fix)


# ---------- render gate (contracts/checks.md) ----------
def gate(film_dir: Path) -> list:
    """[] when the film may be rendered; else one line per reason, each with the command to run."""
    d = Path(film_dir)
    name = d.name
    tiers = report.load(d).get("tiers") or {}
    fp = fingerprint(d)
    why = []
    plan = tiers.get("plan")
    if not plan or plan.get("fingerprint") != fp:
        why.append(f"the plan check has not run on the current film (run: sh bin/studio qc plan {name})")
    elif not plan["pass"]:
        n = sum(1 for i in plan["issues"] if i["severity"] == "block" and not i.get("excepted"))
        why.append(f"the plan check has {n} open problem(s) (run: sh bin/studio qc plan {name})")
    shots = tiers.get("shots")
    if not shots or shots.get("fingerprint") != fp:
        why.append(f"the shot check has not run on the current film (run: sh bin/studio qc shots {name})")
    else:
        n = sum(1 for i in shots["issues"] if i["severity"] == "block" and not i.get("excepted"))
        if n:
            why.append(f"the shot check has {n} open frame problem(s) (run: sh bin/studio qc shots {name}, "
                       f"or mark a deliberate shot: sh bin/studio qc except {name} <shot> <rule> --reason \"…\")")
        w = sum(1 for i in shots["issues"] if i["severity"] == "warn")
        if w and not ((shots.get("style_accept") or {}).get("reason")):
            why.append(f"{w} style warning(s) are open (run: sh bin/studio qc accept-style {name} --reason \"…\")")
    return why


def record_skip(film_dir: Path, reason: str) -> None:
    def put(x):
        x.setdefault("tiers", {})
        r = x["tiers"].get("render") or {}
        r["skipped_checks"] = {"reason": reason, "at": now(), "fingerprint": fingerprint(film_dir)}
        x["tiers"]["render"] = r
    report.update(film_dir, put)
