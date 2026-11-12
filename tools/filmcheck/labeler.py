"""The independent shot labeler (specs/021 FR-002, FR-010; research R3): one `claude -p` run per few contact sheets,
with the studio's own prompt and answer schema, like the script editor of specs/010. It sees only the sheets and the
shot ids (with the measured focus as a cross-check), never the script, the style or the film's name. Same prompt and
schema for reference videos and for films."""
import json
import os
import tempfile
from pathlib import Path

from filmcheck import editor

SCALES = ["ecu", "cu", "med", "wide", "huge", "insert", "unknown"]
ANGLES = ["eye", "low", "high", "top", "ots", "unknown"]
ORDER = ["ecu", "cu", "med", "wide", "huge"]          # "one step" for the agreement check
SHEETS_PER_CALL = 4

SYSTEM = """You are the studio's shot labeler. You look at contact sheets of video frames, one frame per shot, each cell
captioned with its shot id, and label every listed shot. Judge only what you see in the pictures you are given; do
not guess what the film is about or what it intends.

Shot scale (by how much of a standing figure the frame shows; with no figure, by the subject in focus):
- ecu: part of a face, or one small object, fills the frame
- cu: head and shoulders
- med: from the waist or knees up
- wide: whole figure with some of the place around it
- huge: figure smaller than a quarter of the frame height, or a view over a whole place, crowd or city
- insert: a text card, a flat graphic, an empty backdrop carrying only text or numbers
- unknown: you cannot tell
Camera angle:
- eye: at eye level of the subject
- low: camera below, looking up
- high: camera above, looking down at a slant
- top: looking straight down
- ots: over the shoulder, a blurred head or shoulder in the foreground
- unknown: you cannot tell
foreground_blur: true when a large out-of-focus shape (head, shoulder, object) sits in the foreground at an edge.
Each shot comes with a measured focus: the share of the frame in focus (0-1) and the column, row of the sharpest
tile (4 x 3 grid). Use it to check yourself, not to replace looking. Answer every listed id exactly once."""

SCHEMA = {"type": "object", "required": ["shots"], "properties": {"shots": {"type": "array", "items": {
    "type": "object", "required": ["id", "scale", "angle", "foreground_blur", "confidence"],
    "properties": {"id": {"type": "string"}, "scale": {"enum": SCALES}, "angle": {"enum": ANGLES},
                   "foreground_blur": {"type": "boolean"}, "confidence": {"enum": ["high", "low"]}}}}}}


class LabelError(Exception):
    """The labeler could not run or did not answer as asked."""


def prompt(sheets: list, ids: list, hints: dict) -> str:
    lines = ["Read these contact sheets:", *[f"* {Path(s).resolve()}" for s in sheets], "",
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
        out[s["id"]] = {"scale": s["scale"], "angle": s["angle"], "foreground_blur": bool(s.get("foreground_blur")),
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
    return env


def _call(sheets: list, ids: list, hints: dict, timeout: int) -> tuple:
    import subprocess
    args = [editor.claude_bin(), "-p", "--system-prompt", SYSTEM, "--tools", "Read", "--allowedTools", "Read",
            "--json-schema", json.dumps(SCHEMA), "--output-format", "json", "--no-session-persistence",
            *editor.model_args()]
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
            used = list((out.get("modelUsage") or {}).keys())
            return got, (used[0] if used else editor.model_args()[-1]), out.get("usage") or {}
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
