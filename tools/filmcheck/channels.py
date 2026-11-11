"""Channel profiles and lessons (specs/012): the user's own YouTube channels, what they decided, and the mistakes
the studio must not make again.

Files (contracts/files.md): <root>/channels/<slug>/channel.json and lessons.json, with CHANNEL.md and LESSONS.md
written from them; shared lessons in <root>/channels/lessons.json (local) or $STUDIO_DATA/shared/lessons.json
(online). A film gets a snapshot (channel.json + CHANNEL_BRIEF.md) in its own folder; the checks read only that."""
import json
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

SLUG = re.compile(r"^[a-z0-9-]{1,40}$")
LANG = re.compile(r"^[a-z]{2,3}$")
TAG = re.compile(r"^#[^\s#]{1,29}$")
VOICE = (re.compile(r"^[a-z]{2}_[a-z]+$"), re.compile(r"^[a-z]{2,3}-[A-Z]{2,4}-\w+Neural$"))
DEFAULT_VOICE, DEFAULT_SPEED = "af_bella", 1.0
MAX_CHANNELS, MAX_LESSONS, BRIEF_MAX = 20, 200, 6000
RULES = {"phrase": (1, 80), "max_sentence_words": (5, 60), "max_title_chars": (20, 100)}
TEXT_FIELDS = {"name": (1, 80), "niche": (0, 500), "audience": (0, 500), "title_rules": (0, 1500),
               "thumbnail_rules": (0, 1500)}
LIB = Path(__file__).resolve().parents[2] / "lib" / "lemo-opuscar"


class ChannelError(Exception):
    """Bad input or a missing channel (exit code 2, HTTP 404/409/422)."""

    def __init__(self, message, code="invalid"):
        super().__init__(message)
        self.code = code


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def _read(path: Path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


# ---------- where things are ----------
def channels_dir(root: Path) -> Path:
    return Path(root) / "channels"


def channel_dir(root: Path, slug: str) -> Path:
    if not SLUG.match(slug or ""):
        raise ChannelError(f"bad channel id \"{slug}\": use 1–40 lowercase letters, digits or dashes")
    return channels_dir(root) / slug


def lessons_file(root: Path, scope: str, shared_path: Path = None) -> Path:
    """A channel's lessons, or the shared ones (scope 'shared')."""
    if scope == "shared":
        return Path(shared_path) if shared_path else channels_dir(root) / "lessons.json"
    return channel_dir(root, scope) / "lessons.json"


# ---------- checking a profile (FR-002) ----------
def style_exists(name: str, root: Path, lib: Path = None) -> bool:
    lib = Path(lib) if lib else LIB
    return bool(name) and SLUG.match(name) is not None and (
        (Path(root) / "my-styles" / name / "style.json").is_file() or (lib / "styles" / name).is_dir())


def voice_ok(v) -> bool:
    return v is None or (isinstance(v, str) and any(r.match(v) for r in VOICE))


def validate(ch: dict, root: Path, lib: Path = None) -> list:
    errs = []
    if not SLUG.match(str(ch.get("slug") or "")):
        errs.append("slug: 1–40 lowercase letters, digits or dashes")
    for k, (lo, hi) in TEXT_FIELDS.items():
        v = ch.get(k, "")
        if not isinstance(v, str) or not lo <= len(v.strip()) <= hi:
            errs.append(f"{k}: {lo}–{hi} characters")
    if not LANG.match(str(ch.get("language") or "")):
        errs.append("language: a code such as en, vi or zh")
    s = ch.get("seconds")
    if not isinstance(s, int) or isinstance(s, bool) or not 5 <= s <= 900:
        errs.append("seconds: a whole number from 5 to 900")
    if not style_exists(ch.get("style"), root, lib):
        errs.append(f"style: \"{ch.get('style')}\" is not a style of the library or of my-styles/")
    if not voice_ok(ch.get("voice")):
        errs.append("voice: a voice of the library, such as af_bella or vi-VN-HoaiMyNeural (no files, no cloned voices)")
    sp = ch.get("speed", DEFAULT_SPEED)
    if not isinstance(sp, (int, float)) or isinstance(sp, bool) or not 0.5 <= sp <= 2.0:
        errs.append("speed: from 0.5 to 2.0")
    tm = ch.get("title_max")
    if tm is not None and (not isinstance(tm, int) or isinstance(tm, bool) or not 20 <= tm <= 100):
        errs.append("title_max: from 20 to 100, or empty")
    tags = ch.get("hashtags") or []
    if not isinstance(tags, list) or len(tags) > 5 or not all(isinstance(t, str) and TAG.match(t) for t in tags):
        errs.append("hashtags: at most 5, each like #science (at most 30 characters)")
    banned = ch.get("banned") or []
    if not isinstance(banned, list) or len(banned) > 50 or not all(isinstance(b, str) and 1 <= len(b.strip()) <= 60 for b in banned):
        errs.append("banned: at most 50 words or phrases of 1–60 characters")
    elif isinstance(tags, list):
        for t in tags:
            if isinstance(t, str) and find_banned(t.lstrip("#"), banned):
                errs.append(f"hashtags: {t} is also a banned word")
    dec = ch.get("decisions") or []
    if not isinstance(dec, list) or len(dec) > 100 or not all(
            isinstance(d, dict) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(d.get("date"))) and 1 <= len(str(d.get("text", "")).strip()) <= 300
            for d in dec):
        errs.append("decisions: at most 100, each {date: YYYY-MM-DD, text: 1–300 characters}")
    return errs


def normal(ch: dict) -> dict:
    out = {"slug": ch.get("slug"), "name": (ch.get("name") or "").strip(), "niche": (ch.get("niche") or "").strip(),
           "audience": (ch.get("audience") or "").strip(), "language": (ch.get("language") or "").lower(),
           "seconds": ch.get("seconds"), "style": ch.get("style"), "voice": ch.get("voice") or None,
           "speed": float(ch.get("speed", DEFAULT_SPEED)), "title_rules": (ch.get("title_rules") or "").strip(),
           "thumbnail_rules": (ch.get("thumbnail_rules") or "").strip(), "title_max": ch.get("title_max"),
           "hashtags": list(ch.get("hashtags") or []), "banned": [b.strip() for b in ch.get("banned") or []],
           "decisions": list(ch.get("decisions") or []), "updated": ch.get("updated")}
    return out


# ---------- reading and writing ----------
def load(root: Path, slug: str) -> dict:
    p = channel_dir(root, slug) / "channel.json"
    if not p.is_file():
        raise ChannelError(f"no channel \"{slug}\"", "not_found")
    ch = _read(p, None)
    if not isinstance(ch, dict):
        raise ChannelError(f"channels/{slug}/channel.json cannot be read")
    return ch


def list_channels(root: Path) -> list:
    out = []
    d = channels_dir(root)
    for p in sorted(d.glob("*/channel.json")) if d.is_dir() else []:
        ch = _read(p, None)
        if isinstance(ch, dict):
            ls = load_lessons(p.parent / "lessons.json")["lessons"]
            out.append({**ch, "lessons_active": sum(x["status"] == "active" for x in ls),
                        "lessons_draft": sum(x["status"] == "draft" for x in ls)})
    return out


def save(root: Path, ch: dict, lib: Path = None, new: bool = False) -> dict:
    ch = normal(ch)
    errs = validate(ch, root, lib)
    if errs:
        raise ChannelError("; ".join(errs))
    d = channel_dir(root, ch["slug"])
    if new:
        if (d / "channel.json").exists():
            raise ChannelError(f"channel \"{ch['slug']}\" already exists", "exists")
        if len(list_channels(root)) >= MAX_CHANNELS:
            raise ChannelError(f"at most {MAX_CHANNELS} channels", "limit")
    ch["updated"] = now()
    _write(d / "channel.json", json.dumps(ch, ensure_ascii=False, indent=1) + "\n")
    _write(d / "CHANNEL.md", channel_md(ch))
    if not (d / "lessons.json").exists():
        save_lessons(d / "lessons.json", {"lessons": []}, ch["slug"])
    write_readme(root)
    return ch


def decide(root: Path, slug: str, text: str, lib: Path = None) -> dict:
    ch = load(root, slug)
    ch.setdefault("decisions", []).append({"date": today(), "text": (text or "").strip()})
    return save(root, ch, lib)


def channel_md(ch: dict) -> str:
    rows = [f"# Kênh {ch['name']} (`{ch['slug']}`)", "", f"Cập nhật: {(ch.get('updated') or '')[:10]}", ""]
    if ch.get("niche") or ch.get("audience"):
        rows.append(f"- Ngách: {ch.get('niche') or '–'} · Khán giả: {ch.get('audience') or '–'}")
    voice = f" · Giọng: {ch['voice']} × {ch.get('speed', 1.0):g}" if ch.get("voice") else ""
    rows.append(f"- Ngôn ngữ: {ch['language']} · Độ dài: {ch['seconds']} s · Phong cách: {ch['style']}{voice}")
    rows.append(f"- Hashtag luôn dùng: {' '.join(ch['hashtags']) or '–'} · Từ không dùng: {', '.join(ch['banned']) or '–'}")
    if ch.get("title_rules") or ch.get("title_max"):
        most = f" (tối đa {ch['title_max']})" if ch.get("title_max") else ""
        rows.append(f"- Tiêu đề{most}: {ch.get('title_rules') or '–'}")
    if ch.get("thumbnail_rules"):
        rows.append(f"- Thumbnail: {ch['thumbnail_rules']}")
    if ch.get("decisions"):
        rows += ["", "## Quyết định", *[f"- {d['date']}: {d['text']}" for d in ch["decisions"]]]
    return "\n".join(rows) + "\n"


def write_readme(root: Path) -> None:
    d = channels_dir(root)
    rows = ["# Kênh", "",
            "Hồ sơ các kênh YouTube của chính xưởng (specs/012). Mỗi kênh nằm trong `channels/<mã>/`: `channel.json` và "
            "`lessons.json` (sửa bằng lệnh `sh bin/studio channel …` / `lesson …` hoặc bằng tay), `CHANNEL.md` và "
            "`LESSONS.md` (viết lại từ JSON, đừng sửa tay). Bài học chung cho mọi kênh: `channels/lessons.json`. Đây là "
            "kênh của mình, không phải kênh tham chiếu: không ghi tên kênh tham chiếu ở đây.", "",
            "| Mã | Tên | Ngôn ngữ | Phong cách | Bài học |", "|---|---|---|---|---|"]
    for ch in list_channels(root):
        rows.append(f"| {ch['slug']} | {ch.get('name', '')} | {ch.get('language', '')} | {ch.get('style', '')} | "
                    f"{ch['lessons_active']} |")
    _write(d / "README.md", "\n".join(rows) + "\n")


# ---------- lessons (FR-009 … FR-014) ----------
def parse_rule(rule):
    """(kind, value) or None when the rule cannot be read (contracts/cli.md)."""
    if not isinstance(rule, str) or ":" not in rule:
        return None
    kind, value = rule.split(":", 1)
    kind, value = kind.strip(), value.strip()
    if kind not in RULES:
        return None
    lo, hi = RULES[kind]
    if kind == "phrase":
        return (kind, value) if lo <= len(value) <= hi else None
    try:
        n = int(value)
    except ValueError:
        return None
    return (kind, n) if lo <= n <= hi else None


def load_lessons(path: Path) -> dict:
    data = _read(path, {"lessons": []})
    if not isinstance(data, dict) or not isinstance(data.get("lessons"), list):
        data = {"lessons": []}
    return data


def save_lessons(path: Path, data: dict, title: str) -> None:
    path = Path(path)
    data["lessons"].sort(key=lambda x: x["n"])
    _write(path, json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    rows = [f"# Bài học: {title}", "", "| # | Ngày | Trạng thái | Lỗi | Vì sao lọt | Cách chặn | Luật máy |",
            "|---|---|---|---|---|---|---|"]
    cell = lambda s: str(s or "").replace("|", "\\|").replace("\n", " ")       # noqa: E731
    for x in data["lessons"]:
        rule = (f"`{x['rule']}`" + ("" if x.get("rule_valid", True) else " (invalid)")) if x.get("rule") else ""
        rows.append(f"| {x['n']} | {x['date']} | {x['status']} | {cell(x['what'])} | {cell(x['why'])} | {cell(x['stop'])} | {rule} |")
    _write(path.with_name("LESSONS.md"), "\n".join(rows) + "\n")


def add_lesson(path: Path, *, what, why, stop, film=None, rule=None, status="draft", title=None) -> dict:
    for k, v in (("what", what), ("why", why), ("stop", stop)):
        if not isinstance(v, str) or not 1 <= len(v.strip()) <= 400:
            raise ChannelError(f"{k}: 1–400 characters")
    if status not in ("draft", "active"):
        raise ChannelError("a new lesson is draft or active")
    data = load_lessons(path)
    if len(data["lessons"]) >= MAX_LESSONS:
        raise ChannelError(f"at most {MAX_LESSONS} lessons", "limit")
    rule = (rule or "").strip() or None
    x = {"n": max([y["n"] for y in data["lessons"]] or [0]) + 1, "date": today(), "film": film or None,
         "what": what.strip(), "why": why.strip(), "stop": stop.strip(), "status": status, "rule": rule,
         "rule_valid": rule is None or parse_rule(rule) is not None,
         "approved_at": now() if status == "active" else None, "retired_at": None}
    data["lessons"].append(x)
    save_lessons(path, data, title or Path(path).parent.name)
    return x


def _change(path: Path, n: int, fn, title=None) -> dict:
    data = load_lessons(path)
    x = next((y for y in data["lessons"] if y["n"] == int(n)), None)
    if x is None:
        raise ChannelError(f"no lesson #{n}", "not_found")
    fn(x)
    save_lessons(path, data, title or Path(path).parent.name)
    return x


def approve(path: Path, n: int, title=None) -> dict:
    def f(x):
        if x["status"] != "draft":
            raise ChannelError(f"lesson #{n} is {x['status']}, not a draft", "not_draft")
        x["status"], x["approved_at"] = "active", now()
    return _change(path, n, f, title)


def retire(path: Path, n: int, title=None) -> dict:
    def f(x):
        if x["status"] != "retired":
            x["status"], x["retired_at"] = "retired", now()
    return _change(path, n, f, title)


def edit_draft(path: Path, n: int, title=None, **fields) -> dict:
    def f(x):
        if x["status"] != "draft":
            raise ChannelError(f"lesson #{n} is {x['status']}, not a draft", "not_draft")
        for k in ("what", "why", "stop"):
            if fields.get(k) is not None:
                if not 1 <= len(str(fields[k]).strip()) <= 400:
                    raise ChannelError(f"{k}: 1–400 characters")
                x[k] = str(fields[k]).strip()
        if "rule" in fields:
            x["rule"] = (fields["rule"] or "").strip() or None
            x["rule_valid"] = x["rule"] is None or parse_rule(x["rule"]) is not None
    return _change(path, n, f, title)


# ---------- matching (R3) ----------
def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", s or "").lower()


def _cjk(s: str) -> bool:
    letters = [c for c in s if not c.isspace()]
    return bool(letters) and sum(unicodedata.east_asian_width(c) in ("W", "F") for c in letters) * 2 > len(letters)


def find_banned(text: str, words: list) -> list:
    """[(word, position)]: whole words, any case; plain substrings for CJK words."""
    t = _norm(text)
    hits = []
    for w in words or []:
        n = _norm(w.strip())
        if not n:
            continue
        rx = re.escape(n) if _cjk(n) else r"(?<!\w)" + re.escape(n) + r"(?!\w)"
        hits += [(w, m.start()) for m in re.finditer(rx, t)]
    return hits


# ---------- the film's snapshot (R2) ----------
def active_rules(lessons: list, scope: str) -> list:
    return [{"n": x["n"], "scope": scope, "rule": x["rule"]} for x in lessons
            if x["status"] == "active" and x.get("rule") and parse_rule(x["rule"])]


def brief(ch: dict, film: dict, chan_lessons: list, shared_lessons: list) -> tuple:
    """(text ≤ BRIEF_MAX, lessons not shown)."""
    head = [f"# Channel: {ch['name']} (`{ch['slug']}`)", ""]
    for k, label in (("niche", "Niche"), ("audience", "Audience")):
        if ch.get(k):
            head.append(f"- {label}: {ch[k]}")
    head.append(f"- Language: {film['language']} · Length: {film['seconds']} s · Style: {film['style']}"
                + (f" · Voice: {film['voice']} × {film['speed']:g} (use it for every line of lines.json)" if film.get("voice") else ""))
    if ch.get("hashtags"):
        head.append(f"- Hashtags always used: {' '.join(ch['hashtags'])}")
    if ch.get("banned"):
        head.append(f"- Never use: {', '.join(ch['banned'])}")
    if ch.get("title_rules") or ch.get("title_max"):
        most = f" (at most {ch['title_max']} characters)" if ch.get("title_max") else ""
        head.append(f"- Titles{most}: {ch.get('title_rules') or '–'}")
    if ch.get("thumbnail_rules"):
        head.append(f"- Thumbnails: {ch['thumbnail_rules']}")
    if ch.get("decisions"):
        head += ["", "## Decisions", *[f"- {d['date']}: {d['text']}" for d in ch["decisions"]]]
    items = [(x, "channel") for x in chan_lessons if x["status"] == "active"] + \
        [(x, "shared") for x in shared_lessons if x["status"] == "active"]
    ruled = [i for i in items if i[0].get("rule") and parse_rule(i[0]["rule"])]
    plain = sorted([i for i in items if i not in ruled], key=lambda i: (i[0]["date"], i[0]["n"]), reverse=True)
    lines = [f"- #{x['n']}{' (shared)' if s == 'shared' else ''}: {x['what']} → {x['stop']}"
             + (f" [checked: `{x['rule']}`]" if x.get("rule") and parse_rule(x["rule"]) else "") for x, s in ruled + plain]
    text = "\n".join(head)
    if lines:
        text += "\n\n## Lessons (repeating one is a serious mistake)\n"
    shown, left = [], len(lines)
    for ln in lines:
        tail = f"\n({left - 1} lessons not shown: merge or retire some)" if left > 1 else ""
        if len(text) + len("\n".join(shown + [ln])) + len(tail) + 1 > BRIEF_MAX:
            break
        shown.append(ln)
        left -= 1
    text += "\n".join(shown)
    if left:
        text += f"\n({left} lessons not shown: merge or retire some)"
    return text[:BRIEF_MAX].rstrip() + "\n", left


def attach(root: Path, film_dir: Path, slug: str, shared_path: Path = None, lib: Path = None, **override) -> dict:
    """Write channel.json and CHANNEL_BRIEF.md into the film folder. Returns {snapshot, warning}."""
    root, film_dir = Path(root), Path(film_dir)
    ch = load(root, slug)
    film = {"style": override.get("style") or ch["style"], "seconds": int(override.get("seconds") or ch["seconds"]),
            "language": (override.get("language") or ch["language"]).lower(),
            "voice": override.get("voice") or ch.get("voice"),
            "speed": float(override.get("speed") or ch.get("speed") or DEFAULT_SPEED)}
    if not style_exists(film["style"], root, lib):
        raise ChannelError(f"the style \"{film['style']}\" no longer exists; change the channel or pick a style for this film")
    if not voice_ok(film["voice"]):
        raise ChannelError(f"the voice \"{film['voice']}\" is not a voice of the library")
    if not LANG.match(film["language"]):
        raise ChannelError("language: a code such as en, vi or zh")
    chan_lessons = load_lessons(channel_dir(root, slug) / "lessons.json")["lessons"]
    shared_lessons = load_lessons(lessons_file(root, "shared", shared_path))["lessons"]
    override_voice = bool(override.get("voice") or override.get("speed")) and \
        (film["voice"] != ch.get("voice") or abs(film["speed"] - float(ch.get("speed") or DEFAULT_SPEED)) > 0.01)
    snap = {"channel": slug, "at": now(), "film": film, "topic": override.get("topic"),
            "rules": {"language": film["language"], "banned": ch.get("banned") or [], "hashtags": ch.get("hashtags") or [],
                      "title_max": ch.get("title_max"), "voice": film["voice"] if ch.get("voice") or film["voice"] else None,
                      "speed": film["speed"], "voice_override": override_voice},
            "lessons": active_rules(chan_lessons, "channel") + active_rules(shared_lessons, "shared")}
    text, left = brief(ch, film, chan_lessons, shared_lessons)
    film_dir.mkdir(parents=True, exist_ok=True)
    _write(film_dir / "channel.json", json.dumps(snap, ensure_ascii=False, indent=1) + "\n")
    _write(film_dir / "CHANNEL_BRIEF.md", text)
    warn = f"{left} lessons did not fit in CHANNEL_BRIEF.md ({BRIEF_MAX} characters): merge or retire some" if left else None
    return {"snapshot": snap, "warning": warn}


def snapshot(film_dir: Path):
    s = _read(Path(film_dir) / "channel.json", None)
    return s if isinstance(s, dict) and isinstance(s.get("rules"), dict) else None


def lesson_rules(snap, kind: str) -> list:
    """[(n, scope, value)] of the snapshot's lessons of one rule kind."""
    out = []
    for x in (snap or {}).get("lessons") or []:
        r = parse_rule(x.get("rule"))
        if r and r[0] == kind:
            out.append((x["n"], x.get("scope", "channel"), r[1]))
    return out


def lesson_label(n: int, scope: str) -> str:
    return f"#{n}" + (" (shared)" if scope == "shared" else "")
