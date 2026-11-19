"""learn craft-label (specs/027 FR-014): craft labels for every labelled shot of a reference set, the per-video shares
of real action, held objects, outdoor places and over-the-shoulder shots, and their spread written into a style's
template.json → craft with an EVIDENCE.md entry. Labels are cached in references/<set>/profile/craft-labels.json by
the craft labeler's version and each video's shot list, so a second run only labels what is missing."""
import datetime
import hashlib
import json
import shutil

from . import refset, shots

from filmcheck import craftlabel  # noqa: E402  (tools/ is on sys.path through sl.shots)

CACHE = "craft-labels.json"


def cache_file(name: str):
    return refset.set_dir(name) / "profile" / CACHE


def _sig(rows: list) -> str:
    return hashlib.sha256(json.dumps([[r["id"], r.get("evidence")] for r in rows]).encode()).hexdigest()[:12]


def _rows(name: str, vid: str) -> list:
    d = refset.read_json(shots.shots_file(name, vid))
    return [r for r in d["shots"] if not r.get("short")]


def label_set(name: str, force: bool = False, log=print, labeler=None) -> dict:
    """Label every video of the set that has a shot list. labeler: the label function (tests pass a fake)."""
    labeler = labeler or craftlabel.label
    f = cache_file(name)
    cache = refset.read_json(f) if f.exists() and not force else {}
    if cache.get("version") != craftlabel.version():
        cache = {"version": craftlabel.version(), "videos": {}}
    total = {"shots": 0, "calls": 0, "videos": 0}
    for v in shots._videos_with_shots(name):
        vid = v["id"]
        rows = _rows(name, vid)
        sig = _sig(rows)
        have = cache["videos"].get(vid) or {}
        if have.get("sig") == sig and len(have.get("labels") or {}) == len(rows):
            log(f"· {vid}: {len(rows)} shots already labelled")
            continue
        prof = refset.profile_dir(name, vid)
        cells = {} if all((prof / r["frame"]).exists() for r in rows) else shots.cell_frames(prof, rows)
        rows = [r for r in rows if not cells or r["id"] in cells]
        groups = shots.draw_sheets(rows, lambda s: cells.get(s["id"]) or prof / s["frame"], prof / "craft-sheets",
                                   f"{vid}_craft", captions=False)
        got = labeler(groups)
        if cells:
            shutil.rmtree(prof / "label-cells", ignore_errors=True)
        shutil.rmtree(prof / "craft-sheets", ignore_errors=True)
        cache["videos"][vid] = {"sig": sig, "labels": got["labels"], "model": got["model"], "calls": got["calls"],
                                "usage": got["usage"]}
        refset.write_json(f, cache)
        total["shots"] += len(got["labels"])
        total["calls"] += got["calls"]
        total["videos"] += 1
        log(f"✓ {vid}: {len(got['labels'])} shots ({got['calls']} call(s), {got['model']})")
    return total


def per_video(name: str, skip=()) -> dict:
    """{vid: shares} for every labelled video not in skip; ots comes from the shot labels' angle."""
    cache = refset.read_json(cache_file(name)) if cache_file(name).exists() else {"videos": {}}
    out = {}
    for vid, c in sorted(cache["videos"].items()):
        if vid in skip:
            continue
        labs = c.get("labels") or {}
        rows = []
        for r in _rows(name, vid):
            lab = labs.get(r["id"])
            if not lab:
                continue
            card = lab["card"] or r.get("scale") == "insert"
            rows.append({**lab, "card": card, "ots": r.get("angle") == "ots"})
        out[vid] = craftlabel.shares(rows)
    return out


def summary(name: str, skip=()) -> dict:
    pv = per_video(name, skip)
    return {k: craftlabel.spread([s[k] for s in pv.values()]) for k in ("action", "prop", "outdoor", "ots")} | {
        "videos": sorted(pv), "shots": sum(s["shots"] for s in pv.values()), "per_video": pv}


def table(sm: dict) -> list:
    lines = ["| video | shots | action | prop | outdoor | ots |", "|---|---|---|---|---|---|"]
    for vid, s in sm["per_video"].items():
        lines.append(f"| {vid} | {s['shots']} | {s['action']} | {s['prop']} | {s['outdoor']} | {s['ots']} |")
    for q in ("min", "p25", "p50", "p75", "max"):
        lines.append(f"| {q} | | " + " | ".join(str(sm[k].get(q)) for k in ("action", "prop", "outdoor", "ots")) + " |")
    return lines


def craft_block(name: str, sm: dict, skip=()) -> dict:
    """template.json → craft (data-model.md): action min = p25 of the videos (error); other ranges = min–max (warn,
    the same way shots.json keeps its ranges)."""
    a = sm["action"]
    src = (f"learn craft-label {name}, {datetime.date.today().isoformat()}, {sm['shots']} shots of "
           f"{len(sm['videos'])} videos" + (f" (skipped {', '.join(skip)})" if skip else "") +
           f", craftlabel {craftlabel.version()}")
    rng = lambda k: [sm[k]["min"], sm[k]["max"]]  # noqa: E731
    return {"source": src,
            "action": {"share_p25": a["p25"], "share_p50": a["p50"], "share_p75": a["p75"], "min": a["p25"], "rule": "error"},
            "outdoor": {"range": rng("outdoor"), "rule": "warn"},
            "prop": {"range": rng("prop"), "rule": "warn"},
            "ots": {"range": rng("ots"), "rule": "warn"}}


def write_style(name: str, slug: str, sm: dict, skip=()) -> dict:
    d = refset.root() / "my-styles" / refset.check_slug(slug, "phong cách")
    tf = d / "template.json"
    if not tf.is_file():
        raise refset.StepError(f"{tf} không có: phong cách chưa có template.json")
    tpl = json.loads(tf.read_text(encoding="utf-8"))
    tpl["craft"] = craft_block(name, sm, skip)
    if isinstance(tpl.get("source"), dict):             # learn template-check: every number names its source
        tpl["source"]["craft"] = tpl["craft"]["source"] + " (references/" + name + "/profile/craft-labels.json)"
    refset.write_json(tf, tpl)                     # indent 1, like every learned file
    ev = d / "EVIDENCE.md"
    text = ev.read_text(encoding="utf-8") if ev.is_file() else "# Evidence\n"
    head = "## Craft shares (specs/027)"
    if head in text:
        text = text[:text.index(head)].rstrip() + "\n"
    text += "\n" + "\n".join([head, "", tpl["craft"]["source"] + ".",
                              "Action and prop: share of shots with people; outdoor and ots: share of shots that are "
                              "not cards. Action min = p25 of the videos (error in qc plan); others warn outside min–max.",
                              "", *table(sm)]) + "\n"
    ev.write_text(text, encoding="utf-8")
    return tpl["craft"]
