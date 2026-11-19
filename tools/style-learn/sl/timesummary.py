"""Time measures of a reference set gathered for the template (specs/023 T026; data-model.md craft-summary.json).

Camera and acting come from the 3D films only (look rules, EVIDENCE.md corrections #15); transitions, reading rhythm,
sound and the beat recipes use all films. Acting is read on still-camera shots only: when the camera moves through a
3D set, parallax leaves a residue that the flat camera model cannot remove (2026-11-17, v01)."""
import json
from collections import Counter

import numpy as np

from . import refset

FLAT_FILMS = ("v03", "v08")
BEATS = ["hook", "explain", "benefit", "scale", "cost", "crisis", "ending", "sting", "end-card"]
RISE_MAX = 1.5            # spans up to this long count as one gesture (rise, then hold)


def _q(xs, ps=(25, 50, 75), nd=3):
    xs = [x for x in xs if x is not None]
    return [round(float(v), nd) for v in np.percentile(xs, ps)] if xs else None


def _load(name, vid, fname):
    f = refset.profile_dir(name, vid) / fname
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def beats_file(name):
    return refset.set_dir(name) / "profile" / "beats.json"


def check_beats(name) -> list:
    """Problems of profile/beats.json: names, order, contiguous from 0 to the end of each video."""
    f = beats_file(name)
    if not f.exists():
        return [f"chưa có {f.relative_to(refset.root())}"]
    data = refset.load(name)
    dur = {v["id"]: float(v.get("duration") or 0) for v in data["videos"]}
    out = []
    for item in json.loads(f.read_text(encoding="utf-8")):
        vid, bs = item.get("video"), item.get("beats") or []
        if vid not in dur:
            out.append(f"{vid}: không có trong bộ")
            continue
        names = [b[0] for b in bs]
        bad = [n for n in names if n not in BEATS]
        if bad:
            out.append(f"{vid}: tên nhịp lạ {bad}")
        order = [BEATS.index(n) for n in names if n in BEATS]
        if order != sorted(order) or len(set(names)) != len(names):
            out.append(f"{vid}: nhịp sai thứ tự hoặc lặp")
        if not bs or abs(bs[0][1]) > 0.05:
            out.append(f"{vid}: nhịp đầu phải bắt đầu ở 0")
        for a, b in zip(bs, bs[1:]):
            if abs(a[2] - b[1]) > 0.05:
                out.append(f"{vid}: {a[0]} kết thúc {a[2]} nhưng {b[0]} bắt đầu {b[1]}")
        for b in bs:
            if b[2] - b[1] <= 0:
                out.append(f"{vid}: nhịp {b[0]} dài 0")
        if bs and abs(bs[-1][2] - dur[vid]) > 1.0:
            out.append(f"{vid}: nhịp cuối kết thúc {bs[-1][2]}, video dài {dur[vid]:.1f}")
    return out


def beat_of(beats: list, t: float):
    for n, a, b in beats:
        if a <= t < b:
            return n
    return None


def build(name: str) -> dict:
    data = refset.load(name)
    vids = [v["id"] for v in data["videos"]]
    craft = {v: _load(name, v, "craft.json") for v in vids}
    sound = {v: _load(name, v, "sound.json") for v in vids}
    beats = {b["video"]: b["beats"] for b in (json.loads(beats_file(name).read_text(encoding="utf-8"))
                                               if beats_file(name).exists() else [])}
    look = [v for v in vids if craft[v] and v not in FLAT_FILMS]
    allv = [v for v in vids if craft[v]]

    # ---------------- camera (3D films)
    per_film_still, per_film_shift = [], []
    cam_time = Counter()
    by_scale = {}
    acting, none_n, rises = [], 0, []
    for v in look:
        sh = craft[v]["shots"]
        dur = sum(s["t1"] - s["t0"] for s in sh) or 1
        per_film_still.append(sum(s["t1"] - s["t0"] for s in sh if s["cam"]["type"] == "still") / dur)
        per_film_shift.append(sum(s["t1"] - s["t0"] for s in sh if s["cam"]["px_s"] < 4) / dur)
        for s in sh:
            cam_time[s["cam"]["type"]] += s["t1"] - s["t0"]
            sc = s.get("scale")
            if sc in (None, "short", "unknown"):
                continue
            b = by_scale.setdefault(sc, {"n": 0, "moving": 0, "push": 0, "drift_px_s": [], "zoom": []})
            b["n"] += 1
            t = s["cam"]["type"]
            b["moving"] += t != "still"
            b["push"] += t == "push"
            if t in ("drift-h", "drift-v", "follow"):
                b["drift_px_s"].append(s["cam"]["px_s"])
            if t in ("push", "pull"):
                b["zoom"].append(abs(s["cam"]["zoom_pct_s"]))
            if s.get("person") and t == "still" and s["t1"] - s["t0"] >= 1.0:
                acting.append(s["inner"]["active_share"])
                none_n += not s["inner"]["spans"]
                rises += [r for r in s["inner"]["rise_s"] if r <= RISE_MAX]
    tot = sum(cam_time.values()) or 1
    scale_out = {sc: {"n": b["n"], "moving": round(b["moving"] / b["n"], 3), "push": round(b["push"] / b["n"], 3),
                      "drift_px_s": _q(b["drift_px_s"], (25, 75)), "zoom_pct_s": _q(b["zoom"], (25, 75))}
                 for sc, b in by_scale.items()}
    summ = refset.read_json(refset.set_dir(name) / "profile" / "summary.json")
    m720 = (summ.get("by_orientation", {}).get("landscape", {}).get("metrics", {}).get("motion720_p50") or {})
    motion = {
        "films": look,
        "still_ratio": [round(min(per_film_still), 3), round(max(per_film_still), 3)] if per_film_still else None,
        "still_ratio_p50": round(float(np.median(per_film_still)), 3) if per_film_still else None,
        "shift_still_ratio": [round(min(per_film_shift), 3), round(max(per_film_shift), 3)] if per_film_shift else None,
        "cam_time": {k: round(v / tot, 3) for k, v in cam_time.most_common()},
        "by_scale": scale_out,
        "person_still_cam": {"n": len(acting), "active_share": _q(acting, (10, 25, 50, 75)),
                             "none_share": round(none_n / len(acting), 3) if acting else None,
                             "rise_s": _q(rises)},
        "motion720_p50": [m720.get("min"), m720.get("max")] if m720 else None,
    }

    # ---------------- transitions (all films)
    tr = Counter()
    tdur = {}
    for v in allv:
        for s in craft[v]["shots"]:
            t = s.get("trans_in")
            if t:
                tr[t["type"]] += 1
                if t["type"] != "cut":
                    tdur.setdefault(t["type"], []).append(t["dur"])
    n_tr = sum(tr.values()) or 1
    transitions = {"share": {k: round(c / n_tr, 4) for k, c in tr.most_common()}, "count": dict(tr),
                   "dur_s": {k: _q(v, (25, 50, 75)) for k, v in tdur.items()},
                   "fade_per_film": round(tr.get("fade", 0) / max(1, len(allv)), 2)}

    # ---------------- voice and sound (all films)
    pool = {k: [] for k in ("pause_in", "pause_sent", "pause_para", "pre_number")}
    wpm, sfx_pm, mus_on, mus_lv, tempos = [], [], [], [], []
    for v in vids:
        s = sound[v]
        if not s:
            continue
        for k in pool:
            pool[k] += s["speech"][k]
        wpm += [w[1] for w in s["speech"]["wpm_10s"]]
        sfx_pm.append(s["sfx"]["per_min"])
        for w in s["music"]["windows"]:
            if w[2] is not None:
                mus_on.append(bool(w[2]))
                if w[2] and w[3] is not None:
                    mus_lv.append(w[3])
        tempos.append([v, s["music"]["tempo"], s["music"]["tempo_conf"]])
    voice = {k: _q(x) for k, x in pool.items()}
    voice["wpm"] = _q(wpm, (10, 50, 90), 1)
    sound_out = {"sfx_per_min": _q(sfx_pm, (0, 50, 100), 2), "music_share": round(float(np.mean(mus_on)), 3) if mus_on else None,
                 "music_under_voice_db": _q(mus_lv, (25, 50, 75), 1), "tempo": tempos}

    # ---------------- beats (all films with beats)
    rec = {}
    for v, bs in beats.items():
        if not craft.get(v):
            continue
        sh = craft[v]["shots"]
        snd = sound.get(v) or {}
        for i, s in enumerate(sh):
            b = beat_of(bs, (s["t0"] + s["t1"]) / 2)
            if not b:
                continue
            r = rec.setdefault(b, {"shot_s": [], "scales": [], "moving": [], "acting": [], "trans": Counter(),
                                   "insert": [], "sfx": 0, "secs": 0.0, "wpm": [], "music": [], "level": []})
            r["shot_s"].append(s["t1"] - s["t0"])
            r["scales"].append(s.get("scale") or "?")
            r["moving"].append(s["cam"]["type"] != "still")
            r["insert"].append(s.get("scale") == "insert")
            if s.get("person") and s["cam"]["type"] == "still":
                r["acting"].append(bool(s["inner"]["spans"]))
            if s.get("trans_in"):
                r["trans"][s["trans_in"]["type"]] += 1
        for n, a, b2 in bs:
            r = rec.setdefault(n, {"shot_s": [], "scales": [], "moving": [], "acting": [], "trans": Counter(),
                                   "insert": [], "sfx": 0, "secs": 0.0, "wpm": [], "music": [], "level": []})
            r["secs"] += b2 - a
            if snd:
                r["sfx"] += sum(1 for o in snd["sfx"]["onsets"] if a <= o < b2)
                r["wpm"] += [w[1] for w in snd["speech"]["wpm_10s"] if a <= w[0] < b2]
                for w in snd["music"]["windows"]:
                    if a <= w[0] < b2 and w[2] is not None:
                        r["music"].append(bool(w[2]))
                        if w[2] and w[3] is not None:
                            r["level"].append(w[3])
    beats_out = {}
    for b in BEATS:
        r = rec.get(b)
        if not r or not r["shot_s"]:
            continue
        tri = Counter(" → ".join(r["scales"][i:i + 3]) for i in range(len(r["scales"]) - 2))
        beats_out[b] = {"shots": len(r["shot_s"]), "shot_s": _q(r["shot_s"], (25, 75), 2),
                        "top_scales": [t for t, _ in tri.most_common(3)],
                        "cam_moving": round(float(np.mean(r["moving"])), 3),
                        "acting": round(float(np.mean(r["acting"])), 3) if r["acting"] else None,
                        "insert_share": round(float(np.mean(r["insert"])), 3),
                        "trans": {k: c for k, c in r["trans"].items() if k != "cut"},
                        "sfx_per_min": round(r["sfx"] / max(r["secs"] / 60, 1e-6), 2),
                        "wpm": _q(r["wpm"], (50,), 0),
                        "music": round(float(np.mean(r["music"])), 3) if r["music"] else None,
                        "music_db": _q(r["level"], (50,), 1)}
    return {"motion": motion, "transitions": transitions, "voice": voice, "sound": sound_out, "beats": beats_out}
