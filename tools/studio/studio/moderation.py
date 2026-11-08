"""Content check of a film idea before any credit is used (specs/007 FR-012; specs/008 research R6).

One call with structured output {allowed, reason}: through Claude Code (`claude -p`) on the least used Claude
account, with no tools and nothing saved; else through the fallback API key; with neither the studio is not ready.
A refusal counts as not allowed. STUDIO_MODERATION=fake (tests) replaces the call with a keyword rule."""
import json
import os
import subprocess
import tempfile

from . import claude_plan, db, quotas
from .store import StudioError

POLICY = """You check film ideas for an online film studio. Answer whether the idea may be made.
Not allowed:
- graphic violence or gore;
- sexual content;
- hate or harassment against a group or a person;
- impersonating a real person or a real brand, or using their name, likeness or logo;
- naming a YouTube channel or creator to copy.
Everything else is allowed, including dark or sad themes told without graphic detail.
If not allowed, give a short reason in English (one sentence) that the customer can act on."""

SCHEMA = {
    "type": "object",
    "properties": {"allowed": {"type": "boolean"}, "reason": {"type": "string"}},
    "required": ["allowed", "reason"],
    "additionalProperties": False,
}

FAKE_BLOCK = ("gore", "porn", "nude", "behead", "youtube channel")


def check(idea: str):
    """(ok, reason). Raises nothing for a bad idea; network or key problems raise and the job is not created."""
    if os.environ.get("STUDIO_MODERATION") == "fake":
        low = (idea or "").lower()
        hit = next((w for w in FAKE_BLOCK if w in low), None)
        return (False, f"The idea mentions “{hit}”, which the studio does not make.") if hit else (True, "")
    prompt = f"Film idea:\n<idea>\n{idea}\n</idea>"
    for slot in claude_plan.usable():
        got = _through_plan(slot, prompt)
        if got is not None:
            return got
    if claude_plan.api_key():
        return _through_key(prompt)
    raise StudioError("studio_not_ready", "xưởng chưa có tài khoản Claude nào dùng được", 503)


def _verdict(data) -> tuple:
    if not isinstance(data, dict):
        return False, "The idea could not be checked. Please rephrase it."
    return bool(data.get("allowed")), (data.get("reason") or "")[:300]


def _through_plan(slot: int, prompt: str):
    """(ok, reason), or None when this account could not answer (limit, sign-in, timeout): try the next one.
    The idea goes in on stdin (not visible in the process list) and no session is written (T001)."""
    args = ["-p", "--model", db.settings()["model"], "--system-prompt", POLICY, "--tools", "",
            "--json-schema", json.dumps(SCHEMA), "--output-format", "json", "--no-session-persistence"]
    try:
        with tempfile.TemporaryDirectory(prefix="moderation.") as cwd:      # no project files around it
            p = claude_plan.run(slot, args, timeout=120, input=prompt, cwd=cwd, wait=30)
        out = json.loads(p.stdout or "{}")
    except (subprocess.TimeoutExpired, claude_plan.Busy, ValueError):
        return None
    if out.get("is_error") or p.returncode != 0:
        status = out.get("api_error_status")
        if status == 429:
            claude_plan.mark_limited(slot)
        elif status == 401:
            claude_plan.mark_needs_signin(slot)
        return None
    quotas.record_call(None, f"plan:{slot}", db.settings()["model"], out.get("usage") or {})
    if out.get("stop_reason") == "refusal":
        return False, "The idea cannot be made by the studio."
    return _verdict(out.get("structured_output"))


def _through_key(prompt: str):
    import anthropic
    client = anthropic.Anthropic()          # ANTHROPIC_API_KEY of the studio (never a customer's)
    r = client.messages.create(
        model=db.settings()["model"],
        max_tokens=1024,
        system=POLICY,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    quotas.record_call(None, "api", r.model, r.usage.model_dump() if hasattr(r.usage, "model_dump") else {})
    if r.stop_reason == "refusal":
        return False, "The idea cannot be made by the studio."
    text = next((b.text for b in r.content if b.type == "text"), "")
    try:
        return _verdict(json.loads(text))
    except json.JSONDecodeError:
        return False, "The idea could not be checked. Please rephrase it."
