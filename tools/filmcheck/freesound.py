"""Freesound, CC0 only, to fill what the library lacks (specs/037 FR-013, research R4).

APIv2 with a token (the user's free API key): text search filtered to `license:"Creative Commons 0"`, then the HQ Ogg
preview is fetched (a token cannot fetch originals). Every result's licence is checked again before anything is
fetched. Fetched sounds land in $STUDIO_DATA/sound/freesound/<id>.ogg with one library entry each.

The key: FREESOUND_API_KEY from the environment or `.env` on the command line; in the app the proxy holds it
(voicekeys "freesound") and runs this module itself. The key goes in the Authorization header, never in a URL, and is
never printed or logged. STUDIO_FREESOUND_URL points tests at a fake server."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://freesound.org"
CC0 = "Creative Commons 0"
FIELDS = "id,name,tags,description,license,username,duration,previews,url"
TIMEOUT = 30
FETCH_TOP = 3                    # how many CC0 results one gap fills


class FreesoundError(Exception):
    """code: no_key | invalid_key | network | api | not_cc0."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def base() -> str:
    return (os.environ.get("STUDIO_FREESOUND_URL") or API).rstrip("/")


def key() -> str:
    from filmcheck import eleven
    k = eleven.setting("FREESOUND_API_KEY")
    if not k:
        raise FreesoundError("no_key", "no Freesound key: set FREESOUND_API_KEY in .env (sh bin/studio sound key "
                             "freesound) or add it in the app's Settings")
    return k


def has_key() -> bool:
    try:
        return bool(key())
    except FreesoundError:
        return False


def redact(text: str, k: str = None) -> str:
    text = str(text)
    for v in filter(None, [k, os.environ.get("FREESOUND_API_KEY")]):
        text = text.replace(v, "…" + v[-4:] if len(v) > 4 else "…")
    return text


def _get(path: str, params: dict, k: str) -> bytes:
    url = base() + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": f"Token {k}", "User-Agent": "claude-utube-studio"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise FreesoundError("invalid_key", "Freesound refused the key") from None
        raise FreesoundError("api", f"Freesound said {e.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise FreesoundError("network", redact(f"Freesound could not be reached: {e}", k)) from None


def check(k: str) -> None:
    """One small search proves a key works (FreesoundError otherwise)."""
    _get("/apiv2/search/text/", {"query": "click", "page_size": 1, "fields": "id"}, k.strip())


def is_cc0(lic: str) -> bool:
    lic = (lic or "").lower()
    return "publicdomain/zero" in lic or lic.strip() == CC0.lower()


def search_cc0(query: str, dur: float = None, k: str = None, n: int = 8) -> list:
    """CC0 results only; anything else the server sends back is dropped (FR-013)."""
    k = k or key()
    lo, hi = (0.1, 30) if not dur else (max(0.05, dur / 4), max(dur * 4, 1.0))
    raw = _get("/apiv2/search/text/", {"query": query, "filter": f'license:"{CC0}" duration:[{lo:g} TO {hi:g}]',
                                       "fields": FIELDS, "page_size": n, "sort": "score"}, k)
    try:
        results = json.loads(raw).get("results", [])
    except ValueError:
        raise FreesoundError("api", "Freesound sent no JSON") from None
    return [r for r in results if is_cc0(r.get("license")) and r.get("previews", {}).get("preview-hq-ogg")]


def fetch(sound: dict, k: str = None) -> dict:
    """Fetch one CC0 sound's HQ Ogg preview and put it in the library. → the library row."""
    from filmcheck import soundlib
    if not is_cc0(sound.get("license")):
        raise FreesoundError("not_cc0", f"Freesound #{sound.get('id')} is not CC0")
    k = k or key()
    sid = int(sound["id"])
    url = sound["previews"]["preview-hq-ogg"]
    path = urllib.parse.urlsplit(url)
    rel = path.path + ("?" + path.query if path.query else "")
    if path.netloc and not url.startswith(base()):
        req = urllib.request.Request(url, headers={"User-Agent": "claude-utube-studio"})   # previews need no key
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                data = r.read()
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise FreesoundError("network", redact(f"the preview could not be fetched: {e}", k)) from None
    else:
        data = _get(rel, {}, k)
    folder = soundlib.sound_root() / "freesound"
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"{sid}.ogg"
    tmp = dest.with_suffix(".part")
    tmp.write_bytes(data)
    os.replace(tmp, dest)
    st = dest.stat()
    tags = sound.get("tags") or []
    row = {"id": f"fs:{sid}", "path": str(dest), "size": st.st_size, "mtime_ns": st.st_mtime_ns,
           "name": sound.get("name") or f"freesound {sid}", "category": "", "subcategory": "",
           "description": (sound.get("description") or "")[:1000], "keywords": " ".join(tags)[:2000],
           "duration": sound.get("duration"), "rate": None, "channels": None, "source": "freesound",
           "credit": f"Freesound #{sid} by {sound.get('username') or 'unknown'}", "url": sound.get("url") or "",
           "license": "cc0-1.0", "fetched_at": soundlib._now(), "ok": 1, "root": ""}
    try:
        m = soundlib.read_meta(dest)
        row.update(rate=m.get("rate"), channels=m.get("channels"), duration=row["duration"] or m.get("duration"))
    except (ValueError, OSError):
        pass
    c = soundlib.connect()
    soundlib.put(c, row)
    c.commit()
    c.close()
    return row


def fill(query: str, dur: float = None, k: str = None) -> int:
    """Fetch up to FETCH_TOP CC0 sounds for a gap that are not in the library yet. → how many came in."""
    from filmcheck import soundlib
    k = k or key()
    c = soundlib.connect()
    have = {r["id"] for r in c.execute("SELECT id FROM entry WHERE source = 'freesound'")}
    c.close()
    got = 0
    for s in search_cc0(query, dur, k)[:FETCH_TOP]:
        if f"fs:{s['id']}" in have:
            continue
        fetch(s, k)
        got += 1
    return got
