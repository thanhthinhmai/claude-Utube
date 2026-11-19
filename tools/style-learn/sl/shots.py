"""Shot grammar of a reference set (specs/021 US1; research R2–R4; data-model ShotLabel, ShotGrammar).

`learn shots`: split each measured video into shots (ffmpeg scene score > 0.15), take the middle frame of every
shot at 960×540, measure its focus with the studio's shared measure (tools/filmcheck/focus.py), group shots into
places by a colour signature, and draw contact sheets of shots. `learn label`: the independent labeler
(tools/filmcheck/labeler.py) labels scale and angle from those sheets. The video is needed only for `learn shots`."""
import json
import random
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import refset

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))       # tools/: the shared focus measure and labeler
from filmcheck import focus, labeler  # noqa: E402

SCENE_T = 0.15          # ffmpeg scene score; dusk-hypothetical corrections #1: "scene > 0.15" matched the cuts seen by eye
MERGE_S = 0.3           # cuts closer than this are one cut
SHORT_S = 0.5           # shorter shots get no label
SET_D = 0.35            # colour grouping: only a first guess; the labeler's place names replace it (research R4, 2026-11-13)
CPM_RANGE = (16, 26)    # cuts per minute expected of the set (warn outside; dusk-hypothetical corrections #1)
COLS, PER, CW, CH, LAB = 6, 48, 200, 112, 18
SCALE_ORDER = labeler.ORDER


# ---------- cuts and frames ----------
def scene_cuts(path: Path, a: float, b: float) -> list:
    p = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(path),
                        "-vf", f"scale=320:-2,select='gt(scene,{SCENE_T})',metadata=print", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [a + float(x) for x in re.findall(r"pts_time:([\d.]+)", p.stderr)]


def detect(path: Path, segs: list, flashes=()) -> list:
    """[(t0, t1)] shots inside the measured segments."""
    out = []
    for a, b in segs:
        cuts = []
        for c in sorted(scene_cuts(path, a, b)):
            if any(abs(c - f) < 0.15 for f in flashes) or c - a < MERGE_S or b - c < MERGE_S:
                continue
            if cuts and c - cuts[-1] < MERGE_S:
                continue
            cuts.append(c)
        pts = [a, *cuts, b]
        out += [(round(x, 3), round(y, 3)) for x, y in zip(pts, pts[1:])]
    return out


def grab(path: Path, t: float, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1", "-vf",
                    "scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:(ow-iw)/2:(oh-ih)/2",
                    "-q:v", "3", str(out)], check=True)


# ---------- places ----------
def signature(img_path: Path) -> np.ndarray:
    im = Image.open(img_path).convert("RGB").resize((64, 36))
    a = np.asarray(im, np.float32) / 255
    q = np.minimum((a * 4).astype(int), 3)
    hist = np.bincount((q[..., 0] * 16 + q[..., 1] * 4 + q[..., 2]).ravel(), minlength=64).astype(np.float32)
    hist /= hist.sum()
    lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    regions = [lum[r * 12:(r + 1) * 12, c * 21:(c + 1) * 21].mean() for r in range(3) for c in range(3)]
    return np.concatenate([hist, np.array(regions, np.float32)])


def distance(x: np.ndarray, y: np.ndarray) -> float:
    return float(0.5 * np.abs(x[:64] - y[:64]).sum() + np.abs(x[64:] - y[64:]).mean())


def group(sigs: list, d_max: float = SET_D) -> list:
    """Single-link grouping: ["B1", "B2", …] in order of first appearance."""
    parent = list(range(len(sigs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in range(len(sigs)):
        for j in range(i):
            if distance(sigs[i], sigs[j]) < d_max:
                parent[find(i)] = find(j)
    names, out = {}, []
    for i in range(len(sigs)):
        r = find(i)
        names.setdefault(r, f"B{len(names) + 1}")
        out.append(names[r])
    return out


# ---------- sheets ----------
def caption(s: dict) -> str:
    t = s["id"]
    if s.get("scale"):
        t += f" · {s['scale'].upper()} · {s.get('angle', '?')}"
    return t


def draw_sheets(shots: list, frame_of, out_dir: Path, prefix: str, captions=True) -> list:
    """[(sheet path, [ids])]: 6 columns, ≤ 48 cells per sheet, each cell captioned (under 1280 px wide)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob(f"{prefix}_*.jpg"):
        f.unlink()
    groups = []
    for k in range(0, len(shots), PER):
        part = shots[k:k + PER]
        rows = (len(part) + COLS - 1) // COLS
        sheet = Image.new("RGB", (COLS * (CW + 6) + 6, rows * (CH + LAB + 6) + 6), (17, 17, 17))
        d = ImageDraw.Draw(sheet)
        for n, s in enumerate(part):
            x, y = 6 + (n % COLS) * (CW + 6), 6 + (n // COLS) * (CH + LAB + 6)
            sheet.paste(Image.open(frame_of(s)).convert("RGB").resize((CW, CH)), (x, y + LAB))
            d.text((x + 2, y + 3), caption(s) if captions else s["id"], fill=(255, 230, 120) if s.get("check") else (230, 230, 230))
        f = out_dir / f"{prefix}_{k // PER + 1}.jpg"
        sheet.save(f, quality=85)
        groups.append((f, [s["id"] for s in part]))
    return groups


# ---------- learn shots ----------
def shots_file(name: str, vid: str) -> Path:
    return refset.profile_dir(name, vid) / "shots.json"


def video_shots(name: str, v: dict, log=print) -> dict:
    prof = refset.profile_dir(name, v["id"])
    vj = refset.read_json(prof / "video.json")
    path = refset.video_path(name, v)
    if not path.exists():
        raise refset.StepError(f"{v['id']}: the video is not on this machine any more (learn shots runs before clean)")
    spans = detect(path, vj["segments"], vj.get("flashes") or [])
    rows, sigs = [], []
    for n, (t0, t1) in enumerate(spans, 1):
        sid = f"S{n:03d}"
        row = {"id": sid, "t0": t0, "t1": t1, "mid": round((t0 + t1) / 2, 3)}
        if t1 - t0 < SHORT_S:
            row["short"] = True
            rows.append(row)
            continue
        frame = prof / "shot-frames" / f"{sid}.jpg"
        grab(path, row["mid"], frame)
        row["frame"] = str(frame.relative_to(prof))
        row["focus"] = focus.measure(frame)
        rows.append(row)
        sigs.append(signature(frame))
    full = [r for r in rows if not r.get("short")]
    for r, b in zip(full, group(sigs)):
        r["set"] = b
    measured = sum(b - a for a, b in vj["segments"])
    cpm = round((len(spans) - len(vj["segments"])) / max(measured, 1e-6) * 60, 2)
    data = {"video": v["id"], "focus_t": focus.FOCUS_T, "set_d": SET_D, "scene_t": SCENE_T, "cuts_per_min": cpm, "shots": rows}
    groups = draw_sheets(full, lambda s: prof / s["frame"], prof / "shot-sheets", f"{v['id']}_shots")
    for f, ids in groups:
        for r in full:
            if r["id"] in ids:
                r["evidence"] = f"{f.name}#{ids.index(r['id']) + 1}"
    refset.write_json(shots_file(name, v["id"]), data)
    flag = "" if CPM_RANGE[0] <= cpm <= CPM_RANGE[1] else f"  ! outside {CPM_RANGE[0]}–{CPM_RANGE[1]}: look at the cuts again"
    log(f"✓ {v['id']}: {len(spans)} shots · {cpm} cuts/min{flag}")
    return data


def shots_set(name: str, only=None, log=print) -> list:
    data = refset.load(name)
    done = []
    for v in data["videos"]:
        if (only and v["id"] not in only) or v.get("state") not in ("measured", "transcribed"):
            continue
        f = shots_file(name, v["id"])
        if f.exists() and refset.read_json(f).get("source_sig") == v.get("source_sig"):
            continue                                     # resume: already done for this file
        d = video_shots(name, v, log)
        d["source_sig"] = v.get("source_sig")
        refset.write_json(f, d)
        done.append(v["id"])
    return done


def refocus(name: str) -> None:
    """Recompute every focused_share from the stored tile variances with the current FOCUS_T (no new measuring)."""
    for v in refset.load(name)["videos"]:
        f = shots_file(name, v["id"])
        if not f.exists():
            continue
        d = refset.read_json(f)
        if d.get("focus_t") == focus.FOCUS_T:
            continue
        for r in d["shots"]:
            if r.get("focus"):
                r["focus"]["focused_share"] = focus.share(r["focus"]["tiles"])
        d["focus_t"] = focus.FOCUS_T
        refset.write_json(f, d)


# ---------- learn label ----------
def _videos_with_shots(name: str) -> list:
    data = refset.load(name)
    return [v for v in data["videos"] if shots_file(name, v["id"]).exists()]


def cell_frames(prof: Path, rows: list) -> dict:
    """After `clean` the full-size frames are gone: cut each shot's picture back out of its labelled contact sheet
    (the same 200×112 picture the labeler saw), without the caption. {id: path}."""
    out, cache = {}, {}
    tmp = prof / "label-cells"
    tmp.mkdir(exist_ok=True)
    for r in rows:
        sheet, _, n = (r.get("evidence") or "").partition("#")
        f = prof / "shot-sheets" / sheet
        if not n or not f.exists():
            continue
        n = int(n) - 1
        im = cache.setdefault(sheet, Image.open(f).convert("RGB"))
        x, y = 6 + (n % COLS) * (CW + 6), 6 + (n // COLS) * (CH + LAB + 6) + LAB
        dst = tmp / f"{r['id']}.jpg"
        im.crop((x, y, x + CW, y + CH)).save(dst, quality=92)
        out[r["id"]] = dst
    return out


def label_set(name: str, log=print) -> dict:
    total = {"shots": 0, "calls": 0, "check": []}
    for v in _videos_with_shots(name):
        prof = refset.profile_dir(name, v["id"])
        d = refset.read_json(shots_file(name, v["id"]))
        full = [r for r in d["shots"] if not r.get("short")]
        cells = {} if all((prof / r["frame"]).exists() for r in full) else cell_frames(prof, full)
        full = [r for r in full if not cells or r["id"] in cells]
        plain = draw_sheets(full, lambda s: cells.get(s["id"]) or prof / s["frame"], prof / "label-sheets",
                            f"{v['id']}_plain", captions=False)
        hints = {r["id"]: r.get("focus") or {} for r in full}
        got = labeler.label(plain, hints)
        for r in full:
            if r.get("edited_by") == "user":
                continue
            lab = got["labels"].get(r["id"])
            if lab:
                r.update(lab)
                r["set"] = lab.get("place") or r.get("set")       # specs/021 FR-004 (2026-11-13): places from the labeler
                r["check"] = labeler.contradicts(lab, r.get("focus"))
                if r["check"]:
                    total["check"].append(f"{v['id']}:{r['id']}")
        d["labeler"] = {"model": got["model"], "usage": got["usage"], "calls": got["calls"]}
        draw_sheets(full, lambda s: cells.get(s["id"]) or prof / s["frame"], prof / "shot-sheets", f"{v['id']}_shots")
        if cells:
            import shutil
            shutil.rmtree(prof / "label-cells", ignore_errors=True)
        refset.write_json(shots_file(name, v["id"]), d)
        total["shots"] += len(full)
        total["calls"] += got["calls"]
        log(f"✓ {v['id']}: {len(full)} shots labelled ({got['calls']} call(s), {got['model']})")
    for c in total["check"]:
        log(f"  ! {c}: the label and the focus measure disagree, look at it on the sheet")
    return total


def set_label(name: str, ref: str, pairs: list) -> dict:
    """`--set vNN:Sxxx key=value …`: a hand correction, kept by later labelling runs."""
    vid, sid = ref.split(":", 1)
    f = shots_file(name, vid)
    d = refset.read_json(f)
    row = next((r for r in d["shots"] if r["id"] == sid), None)
    if not row:
        raise refset.UsageError(f"no shot {sid} in {vid}")
    for p in pairs:
        k, _, val = p.partition("=")
        if k == "scale" and val not in labeler.SCALES or k == "angle" and val not in labeler.ANGLES or k not in (
                "scale", "angle", "foreground_blur", "set", "place"):
            raise refset.UsageError(f"bad value {p} (scale: {'/'.join(labeler.SCALES)}; angle: {'/'.join(labeler.ANGLES)})")
        row[k] = (val.lower() in ("1", "true", "yes")) if k == "foreground_blur" else val
        if k == "place":
            row["set"] = val
    row["edited_by"] = "user"
    row["check"] = False
    refset.write_json(f, d)
    return row


def second_pass(name: str, n: int = 40, seed: int = 21, log=print) -> dict:
    """SC-001: an independent second labelling of n shots spread over the videos; agreement with the first."""
    pool = []
    for v in _videos_with_shots(name):
        d = refset.read_json(shots_file(name, v["id"]))
        pool += [(v["id"], r) for r in d["shots"] if not r.get("short") and r.get("scale")]
    if not pool:
        raise refset.StepError("no labelled shot yet: run learn label first")
    pick = random.Random(seed).sample(pool, min(n, len(pool)))
    tmp = refset.set_dir(name) / "profile" / "pass2"
    rows = [{**r, "id": f"{vid}-{r['id']}", "_vid": vid, "_sid": r["id"]} for vid, r in pick]
    cells = {}
    for vid in {x["_vid"] for x in rows}:
        prof = refset.profile_dir(name, vid)
        mine = [x for x in rows if x["_vid"] == vid]
        if not all((prof / x["frame"]).exists() for x in mine):
            got_cells = cell_frames(prof, [{**x, "id": x["_sid"]} for x in mine])
            cells.update({f"{vid}-{k}": p for k, p in got_cells.items()})
    groups = draw_sheets(rows, lambda s: cells.get(s["id"]) or refset.profile_dir(name, s["_vid"]) / s["frame"], tmp, "pass2",
                         captions=False)
    got = labeler.label(groups, {r["id"]: r.get("focus") or {} for r in rows})
    same = within = angle = 0
    scale_n = 0
    dis = []
    for r in rows:
        b = got["labels"][r["id"]]
        steps = labeler.steps_apart(r["scale"], b["scale"])
        if r["scale"] == b["scale"]:
            same += 1
        if steps is not None:
            scale_n += 1
            within += steps <= 1
        elif r["scale"] == b["scale"]:
            scale_n += 1
            within += 1
        angle += r["angle"] == b["angle"]
        if r["scale"] != b["scale"] or r["angle"] != b["angle"]:
            dis.append({"id": r["id"], "a": [r["scale"], r["angle"]], "b": [b["scale"], b["angle"]]})
    k = len(rows)
    # angles of text cards are not defined (and not counted in the angle shares): agreement on the other shots too
    cam = [r for r in rows if r["scale"] != "insert" and got["labels"][r["id"]]["scale"] != "insert"]
    angle_cam = sum(r["angle"] == got["labels"][r["id"]]["angle"] for r in cam)
    rep = {"n": k, "scale_same": round(same / k, 3), "scale_within_one": round(within / max(scale_n, 1), 3),
           "angle_same": round(angle / k, 3), "angle_same_without_inserts": round(angle_cam / max(len(cam), 1), 3),
           "n_without_inserts": len(cam), "disagreements": dis, "model": got["model"]}
    refset.write_json(refset.set_dir(name) / "profile" / "labels-pass2.json", got["labels"])
    refset.write_json(refset.set_dir(name) / "profile" / "agreement.json", rep)
    log(f"scale same {rep['scale_same']:.2f} · within one {rep['scale_within_one']:.2f} · angle same {rep['angle_same']:.2f}"
        f" ({rep['angle_same_without_inserts']:.2f} without text cards, n={len(cam)}) · n={k}")
    return rep


# ---------- grammar ----------
grammar = labeler.grammar      # one definition for reference videos and films (tools/filmcheck/labeler.py)


GRAMMAR_METRICS = ["scale_change_share", "longest_same_scale", "focused_share_p50", "subject_sharp_share",
                   "foreground_blur_share", "sets", "top_set_share", "set_change_s_p50"]


def flatten(g: dict) -> dict:
    """Flat metric names for the set summary: scale_huge, angle_eye, … plus the plain ones."""
    out = {f"scale_{k}": v for k, v in (g.get("scale_share") or {}).items()}
    out.update({f"angle_{k}": v for k, v in (g.get("angle_share") or {}).items()})
    out.update({k: g.get(k) for k in GRAMMAR_METRICS})
    return out
