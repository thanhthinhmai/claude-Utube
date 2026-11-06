"""Compare the proof frame drawn in code with a reference frame (research.md §11, SC-004)."""
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import color, refset

LIMITS = {"luma_diff": 0.05, "sat_median_diff": 0.08, "dark_diff_pp": 5.0}
MATCH_DE = 15.0


def _load(path: Path) -> np.ndarray:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    return np.asarray(im.resize((320, max(2, round(h * 320 / w))), Image.BILINEAR))


def _stats(a: np.ndarray) -> dict:
    lum, _, sat, dark, _ = color.frame_stats(a)
    rng = np.random.default_rng(3)
    pal, _ = color.palette(color.sample_pixels(a, 6000, rng))
    return {"luma": lum, "sat": sat, "dark": dark, "palette": pal}


def matched(p1: list, p2: list) -> int:
    """Greedy pairing of two palettes; count pairs closer than ΔE76 15."""
    pairs = sorted((color.delta_e(a["lab"], b["lab"]), i, j) for i, a in enumerate(p1) for j, b in enumerate(p2))
    used_i, used_j, n = set(), set(), 0
    for d, i, j in pairs:
        if d < MATCH_DE and i not in used_i and j not in used_j:
            used_i.add(i); used_j.add(j); n += 1
    return n


def compare(ref: Path, ours: Path) -> dict:
    r, o = _stats(_load(ref)), _stats(_load(ours))
    need = min(4, len(r["palette"]))
    res = {
        "luma_diff": round(abs(r["luma"] - o["luma"]), 4),
        "sat_median_diff": round(abs(r["sat"] - o["sat"]), 4),
        "dark_diff_pp": round(abs(r["dark"] - o["dark"]) * 100, 2),
        "palette_matched": matched(r["palette"], o["palette"]),
        "palette_needed": need,
        "ref_palette": [c["hex"] for c in r["palette"]], "our_palette": [c["hex"] for c in o["palette"]],
    }
    res["pass"] = (res["luma_diff"] <= LIMITS["luma_diff"] and res["sat_median_diff"] <= LIMITS["sat_median_diff"]
                   and res["dark_diff_pp"] <= LIMITS["dark_diff_pp"] and res["palette_matched"] >= need)
    return res


def sheet(ref: Path, ours: Path, res: dict, out: Path) -> None:
    a, b = Image.open(ref).convert("RGB"), Image.open(ours).convert("RGB")
    H = 540
    a = a.resize((max(1, round(a.width * H / a.height)), H))
    b = b.resize((max(1, round(b.width * H / b.height)), H))
    W = a.width + b.width + 20
    img = Image.new("RGB", (W, H + 150), (24, 24, 24))
    img.paste(a, (0, 0)); img.paste(b, (a.width + 20, 0))
    d = ImageDraw.Draw(img)
    d.text((8, H + 8), "REFERENCE (left)  |  OURS (right)", fill=(230, 230, 230))
    rows = [("luma diff", res["luma_diff"], f"<= {LIMITS['luma_diff']}"),
            ("saturation diff", res["sat_median_diff"], f"<= {LIMITS['sat_median_diff']}"),
            ("very dark diff (pp)", res["dark_diff_pp"], f"<= {LIMITS['dark_diff_pp']}"),
            ("palette matched", res["palette_matched"], f">= {res['palette_needed']}")]
    for k, (n, v, lim) in enumerate(rows):
        d.text((8, H + 30 + 18 * k), f"{n:22s} {v!s:8s} {lim}", fill=(230, 230, 230))
    for k, (hx_r, hx_o) in enumerate(zip(res["ref_palette"] + [None] * 6, res["our_palette"] + [None] * 6)):
        if k >= 6:
            break
        for col, hx in ((W // 2, hx_r), (W // 2 + 200, hx_o)):
            if hx:
                d.rectangle([col + k * 28, H + 40, col + k * 28 + 24, H + 64], fill=hx)
    d.text((8, H + 128), "PASS" if res["pass"] else "NOT YET", fill=(120, 230, 120) if res["pass"] else (240, 120, 100))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=90)


def cli(name: str, ref: str, ours: str, rnd: int = 1) -> int:
    d = refset.set_dir(name)
    ref_p, ours_p = Path(ref).resolve(), Path(ours).resolve()
    for p in (ref_p, ours_p):
        if not p.exists():
            raise refset.UsageError(f"không thấy ảnh: {p}")
    res = compare(ref_p, ours_p)
    rel = lambda p: os.path.relpath(p, d) if str(p).startswith(str(d)) else str(p)  # noqa: E731
    res.update(ref=rel(ref_p), ours=rel(ours_p), round=rnd)
    refset.write_json(d / "proof" / "compare.json", res)
    sheet(ref_p, ours_p, res, d / "proof" / "compare.jpg")
    print(f"Vòng {rnd}: luma Δ {res['luma_diff']} · bão hoà Δ {res['sat_median_diff']} · "
          f"rất tối Δ {res['dark_diff_pp']} điểm % · màu khớp {res['palette_matched']}/{res['palette_needed']}")
    print("✓ đạt ngưỡng SC-004" if res["pass"] else "✗ chưa đạt ngưỡng SC-004")
    print(f"Ảnh ghép: {d / 'proof' / 'compare.jpg'}")
    return 0 if res["pass"] else 1
