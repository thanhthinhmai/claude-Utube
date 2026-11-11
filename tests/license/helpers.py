"""Shared bits of the license server tests (specs/017)."""
import hashlib
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "license"))

import server  # noqa: E402,F401
import signing  # noqa: E402
import store  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

PASSWORD = "a-good-admin-password"
T0 = 1_800_000_000.0


def device(n: int) -> str:
    return hashlib.sha256(f"device-{n}".encode()).hexdigest()


class Clock:
    def __init__(self, t=T0):
        self.t = t

    def __call__(self):
        return self.t


def make(**env):
    """(store, client, clock, private key, public key) with a fresh data folder and a fake clock."""
    priv, pub = signing.new_keypair()
    clock = Clock()
    store.now = clock
    s = store.Store(Path(tempfile.mkdtemp(prefix="license.")), priv)
    s.set_password(PASSWORD)
    return s, TestClient(server.create_app(s)), clock, priv, pub


def admin(client):
    r = client.post("/admin/api/login", json={"password": PASSWORD}, headers={"x-cu-admin": "1"})
    assert r.status_code == 200, r.text
    return {"x-cu-admin": "1"}
