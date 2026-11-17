"""Comparison sheets of the kit against the reference (specs/023 FR-009, research R9; `learn pairs`).

A sheet holds ≥ 3 rows "kit frame | reference frame of the same kind", with the component and optional measures.
For a moving component, a clip puts the kit's clip on the left and the reference strip (8 kept frames, played at the
shot's own pace) on the right; the reference side is built from kept frames, never cut from a video.
Sheets stay in references/<set>/pairs/ (outside git) and are never sent anywhere."""
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import refset, template

W, H, LAB = 480, 270, 20
MIN_PAIRS = 3


def font(size=14):
    """A font with Vietnamese marks when the system has one (the default bitmap font has none)."""
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def ref_image(name: str, ref: str) -> Image.Image:
    """A kept reference frame: a shot-sheet cell, a frame k of a strip, or an evidence frame."""
    prof = refset.set_dir(name) / "profile"
    if template.EV_SHEET.match(ref):
        return template.cell(name, ref)
    m = template.EV_STRIP.match(ref)
    if m:
        path, _, k = ref.partition("#")
        im = Image.open(prof / path).convert("RGB")
        fw = im.width // 8
        return im.crop((int(k) * fw, 0, (int(k) + 1) * fw, im.height))
    if template.EV_FILE.match(ref):
        return Image.open(prof / ref).convert("RGB")
    raise refset.UsageError(f"bằng chứng sai dạng: {ref}")


def sheet(name: str, batch: int, component: str, ours: list, refs: list, notes: str = "") -> Path:
    n = min(len(ours), len(refs))
    if n < MIN_PAIRS:
        raise refset.UsageError(f"bảng so cần ≥ {MIN_PAIRS} cặp (có {n})")
    head = 28 + (18 if notes else 0)
    im = Image.new("RGB", (2 * W + 12, head + n * (H + LAB + 6)), (14, 12, 20))
    d, fnt = ImageDraw.Draw(im), font(14)
    d.text((6, 6), f"Đợt {batch} · {component}   (trái: bộ dựng · phải: kênh mẫu cùng loại cảnh)", fill=(255, 230, 120), font=fnt)
    if notes:
        d.text((6, 26), notes, fill=(220, 220, 220), font=fnt)
    for i in range(n):
        y = head + i * (H + LAB + 6)
        a = Image.open(ours[i]).convert("RGB").resize((W, H))
        b = ref_image(name, refs[i]).resize((W, H))
        im.paste(a, (4, y + LAB)); im.paste(b, (W + 8, y + LAB))
        d.text((6, y + 3), Path(ours[i]).name, fill=(200, 200, 200), font=fnt)
        d.text((W + 10, y + 3), refs[i], fill=(200, 200, 200), font=fnt)
    out = refset.set_dir(name) / "pairs" / str(batch) / f"{component}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, quality=88)
    return out


def clip(name: str, batch: int, component: str, ours_mp4: str, ref_strip: str, ref_seconds: float = None) -> Path:
    """Side-by-side mp4: the kit's clip | the reference strip's 8 frames, each held 1/8 of the shot."""
    prof = refset.set_dir(name) / "profile"
    strip = prof / ref_strip.split("#")[0]
    if not strip.exists():
        raise refset.UsageError(f"không thấy dải khung {ref_strip}")
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", ours_mp4],
                               capture_output=True, text=True).stdout.strip() or 0)
    if dur <= 0:
        raise refset.UsageError(f"không đọc được đoạn {ours_mp4}")
    each = (ref_seconds or dur) / 8
    im = Image.open(strip).convert("RGB")
    fw = im.width // 8
    out = refset.set_dir(name) / "pairs" / str(batch) / f"{component}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        lines = []
        for k in range(8):
            f = Path(tmp) / f"r{k}.png"
            im.crop((k * fw, 0, (k + 1) * fw, im.height)).resize((640, 360)).save(f)
            lines += [f"file '{f}'", f"duration {each:.4f}"]
        lines.append(f"file '{Path(tmp) / 'r7.png'}'")
        (Path(tmp) / "list.txt").write_text("\n".join(lines) + "\n")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", ours_mp4, "-f", "concat", "-safe", "0", "-i", str(Path(tmp) / "list.txt"),
                        "-filter_complex",
                        "[0:v]scale=640:360,setsar=1,fps=30[a];[1:v]scale=640:360,setsar=1,fps=30,tpad=stop_mode=clone:stop_duration=30[b];"
                        "[a][b]hstack=inputs=2[v]", "-map", "[v]", "-t", f"{max(dur, ref_seconds or 0):.3f}",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)], check=True)
    return out


def cli(name, batch, component, ours, refs, notes="", clip_mp4=None, ref_strip=None, ref_seconds=None) -> int:
    out = sheet(name, batch, component, ours, refs, notes)
    print(f"✓ {out}")
    if clip_mp4:
        if not ref_strip:
            raise refset.UsageError("--clip cần --ref-strip vNN/strips/Sxxx.jpg")
        print(f"✓ {clip(name, batch, component, clip_mp4, ref_strip, ref_seconds)}")
    return 0
