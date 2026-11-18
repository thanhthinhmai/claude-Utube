"""The independent shot labeler (specs/021 FR-002, FR-010; research R3): one `claude -p` run per few contact sheets,
with the studio's own prompt and answer schema, like the script editor of specs/010. It sees only the sheets and the
shot ids (with the measured focus as a cross-check), never the script, the style or the film's name. Same prompt and
schema for reference videos and for films."""
import json
import os
import tempfile
from pathlib import Path

from filmcheck import editor, models

SCALES = ["ecu", "cu", "med", "wide", "huge", "insert", "unknown"]
ANGLES = ["eye", "low", "high", "top", "ots", "unknown"]
ORDER = ["ecu", "cu", "med", "wide", "huge"]          # "one step" for the agreement check
SHEETS_PER_CALL = 4

SYSTEM = """You are the studio's shot labeler. You look at contact sheets of video frames, one frame per shot, each cell
captioned with its shot id, and label every listed shot. Judge only what you see in the pictures you are given; do
not guess what the film is about or what it intends.

The first image is the studio's guide (not a shot): one figure at each scale, captioned with the rule.
Shot scale: decide by where the frame's bottom edge cuts the main figure (on big-headed figures the head counts as the
face); with no figure, by the subject in focus:
- ecu: the edge cuts the head or face (part of the face fills the frame), or one small object fills the frame
- cu: the edge falls between the chin and the chest (head and shoulders)
- med: the edge falls between the chest and the knees
- wide: the whole figure is in the frame and is at least a quarter of the frame height
- huge: the figure is under a quarter of the frame height, or a view over a whole place, crowd or city
When two figures differ, use the one in focus; when it is between two scales, use the edge rule exactly as written.
- insert: a text card, a flat graphic, an empty backdrop carrying only text or numbers
- unknown: you cannot tell
Camera angle (eye unless the picture clearly shows otherwise):
- eye: at eye level of the subject
- low: clearly looking up: ceiling or sky behind the subject, the subject towers
- high: clearly looking down at a slant: the floor or ground fills the background behind the subject
- top: looking straight down, the floor is the whole background
- ots: over the shoulder: a blurred head or shoulder of another figure in the foreground (this wins over eye)
- unknown: you cannot tell; for a text card or flat graphic use eye
foreground_blur: true when a large out-of-focus shape (head, shoulder, object) sits in the foreground at an edge.
place: where the shot is, in at most three lowercase words ("bedroom", "football field", "empty void"). Use the same
words for every shot in the same place, across all the sheets you are given; a text card on a plain backdrop is
"text card".
Each shot comes with a measured focus: the share of the frame in focus (0-1) and the column, row of the sharpest
tile (4 x 3 grid). Use it to check yourself, not to replace looking. Answer every listed id exactly once."""

SCHEMA = {"type": "object", "required": ["shots"], "properties": {"shots": {"type": "array", "items": {
    "type": "object", "required": ["id", "scale", "angle", "foreground_blur", "place", "confidence"],
    "properties": {"id": {"type": "string"}, "scale": {"enum": SCALES}, "angle": {"enum": ANGLES},
                   "foreground_blur": {"type": "boolean"}, "place": {"type": "string", "maxLength": 40},
                   "confidence": {"enum": ["high", "low"]}}}}}}


def version() -> str:
    """A short hash of the prompt, the schema and the guide: labels made by another version are made again."""
    import hashlib
    h = hashlib.sha256((SYSTEM + json.dumps(SCHEMA, sort_keys=True)).encode())
    if GUIDE.is_file():
        h.update(GUIDE.read_bytes())
    return h.hexdigest()[:12]


class LabelError(Exception):
    """The labeler could not run or did not answer as asked."""


GUIDE = Path(__file__).resolve().parent / "labeler-guide.png"      # code-drawn (tools/style-learn/sl/guide.py)


def prompt(sheets: list, ids: list, hints: dict) -> str:
    guide = [f"* {GUIDE} (the guide: read it first; it is not a shot)"] if GUIDE.is_file() else []
    lines = ["Read these images:", *guide, *[f"* {Path(s).resolve()}" for s in sheets], "",
             "Label these shots (id, measured focus share, sharpest tile column,row):"]
    for i in ids:
        h = hints.get(i) or {}
        at = h.get("sharpest_at") or ["?", "?"]
        lines.append(f"- {i} focus={h.get('focused_share', '?')} sharpest={at[0]},{at[1]}")
    return "\n".join(lines) + "\n"


def _valid(ans, ids: list):
    if not isinstance(ans, dict) or not isinstance(ans.get("shots"), list):
        return None
    out = {}
    for s in ans["shots"]:
        if not isinstance(s, dict) or s.get("id") not in ids or s.get("scale") not in SCALES or s.get("angle") not in ANGLES:
            return None
        place = " ".join(str(s.get("place") or "unknown").lower().split()[:3])
        out[s["id"]] = {"scale": s["scale"], "angle": s["angle"], "foreground_blur": bool(s.get("foreground_blur")),
                        "place": place,
                        "confidence": s.get("confidence") if s.get("confidence") in ("high", "low") else "low"}
    return out if set(out) == set(ids) else None


def _env():
    env = {**os.environ}
    env.setdefault("XDG_CACHE_HOME", tempfile.gettempdir())
    if os.environ.get("STUDIO_MODE") == "online":           # through the studio's proxy, like the editor (specs/010)
        if not env.get("CLAUDE_CODE_OAUTH_TOKEN") and env.get("STUDIO_JOB_TOKEN"):
            env["CLAUDE_CODE_OAUTH_TOKEN"] = env["STUDIO_JOB_TOKEN"]
        if not env.get("ANTHROPIC_BASE_URL") and env.get("STUDIO_PROXY"):
            env["ANTHROPIC_BASE_URL"] = env["STUDIO_PROXY"]
        env.setdefault("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "1")
        env.pop("ANTHROPIC_API_KEY", None)
    models.helper_env(env)
    return env


def _call(sheets: list, ids: list, hints: dict, timeout: int) -> tuple:
    import subprocess
    args = [editor.claude_bin(), "-p", "--system-prompt", SYSTEM, "--tools", "Read", "--allowedTools", "Read",
            "--json-schema", json.dumps(SCHEMA), "--output-format", "json", "--no-session-persistence",
            "--model", models.current()]
    for _ in range(2):
        try:
            p = subprocess.run(args, input=prompt(sheets, ids, hints), capture_output=True, text=True, timeout=timeout,
                               env=_env(), cwd=str(Path(sheets[0]).resolve().parent))
        except (OSError, subprocess.TimeoutExpired) as e:
            raise LabelError(f"the labeler did not finish: {e}") from None
        try:
            out = json.loads(p.stdout or "{}")
        except ValueError:
            out = {}
        if p.returncode != 0 and not out:
            raise LabelError(f"the labeler could not run: {(p.stderr or '').strip()[-300:]}")
        got = _valid(out.get("structured_output"), ids)
        if got is not None:
            want = models.current()
            model = models.main_model(out, want)
            return got, model, out.get("usage") or {}
    raise LabelError("the labeler did not answer every shot in the asked form (twice)")


def label(groups: list, hints: dict, timeout: int = 900) -> dict:
    """groups: [(sheet path, [ids on that sheet])]. Returns {labels: {id: {...}}, model, usage, calls}."""
    labels, usage, model, calls = {}, {"input_tokens": 0, "output_tokens": 0}, None, 0
    for k in range(0, len(groups), SHEETS_PER_CALL):
        part = groups[k:k + SHEETS_PER_CALL]
        sheets = [g[0] for g in part]
        ids = [i for g in part for i in g[1]]
        if not ids:
            continue
        got, model, u = _call(sheets, ids, hints, timeout)
        labels.update(got)
        calls += 1
        for key in usage:
            usage[key] += int(u.get(key) or 0)
    return {"labels": labels, "model": model, "usage": usage, "calls": calls}


def contradicts(lab: dict, focus: dict) -> bool:
    """A label that the focus measure argues against (FR-002): look at it again."""
    if not focus:
        return False
    share = focus.get("focused_share", 0)
    col, row = (focus.get("sharpest_at") or [1, 1])
    edge = col in (0, 3) or row in (0, 2)
    # a close-up whose only sharp tile is small and at the edge of the frame: the subject may be far, not close
    return lab.get("scale") in ("ecu", "cu") and 0 < share <= 1 / 12 + 1e-9 and edge


def steps_apart(a: str, b: str):
    """How many scale steps two labels are apart, or None when one is not on the scale (insert, unknown)."""
    if a in ORDER and b in ORDER:
        return abs(ORDER.index(a) - ORDER.index(b))
    return None


def _median(v: list):
    v = sorted(v)
    if not v:
        return None
    m = len(v) // 2
    return v[m] if len(v) % 2 else (v[m - 1] + v[m]) / 2


def grammar(rows: list) -> dict:
    """data-model ShotGrammar for shots in order ({id, t0, t1, scale, angle, foreground_blur, set, focus, short?});
    the same numbers for a reference video (style-learn) and for a film (qc shots)."""
    full = [r for r in rows if not r.get("short")]
    lab = [r for r in full if r.get("scale") and r["scale"] not in ("insert", "unknown")]
    n = len(lab)

    def share(key, vals):
        return {x: round(sum(r.get(key) == x for r in lab) / n, 3) if n else None for x in vals}
    seq = [r["scale"] for r in full if r.get("scale") and r["scale"] != "unknown"]
    pairs = [(a, b) for a, b in zip(seq, seq[1:]) if a != "insert" and b != "insert"]
    run = best = 0
    prev = None
    for sc in seq:
        run = run + 1 if sc == prev and sc != "insert" else 1
        best = max(best, run)
        prev = sc
    sets = [r.get("set") for r in full if r.get("set")]
    changes = [r["t0"] for r, q in zip(full[1:], full) if r.get("set") and r.get("set") != q.get("set")]
    gaps = [b - a for a, b in zip(changes, changes[1:])]
    fs = [r["focus"]["focused_share"] for r in full if r.get("focus")]
    med = _median(fs)
    gap = _median(gaps)
    return {
        "shots": len(rows), "labelled": n, "inserts": sum(r.get("scale") == "insert" for r in full),
        "short": sum(bool(r.get("short")) for r in rows), "unknown": sum(r.get("scale") == "unknown" for r in full),
        "scale_share": share("scale", ORDER),
        "angle_share": share("angle", ["eye", "low", "high", "top", "ots"]),
        "scale_change_share": round(sum(a != b for a, b in pairs) / len(pairs), 3) if pairs else None,
        "longest_same_scale": best,
        "focused_share_p50": round(med, 3) if med is not None else None,
        "subject_sharp_share": round(sum((r.get("focus") or {}).get("focused_share", 0) > 0 for r in lab) / n, 3) if n else None,
        "foreground_blur_share": round(sum(bool(r.get("foreground_blur")) for r in lab) / n, 3) if n else None,
        "sets": len(set(sets)),
        "top_set_share": round(max(sets.count(x) for x in set(sets)) / len(sets), 3) if sets else None,
        "set_change_s_p50": round(gap, 2) if gap is not None else None,
    }


def runs(rows: list) -> list:
    """[[ids]] of consecutive shots with the same scale (inserts and unknowns break a run)."""
    out, cur, prev = [], [], None
    for r in rows:
        sc = r.get("scale")
        if sc and sc not in ("insert", "unknown") and sc == prev:
            cur.append(r["id"])
        else:
            if len(cur) > 1:
                out.append(cur)
            cur = [r["id"]] if sc and sc not in ("insert", "unknown") else []
        prev = sc if sc not in ("insert", "unknown") else None
    if len(cur) > 1:
        out.append(cur)
    return out
