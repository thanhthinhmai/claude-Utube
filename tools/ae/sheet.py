"""The cast sheet of an AE film (specs/034 research R1, contracts/files.md → cast/sheets/<id>/, contracts/rig.md).

plan() lists the pictures of each character (three views, the expressions and poses its needs name, a walk loop, or
one group picture); build() draws them in After Effects through the usual build path (one frame per picture in
master.mp4, kit/castsheet.jsx) and cut() splits master.mp4 into JPEG pictures (long side 720 px, at most 300 KB) and
a walk.mp4 (H.264, at most 400 px, 2.5 s, no sound). The sheet a character had before is kept as <id>.prev/ (one
only, FR-014); characters not asked for (--only) are not touched at all (SC-003)."""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from ae import film as filmdoc
from ae import rigs

WALK_FRAMES = 75
MAX_FRAMES = 100              # pictures per AE request (the bridge queue takes at most 100 shots)
JPEG_LONG = 720
JPEG_MAX = 300 * 1024
WALK_LONG = 400
VIEWS = (("front", "Front"), ("back", "Back"), ("34", "3/4 view"))


class SheetError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_cast(film_dir) -> dict:
    p = Path(film_dir) / "cast" / "cast.json"
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SheetError("no_cast", f"{p} does not exist: write the film's characters first (specs/034 contracts/files.md)")
    except (OSError, ValueError) as e:
        raise SheetError("bad_cast", f"cast/cast.json cannot be read: {e}")
    if not isinstance(doc, dict) or not isinstance(doc.get("characters"), list):
        raise SheetError("bad_cast", "cast/cast.json must have a characters list")
    return doc


def char_frames(c: dict, keep=()) -> list:
    """Pictures of one character in sheet order; keep: keys already approved elsewhere (not drawn again)."""
    rig = c.get("rig") or ""
    try:
        cat = rigs.catalog(rig)
    except (OSError, ValueError):
        cat = {"views": [], "expressions": [], "poses": [], "walk": False}
    out = []

    def add(key, group, label, kind, para=None, ok=True, why="", **kw):
        fr = {"character": c["id"], "key": key, "group": group, "label": label, "kind": kind,
              "len": WALK_FRAMES if kind == "walk" else 1}
        if para:
            fr["para"] = para
        if not ok:
            fr["missing_reason"] = why
        if key in keep:
            fr["keep"] = True
        fr.update(kw)
        out.append(fr)

    if c.get("kind") == "group":
        add("group", "group", c.get("name") or "Group", "group")
        return out
    for key, label in VIEWS:
        add(key, "turn", label, "view", view=key, ok=key in cat.get("views", []), why=f"not in the {rig} catalog")
    needs = c.get("needs") or {}
    for r in needs.get("expressions", []):
        add(f"expr-{r['key']}", "expr", r.get("label") or r["key"], "expr", r.get("para"), r["key"] in cat.get("expressions", []),
            f"expression {r['key']} is not in the {rig} catalog", view="front", expr=r["key"])
    for r in needs.get("poses", []):
        add(f"pose-{r['key']}", "pose", r.get("label") or r["key"], "pose", r.get("para"), r["key"] in cat.get("poses", []),
            f"pose {r['key']} is not in the {rig} catalog", view="front", pose=r["key"])
    if needs.get("walk"):
        add("walk", "walk", "Walk loop", "walk", ok=bool(cat.get("walk")), why=f"the {rig} rig has no walk", view="front")
    return out


def plan(film_dir, only=None, keep: dict = None) -> dict:
    """{fps, cast, characters:[ids], frames:[…drawable…], all:{id: [every picture, drawn or not]}}."""
    d = Path(film_dir)
    doc = filmdoc.require_ae(d)
    cast = load_cast(d)
    ids = [c["id"] for c in cast["characters"] if isinstance(c, dict) and c.get("id")]
    if only:
        unknown = [i for i in only if i not in ids]
        if unknown:
            raise SheetError("no_character", f"no character {', '.join(unknown)} in cast/cast.json")
        ids = [i for i in ids if i in only]
    keep = keep or {}
    allf, frames = {}, []
    for c in cast["characters"]:
        if c.get("id") not in ids:
            continue
        fl = char_frames(c, keep.get(c["id"], ()))
        allf[c["id"]] = fl
        frames += [f for f in fl if "missing_reason" not in f and not f.get("keep")]
    return {"fps": doc["fps"], "cast": cast, "characters": ids, "frames": frames, "all": allf}


def chunks(p: dict) -> list:
    """Split a plan into AE requests of at most MAX_FRAMES pictures, never splitting a character."""
    out, cur, n = [], [], 0
    for cid in p["characters"]:
        fl = [f for f in p["frames"] if f["character"] == cid]
        if cur and n + len(fl) > MAX_FRAMES:
            out.append(cur); cur, n = [], 0
        cur += fl; n += len(fl)
    if cur:
        out.append(cur)
    return out


# ---------- cutting master.mp4 ----------
def _ff(args: list) -> None:
    r = subprocess.run(["ffmpeg", "-v", "error", "-y"] + args, capture_output=True, text=True)
    if r.returncode:
        raise SheetError("ffmpeg", (r.stderr or "ffmpeg failed").strip()[-400:])


def cut_jpeg(master: Path, t: float, out: Path) -> None:
    for q in (3, 5, 8, 12):
        _ff(["-ss", f"{t:.4f}", "-i", str(master), "-frames:v", "1",
             "-vf", f"scale='if(gt(iw,ih),{JPEG_LONG},-2)':'if(gt(iw,ih),-2,{JPEG_LONG})'", "-q:v", str(q), str(out)])
        if out.stat().st_size <= JPEG_MAX:
            return
    raise SheetError("too_big", f"{out.name} stays larger than 300 KB")


def cut_walk(master: Path, t0: float, dur: float, out: Path) -> None:
    _ff(["-ss", f"{t0:.4f}", "-i", str(master), "-t", f"{dur:.4f}", "-an",
         "-vf", f"scale='if(gt(iw,ih),{WALK_LONG},-2)':'if(gt(iw,ih),-2,{WALK_LONG})'",
         "-c:v", "libx264", "-crf", "26", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)])


def cut(master, marks: list, frames: list, fps: float, dest: Path, checks=()) -> dict:
    """Cut one AE result into dest/<character>/<key>.jpg|walk.mp4; returns {(character, key): file or why}."""
    master = Path(master)
    if len(marks) != len(frames):
        raise SheetError("bad_result", f"After Effects drew {len(marks)} pictures, the plan has {len(frames)}")
    missing = {}
    for c in checks:                    # CHECK missing <n> <character> <key>: why
        parts = c.split(" ", 5)
        if len(parts) >= 5 and parts[1] == "missing" and parts[2].isdigit():
            missing[int(parts[2])] = c.split(": ", 1)[-1] if ": " in c else "the rig could not draw it"
    got = {}
    for i, (m, fr) in enumerate(zip(marks, frames), start=1):
        folder = dest / fr["character"]
        folder.mkdir(parents=True, exist_ok=True)
        if i in missing:
            got[(fr["character"], fr["key"])] = {"why": f"build error: {missing[i]}"}
            continue
        if fr["kind"] == "walk":
            out = folder / "walk.mp4"
            cut_walk(master, m[0], m[1] - m[0], out)
        else:
            out = folder / f"{fr['key']}.jpg"
            cut_jpeg(master, m[0] + 0.5 / fps, out)
        got[(fr["character"], fr["key"])] = {"file": out.name}
    return got


# ---------- writing the sheets ----------
def sheet_json(c: dict, frames: list, got: dict) -> dict:
    rows = []
    for f in frames:
        r = {"key": f["key"], "group": f["group"], "label": f["label"]}
        if f.get("para"):
            r["para"] = f["para"]
        g = got.get((f["character"], f["key"])) or {}
        if "missing_reason" in f:
            r["file"], r["missing_reason"] = None, f["missing_reason"]
        elif g.get("file"):
            r["file"] = g["file"]
        else:
            r["file"], r["missing_reason"] = None, g.get("why") or "not drawn"
        rows.append(r)
    return {"character": c["id"], "rig": c.get("rig"), "built_at": now(), "frames": rows}


def write_json(p: Path, doc) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def install(film_dir, p: dict, stage: Path, got: dict, carry: dict = None) -> list:
    """Move each planned character's new pictures into cast/sheets/<id>/, the old sheet to <id>.prev/ (one only).
    carry: {id: folder} with pictures kept from elsewhere (the channel's cast library) for the frames marked keep."""
    d = Path(film_dir)
    sheets = d / "cast" / "sheets"
    sheets.mkdir(parents=True, exist_ok=True)
    out = []
    for c in p["cast"]["characters"]:
        cid = c.get("id")
        if cid not in p["characters"]:
            continue
        frames = p["all"][cid]
        new = stage / cid
        new.mkdir(parents=True, exist_ok=True)
        for f in frames:
            if f.get("keep") and carry and carry.get(cid):
                name = "walk.mp4" if f["kind"] == "walk" else f"{f['key']}.jpg"
                src = Path(carry[cid]) / name
                if src.is_file():
                    shutil.copyfile(src, new / name)
                    got[(cid, f["key"])] = {"file": name}
        doc = sheet_json(c, frames, got)
        write_json(new / "sheet.json", doc)
        cur, prev = sheets / cid, sheets / f"{cid}.prev"
        if cur.exists():
            if prev.exists():
                shutil.rmtree(prev)
            os.replace(cur, prev)
        shutil.move(str(new), str(cur))
        out.append({"character": cid, "pictures": sum(1 for r in doc["frames"] if r["file"]),
                    "missing": [(r["key"], r["missing_reason"]) for r in doc["frames"] if not r["file"]]})
    return out


def write_catalog(film_dir, cast: dict) -> None:
    rigset = sorted({c.get("rig") for c in cast["characters"] if c.get("rig")}, key=lambda r: rigs.parse(r) if rigs.RIG_ID.fullmatch(r) else ("", 0))
    if not rigset:
        return
    top = rigset[-1]
    try:
        cat = rigs.catalog(top)
    except (OSError, ValueError):
        return
    write_json(Path(film_dir) / "cast" / "catalog.json",
               {"rig": top, "views": cat.get("views", []), "expressions": cat.get("expressions", []),
                "poses": cat.get("poses", []), "walk": bool(cat.get("walk"))})


def build(film_dir, run, only=None, keep: dict = None, carry: dict = None, progress=None) -> list:
    """Draw the planned pictures with run(film_dir, None, progress=…, sheet=…) (local.build or remote.build)."""
    d = Path(film_dir)
    p = plan(d, only, keep)
    write_catalog(d, p["cast"])
    stage = d / "cast" / ".stage"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    got = {}
    try:
        for part in chunks(p):
            sub = {"fps": p["fps"], "cast": p["cast"], "frames": part}
            r = run(d, None, progress=progress, sheet=sub)
            got.update(cut(r["master"], r["marks"], part, p["fps"], stage, r.get("checks") or []))
        return install(d, p, stage, got, carry)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
