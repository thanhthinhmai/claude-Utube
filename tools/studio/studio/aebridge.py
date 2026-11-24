"""The desktop app's key for /api/v1/ae/bridge/* (specs/032 research R2).

The desktop app makes a random 32-byte key at each start, writes it to bridge.json and starts the core with
`app start --bridge <file>`; the file's path is in STUDIO_AE_BRIDGE for the web and the proxy. A bridge call must come
from 127.0.0.1 with the header X-CU-Bridge equal to the key (constant-time compare). No file: the bridge is closed."""
import hmac
import json
import os
from pathlib import Path

LOOPBACK = {"127.0.0.1", "::1", "testclient"}
_cache = {"key": None, "value": None}


def key() -> str:
    p = os.environ.get("STUDIO_AE_BRIDGE")
    if not p:
        return ""
    try:
        st = Path(p).stat()
    except OSError:
        return ""
    k = (p, st.st_mtime_ns, st.st_size)
    if _cache["key"] != k:
        try:
            v = json.loads(Path(p).read_text()).get("key") or ""
        except (OSError, ValueError, AttributeError):
            v = ""
        _cache.update(key=k, value=v if len(v) >= 32 else "")
    return _cache["value"]


def allowed(client: str, header: str) -> bool:
    k = key()
    return bool(k) and client in LOOPBACK and hmac.compare_digest((header or "").encode(), k.encode())
