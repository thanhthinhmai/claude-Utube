"""Tier 2: one frame per shot, frame faults and the style comparison (specs/020 US2; FR-011 – FR-014; research R5, R6).

shots.mjs draws and measures the frames in the page; this module scores them (contracts/checks.md "shots"), compares
the film with the style's measured ranges (warnings only, FR-013), draws the contact sheet and saves tiers.shots."""
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from filmcheck import plancheck, qc, rhythm, stylerefs, tiers

HERE = Path(__file__).resolve().parent
FLAT_SHARE, FLAT_SD, TEXT_AREA = 0.60, 0.04, 0.02
DARK_P50, BLOWN_SHARE, SUB_ZONE = 0.04, 0.25, (0.82, 1.0)
SHORT_FILM = 30.0
SEC_PER_FRAME = {"gpu": 0.4, "software": 1.0}


class ShotError(Exception):
    """The frames cannot be made (exit code 2)."""


def frames_for(shots: list, cards: list) -> list:
    """[{key, shot, t, label}]: the middle of each shot, plus the middle of each card inside the shot that holds it."""
    out = []
    for s in shots:
        out.append({"key": s["id"].replace("/", "_"), "shot": s["id"], "t": round((s["t0"] + s["t1"]) / 2, 3), "label": s["id"]})
    for k in cards or []:
        mid = (k["t0"] + max(k["t0"], k.get("t1", k["t0"] + k.get("got", 0)))) / 2
        s = rhythm.shot_at(shots, mid)
        if not s:
            continue
        if abs(mid - (s["t0"] + s["t1"]) / 2) < 0.05:
            continue
        key = f"{s['id']}~{k['id']}".replace("/", "_")
        if any(f["key"] == key for f in out):
            continue
        out.append({"key": key, "shot": s["id"], "t": round(mid, 3), "label": f"{s['id']} {k['id']}"})
    return out


def _issue(rule, ref, at, measure, limit, text="", fix="", severity="block"):
    return {"tier": "shots", "ref": ref, "at": round(at, 2) if at is not None else None, "rule": rule, "severity": severity,
            "measure": measure, "limit": limit, "text": text, "fix": fix, "excepted": None}


def wmedian(pairs) -> float:
    """Median of values weighted by duration: [(value, weight)]."""
    pairs = sorted((v, w) for v, w in pairs if w > 0)
    tot = sum(w for _, w in pairs)
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc >= tot / 2:
            return v
    return pairs[-1][0] if pairs else 0.0


def score(frames: list, shots: list, cues, style: dict, dur: float, film_dir=None) -> tuple:
    """(issues, measures, skipped) from measured frames (see shots.mjs `measure`)."""
    flat = float(style.get("flat_share") or FLAT_SHARE)
    dark = float(style.get("dark_p50") or DARK_P50)
    blown = float(style.get("blown_share") or BLOWN_SHARE)
    zone = style.get("subtitle_zone") or SUB_ZONE
    issues, skipped = [], []
    for f in frames:
        m, ref, at = f["m"], f["shot"], f["t"]
        has_text = m["text_share"] >= TEXT_AREA
        if m["blown_share"] > blown:                          # one fault per frame: blown, then dark, then flat
            issues.append(_issue("blown", ref, at, round(m["blown_share"], 2), blown, fix="bring the highlights down"))
        elif m["content_p50"] < dark and not has_text:
            issues.append(_issue("dark", ref, at, round(m["content_p50"], 3), dark, fix="light the shot"))
        elif (m["dominant_share"] > flat or m["luma_sd"] < FLAT_SD) and not has_text:   # US2 AC4: a card is content
            issues.append(_issue("flat", ref, at, round(max(m["dominant_share"], 0), 2), flat,
                                 text=f"one colour covers {m['dominant_share']:.0%}, luma spread {m['luma_sd']:.3f}",
                                 fix="move the camera out of the object, or add the shot as an exception"))
        cue_on = any(a <= at < b for a, b, _ in cues or [])
        if cue_on:
            H = 540
            for b in f["texts"]:
                if b["y1"] / H > zone[0] and b["y0"] / H < zone[1]:
                    issues.append(_issue("text_over_subtitle", ref, at, round(b["y1"] / H, 2), zone[0],
                                         text=str(b["text"])[:30], fix="move the text above the subtitle band"))
                    break
    # missing glyphs: every on-screen text and subtitle
    texts = sorted({str(b["text"]) for f in frames for b in f["texts"]} | {str(c[2]) for c in cues or []})
    glyphs, fonts_ok = qc.missing_glyphs(Path(film_dir or "."), texts) if texts else ([], True)
    for g in glyphs:
        f = next((f for f in frames if any(g["char"] in str(b["text"]) for b in f["texts"])), None)
        issues.append(_issue("missing_glyph", f["shot"] if f else "subtitles", f["t"] if f else None, g["codepoint"], "a font",
                             text=g["text"], fix="use a font that has the character"))
    if not fonts_ok:
        skipped.append("fonts: fontconfig is not installed, missing glyphs not checked")
    # the style (warnings): duration-weighted medians of the mid-shot frames
    mids = [f for f in frames if "~" not in f["key"]]
    by = {s["id"]: s["t1"] - s["t0"] for s in shots}
    meas = {"frames": len(frames), "luma_p50": round(wmedian((f["m"]["luma_mean"], by.get(f["shot"], 0)) for f in mids), 3),
            "saturation_p50": round(wmedian((f["m"]["sat_p50"], by.get(f["shot"], 0)) for f in mids), 3),
            "cuts_per_min": round((len(shots) - 1) / (dur / 60), 1) if dur > 0 else 0}
    if not stylerefs.has_ranges(style):
        skipped.append("style: no measurements (no EVIDENCE.md ranges or qc.json), style comparison skipped")
    else:
        meas["style_source"] = style.get("source")
        for key, rule in (("luma_p50", "style_luma"), ("saturation_p50", "style_saturation"), ("cuts_per_min", "style_cuts_per_min")):
            rng = style.get(key)
            if not rng:
                continue
            if key == "cuts_per_min" and dur < SHORT_FILM:
                skipped.append("style cuts per minute: the film is under 30 s")
                continue
            v = meas[key]
            if not (rng[0] <= v <= rng[1]):
                issues.append(_issue(rule, "film", None, v, f"{rng[0]:g}–{rng[1]:g}", severity="warn",
                                     fix="match the style, or accept with a reason (qc accept-style)"))
    return issues, meas, skipped


def _node(args, timeout):
    p = subprocess.run(["node", *map(str, args)], capture_output=True, text=True, timeout=timeout)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise ShotError(f"the frames could not be made: {(p.stderr or p.stdout).strip()[-400:]}") from None


def run(film_dir: Path, lib, say=print) -> dict:
    t0 = time.time()
    d = Path(film_dir)
    fp = tiers.fingerprint(d)
    try:
        inp = plancheck.read_input(d, lib, fp)
    except plancheck.PlanError as e:
        raise ShotError(str(e)) from None
    dur, shots = inp["dur"], inp["shots"]
    if not shots:                                   # no shot list: a frame every 3 s
        n = max(1, int(dur // 3))
        shots = [{"id": f"t{i * 3:05.1f}", "t0": i * 3.0, "t1": min(dur, i * 3.0 + 3)} for i in range(n)]
    frames = frames_for(shots, inp.get("cards"))
    mode = os.environ.get("STUDIO_RENDER_MODE") or "software"
    say(f"  {len(frames)} frames · {mode} · ≈ {len(frames) * SEC_PER_FRAME.get(mode, 1.0):.0f} s")
    out = d / ".check" / "shots"
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.jpg"):
        f.unlink()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump({"frames": frames, "out": str(out), "w": 960, "h": 540}, fh)
        job = fh.name
    try:
        got = _node([HERE / "shots.mjs", d, job], timeout=7200)
        style = stylerefs.load(d)
        issues, meas, skipped = score(got["frames"], shots, inp.get("cues"), style, dur, film_dir=d)
        meas["render"] = {"mode": got.get("mode"), "renderer": got.get("renderer")}
        exc = tiers.load_exceptions(d)
        tiers.apply_exceptions(issues, exc)
        bad = {i["ref"] for i in issues if i["severity"] == "block" and not i.get("excepted")}
        marks = {f["key"]: True for f in frames if f["shot"] in bad}
        with open(job, "w") as fh:
            json.dump({"frames": frames, "out": str(out), "sheet": {"marks": marks, "cols": 6, "per": 48}}, fh)
        sheets = _node([HERE / "shots.mjs", d, job], timeout=1800).get("sheets", [])
    finally:
        os.unlink(job)
    meas["sheets"] = [str(Path(s).relative_to(d)) for s in sheets]
    meas["per_frame"] = [{"key": f["key"], "shot": f["shot"], "t": f["t"], **{k: round(v, 4) if isinstance(v, float) else v
                                                                           for k, v in f["m"].items()}} for f in got["frames"]]
    res = tiers.result("shots", issues, meas, skipped, time.time() - t0, fp, exceptions=exc)
    tiers.save_tier(d, "shots", res)
    return tiers.load_tier(d, "shots")


def accept_style(film_dir: Path, reason: str) -> dict:
    reason = (reason or "").strip()
    if not reason:
        raise tiers.TierError("accepting the style warnings needs a reason (--reason \"…\")")
    if len(reason) > tiers.REASON_MAX:
        raise tiers.TierError(f"the reason is {len(reason)} characters; at most {tiers.REASON_MAX}")
    r = tiers.load_tier(film_dir, "shots")
    if not r or not any(i["severity"] == "warn" for i in r["issues"]):
        raise tiers.TierError("there is no open style warning (run: sh bin/studio qc shots <film>)")
    from filmcheck import report
    report.update(film_dir, lambda x: x["tiers"]["shots"].update(style_accept={"reason": reason, "at": tiers.now()}))
    return tiers.load_tier(film_dir, "shots")
