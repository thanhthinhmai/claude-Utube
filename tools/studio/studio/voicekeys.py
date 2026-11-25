"""The studio owner's ElevenLabs key (specs/036 research R3, contracts/http.md).

Kept encrypted (Fernet) in $STUDIO_DATA/secrets/elevenlabs.json, its key in secrets/.key; the folder 0700, files 0600.
Only the proxy reads it back (`secret()`); every answer of the app carries the last 4 characters at most. A key is saved
only after one call to ElevenLabs proved it works."""
import json
import os
import time
from pathlib import Path

from . import db

FILE, KEYFILE, STATUS = "elevenlabs.json", ".key", "elevenlabs.status.json"


def folder() -> Path:
    d = db.data_dir() / "secrets"
    d.mkdir(parents=True, exist_ok=True)
    os.chmod(d, 0o700)
    return d


def _write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(data)
    os.replace(tmp, path)


def _fernet():
    from cryptography.fernet import Fernet
    f = folder() / KEYFILE
    if not f.is_file():
        _write(f, Fernet.generate_key())
    return Fernet(f.read_bytes().strip())


def secret():
    """{key, model} or None. For the proxy only: never put this in an answer, a log or a job."""
    f = folder() / FILE
    if not f.is_file():
        return None
    try:
        return json.loads(_fernet().decrypt(f.read_bytes()))
    except Exception:                 # noqa: BLE001 — a damaged file or a lost .key is the same as no key
        return None


def _status(**kw) -> dict:
    f = folder() / STATUS
    try:
        st = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    if kw:
        st.update(kw)
        _write(f, json.dumps(st).encode())
    return st


def public() -> dict:
    """{set, last4, model, tier, left, limit, reset_at, checked_at, status: none|ok|invalid|quota}."""
    s = secret()
    if not s:
        return {"set": False, "last4": None, "model": None, "tier": None, "left": None, "limit": None,
                "reset_at": None, "checked_at": None, "status": "none"}
    st = _status()
    return {"set": True, "last4": s["key"][-4:], "model": s.get("model"), "tier": st.get("tier"), "left": st.get("left"),
            "limit": st.get("limit"), "reset_at": st.get("reset_at"), "checked_at": st.get("checked_at"),
            "status": st.get("status", "ok")}


def _check(key: str) -> dict:
    """One subscription call. ElevenError when the key does not work."""
    from filmcheck import eleven
    return eleven.subscription(key=key)


def save(key: str, model: str = None, by: str = None) -> dict:
    """Try the key, then keep it (FR-001, US1-2: a bad key is never saved). Raises eleven.ElevenError."""
    from filmcheck import eleven
    key = key.strip()
    sub = _check(key)
    model = (model or "").strip() or eleven.DEFAULT_MODEL
    _write(folder() / FILE, _fernet().encrypt(json.dumps(
        {"key": key, "model": model, "saved_at": int(time.time()), "saved_by": by}).encode()))
    _status(status="ok", checked_at=int(time.time()), **{k: sub.get(k) for k in ("tier", "left", "limit", "reset_at")})
    return public()


def test() -> dict:
    """Check the saved key again; the status says ok, invalid or quota."""
    from filmcheck import eleven
    s = secret()
    if not s:
        return public()
    try:
        sub = _check(s["key"])
        _status(status="ok" if sub.get("left") else "quota", checked_at=int(time.time()),
                **{k: sub.get(k) for k in ("tier", "left", "limit", "reset_at")})
    except eleven.ElevenError as e:
        _status(status="invalid" if e.code == "invalid_key" else "quota" if e.code == "quota" else "ok",
                checked_at=int(time.time()), error=e.code)
    return public()


def set_model(model: str) -> dict:
    s = secret()
    if s:
        s["model"] = model.strip()
        _write(folder() / FILE, _fernet().encrypt(json.dumps(s).encode()))
    return public()


def delete() -> None:
    for name in (FILE, STATUS):
        (folder() / name).unlink(missing_ok=True)
