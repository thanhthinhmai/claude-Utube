"""Craft labels of reference shots (specs/027 FR-014, research R1, R2): one independent `claude -p` run per few contact
sheets, like the shot labeler (labeler.py), with its own prompt, schema and version so the shot labels' caches stay
valid. For each shot it says whether it is a card, how many people are in it, and whether someone is doing a real
action, the place is outdoors, and someone holds an object. The same definitions name the kit's act kinds, so the
shares measured here compare with a film's window.CRAFT."""
import hashlib
import json
import subprocess
from pathlib import Path

from filmcheck import editor, labeler, models

SHEETS_PER_CALL = 3

SYSTEM = """You are the studio's craft labeler. You look at contact sheets of video frames, one frame per shot, each cell
captioned with its shot id, and label every listed shot. Judge only what you see in the picture; do not guess the story.

For each shot answer:
- card: true when the frame is a text card, a number or fact card, a flat graphic, a map, or an empty backdrop with
  only text or icons. A card has no other field that counts.
- people: how many people (cartoon figures) are clearly visible, 0 to 9 (9 means nine or more; a crowd is 9).
- action: true when at least one person is clearly DOING something with a purpose, with their body, an object or
  another person: running, jumping, falling, throwing, catching, carrying, pushing, pulling, typing, cooking,
  playing (cards, a ball, an instrument), fighting, hugging, handing something over, climbing, dancing, driving.
  NOT an action: only standing, sitting or walking calmly, looking, nodding, tilting the head, a facial expression,
  waving hello, pointing, raising a hand, shrugging, talking. When unsure, false.
- outdoor: true when the sky is visible or the place is clearly outdoors (street, field, court, rooftop, park,
  parking lot, beach, space). Inside a room, hall, shop or vehicle: false.
- prop: true when a person is holding an object in a hand (phone, cards, money, ball, box, cup, paper, tool, food).
  Clothes and bags worn on the body do not count.
- subject: the box around the main person (the one the shot is about; when unsure, the largest), as
  [left, top, right, bottom] in percent of the frame (0 = left/top edge, 100 = right/bottom edge), from the top of the
  head (or hair) to the lowest visible part of the body. null when there is no person or the frame is a card.
Answer every listed id exactly once."""

SCHEMA = {"type": "object", "required": ["shots"], "properties": {"shots": {"type": "array", "items": {
    "type": "object", "required": ["id", "card", "people", "action", "outdoor", "prop", "subject"],
    "properties": {"id": {"type": "string"}, "card": {"type": "boolean"},
                   "people": {"type": "integer", "minimum": 0, "maximum": 9},
                   "action": {"type": "boolean"}, "outdoor": {"type": "boolean"}, "prop": {"type": "boolean"},
                   "subject": {"type": ["array", "null"], "items": {"type": "number"}, "minItems": 4, "maxItems": 4}}}}}}


def version() -> str:
    return hashlib.sha256((SYSTEM + json.dumps(SCHEMA, sort_keys=True)).encode()).hexdigest()[:12]


class CraftLabelError(labeler.LabelError):
    """The craft labeler could not run or did not answer as asked."""


def prompt(sheets: list, ids: list) -> str:
    return "\n".join(["Read these images:", *[f"* {Path(s).resolve()}" for s in sheets], "",
                      "Label these shots:", *[f"- {i}" for i in ids]]) + "\n"


def valid(ans, ids: list):
    """The answer as {id: {card, people, action, outdoor, prop, subject}}, or None when it is not every id in the asked
    form. A subject box outside 0–100 or upside down is dropped (null), not the whole answer (specs/039 R2)."""
    if not isinstance(ans, dict) or not isinstance(ans.get("shots"), list):
        return None
    out = {}
    for s in ans["shots"]:
        if not isinstance(s, dict) or s.get("id") not in ids:
            return None
        if not all(isinstance(s.get(k), bool) for k in ("card", "action", "outdoor", "prop")):
            return None
        n = s.get("people")
        if not isinstance(n, int) or isinstance(n, bool) or not 0 <= n <= 9:
            return None
        card = s["card"]
        out[s["id"]] = {"card": card, "people": 0 if card else n,
                        "action": bool(s["action"]) and not card and n > 0,
                        "outdoor": bool(s["outdoor"]) and not card,
                        "prop": bool(s["prop"]) and not card and n > 0,
                        "subject": _box(s.get("subject")) if not card and n > 0 else None}
    return out if set(out) == set(ids) else None


def _box(b):
    """[x0, y0, x1, y1] in percent, rounded, or None when it is not a real box inside the frame."""
    if not (isinstance(b, list) and len(b) == 4 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in b)):
        return None
    x0, y0, x1, y1 = b
    if not (0 <= x0 < x1 <= 100 and 0 <= y0 < y1 <= 100):
        return None
    return [round(float(v), 1) for v in b]


def _call(sheets: list, ids: list, timeout: int) -> tuple:
    args = [editor.claude_bin(), "-p", "--system-prompt", SYSTEM, "--tools", "Read", "--allowedTools", "Read",
            "--json-schema", json.dumps(SCHEMA), "--output-format", "json", "--no-session-persistence",
            "--model", models.current()]
    for _ in range(2):
        try:
            p = subprocess.run(args, input=prompt(sheets, ids), capture_output=True, text=True, timeout=timeout,
                               env=labeler._env(), cwd=str(Path(sheets[0]).resolve().parent))
        except (OSError, subprocess.TimeoutExpired) as e:
            raise CraftLabelError(f"the craft labeler did not finish: {e}") from None
        try:
            out = json.loads(p.stdout or "{}")
        except ValueError:
            out = {}
        if p.returncode != 0 and not out:
            raise CraftLabelError(f"the craft labeler could not run: {(p.stderr or '').strip()[-300:]}")
        got = valid(out.get("structured_output"), ids)
        if got is not None:
            return got, models.main_model(out, models.current()), out.get("usage") or {}
    raise CraftLabelError("the craft labeler did not answer every shot in the asked form (twice)")


def label(groups: list, timeout: int = 900) -> dict:
    """groups: [(sheet path, [ids on that sheet])]. Returns {labels, model, usage, calls}."""
    labels, usage, model, calls = {}, {"input_tokens": 0, "output_tokens": 0}, None, 0
    for k in range(0, len(groups), SHEETS_PER_CALL):
        part = groups[k:k + SHEETS_PER_CALL]
        ids = [i for g in part for i in g[1]]
        if not ids:
            continue
        got, model, u = _call([g[0] for g in part], ids, timeout)
        labels.update(got)
        calls += 1
        for key in usage:
            usage[key] += int(u.get(key) or 0)
    return {"labels": labels, "model": model, "usage": usage, "calls": calls}


# ---------- shares (the same counting as craftcheck.py uses on a film's window.CRAFT) ----------
def shares(rows: list) -> dict:
    """rows: [{card, people, action, outdoor, prop, ots}] → {action, prop, outdoor, ots, shots, people_shots}.
    action and prop over shots with people; outdoor and ots over every shot that is not a card."""
    shots = [r for r in rows if not r.get("card")]
    people = [r for r in shots if (r.get("people") or 0) > 0]
    f = lambda xs, k: round(sum(1 for r in xs if r.get(k)) / len(xs), 3) if xs else None  # noqa: E731
    return {"action": f(people, "action"), "prop": f(people, "prop"), "outdoor": f(shots, "outdoor"),
            "ots": f(shots, "ots"), "shots": len(shots), "people_shots": len(people)}


def spread(values: list) -> dict:
    """min, p25, p50, p75, max of per-video shares (linear interpolation), rounded to 3 places."""
    v = sorted(x for x in values if x is not None)
    if not v:
        return {}

    def q(p):
        i = (len(v) - 1) * p
        lo = int(i)
        hi = min(lo + 1, len(v) - 1)
        return round(v[lo] + (v[hi] - v[lo]) * (i - lo), 3)
    return {"min": v[0], "p25": q(0.25), "p50": q(0.5), "p75": q(0.75), "max": v[-1]}
