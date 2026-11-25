"""Review points of a film (specs/026, data-model "Point", "Film reviews"): which points are on, the fingerprint of
each point's files, approvals in checks.json → reviews, and the gates of voice make and render. Standard library only."""
import hashlib
import json
import time
from pathlib import Path

from filmcheck import report, tiers

POINTS = ("script", "cast", "voice", "shots", "mix", "publish")
DEFAULT_ON = ["script", "shots"]
AE_ON = ("cast",)                       # on by default for After Effects films unless turned off (specs/034)
STEP = {"script": "Script", "cast": "Cast", "voice": "Voice", "shots": "Shots", "mix": "Mix", "publish": "Publish"}
LOCKED = {"approved", "waiting"}            # a point in these states cannot be turned on or off (data-model)


class PointError(Exception):
    """Bad input (exit code 2)."""


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def check_point(p: str) -> str:
    if p not in POINTS:
        raise PointError(f"unknown review point \"{p}\" (one of {', '.join(POINTS)})")
    return p


def parse_list(text) -> list:
    """'script,shots' or ['script','shots'] or 'none' → ordered list of points."""
    items = text if isinstance(text, (list, tuple)) else str(text or "").replace(" ", "").split(",")
    items = [x for x in items if x and x != "none"]
    for x in items:
        check_point(x)
    return [p for p in POINTS if p in items]


# ---------- fingerprints by part (research R2) ----------
def _hash(d: Path, files: list) -> str:
    h = hashlib.sha256()
    for p in sorted((f for f in files if f.is_file()), key=lambda f: f.relative_to(d).as_posix()):
        h.update(p.relative_to(d).as_posix().encode() + b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()[:16]


def fingerprint(film_dir: Path, point: str) -> str:
    d = Path(film_dir)
    check_point(point)
    if point == "voice":
        return tiers.fingerprint(d, "voice")
    if point == "shots":
        return tiers.fingerprint(d)
    if point == "cast":
        from filmcheck import cast
        return cast.fingerprint(d) if cast.exists(d) else ""
    files = {"script": ["SCRIPT.md", "SOURCES.md"], "mix": ["mix.json", "out/mix.wav"],
             "publish": ["publish/pack.json"]}[point]
    return _hash(d, [d / f for f in files])


# ---------- state ----------
def is_ae(film_dir: Path) -> bool:
    from ae import film as filmdoc
    return filmdoc.engine(film_dir) == "ae"


def _with_ae(film_dir: Path, on: list, off: list) -> list:
    """AE films have the cast point on unless it was turned off for the film (FR-002)."""
    if is_ae(film_dir):
        on = on + [p for p in AE_ON if p not in on and p not in off]
    return [p for p in POINTS if p in on]


def load(film_dir: Path) -> dict:
    r = report.load(Path(film_dir)).get("reviews") or {}
    on = r.get("on")
    off = list(r.get("off") or [])
    return {"on": _with_ae(Path(film_dir), list(DEFAULT_ON) if on is None else list(on), off), "off": off,
            "from": r.get("from") or ("studio default" if on is None else None),
            "approved": dict(r.get("approved") or {}), "skipped": dict(r.get("skipped") or {}),
            "rejected": dict(r.get("rejected") or {})}


def _save(film_dir: Path, fn) -> dict:
    def put(x):
        cur = x.get("reviews") or {}
        rv = {"on": cur.get("on"), "off": list(cur.get("off") or []), "from": cur.get("from"), "approved": dict(cur.get("approved") or {}),
              "skipped": dict(cur.get("skipped") or {}), "rejected": dict(cur.get("rejected") or {})}
        if rv["on"] is None:
            rv["on"], rv["from"] = list(DEFAULT_ON), "studio default"
        fn(rv)
        x["reviews"] = rv
    return report.update(Path(film_dir), put)["reviews"]


def narrated(film_dir: Path) -> bool:
    d = Path(film_dir)
    if (report.load(d).get("script") or {}).get("verdict") == "skipped":
        return False
    return (d / "SCRIPT.md").is_file() or (d / "lines.json").is_file()


def reached(film_dir: Path, point: str) -> bool:
    """The point's work exists, so it can be reviewed."""
    d = Path(film_dir)
    return {"script": (d / "SCRIPT.md").is_file(),
            "voice": (d / "voices").is_dir() and any((d / "voices").glob("*.wav")),
            "shots": tiers.load_tier(d, "shots") is not None,
            "mix": (d / "out" / "mix.wav").is_file(),
            "publish": (d / "publish" / "pack.json").is_file(),
            "cast": _cast_reached(d)}[point]


def _cast_reached(d: Path) -> bool:
    from filmcheck import cast
    try:
        return cast.exists(d) and bool(cast.load(d)["characters"])
    except cast.CastError:
        return True             # a broken cast.json must be fixed, not skipped


def cast_skip_reason(film_dir: Path):
    """Why the cast point does not apply: not an AE film, or a film without characters."""
    d = Path(film_dir)
    if not is_ae(d):
        return "not an After Effects film"
    from filmcheck import cast
    try:
        if cast.exists(d) and not cast.load(d)["characters"]:
            return "no characters"
    except cast.CastError:
        return None
    return None


def state(film_dir: Path, point: str, pending: bool = False) -> str:
    """off · skipped · not_reached · ready (work exists, not approved) · waiting · approved · stale · rejected."""
    d = Path(film_dir)
    rv = load(d)
    if point in ("script", "voice") and not narrated(d):
        return "skipped"
    if point == "cast" and cast_skip_reason(d):
        return "skipped"
    if point not in rv["on"]:
        return "off"
    if point == "cast" and not pending and reached(d, point):
        from filmcheck import cast
        try:
            if cast.all_approved(d):
                return "approved"                   # every character approved with its current pictures
        except cast.CastError:
            return "ready"
    a = rv["approved"].get(point)
    if pending:
        return "waiting"
    if a:
        return "approved" if a.get("fingerprint") == fingerprint(d, point) else "stale"
    if rv["rejected"].get(point):
        return "rejected"
    return "ready" if reached(d, point) else "not_reached"


def status(film_dir: Path, pending: set = frozenset()) -> dict:
    d = Path(film_dir)
    rv = load(d)
    out = {}
    for p in POINTS:
        a = rv["approved"].get(p) or {}
        out[p] = {"on": p in rv["on"], "state": state(d, p, p in pending), "fingerprint": fingerprint(d, p),
                  "approved_at": a.get("at"), "by": a.get("by"), "source": a.get("source")}
    return out


def set_on(film_dir: Path, points, origin: str = None, pending: set = frozenset()) -> list:
    """Turn points on or off for this film; a point that is approved (still valid) or waiting cannot change."""
    d = Path(film_dir)
    want = parse_list(points)
    cur = load(d)["on"]
    for p in POINTS:
        if (p in want) != (p in cur) and state(d, p, p in pending) in LOCKED:
            raise PointError(f"the {p} review is {state(d, p, p in pending)}; it cannot be turned "
                             + ("off" if p in cur else "on") + " now")

    def f(rv):
        rv["on"] = want
        rv["off"] = [p for p in AE_ON if p not in want] if is_ae(d) else list(rv.get("off") or [])
        if origin:
            rv["from"] = origin
    return _save(d, f)["on"]


# ---------- checks that must pass to approve (research R3) ----------
def checks_pass(film_dir: Path, point: str) -> list:
    d = Path(film_dir)
    check_point(point)
    if point == "script":
        from filmcheck import script
        try:
            r = script.check(d, customer_round=True)
        except script.ScriptError as e:
            return [str(e)]
        if r["pass"]:
            return []
        failed = [k for k, ok in r["hard"].items() if not ok]
        return [f"the script check does not pass ({r['score']}/10" + (f"; failed: {', '.join(failed)}" if failed else "") + ")"]
    if point == "voice":
        t = tiers.load_tier(d, "voice")
        if not t or t.get("fingerprint") != tiers.fingerprint(d, "voice"):
            return ["the voice check has not run on the current voice (run: sh bin/studio qc voice <film>)"]
        n = sum(1 for i in t["issues"] if i["severity"] == "block" and not i.get("excepted"))
        return [f"the voice check has {n} open problem(s)"] if not t["pass"] else []
    if point == "shots":
        why = tiers.gate(d)
        return why
    if point == "cast":
        from filmcheck import cast
        try:
            doc = cast.load(d)
        except cast.CastError as e:
            return [e.message]
        bad = cast.validate(doc)
        if bad:
            return [f"cast/cast.json: {bad[0][2]}" + (f" ({bad[0][0]})" if bad[0][0] else "")]
        notes = cast.open_notes(d)
        why = [f"{c['id']}: no cast sheet yet" for c in doc["characters"] if not cast.has_sheet(d, c["id"])]
        why += [f"{cid}: {n} open note(s)" for cid, n in notes.items() if n]
        return why
    if point == "mix":
        mix = d / "out" / "mix.wav"
        if not mix.is_file():
            return ["there is no mix yet (out/mix.wav)"]
        newer = [p for p in [d / "mix.json", d / "narration.json"] + sorted((d / "voices").glob("*.wav"))
                 if p.is_file() and p.stat().st_mtime > mix.stat().st_mtime]
        return [f"the mix is older than {newer[0].relative_to(d).as_posix()}: mix again"] if newer else []
    from filmcheck import publish
    try:
        r = publish.check(d, publish.read_pack(d))
    except publish.PublishError as e:
        return [str(e)]
    return [f"the publish pack has {len(r['problems'])} problem(s): {r['problems'][0]}"] if r["problems"] else []


def approve(film_dir: Path, point: str, base: str = None, source: str = "chat", by: str = "local",
            review_id: str = None) -> tuple:
    """(code, reasons): 0 approved · 1 checks do not pass · 4 base is not the current fingerprint."""
    d = Path(film_dir)
    check_point(point)
    if source not in ("ui", "chat", "api"):
        raise PointError("source: ui, chat or api")
    fp = fingerprint(d, point)
    if base is not None and base != fp:
        return 4, [f"the {point} changed since it was shown (now {fp}, shown {base}): reload"]
    why = checks_pass(d, point)
    if why:
        return 1, why
    if point == "cast":           # approving the point approves every character ("Approve cast", FR US1-3)
        from filmcheck import cast
        doc = cast.load(d)
        why = cast.approve(d, [c["id"] for c in doc["characters"]], "chat" if source == "chat" else "ui", by)
        if why:
            return 1, why

    def f(rv):
        rv["approved"][point] = {"fingerprint": fp, "at": now(), "by": by or "local", "source": source,
                                 "review_id": review_id}
        rv["rejected"].pop(point, None)
    _save(d, f)
    return 0, []


def reject(film_dir: Path, point: str, note: str, by: str = "local") -> None:
    def f(rv):
        rv["rejected"][point] = {"note": note, "at": now(), "by": by}
        rv["approved"].pop(point, None)
    _save(Path(film_dir), f)


def skip(film_dir: Path, point: str, reason: str) -> None:
    if not (reason or "").strip():
        raise PointError("a reason is needed")

    def f(rv):
        rv["skipped"][point] = {"reason": reason.strip(), "at": now(), "fingerprint": fingerprint(Path(film_dir), point)}
    _save(Path(film_dir), f)


# ---------- gates (research R5) ----------
def gate(film_dir: Path, point: str) -> list:
    """[] when the step after this point may run; else the reasons, each with the command to run."""
    d = Path(film_dir)
    st = state(d, point)
    if st in ("off", "skipped", "approved", "not_reached"):      # not_reached: nothing to review (no SCRIPT.md, …)
        return []
    sk = load(d)["skipped"].get(point)
    if sk and sk.get("fingerprint") == fingerprint(d, point):
        return []
    if point == "cast":
        from filmcheck import cast
        try:
            names = cast.unapproved(d)
        except cast.CastError as e:
            return [e.message]
        if names:
            return [f"characters not approved: {', '.join(names)} (approve on the job page, or in the chat: "
                    f"sh bin/studio cast approve {d.name} --all --source chat)"]
        return []
    what = {"script": "the script review", "shots": "the shots review"}.get(point, f"the {point} review")
    if st == "stale":
        return [f"{what} was approved, but the {point} changed since (review again: sh bin/studio point approve {d.name} "
                f"{point} --source chat, or on the job page)"]
    return [f"{what} is not approved (approve on the job page, or in the chat: sh bin/studio point approve {d.name} "
            f"{point} --source chat)"]


def to_json(film_dir: Path) -> str:
    return json.dumps(status(film_dir), ensure_ascii=False)
