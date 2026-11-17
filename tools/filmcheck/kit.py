"""Film kits of the learned styles (specs/022): copy a style's kit/ into a film, and the hero colour check.

The library's page server only serves the library and the film folder (mounted at /@film/), so a film page cannot
reach my-styles/. `kit use` copies my-styles/<style>/kit/ into films/<film>/kit/ and records where it came from.
Standard library only.
"""
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

SKIP = {"test", ".from", "__pycache__"}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


class KitError(Exception):
    pass


# ---------- colour ----------
def _lab(hexcol: str) -> tuple:
    r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    x = (0.4124 * lin[0] + 0.3576 * lin[1] + 0.1805 * lin[2]) / 0.95047
    y = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    z = (0.0193 * lin[0] + 0.1192 * lin[1] + 0.9505 * lin[2]) / 1.08883
    f = [t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116 for t in (x, y, z)]
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


def delta_e(a: str, b: str) -> float:
    """CIE76 colour distance between two #rrggbb colours."""
    la, lb = _lab(a), _lab(b)
    return sum((p - q) ** 2 for p, q in zip(la, lb)) ** 0.5


# ---------- catalogue ----------
def style_kit(root: Path, style: str) -> Path:
    return Path(root) / "my-styles" / style / "kit"


def catalog(root: Path, style: str):
    p = style_kit(root, style) / "catalog.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def hero_problem(hero: dict, cat) -> str:
    """Why a hero costume is not allowed for a style's kit, or '' (FR-014, FR-015)."""
    if not hero or not cat:
        return ""
    avoid = cat.get("avoid_hero") or {}
    hood = hero.get("hoodie")
    if hood and HEX.match(hood) and avoid.get("hoodie"):
        d = delta_e(hood, avoid["hoodie"])
        lim = float(avoid.get("min_delta_e", 25))
        if d < lim:
            return f"hoodie too close to the reference character (ΔE {d:.0f} < {lim:g})"
    return ""


# ---------- copy ----------
def _files(d: Path) -> list:
    return sorted(p for p in d.rglob("*") if p.is_file() and not (set(p.relative_to(d).parts) & SKIP))


def kit_hash(d: Path) -> str:
    """Hash of the kit's files and of the style's template.json beside it (copied in with the kit, specs/023)."""
    h = hashlib.sha256()
    for p in _files(d):
        h.update(str(p.relative_to(d).as_posix()).encode() + b"\0" + p.read_bytes() + b"\0")
    tpl = d.parent / "template.json"
    if tpl.is_file():
        h.update(b"template.json\0" + tpl.read_bytes() + b"\0")
    return h.hexdigest()


def _snapshot(film_dir: Path) -> dict:
    try:
        s = json.loads((film_dir / "channel.json").read_text(encoding="utf-8"))
        return s if isinstance(s, dict) else {}
    except (OSError, ValueError):
        return {}


def use(root: Path, film_dir: Path, style: str = None, update: bool = False) -> dict:
    """Copy my-styles/<style>/kit/ into <film>/kit/. Returns {status, style, sha256, hint}; raises KitError."""
    root, film_dir = Path(root), Path(film_dir)
    snap = _snapshot(film_dir)
    film = snap.get("film") or {}
    style = style or film.get("style")
    if not style:
        raise KitError("no style: give --style, or attach a channel to the film first")
    src = style_kit(root, style)
    if not src.is_dir():
        raise KitError(f"the style \"{style}\" has no kit (my-styles/{style}/kit/)")
    cat = catalog(root, style)
    why = hero_problem(film.get("hero"), cat)
    if why:
        raise KitError(f"hero: {why}")
    sha = kit_hash(src)
    dst = film_dir / "kit"
    status = "copied"
    if dst.exists():
        try:
            old = json.loads((dst / ".from").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            old = {}
        if old.get("sha256") == sha and old.get("style") == style:
            status = "up_to_date"
        elif not update:
            raise KitError(f"films/{film_dir.name}/kit/ is from {str(old.get('sha256', 'unknown'))[:8]}; the style has "
                           f"{sha[:8]}. Use --update to replace it")
        else:
            status = "updated"
    if status != "up_to_date":
        tmp = film_dir / ".kit-new"
        shutil.rmtree(tmp, ignore_errors=True)
        for p in _files(src):
            q = tmp / p.relative_to(src)
            q.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, q)
        if (src.parent / "template.json").is_file():           # specs/023: the page reads the style's measures
            shutil.copy2(src.parent / "template.json", tmp / "template.json")
        (tmp / ".from").write_text(json.dumps({"style": style, "sha256": sha,
                                               "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}) + "\n",
                                   encoding="utf-8")
        shutil.rmtree(dst, ignore_errors=True)
        tmp.rename(dst)
    hint = ""
    if snap.get("channel") and not film.get("hero"):
        hint = f'set the channel hero with "channel set {snap["channel"]} hero hoodie=#rrggbb …"'
    return {"status": status, "style": style, "sha256": sha, "hint": hint}
