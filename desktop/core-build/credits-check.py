#!/usr/bin/env python3
"""Check that everything inside a built core is in CREDITS (specs/016 T008, SC-005).

    python3 credits-check.py --root <studio folder of the core> [--sys /] [--credits CREDITS] [--print]

- Python packages (every venv and the bundled Python of macOS) and the library's npm packages must each have a
  line "- <name> (<license>)" in CREDITS.
- Debian packages (Linux core) are covered by one group line; each must ship its copyright file in the Linux.
- A fixed list of named parts (Node.js, Chromium, FFmpeg, the models, …) must be named in CREDITS.
--print writes the missing lines in CREDITS format. Exit 0 when nothing is missing, 1 otherwise.
Python 3 standard library only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

NAMED = ["Python", "Node.js", "Chromium", "FFmpeg", "Kokoro", "Whisper", "espeak-ng", "lemo-opuscar", "Electron"]


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def _license(meta: str) -> str:
    for key in ("License-Expression", "License"):
        m = re.search(rf"^{key}: *(.+)$", meta, re.M)
        if m and m.group(1).strip() not in ("", "UNKNOWN") and len(m.group(1)) < 80:
            return m.group(1).strip()
    m = re.findall(r"^Classifier: License :: (?:OSI Approved :: )?(.+)$", meta, re.M)
    return "; ".join(m) if m else "see its METADATA"


def pip_packages(root: Path) -> dict:
    found = {}
    pats = ["tools/.venv/lib/python*/site-packages/*.dist-info", "lib/lemo-opuscar/.venv/lib/python*/site-packages/*.dist-info",
            "python/lib/python*/site-packages/*.dist-info"]
    for pat in pats:
        for d in root.glob(pat):
            meta = (d / "METADATA").read_text("utf-8", "replace") if (d / "METADATA").is_file() else ""
            m = re.search(r"^Name: *(.+)$", meta, re.M)
            if m:
                found.setdefault(norm(m.group(1)), (m.group(1).strip(), _license(meta)))
    return found


def npm_packages(root: Path) -> dict:
    found = {}
    nm = root / "lib" / "lemo-opuscar" / "node_modules"
    for pj in list(nm.glob("*/package.json")) + list(nm.glob("@*/*/package.json")):
        try:
            p = json.loads(pj.read_text("utf-8"))
        except (OSError, ValueError):
            continue
        name, lic = p.get("name"), p.get("license")
        if isinstance(lic, dict):
            lic = lic.get("type")
        if name:
            found.setdefault(norm(name), (name, lic or "see its package.json"))
    return found


def dpkg_without_copyright(sysroot: Path) -> list:
    status = sysroot / "var" / "lib" / "dpkg" / "status"
    if not status.is_file():
        return []
    missing = []
    for pkg in re.findall(r"^Package: *(\S+)$", status.read_text("utf-8", "replace"), re.M):
        base = pkg.split(":")[0]
        if not (sysroot / "usr" / "share" / "doc" / base / "copyright").exists():
            missing.append(pkg)
    return missing


def credited(text: str) -> set:
    return {norm(m) for m in re.findall(r"^- +([^\s(]+)", text, re.M)}


def check(root: Path, sysroot: Path | None, credits: str) -> dict:
    have = credited(credits)
    low = credits.lower()
    out = {"named": [n for n in NAMED if n.lower() not in low], "pip": [], "npm": [], "dpkg": []}
    for kind, pkgs in (("pip", pip_packages(root)), ("npm", npm_packages(root))):
        out[kind] = sorted((v for k, v in pkgs.items() if k not in have), key=lambda v: v[0].lower())
    if sysroot is not None:
        out["dpkg"] = dpkg_without_copyright(sysroot)
        if out["dpkg"] == [] and (sysroot / "var/lib/dpkg/status").is_file() and "debian packages" not in low:
            out["named"].append("Debian packages (group line)")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--sys", type=Path)
    ap.add_argument("--credits", type=Path, help="default: CREDITS of this repo")
    ap.add_argument("--print", action="store_true", dest="show")
    a = ap.parse_args(argv)
    credits = a.credits or Path(__file__).resolve().parents[2] / "CREDITS"
    r = check(a.root, a.sys, credits.read_text("utf-8"))
    bad = any(r.values())
    for n in r["named"]:
        print(f"✗ not named in CREDITS: {n}")
    for kind in ("pip", "npm"):
        for name, lic in r[kind]:
            print(f"- {name} ({lic})" if a.show else f"✗ {kind} package not in CREDITS: {name}")
    for p in r["dpkg"]:
        print(f"✗ Debian package without a copyright file: {p}")
    print("✓ every part is in CREDITS" if not bad else "✗ CREDITS is missing parts", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
