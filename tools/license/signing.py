"""Ed25519 signatures for the desktop license (specs/017 research R2). Shared by the license server, the studio
core's gate (tools/studio/studio/gate.py) and the release workflow. Keys are base64 of the 32 raw bytes.

A lease is base64url(JSON) "." base64url(signature over the first part); times are in seconds."""
import base64
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

LEASE_DAYS = 7
CLOCK_SKEW_S = 600


def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def unb64u(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def new_keypair() -> tuple:
    """(private, public), each base64 of 32 raw bytes."""
    k = Ed25519PrivateKey.generate()
    priv = k.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    pub = k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(priv).decode(), base64.b64encode(pub).decode()


def public_of(priv_b64: str) -> str:
    k = Ed25519PrivateKey.from_private_bytes(base64.b64decode(priv_b64.strip()))
    return base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()


def sign_bytes(priv_b64: str, data: bytes) -> str:
    return b64u(Ed25519PrivateKey.from_private_bytes(base64.b64decode(priv_b64.strip())).sign(data))


def verify_bytes(pub_b64: str, data: bytes, sig: str) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(pub_b64.strip())).verify(unb64u(sig.strip()), data)
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def sign_lease(priv_b64: str, payload: dict) -> str:
    body = b64u(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    return body + "." + sign_bytes(priv_b64, body.encode())


def verify_lease(pub_b64: str, lease: str):
    """The payload of a lease with a good signature, or None."""
    if not isinstance(lease, str) or lease.count(".") != 1:
        return None
    body, sig = lease.split(".")
    if not verify_bytes(pub_b64, body.encode(), sig):
        return None
    try:
        p = json.loads(unb64u(body))
    except ValueError:
        return None
    return p if isinstance(p, dict) and p.get("v") == 1 else None


def lease_problem(payload, device_id: str, now: float, clock: float = 0):
    """Why a verified lease cannot be used now, or None (research R4)."""
    if not payload:
        return "signature"
    if payload.get("did") != device_id:
        return "device"
    if now < max(payload.get("iat", 0), clock or 0) - CLOCK_SKEW_S:
        return "clock"
    if payload.get("keyExp") and now >= payload["keyExp"]:
        return "key_expired"
    if now >= payload.get("exp", 0):
        return "expired"
    return None
