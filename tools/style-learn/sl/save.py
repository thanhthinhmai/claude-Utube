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


def save(name: str, slug: str, en: str, cn: str, based_on: str, accept_proof: bool = False) -> int:
    refset.check_slug(slug, "mã phong cách")
    mine = refset.root() / "my-styles"
    lib = library_styles()
    if slug in lib or (mine / slug).exists():
        raise StepError(f"mã \"{slug}\" đã có trong thư viện hoặc my-styles/: chọn mã khác")
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
    pkg_files = [p for p in style.rglob("*") if p.is_file()] + _proof_sources(proof)
    bad = [p for p in pkg_files if p.suffix.lower() in MEDIA_EXT or p.name == "words.json"
           or (p.parent != style and p.suffix.lower() not in SOURCE_EXT)]
    if bad:
        raise StepError("gói phong cách không được chứa media hay bản chép lời: " + ", ".join(str(p.relative_to(d)) for p in bad))
    viol = names.check_strings(name, [slug, en, cn]) + names.check_files(
        name, [p for p in pkg_files if p.suffix.lower() in {".md", ".json", ".html", ".js", ".mjs", ".txt", ".css"}])
    if viol:
        names.report(viol)
        raise StepError(f"{len(viol)} vi phạm tên hoặc câu thoại: sửa rồi lưu lại")

    tmp = mine / f".{slug}.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    (tmp / "measurements").mkdir(parents=True)
    shutil.copy2(style / "STYLE.md", tmp / "STYLE.md")
    shutil.copy2(style / "EVIDENCE.md", tmp / "EVIDENCE.md")
    for p in style.rglob("*"):
        rel = p.relative_to(style)
        if p.is_file() and str(rel) not in ("STYLE.md", "EVIDENCE.md", "style.json"):
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, tmp / rel)
    summ = d / "profile" / "summary.json"
    s = scrub(refset.read_json(summ)) if summ.exists() else {}
    refset.write_json(tmp / "measurements" / "summary.json", s)
    meta = scrub(refset.read_json(style / "style.json"))
    meta.update({"slug": slug, "en": en, "cn": cn, "based_on": based_on, "borrows": meta.get("borrows", []),
                 "library_version": library_version(), "created": datetime.date.today().isoformat(),
                 "source": "learned",
                 "reference": {"videos": s.get("videos_measured"), "measured_seconds": s.get("measured_seconds"),
                               "formats": sorted((s.get("by_orientation") or {}).keys())}})
    refset.write_json(tmp / "style.json", meta)
    for p in _proof_sources(proof):
        dst = tmp / "styleframe" / p.relative_to(proof)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst)
    shutil.copy2(ours, tmp / "styleframe.jpg")
    tmp.rename(mine / slug)

    readme = mine / "README.md"
    title = en + (f" · {cn}" if cn else "")
    row = f"| {slug} | {title} | {based_on} | learned ({s.get('videos_measured', '?')} video) | {meta['created']} |\n"
    text = readme.read_text(encoding="utf-8") if readme.exists() else \
        "# Phong cách riêng\n\n| Slug | Tên | Dựa trên | Nguồn | Ngày lưu |\n|---|---|---|---|---|\n"
    readme.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    with open(readme, "a", encoding="utf-8") as f:
        f.write(row)
    print(f"✓ đã lưu my-styles/{slug}/ và thêm vào danh mục my-styles/README.md")
    return 0


def _size(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else (p.stat().st_size if p.exists() else 0)


def clean(name: str, keep: bool = False) -> int:
    d = refset.set_dir(name).resolve()
    if keep:
        print(f"= giữ video tham chiếu trong references/{name}/ (không vào git). Xoá sau: sh bin/studio learn clean {name}")
        return 0
    targets = [d / "videos", d / "proof" / "compare.jpg"]
    targets += list((d / "profile").glob("*/words.json")) + list((d / "profile").glob("*/sheets"))
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
