"""Films, reference sets and saved styles, read from the project folders by id only (FR-019)."""
import html
import re
from pathlib import Path

import markdown as md

from . import store
from .store import StudioError

NAME = re.compile(r"^[a-z0-9-]{1,60}$")
SHEET = re.compile(r"^v\d{2}_\d{4}\.jpg$")
PROOF = re.compile(r"^(ref|ours_r\d+_[\d.]+)\.jpg$")
PRIVATE = {"origin", "title", "channel", "handle", "source_id", "src_name", "src_size"}


def check_name(name: str) -> str:
    if not NAME.match(name or ""):
        raise StudioError("bad_name", "tên không hợp lệ", 400)
    return name


def _inside(base: Path, *parts: str) -> Path:
    p = base.joinpath(*parts).resolve()
    if not p.is_relative_to(base.resolve()):
        raise StudioError("bad_name", "đường dẫn không hợp lệ", 400)
    return p


def film_dir(name: str) -> Path:
    return _inside(store.root() / "films", check_name(name))


def set_dir(name: str) -> Path:
    return _inside(store.root() / "references", check_name(name))


def style_dir(slug: str) -> Path:
    return _inside(store.root() / "my-styles", check_name(slug))


def to_html(text: str) -> str:
    """Markdown to HTML with raw HTML neutralised (a style file must never inject scripts)."""
    safe = (text or "").replace("&", "&amp;").replace("<", "&lt;")
    return md.markdown(safe, extensions=["tables", "fenced_code", "sane_lists"])


def srt_to_vtt(srt: str) -> str:
    body = re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", srt.replace("\r\n", "\n").strip())
    return "WEBVTT\n\n" + body + "\n"


def _need(p: Path) -> Path:
    if not p.is_file():
        raise StudioError("not_found", f"không thấy tệp {p.name}", 404)
    return p


# ---------- films ----------
def films() -> list:
    out = []
    base = store.root() / "films"
    for d in sorted(base.glob("*/")) if base.exists() else []:
        if not NAME.match(d.name):
            continue
        out.append(film_summary(d.name))
    return out


def film_summary(name: str) -> dict:
    d = film_dir(name)
    if not d.is_dir():
        raise StudioError("not_found", f"không có phim \"{name}\"", 404)
    has_video = (d / f"{name}.mp4").is_file()
    return {"name": name, "has_video": has_video, "has_poster": (d / "poster.jpg").is_file(),
            "has_subtitles": (d / f"{name}.srt").is_file(), "rendering": not has_video and (d / "out").exists()}


def film(name: str) -> dict:
    f = film_summary(name)
    d = film_dir(name)
    credits = d / "CREDITS"
    treat = d / "TREATMENT.md"
    f["credits"] = credits.read_text(encoding="utf-8", errors="replace") if credits.is_file() else None
    f["treatment_html"] = to_html(treat.read_text(encoding="utf-8", errors="replace")) if treat.is_file() else None
    return f


def film_file(name: str, kind: str) -> Path:
    d = film_dir(name)
    return _need({"video": d / f"{name}.mp4", "poster": d / "poster.jpg", "srt": d / f"{name}.srt"}[kind])


# ---------- reference sets ----------
def _scrub(x):
    if isinstance(x, dict):
        return {k: _scrub(v) for k, v in x.items() if k not in PRIVATE}
    if isinstance(x, list):
        return [_scrub(v) for v in x]
    return x


def sets() -> list:
    out = []
    base = store.root() / "references"
    for p in sorted(base.glob("*/set.json")) if base.exists() else []:
        if not NAME.match(p.parent.name):
            continue
        data = store.read_json(p) or {}
        vids = data.get("videos", [])
        out.append({"set": p.parent.name, "videos": len(vids),
                    "measured": sum(v.get("state") in ("measured", "transcribed") for v in vids),
                    "media_removed": bool(data.get("media_removed")) or not (p.parent / "videos").exists()})
    return out


def set_detail(name: str) -> dict:
    d = set_dir(name)
    data = store.read_json(d / "set.json")
    if not data:
        raise StudioError("not_found", f"không có bộ tham chiếu \"{name}\"", 404)
    videos = []
    for v in data.get("videos", []):
        prof = store.read_json(d / "profile" / v["id"] / "video.json") or {}
        videos.append({"id": v["id"], "state": v.get("state"), "skip_reason": v.get("skip_reason"),
                       **{k: prof.get(k) for k in ("orientation", "duration", "fps", "frames_measured", "frames_expected",
                                                   "cuts_per_min", "still_ratio", "shot_len", "palette", "audio", "speech")}})
    return {"set": name, "created": data.get("created"), "media_removed": bool(data.get("media_removed")),
            "summary": _scrub(store.read_json(d / "profile" / "summary.json")), "videos": _scrub(videos),
            "compare": store.read_json(d / "proof" / "compare.json")}


def sheets(name: str) -> dict:
    d = set_dir(name)
    found = {}
    for f in sorted((d / "profile").glob("v*/sheets/*.jpg")):
        if SHEET.match(f.name):
            found.setdefault(f.parent.parent.name, []).append(f.name)
    if not found:
        return {"removed": True, "sheets": {}}
    return {"removed": False, "sheets": found}


def sheet_file(name: str, file: str) -> Path:
    if not SHEET.match(file or ""):
        raise StudioError("bad_name", "tên ảnh ghép không hợp lệ", 400)
    return _need(_inside(set_dir(name), "profile", file[:3], "sheets", file))


def proof_file(name: str, file: str) -> Path:
    if not PROOF.match(file or ""):
        raise StudioError("bad_name", "tên ảnh chứng minh không hợp lệ", 400)
    return _need(_inside(set_dir(name), "proof", "out", file))


# ---------- saved styles ----------
def styles() -> list:
    out = []
    base = store.root() / "my-styles"
    for p in sorted(base.glob("*/style.json")) if base.exists() else []:
        if NAME.match(p.parent.name):
            meta = store.read_json(p) or {}
            out.append({**meta, "slug": p.parent.name, "has_styleframe": (p.parent / "styleframe.jpg").is_file(),
                        "based_on_in_library": in_library(meta.get("based_on"))})
    return out


def style(slug: str) -> dict:
    d = style_dir(slug)
    meta = store.read_json(d / "style.json")
    if meta is None:
        raise StudioError("not_found", f"không có phong cách \"{slug}\"", 404)
    read = lambda f: (d / f).read_text(encoding="utf-8", errors="replace") if (d / f).is_file() else ""  # noqa: E731
    return {**meta, "slug": slug, "has_styleframe": (d / "styleframe.jpg").is_file(),
            "based_on_in_library": in_library(meta.get("based_on")),
            "style_html": to_html(read("STYLE.md")), "evidence_html": to_html(read("EVIDENCE.md"))}


def styleframe(slug: str) -> Path:
    return _need(style_dir(slug) / "styleframe.jpg")


def escape(s: str) -> str:
    return html.escape(s or "")


# ---------- style library (004) ----------
LIB_FIELDS = ("num", "en", "cn", "film", "line", "uses", "dur")


def lib_dir() -> Path:
    return store.project_root() / "lib" / "lemo-opuscar"


def _lib_commit() -> str:
    head = (lib_dir() / ".git" / "HEAD")
    try:
        sha = head.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return sha if re.fullmatch(r"[0-9a-f]{40}", sha) else ""


def _github_base() -> str:
    """https://github.com/<owner>/<repo> from library.lock, or "" when the library is not on GitHub."""
    try:
        lock = (store.project_root() / "library.lock").read_text(encoding="utf-8")
    except OSError:
        return ""
    m = re.search(r"^LIB_REPO=https://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?\s*$", lock, re.M)
    return f"https://github.com/{m.group(1)}/{m.group(2)}" if m else ""


def _lib_entry(d: Path, base: str, sha: str):
    """One library style as served by the API, or None when its files are missing or broken."""
    try:
        meta = store.read_json(d / "style.json")
    except (OSError, ValueError):
        meta = None
    if not isinstance(meta, dict) or not meta.get("en") or not (d / "STYLE.md").is_file():
        return None
    out = {"slug": d.name, **{k: meta.get(k) for k in LIB_FIELDS}}
    out["num"] = str(out["num"] or "")
    out["uses"] = [str(u) for u in (out["uses"] or []) if u]
    out["dur"] = out["dur"] or 0
    out["category"] = meta.get("category_en") or "Other"
    out["has_poster"] = (d / "poster.jpg").is_file()
    out["github_url"] = f"{base}/tree/{sha}/styles/{d.name}" if base and sha else None
    return out


def _num_key(s: dict):
    return (int(s["num"]) if s["num"].isdigit() else 10**6, s["slug"])


def library() -> dict:
    styles_dir = lib_dir() / "styles"
    if not styles_dir.is_dir():
        return {"installed": False, "version": "", "styles": [], "groups": [], "posters": {"have": 0, "total": 0}, "skipped": 0}
    base, sha = _github_base(), _lib_commit()
    styles, skipped = [], 0
    for d in sorted(p for p in styles_dir.iterdir() if p.is_dir()):
        if d.name == "_template" or d.name.startswith("."):
            continue
        entry = _lib_entry(d, base, sha) if NAME.match(d.name) else None
        if entry is None:
            skipped += 1
        else:
            styles.append(entry)
    styles.sort(key=_num_key)
    groups = {}
    for s in styles:
        groups[s["category"]] = groups.get(s["category"], 0) + 1
    return {"installed": True, "version": sha[:7], "styles": styles,
            "groups": [{"name": k, "count": v} for k, v in groups.items()],
            "posters": {"have": sum(s["has_poster"] for s in styles), "total": len(styles)}, "skipped": skipped}


def _lib_style_dir(slug: str) -> Path:
    if slug == "_template":            # the library's template folder is never a style (before check_name: 404, not 400)
        raise StudioError("not_found", "không có phong cách này trong thư viện", 404)
    check_name(slug)
    return _inside(lib_dir() / "styles", slug)


def library_style(slug: str) -> dict:
    d = _lib_style_dir(slug)
    entry = _lib_entry(d, _github_base(), _lib_commit()) if d.is_dir() else None
    if entry is None:
        raise StudioError("not_found", f"không có phong cách \"{slug}\" trong thư viện", 404)
    entry["style_html"] = to_html((d / "STYLE.md").read_text(encoding="utf-8", errors="replace"))
    return entry


def library_poster(slug: str) -> Path:
    d = _lib_style_dir(slug)
    if not d.is_dir() or _lib_entry(d, "", "") is None:
        raise StudioError("not_found", f"không có phong cách \"{slug}\" trong thư viện", 404)
    return _need(d / "poster.jpg")


def in_library(slug) -> bool:
    if not isinstance(slug, str) or not NAME.match(slug) or slug == "_template":
        return False
    d = lib_dir() / "styles" / slug
    return d.is_dir() and _lib_entry(d, "", "") is not None
