"""No private key, real license key or GitHub token in the repo (specs/017 T023, SC-005). The test vectors' private
key is a TEST key and is marked as such; it is allowed only there."""
import re
import subprocess
import unittest

from helpers import REPO

PATTERNS = {
    "license key": re.compile(r"\bCU-(?!TEST-TEST-TEST-TEST)(?!XXXX)(?!ABCD-EFGH)[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}\b"),
    "GitHub token": re.compile(r"\b(ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b"),
    "signing key line": re.compile(r"^LICENSE_SIGNING_KEY=\S+", re.M),
}
ALLOWED = {"desktop/test/vectors/vectors.json"}


class Secrets(unittest.TestCase):
    def test_repo_has_no_secrets(self):
        files = subprocess.run(["git", "-C", str(REPO), "ls-files", "-co", "--exclude-standard"], capture_output=True,
                               text=True).stdout.split()
        found = []
        for f in files:
            if f in ALLOWED or f.startswith("lib/"):
                continue
            p = REPO / f
            try:
                text = p.read_text("utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for name, rx in PATTERNS.items():
                if rx.search(text):
                    found.append(f"{f}: {name}")
        self.assertEqual(found, [])

    def test_public_key_file_holds_only_a_public_key(self):
        text = (REPO / "desktop" / "license-public-key.txt").read_text().strip()
        self.assertTrue(text == "" or re.fullmatch(r"[A-Za-z0-9+/]{43}=", text), "one base64 public key, or empty")

    def test_vectors_are_marked_as_test_only(self):
        self.assertIn("TEST KEY ONLY", (REPO / "desktop" / "test" / "vectors" / "vectors.json").read_text())


if __name__ == "__main__":
    unittest.main()
