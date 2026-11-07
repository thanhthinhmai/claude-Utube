"""Online-mode test project: temporary data folder, mails written to files, a fake style library."""
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "studio"))


def _ui_helpers():
    """tests/ui/helpers.py (same module name as this file, so load it by path)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("ui_helpers", REPO / "tests" / "ui" / "helpers.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

ENV = ("STUDIO_ROOT", "STUDIO_MODE", "STUDIO_DATA", "MAIL_DIR", "STUDIO_URL")
W = {"X-Studio": "1"}
PASSWORD = "correct horse battery"


class OnlineProject:
    """STUDIO_ROOT is a project with a fake library (from the UI tests); STUDIO_DATA holds accounts and the DB."""

    def __init__(self):
        self.base = _ui_helpers().Project()     # films, sets, styles and a fake library
        self.dir = self.base.dir
        self.data = Path(tempfile.mkdtemp(prefix="online data."))
        self.mails = self.data / "outbox"
        self.old = {k: os.environ.get(k) for k in ENV}
        os.environ.update(STUDIO_ROOT=str(self.dir), STUDIO_MODE="online", STUDIO_DATA=str(self.data),
                          MAIL_DIR=str(self.mails), STUDIO_URL="https://studio.test")

    def close(self):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.data, ignore_errors=True)
        self.base.close()

    def client(self):
        from fastapi.testclient import TestClient
        from studio.server import create_app
        return TestClient(create_app(), base_url="https://studio.test")

    def flush_mail(self) -> list:
        from studio import mail
        mail.flush()
        return sorted(self.mails.glob("*.eml")) if self.mails.exists() else []

    def last_link(self, email: str, kind: str) -> str:
        """The token of the newest verify/reset mail sent to `email`."""
        for p in reversed(self.flush_mail()):
            text = p.read_text(errors="replace")
            if f"To: {email}" in text:
                m = re.search(rf"#/{kind}/([A-Za-z0-9_\-]+)", text)
                if m:
                    return m.group(1)
        raise AssertionError(f"no {kind} mail for {email}")

    def signup_verified(self, email: str, c=None):
        """A logged-in client of a new, verified customer."""
        c = c or self.client()
        r = c.post("/api/v1/auth/signup", json={"email": email, "password": PASSWORD, "accept_terms": True}, headers=W)
        assert r.status_code == 201, r.text
        assert c.post("/api/v1/auth/verify", json={"token": self.last_link(email, "verify")}, headers=W).status_code == 200
        assert c.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}, headers=W).status_code == 200
        return c

    def copy_fixtures_to(self, account_id: str):
        """Give a customer the demo film, set and style of the UI test project (their own copies)."""
        from studio import store
        d = store.account_dir(account_id)
        for sub in ("films", "references", "my-styles"):
            shutil.copytree(self.dir / sub, d / sub, dirs_exist_ok=True)
        return d


def account_id(c) -> str:
    return c.get("/api/v1/me").json()["id"]
