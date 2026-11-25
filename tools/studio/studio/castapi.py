"""The channel's cast library over HTTP (specs/034 US3, contracts/api.md → /cast-library).

The library lives in the studio app's store, per account (filmcheck/castlib.py): a request sees its own account's
library only. Outside the app (local mode, no account folder) the library is not available."""
import re
import sys
from pathlib import Path

from fastapi import APIRouter
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
    return {"channel": channel, "id": cid, "v": g["v"], "versions": g["versions"], "character": g["character"],
            "sheet": g["sheet"], "preview": preview}


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
