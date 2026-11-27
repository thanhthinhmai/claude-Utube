"""learn camera (specs/039 US1, research R1–R3): the reference-shot library of a set and its camera summary.

camera_set() measures every shot of every video with a shot list (camtrack), joins the shot labels (size, camera
height, lens: specs/021, 038) and the craft labels (card, people, action, outdoor, prop, subject box: specs/027, 039),
takes the transition into the shot from craft.transition, cuts two 360 px evidence frames per shot while the video is
here, and writes references/<set>/profile/<vid>/camera.json. summary() is the camera summary per shot size that
`learn save` writes into my-styles/<style>/camera.json and `camera suggest` reads."""
import datetime
import hashlib
import json

import numpy as np

from . import camtrack, craft, refset, shots

MEASURE = "camtrack/1"
EVIDENCE_W = 360
MAX_EVIDENCE = 150
SIZES = ("ecu", "cu", "med", "wide", "huge", "insert")
THIN = 5


class CameraError(refset.StepError):
    pass


def camera_file(name: str, vid: str):
    return refset.profile_dir(name, vid) / "camera.json"


def _sig(rows: list) -> str:
    return hashlib.sha256(json.dumps([[r["id"], r["t0"], r["t1"]] for r in rows]).encode()).hexdigest()[:12]


def _craft_labels(name: str) -> dict:
    f = refset.set_dir(name) / "profile" / "craft-labels.json"
    if not f.exists():
        return {}
    return {vid: c.get("labels") or {} for vid, c in (refset.read_json(f).get("videos") or {}).items()}


def composition(box):
    """subject box [x0, y0, x1, y1] % → (x, y, h, headroom) %, or Nones."""
    if not box:
        return None, None, None, None
    x0, y0, x1, y1 = box
    return round((x0 + x1) / 2, 1), round((y0 + y1) / 2, 1), round(y1 - y0, 1), round(y0, 1)


def _evidence(path, vid: str, row: dict, t: float, tag: str, prof) -> str:
    from PIL import Image
    w, h = EVIDENCE_W, round(EVIDENCE_W * 9 / 16)
    f = craft._ffmpeg(["-ss", f"{max(0.0, t):.3f}", "-i", str(path), "-frames:v", "1", "-vf", f"scale={w}:{h}",
                       "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], w, h, 3)
    if not len(f):
        return None
    rel = f"camera/{row['id']}-{tag}.jpg"
    out = prof / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(f[0].astype(np.uint8)).save(out, quality=85)
    return rel


def measure_row(path, vid: str, row: dict, labels: dict, prof, cut_evidence: bool = True, trans_in=None,
                trans_out=None) -> dict:
    """One Reference shot (data-model) for a shots.json row. trans_in/out: craft.transition() at its two ends."""
    if trans_in is None and float(row["t0"]) > 0:
        trans_in = craft.transition(path, float(row["t0"]))
    m = camtrack.measure(path, row["t0"], row["t1"], camtrack.trim_for(trans_in), camtrack.trim_for(trans_out))
    lab = labels.get(row["id"]) or {}
    sx, sy, sh, head = composition(lab.get("subject"))
    trans = trans_in["type"] if trans_in else None
    out = {"id": f"{vid}:{row['id']}", "t0": float(row["t0"]), "t1": float(row["t1"]), "dur": m["dur"],
           "size": row.get("scale"), "cam_height": row.get("cam_height"), "lens": row.get("lens"),
           "card": lab.get("card"), "people": lab.get("people"), "action": lab.get("action"),
           "outdoor": lab.get("outdoor"), "prop": lab.get("prop"), "subject": lab.get("subject"),
           "subject_x": sx, "subject_y": sy, "subject_h": sh, "headroom": head,
           "move": m["move"], "zoom_pct": m["zoom_pct"], "rate_pct_s": m["rate_pct_s"], "ease": m["ease"],
           "drift_px": m["drift_px"], "parallax_px": m["parallax_px"], "parallax": m["parallax"],
           "transition": trans, "reliable": m["reliable"], "why_unreliable": m["why_unreliable"]}
    if cut_evidence:
        a = craft.EDGE_TRIM
        ev = [_evidence(path, vid, row, float(row["t0"]) + a, "a", prof),
              _evidence(path, vid, row, float(row["t1"]) - a, "b", prof)]
        out["evidence"] = ev if all(ev) else None
    return out


def missing_labels(rows: list, labels: dict) -> list:
    """The commands still to run for the joined fields (left null meanwhile)."""
    need = []
    rows = [r for r in rows if not r.get("short")]          # short shots get no labels (specs/021, 027)
    if any(r.get("scale") is None for r in rows):
        need.append("learn label")
    if not labels or any(r["id"] not in labels for r in rows):
        need.append("learn craft-label")
    elif any("subject" not in (labels.get(r["id"]) or {}) for r in rows):
        need.append("learn craft-label (version 2: subject)")
    return need


def camera_set(name: str, videos=None, force: bool = False, log=print) -> dict:
    data = refset.load(name)
    labels = _craft_labels(name)
    done = {"videos": 0, "shots": 0, "skipped": 0, "need": set()}
    for v in data["videos"]:
        vid = v["id"]
        if videos and vid not in videos:
            continue
        sf = shots.shots_file(name, vid)
        if not sf.exists():
            log(f"· {vid}: no shot list (run: learn shots {name})")
            continue
        rows = [r for r in refset.read_json(sf)["shots"]]
        sig = _sig(rows)
        out_f = camera_file(name, vid)
        if out_f.exists() and not force and refset.read_json(out_f).get("sig") == sig:
            log(f"· {vid}: already measured")
            continue
        path = refset.video_path(name, v)
        if not path.exists():
            raise CameraError(f"{vid}: the video is gone; run: learn refetch {name}")
        need = missing_labels(rows, labels.get(vid) or {})
        done["need"].update(need)
        prof = refset.profile_dir(name, vid)
        out, skipped = [], []
        cuts = {}
        for r in rows:                                   # transition at each start, shared by the shot before
            if float(r["t0"]) > 0:
                try:
                    cuts[round(float(r["t0"]), 3)] = craft.transition(path, float(r["t0"]))
                except craft.CraftError:
                    pass
        for r in rows:
            try:
                out.append(measure_row(path, vid, r, labels.get(vid) or {}, prof,
                                       trans_in=cuts.get(round(float(r["t0"]), 3)),
                                       trans_out=cuts.get(round(float(r["t1"]), 3))))
            except (camtrack.TrackError, craft.CraftError) as e:
                skipped.append({"id": f"{vid}:{r['id']}", "reason": str(e)})
        doc = {"version": 1, "video": vid, "measured_at": datetime.date.today().isoformat(), "measure": MEASURE,
               "sig": sig, "shots": out, "skipped": skipped}
        refset.write_json(out_f, doc)
        cuts = [s for s in out if s["transition"]]
        log(f"{vid}: {len(out)} shots, {len(skipped)} skipped, parallax {sum(1 for s in out if s['parallax'])}/{len(out)}, "
            f"cut {sum(1 for s in cuts if s['transition'] == 'cut')}/{len(cuts)}")
        done["videos"] += 1
        done["shots"] += len(out)
        done["skipped"] += len(skipped)
    done["need"] = sorted(done["need"])
    return done


def library(name: str) -> list:
    """Every Reference shot of the set (all measured videos), in video and time order."""
    out = []
    for v in refset.load(name)["videos"]:
        f = camera_file(name, v["id"])
        if f.exists():
            out += refset.read_json(f)["shots"]
    return out


def _q(vals):
    v = [x for x in vals if x is not None]
    if not v:
        return None
    return [round(float(np.percentile(v, p)), 3) for p in (25, 50, 75)]


def summary(rows: list) -> dict:
    """Camera summary (data-model "Camera summary") over the reliable shots."""
    rel = [r for r in rows if r.get("reliable")]
    trans = [r["transition"] for r in rows if r.get("transition")]
    share = {t: round(trans.count(t) / len(trans), 3) for t in sorted(set(trans))} if trans else {}
    by = {}
    for size in SIZES:
        rs = [r for r in rel if r.get("size") == size]
        if not rs:
            continue
        n = len(rs)
        moving = [r for r in rs if r["move"] != "static"]
        by[size] = {"n": n, "thin": n < THIN,
                    "dur": _q([r["dur"] for r in rs]),
                    "zoom_pct": _q([abs(r["zoom_pct"]) for r in rs if r["move"] in ("push", "pull")]),
                    "rate_pct_s": _q([abs(r["rate_pct_s"]) for r in rs if r["move"] in ("push", "pull")]),
                    "push_share": round(sum(r["move"] == "push" for r in rs) / n, 3),
                    "pull_share": round(sum(r["move"] == "pull" for r in rs) / n, 3),
                    "pan_share": round(sum(r["move"] == "pan" for r in rs) / n, 3),
                    "static_share": round(sum(r["move"] == "static" for r in rs) / n, 3),
                    "drift_px": _q([float(np.hypot(*r["drift_px"])) for r in moving]),
                    "ease_q": [x for x in (np.median([r["ease"][i] for r in moving if r.get("ease")]).round(3).item()
                                           if any(r.get("ease") for r in moving) else None for i in range(3))]
                    if any(r.get("ease") for r in moving) else None,
                    "subject_h": _q([r.get("subject_h") for r in rs]),
                    "subject_x": _q([r.get("subject_x") for r in rs]),
                    "subject_y": _q([r.get("subject_y") for r in rs]),
                    "headroom": _q([r.get("headroom") for r in rs])}
    return {"transition_main": max(share, key=share.get) if share else "cut", "transition_share": share,
            "parallax_share": round(sum(1 for r in rel if r["parallax"]) / len(rel), 3) if rel else 0.0,
            "shots_n": len(rows), "reliable_n": len(rel), "by_size": by}


def pick_evidence(rows: list, k: int = MAX_EVIDENCE) -> list:
    """Ids of at most k shots that keep their evidence frames in a style: round-robin over (size × move) groups,
    reliable shots first, then the longest."""
    groups = {}
    for r in rows:
        if r.get("evidence"):
            groups.setdefault((r.get("size"), r.get("move")), []).append(r)
    for g in groups.values():
        g.sort(key=lambda r: (not r.get("reliable"), -r["dur"]))
    out, keys = [], sorted(groups, key=lambda x: (str(x[0]), str(x[1])))
    while len(out) < k and any(groups[x] for x in keys):
        for x in keys:
            if groups[x] and len(out) < k:
                out.append(groups[x].pop(0)["id"])
    return out


def style_doc(name: str) -> dict:
    """my-styles/<style>/camera.json for this set: summary + shots (evidence only on the picked ones)."""
    rows = library(name)
    keep = set(pick_evidence(rows))
    shots_out = []
    for r in rows:
        r = dict(r)
        if r["id"] in keep and r.get("evidence"):
            vid, sid = r["id"].split(":")
            r["evidence"] = [f"camera/{vid}-{sid}-{t}.jpg" for t in ("a", "b")]
        else:
            r["evidence"] = None
        shots_out.append(r)
    return {"version": 1, "source_set": name, "measure": MEASURE, **summary(rows), "shots": shots_out}
