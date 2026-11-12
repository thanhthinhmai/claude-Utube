"""A style's measured ranges for the QC tiers (specs/020 FR-013, FR-017; research R6).

Read from the "Key numbers" table of my-styles/<slug>/EVIDENCE.md (written by style-learn), then overridden key by key
by my-styles/<slug>/qc.json, then the studio's own tools/filmcheck/styles.json entry for library styles. A style with
none of these gives {} and the style comparison is skipped."""
import json
import os
import re
from pathlib import Path

STYLES_FILE = Path(__file__).resolve().parent / "styles.json"
ROWS = {   # EVIDENCE.md metric (lower-case, start of the cell) → key
    "luma p50": "luma_p50",
    "saturation p50": "saturation_p50",
    "cuts/min": "cuts_per_min",
    "loudness range": "loudness_range",
}
KEYS = ("luma_p50", "saturation_p50", "cuts_per_min", "loudness_range", "shot_max", "still_max", "subtitle_zone",
        "dark_p50", "blown_share")
_NUM = r"[−-]?\d+(?:\.\d+)?"
RANGE = re.compile(rf"({_NUM})\s*(?:–|-|to)\s*({_NUM})")


def _f(x: str) -> float:
    return float(x.replace("−", "-"))


def slug_of(film_dir: Path):
    from filmcheck import qc
    return qc.style_slug(Path(film_dir))


def style_dir(film_dir: Path, slug: str) -> Path:
    root = Path(os.environ.get("STUDIO_ROOT") or Path(film_dir).resolve().parents[1])
    d = Path(film_dir).resolve().parents[1] / "my-styles" / slug
    return d if d.is_dir() else root / "my-styles" / slug


def from_evidence(text: str) -> dict:
    out = {}
    for row in text.splitlines():
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        name = cells[0].lower()
        for k, key in ROWS.items():
            if name.startswith(k):
                m = RANGE.search(cells[-1])
                if m:
                    a, b = sorted((_f(m.group(1)), _f(m.group(2))))
                    out[key] = [a, b]
    return out


def load(film_dir: Path, slug=None) -> dict:
    slug = slug or slug_of(film_dir)
    if not slug:
        return {}
    out, sources = {}, []
    d = style_dir(film_dir, slug)
    ev = d / "EVIDENCE.md"
    if ev.is_file():
        got = from_evidence(ev.read_text(encoding="utf-8", errors="replace"))
        if got:
            out.update(got)
            sources.append("EVIDENCE.md")
    for p, key in ((STYLES_FILE, slug), (d / "qc.json", None)):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        data = (data.get(key) or {}) if key else data
        if not isinstance(data, dict):
            continue
        got = {k: v for k, v in data.items() if k in KEYS}
        if got:
            out.update(got)
            sources.append(p.name)
    if out:
        out["source"] = " + ".join(sources)
    return out


def has_ranges(refs: dict) -> bool:
    return any(k in refs for k in ("luma_p50", "saturation_p50", "cuts_per_min", "loudness_range"))
