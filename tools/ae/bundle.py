"""The jsx bundle of one AE build request (specs/032 contracts/film-ae.md).

bundle.tar holds kit/*.jsx (the studio's shared kit), ae/<ae_files> (the film's own shots), data/ (the film's data:
measured camera moves, snaps), bundle.json and entry.jsx. entry.jsx sets CU.WORK to the folder it runs in, so the
same bundle runs from any work folder on Windows or macOS."""
import io
import json
import tarfile
from pathlib import Path

from ae import film as filmdoc

KIT = Path(__file__).resolve().parent / "kit"
KIT_FILES = ("lib.jsx", "chars.jsx", "scene.jsx", "persp.jsx", "build_core.jsx")
PROJ = "build.aep"
MAX_DATA = 50 * 1024 * 1024


def entry_text(doc: dict, shots: list, film_name: str, proj: str = PROJ) -> str:
    ids = ", ".join(json.dumps(s[1:]) for s in shots)
    w, h = doc["size"]
    lines = [f"// entry.jsx (tools/ae/bundle.py): builds {', '.join(shots)} of {film_name} into {proj}.",
             '#include "kit/lib.jsx"',
             'CU.WORK = (new File($.fileName)).parent.fsName.replace(/\\\\/g, "/");',
             'CU.MOTION = CU.WORK + "/data/motion/";',
             f"CU.FPS = {doc['fps']}; CU.W = {w}; CU.H = {h};"]
    lines += [f'#include "kit/{f}"' for f in KIT_FILES[1:]]
    lines += [f'#include "ae/{f}"' for f in doc["ae_files"]]
    lines += [f"CU.PROJ = {json.dumps(proj)};", 'CU.RENDER = "master.mp4";   // rendered inside After Effects (no aerender)',
              f"CU.build([{ids}]);", ""]
    return "\n".join(lines)


def _add(tar: tarfile.TarFile, name: str, data: bytes) -> None:
    ti = tarfile.TarInfo(name)
    ti.size, ti.mode, ti.mtime = len(data), 0o644, 0
    tar.addfile(ti, io.BytesIO(data))


def make(film_dir, shots=None, out=None, proj: str = PROJ) -> dict:
    """Write bundle.tar for these shots (default: all); returns {path, shots, proj, files}."""
    d = Path(film_dir)
    doc = filmdoc.require_ae(d)
    shots = filmdoc.pick_shots(doc, shots)
    if not shots:
        raise filmdoc.FilmError("bad_shot", "film.json lists no shots")
    out = Path(out or d / "out" / "bundle.tar")
    out.parent.mkdir(parents=True, exist_ok=True)
    files, size = [], 0
    with tarfile.open(out, "w") as tar:
        for f in KIT_FILES:
            _add(tar, f"kit/{f}", (KIT / f).read_bytes()); files.append(f"kit/{f}")
        for f in doc["ae_files"]:
            _add(tar, f"ae/{f}", (d / "ae" / f).read_bytes()); files.append(f"ae/{f}")
        data = d / "ae" / "data"
        if data.is_dir():
            for p in sorted(data.rglob("*")):
                if p.is_file() and not p.is_symlink() and "heads" not in p.relative_to(data).parts:
                    size += p.stat().st_size
                    if size > MAX_DATA:
                        raise filmdoc.FilmError("bundle_too_big", "ae/data is larger than 50 MB")
                    rel = "data/" + p.relative_to(data).as_posix()
                    _add(tar, rel, p.read_bytes()); files.append(rel)
        ti = tarfile.TarInfo("data/heads"); ti.type, ti.mode, ti.mtime = tarfile.DIRTYPE, 0o755, 0
        tar.addfile(ti)
        meta = {"film": d.name, "shots": shots, "proj": proj, "fps": doc["fps"], "size": doc["size"]}
        _add(tar, "bundle.json", json.dumps(meta, ensure_ascii=False).encode())
        _add(tar, "entry.jsx", entry_text(doc, shots, d.name, proj).encode())
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
