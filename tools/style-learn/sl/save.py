"""Save an approved style into my-styles/ and clean up the reference media (research.md §13, FR-004a, FR-020, FR-021)."""
import datetime
import json
import shutil
import subprocess
from pathlib import Path

from . import names, refset
from .refset import MEDIA_EXT, StepError, UsageError

PRIVATE_KEYS = {"title", "channel", "handle", "origin", "source_id", "src_name", "set", "skipped"}
SOURCE_EXT = {".html", ".js", ".mjs", ".css", ".json", ".svg", ".woff", ".woff2", ".ttf", ".otf", ".txt", ".md"}
RASTER_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".avif"}


def lib_dir() -> Path:
    return refset.root() / "lib" / "lemo-opuscar"


def library_styles() -> set:
    d = lib_dir() / "styles"
    return {p.name for p in d.iterdir() if p.is_dir() and not p.name.startswith("_")} if d.exists() else set()


def library_version() -> str:
    try:
        return subprocess.run(["git", "-C", str(lib_dir()), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        lock = refset.root() / "library.lock"
        for line in lock.read_text().splitlines() if lock.exists() else []:
            if line.startswith("LIB_COMMIT="):
                return line.split("=", 1)[1][:7]
        return "unknown"


def scrub(x):
    """Remove anything that could name the channel or its videos."""
    if isinstance(x, dict):
        out = {k: scrub(v) for k, v in x.items() if k not in PRIVATE_KEYS}
        if "skipped" in x:
            out["skipped_count"] = len(x["skipped"])
        return out
    if isinstance(x, list):
        return [scrub(v) for v in x]
    return x


def _proof_sources(proof: Path) -> list:
    files = []
    for f in proof.rglob("*"):
        rel = f.relative_to(proof)
        if f.is_file() and rel.parts[0] not in ("out", "stills") and not f.name.startswith("compare."):
            files.append(f)
    return files


CORR_HEAD = "## Corrections log"
DEMO_FILES = ("DEMO.md", "demo", "test.jpg", "test.mp4", "demo-checks.json")
KEEP_ON_UPDATE = DEMO_FILES + ("kit",)                     # specs/022: the film kit stays with the style too
TEMPLATE_FILES = ("TEMPLATE.md", "template.json")          # specs/023: the craft template; a new one from style/ wins, else the old one is kept
# specs/022 FR-013: the only files of references/<set>/style/ that go into the style; work files (logs, reviews, .job)
# stay behind. The proof frame's sources come from proof/, the measurements from profile/.
STYLE_FILES = ("STYLE.md", "EVIDENCE.md", "style.json", "STRUCTURE.md", "shots.json") + TEMPLATE_FILES


def corrections(text: str) -> list:
    """The table rows of the "Corrections log" section of an EVIDENCE.md (header and separator left out)."""
    out, inside = [], False
    for ln in text.splitlines():
        if ln.startswith("## "):
            inside = ln.strip().startswith(CORR_HEAD)
            continue
        if inside and ln.strip().startswith("|") and not set(ln.replace("|", "").strip()) <= set("-: "):
            out.append(ln.strip())
    return out[1:] if out else []                      # the first row is the header


def shot_refs(summary: dict) -> dict:
    """my-styles/<slug>/shots.json (specs/021 data-model ShotGrammarRefs) from the set summary, or {}."""
    by = summary.get("by_orientation") or {}
    g = (by.get(summary.get("majority_orientation")) or {}).get("shot_grammar")
    if not g:
        return {}
    rng = lambda k: [g[k]["min"], g[k]["max"]] if g.get(k) and g[k].get("min") is not None else None  # noqa: E731
    out = {"source": f"learned {datetime.date.today().isoformat()}, {summary.get('videos_measured')} videos",
           "scale_share": {k[6:]: rng(k) for k in g if k.startswith("scale_") and k != "scale_change_share" and rng(k)},
           "angle_share": {k[6:]: rng(k) for k in g if k.startswith("angle_") and rng(k)},
           "scale_change_share": rng("scale_change_share"), "focused_share_p50": rng("focused_share_p50")}
    if g.get("longest_same_scale", {}).get("max") is not None:
        out["longest_same_scale_max"] = g["longest_same_scale"]["max"]
    if g.get("top_set_share", {}).get("max") is not None:
        out["top_set_share_max"] = g["top_set_share"]["max"]
    try:
        import sys as _s
        _s.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from filmcheck import focus
        out["focus_t"] = focus.FOCUS_T
    except ImportError:
        pass
    return {k: v for k, v in out.items() if v not in (None, {}, [])}


def save(name: str, slug: str, en: str, cn: str, based_on: str, accept_proof: bool = False, update: bool = False) -> int:
    refset.check_slug(slug, "mã phong cách")
    mine = refset.root() / "my-styles"
    lib = library_styles()
    old = mine / slug
    if slug in lib or (old.exists() and not update):
        raise StepError(f"mã \"{slug}\" đã có trong thư viện hoặc my-styles/: chọn mã khác"
                        + ("" if slug in lib else " (học lại phong cách này: thêm --update)"))
    if update and not old.exists():
        raise StepError(f"--update: chưa có my-styles/{slug}/ để học lại")
    if based_on not in lib and not (mine / based_on).exists():
        raise UsageError(f"--based-on \"{based_on}\" không phải phong cách thư viện hay phong cách riêng")
    d = refset.set_dir(name)
    style, proof = d / "style", d / "proof"
    for f in ("STYLE.md", "style.json", "EVIDENCE.md"):
        if not (style / f).exists():
            raise StepError(f"thiếu style/{f}: viết bản phong cách trước")
    cj = proof / "compare.json"
    if not cj.exists():
        raise StepError("chưa có khung chứng minh: chạy learn compare trước")
    comp = refset.read_json(cj)
    if not comp.get("pass") and not accept_proof:
        raise StepError("khung chứng minh chưa đạt ngưỡng. Chỉ lưu khi người dùng chấp nhận: thêm --accept-proof")
    ours = (d / comp.get("ours", "")).resolve() if comp.get("ours") else None
    if not ours or not ours.exists():
        raise StepError("không thấy ảnh khung chứng minh (ours) ghi trong compare.json")

    raster = [p for p in _proof_sources(proof) if p.suffix.lower() in RASTER_EXT]
    if raster:      # could be a frame of the reference video: only code-drawn sources go into the style
        raise StepError("proof/ có ảnh raster ngoài proof/out/ (có thể là khung của video gốc), không được lưu vào phong cách: "
                        + ", ".join(str(p.relative_to(d)) for p in raster) + ". Vẽ bằng code, hoặc chuyển vào proof/out/")
    skipped = sorted(p.relative_to(style) for p in style.rglob("*") if p.is_file() and str(p.relative_to(style)) not in STYLE_FILES
                     and p.suffix.lower() not in MEDIA_EXT)
    pkg_files = [style / f for f in STYLE_FILES if (style / f).is_file()] + _proof_sources(proof)
    every = [p for p in style.rglob("*") if p.is_file()] + _proof_sources(proof)   # media anywhere is refused, not skipped
    bad = [p for p in every if p.suffix.lower() in MEDIA_EXT or p.name == "words.json"
           or (p.parent != style and style not in p.parents and p.suffix.lower() not in SOURCE_EXT)]
    if bad:
        raise StepError("gói phong cách không được chứa media hay bản chép lời: " + ", ".join(str(p.relative_to(d)) for p in bad))
    viol = names.check_strings(name, [slug, en, cn]) + names.check_files(
        name, [p for p in pkg_files if p.suffix.lower() in {".md", ".json", ".html", ".js", ".mjs", ".txt", ".css"}])
    if viol:
        names.report(viol)
        raise StepError(f"{len(viol)} vi phạm tên hoặc câu thoại: sửa rồi lưu lại")

    if update and (old / "EVIDENCE.md").exists():          # specs/021 FR-008: the old corrections log is kept
        new_rows = set(corrections((style / "EVIDENCE.md").read_text(encoding="utf-8")))
        lost = [r for r in corrections((old / "EVIDENCE.md").read_text(encoding="utf-8")) if r not in new_rows]
        if lost:
            raise StepError("EVIDENCE.md mới làm mất dòng của nhật ký sửa cũ (phải giữ mọi dòng): " + lost[0][:120])
    tmp = mine / f".{slug}.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    (tmp / "measurements").mkdir(parents=True)
    shutil.copy2(style / "STYLE.md", tmp / "STYLE.md")
    shutil.copy2(style / "EVIDENCE.md", tmp / "EVIDENCE.md")
    for f in STYLE_FILES:
        if f not in ("STYLE.md", "EVIDENCE.md", "style.json") and (style / f).is_file():
            shutil.copy2(style / f, tmp / f)
    for rel in skipped:
        print(f"skipped: style/{rel}")
    summ = d / "profile" / "summary.json"
    s = scrub(refset.read_json(summ)) if summ.exists() else {}
    refset.write_json(tmp / "measurements" / "summary.json", s)
    meta = scrub(refset.read_json(style / "style.json"))
    created = datetime.date.today().isoformat()
    if update:
        try:
            created = refset.read_json(old / "style.json").get("created") or created
        except (OSError, ValueError):
            pass
        meta["updated"] = datetime.date.today().isoformat()
    meta.update({"slug": slug, "en": en, "cn": cn, "based_on": based_on, "borrows": meta.get("borrows", []),
                 "library_version": library_version(), "created": created,
                 "source": "learned",
                 "reference": {"videos": s.get("videos_measured"), "measured_seconds": s.get("measured_seconds"),
                               "formats": sorted((s.get("by_orientation") or {}).keys())}})
    refset.write_json(tmp / "style.json", meta)
    for p in _proof_sources(proof):
        dst = tmp / "styleframe" / p.relative_to(proof)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst)
    shutil.copy2(ours, tmp / "styleframe.jpg")
    refs = shot_refs(s)                                      # specs/021: the shot grammar the checks compare with
    if refs:
        refset.write_json(tmp / "shots.json", refs)
    if update:                                               # the demo film stays with the style (specs/021 FR-015)
        for f in KEEP_ON_UPDATE + tuple(f for f in TEMPLATE_FILES if not (tmp / f).exists()):
            src = old / f
            if src.is_dir():
                shutil.copytree(src, tmp / f)
            elif src.exists():
                shutil.copy2(src, tmp / f)
        gone = mine / f".{slug}.old"
        shutil.rmtree(gone, ignore_errors=True)
        old.rename(gone)
        tmp.rename(old)
        shutil.rmtree(gone, ignore_errors=True)
    else:
        tmp.rename(mine / slug)

    readme = mine / "README.md"
    title = en + (f" · {cn}" if cn else "")
    row = f"| {slug} | {title} | {based_on} | learned ({s.get('videos_measured', '?')} video) | {meta['created']} |\n"
    text = readme.read_text(encoding="utf-8") if readme.exists() else \
        "# Phong cách riêng\n\n| Slug | Tên | Dựa trên | Nguồn | Ngày lưu |\n|---|---|---|---|---|\n"
    text = text if text.endswith("\n") else text + "\n"
    lines = [ln for ln in text.splitlines(True) if not ln.startswith(f"| {slug} |")]
    readme.write_text("".join(lines) + row, encoding="utf-8")
    print(f"✓ đã lưu my-styles/{slug}/" + (" (học lại)" if update else "") + " và cập nhật danh mục my-styles/README.md")
    return 0


def _size(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else (p.stat().st_size if p.exists() else 0)


def clean(name: str, keep: bool = False) -> int:
    d = refset.set_dir(name).resolve()
    if keep:
        print(f"= giữ video tham chiếu trong references/{name}/ (không vào git). Xoá sau: sh bin/studio learn clean {name}")
        return 0
    targets = [d / "videos", d / "stems", d / "proof" / "compare.jpg"]   # stems: layers split by learn sfx (specs/037)
    targets += list((d / "profile").glob("*/words.json")) + list((d / "profile").glob("*/sheets"))
    # specs/021: full-size shot frames and the unlabelled sheets; the small labelled shot sheets and the labels stay
    targets += list((d / "profile").glob("*/shot-frames")) + list((d / "profile").glob("*/label-sheets")) + [d / "profile" / "pass2"]
    # frames taken from the reference videos (anything in proof/out that we did not draw ourselves)
    targets += [f for f in (d / "proof" / "out").glob("*") if not f.name.startswith("ours_")]
    total = 0
    for t in targets:
        t = t.resolve()
        if d not in t.parents:                # never touch anything outside this set
            continue
        if t.exists():
            total += _size(t)
            shutil.rmtree(t) if t.is_dir() else t.unlink()
            print(f"− {t.relative_to(d)}")
    data = refset.load(name)
    for v in data["videos"]:
        for k in ("origin", "source_id", "title", "channel", "handle", "src_name", "src_size"):
            v.pop(k, None)
    data["source"]["inputs"] = []
    data["media_removed"] = datetime.date.today().isoformat()
    refset.save(name, data)
    print(f"✓ đã xoá {total / 1e6:.1f} MB media và bản chép lời của bộ {name}; giữ số liệu đo.")
    return 0
