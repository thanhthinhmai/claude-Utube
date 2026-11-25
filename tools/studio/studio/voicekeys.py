"""The studio owner's service keys: ElevenLabs (specs/036 research R3) and Freesound (specs/037 research R4).

Kept encrypted (Fernet) in $STUDIO_DATA/secrets/<name>.json, the Fernet key in secrets/.key; the folder 0700, files 0600.
Only the proxy reads one back (`secret(name)`); every answer of the app carries the last 4 characters at most. A key is
saved only after one call to its service proved it works. Without a name every function means ElevenLabs (036 callers)."""
import json
import os
import time
from pathlib import Path

from . import db

KEYFILE = ".key"
NAMES = ("elevenlabs", "freesound")
FILE, STATUS = "elevenlabs.json", "elevenlabs.status.json"       # 036 names, kept for callers and tests


def _files(name: str):
    if name not in NAMES:
        raise ValueError(f"unknown key name: {name}")
    return f"{name}.json", f"{name}.status.json"


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


def secret(name: str = "elevenlabs"):
    """{key, model?} or None. For the proxy only: never put this in an answer, a log or a job."""
    f = folder() / _files(name)[0]
    if not f.is_file():
        return None
    try:
        return json.loads(_fernet().decrypt(f.read_bytes()))
    except Exception:                 # noqa: BLE001 — a damaged file or a lost .key is the same as no key
        return None


def _status(name: str = "elevenlabs", **kw) -> dict:
    f = folder() / _files(name)[1]
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


def delete(name: str = "elevenlabs") -> None:
    for f in _files(name):
        (folder() / f).unlink(missing_ok=True)


# ---------- any named key (specs/037) ----------
def status(name: str) -> dict:
    """{set, last4, status: none|ok|invalid, checked_at}: what an answer may carry about any key."""
    if name == "elevenlabs":
        p = public()
        return {k: p[k] for k in ("set", "last4", "status", "checked_at")}
    s = secret(name)
    if not s:
        return {"set": False, "last4": None, "status": "none", "checked_at": None}
    st = _status(name)
    return {"set": True, "last4": s["key"][-4:], "status": st.get("status", "ok"), "checked_at": st.get("checked_at")}


def save_named(name: str, key: str, by: str = None) -> dict:
    """Try then keep a key other than ElevenLabs. Freesound: one search call (freesound.FreesoundError when bad)."""
    if name == "elevenlabs":
        save(key, by=by)
        return status(name)
    key = key.strip()
    if name == "freesound":
        from filmcheck import freesound
        freesound.check(key)
    _write(folder() / _files(name)[0], _fernet().encrypt(json.dumps(
        {"key": key, "saved_at": int(time.time()), "saved_by": by}).encode()))
    _status(name, status="ok", checked_at=int(time.time()))
    return status(name)
