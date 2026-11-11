"""credits-check.py (specs/016 T008, SC-005): parts of a core compared with CREDITS, on a fake core tree."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("credits_check", REPO / "desktop" / "core-build" / "credits-check.py")
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)

NAMED = "\n".join(f"- {n} stuff" for n in cc.NAMED) + "\n- Debian packages of the core\n"


class CreditsCheck(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="core."))
        d = self.root / "tools/.venv/lib/python3.12/site-packages/Foo_Bar-1.0.dist-info"
        d.mkdir(parents=True)
        (d / "METADATA").write_text("Name: Foo_Bar\nLicense-Expression: MIT\n")
        n = self.root / "lib/lemo-opuscar/node_modules/@sc/pkg"
        n.mkdir(parents=True)
        (n / "package.json").write_text(json.dumps({"name": "@sc/pkg", "license": "ISC"}))
        s = self.root / "sys"
        (s / "var/lib/dpkg").mkdir(parents=True)
        (s / "var/lib/dpkg/status").write_text("Package: bash\n\nPackage: libfoo:amd64\n")
        (s / "usr/share/doc/bash").mkdir(parents=True)
        (s / "usr/share/doc/bash/copyright").write_text("GPL")

    def test_missing_then_complete(self):
        r = cc.check(self.root, self.root / "sys", "- Python only\n")
        self.assertIn("Node.js", r["named"])
        self.assertEqual(r["pip"], [("Foo_Bar", "MIT")])
        self.assertEqual(r["npm"], [("@sc/pkg", "ISC")])
        self.assertEqual(r["dpkg"], ["libfoo:amd64"])
        (self.root / "sys/usr/share/doc/libfoo").mkdir(parents=True)
        (self.root / "sys/usr/share/doc/libfoo/copyright").write_text("MIT")
        r = cc.check(self.root, self.root / "sys", NAMED + "- foo-bar (MIT)\n- @sc/pkg (ISC)\n")
        self.assertFalse(any(r.values()), r)

    def test_real_credits_names_every_part(self):
        text = (REPO / "CREDITS").read_text()
        self.assertEqual(cc.check(self.root, None, text)["named"], [])
