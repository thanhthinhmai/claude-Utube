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
}


def empty() -> dict:
    return {"narration": None,
            "script": {"verdict": "pending", "skip_reason": None, "machine": [], "editor": [], "fix_rounds": 0},
            "film": None}


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
        if (f.get("measures") or {}).get("texts_checked") is False:
            out.append("| on-screen text | not checked | the film has no window.TEXTS |")
        out.append("")
        if f.get("problems"):
            out += ["Problems:", "", *[f"- {p}" for p in f["problems"]], ""]
    return "\n".join(out).rstrip() + "\n"
