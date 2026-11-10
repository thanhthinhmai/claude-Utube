"""The independent script editor (specs/010 R3): one `claude -p` run with the studio's own prompt and answer schema.

The editor sees only SCRIPT.md, SOURCES.md, TREATMENT.md and the film's brief, never the writer's history."""
import json
import os
from pathlib import Path

MODELS = ("inherit", "opus", "sonnet", "haiku")


def studio_root() -> Path:
    return Path(os.environ.get("STUDIO_ROOT") or Path(__file__).resolve().parents[2])


def config_path() -> Path:
    return studio_root() / ".studio" / "config.json"


def read_config() -> dict:
    try:
        return json.loads(config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def set_editor_model(value: str) -> None:
    if value not in MODELS:
        raise ValueError(f"editor model must be one of {', '.join(MODELS)}")
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    data = read_config()
    data["editor_model"] = value
    p.write_text(json.dumps(data, indent=1), encoding="utf-8")


def editor_model() -> str:
    """STUDIO_EDITOR_MODEL (online: set by the worker from Settings), else .studio/config.json, else inherit."""
    v = os.environ.get("STUDIO_EDITOR_MODEL") or read_config().get("editor_model") or "inherit"
    return v if v in MODELS else "inherit"


def model_args() -> list:
    """`--model` for claude -p: nothing for inherit (Claude Code keeps the job's or the session's model), unless
    STUDIO_MODEL names the job's model."""
    m = editor_model()
    if m != "inherit":
        return ["--model", m]
    return ["--model", os.environ["STUDIO_MODEL"]] if os.environ.get("STUDIO_MODEL") else []
