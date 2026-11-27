"""camera stills (specs/039 R8): a quick ¼-size still of every camera option, drawn with the real set and characters.

Each shot is drawn once at quarter size with the camera at scale 1 on the middle of the picture:
  AE shots       one AE draft build of the shots with CU.CAMSTILL (every CU.camera holds scale 1), then the first frame
                 of each shot from the master (no voice needed: lengths come from timing.json or shots.json)
  Blender shots  `blender build S# --still 1 --quarter` with the camera block left out (a still camera at scale 1)
Then each option's still is that frame cut to the option's start window (start.scale, cx, cy), enlarged to 480×270, with
the end window drawn over it (yellow, 2 px) → films/<f>/camera/stills/S#-o<n>.jpg; options.json gets each `still`.
One build per shot instead of one per option: the 2D camera only scales and moves the drawn picture, so the cut is the
same frame AE would draw for that option (overlays left out of CAM aside).

Exit codes: 2 no options or a shot not written yet (ae/*.jsx, blender/S#.py) · 3 no After Effects, no Blender, no
GPU (a software render stops and asks, as every render of the studio) · 1 the build failed."""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from filmcheck import camsuggest, shotnotes

HERE = Path(__file__).resolve().parent
SIZE = (480, 270)
BOX = (255, 214, 0)


class StillError(Exception):
    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


def _film():
    sys.path.insert(0, str(HERE.parent))
    from ae import film as filmdoc
    return filmdoc


def written(d: Path, doc: dict, sid: str, engine: str) -> bool:
    """The shot's own code exists: blender/S#.py, or a CU.shot<N> function in ae/*.jsx."""
    if engine == "blender":
        return (d / "blender" / f"{sid}.py").is_file()
    pat = re.compile(rf"CU\.shot{re.escape(sid[1:])}\s*=\s*function")
    return any(pat.search((d / "ae" / f).read_text(encoding="utf-8", errors="replace"))
               for f in doc.get("ae_files") or [] if (d / "ae" / f).is_file())


# ---------- drawing (pure, tested) ----------
def windows(opt: dict, w: int, h: int):
    """(crop box of the start window, end box in the crop's own pixels at SIZE) for a frame w×h at scale 1."""
    st = opt["start"]
    s = float(st["scale"])
    cx, cy = st["cx"] / 100 * w, st["cy"] / 100 * h
    cw, ch = w / s, h / s
    crop = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    se = s * (1 + float(opt.get("zoom_pct") or 0) / 100)
    dx, dy = (opt.get("drift_px") or [0, 0])[:2]
    ex = cx + float(dx) / 1920 * w / se
    ey = cy + float(dy) / 1080 * h / se
    ew, eh = w / se, h / se
    k = SIZE[0] / cw
    end = ((ex - ew / 2 - crop[0]) * k, (ey - eh / 2 - crop[1]) * k, (ex + ew / 2 - crop[0]) * k, (ey + eh / 2 - crop[1]) * k)
    return crop, end


def draw(base, opt: dict):
    """The option's still (PIL image) from the scale-1 frame."""
    from PIL import ImageDraw
    crop, end = windows(opt, *base.size)
    img = base.crop(tuple(round(x) for x in crop)).resize(SIZE)
    dr = ImageDraw.Draw(img)
    x0, y0, x1, y1 = (max(1, min(SIZE[0] - 2, end[0])), max(1, min(SIZE[1] - 2, end[1])),
                      max(1, min(SIZE[0] - 2, end[2])), max(1, min(SIZE[1] - 2, end[3])))
    dr.rectangle((x0, y0, x1, y1), outline=BOX, width=2)
    return img


# ---------- builds ----------
def _ae_frames(d: Path, shots: list, ae_build, tmp: Path) -> dict:
    """{shot: png} — one AE draft build with CU.CAMSTILL, first frame of each shot."""
    old = os.environ.get("STUDIO_AE_CAMSTILL")
    os.environ["STUDIO_AE_CAMSTILL"] = "1"
    try:
        r = ae_build(d, shots)
    finally:
        if old is None:
            os.environ.pop("STUDIO_AE_CAMSTILL", None)
        else:
            os.environ["STUDIO_AE_CAMSTILL"] = old
    out = {}
    for m in r.get("marks") or []:
        sid = str(m[3])
        if sid not in shots:
            continue
        png = tmp / f"{sid}.png"
        t = float(m[0]) + 0.5 / 30
        p = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(r["master"]), "-frames:v", "1",
                            str(png)], capture_output=True, text=True)
        if p.returncode or not png.is_file():
            raise StillError(f"{sid}: no first frame in the AE build ({p.stderr.strip()[-200:]})")
        out[sid] = png
    missing = [s for s in shots if s not in out]
    if missing:
        raise StillError(f"the AE build has no {', '.join(missing)}")
    return out


def _blender_frames(d: Path, doc: dict, shots: list, blender_build) -> dict:
    doc = json.loads(json.dumps(doc))
    for s in shots:                                     # the camera at scale 1: no camera block, no move
        p = doc.setdefault("shot_plan", {}).setdefault(s, {})
        p.pop("camera", None)
        p["move"] = "static"
    r = blender_build(d, doc, shots)
    gpu = r.get("gpu")
    if not gpu or str(gpu).lower() in ("none", "cpu", "software", "false"):
        raise StillError(f"Blender drew without a GPU ({gpu}): stop and ask the owner before any software render", 3)
    return {s: Path(p) for s, p in r["shots"].items()}


def default_ae_build(d: Path, shots: list) -> dict:
    sys.path.insert(0, str(HERE.parent))
    from ae import mixed
    return mixed.ae_runner()(d, shots, progress=None, draft=True)


def default_blender_build(d: Path, doc: dict, shots: list) -> dict:
    sys.path.insert(0, str(HERE.parent))
    from blender import bundle as bbundle
    from blender import cli as bcli
    req = bbundle.request(d, doc, shots, quarter=True, still={s: 1 for s in shots})
    return bcli.runner()(d, req)


def _engine_error(e: Exception) -> StillError:
    code = getattr(e, "exit_code", None)
    code = code() if callable(code) else code
    return StillError(f"{type(e).__name__}: {getattr(e, 'message', e)}", 3 if code == 3 else (code or 1))


def make(d: Path, shots=None, say=print, ae_build=None, blender_build=None) -> dict:
    from PIL import Image
    d = Path(d)
    t0 = time.time()
    filmdoc = _film()
    try:
        doc = filmdoc.require_ae(d)
    except filmdoc.FilmError as e:
        raise StillError(e.message, 2) from None
    o = camsuggest.load(d)
    if not o:
        raise StillError(f"no camera options: run `sh bin/studio camera suggest {d.name}`", 2)
    want = [s for s in (shots or list(o["shots"])) if s in o["shots"]]
    if not want:
        raise StillError("none of these shots has camera options", 2)
    eng = {s: filmdoc.engine_of(doc, s) for s in want}
    todo = [s for s in want if not written(d, doc, s, eng[s])]
    if todo:
        raise StillError(f"{', '.join(todo)} not written yet: write each shot's code (set, places, rough length) "
                         "right after Cast, then make the stills", 2)
    ae = [s for s in want if eng[s] == "ae"]
    bl = [s for s in want if eng[s] == "blender"]
    out_dir = d / "camera" / "stills"
    out_dir.mkdir(parents=True, exist_ok=True)
    made = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        bases = {}
        try:
            if ae:
                say(f"… AE: {len(ae)} shot(s) at ¼, camera at scale 1")
                bases.update(_ae_frames(d, ae, ae_build or default_ae_build, tmp))
            if bl:
                say(f"… Blender: {len(bl)} still(s) at ¼")
                bases.update(_blender_frames(d, doc, bl, blender_build or default_blender_build))
        except StillError:
            raise
        except Exception as e:                          # noqa: BLE001 (AE/Blender errors carry their exit codes)
            raise _engine_error(e) from None
        for s in want:
            base = Image.open(bases[s]).convert("RGB")
            for opt in o["shots"][s]["options"]:
                rel = f"camera/stills/{s}-o{opt['n']}.jpg"
                draw(base, opt).save(d / rel, quality=85)
                made[(s, opt["n"])] = rel
    with shotnotes.locked(camsuggest.opath(d)):        # only the still fields change
        cur = camsuggest.load(d) or o
        for (s, n), rel in made.items():
            for opt in (cur.get("shots", {}).get(s) or {}).get("options", []):
                if opt["n"] == n:
                    opt["still"] = rel
        shotnotes.write_atomic(camsuggest.opath(d), camsuggest._dump(cur))
    return {"stills": sorted(made.values()), "shots": want, "seconds": round(time.time() - t0, 1)}
