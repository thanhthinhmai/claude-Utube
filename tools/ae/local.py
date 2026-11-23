"""Run After Effects on this machine from the command line (specs/031 T007, research R3/R4).

Used outside a job (development machine: WSL with AE on Windows, or macOS). Inside the app a job goes through the
desktop app's bridge instead (tools/ae/remote.py). Steps: bundle → work/<id>/ → AfterFX -r entry.jsx (macOS:
osascript DoScriptFile) → wait for log.txt START … DONE → close AfterFX → aerender MASTER → master.mp4 + marks."""
import json
import os
import re
import secrets
import shutil
import subprocess
import time
from pathlib import Path

from ae import bundle

CONFIG = Path(os.environ.get("STUDIO_AE_CONFIG") or Path.home() / ".config" / "claude-utube" / "ae.json")
FAKE = Path(__file__).resolve().parents[2] / "desktop" / "test" / "fake-ae.mjs"
START_TIMEOUT = 120
SHOT_TIMEOUT = 300
MIN_FREE = 2 * 1024 ** 3
OM_TEMPLATE = "H.264 - Match Render Settings - 40 Mbps"
EXIT = {"ae_missing": 3, "ae_unavailable": 3, "ae_scripting_off": 3, "bridge_lost": 3}


class AeError(Exception):
    def __init__(self, code: str, message: str, log_tail: str = ""):
        super().__init__(message)
        self.code, self.message, self.log_tail = code, message, log_tail

    def exit_code(self) -> int:
        return EXIT.get(self.code, 1)


def load_config() -> dict:
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        return cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        return {}


def save_config(changes: dict) -> dict:
    cfg = load_config()
    cfg.update({k: v for k, v in changes.items() if v is not None})
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    tmp.replace(CONFIG)
    return cfg


def _newest(paths) -> str:
    def year(p):
        m = re.search(r"(20\d\d)", str(p))
        return int(m.group(1)) if m else 0
    paths = [p for p in paths if Path(p).exists()]
    return str(max(paths, key=year)) if paths else ""


def find_ae() -> dict:
    """Default install places: Windows seen from WSL (/mnt/c/Program Files/Adobe/…) or macOS /Applications."""
    win = list(Path("/mnt/c/Program Files/Adobe").glob("Adobe After Effects */Support Files/AfterFX.exe")) \
        if Path("/mnt/c/Program Files/Adobe").is_dir() else []
    if win:
        fx = _newest(win)
        return {"afterfx": fx, "aerender": str(Path(fx).with_name("aerender.exe"))}
    mac = list(Path("/Applications").glob("Adobe After Effects */Adobe After Effects *.app")) if Path("/Applications").is_dir() else []
    if mac:
        app = _newest(mac)
        return {"afterfx": app, "aerender": str(Path(app).parent / "aerender")}
    return {}


def settings() -> dict:
    """Paths in use: fake AE (STUDIO_AE_FAKE=1), else ae.json, else the default install places."""
    cfg = load_config()
    if os.environ.get("STUDIO_AE_FAKE") == "1":
        node = shutil.which("node") or "node"
        return {"kind": "fake", "afterfx": [node, str(FAKE), "afterfx"], "aerender": [node, str(FAKE), "aerender"],
                "work": cfg.get("work") or os.environ.get("STUDIO_AE_WORK") or "",
                "shotTimeoutSec": int(cfg.get("shotTimeoutSec") or os.environ.get("STUDIO_AE_SHOT_TIMEOUT") or SHOT_TIMEOUT),
                "startTimeoutSec": int(os.environ.get("STUDIO_AE_START_TIMEOUT") or START_TIMEOUT)}
    found = find_ae()
    fx = cfg.get("afterfx") or found.get("afterfx", "")
    kind = "windows" if fx.lower().endswith(".exe") else ("mac" if fx.endswith(".app") else "unknown")
    return {"kind": kind, "afterfx": fx, "aerender": cfg.get("aerender") or found.get("aerender", ""),
            "work": cfg.get("work", ""), "shotTimeoutSec": int(cfg.get("shotTimeoutSec") or SHOT_TIMEOUT),
            "startTimeoutSec": int(os.environ.get("STUDIO_AE_START_TIMEOUT") or START_TIMEOUT)}


def winpath(p) -> str:
    r = subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True)
    if r.returncode:
        raise AeError("bad_work", f"{p} is not a folder Windows can see; set a work folder under /mnt/<drive>/ "
                                  "with: sh bin/studio config ae --work /mnt/e/claude-utube-ae/work")
    return r.stdout.strip()


def check(s: dict) -> None:
    if s["kind"] == "fake":
        return
    if not s["afterfx"] or not Path(s["afterfx"]).exists():
        raise AeError("ae_missing", "After Effects was not found on this machine"
                      + (f" ({s['afterfx']})" if s["afterfx"] else "")
                      + "; set its path with: sh bin/studio config ae --afterfx <AfterFX.exe or .app> --aerender <aerender>")
    if not s["aerender"] or not Path(s["aerender"]).exists():
        raise AeError("ae_missing", f"aerender was not found ({s['aerender'] or 'no path'}); set it with: "
                                    "sh bin/studio config ae --aerender <path>")
    if s["kind"] == "unknown":
        raise AeError("ae_missing", f"{s['afterfx']} is neither AfterFX.exe nor an After Effects .app")


def free_bytes(folder) -> int:
    return shutil.disk_usage(folder).free


def _kill(s: dict, procs=()) -> None:
    for p in procs:
        if p and p.poll() is None:
            p.kill()
    if s["kind"] == "windows":
        for im in ("AfterFX.exe", "AfterFX.com", "aerender.exe"):
            subprocess.run(["/mnt/c/Windows/System32/taskkill.exe", "/IM", im, "/F"], capture_output=True)


def _path(s: dict, p) -> str:
    return winpath(p) if s["kind"] == "windows" else str(p)


def _argv(s: dict, tool: str) -> list:
    v = s[tool]
    return list(v) if isinstance(v, list) else [v]


def _tail(text: str, n: int = 20) -> str:
    return "\n".join(text.strip().splitlines()[-n:])


def run_script(s: dict, entry: Path):
    """Start AfterFX on the entry script; returns the process (may exit at once after handing the script to AE)."""
    if s["kind"] == "mac":
        script = f'tell application "{s["afterfx"]}" to DoScriptFile "{entry}"'
        return subprocess.Popen(["osascript", "-e", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cwd = entry.parent
    return subprocess.Popen(_argv(s, "afterfx") + ["-r", _path(s, entry)], cwd=cwd,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_log(s: dict, log: Path, shots: list, proc, progress=None, sleep=0.25) -> str:
    """Wait for START (start timeout), then a new line at least every shot timeout, until DONE."""
    t0 = time.time()
    last, seen, text = t0, 0, ""
    while True:
        text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        lines = text.splitlines()
        if lines and lines[-1].strip() == "DONE" or any(x.strip() == "DONE" for x in lines):
            return text
        if len(lines) > seen:
            seen, last = len(lines), time.time()
            done = [x for x in lines if re.match(r"shot \S+ ok", x)]
            if progress and done:
                progress({"state": "running", "shot": "S" + done[-1].split()[1], "index": len(done), "total": len(shots)})
        now = time.time()
        if not lines and now - t0 > s["startTimeoutSec"]:
            _kill(s, [proc])
            raise AeError("ae_scripting_off", "After Effects did not start the script in "
                          f"{s['startTimeoutSec']} s. Open After Effects once (a dialog may be waiting) and turn on "
                          "Edit > Preferences > Scripting & Expressions > \"Allow Scripts to Write Files and Access Network\".")
        if lines and now - last > s["shotTimeoutSec"]:
            _kill(s, [proc])
            raise AeError("ae_stalled", f"After Effects made no progress for {s['shotTimeoutSec']} s", _tail(text))
        time.sleep(sleep)


def render(s: dict, aep: Path, out: Path, timeout: float) -> str:
    cmd = _argv(s, "aerender") + ["-project", _path(s, aep), "-comp", "MASTER", "-OMtemplate", OM_TEMPLATE,
                                  "-output", _path(s, out)]
    try:
        r = subprocess.run(cmd, cwd=aep.parent, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        _kill(s)
        raise AeError("shot_timeout", f"aerender ran longer than {int(timeout)} s", _tail(str(e.stdout or "")))
    return (r.stdout or "") + (r.stderr or "")


def build(film_dir, shots=None, progress=None, s: dict = None) -> dict:
    """Build and render these shots on this machine; returns {master, marks, checks, log, dir}."""
    s = s or settings()
    check(s)
    work = Path(s["work"] or (Path.home() / ".cache" / "claude-utube-ae" if s["kind"] in ("fake", "mac") else ""))
    if not s["work"] and s["kind"] == "windows":
        raise AeError("bad_work", "set a work folder Windows can see: sh bin/studio config ae --work /mnt/e/claude-utube-ae/work")
    work.mkdir(parents=True, exist_ok=True)
    if free_bytes(work) < MIN_FREE:
        raise AeError("disk_low", f"the work folder {work} has less than 2 GB free")
    rid = time.strftime("ae-%Y%m%d-%H%M%S-") + secrets.token_hex(2)
    folder = work / rid
    b = bundle.make(film_dir, shots, folder.with_suffix(".tar"))
    bundle.extract(b["path"], folder)
    Path(b["path"]).unlink()
    return run_folder(s, folder, b["shots"], b["proj"], progress)


def run_folder(s: dict, folder: Path, shots: list, proj: str, progress=None) -> dict:
    """Run an unpacked bundle in folder (shared by the CLI and tests)."""
    log = folder / "log.txt"
    _kill(s)
    proc = run_script(s, folder / "entry.jsx")
    text = wait_log(s, log, shots, proc, progress)
    errs = [x for x in text.splitlines() if x.startswith("ERR")]
    checks = [x for x in text.splitlines() if x.startswith("CHECK ")]
    if proc.poll() is None and s["kind"] == "fake":
        proc.wait(timeout=10)
    if errs:
        raise AeError("build_error", errs[0], _tail(text))
    _kill(s, [proc])
    aep, out = folder / proj, folder / "master.mp4"
    marks_file = folder / f"shots_{proj[:-4]}.json"
    if not aep.exists() or not marks_file.exists():
        raise AeError("build_error", "After Effects finished but saved no project or shot marks", _tail(text))
    if progress:
        progress({"state": "running", "shot": "MASTER", "index": len(shots), "total": len(shots)})
    rlog = render(s, aep, out, s["shotTimeoutSec"] * max(1, len(shots)))
    if not out.exists() or out.stat().st_size == 0:
        raise AeError("render_error", "aerender wrote no video", _tail(rlog))
    marks = json.loads(marks_file.read_text(encoding="utf-8"))
    return {"master": str(out), "marks": marks["shots"], "duration": marks["duration"], "checks": checks,
            "log": text, "dir": str(folder)}
