"""Write desktop/test/vectors/ (specs/017 T005): a test key pair, a lease and a signed release.json made by
signing.py, so the desktop app's Node code is checked against the Python side. Run again only to renew them."""
import json
from pathlib import Path

from helpers import REPO, device, signing

out = REPO / "desktop" / "test" / "vectors"
out.mkdir(parents=True, exist_ok=True)
priv, pub = signing.new_keypair()
payload = {"v": 1, "lid": "lic-1", "did": device(1), "label": "Test person", "iat": 1_800_000_000, "exp": 1_800_604_800, "keyExp": None}
release = json.dumps({"version": "0.2.0", "tag": "desktop-v0.2.0",
                      "files": [{"name": "claude-Utube-Setup-0.2.0.exe", "size": 3, "sha256": "a" * 64}]}, indent=1).encode()
(out / "vectors.json").write_text(json.dumps({
    "note": "TEST KEY ONLY (specs/017 T005); never used by a real license server",
    "public": pub, "private_test_only": priv, "device": device(1), "payload": payload,
    "lease": signing.sign_lease(priv, payload)}, indent=1) + "\n")
(out / "release.json").write_bytes(release)
(out / "release.json.sig").write_text(signing.sign_bytes(priv, release) + "\n")
print(out)
