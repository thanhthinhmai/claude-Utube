"""Blender of this machine (specs/038 T007, research R4): blender.json, default install places, Windows paths from WSL.

blender.json (~/.config/claude-utube/blender.json or $STUDIO_BLENDER_CONFIG):
  {"blender": "<blender.exe or Blender.app/Contents/MacOS/Blender>", "work": "<folder Blender can see>",
   "shotTimeoutSec": 3600, "secPerFrame": 2.0}
Blender is the user's own install (constitution VII): the studio never downloads or bundles it."""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

FAKE = Path(__file__).resolve().parents[2] / "desktop" / "test" / "fake-blender.mjs"
SHOT_TIMEOUT = 3600            # a 3 s 1080p shot on an integrated GPU takes ~7 min; long shots more
START_TIMEOUT = 120
SEC_PER_FRAME = 2.0            # measured on Intel UHD 730, EEVEE 8 samples, 1080p (2026-11-26); replaced by each real run
SOFTWARE = re.compile(r"llvmpipe|softpipe|swrast|swiftshader|microsoft basic render|\bsoftware\b", re.I)
WIN_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")


class BlenderError(Exception):
    EXIT = {"no_blender": 3, "gpu_software": 3, "bridge_lost": 3, "bad_work": 2}

    def __init__(self, code: str, message: str, log_tail: str = ""):
        super().__init__(message)
        self.code, self.message, self.log_tail = code, message, log_tail

    def exit_code(self) -> int:
        return self.EXIT.get(self.code, 1)


def config_path() -> Path:
    return Path(os.environ.get("STUDIO_BLENDER_CONFIG") or Path.home() / ".config" / "claude-utube" / "blender.json")


def load() -> dict:
    try:
        cfg = json.loads(config_path().read_text(encoding="utf-8"))
        return cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        return {}


def save(changes: dict) -> dict:
    cfg = load()
    cfg.update({k: v for k, v in changes.items() if v is not None})
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    tmp.replace(p)
    return cfg


def _version_key(p) -> tuple:
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", str(p))
    return tuple(int(x or 0) for x in m.groups()) if m else (0, 0, 0)


def find_default() -> str:
    """Newest Blender in the default install places: Windows seen from WSL, else macOS."""
    roots = [Path("/mnt/c/Program Files/Blender Foundation")]
    win = [p for r in roots if r.is_dir() for p in r.glob("Blender*/blender.exe")]
    if win:
        return str(max(win, key=_version_key))
    mac = Path("/Applications/Blender.app/Contents/MacOS/Blender")
    return str(mac) if mac.exists() else ""


def local_path(p: str) -> str:
    """A path this shell can open: E:\\tools\\b.exe → /mnt/e/tools/b.exe on WSL; other paths unchanged."""
    if WIN_DRIVE.match(p or ""):
        r = subprocess.run(["wslpath", "-u", p], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
        return "/mnt/" + p[0].lower() + "/" + p[3:].replace("\\", "/")
    return p


def win_path(p) -> str:
    """A path Windows Blender can open (wslpath -w); raises bad_work for folders Windows cannot see."""
    r = subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True)
    out = r.stdout.strip()
    if r.returncode or out.startswith("\\\\wsl"):
        raise BlenderError("bad_work", f"{p} is not a folder Windows can see; set a work folder under /mnt/<drive>/ with: "
                                       "sh bin/studio blender config --work /mnt/e/claude-utube-ae/blender")
    return out


def settings() -> dict:
    """Blender in use: fake (STUDIO_BLENDER_FAKE=1), else blender.json, else the default install place."""
    cfg = load()
    timeout = int(os.environ.get("STUDIO_BLENDER_SHOT_TIMEOUT") or cfg.get("shotTimeoutSec") or SHOT_TIMEOUT)
    common = {"shotTimeoutSec": timeout, "startTimeoutSec": int(os.environ.get("STUDIO_BLENDER_START_TIMEOUT") or START_TIMEOUT),
              "secPerFrame": float(cfg.get("secPerFrame") or SEC_PER_FRAME)}
    if os.environ.get("STUDIO_BLENDER_FAKE") == "1":
        return {"kind": "fake", "argv": [shutil.which("node") or "node", str(FAKE)],
                "work": os.environ.get("STUDIO_BLENDER_WORK") or "", "exe": str(FAKE), **common}
    exe = cfg.get("blender") or find_default()
    loc = local_path(exe) if exe else ""
    kind = "windows" if loc.lower().endswith(".exe") else ("mac" if loc else "unknown")
    return {"kind": kind, "argv": [loc] if loc else [], "exe": exe, "work": cfg.get("work", ""), **common}


def check(s: dict) -> None:
    if s["kind"] == "fake":
        return
    if not s["argv"] or not Path(s["argv"][0]).exists():
        raise BlenderError("no_blender", "Blender was not found on this machine" + (f" ({s['exe']})" if s.get("exe") else "")
                           + "; install it from blender.org, then: sh bin/studio blender config --exe <blender.exe>")
    if not s.get("work"):
        raise BlenderError("bad_work", "no Blender work folder; set one with: sh bin/studio blender config --work "
                                       "/mnt/e/claude-utube-ae/blender")


def host_path(s: dict, p) -> str:
    """How Blender sees a path of this shell."""
    return win_path(p) if s["kind"] == "windows" else str(p)
