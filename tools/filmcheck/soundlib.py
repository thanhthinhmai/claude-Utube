"""The sound library on this machine (specs/037 US2, research R2, R3, R5, R11).

$STUDIO_DATA/sound/ (default ~/.local/share/claude-utube/sound), never in the repo:
- roots.json   the folders the owner added (Sonniss GDC packs);
- library.db   one row per sound file + an FTS5 index, built only from the file name, its folders, the header and the
               text chunks in the file (bext, LIST/INFO, iXML, FLAC/Ogg comments). No audio sample is ever read and no
               AI model ever hears a Sonniss sound (FR-013b: the Sonniss licence forbids AI use);
- freesound/   CC0 previews fetched to fill gaps (freesound.py).

Scope (FR-013a): Sonniss sounds are for the studio owner's films only; a customer's job sees CC0 sounds only.
Inside an app job the library is reached through the proxy (`/internal/sound/…`), never read directly."""
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import struct
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIO = {".wav", ".wave", ".bwf", ".flac", ".ogg", ".mp3", ".aif", ".aiff"}
SOURCES = ("sonniss", "freesound", "user")
LICENSES = {"sonniss": "sonniss-gdc-2.0", "freesound": "cc0-1.0"}
SCOPES = ("all", "cc0")
WEAK = 0.5                  # a top hit covering fewer query words than this sends find() to Freesound (FR-013)


class LibraryError(Exception):
    """code: forbidden | not_found | scope | no_library."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


# ---------- where things live ----------
def data_root() -> Path:
    return Path(os.environ.get("STUDIO_DATA") or Path.home() / ".local" / "share" / "claude-utube").expanduser().resolve()


def sound_root() -> Path:
    d = data_root() / "sound"
    d.mkdir(parents=True, exist_ok=True)
    return d


def repo() -> Path:
    return Path(os.environ.get("STUDIO_ROOT") or HERE.parents[1]).resolve()


def forbidden(path) -> str:
    """Why a folder may not be indexed (R11: reference audio never becomes a library sound), or ''."""
    p = Path(path).expanduser().resolve()
    for bad, why in ((repo() / "references", "reference videos"), (data_root() / "learn", "style-learning data")):
        if p == bad or bad in p.parents:
            return f"{p} holds {why}: reference audio never goes into the sound library"
    return ""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------- roots.json ----------
def roots() -> list:
    try:
        return json.loads((sound_root() / "roots.json").read_text(encoding="utf-8")).get("roots", [])
    except (OSError, ValueError):
        return []


def _save_roots(rows: list) -> None:
    f = sound_root() / "roots.json"
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps({"version": 1, "roots": rows}, indent=1), encoding="utf-8")
    os.replace(tmp, f)


def add_root(path, kind: str = "sonniss") -> dict:
    p = Path(path).expanduser().resolve()
    why = forbidden(p)
    if why:
        raise LibraryError("forbidden", why)
    if not p.is_dir():
        raise LibraryError("not_found", f"no such folder: {p}")
    rows = [r for r in roots() if Path(r["path"]) != p]
    row = {"path": str(p), "kind": kind, "added_at": _now()}
    _save_roots(rows + [row])
    return row


def remove_root(path) -> None:
    p = str(Path(path).expanduser().resolve())
    _save_roots([r for r in roots() if r["path"] != p])


# ---------- the database ----------
SCHEMA = """
CREATE TABLE IF NOT EXISTS entry (
  id TEXT PRIMARY KEY, path TEXT UNIQUE, size INTEGER, mtime_ns INTEGER, name TEXT, category TEXT, subcategory TEXT,
  description TEXT, keywords TEXT, duration REAL, rate INTEGER, channels INTEGER, source TEXT, credit TEXT,
  url TEXT DEFAULT '', license TEXT, fetched_at TEXT DEFAULT '', ok INTEGER DEFAULT 1, root TEXT DEFAULT '');
CREATE VIRTUAL TABLE IF NOT EXISTS entry_fts USING fts5(id UNINDEXED, name, category, subcategory, description, keywords,
  tokenize = 'unicode61');
"""
FIELDS = ("id", "path", "size", "mtime_ns", "name", "category", "subcategory", "description", "keywords", "duration",
          "rate", "channels", "source", "credit", "url", "license", "fetched_at", "ok", "root")


def connect() -> sqlite3.Connection:
    c = sqlite3.connect(sound_root() / "library.db", timeout=30)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


def put(c: sqlite3.Connection, row: dict) -> None:
    """Insert or replace one entry and its index row. license is set when a sound comes in and never changes after."""
    row = {k: row.get(k) for k in FIELDS}
    if row["source"] not in SOURCES:
        raise LibraryError("forbidden", f"unknown source {row['source']!r}")
    old = c.execute("SELECT license FROM entry WHERE id = ?", (row["id"],)).fetchone()
    if old and old["license"]:
        row["license"] = old["license"]
    row["ok"] = 1 if row.get("ok", 1) else 0
    c.execute(f"INSERT OR REPLACE INTO entry ({','.join(FIELDS)}) VALUES ({','.join('?' * len(FIELDS))})",
              [row[k] for k in FIELDS])
    c.execute("DELETE FROM entry_fts WHERE id = ?", (row["id"],))
    if row["ok"]:
        c.execute("INSERT INTO entry_fts (id, name, category, subcategory, description, keywords) VALUES (?,?,?,?,?,?)",
                  (row["id"], row["name"] or "", row["category"] or "", row["subcategory"] or "",
                   row["description"] or "", row["keywords"] or ""))


def drop(c: sqlite3.Connection, entry_id: str) -> None:
    c.execute("DELETE FROM entry WHERE id = ?", (entry_id,))
    c.execute("DELETE FROM entry_fts WHERE id = ?", (entry_id,))


# ---------- reading a file's header and text, never its samples ----------
def _txt(b: bytes) -> str:
    return b.split(b"\0", 1)[0].decode("utf-8", "replace").strip() if b else ""


def _xml_tag(xml: str, tag: str) -> str:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", xml, re.S | re.I)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def _riff(f, size: int) -> dict:
    """fmt, data size, bext, LIST/INFO, iXML of a RIFF/WAVE file; the data chunk is skipped with seek."""
    out = {"desc": [], "keys": [], "cat_id": "", "category": "", "subcategory": ""}
    rate = channels = block = 0
    data_len = None
    pos = 12
    while pos + 8 <= size:
        f.seek(pos)
        head = f.read(8)
        if len(head) < 8:
            break
        cid, n = head[:4], struct.unpack("<I", head[4:])[0]
        body_at = pos + 8
        if cid == b"fmt ":
            fmt = f.read(min(n, 40))
            if len(fmt) >= 16:
                _, channels, rate, _, block, _ = struct.unpack("<HHIIHH", fmt[:16])
        elif cid == b"data":
            data_len = min(n, size - body_at)
        elif cid == b"bext":
            out["desc"].append(_txt(f.read(min(n, 256))))
        elif cid == b"LIST":
            blob = f.read(min(n, 65536))
            if blob[:4] == b"INFO":
                i = 4
                while i + 8 <= len(blob):
                    k, m = blob[i:i + 4], struct.unpack("<I", blob[i + 4:i + 8])[0]
                    v = _txt(blob[i + 8:i + 8 + m])
                    if k in (b"INAM", b"ICMT", b"ISBJ") and v:
                        out["desc"].append(v)
                    elif k == b"IKEY" and v:
                        out["keys"].append(v)
                    i += 8 + m + (m & 1)
        elif cid == b"iXML":
            xml = f.read(min(n, 262144)).decode("utf-8", "replace")
            for tag in ("DESCRIPTION", "FXNAME"):
                v = _xml_tag(xml, tag)
                if v:
                    out["desc"].append(v)
            for tag in ("KEYWORDS",):
                v = _xml_tag(xml, tag)
                if v:
                    out["keys"].append(v)
            out["cat_id"] = _xml_tag(xml, "CATID")
            out["category"] = _xml_tag(xml, "CATEGORY")
            out["subcategory"] = _xml_tag(xml, "SUBCATEGORY")
        pos = body_at + n + (n & 1)
    if not rate or not channels or not block or data_len is None:
        raise ValueError("no fmt or data chunk")
    out.update(rate=rate, channels=channels, duration=round(data_len / (block * rate), 3))
    return out


def _ext80(b: bytes) -> float:
    exp = ((b[0] & 0x7F) << 8) | b[1]
    mant = int.from_bytes(b[2:10], "big")
    return 0.0 if exp == 0 and mant == 0 else mant * 2.0 ** (exp - 16383 - 63)


def _aiff(f, size: int) -> dict:
    pos = 12
    while pos + 8 <= size:
        f.seek(pos)
        head = f.read(8)
        cid, n = head[:4], struct.unpack(">I", head[4:])[0]
        if cid == b"COMM":
            c = f.read(18)
            channels, frames = struct.unpack(">hI", c[:6])
            rate = _ext80(c[8:18])
            return {"rate": int(rate), "channels": channels, "duration": round(frames / rate, 3) if rate else None,
                    "desc": [], "keys": []}
        pos += 8 + n + (n & 1)
    raise ValueError("no COMM chunk")


def _vorbis_comments(blob: bytes) -> dict:
    out = {}
    try:
        n = struct.unpack("<I", blob[:4])[0]
        i = 4 + n
        count = struct.unpack("<I", blob[i:i + 4])[0]
        i += 4
        for _ in range(min(count, 200)):
            m = struct.unpack("<I", blob[i:i + 4])[0]
            k, _, v = blob[i + 4:i + 4 + m].decode("utf-8", "replace").partition("=")
            out[k.upper()] = v
            i += 4 + m
    except (struct.error, IndexError):
        pass
    return out


def _from_comments(cm: dict) -> dict:
    desc = [cm[k] for k in ("TITLE", "DESCRIPTION", "COMMENT") if cm.get(k)]
    keys = [cm[k] for k in ("KEYWORDS", "GENRE") if cm.get(k)]
    return {"desc": desc, "keys": keys}


def _flac(f, size: int) -> dict:
    out = {"desc": [], "keys": []}
    f.seek(4)
    last = False
    while not last:
        h = f.read(4)
        if len(h) < 4:
            break
        last, kind, n = bool(h[0] & 0x80), h[0] & 0x7F, int.from_bytes(h[1:4], "big")
        blob = f.read(n) if kind in (0, 4) else (f.seek(n, 1) and b"")
        if kind == 0:
            v = int.from_bytes(blob[10:18], "big")
            rate, channels, total = v >> 44, ((v >> 41) & 7) + 1, v & ((1 << 36) - 1)
            out.update(rate=rate, channels=channels, duration=round(total / rate, 3) if rate else None)
        elif kind == 4:
            out.update(_from_comments(_vorbis_comments(blob)))
    if "rate" not in out:
        raise ValueError("no STREAMINFO")
    return out


def _ogg(f, size: int) -> dict:
    """Vorbis/Opus identification + comment headers, and the last page's granule position for the length."""
    first = f.read(min(size, 65536))
    out = {"desc": [], "keys": []}
    i = first.find(b"\x01vorbis")
    if i >= 0:
        channels, rate = first[i + 11], struct.unpack("<I", first[i + 12:i + 16])[0]
        j = first.find(b"\x03vorbis", i)
        if j >= 0:
            out.update(_from_comments(_vorbis_comments(first[j + 7:])))
    else:
        i = first.find(b"OpusHead")
        if i < 0:
            raise ValueError("not Vorbis or Opus")
        channels, rate = first[i + 9], 48000
        j = first.find(b"OpusTags", i)
        if j >= 0:
            out.update(_from_comments(_vorbis_comments(first[j + 8:])))
    f.seek(max(0, size - 65536))
    tail = f.read()
    k = tail.rfind(b"OggS")
    granule = struct.unpack("<q", tail[k + 6:k + 14])[0] if k >= 0 and len(tail) >= k + 14 else 0
    out.update(rate=rate, channels=channels, duration=round(granule / rate, 3) if granule > 0 and rate else None)
    return out


def _mp3(f, size: int) -> dict:
    out = {"desc": [], "keys": [], "rate": None, "channels": None, "duration": None}
    head = f.read(10)
    if head[:3] == b"ID3":
        n = (head[6] << 21) | (head[7] << 14) | (head[8] << 7) | head[9]
        tag = f.read(min(n, 262144))
        for fid in (b"TIT2", b"COMM"):
            i = tag.find(fid)
            if i >= 0:
                m = struct.unpack(">I", tag[i + 4:i + 8])[0]
                v = tag[i + 11:i + 10 + m].decode("latin-1", "replace").strip("\0 ")
                if v:
                    out["desc"].append(v)
    elif head[:2] != b"\xff\xfb" and head[:2] != b"\xff\xf3" and head[:2] != b"\xff\xf2":
        raise ValueError("not an mp3")
    return out


READERS = {".wav": _riff, ".wave": _riff, ".bwf": _riff, ".aif": _aiff, ".aiff": _aiff, ".flac": _flac, ".ogg": _ogg,
           ".mp3": _mp3}


def read_meta(path: Path) -> dict:
    """Header + text of one file. Raises ValueError when the file cannot be read as a sound."""
    size = path.stat().st_size
    with open(path, "rb") as f:
        magic = f.read(12)
        ext = path.suffix.lower()
        if ext in (".wav", ".wave", ".bwf") and not (magic[:4] in (b"RIFF", b"RF64") and magic[8:12] == b"WAVE"):
            raise ValueError("not RIFF/WAVE")
        if ext in (".aif", ".aiff") and not (magic[:4] == b"FORM" and magic[8:12] in (b"AIFF", b"AIFC")):
            raise ValueError("not AIFF")
        if ext == ".flac" and magic[:4] != b"fLaC":
            raise ValueError("not FLAC")
        if ext == ".ogg" and magic[:4] != b"OggS":
            raise ValueError("not Ogg")
        f.seek(0)
        return READERS[ext](f, size)


# ---------- indexing ----------
def entry_id(path) -> str:
    return "s:" + hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:12]


def _pack(path: Path, root: Path):
    """('Sonniss GDC 2024 · <pack>', year) from the folders between the root and the file."""
    rel = path.relative_to(root).parts
    chain = [root.name] + list(rel[:-1])
    year = ""
    for part in reversed(chain):
        m = re.search(r"GDC\s*[-_ ]?\s*(20\d\d)", part, re.I)
        if m:
            year = m.group(1)
            break
    pack = rel[0] if len(rel) > 1 else root.name
    return f"Sonniss GDC {year} · {pack}".replace("GDC  ·", "GDC ·"), pack


def describe(path: Path, root: Path, meta: dict) -> dict:
    from filmcheck import ucs
    stem = path.stem
    u = ucs.parse_name(stem)
    cat = meta.get("category") or u["category"]
    if not cat and meta.get("cat_id"):
        code, _ = ucs.split_catid(meta["cat_id"])
        cat = ucs.CATEGORIES.get(code, "")
    folders = " ".join(path.relative_to(root).parts[:-1])
    credit, _ = _pack(path, root)
    return {"name": stem.replace("_", " ").strip(), "category": (cat or "").upper(),
            "subcategory": (meta.get("subcategory") or u["subcategory"] or "").upper(),
            "description": " · ".join(dict.fromkeys(d for d in meta.get("desc", []) if d)),
            "keywords": " ".join(dict.fromkeys(meta.get("keys", []) + [folders]))[:2000],
            "duration": meta.get("duration"), "rate": meta.get("rate"), "channels": meta.get("channels"),
            "credit": credit}


def index(full: bool = False, progress=None) -> dict:
    """Index every root: only new or changed files are read (key (path, size, mtime_ns)); gone files lose their entry.
    → {new, changed, gone, broken, entries, secs}."""
    t = time.time()
    c = connect()
    known = {r["path"]: r for r in c.execute("SELECT id, path, size, mtime_ns, ok, root FROM entry WHERE source != 'freesound'")}
    seen, counts = set(), {"new": 0, "changed": 0, "gone": 0, "broken": 0}
    for r in roots():
        root = Path(r["path"])
        if forbidden(root) or not root.is_dir():
            continue
        kind = r.get("kind", "sonniss")
        for dirpath, dirs, files in os.walk(root):
            dirs.sort()
            for fn in sorted(files):
                p = Path(dirpath) / fn
                if p.suffix.lower() not in AUDIO or fn.startswith("._"):
                    continue
                sp = str(p)
                seen.add(sp)
                try:
                    st = p.stat()
                except OSError:
                    continue
                old = known.get(sp)
                if old and not full and old["size"] == st.st_size and old["mtime_ns"] == st.st_mtime_ns:
                    counts["broken"] += 0 if old["ok"] else 1
                    continue
                row = {"id": entry_id(sp), "path": sp, "size": st.st_size, "mtime_ns": st.st_mtime_ns, "source": kind,
                       "license": LICENSES.get(kind, ""), "root": str(root), "url": "", "fetched_at": ""}
                try:
                    row.update(describe(p, root, read_meta(p)), ok=1)
                except (ValueError, OSError, struct.error, IndexError, ZeroDivisionError):
                    row.update(name=p.stem.replace("_", " "), category="", subcategory="", description="",
                               keywords="", duration=None, rate=None, channels=None, credit=_pack(p, root)[0], ok=0)
                    counts["broken"] += 1
                put(c, row)
                counts["changed" if old else "new"] += 1
                if progress and (counts["new"] + counts["changed"]) % 500 == 0:
                    progress(counts)
    for sp, old in known.items():
        if sp not in seen:
            drop(c, old["id"])
            counts["gone"] += 1
    c.commit()
    counts["entries"] = c.execute("SELECT COUNT(*) FROM entry WHERE ok = 1").fetchone()[0]
    c.close()
    counts["secs"] = round(time.time() - t, 1)
    return counts


def status() -> dict:
    c = connect()
    by = {r["source"]: r["n"] for r in c.execute("SELECT source, COUNT(*) n FROM entry WHERE ok = 1 GROUP BY source")}
    broken = [r["path"] for r in c.execute("SELECT path FROM entry WHERE ok = 0 ORDER BY path LIMIT 50")]
    nb = c.execute("SELECT COUNT(*) FROM entry WHERE ok = 0").fetchone()[0]
    c.close()
    return {"roots": roots(), "by_source": by, "broken": nb, "broken_files": broken, "folder": str(sound_root())}


# ---------- search ----------
_WORD = re.compile(r"[A-Za-z0-9]+")


def words(q: str) -> list:
    return [w.lower() for w in _WORD.findall(q or "") if len(w) > 1 or w.isdigit()]


def public(row) -> dict:
    """What may leave the library: text only (R3), never the path of a file."""
    return {"id": row["id"], "name": row["name"], "category": row["category"], "subcategory": row["subcategory"],
            "duration": row["duration"], "source": row["source"], "credit": row["credit"], "license": row["license"],
            "url": row["url"] or ""}


def search(query: str, cat: str = None, dur: float = None, scope: str = "all", n: int = 8) -> list:
    """bm25 over name 3 · description 2 · keywords 2 · category 1, + when the category matches, − when the length is
    far from `dur`. Each hit has `score` and `cover` (share of the query words found in it)."""
    from filmcheck import ucs
    if scope not in SCOPES:
        raise LibraryError("scope", f"unknown scope {scope!r}")
    ws = words(query)
    if not ws:
        return []
    c = connect()
    match = " OR ".join(f'"{w}"*' for w in ws)
    sql = ("SELECT e.*, bm25(entry_fts, 0, 3.0, 1.0, 1.0, 2.0, 2.0) AS rank FROM entry_fts JOIN entry e ON e.id = entry_fts.id "
           "WHERE entry_fts MATCH ? AND e.ok = 1" + (" AND e.license = 'cc0-1.0'" if scope == "cc0" else "") +
           " ORDER BY rank LIMIT 200")
    try:
        rows = c.execute(sql, (match,)).fetchall()
    finally:
        c.close()
    out = []
    for r in rows:
        text = " ".join(str(r[k] or "") for k in ("name", "category", "subcategory", "description", "keywords")).lower()
        cover = sum(1 for w in ws if w in text) / len(ws)
        score = -r["rank"] + 2.0 * cover
        if cat and ucs.match(cat, r["category"] or ""):
            score += 3.0
        if dur and r["duration"]:
            ratio = max(r["duration"], 0.05) / max(dur, 0.05)
            score -= 1.5 * abs(math.log(ratio))
        d = public(r)
        d.update(score=round(score, 3), cover=round(cover, 2))
        out.append(d)
    out.sort(key=lambda d: (-d["score"], d["name"]))
    return out[:n]


def get(entry: str, scope: str = "all") -> dict:
    """The full row of one entry (path included: for the mixer and the proxy only)."""
    c = connect()
    r = c.execute("SELECT * FROM entry WHERE id = ?", (entry,)).fetchone()
    c.close()
    if not r:
        raise LibraryError("not_found", f"no sound {entry} in the library")
    d = dict(r)
    if scope == "cc0" and d["license"] != "cc0-1.0":
        raise LibraryError("scope", "this sound is for the studio owner's films only")
    return d


# ---------- jobs reach the library through the proxy ----------
def via_proxy() -> bool:
    return bool(os.environ.get("STUDIO_JOB_TOKEN") and os.environ.get("STUDIO_PROXY"))


def _proxy(path: str, body: dict) -> dict:
    import urllib.error
    import urllib.request
    req = urllib.request.Request(os.environ["STUDIO_PROXY"].rstrip("/") + path, data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json",
                                          "authorization": f"Bearer {os.environ['STUDIO_JOB_TOKEN']}"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read()).get("error", {})
        except ValueError:
            err = {}
        raise LibraryError(err.get("code") or "api", err.get("message") or f"proxy said {e.code}") from None


def find(query: str, cat: str = None, dur: float = None, scope: str = "all", n: int = 8, online: bool = True,
         key: str = None) -> list:
    """Search here; when the best hit is weak (or there is none) and a Freesound key is at hand, fetch CC0 sounds and
    search again (FR-013, automatic). Inside an app job everything goes through the proxy with the job's scope."""
    if via_proxy():
        return _proxy("/internal/sound/search", {"query": query, "cat": cat, "dur": dur})["results"]
    hits = search(query, cat, dur, scope, n)
    if online and (not hits or hits[0]["cover"] < WEAK):
        from filmcheck import freesound
        try:
            got = freesound.fill(query, dur, key)
        except freesound.FreesoundError:
            got = 0
        if got:
            hits = search(query, cat, dur, scope, n)
    return hits


def cache(entry: str, film_dir: Path, scope: str = "all") -> Path:
    """Copy one sound into films/<film>/sound/cache/ (R5), so a film mixes again with the library drive away."""
    film_dir = Path(film_dir)
    dest_dir = film_dir / "sound" / "cache"
    for p in dest_dir.glob(f"{safe(entry)}.*") if dest_dir.is_dir() else []:
        return p
    if via_proxy():
        r = _proxy("/internal/sound/fetch", {"entry": entry, "film": film_dir.name})
        return film_dir / r["path"]
    row = get(entry, scope)
    src = Path(row["path"])
    if forbidden(src):
        raise LibraryError("forbidden", forbidden(src))
    if not row["ok"] or not src.is_file():
        raise LibraryError("not_found", f"the file of {entry} is gone: {src.name}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{safe(entry)}{src.suffix.lower()}"
    shutil.copy2(src, dest)
    return dest


def safe(entry: str) -> str:
    return entry.replace(":", "_")
