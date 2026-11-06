"""Whole-set summary: median / min / max per metric, by orientation (data-model.md: SetSummary)."""
import numpy as np

from . import color, refset

METRICS = {
    "luma_p50": lambda p: p["luma"]["p50"],
    "contrast_p50": lambda p: p["contrast"]["p50"],
    "sat_p50": lambda p: p["sat"]["p50"],
    "dark_p50": lambda p: p["dark"]["p50"],
    "bright_p50": lambda p: p["bright"]["p50"],
    "luma_p2": lambda p: p["luma"]["p2"],
    "luma_p98": lambda p: p["luma"]["p98"],
    "still_ratio": lambda p: p["still_ratio"],
    "motion720_p50": lambda p: p["motion_720"]["p50"],
    "motion720_p90": lambda p: p["motion_720"]["p90"],
    "shot_len_median": lambda p: p["shot_len"]["median"],
    "cuts_per_min": lambda p: p["cuts_per_min"],
    "flashes_per_min": lambda p: len(p["flashes"]) / max(sum(b - a for a, b in p["segments"]), 1e-6) * 60,
    "lufs": lambda p: (p["audio"] or {}).get("lufs"),
    "lra": lambda p: (p["audio"] or {}).get("lra"),
    "silence_per_min": lambda p: ((p["audio"] or {}).get("silence_total") or 0) / max(sum(b - a for a, b in p["segments"]), 1e-6) * 60 if p["audio"] else None,
    "first_voice_t": lambda p: (p["speech"] or {}).get("first_word_t") if p.get("speech") else (p["audio"] or {}).get("first_voice_t"),
    "speech_rate": lambda p: (p["speech"] or {}).get("rate") if p.get("speech") else None,
}


def stat(values) -> dict:
    v = [x for x in values if x is not None]
    if not v:
        return {"median": None, "min": None, "max": None, "n": 0}
    return {"median": round(float(np.median(v)), 4), "min": round(float(min(v)), 4),
            "max": round(float(max(v)), 4), "n": len(v)}


def set_palette(profiles) -> list:
    """Merge every video's palette, weighted by share, into one set palette."""
    pts, w, hexes = [], [], []
    for p in profiles:
        for c in p["palette"]:
            pts.append(c["lab"]); w.append(c["share"]); hexes.append(c["hex"])
    if not pts:
        return []
    groups = []
    for lab, share, hx in sorted(zip(pts, w, hexes), key=lambda z: -z[1]):
        for g in groups:
            if color.delta_e(g["lab"], lab) < 10:
                g["share"] += share
                break
        else:
            groups.append({"lab": lab, "share": share, "hex": hx})
    total = sum(g["share"] for g in groups)
    groups.sort(key=lambda g: -g["share"])
    return [{"hex": g["hex"], "lab": g["lab"], "share": round(g["share"] / total, 4)} for g in groups[:8]]


def build(name: str) -> dict:
    data = refset.load(name)
    d = refset.set_dir(name)
    profs = []
    for v in data["videos"]:
        f = d / "profile" / v["id"] / "video.json"
        if v.get("state") in ("measured", "transcribed") and f.exists():
            profs.append(refset.read_json(f))
    by = {}
    for o in sorted({p["orientation"] for p in profs}):
        group = [p for p in profs if p["orientation"] == o]
        by[o] = {"videos": len(group), "metrics": {k: stat(fn(p) for p in group) for k, fn in METRICS.items()},
                 "palette": set_palette(group)}
    disp = []
    for k, fn in METRICS.items():
        v = [x for x in (fn(p) for p in profs) if x is not None]
        if len(v) >= 3:
            med = np.median(v)
            mad = np.median(np.abs(np.array(v) - med))
            if mad > 0 and (max(v) - min(v)) > 3 * mad * 1.4826 * 2:
                disp.append(k)
    s = {
        "schema": refset.SCHEMA, "set": name, "videos_measured": len(profs),
        "measured_seconds": round(sum(sum(b - a for a, b in p["segments"]) for p in profs), 2),
        "by_orientation": by,
        "majority_orientation": max(by, key=lambda o: by[o]["videos"]) if by else None,
        "dispersion_warnings": disp,
        "skipped": [{"id": v["id"], "reason": v.get("skip_reason", "")} for v in data["videos"] if v.get("state") == "skipped"],
        "low_count_warning": len(profs) < 5,
    }
    refset.write_json(d / "profile" / "summary.json", s)
    (d / "profile" / "summary.md").write_text(to_markdown(s), encoding="utf-8")
    return s


def to_markdown(s: dict) -> str:
    out = [f"# Hồ sơ đo: {s['set']}", "",
           f"Video đã đo: {s['videos_measured']} · tổng thời lượng đo: {s['measured_seconds']} s · định dạng chính: {s['majority_orientation']}", ""]
    if s["low_count_warning"]:
        out += ["⚠️ Dưới 5 video: kết luận kém tin cậy.", ""]
    if s["dispersion_warnings"]:
        out += ["⚠️ Phân tán lớn (bộ có thể không đồng nhất): " + ", ".join(s["dispersion_warnings"]), ""]
    for o, g in s["by_orientation"].items():
        out += [f"## {o} ({g['videos']} video)", "", "| Chỉ số | Trung vị | Thấp nhất | Cao nhất |", "|---|---|---|---|"]
        for k, m in g["metrics"].items():
            out.append(f"| {k} | {m['median']} | {m['min']} | {m['max']} |")
        out += ["", "Bảng màu: " + " ".join(f"{c['hex']} ({c['share']:.0%})" for c in g["palette"]), ""]
    if s["skipped"]:
        out += ["## Bỏ qua", ""] + [f"- {x['id']}: {x['reason']}" for x in s["skipped"]]
    return "\n".join(out) + "\n"
