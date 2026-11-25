"""The channel's cast library over HTTP (specs/034 US3, contracts/api.md → /cast-library).

The library lives in the studio app's store, per account (filmcheck/castlib.py): a request sees its own account's
library only. Outside the app (local mode, no account folder) the library is not available."""
import re
import sys
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse

from . import store
from .store import StudioError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from filmcheck import cast, castlib  # noqa: E402

router = APIRouter(prefix="/api/v1")
FILE = re.compile(r"[a-z0-9-]{1,40}\.(jpg|mp4)|sheet\.json")
TYPES = {"jpg": "image/jpeg", "mp4": "video/mp4", "json": "application/json"}


def library_root():
    """The account folder of this request (the app); None outside the app."""
    return store._account_root.get()


def _need():
    acc = library_root()
    if acc is None:
        raise StudioError("no_library", "the channel's cast lives in the studio app", 404)
    return acc


def _call(fn, *a):
    try:
        return fn(*a)
    except cast.CastError as e:
        raise StudioError("not_found" if e.code in ("no_character", "bad_channel") else e.code, e.message,
                          404 if e.code in ("no_character", "bad_channel") else 422) from None


@router.get("/cast-library")
def cast_library():
    acc = library_root()
    if acc is None:
        return {"available": False, "channels": []}
    return {"available": True, "channels": _call(castlib.listing, acc)}


@router.get("/cast-library/{channel}/{cid}")
def cast_library_character(channel: str, cid: str):
    acc = _need()
    g = _call(castlib.get, acc, channel, cid)
    prev = sorted(p.name for p in (g["dir"].parent).glob("v*.preview") if p.is_dir())
    preview = None
    if prev:
        pd = g["dir"].parent / prev[-1]
        preview = {"v": prev[-1][1:].split(".")[0], "sheet": castlib._read(pd / "sheet" / "sheet.json", {"frames": []}),
                   "character": castlib._read(pd / "character.json", {})}
    ent = castlib.index(acc, channel)["characters"][cid]
    pending = None
    if ent.get("pending"):
        pdir = castlib.version_dir(acc, channel, cid, ent["pending"])
        pending = {"v": ent["pending"], "character": castlib._read(pdir / "character.json", {}),
                   "sheet": castlib._read(pdir / "sheet" / "sheet.json", {"frames": []}),
                   "notes": castlib._read(pdir / "notes.json")}
    from ae import rigs
    try:
        new_rig = rigs.newer(g["character"].get("rig") or "")
    except ValueError:
        new_rig = None
    from . import jobs
    busy = [j["id"] for j in store.doc_list("job") if j.get("kind") == "fix" and j["status"] not in jobs.FINAL
            and (j.get("input") or {}).get("target") == "cast" and (j["input"].get("channel"), j["input"].get("character")) == (channel, cid)]
    return {"channel": channel, "id": cid, "v": g["v"], "versions": g["versions"], "character": g["character"],
            "sheet": g["sheet"], "preview": preview, "pending": pending, "new_rig": new_rig, "job": busy[0] if busy else None}


@router.get("/cast-library/{channel}/{cid}/{ver}/{name}")
def cast_library_file(channel: str, cid: str, ver: str, name: str):
    acc = _need()
    if not re.fullmatch(r"v[1-9][0-9]{0,3}(\.preview)?", ver) or not FILE.fullmatch(name) \
            or not cast.CHAR_ID.fullmatch(cid) or not cast.CHAR_ID.fullmatch(channel):
        raise StudioError("not_found", "no such file", 404)
    p = Path(acc) / "channels" / channel / "cast" / cid / ver / "sheet" / name
    if not p.is_file():
        raise StudioError("not_found", "no such file", 404)
    return FileResponse(p, media_type=TYPES[name.rsplit(".", 1)[1]], headers={"Cache-Control": "no-cache"})


# ---------- changes to the library (US4): a newer rig, notes, update, approve ----------
WRITE_ROLES = {"customer", "admin"}


class LibFixIn(BaseModel):
    rig: Optional[str] = Field(None, max_length=20)
    notes: Optional[List[str]] = Field(None, max_length=10)


def _writer(request: Request) -> dict:
    a = getattr(request.state, "account", None)
    if a is None:
        raise StudioError("app_only", "the channel's cast lives in the studio app (sh bin/studio app start)", 409)
    if a["role"] not in WRITE_ROLES:
        raise StudioError("forbidden", "this token may only read", 403)
    return a


def _fix_job(request: Request, channel: str, cid: str, mode: str, rig=None, notes=None) -> dict:
    a = _writer(request)
    acc = _need()
    _call(castlib.get, acc, channel, cid)
    from ae import aequeue
    st = aequeue.bridge_status()
    if not st["ready"]:
        raise StudioError(st["code"], st["message"], 409)
    from . import jobs
    busy = [j for j in store.doc_list("job", a["id"]) if j.get("kind") == "fix" and j["status"] not in jobs.FINAL
            and (j.get("input") or {}).get("target") == "cast" and (j["input"].get("channel"), j["input"].get("character")) == (channel, cid)]
    if busy:
        raise StudioError("in_progress", f"{channel}/{cid} is being redrawn ({busy[0]['id']})", 409)
    what = f"Preview {cid} with {rig}" if mode == "preview" else f"Fix {cid} in the {channel} cast"
    j = jobs.build("fix", what[:80], {}, owner=a["id"], status="queued", extra={"charged": False})
    j["input"] = {"kind": "fix", "target": "cast", "mode": mode, "channel": channel, "character": cid,
                  "rig": rig, "notes": notes or []}
    store.doc_put("job", j["id"], j)
    return {"job": j["id"]}


@router.post("/cast-library/{channel}/{cid}/preview", status_code=201)
def cast_library_preview(channel: str, cid: str, body: LibFixIn, request: Request):
    from ae import rigs
    if not body.rig or not rigs.RIG_ID.fullmatch(body.rig) or not rigs.is_locked(body.rig):
        raise StudioError("bad_rig", "rig: a locked rig version such as ball@2", 422)
    return _fix_job(request, channel, cid, "preview", rig=body.rig)


@router.post("/cast-library/{channel}/{cid}/fix", status_code=201)
def cast_library_fix(channel: str, cid: str, body: LibFixIn, request: Request):
    notes = [n.strip() for n in (body.notes or []) if isinstance(n, str) and n.strip()]
    if not notes or any(len(n) > castnotes_max() for n in notes):
        raise StudioError("invalid", "notes: 1 to 10 notes of 1 to 2000 characters", 422)
    return _fix_job(request, channel, cid, "library", notes=notes)


def castnotes_max() -> int:
    from filmcheck import castnotes
    return castnotes.TEXT_MAX


@router.post("/cast-library/{channel}/{cid}/update")
def cast_library_update(channel: str, cid: str, request: Request):
    _writer(request)
    return {"v": _call(castlib.update_from_preview, _need(), channel, cid)}


@router.post("/cast-library/{channel}/{cid}/approve")
def cast_library_approve(channel: str, cid: str, request: Request):
    a = _writer(request)
    return {"v": _call(castlib.approve_latest, _need(), channel, cid, a["email"])}
