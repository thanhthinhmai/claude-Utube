"""Content check of a film idea before any credit is used (specs/007 FR-012).

One Messages API call with structured output {allowed, reason}. A refusal counts as not allowed.
STUDIO_MODERATION=fake (tests) replaces the call with a keyword rule."""
import json
import os

from . import db

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
    import anthropic
    client = anthropic.Anthropic()          # ANTHROPIC_API_KEY of the studio (never a customer's)
    r = client.messages.create(
        model=db.settings()["model"],
        max_tokens=1024,
        system=POLICY,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": f"Film idea:\n<idea>\n{idea}\n</idea>"}],
    )
    if r.stop_reason == "refusal":
        return False, "The idea cannot be made by the studio."
    text = next((b.text for b in r.content if b.type == "text"), "")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return False, "The idea could not be checked. Please rephrase it."
    return bool(data.get("allowed")), (data.get("reason") or "")[:300]
