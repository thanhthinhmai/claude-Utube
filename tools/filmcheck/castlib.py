"""The channel's cast library (specs/034 US3, research R6/R9, contracts/files.md → "Cast library").

Approved characters live in the studio app's store only (never in git):
  <data>/accounts/<owner>/channels/<channel>/cast/index.json
  <data>/accounts/<owner>/channels/<channel>/cast/<id>/v<n>/{character.json, sheet/{sheet.json, *.jpg, walk.mp4}}
A written version never changes, except the list of films that used it. Saving a character whose rig and look match the
latest version only adds the film (or, when the film drew pictures the library lacks, writes a new version holding the
old and the new pictures); another look is a new version (FR-017). Writes hold a file lock on the channel's cast folder.
"""
import fcntl
import json
import os
import shutil
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from filmcheck import cast

HERE = Path(__file__).resolve().parent
BODY = ("rig", "kind", "spec", "members")
COPY = ("id", "name", "role", "kind", "rig", "spec", "members")


class LibraryError(cast.CastError):
    pass


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------- where the library is ----------
def _account_of(film_dir):
    """<data>/accounts/<owner> when the film lives in an app account (the app runs it), else None."""
    if not film_dir:
        return None
    p = Path(film_dir).resolve()
    if p.parent.name == "films" and p.parent.parent.parent.name == "accounts":
        return p.parent.parent
    return None


def _running_app():
    try:
        sys.path.insert(0, str(HERE.parent / "studio"))
        from studio import host
        project = Path(os.environ.get("STUDIO_ROOT") or HERE.parents[1])
        ptr = host.running_pointer(project)
        if not ptr:
            return None
        owner = host.owner_id(Path(ptr["data"]))
        return Path(ptr["data"]) / "accounts" / owner if owner else None
    except Exception:           # noqa: BLE001 — the app's state never stops a command
        return None


def root(film_dir=None):
    """The account folder holding the channels' casts: the film's own account (app), else the app running for this
    project (the chat flow, like cli.app_film), else None ("the app is not running")."""
    return _account_of(film_dir) or _running_app()


def available(film_dir=None) -> bool:
    return root(film_dir) is not None


def channel_of(doc: dict) -> str:
    return doc.get("channel") or "default"


def _cast_dir(acc: Path, channel: str) -> Path:
    if not cast.CHAR_ID.fullmatch(channel or ""):
        raise LibraryError("bad_channel", f"bad channel name {channel!r}")
    return Path(acc) / "channels" / channel / "cast"


def _need(film_dir=None) -> Path:
    acc = root(film_dir)
    if acc is None:
        raise LibraryError("no_app", "the app is not running: the channel's cast lives in the studio app "
                                     "(start it: sh bin/studio app start)")
    return acc


@contextmanager
def _locked(cdir: Path):
    cdir.mkdir(parents=True, exist_ok=True)
    with open(cdir / ".lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _write_json(p: Path, doc) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def _read(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


# ---------- reading ----------
def index(acc: Path, channel: str) -> dict:
    return _read(_cast_dir(acc, channel) / "index.json", {"characters": {}}) or {"characters": {}}


def channels(acc: Path) -> list:
    d = Path(acc) / "channels"
    return sorted(p.parent.parent.name for p in d.glob("*/cast/index.json")) if d.is_dir() else []


def version_dir(acc: Path, channel: str, cid: str, v: int) -> Path:
    return _cast_dir(acc, channel) / cid / f"v{int(v)}"


def get(acc: Path, channel: str, cid: str, v: int = None) -> dict:
    """{v, versions, character (character.json), sheet (sheet.json), dir} of one character (latest by default)."""
    if not cast.CHAR_ID.fullmatch(cid or ""):
        raise LibraryError("no_character", f"bad character id {cid!r}")
    ent = index(acc, channel)["characters"].get(cid)
    if not ent:
        raise LibraryError("no_character", f"no character {cid} in the {channel} cast")
    v = int(v or ent["latest"])
    d = version_dir(acc, channel, cid, v)
    ch = _read(d / "character.json")
    if not ch:
        raise LibraryError("no_character", f"{channel}/{cid} has no version {v}")
    return {"v": v, "versions": ent.get("versions", []), "character": ch,
            "sheet": _read(d / "sheet" / "sheet.json", {"frames": []}), "dir": d}


def listing(acc: Path, channel: str = None) -> list:
    """[{channel, characters:[{id, name, role, latest, rig, approved_at, films, new_rig}]}]."""
    from ae import rigs
    out = []
    for ch in ([channel] if channel else channels(acc)):
        rows = []
        for cid, ent in sorted(index(acc, ch)["characters"].items()):
            last = (ent.get("versions") or [{}])[-1]
            info = _read(version_dir(acc, ch, cid, ent["latest"]) / "character.json", {}) or {}
            try:
                newer = rigs.newer(last.get("rig") or "")
            except ValueError:
                newer = None
            rows.append({"id": cid, "name": ent.get("name") or cid, "role": info.get("role"), "latest": ent["latest"],
                         "rig": last.get("rig"), "approved_at": last.get("approved_at"),
                         "films": info.get("films", []), "new_rig": newer})
        out.append({"channel": ch, "characters": rows})
    return out


def _body(c: dict) -> dict:
    return {k: c.get(k) for k in BODY}


# ---------- saving ----------
def _pictures(sheet_dir: Path) -> dict:
    """{key: row} of the sheet's rows that have a file present."""
    doc = _read(Path(sheet_dir) / "sheet.json", {"frames": []}) or {"frames": []}
    return {r["key"]: r for r in doc.get("frames", []) if r.get("file") and (Path(sheet_dir) / r["file"]).is_file()}


def save(acc: Path, channel: str, c: dict, sheet_dir: Path, film: str, by: str = "local") -> tuple:
    """Save one approved character; returns (v, "new" | "added film" | "same")."""
    cdir = _cast_dir(acc, channel)
    sheet_dir = Path(sheet_dir)
    got = _pictures(sheet_dir)
    if not got:
        raise LibraryError("no_sheet", f"{c['id']} has no pictures to save")
    with _locked(cdir):
        idx = index(acc, channel)
        ent = idx["characters"].get(c["id"])
        last = None
        if ent:
            last = {"v": ent["latest"], "character": _read(version_dir(acc, channel, c["id"], ent["latest"]) / "character.json", {})}
        base_rows, base_dir = {}, None
        if last and _body(last["character"]) == _body(c):
            have = set(last["character"].get("frames_approved", []))
            if set(got) <= have:                          # the same character: only the film is added
                ch = last["character"]
                if film in ch.setdefault("films", []):
                    return last["v"], "same"
                ch["films"].append(film)
                _write_json(version_dir(acc, channel, c["id"], last["v"]) / "character.json", ch)
                return last["v"], "added film"
            base_dir = version_dir(acc, channel, c["id"], last["v"]) / "sheet"   # new pictures: old + new
            base_rows = _pictures(base_dir)
        v = (ent["latest"] if ent else 0) + 1
        while version_dir(acc, channel, c["id"], v).exists():
            v += 1
        final = version_dir(acc, channel, c["id"], v)
        tmp = final.with_name(f".v{v}.{os.getpid()}.tmp")
        if tmp.exists():
            shutil.rmtree(tmp)
        (tmp / "sheet").mkdir(parents=True)
        rows = {}
        for key, r in base_rows.items():
            shutil.copyfile(base_dir / r["file"], tmp / "sheet" / r["file"])
            rows[key] = r
        for key, r in got.items():
            shutil.copyfile(sheet_dir / r["file"], tmp / "sheet" / r["file"])
            rows[key] = r
        at = now()
        _write_json(tmp / "sheet" / "sheet.json", {"character": c["id"], "rig": c.get("rig"), "built_at": at,
                                                  "frames": list(rows.values())})
        ch = {k: c.get(k) for k in COPY if c.get(k) is not None}
        ch.update(frames_approved=sorted(rows), approved={"at": at, "by": by or "local", "film": film}, films=[film])
        _write_json(tmp / "character.json", ch)
        os.rename(tmp, final)
        ent = ent or {"versions": []}
        ent.update(name=c.get("name") or c["id"], latest=v)
        ent["versions"].append({"v": v, "rig": c.get("rig"), "approved_at": at})
        idx["characters"][c["id"]] = ent
        _write_json(cdir / "index.json", idx)
        return v, "new"


def save_approved(film_dir, ids, by: str = None) -> list:
    """After `cast approve --save`: save each approved character, mark it from_library; returns lines to print."""
    d = Path(film_dir)
    acc = root(d)
    if acc is None:
        return ["! the app is not running: approved, but not saved to the channel's cast"]
    doc = cast.load(d)
    channel = channel_of(doc)
    st = cast.states(d, doc)
    lines = []
    for cid in ids:
        c = cast.find(doc, cid)
        if st.get(cid) != "approved":
            continue
        v, what = save(acc, channel, c, cast.sheet_dir(d, cid), d.name, by or os.environ.get("STUDIO_USER") or "local")
        c["from_library"] = {"channel": channel, "id": cid, "v": v}
        lines.append(f"✓ {channel}/{cid}: v{v} ({what})")
    cast.save(d, doc)
    return lines


# ---------- using a character in a film ----------
def library_frames(film_dir, only=None) -> tuple:
    """For `ae sheet`: {id: [keys kept from the library]}, {id: library sheet folder} of the characters that came from
    the library and still look the same (their approved pictures are copied, not drawn again)."""
    d = Path(film_dir)
    acc = root(d)
    if acc is None:
        return {}, {}
    keep, carry = {}, {}
    try:
        doc = cast.load(d)
    except cast.CastError:
        return {}, {}
    for c in doc["characters"]:
        fl = c.get("from_library")
        if not fl or (only and c["id"] not in only):
            continue
        try:
            g = get(acc, fl["channel"], fl["id"], fl["v"])
        except (cast.CastError, KeyError):
            continue
        if _body(g["character"]) != _body(c):
            continue
        pics = _pictures(g["dir"] / "sheet")
        keep[c["id"]] = sorted(k for k in g["character"].get("frames_approved", []) if k in pics)
        carry[c["id"]] = str(g["dir"] / "sheet")
    return keep, carry


def parse_ref(ref: str) -> tuple:
    """"default/hero@2" → ("default", "hero", 2)."""
    ch, _, rest = (ref or "").partition("/")
    cid, _, v = rest.partition("@")
    if not ch or not cid or (v and not v.isdigit()):
        raise LibraryError("bad_ref", f"a library character looks like default/hero or default/hero@2, not {ref!r}")
    return ch, cid, int(v) if v else None


def use(film_dir, ref: str, by: str = "local") -> dict:
    """Put a library character in the film: its look into cast.json (the film's needs stay), its approved pictures into
    cast/sheets/<id>/. Approved (source library) when every picture the film needs is in the library."""
    from ae import sheet as aesheet
    d = Path(film_dir)
    acc = _need(d)
    channel, cid, v = parse_ref(ref)
    g = get(acc, channel, cid, v)
    doc = cast.load(d) if cast.exists(d) else {"version": 1, "channel": channel, "save_to_library": True, "characters": []}
    old = next((c for c in doc["characters"] if c.get("id") == cid), None)
    c = {k: g["character"].get(k) for k in COPY if g["character"].get(k) is not None}
    c["needs"] = (old or {}).get("needs") or {"expressions": [], "poses": [], "walk": False}
    c["from_library"] = {"channel": channel, "id": cid, "v": g["v"]}
    c["approved"] = None
    if old:
        doc["characters"][doc["characters"].index(old)] = c
    else:
        doc["characters"].append(c)
    src = g["dir"] / "sheet"
    pics = _pictures(src)
    frames = aesheet.char_frames(c)
    sdir = cast.sheet_dir(d, cid)
    stage = sdir.with_name(f".{cid}.{os.getpid()}.use")
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    got, lacking = {}, []
    for f in frames:
        r = pics.get(f["key"])
        if r and f["key"] in g["character"].get("frames_approved", []):
            shutil.copyfile(src / r["file"], stage / r["file"])
            got[(cid, f["key"])] = {"file": r["file"]}
        elif "missing_reason" not in f:
            got[(cid, f["key"])] = {"why": f"not in the channel's cast yet: draw it with ae sheet {d.name} --only {cid}"}
            lacking.append(f["key"])
    aesheet.write_json(stage / "sheet.json", aesheet.sheet_json(c, frames, got))
    prev = sdir.with_name(f"{cid}.prev")
    if sdir.exists():
        if prev.exists():
            shutil.rmtree(prev)
        os.replace(sdir, prev)
    os.replace(stage, sdir)
    cast.save(d, doc)
    if not lacking:
        doc = cast.load(d)
        cc = cast.find(doc, cid)
        cc["approved"] = {"fingerprint": cast.char_fingerprint(d, cc), "at": now(), "by": by or "local", "source": "library"}
        cast.save(d, doc)
    return {"channel": channel, "id": cid, "v": g["v"], "approved": not lacking, "lacking": lacking}
