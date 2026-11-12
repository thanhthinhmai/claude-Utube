"""checks.json and CHECKS.md in a film folder (specs/010 R10, contracts/files.md).

Every writer goes through update(): it reads the current file, changes one part and writes both files atomically,
so `script check`, `script review` and `qc` never drop each other's results."""
import json
import os
import tempfile
from pathlib import Path

THRESHOLDS = {   # what CHECKS.md shows next to each measure (contracts/cli.md)
    "silence_ratio": "≤ 0.20",
    "long_pauses_bad": "pauses ≥ 0.8 s only between paragraphs",
    "cuts_bad": "no cut inside a sentence; ≥ 0.4 s after it ends",
    "key_shots_bad": "shot with each paragraph's last word ≥ 2.5 s",
    "tail_s": "≤ 1.5 s",
    "stills_bad": "no still picture longer than the style allows (6 s)",
    "missing_glyphs": "0 characters without a font",
    "shots_short": "every shot ≥ 1.1 s",
    "shots_long": "every shot ≤ the style's longest (6 s)",
    "cues_short": "each subtitle ≥ max(1.8 s, its speech + 0.6 s)",
    "loudness_range": "inside the style's range",
    "av_sync": "sound and picture lengths within 0.1 s",
}
TIER_NAMES = (("voice", "Voice (tier 0)"), ("plan", "Plan (tier 1)"), ("shots", "Shots (tier 2)"),
              ("render", "Render (tier 3)"), ("final", "Final (tier 4)"))


THRESHOLDS_PUBLISH = {   # the publish pack's measures in CHECKS.md (specs/011 contracts/cli.md)
    "title_lengths": "≤ 100 characters; a break in the first 60",
    "hook_chars": "≤ 150 characters in 2 lines",
    "description_chars": "≤ 5000 characters",
    "hashtags": "3–5 tags",
    "numbers_unsourced": "every number is in SCRIPT.md or SOURCES.md",
    "subtitles_match": "the subtitles say the passed script",
    "subtitle_cues_bad": "≤ 2 lines of ≤ 42, 1–7 s each",
}


def empty() -> dict:
    return {"narration": None,
            "script": {"verdict": "pending", "skip_reason": None, "machine": [], "editor": [], "fix_rounds": 0},
            "film": None, "publish": None, "tiers": {}}


def load(film_dir: Path) -> dict:
    p = Path(film_dir) / "checks.json"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return empty()
    base = empty()
    base.update(data)
    base["script"] = {**empty()["script"], **(data.get("script") or {})}
    return base


def _write(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def save(film_dir: Path, data: dict) -> dict:
    d = Path(film_dir)
    d.mkdir(parents=True, exist_ok=True)
    _write(d / "checks.json", json.dumps(data, ensure_ascii=False, indent=1))
    _write(d / "CHECKS.md", markdown(data))
    return data


def update(film_dir: Path, fn) -> dict:
    """fn(data) changes data in place; the result is saved and returned."""
    data = load(film_dir)
    fn(data)
    return save(film_dir, data)


def _fmt(v) -> str:
    if v is None:
        return "–"
    if isinstance(v, float):
        return f"{v:.2f}"
    if isinstance(v, list):
        return "none" if not v else f"{len(v)}: " + "; ".join(
            ", ".join(f"{k} {_fmt(x) if not isinstance(x, str) else x}" for k, x in i.items()) if isinstance(i, dict) else str(i)
            for i in v[:5]) + (" …" if len(v) > 5 else "")
    return str(v)


def markdown(data: dict) -> str:
    s, out = data["script"], ["# Checks", ""]
    out.append(f"**Script:** {s['verdict']}" + (f" ({s['skip_reason']})" if s.get("skip_reason") else "")
               + f" · fix rounds: {s.get('fix_rounds', 0)}")
    out.append("")
    if s["machine"] or s["editor"]:
        out += ["| Round | Who | Score | Notes |", "|---|---|---|---|"]
        for m in s["machine"]:
            hard = ", ".join(k for k, ok in (m.get("hard") or {}).items() if not ok)
            out.append(f"| {m.get('round', 0)} | machine | {m.get('score')} | "
                       + (f"failed: {hard}; " if hard else "") + f"{len(m.get('issues', []))} issues |")
        for e in s["editor"]:
            out.append(f"| {e.get('round')} | editor ({e.get('model') or 'same as job'}) | {e.get('score')} | "
                       f"P1 {e.get('p1', 0)} · P2 {e.get('p2', 0)} · P3 {e.get('p3', 0)} |")
        out.append("")
        last_m = s["machine"][-1] if s["machine"] else None
        last_e = s["editor"][-1] if s["editor"] else None
        issues = [f"- {i['para']}.{i.get('sentence', '')} {i['rule']}: {i.get('detail', '')}" for i in (last_m or {}).get("issues", [])]
        issues += [f"- {i['level']} {i['para']}: {i['reason']}" for i in (last_e or {}).get("issues", [])]
        if issues:
            out += ["Latest issues:", "", *issues, ""]
    f = data.get("film")
    if f:
        out += [f"**Film:** {'pass' if f.get('pass') else 'fail'}", "", "| Measure | Value | Rule |", "|---|---|---|"]
        for k, v in (f.get("measures") or {}).items():
            if k in THRESHOLDS:
                out.append(f"| {k} | {_fmt(v)} | {THRESHOLDS[k]} |")
        rend = (f.get("measures") or {}).get("render")
        if rend:
            out.append(f"| rendering | {rend.get('mode')}{' · ' + rend['renderer'] if rend.get('renderer') else ''} | GPU when the machine can (specs/019) |")
        if (f.get("measures") or {}).get("texts_checked") is False:
            out.append("| on-screen text | not checked | the film has no window.TEXTS |")
        out.append("")
        if f.get("problems"):
            out += ["Problems:", "", *[f"- {p}" for p in f["problems"]], ""]
    out += tiers_markdown(data.get("tiers") or {})
    p = data.get("publish")
    if p:
        out += [f"**Publish:** {'pass' if p.get('pass') else 'fail'}", ""]
        if p.get("cut"):
            out += [f"The publish step was stopped: {p['cut']}", ""]
        m = p.get("measures") or {}
        out += ["| Measure | Value | Rule |", "|---|---|---|"]
        for t in m.get("thumbs") or []:
            out.append(f"| {t.get('file')} | {t.get('w')}×{t.get('h')}, {t.get('bytes')} B, text "
                       f"{_fmt(t.get('text_height_ratio'))}, contrast {_fmt(t.get('contrast'))} | "
                       f"right size, < 2 MB, text ≥ 0.08 of the height, contrast ≥ 4.5 |")
        for k, rule in THRESHOLDS_PUBLISH.items():
            if k in m and m[k] is not None:
                out.append(f"| {k} | {_fmt(m[k])} | {rule} |")
        for k, ok in (p.get("applicable") or {}).items():
            if not ok:
                out.append(f"| {k} | not applicable | |")
        out.append("")
        if p.get("problems"):
            out += ["Problems:", "", *[f"- {x}" for x in p["problems"]], ""]
    return "\n".join(out).rstrip() + "\n"


def tiers_markdown(tiers: dict) -> list:
    """The "Tiers" part of CHECKS.md (specs/020 contracts/checks.md)."""
    if not tiers:
        return []
    out = ["**Tiers**", "", "| Tier | Result | Problems | Warnings | Exceptions | At |", "|---|---|---|---|---|---|"]
    open_, excepted, accepted = [], [], []
    for key, label in TIER_NAMES:
        r = tiers.get(key)
        if not r:
            out.append(f"| {label} | not run | | | | |")
            continue
        iss = r.get("issues") or []
        blk = [i for i in iss if i.get("severity") == "block" and not i.get("excepted")]
        wrn = [i for i in iss if i.get("severity") == "warn"]
        exc = [i for i in iss if i.get("excepted")]
        res = "pass" if r.get("pass") else "fail"
        if key == "render" and r.get("skipped_checks"):
            res += f" · checks skipped: {r['skipped_checks'].get('reason')}"
        out.append(f"| {label} | {res} | {len(blk)} | {len(wrn)} | {len(exc)} | {r.get('at') or ''} |")
        open_ += [(key, i) for i in blk + wrn]
        excepted += [(key, i) for i in exc]
        sa = r.get("style_accept")
        if sa and sa.get("reason") and wrn:
            accepted.append(f"- {label}: {len(wrn)} style warning(s) accepted — {sa['reason']}")
    out.append("")
    if open_:
        out += ["Open:", ""] + [f"- {k}: {i.get('ref')} {i.get('rule')} {i.get('measure')} (limit {i.get('limit')})"
                                + (f" → {i['fix']}" if i.get("fix") else "") for k, i in open_[:40]]
        out += ([f"- … {len(open_) - 40} more"] if len(open_) > 40 else []) + [""]
    if excepted:
        out += ["Exceptions:", ""] + [f"- {k}: {i.get('ref')} {i.get('rule')} — {i['excepted'].get('reason')}" for k, i in excepted] + [""]
    if accepted:
        out += ["Style warnings accepted:", ""] + accepted + [""]
    return out
