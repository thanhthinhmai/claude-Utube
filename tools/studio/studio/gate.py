"""The desktop app's license gate (specs/017 research R4). The app writes gate.json and starts the core with
`app start --gate <file>`; the web answers 423 and the worker takes no new job while the gate is closed.
No gate file given (development, `app start` by hand): nothing is checked."""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "license"))
import signing  # noqa: E402

now = time.time                     # tests replace it
_cache = {"key": None, "doc": None}


def path():
    p = os.environ.get("STUDIO_LICENSE_GATE")
    return Path(p) if p else None


def public_key():
    k = os.environ.get("CU_LICENSE_PUBLIC_KEY", "").strip()
    if k:
        return k
    f = ROOT / "desktop" / "license-public-key.txt"
    return f.read_text().strip() if f.is_file() else ""


def _read(p: Path):
    try:
        st = p.stat()
    except OSError:
        return None
    key = (str(p), st.st_mtime_ns, st.st_size)
    if _cache["key"] != key:
        try:
            _cache.update(key=key, doc=json.loads(p.read_text()))
        except (OSError, ValueError):
            _cache.update(key=key, doc=None)
    return _cache["doc"]


def check():
    """(open?, reason). Open when no gate is set."""
    p = path()
    if not p:
        return True, None
    doc = _read(p)
    if not isinstance(doc, dict):
        return False, "no_gate"
    if doc.get("refused"):
        return False, str(doc["refused"])
    pub = public_key()
    if not pub:
        return False, "no_public_key"
    payload = signing.verify_lease(pub, doc.get("lease") or "")
    why = signing.lease_problem(payload, doc.get("deviceId"), now(), doc.get("clock") or 0)
    return (why is None), why


LOCKED_HTML = """<!doctype html><meta charset="utf-8"><title>claude-Utube is locked</title>
<body style="font:16px/1.5 system-ui,sans-serif;max-width:560px;margin:15vh auto;padding:0 16px">
<h1>claude-Utube is locked</h1><p>This computer has no valid license right now. Open the claude-Utube app and enter
a key from the studio owner. Your films and data are kept.</p></body>"""
