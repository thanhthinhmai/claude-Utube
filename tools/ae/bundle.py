"""The jsx bundle of one AE build request (specs/032 contracts/film-ae.md).

bundle.tar holds kit/*.jsx (the studio's shared kit), ae/<ae_files> (the film's own shots), data/ (the film's data:
measured camera moves, snaps), bundle.json and entry.jsx. entry.jsx sets CU.WORK to the folder it runs in, so the
same bundle runs from any work folder on Windows or macOS.

specs/034: the bundle also carries every locked rig version the film's cast/cast.json names plus the newest one
(kit/rigs/<family>/v<N>/), and entry.jsx defines CU.rig(id), CU.CAST (the film's characters) and CU.char(id, o), so a
shot always draws a character with the rig version and spec that were approved. sheet=… builds the cast sheet
(kit/castsheet.jsx) instead of the film's shots."""
import io
import json
import tarfile
from pathlib import Path

from ae import film as filmdoc
from ae import rigs

KIT = Path(__file__).resolve().parent / "kit"
KIT_FILES = ("lib.jsx", "chars.jsx", "scene.jsx", "persp.jsx", "build_core.jsx")
SHEET_FILE = "castsheet.jsx"
SHEET_DATA = "data/cast_sheet.json"
PROJ = "build.aep"
MAX_DATA = 50 * 1024 * 1024


def cast_doc(film_dir) -> dict:
    p = Path(film_dir) / "cast" / "cast.json"
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) and isinstance(doc.get("characters"), list) else {"characters": []}
    except (OSError, ValueError):
        return {"characters": []}


def rig_ids(cast: dict, extra=()) -> list:
    """Locked rig versions to carry: the ones the cast names (and extra), plus the newest of each family."""
    want = {c.get("rig") for c in cast.get("characters", []) if isinstance(c, dict)} | set(extra)
    fams = {rigs.parse(r)[0] for r in want if r and rigs.RIG_ID.fullmatch(r)} | {"ball"}
    want |= {rigs.latest(f) for f in fams}
    out = []
    for r in want:
        if not r or not rigs.RIG_ID.fullmatch(r):
            continue
        if not rigs.is_locked(r):
            raise filmdoc.FilmError("bad_rig", f"rig {r} is not in tools/ae/rigs.lock")
        out.append(r)
    return sorted(out, key=rigs.parse)


def rig_file(rig_id: str) -> str:
    fam, n = rigs.parse(rig_id)
    return f"rigs/{fam}/v{n}/{fam}.jsx"


def cast_js(cast: dict) -> str:
    """CU.CAST: {id: {rig, kind, spec | members, name}} of the film (approved data only, no notes)."""
    out = {}
    for c in cast.get("characters", []):
        if isinstance(c, dict) and isinstance(c.get("id"), str):
            out[c["id"]] = {k: c.get(k) for k in ("rig", "kind", "spec", "members", "name") if c.get(k) is not None}
    return json.dumps(out, ensure_ascii=False)


RIG_JS = """CU._rig = {};
CU.rig = function (id) { if (!CU.RIGS || !CU.RIGS[id]) { throw new Error("rig " + id + " is not in this bundle"); } return CU._rig[id] || (CU._rig[id] = CU.RIGS[id](CU)); };
CU.mergeSpec = function (a, b) { var o = {}, k; for (k in a) { if (a.hasOwnProperty(k)) { o[k] = a[k]; } } for (k in (b || {})) { if (b.hasOwnProperty(k)) { o[k] = b[k]; } } return o; };
// CU.char(id, o): a character of cast/cast.json drawn with its own rig version and spec (o: name, dur, view, keys, …;
// o.member = index for a group). Returns what the rig's make() returns ({comp, ctrl, …}).
CU.char = function (id, o) {
  var c = CU.CAST[id]; if (!c) { throw new Error("no character " + id + " in cast/cast.json"); }
  var spec = c.kind === "group" ? c.members[(o && o.member) || 0] : (c.spec || {});
  var p = CU.mergeSpec(spec, o); if (!p.name) { p.name = id; }
  if (p.hat && p.hat.kind === "none") { p.hat = null; }
  return CU.rig(c.rig).make(p);
};"""


def entry_text(doc: dict, shots: list, film_name: str, proj: str = PROJ, rig_list=(), cast: dict = None,
               sheet: bool = False) -> str:
    ids = ", ".join(json.dumps(s[1:]) for s in shots)
    w, h = doc["size"]
    lines = [f"// entry.jsx (tools/ae/bundle.py): builds {', '.join(shots)} of {film_name} into {proj}.",
             '#include "kit/lib.jsx"',
             'CU.WORK = (new File($.fileName)).parent.fsName.replace(/\\\\/g, "/");',
             'CU.MOTION = CU.WORK + "/data/motion/";',
             f"CU.FPS = {doc['fps']}; CU.W = {w}; CU.H = {h};"]
    lines += [f'#include "kit/{f}"' for f in KIT_FILES[1:]]
    lines += [f'#include "kit/{rig_file(r)}"' for r in rig_list]
    lines += [RIG_JS, f"CU.CAST = {cast_js(cast or {})};"]
    if sheet:
        lines += [f'#include "kit/{SHEET_FILE}"', f"CU.PROJ = {json.dumps(proj)};",
                  'CU.RENDER = "master.mp4";   // rendered inside After Effects (no aerender)',
                  f'CU.build(CU.castSheet(CU.readJSON(CU.WORK + "/{SHEET_DATA}")));', ""]
        return "\n".join(lines)
    lines += [f'#include "ae/{f}"' for f in doc["ae_files"]]
    lines += [f"CU.PROJ = {json.dumps(proj)};", 'CU.RENDER = "master.mp4";   // rendered inside After Effects (no aerender)',
              f"CU.build([{ids}]);", ""]
    return "\n".join(lines)


def _add(tar: tarfile.TarFile, name: str, data: bytes) -> None:
    ti = tarfile.TarInfo(name)
    ti.size, ti.mode, ti.mtime = len(data), 0o644, 0
    tar.addfile(ti, io.BytesIO(data))


def make(film_dir, shots=None, out=None, proj: str = PROJ, sheet: dict = None) -> dict:
    """Write bundle.tar for these shots (default: all); returns {path, shots, proj, files}.
    sheet: the cast sheet plan of tools/ae/sheet.py ({frames:[…], …}); the bundle then draws one shot per frame."""
    d = Path(film_dir)
    doc = filmdoc.require_ae(d)
    cast = sheet.get("cast") if sheet else cast_doc(d)
    if sheet:
        shots = [f"S{i + 1}" for i in range(len(sheet["frames"]))]
        if not shots:
            raise filmdoc.FilmError("bad_cast", "the cast sheet has no pictures to draw")
    else:
        shots = filmdoc.pick_shots(doc, shots)
    if not shots:
        raise filmdoc.FilmError("bad_shot", "film.json lists no shots")
    rig_list = rig_ids(cast)
    out = Path(out or d / "out" / "bundle.tar")
    out.parent.mkdir(parents=True, exist_ok=True)
    files, size = [], 0
    with tarfile.open(out, "w") as tar:
        for f in KIT_FILES + ((SHEET_FILE,) if sheet else ()):
            _add(tar, f"kit/{f}", (KIT / f).read_bytes()); files.append(f"kit/{f}")
        for r in rig_list:
            _add(tar, f"kit/{rig_file(r)}", (KIT / rig_file(r)).read_bytes()); files.append(f"kit/{rig_file(r)}")
        if sheet:
            _add(tar, SHEET_DATA, json.dumps(sheet, ensure_ascii=False).encode()); files.append(SHEET_DATA)
        for f in ([] if sheet else doc["ae_files"]):
            _add(tar, f"ae/{f}", (d / "ae" / f).read_bytes()); files.append(f"ae/{f}")
        data = d / "ae" / "data"
        if data.is_dir() and not sheet:
            for p in sorted(data.rglob("*")):
                if p.is_file() and not p.is_symlink() and "heads" not in p.relative_to(data).parts:
                    size += p.stat().st_size
                    if size > MAX_DATA:
                        raise filmdoc.FilmError("bundle_too_big", "ae/data is larger than 50 MB")
                    rel = "data/" + p.relative_to(data).as_posix()
                    _add(tar, rel, p.read_bytes()); files.append(rel)
        ti = tarfile.TarInfo("data/heads"); ti.type, ti.mode, ti.mtime = tarfile.DIRTYPE, 0o755, 0
        tar.addfile(ti)
        meta = {"film": d.name, "shots": shots, "proj": proj, "fps": doc["fps"], "size": doc["size"], "rigs": rig_list,
                "kind": "sheet" if sheet else "film"}
        _add(tar, "bundle.json", json.dumps(meta, ensure_ascii=False).encode())
        _add(tar, "entry.jsx", entry_text(doc, shots, d.name, proj, rig_list, cast, bool(sheet)).encode())
        files += ["bundle.json", "entry.jsx"]
    return {"path": str(out), "shots": shots, "proj": proj, "files": files}


def extract(tar_path, dest) -> Path:
    """Unpack a bundle safely (no absolute paths, no .., no links) into dest."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    root = dest.resolve()
    with tarfile.open(tar_path) as tar:
        for m in tar.getmembers():
            p = (root / m.name).resolve()
            if not p.is_relative_to(root) or m.issym() or m.islnk() or not (m.isfile() or m.isdir()):
                raise filmdoc.FilmError("bad_bundle", f"unsafe entry in bundle: {m.name}")
        try:
            tar.extractall(root, filter="data")
        except TypeError:          # Python before 3.12
            tar.extractall(root)
    return root
