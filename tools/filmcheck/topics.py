"""Topic picker (specs/013): score candidate topics for one of the user's channels with public YouTube numbers,
keep the evidence, and keep a per-channel queue.

Fetching (research R1) costs at most ~220 YouTube units a topic; scoring (R2) is a pure function of the raw numbers,
so a recheck gives the same scores; the queue rules are in R4. Locally the key is read from YOUTUBE_API_KEY or
~/.config/claude-utube/youtube.key; online every call goes through the proxy, which holds the key (R5). The key is
never printed: every message from YouTube goes through redact()."""
import hashlib
import json
import math
import os
import re
import statistics
import tempfile
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

YOUTUBE = "https://www.googleapis.com/youtube/v3"
PRICE = {"search": 100, "videos": 1, "channels": 1, "playlistItems": 1}
ENDPOINTS = set(PRICE)
KEY_FILE = Path.home() / ".config" / "claude-utube" / "youtube.key"
MAX_TOPICS, MAX_SUGGEST, MAX_REFS, STALE_DAYS, CACHE_HOURS = 20, 10, 10, 14, 24
TYPES = ("explainer", "comparison", "list", "true story", "q&a", "other")
VERDICT_ORDER = {"PRIORITY": 0, "GO": 1, "HOLD": 2}
MEANINGFUL = 1000          # views: a video below this is neither demand nor a competitor (research, fix after the live run)
REGION = {"en": "US", "vi": "VN", "zh": "TW", "ja": "JP", "ko": "KR", "es": "ES", "fr": "FR", "de": "DE", "pt": "BR"}
CJK_LANGS = ("zh", "ja", "ko")
STOP = set("""a an and are as at be by can did do does for from has have how i in is it its of on or so that the this to
was what when where which who why will with you your vs versus about than then they them there these those we our
và của là có những một các cho với không được này đó khi thì mà vì sao như thế nào tại""".split())


class TopicError(Exception):
    """Bad input, no key, a broken key (exit code 2)."""


class QuotaError(Exception):
    """No YouTube units left today (exit code 3)."""


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(s: str) -> datetime:
    return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def pacific_day(t: datetime = None) -> str:
    """YouTube's quota day starts at midnight Pacific time (UTC−8, or −7 in summer: −8 is close enough here)."""
    return ((t or now_utc()) - timedelta(hours=8)).strftime("%Y-%m-%d")


def redact(text, key) -> str:
    text = str(text or "")
    if key:
        text = text.replace(key, f"…{key[-4:]}")
        text = text.replace(urllib.parse.quote(key, safe=""), f"…{key[-4:]}")
    return re.sub(r"(key=)[\w-]{10,}", r"\1…", text)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


# ---------- quota, cache, key (R5) ----------
class Usage:
    def __init__(self, path: Path, limit: int):
        self.path, self.limit = Path(path), int(limit)

    def read(self) -> dict:
        try:
            d = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            d = {}
        return d if d.get("day") == pacific_day() else {"day": pacific_day(), "units": 0}

    def today(self) -> int:
        return int(self.read()["units"])

    def charge(self, endpoint: str) -> int:
        d = self.read()
        cost = PRICE[endpoint]
        if d["units"] + cost > self.limit:
            raise QuotaError(f"YouTube units for today are used up ({d['units']} of {self.limit}); "
                             "they come back at midnight Pacific time")
        d["units"] += cost
        _write(self.path, json.dumps(d))
        return cost


class Cache:
    def __init__(self, folder: Path, hours: int = CACHE_HOURS):
        self.dir, self.hours = Path(folder), hours

    def _file(self, endpoint: str, params: dict) -> Path:
        h = hashlib.sha256((endpoint + json.dumps(params, sort_keys=True)).encode()).hexdigest()
        return self.dir / f"{h}.json"

    def get(self, endpoint, params):
        f = self._file(endpoint, params)
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return d["body"] if now_utc() - parse_time(d["at"]) < timedelta(hours=self.hours) else None

    def put(self, endpoint, params, body) -> None:
        _write(self._file(endpoint, params), json.dumps({"at": iso(now_utc()), "body": body}))


def read_key():
    k = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if k:
        return k
    try:
        return KEY_FILE.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def save_key(key: str) -> None:
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(KEY_FILE.parent, 0o700)
    fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(key.strip() + "\n")


def online_key_file(data_dir: Path) -> Path:
    return Path(data_dir) / "secrets" / "youtube.key"


def online_usage(data_dir: Path, limit: int) -> Usage:
    return Usage(Path(data_dir) / "youtube" / "usage.json", limit)


def online_cache(data_dir: Path) -> Cache:
    return Cache(Path(data_dir) / "youtube" / "cache")


def read_online_key(data_dir: Path):
    try:
        return online_key_file(data_dir).read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def save_online_key(data_dir: Path, key: str) -> None:
    f = online_key_file(data_dir)
    f.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(f.parent, 0o700)
    fd = os.open(f, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as out:
        out.write(key.strip() + "\n")


def no_template_params(params: dict) -> dict:
    """Times rounded to the hour, so a recheck within the hour hits the cache."""
    out = dict(params)
    for k in ("publishedAfter", "publishedBefore"):
        if k in out:
            out[k] = out[k][:13] + ":00:00Z"
    return out


class Fetcher:
    """`get(endpoint, params) -> dict`; `units` counts what this run spent (cache hits cost nothing)."""

    def __init__(self, call):
        self._call, self.units = call, 0

    def get(self, endpoint: str, params: dict) -> dict:
        if endpoint not in ENDPOINTS:
            raise TopicError(f"unknown YouTube endpoint {endpoint}")
        body, cost = self._call(endpoint, no_template_params(params))
        self.units += cost
        return body

    @classmethod
    def local(cls, key: str, usage: Usage, cache: Cache, base: str = None):
        base = (base or os.environ.get("STUDIO_YOUTUBE_URL") or YOUTUBE).rstrip("/")

        def call(endpoint, params):
            hit = cache.get(endpoint, params)
            if hit is not None:
                return hit, 0
            cost = usage.charge(endpoint)
            url = f"{base}/{endpoint}?" + urllib.parse.urlencode({**params, "key": key})
            try:
                with urllib.request.urlopen(url, timeout=30) as r:
                    body = json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                text = e.read().decode("utf-8", "replace")
                if "quotaExceeded" in text or "dailyLimitExceeded" in text:
                    raise QuotaError("YouTube says today's quota for this key is used up") from None
                raise TopicError("YouTube refused the call: " + redact(f"{e.code} {text[:300]}", key)) from None
            except (urllib.error.URLError, OSError, ValueError) as e:
                raise TopicError("YouTube could not be reached: " + redact(str(e), key)) from None
            cache.put(endpoint, params, body)
            return body, cost
        return cls(call)

    @classmethod
    def proxy(cls, url: str, token: str):
        def call(endpoint, params):
            req = urllib.request.Request(url.rstrip("/") + "/internal/youtube", method="POST",
                                         data=json.dumps({"endpoint": endpoint, "params": params}).encode(),
                                         headers={"authorization": "Bearer " + token, "content-type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    body = json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                text = e.read().decode("utf-8", "replace")
                if e.code == 429:
                    raise QuotaError("the studio's YouTube units for today are used up") from None
                raise TopicError(f"the studio could not reach YouTube ({e.code}): {text[:200]}") from None
            return body, int(body.pop("_units", 0) or 0)
        return cls(call)


# ---------- words ----------
def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", s or "").lower()


def is_cjk_text(s: str) -> bool:
    letters = [c for c in s if c.isalpha()]
    return bool(letters) and sum(unicodedata.east_asian_width(c) in ("W", "F") for c in letters) * 2 > len(letters)


def words(s: str) -> set:
    """Meaningful words: lowercase, no punctuation, no short or common words; CJK text as character pairs."""
    t = _norm(s)
    if is_cjk_text(t):
        chars = [c for c in t if c.isalnum()]
        return {a + b for a, b in zip(chars, chars[1:])}
    return {w for w in re.findall(r"\w+", t) if len(w) >= 3 and w not in STOP}


def similarity(a: str, b: str) -> float:
    x, y = words(a), words(b)
    return len(x & y) / len(x | y) if x and y else 0.0


def on_topic(title: str, topic: str) -> bool:
    """At least half of the topic's meaningful words are in the title (R1: drops what YouTube adds off-topic)."""
    tw = words(topic)
    return not tw or len(tw & words(title)) * 2 >= len(tw)


def script_ok(title: str, lang: str) -> bool:
    """The title is written in the channel's script: ≥ 60% Latin letters for a Latin-script language, ≥ 30% CJK for
    zh, ja and ko (research, added after the live run). Emoji, digits and punctuation do not count."""
    letters = [c for c in title if c.isalpha()]
    if not letters or not lang:
        return True
    name = lambda c: unicodedata.name(c, "")              # noqa: E731
    if lang in CJK_LANGS:
        cjk = sum(1 for c in letters if any(k in name(c) for k in ("CJK", "HIRAGANA", "KATAKANA", "HANGUL")))
        return cjk / len(letters) >= 0.3
    return sum(1 for c in letters if name(c).startswith("LATIN")) / len(letters) >= 0.6


def guess_type(text: str) -> str:
    t = _norm(text)
    if re.search(r"\b(vs\.?|versus)\b|so với", t):
        return "comparison"
    if re.search(r"^\s*(top\s+)?\d+\s|\btop \d+|\d+ (điều|cách|things|ways|reasons)", t):
        return "list"
    if re.search(r"\b(why|how)\b|vì sao|tại sao|làm sao|thế nào", t):
        return "explainer"
    if re.search(r"\b(story|true|history)\b|câu chuyện|chuyện có thật", t):
        return "true story"
    if t.strip().endswith("?"):
        return "q&a"
    return "explainer"


# ---------- fetching (R1) ----------
def _chunks(xs, n=50):
    return [xs[i:i + n] for i in range(0, len(xs), n)]


def _region(lang: str) -> dict:
    p = {"relevanceLanguage": lang} if lang else {}
    if REGION.get(lang):
        p["regionCode"] = REGION[lang]
    return p


def _videos(fetcher: Fetcher, ids: list) -> dict:
    out = {}
    for part in _chunks(list(dict.fromkeys(ids))):
        if not part:
            continue
        body = fetcher.get("videos", {"part": "snippet,statistics", "id": ",".join(part), "maxResults": 50})
        for it in body.get("items") or []:
            sn, st = it.get("snippet") or {}, it.get("statistics") or {}
            out[it["id"]] = {"id": it["id"], "title": sn.get("title", ""), "channel_id": sn.get("channelId", ""),
                             "channel": sn.get("channelTitle", ""), "published": sn.get("publishedAt", ""),
                             "views": int(st.get("viewCount") or 0)}
    return out


def _channels(fetcher: Fetcher, ids: list) -> dict:
    out = {}
    for part in _chunks(list(dict.fromkeys(i for i in ids if i))):
        body = fetcher.get("channels", {"part": "statistics,contentDetails", "id": ",".join(part), "maxResults": 50})
        for it in body.get("items") or []:
            st = it.get("statistics") or {}
            subs = None if st.get("hiddenSubscriberCount") else int(st.get("subscriberCount") or 0)
            uploads = ((it.get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads")
            out[it["id"]] = {"subs": subs, "uploads": uploads}
    return out


def _uploads(fetcher: Fetcher, playlist: str) -> list:
    body = fetcher.get("playlistItems", {"part": "snippet,contentDetails", "playlistId": playlist, "maxResults": 50})
    out = []
    for it in body.get("items") or []:
        cd, sn = it.get("contentDetails") or {}, it.get("snippet") or {}
        out.append({"id": cd.get("videoId"), "title": sn.get("title", ""),
                    "published": cd.get("videoPublishedAt") or sn.get("publishedAt", "")})
    return out


def fetch_topic(fetcher: Fetcher, text: str, lang: str) -> dict:
    t0 = now_utc()
    base = {"part": "snippet", "q": text, "type": "video", "maxResults": 50, **_region(lang)}
    ys = fetcher.get("search", {**base, "order": "viewCount", "publishedAfter": iso(t0 - timedelta(days=365))})
    # two windows by views, not one by date: the newest 50 of a popular topic are all from the last days (live run)
    n30 = fetcher.get("search", {**base, "order": "viewCount", "publishedAfter": iso(t0 - timedelta(days=30))})
    n60 = fetcher.get("search", {**base, "order": "viewCount", "publishedAfter": iso(t0 - timedelta(days=90)),
                                 "publishedBefore": iso(t0 - timedelta(days=30))})
    ids = lambda b: [i["id"]["videoId"] for i in b.get("items") or [] if (i.get("id") or {}).get("videoId")]  # noqa: E731
    yid, nid = ids(ys), list(dict.fromkeys(ids(n30) + ids(n60)))
    vids = _videos(fetcher, yid + nid)
    keep = lambda v: on_topic(v["title"], text) and script_ok(v["title"], lang)     # noqa: E731
    y = [vids[i] for i in yid if i in vids and keep(vids[i])]
    n = [vids[i] for i in nid if i in vids and keep(vids[i])]
    chans = _channels(fetcher, [v["channel_id"] for v in y + n])
    top = []
    for v in sorted(y, key=lambda v: -v["views"]):
        if v["channel_id"] not in top:
            top.append(v["channel_id"])
        if len(top) == 5:
            break
    medians = {}
    for cid in top:
        pl = (chans.get(cid) or {}).get("uploads")
        if not pl:
            continue
        ups = _uploads(fetcher, pl)
        views = [v["views"] for v in _videos(fetcher, [u["id"] for u in ups if u["id"]]).values()]
        if views:
            medians[cid] = statistics.median(views)
    channels = {cid: {"subs": c["subs"], "median_views": medians.get(cid)} for cid, c in chans.items()}
    return {"y365": y, "n90": n, "channels": channels, "fetched_at": iso(t0)}


def fetch_refs(fetcher: Fetcher, ids: list) -> list:
    """Recent uploads of the reference channels: [{channel_id, title, published}]."""
    out = []
    chans = _channels(fetcher, ids[:MAX_REFS])
    for cid, c in chans.items():
        if c.get("uploads"):
            out += [{"channel_id": cid, **u} for u in _uploads(fetcher, c["uploads"])]
    return out


# ---------- scoring (R2) ----------
def _step(value, table) -> int:
    """table = [(threshold, points)] ascending: points of the highest threshold reached, else 0."""
    pts = 0
    for th, p in table:
        if value >= th:
            pts = p
    return pts


DEMAND = [(1_000, 2), (10_000, 3), (50_000, 4), (100_000, 5), (300_000, 6), (1_000_000, 8), (3_000_000, 9), (10_000_000, 10)]
HEAT = [(0, 1), (0.4, 2), (0.7, 4), (1.0, 6), (1.5, 8), (2.0, 10)]
COMPETITION = [(2, 10), (5, 8), (10, 6), (20, 4), (35, 2)]


def _age_days(v: dict, now: datetime) -> float:
    try:
        return (now - parse_time(v["published"])).total_seconds() / 86400
    except (KeyError, ValueError):
        return 9999


def on_topic_y(raw: dict) -> list:
    """The year's videos without the ones the fit run marked as off-topic."""
    off = set(raw.get("offtopic") or [])
    return [v for v in raw.get("y365") or [] if v["id"] not in off]


def score_demand(raw: dict) -> tuple:
    y = on_topic_y(raw)
    if not y:
        return 0, 0
    top = sorted((v["views"] for v in y), reverse=True)[:10]
    pts = _step(statistics.median(top), DEMAND)
    outliers = sum(1 for v in y if (raw["channels"].get(v["channel_id"]) or {}).get("median_views")
                   and v["views"] > 3 * raw["channels"][v["channel_id"]]["median_views"])
    return min(10, pts + (2 if outliers else 0)), outliers


def heat_counts(raw: dict) -> tuple:
    now = parse_time(raw["fetched_at"])
    n = [v for v in raw.get("n90") or [] if v["views"] >= MEANINGFUL]
    recent = [v for v in n if _age_days(v, now) <= 30]
    older = [v for v in n if 30 < _age_days(v, now) <= 90]
    return recent, older


def score_heat(raw: dict) -> int:
    recent, older = heat_counts(raw)
    if not recent:
        return 0
    r = (len(recent) / 30) / max(len(older) / 60, 1 / 60)
    return _step(r, HEAT)


def cooling(raw: dict) -> bool:
    """Most of the last 30 days' videos came out 16–30 days ago: the pace is slowing down (R2, PRIORITY)."""
    recent, _ = heat_counts(raw)
    now = parse_time(raw["fetched_at"])
    return bool(recent) and sum(1 for v in recent if _age_days(v, now) > 15) / len(recent) >= 0.65


def weight(subs) -> float:
    if subs is None:
        return 1.0
    return 0.5 if subs < 10_000 else 1.0 if subs < 100_000 else 2.0 if subs < 1_000_000 else 3.0


def score_competition(raw: dict) -> tuple:
    chans = {v["channel_id"] for v in raw.get("n90") or [] if v["views"] >= MEANINGFUL}
    w = sum(weight((raw["channels"].get(c) or {}).get("subs")) for c in chans)
    pts = 1
    for th, p in COMPETITION:
        if w <= th:
            pts = p
            break
    return pts, len(chans), round(w, 1)


def score_overlap(text: str, made: list) -> tuple:
    """(points, {name, similarity} of the closest film or None); made = [{name, text}]."""
    if not made:
        return 10, None
    best = max(made, key=lambda m: similarity(text, m["text"]))
    s = similarity(text, best["text"])
    pts = max(0, min(10, round(10 * (1 - s / 0.6))))
    return pts, ({"name": best["name"], "similarity": round(s, 2)} if s > 0 else None)


def verdict(scores: dict, raw: dict = None) -> str:
    vals = [scores.get(k) or 0 for k in ("demand", "heat", "competition", "overlap", "fit")]
    total = sum(vals)
    if total < 25:
        return "DROP"
    if total >= 32 and min(vals) > 3:
        return "PRIORITY" if raw and (scores.get("heat") or 0) >= 8 and cooling(raw) else "GO"
    return "HOLD"


def score_raw(text: str, raw: dict, made: list, fit=None) -> dict:
    """Scores, total, verdict and evidence from raw numbers only (FR-005: the same numbers give the same result)."""
    demand, outliers = score_demand(raw)
    heat = score_heat(raw)
    comp, nchan, w = score_competition(raw)
    overlap, closest = score_overlap(text, made)
    scores = {"demand": demand, "heat": heat, "competition": comp, "overlap": overlap, "fit": fit}
    now = parse_time(raw["fetched_at"])
    recent, older = heat_counts(raw)
    y = on_topic_y(raw)
    topv = max(y, key=lambda v: v["views"]) if y else None
    ev = {"top_video": {"id": topv["id"], "title": topv["title"], "channel": topv["channel"], "views": topv["views"],
                        "age_days": round(_age_days(topv, now)), "url": f"https://www.youtube.com/watch?v={topv['id']}"}
          if topv else None,
          "counts": {"y365": len(y), "n30": len(recent), "n60": len(older), "channels90": nchan, "weight90": w,
                     "outliers": outliers},
          "closest_film": closest, "reference_hit": None}
    return {"scores": scores, "total": sum(v or 0 for v in scores.values()), "verdict": verdict(scores, raw), "evidence": ev}


def reference_hit(text: str, ref_videos: list, now: datetime = None):
    now = now or now_utc()
    for v in ref_videos or []:
        if _age_days(v, now) <= 30 and similarity(text, v["title"]) >= 0.5:
            return {"channel_id": v["channel_id"], "title": v["title"], "age_days": round(_age_days(v, now))}
    return None


# ---------- storage ----------
def topics_file(root: Path, slug: str) -> Path:
    return Path(root) / "channels" / slug / "topics.json"


def refs_file(root: Path, slug: str) -> Path:
    return Path(root) / "channels" / slug / "references.json"


def load(root: Path, slug: str) -> dict:
    try:
        d = json.loads(topics_file(root, slug).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    return d if isinstance(d.get("topics"), list) else {"topics": []}


def stale(t: dict, now: datetime = None) -> bool:
    return bool(t.get("scored_at")) and (now or now_utc()) - parse_time(t["scored_at"]) > timedelta(days=STALE_DAYS)


def save(root: Path, slug: str, data: dict, name: str = None, units_today=None, limit=None) -> None:
    data["topics"].sort(key=lambda t: t["n"])
    _write(topics_file(root, slug), json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    _write(topics_file(root, slug).with_name("TOPICS.md"), topics_md(data, name or slug, units_today, limit))


def topics_md(data: dict, name: str, units_today=None, limit=None) -> str:
    rows = [f"# Topics: {name}", "", f"Updated {iso(now_utc())[:10]}"
            + (f" · YouTube units used today: {units_today} / {limit}" if units_today is not None else ""), "",
            "## Queue", "", "| # | Verdict | Total | Demand | Heat | Competition | Overlap | Fit | Type | Strongest video | Age |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    cell = lambda s: str(s).replace("|", "\\|")                 # noqa: E731
    for t in [x for n in queue(data) for x in data["topics"] if x["n"] == n]:
        s, tv = {k: "–" for k in ("demand", "heat", "competition", "overlap")} | (t.get("scores") or {}), \
            (t.get("evidence") or {}).get("top_video")
        vid = f"[{cell(tv['title'][:60])}]({tv['url']}) · {tv['views']:,}" if tv else "–"
        rows.append(f"| {t['n']} | {t['verdict']}{' (stale)' if stale(t) else ''} | {t['total']} | {s['demand']} | {s['heat']} | "
                    f"{s['competition']} | {s['overlap']} | {s['fit'] if s.get('fit') is not None else '–'} | {t['type']} | "
                    f"{vid} | {tv['age_days'] if tv else '–'} d |")
    other = [t for t in data["topics"] if t["status"] in ("blocked_reference", "unscored")]
    if other:
        rows += ["", "## Blocked or not scored", "", *[f"- #{t['n']} \"{t['text']}\": {t.get('note') or t['status']}" for t in other]]
    dropped = [t for t in data["topics"] if t["status"] == "dropped"]
    if dropped:
        rows += ["", "## Dropped", "", *[f"- #{t['n']} \"{t['text']}\" {t['total']}/50" for t in dropped]]
    done = [t for t in data["topics"] if t["status"] in ("in_progress", "made")]
    if done:
        rows += ["", "## Taken", "", *[f"- #{t['n']} \"{t['text']}\": {t['status']}"
                                        + (f" (film {t['film']})" if t.get("film") else "") for t in done]]
    return "\n".join(rows) + "\n"


def made_items(root: Path, slug: str, data: dict) -> list:
    """What the channel already made, for the overlap score: taken topics and the films of the channel."""
    out = [{"name": t.get("film") or f"topic #{t['n']}", "text": t["text"]} for t in data["topics"]
           if t["status"] in ("in_progress", "made")]
    films = Path(root) / "films"
    for snap in films.glob("*/channel.json") if films.is_dir() else []:
        try:
            if json.loads(snap.read_text(encoding="utf-8")).get("channel") != slug:
                continue
        except (OSError, ValueError):
            continue
        title = snap.parent.name
        sc = snap.parent / "SCRIPT.md"
        if sc.is_file():
            m = re.search(r"^Title:\s*(.+)$", sc.read_text(encoding="utf-8"), re.M)
            title = m.group(1).strip() if m else title
        out.append({"name": snap.parent.name, "text": title})
    return out


def _entry(data: dict, text: str, source: str) -> dict:
    """The topic of this text: an existing one (similarity ≥ 0.8) or a new one."""
    for t in data["topics"]:
        if t["text"].lower() == text.lower() or similarity(t["text"], text) >= 0.8:
            return t
    t = {"n": max([x["n"] for x in data["topics"]] or [0]) + 1, "text": text, "source": source, "type": guess_type(text),
         "status": "unscored", "scores": {"demand": 0, "heat": 0, "competition": 0, "overlap": 0, "fit": None},
         "fit_by": None, "fit_reason": "", "total": 0, "verdict": "DROP", "evidence": None, "raw": None,
         "scored_at": None, "film": None, "taken_at": None, "note": None}
    data["topics"].append(t)
    return t


def apply_score(t: dict, made: list, refs: list) -> None:
    keep_fit = t["scores"].get("fit") if t.get("fit_by") == "user" else None
    r = score_raw(t["text"], t["raw"], [m for m in made if m["text"] != t["text"]],
                  keep_fit if keep_fit is not None else t["scores"].get("fit"))
    t.update(scores=r["scores"], total=r["total"], verdict=r["verdict"], evidence=r["evidence"])
    if t["status"] in ("in_progress", "made"):
        return
    hit = reference_hit(t["text"], refs, parse_time(t["raw"]["fetched_at"]))
    t["evidence"]["reference_hit"] = hit
    if hit:
        t["status"], t["note"] = "blocked_reference", f"a reference channel posted it {hit['age_days']} days ago"
    elif t["verdict"] == "DROP":
        t["status"], t["note"] = "dropped", None
    else:
        t["status"], t["note"] = "queued", ("fit not scored" if t["scores"]["fit"] is None else None)


def language_note(text: str, lang: str):
    cjk = is_cjk_text(text)
    if cjk and lang not in CJK_LANGS:
        return f"the topic looks like CJK text but the channel is in '{lang}'"
    if not cjk and lang in CJK_LANGS and re.search(r"[A-Za-zÀ-ỹ]{3,}", text):
        return f"the topic is not in the channel's language '{lang}'"
    return None


def score_batch(root: Path, slug: str, channel: dict, texts: list, fetcher: Fetcher, *, suggest=False, refs=None,
                fit=None, made=None, data=None) -> dict:
    """Score topics into the channel's data. fit(channel, [text], suggest) -> ({text: {score,type,reason}}, [suggested])
    or None. Returns {data, scored: [n], stopped: None | message, units}."""
    data = data if data is not None else load(root, slug)
    texts = [t.strip() for t in texts if t and t.strip()]
    for t in texts:
        if not 3 <= len(t) <= 120:
            raise TopicError(f"a topic must have 3–120 characters: \"{t[:40]}\"")
    if not 1 <= len(texts) <= MAX_TOPICS:
        raise TopicError(f"give 1–{MAX_TOPICS} topics")
    lang = channel.get("language") or ""
    made = made if made is not None else made_items(root, slug, data)
    stopped, scored = None, []
    try:
        ref_videos = fetch_refs(fetcher, refs) if refs else []
    except QuotaError as e:
        ref_videos, stopped = [], str(e)

    def run(batch, source):
        nonlocal stopped
        out = []
        for text in batch:
            t = _entry(data, text, source)
            if stopped:
                if not t.get("raw"):
                    t["status"], t["note"] = "unscored", "not scored: " + stopped
                continue
            try:
                t["raw"] = fetch_topic(fetcher, text, lang)
            except QuotaError as e:
                stopped = str(e)
                if not t.get("raw"):
                    t["status"], t["note"] = "unscored", "not scored: " + stopped
                continue
            t["scored_at"] = t["raw"]["fetched_at"]
            out.append(t)
        return out

    first = run(texts, "user")
    suggested = []
    if fit and first:
        got, suggested = fit(channel, [t["text"] for t in first], suggest, top_videos(first)) or ({}, [])
        _set_fit(first, got)
    if suggest and suggested and not stopped:
        extra = run([s for s in suggested if 3 <= len(s) <= 120][:MAX_SUGGEST], "suggested")
        if fit and extra:
            got, _ = fit(channel, [t["text"] for t in extra], False, top_videos(extra)) or ({}, [])
            _set_fit(extra, got)
        first += extra
    for t in first:
        apply_score(t, made, ref_videos)
        note = language_note(t["text"], lang)
        if note:
            t["note"] = (t["note"] + "; " if t.get("note") else "") + note
        scored.append(t["n"])
    return {"data": data, "scored": scored, "stopped": stopped, "units": fetcher.units}


def top_videos(topics: list) -> dict:
    """{topic text: [(id, title)]}: the 10 most viewed videos of the year, for the fit run to judge (off-topic)."""
    return {t["text"]: [(v["id"], v["title"]) for v in sorted(t["raw"]["y365"], key=lambda v: -v["views"])[:10]]
            for t in topics if t.get("raw")}


def _set_fit(topics: list, got: dict) -> None:
    for t in topics:
        g = (got or {}).get(t["text"])
        if t.get("raw") is not None:
            t["raw"]["offtopic"] = list((g or {}).get("offtopic") or [])
        if t.get("fit_by") == "user":
            continue
        if g and isinstance(g.get("score"), int):
            t["scores"]["fit"], t["fit_by"], t["fit_reason"] = g["score"], "claude", str(g.get("reason") or "")[:160]
            if g.get("type") in TYPES:
                t["type"] = g["type"]
        else:
            t["scores"]["fit"], t["fit_by"] = None, None


def set_fit(data: dict, n: int, score: int, made=None) -> dict:
    t = find(data, n)
    if not isinstance(score, int) or not 0 <= score <= 10:
        raise TopicError("fit is a whole number from 0 to 10")
    t["scores"]["fit"], t["fit_by"], t["fit_reason"] = score, "user", "set by hand"
    if t.get("raw"):
        apply_score(t, made or [], [])
    return t


def set_type(data: dict, n: int, kind: str) -> dict:
    if kind not in TYPES:
        raise TopicError("type is one of: " + ", ".join(TYPES))
    t = find(data, n)
    t["type"] = kind
    return t


def find(data: dict, n: int) -> dict:
    t = next((x for x in data["topics"] if x["n"] == int(n)), None)
    if t is None:
        raise TopicError(f"no topic #{n}")
    return t


# ---------- the queue (R4) ----------
def queue(data: dict) -> list:
    q = [t for t in data["topics"] if t["status"] == "queued" and t["verdict"] in VERDICT_ORDER]
    q.sort(key=lambda t: (VERDICT_ORDER[t["verdict"]], -t["total"], t["n"]))
    return [t["n"] for t in q]


def last_types(data: dict, k: int = 2) -> list:
    taken = sorted((t for t in data["topics"] if t["status"] in ("in_progress", "made") and t.get("taken_at")),
                   key=lambda t: t["taken_at"], reverse=True)
    return [t["type"] for t in taken[:k]]


def take(data: dict, film=None, allow_stale=False) -> tuple:
    """(topic or None, [{n, reason}])."""
    lt = last_types(data)
    same = lt[0] if len(lt) == 2 and lt[0] == lt[1] else None
    skipped = []
    for n in queue(data):
        t = find(data, n)
        if same and t["type"] == same:
            skipped.append({"n": n, "reason": f"the last 2 films were both '{same}'"})
            continue
        if stale(t) and not allow_stale:
            skipped.append({"n": n, "reason": f"scored over {STALE_DAYS} days ago: check it again (topics recheck)"})
            continue
        t["status"], t["film"], t["taken_at"] = "in_progress", film, iso(now_utc())
        return t, skipped
    return None, skipped


def mark_made(data: dict, n: int, film=None) -> dict:
    t = find(data, n)
    if t["status"] not in ("in_progress", "made"):
        raise TopicError(f"topic #{n} is {t['status']}, not in progress")
    t["status"] = "made"
    if film:
        t["film"] = film
    return t


def load_refs(root: Path, slug: str) -> list:
    try:
        d = json.loads(refs_file(root, slug).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [c for c in d.get("channels") or [] if isinstance(c, dict) and c.get("id")]


def save_refs(root: Path, slug: str, ids: list) -> list:
    ids = list(dict.fromkeys(ids))
    if len(ids) > MAX_REFS:
        raise TopicError(f"at most {MAX_REFS} reference channels")
    for i in ids:
        if not re.fullmatch(r"UC[\w-]{22}", i or ""):
            raise TopicError(f"\"{i}\" is not a YouTube channel id (UC followed by 22 letters, digits, - or _)")
    old = {c["id"]: c for c in load_refs(root, slug)}
    rows = [old.get(i) or {"id": i, "title": "", "added": pacific_day()} for i in ids]
    _write(refs_file(root, slug), json.dumps({"channels": rows}, indent=1) + "\n")
    return rows


def run_job(work: Path) -> dict:
    """An online `topics` job inside its container (R6): numbers through the proxy, fit through the proxy, the
    result in work/topics-result.json for the worker to merge."""
    from filmcheck import topics_fit
    work = Path(work)
    inp = json.loads((work / ".input.json").read_text(encoding="utf-8"))
    token = os.environ.get("STUDIO_JOB_TOKEN") or os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or ""
    fetcher = Fetcher.proxy(os.environ["STUDIO_PROXY"], token)
    channel = inp.get("channel_profile") or {}
    data = {"topics": inp.get("existing") or []}
    out = score_batch(work, inp["channel"], channel, inp["topics"], fetcher, suggest=bool(inp.get("suggest")),
                      refs=[r["id"] for r in inp.get("references") or []], fit=topics_fit.fit_for(channel),
                      made=inp.get("made") or [], data=data)
    keep = {n for n in out["scored"]} | {t["n"] for t in data["topics"] if t["status"] == "unscored"}
    result = {"topics": [t for t in data["topics"] if t["n"] in keep], "units": out["units"],
              "stopped": "youtube_quota" if out["stopped"] else None}
    _write(work / "topics-result.json", json.dumps(result, ensure_ascii=False))
    return result
