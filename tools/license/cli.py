"""License server commands (specs/017 contracts):
    python cli.py keygen [--out FILE]        print the public key; write the private key to FILE (mode 600)
    python cli.py admin-password             set the admin password (asked twice, never printed)
    python cli.py sign-release FILE          sign FILE with $LICENSE_SIGNING_KEY into FILE.sig
"""
import argparse
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signing  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="claude-Utube license server commands")
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("keygen")
    k.add_argument("--out", type=Path)
    sub.add_parser("admin-password")
    s = sub.add_parser("sign-release")
    s.add_argument("file", type=Path)
    a = ap.parse_args(argv)
    if a.cmd == "keygen":
        priv, pub = signing.new_keypair()
        if a.out:
            fd = os.open(a.out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(priv + "\n")
            print(f"private key written to {a.out} (keep it secret, back it up)", file=sys.stderr)
        else:
            print("private key (put it in LICENSE_SIGNING_KEY; keep it secret):", file=sys.stderr)
            print(priv, file=sys.stderr)
        print(pub)
        return 0
    if a.cmd == "admin-password":
        import store
        p1 = getpass.getpass("New admin password (12+ characters): ")
        if len(p1) < 12:
            print("✗ at least 12 characters", file=sys.stderr)
            return 1
        if getpass.getpass("Again: ") != p1:
            print("✗ the two passwords differ", file=sys.stderr)
            return 1
        store.Store.open().set_password(p1)
        print("✓ admin password set")
        return 0
    if a.cmd == "sign-release":
        priv = os.environ.get("LICENSE_SIGNING_KEY", "").strip()
        if not priv:
            print("✗ LICENSE_SIGNING_KEY is not set", file=sys.stderr)
            return 1
        sig = signing.sign_bytes(priv, a.file.read_bytes())
        Path(str(a.file) + ".sig").write_text(sig + "\n")
        print(f"✓ {a.file}.sig")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
