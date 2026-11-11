"""Storage of the license server (specs/017 data-model.md): SQLite in $LICENSE_DATA/license.db, a daily backup.
One process; every call opens its own connection."""
import hashlib
import os
import re
import secrets
import sqlite3
import threading
import time
import uuid
from pathlib import Path

import signing

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
MAX_DEVICES = 20
SESSION_S = 12 * 3600
BACKUPS_KEPT = 30
now = time.time                       # tests replace it

SCHEMA = """
CREATE TABLE IF NOT EXISTS licenses (
  id TEXT PRIMARY KEY, key_hash TEXT UNIQUE NOT NULL, key_last4 TEXT NOT NULL, label TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '', max_devices INTEGER NOT NULL DEFAULT 1, expires_at REAL, revoked_at REAL,
  created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS devices (
  id TEXT PRIMARY KEY, license_id TEXT NOT NULL REFERENCES licenses(id) ON DELETE CASCADE, device_id TEXT NOT NULL,
  device_name TEXT NOT NULL DEFAULT '', os TEXT NOT NULL DEFAULT '', app_version TEXT NOT NULL DEFAULT '',
  last_ip TEXT NOT NULL DEFAULT '', first_seen_at REAL NOT NULL, last_seen_at REAL NOT NULL, removed_at REAL,
  UNIQUE (license_id, device_id));
CREATE TABLE IF NOT EXISTS admin (id INTEGER PRIMARY KEY CHECK (id = 1), password_hash TEXT NOT NULL, updated_at REAL);
CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, created_at REAL NOT NULL, expires_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS events (at REAL NOT NULL, kind TEXT NOT NULL, license_id TEXT, detail TEXT NOT NULL DEFAULT '');
"""


class LicenseError(Exception):
    def __init__(self, code: str, message: str, status: int = 403):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def new_key() -> str:
    raw = "".join(secrets.choice(ALPHABET) for _ in range(16))
    return "CU-" + "-".join(raw[i:i + 4] for i in range(0, 16, 4))


def normalize_key(key) -> str | None:
    s = re.sub(r"[^A-Z0-9]", "", str(key or "").upper())
    if s.startswith("CU") and len(s) == 18:
        s = s[2:]
    return s if len(s) == 16 and all(c in ALPHABET for c in s) else None


def status_of(row) -> str:
    if row["revoked_at"]:
        return "revoked"
    if row["expires_at"] and row["expires_at"] <= now():
        return "expired"
    return "active"


class Store:
    def __init__(self, data: Path, signing_key: str | None = None):
        self.data = Path(data)
        self.data.mkdir(parents=True, exist_ok=True)
        self.db = self.data / "license.db"
        self.signing_key = (signing_key or "").strip() or None
        with self.con() as c:
            c.executescript(SCHEMA)

    @classmethod
    def open(cls):
        return cls(Path(os.environ.get("LICENSE_DATA", "/data")), os.environ.get("LICENSE_SIGNING_KEY"))

    def con(self):
        c = sqlite3.connect(self.db, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        return c

    def event(self, c, kind, license_id=None, detail=""):
        c.execute("INSERT INTO events VALUES (?,?,?,?)", (now(), kind, license_id, detail[:500]))

    # ---------- admin ----------
    def set_password(self, password: str):
        from argon2 import PasswordHasher
        with self.con() as c:
            c.execute("INSERT INTO admin (id, password_hash, updated_at) VALUES (1, ?, ?) "
                      "ON CONFLICT(id) DO UPDATE SET password_hash = excluded.password_hash, updated_at = excluded.updated_at",
                      (PasswordHasher().hash(password), now()))
            c.execute("DELETE FROM sessions")
            self.event(c, "admin_password")

    def has_password(self) -> bool:
        with self.con() as c:
            return c.execute("SELECT 1 FROM admin WHERE id = 1").fetchone() is not None

    def login(self, password: str) -> str | None:
        from argon2 import PasswordHasher
        from argon2.exceptions import VerifyMismatchError, InvalidHashError
        with self.con() as c:
            row = c.execute("SELECT password_hash FROM admin WHERE id = 1").fetchone()
            if not row:
                return None
            try:
                PasswordHasher().verify(row["password_hash"], password)
            except (VerifyMismatchError, InvalidHashError):
                return None
            token = secrets.token_urlsafe(32)
            c.execute("DELETE FROM sessions WHERE expires_at < ?", (now(),))
            c.execute("INSERT INTO sessions VALUES (?,?,?)", (sha(token), now(), now() + SESSION_S))
            self.event(c, "login")
            return token

    def session_ok(self, token: str | None) -> bool:
        if not token:
            return False
        with self.con() as c:
            return c.execute("SELECT 1 FROM sessions WHERE token_hash = ? AND expires_at > ?", (sha(token), now())).fetchone() is not None

    def logout(self, token: str | None):
        if token:
            with self.con() as c:
                c.execute("DELETE FROM sessions WHERE token_hash = ?", (sha(token),))

    # ---------- licenses ----------
    def list_licenses(self) -> list:
        with self.con() as c:
            lic = c.execute("SELECT * FROM licenses ORDER BY created_at DESC").fetchall()
            dev = c.execute("SELECT * FROM devices ORDER BY first_seen_at").fetchall()
        out = []
        for r in lic:
            out.append({"id": r["id"], "label": r["label"], "note": r["note"], "last4": r["key_last4"],
                        "maxDevices": r["max_devices"], "expiresAt": r["expires_at"], "revokedAt": r["revoked_at"],
                        "status": status_of(r), "createdAt": r["created_at"],
                        "devices": [{"deviceId": d["device_id"], "name": d["device_name"], "os": d["os"],
                                     "version": d["app_version"], "lastIp": d["last_ip"], "firstSeenAt": d["first_seen_at"],
                                     "lastSeenAt": d["last_seen_at"], "removedAt": d["removed_at"]}
                                    for d in dev if d["license_id"] == r["id"]]})
        return out

    @staticmethod
    def _fields(body: dict, partial: bool) -> dict:
        f = {}
        if "label" in body or not partial:
            label = str(body.get("label") or "").strip()
            if not label or len(label) > 80:
                raise LicenseError("invalid", "label needs 1–80 characters", 422)
            f["label"] = label
        if "note" in body:
            note = str(body.get("note") or "")
            if len(note) > 500:
                raise LicenseError("invalid", "note is at most 500 characters", 422)
            f["note"] = note
        if "maxDevices" in body:
            m = body.get("maxDevices")
            if not isinstance(m, int) or isinstance(m, bool) or not 1 <= m <= MAX_DEVICES:
                raise LicenseError("invalid", f"maxDevices is 1–{MAX_DEVICES}", 422)
            f["max_devices"] = m
        if "expiresAt" in body:
            e = body.get("expiresAt")
            if e is not None and (not isinstance(e, (int, float)) or isinstance(e, bool) or e <= 0):
                raise LicenseError("invalid", "expiresAt is seconds since 1970, or null", 422)
            f["expires_at"] = e
        return f

    def create_license(self, body: dict) -> str:
        f = self._fields(body, partial=False)
        key = new_key()
        norm = normalize_key(key)
        with self.con() as c:
            lid = str(uuid.uuid4())
            c.execute("INSERT INTO licenses (id, key_hash, key_last4, label, note, max_devices, expires_at, created_at) "
                      "VALUES (?,?,?,?,?,?,?,?)", (lid, sha(norm), norm[-4:], f["label"], f.get("note", ""),
                                                   f.get("max_devices", 1), f.get("expires_at"), now()))
            self.event(c, "create", lid, f["label"])
        return key

    def update_license(self, lid: str, body: dict):
        f = self._fields(body, partial=True)
        if "revoked" in body:
            f["revoked_at"] = now() if body["revoked"] else None
        with self.con() as c:
            if not c.execute("SELECT 1 FROM licenses WHERE id = ?", (lid,)).fetchone():
                raise LicenseError("not_found", "no such license", 404)
            for k, v in f.items():
                c.execute(f"UPDATE licenses SET {k} = ? WHERE id = ?", (v, lid))       # k is from a fixed list
            self.event(c, "revoke" if f.get("revoked_at") else "update", lid, ",".join(sorted(f)))

    def delete_license(self, lid: str):
        with self.con() as c:
            if c.execute("DELETE FROM licenses WHERE id = ?", (lid,)).rowcount == 0:
                raise LicenseError("not_found", "no such license", 404)
            self.event(c, "delete", lid)

    def remove_device(self, lid: str, device_id: str):
        """First time: the seat is free and this computer is refused. Second time: forgotten (may activate again)."""
        with self.con() as c:
            d = c.execute("SELECT id, removed_at FROM devices WHERE license_id = ? AND device_id = ?", (lid, device_id)).fetchone()
            if not d:
                raise LicenseError("not_found", "no such computer", 404)
            if d["removed_at"]:
                c.execute("DELETE FROM devices WHERE id = ?", (d["id"],))
                self.event(c, "device_forget", lid, device_id[:12])
            else:
                c.execute("UPDATE devices SET removed_at = ? WHERE id = ?", (now(), d["id"]))
                self.event(c, "device_remove", lid, device_id[:12])

    # ---------- leases ----------
    def lease_for(self, key, device_id: str, name="", os_name="", version="", ip="") -> dict:
        if not self.signing_key:
            raise LicenseError("not_configured", "this server has no signing key", 404)
        if not isinstance(device_id, str) or not re.fullmatch(r"[0-9a-f]{64}", device_id):
            raise LicenseError("invalid", "deviceId must be 64 hex characters", 422)
        norm = normalize_key(key)
        with self.con() as c:
            r = c.execute("SELECT * FROM licenses WHERE key_hash = ?", (sha(norm),)).fetchone() if norm else None
            if not r:
                raise LicenseError("unknown", "This key is not right.")
            st = status_of(r)
            if st == "revoked":
                raise LicenseError("revoked", "This key was turned off by the studio owner.")
            if st == "expired":
                raise LicenseError("expired", "This key has expired.")
            d = c.execute("SELECT * FROM devices WHERE license_id = ? AND device_id = ?", (r["id"], device_id)).fetchone()
            if d and d["removed_at"]:
                raise LicenseError("device_removed", "This computer was removed from the key by the studio owner.")
            t = now()
            vals = (str(name)[:80], str(os_name)[:40], str(version)[:20], str(ip)[:64])
            if d:
                c.execute("UPDATE devices SET device_name = ?, os = ?, app_version = ?, last_ip = ?, last_seen_at = ? WHERE id = ?",
                          (*vals, t, d["id"]))
            else:
                used = c.execute("SELECT COUNT(*) FROM devices WHERE license_id = ? AND removed_at IS NULL", (r["id"],)).fetchone()[0]
                if used >= r["max_devices"]:
                    raise LicenseError("device_limit", f"This key is already used on {used} of {r['max_devices']} computers.")
                c.execute("INSERT INTO devices (id, license_id, device_id, device_name, os, app_version, last_ip, first_seen_at, last_seen_at) "
                          "VALUES (?,?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), r["id"], device_id, *vals, t, t))
                self.event(c, "activate", r["id"], device_id[:12])
            exp = t + signing.LEASE_DAYS * 86400
            if r["expires_at"]:
                exp = min(exp, r["expires_at"])
            payload = {"v": 1, "lid": r["id"], "did": device_id, "label": r["label"], "iat": int(t), "exp": int(exp),
                       "keyExp": int(r["expires_at"]) if r["expires_at"] else None}
            return {"lease": signing.sign_lease(self.signing_key, payload), "label": r["label"],
                    "expiresAt": r["expires_at"], "serverTime": int(t)}

    def in_good_standing(self, lease: str | None) -> bool:
        """A signed, unexpired lease whose key and computer are still good right now (releases, R5)."""
        if not self.signing_key or not lease:
            return False
        p = signing.verify_lease(signing.public_of(self.signing_key), lease)
        if not p or signing.lease_problem(p, p.get("did"), now()):
            return False
        with self.con() as c:
            r = c.execute("SELECT * FROM licenses WHERE id = ?", (p.get("lid"),)).fetchone()
            if not r or status_of(r) != "active":
                return False
            d = c.execute("SELECT removed_at FROM devices WHERE license_id = ? AND device_id = ?", (r["id"], p["did"])).fetchone()
            return bool(d) and not d["removed_at"]

    # ---------- backup ----------
    def backup(self) -> Path:
        d = self.data / "backup"
        d.mkdir(exist_ok=True)
        out = d / time.strftime("license-%Y%m%d-%H%M%S.db", time.gmtime(now()))
        src, dst = sqlite3.connect(self.db), sqlite3.connect(out)
        with dst:
            src.backup(dst)
        src.close()
        dst.close()
        for old in sorted(d.glob("license-*.db"))[:-BACKUPS_KEPT]:
            old.unlink()
        return out

    def backup_daily(self):
        def loop():
            while True:
                try:
                    self.backup()
                except Exception as e:                       # keep serving; the log says why
                    print(f"backup failed: {e}", flush=True)
                time.sleep(86400)
        threading.Thread(target=loop, daemon=True).start()
