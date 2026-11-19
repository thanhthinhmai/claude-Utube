"""The studio's one Claude model (specs/024): the allowed list lives in tools/models.json; every Claude call takes
its model from here and passes it explicitly, helper calls of Claude Code included. Python standard library only."""
import json
import os
import sys
from pathlib import Path

LIST_FILE = Path(__file__).resolve().parents[1] / "models.json"
HELPER_ENV = ("ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_SMALL_FAST_MODEL")


def _list() -> dict:
    return json.loads(LIST_FILE.read_text(encoding="utf-8"))


def allowed() -> dict:
    """{model id: display name}."""
    return dict(_list()["allowed"])


def default() -> str:
    return _list()["default"]


def resolve(value, warn: bool = True) -> str:
    """The value when it is allowed, else the default (with one warning line on stderr when a value was given)."""
    if value in allowed():
        return value
    if value and warn:
        print(f"model {value} is not allowed; using {default()}", file=sys.stderr)
    return default()


def _config_path() -> Path:
    root = Path(os.environ.get("STUDIO_ROOT") or Path(__file__).resolve().parents[2])
    return root / ".studio" / "config.json"


def _config() -> dict:
    try:
        return json.loads(_config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def current() -> str:
    """STUDIO_MODEL (online: the worker sets it from Settings), else .studio/config.json `model`, else the default.
    The old editor_model / STUDIO_EDITOR_MODEL are ignored."""
    return resolve(os.environ.get("STUDIO_MODEL") or _config().get("model"))


def set_model(value: str) -> None:
    if value not in allowed():
        raise ValueError("model must be one of: " + ", ".join(allowed()))
    p = _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    data = _config()
    data["model"] = value
    p.write_text(json.dumps(data, indent=1), encoding="utf-8")


def helper_env(env: dict, model: str = None) -> dict:
    """Claude Code runs helper calls (WebSearch, summaries) on a small model; point them at the run's model
    (checked 2026-11-18: modelUsage then lists only the asked model)."""
    m = model or current()
    for k in HELPER_ENV:
        env[k] = m
    return env


def main_model(out: dict, want: str) -> str:
    """The model a run used: the asked one when Claude Code used it, else the one that wrote the most."""
    used = out.get("modelUsage") or {}
    if not used:
        return want
    return want if want in used else max(used, key=lambda k: (used[k] or {}).get("outputTokens", 0))
