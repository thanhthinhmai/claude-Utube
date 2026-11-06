"""Measure one video in a single pass over its frames, and a whole reference set (data-model.md: VideoProfile)."""
import csv
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np

from . import audio, color, motion, probe, refset
from .frames import WIDTH, iter_frames
from .sheets import SheetWriter

COLS = ["i", "t", "dx", "dy", "motion", "motion_ok", "hist_d", "cut", "flash",
        "luma", "contrast", "sat", "dark", "bright"]


def pct(values) -> dict:
    v = np.asarray(values, float)
    if v.size == 0:
        return {"p2": None, "p50": None, "p98": None}
    return {k: round(float(np.percentile(v, q)), 4) for k, q in (("p2", 2), ("p50", 50), ("p98", 98))}


def analyze(path: Path, max_seconds: float = 180, sheet_dir: Path = None, vid: str = "v01", progress=None) -> dict:
    meta = probe.probe(path)
    segs = probe.segments(meta["duration"], max_seconds)
    h = probe.scaled_height(meta["width"], meta["height"], WIDTH)
    win = motion.window((h, WIDTH))
    sheets = SheetWriter(sheet_dir, vid, meta["fps"], meta["orientation"], h)
    rng = np.random.default_rng(7)
    rows, hists, lums, thumbs, starts, pix = [], [], [], [], set(), []
    prev_F, prev_h, prev_seg = None, None, None
    t0 = time.time()
    for i, (si, t, f) in enumerate(iter_frames(path, meta, segs)):
        F = motion.spectrum(motion.gray(f), win)
        hh = motion.hist(f)
        if si != prev_seg:
            starts.add(i)
            dx = dy = 0.0; ok = 0; d = 0.0
        else:
            dx, dy, peak = motion.shift(prev_F, F, (h, WIDTH))
            ok = int(peak >= motion.PEAK_OK)
            d = motion.hdist(prev_h, hh)
        lum, con, sat, dark, bright = color.frame_stats(f)
        rows.append({"i": i, "t": round(t, 4), "dx": round(dx, 4), "dy": round(dy, 4),
                     "motion": round(float(np.hypot(dx, dy)) / WIDTH, 6), "motion_ok": ok, "hist_d": round(d, 4),
                     "cut": 0, "flash": 0, "luma": round(lum, 4), "contrast": round(con, 4), "sat": round(sat, 4),
                     "dark": round(dark, 4), "bright": round(bright, 4)})
        hists.append(hh); lums.append(lum); thumbs.append(motion.thumb(f))
        if i % 10 == 0:
            pix.append(color.sample_pixels(f, 400, rng))
        sheets.add(f, t, si)
        prev_F, prev_h, prev_seg = F, hh, si
        if progress and i and i % 300 == 0:
            progress(i, time.time() - t0)
    sheets.flush()
    n = len(rows)
    if n == 0:
        raise refset.StepError("không đọc được khung nào")
    ev = motion.events(np.array([r["hist_d"] for r in rows]), np.array(hists), np.array(lums), np.array(thumbs), starts)
    for i in ev["cuts"]:
        rows[i]["cut"] = 1
    for i in ev["flashes"]:
        rows[i]["flash"] = 1
    ts = [r["t"] for r in rows]

    bounds = []                                          # shot lengths inside each segment
    for a, b in segs:
        inside = [ts[i] for i in ev["cuts"] if a <= ts[i] < b]
        pts = [a] + inside + [b]
        bounds += [pts[k + 1] - pts[k] for k in range(len(pts) - 1)]
    okrows = [r for r in rows if r["motion_ok"]]
    m720 = [r["motion"] * 720 for r in okrows]
    measured_s = sum(b - a for a, b in segs)
    pal, note = color.palette(np.concatenate(pix))
    prof = {
        "schema": refset.SCHEMA, "width": meta["width"], "height": meta["height"], "fps": meta["fps"],
        "duration": meta["duration"], "orientation": meta["orientation"], "segments": segs,
        "frames_expected": probe.expected_frames(meta, segs), "frames_measured": n,
        "cuts": [ts[i] for i in ev["cuts"]], "flashes": [ts[i] for i in ev["flashes"]],
        "soft_transitions": [[ts[a], ts[b]] for a, b in ev["soft"]],
        "shot_len": {"median": round(float(np.median(bounds)), 3), "min": round(min(bounds), 3),
                     "max": round(max(bounds), 3)},
        "cuts_per_min": round(len(ev["cuts"]) / measured_s * 60, 3),
        "still_ratio": round(sum(v < motion.STILL_PX_720 for v in m720) / len(m720), 4) if m720 else None,
        "motion_720": {k: (round(float(np.percentile(m720, q)), 3) if m720 else None)
                       for k, q in (("p50", 50), ("p90", 90), ("max", 100))},
        **{k: pct([r[k] for r in rows]) for k in ("luma", "contrast", "sat", "dark", "bright")},
        "palette": pal,
        "audio": audio.analyze(path, meta, segs),
        "speech": None,
        "sheets": sheets.files,
    }
    if note:
        prof["palette_note"] = note
    return {"meta": meta, "rows": rows, "profile": prof}


def write_profile(out: Path, result: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "frames.csv.tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in result["rows"]:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})
    os.replace(tmp, out / "frames.csv")
    refset.write_json(out / "video.json", result["profile"])


def measure_set(name: str, only=None, log=print) -> list:
    data = refset.load(name)
    done = []
    for v in data["videos"]:
        if only and v["id"] not in only:
            continue
        path = refset.video_path(name, v)
        out = refset.profile_dir(name, v["id"])
        if not path.exists():
            v.update(state="skipped", skip_reason="không thấy file video")
            refset.save(name, data); continue
        sig = refset.source_sig(path)
        if v.get("state") in ("measured", "transcribed") and v.get("source_sig") == sig and (out / "video.json").exists():
            continue
        if v.get("state") == "skipped" and v.get("source_sig") == sig:
            continue
        log(f"… đo {v['id']} ({v['file']})")
        prog = lambda i, s: log(f"   {i} khung, {i / max(s, 1e-6):.0f} khung/giây")  # noqa: E731
        try:
            if (out / "sheets").exists():
                shutil.rmtree(out / "sheets")
            r = analyze(path, data.get("max_seconds", 180), out / "sheets", v["id"], prog)
            write_profile(out, r)
            m = r["meta"]
            v.update({k: m[k] for k in ("width", "height", "fps", "duration", "orientation")},
                     segments=r["profile"]["segments"], state="measured", source_sig=sig)
            v.pop("skip_reason", None)
            done.append(v["id"])
            log(f"✓ {v['id']}: {r['profile']['frames_measured']}/{r['profile']['frames_expected']} khung")
        except refset.StepError as e:
            v.update(state="skipped", skip_reason=str(e), source_sig=sig)
            log(f"✗ {v['id']} bỏ qua: {e}")
        refset.save(name, data)                     # after every video, so an interrupted run resumes
    return done


if __name__ == "__main__":
    print(analyze(Path(sys.argv[1]))["profile"])
