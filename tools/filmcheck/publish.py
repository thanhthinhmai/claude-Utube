"""The publish pack of a film (specs/011): titles, thumbnails, description, chapters and subtitles for YouTube.

The agent writes only films/<name>/publish/pack.json. `build()` writes every other file of the pack and `check()`
measures it against the rules of contracts/cli.md. No Claude, no network. Thumbnails need node and the library
(thumbs.mjs); everything else is plain Python."""
import json
import math
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

from filmcheck import qc, report, script as scriptmod

ANGLES = ("curiosity", "number", "question")
ANGLE_LABEL = {"curiosity": "Curiosity", "number": "Number or benefit", "question": "Question"}
TITLE_MAX, TITLE_VISIBLE, HOOK_MAX, DESC_MAX, SUMMARY_MAX = 100, 60, 150, 5000, 600
THUMB_BYTES, THUMB_WORDS, THUMB_CJK, TEXT_HEIGHT, CONTRAST, COVER_MAX = 2_000_000, 6, 12, 0.08, 4.5, 0.10
CHAPTER_MIN, CHAPTER_COUNT, CHAPTER_TITLE = 10.0, 3, 40
CUE_LINES, CUE_UNITS, CUE_MIN, CUE_MAX = 2, 42, 1.0, 7.0
BREAKS = (":", " - ", " — ", " – ", "|", "?", "!")
OWN_FILES = re.compile(r"^(thumbnail-[123]\.(png|jpg)|thumbs\.json|titles\.md|description\.md|subtitles\.srt|PUBLISH\.md)$")
TOL = 1e-3


class PublishError(Exception):
    """The pack cannot be made (exit code 2)."""


# ---------- small helpers ----------
def wide(ch: str) -> bool:
    return unicodedata.east_asian_width(ch) in ("W", "F")


def units(s: str) -> int:
    """Display width: CJK characters count 2 (contracts/cli.md)."""
    return sum(2 if wide(c) else 1 for c in s)


def is_cjk(s: str) -> bool:
    letters = [c for c in s if not c.isspace()]
    return bool(letters) and sum(wide(c) for c in letters) * 2 > len(letters)


def tokens(s: str) -> list:
    return list(s.replace(" ", "")) if is_cjk(s) and " " not in s.strip() else s.split()


def joiner(s: str) -> str:
    return "" if is_cjk(s) and " " not in s.strip() else " "


def stamp(sec: float) -> str:
    s = int(sec)
    h, m, s = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def srt_time(sec: float) -> str:
    ms = int(round(sec * 1000))
    return f"{ms // 3600000:02d}:{ms % 3600000 // 60000:02d}:{ms % 60000 // 1000:02d},{ms % 1000:03d}"


def mp4_of(d: Path) -> Path:
    return d / f"{d.name}.mp4"


def video_size(mp4: Path) -> tuple:
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(mp4)], capture_output=True, text=True)
    try:
        w, h = (int(x) for x in p.stdout.strip().split(",")[:2])
    except ValueError:
        raise PublishError(f"{mp4.name} cannot be read: {p.stderr.strip()[-200:]}") from None
    return w, h


def thumb_size(film_wh: tuple) -> tuple:
    return (720, 1280) if film_wh[1] > film_wh[0] else (1280, 720)


def image_size(path: Path) -> tuple:
    try:
        return video_size(path)
    except PublishError:
        return 0, 0


# ---------- pack.json ----------
def read_pack(d: Path) -> dict:
    p = Path(d) / "publish" / "pack.json"
    if not p.is_file():
        raise PublishError("publish/pack.json is missing: write it first (contracts/files.md)")
    try:
        pk = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        raise PublishError(f"publish/pack.json is not valid JSON: {e}") from None
    if not isinstance(pk, dict):
        raise PublishError("publish/pack.json must be an object")
    titles = pk.get("titles")
    if not isinstance(titles, list) or len(titles) != 3:
        raise PublishError("pack.json: 'titles' must be a list of 3 titles")
    for i, t in enumerate(titles, 1):
        if not isinstance(t, dict) or not isinstance(t.get("angle"), str) or not isinstance(t.get("text"), str):
            raise PublishError(f"pack.json: title {i} needs 'angle' and 'text'")
        th = t.get("thumb")
        if not isinstance(th, dict) or not isinstance(th.get("text"), str) or not isinstance(th.get("t"), (int, float)):
            raise PublishError(f"pack.json: title {i} needs 'thumb' with 't' (seconds) and 'text'")
        th.setdefault("position", "bottom")
        th.setdefault("color", "#ffffff")
        th.setdefault("plate", "#000000")
        th.setdefault("plate_opacity", 0.6)
        if th["position"] not in ("top", "bottom", "center"):
            raise PublishError(f"pack.json: title {i} thumb 'position' must be top, bottom or center")
    if not isinstance(pk.get("hook"), list) or not all(isinstance(x, str) for x in pk["hook"]):
        raise PublishError("pack.json: 'hook' must be a list of 2 lines")
    if not isinstance(pk.get("summary"), str) or not pk["summary"].strip():
        raise PublishError("pack.json: 'summary' must be a non-empty string")
    ch = pk.setdefault("chapters", [])
    if not isinstance(ch, list) or not all(isinstance(c, dict) and isinstance(c.get("from"), str)
                                           and isinstance(c.get("title"), str) for c in ch):
        raise PublishError("pack.json: 'chapters' must be a list of {\"from\": \"Pnn\", \"title\": \"…\"}")
    if not isinstance(pk.get("hashtags"), list) or not all(isinstance(x, str) for x in pk["hashtags"]):
        raise PublishError("pack.json: 'hashtags' must be a list of strings")
    pk.setdefault("language", "")
    return pk


# ---------- what the film has ----------
def narration(d: Path):
    try:
        return qc.load_narration(d)
    except qc.QcError:
        return None


def script_or_none(d: Path):
    try:
        return scriptmod.read_script(d / "SCRIPT.md")
    except scriptmod.ScriptError:
        return None


def voice_lines(d: Path, nar) -> dict:
    """{line id: text} from the lines.json the voice was made from, or {}."""
    if not nar or not nar.get("lines_file"):
        return {}
    try:
        rows = json.loads((d / nar["lines_file"]).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {r.get("id"): str(r.get("text", "")) for r in rows if isinstance(r, dict)}


# ---------- chapters (R4) ----------
def para_starts(nar) -> list:
    """[(para, start second)] in narration order; the first is the film's start, 0:00."""
    out = []
    for ln in nar["lines"]:
        if not out or out[-1][0] != ln["para"]:
            if all(p != ln["para"] for p, _ in out):
                out.append((ln["para"], ln["at"]))
    if out:
        out[0] = (out[0][0], 0.0)
    return out


def can_split(starts: list, duration: float) -> bool:
    """Whether some grouping of neighbouring paragraphs gives ≥ 3 chapters of ≥ 10 s (greedy earliest is best)."""
    if duration < CHAPTER_MIN * CHAPTER_COUNT or not starts:
        return False
    chosen = [0.0]
    for _, s in starts[1:]:
        if s - chosen[-1] >= CHAPTER_MIN - TOL:
            chosen.append(s)
    while len(chosen) > 1 and duration - chosen[-1] < CHAPTER_MIN - TOL:
        chosen.pop()
    return len(chosen) >= CHAPTER_COUNT


def chapters(d: Path, pack: dict, nar=None, duration=None) -> tuple:
    """([{at, title, from, length}], applicable, problems)."""
    nar = nar if nar is not None else narration(d)
    if not nar:
        return [], False, []
    duration = duration if duration is not None else qc.probe_duration(mp4_of(d))
    starts = para_starts(nar)
    if not can_split(starts, duration):
        return [], False, []
    at = dict(starts)
    order = [p for p, _ in starts]
    given = pack.get("chapters") or []
    if not given:
        return [], True, ["chapters: the film can have chapters (3 or more of at least 10 s) but pack.json has none"]
    rows, problems = [], []
    for c in given:
        if c["from"] not in at:
            problems.append(f"chapters: {c['from']} is not a paragraph of the narration")
            continue
        rows.append({"from": c["from"], "title": c["title"].strip(), "at": at[c["from"]]})
    if rows and rows[0]["from"] != order[0]:
        problems.append(f"chapters: the first chapter must start at {order[0]} (0:00), not {rows[0]['from']}")
    for a, b in zip(rows, rows[1:]):
        if order.index(b["from"]) <= order.index(a["from"]):
            problems.append(f"chapters: {b['from']} comes after {a['from']}; chapters must go forward")
    for i, r in enumerate(rows):
        end = rows[i + 1]["at"] if i + 1 < len(rows) else duration
        r["length"] = round(end - r["at"], 2)
        if r["length"] < CHAPTER_MIN - TOL:
            problems.append(f"chapters: \"{r['title']}\" at {stamp(r['at'])} lasts {r['length']:.1f} s; at least {CHAPTER_MIN:g} s")
        if not r["title"] or len(r["title"]) > CHAPTER_TITLE:
            problems.append(f"chapters: the title at {stamp(r['at'])} must have 1–{CHAPTER_TITLE} characters")
    if len(rows) < CHAPTER_COUNT:
        problems.append(f"chapters: {len(rows)} chapters; YouTube needs at least {CHAPTER_COUNT}")
    return rows, True, problems


# ---------- subtitles (R5) ----------
def wrap(text: str):
    """The text as at most 2 lines of ≤ 42 units, or None."""
    if units(text) <= CUE_UNITS:
        return [text]
    j = joiner(text)
    toks = tokens(text)
    best = None
    for k in range(1, len(toks)):
        a, b = j.join(toks[:k]), j.join(toks[k:])
        if units(a) <= CUE_UNITS and units(b) <= CUE_UNITS:
            score = abs(units(a) - units(b))
            if best is None or score < best[0]:
                best = (score, [a, b])
    return best[1] if best else None


def _split_points(toks: list) -> list:
    """Where a chunk may be split: after sentence ends first, then after commas, then anywhere."""
    ends = [i + 1 for i, t in enumerate(toks[:-1]) if re.search(r"[.?!…。？！][\"'”’)]*$", t)]
    commas = [i + 1 for i, t in enumerate(toks[:-1]) if re.search(r"[,;:，、；：][\"'”’)]*$", t)]
    return [ends, commas, list(range(1, len(toks)))]


def _cues_for_line(text: str, words: list) -> list:
    toks, j = tokens(text), joiner(text)
    if not toks or not words:
        return []
    n, m = len(words), len(toks)

    def timing(i, k):
        a = min(n - 1, i * n // m)
        b = max(a, min(n - 1, math.ceil(k * n / m) - 1))
        return words[a][1], words[b][2]

    def ok(i, k):
        s, e = timing(i, k)
        return wrap(j.join(toks[i:k])) is not None and e - s <= CUE_MAX + TOL

    out = []

    def place(i, k):
        if k - i <= 1 or ok(i, k):
            s, e = timing(i, k)
            out.append({"start": s, "end": e, "lines": wrap(j.join(toks[i:k])) or [j.join(toks[i:k])]})
            return
        for points in _split_points(toks[i:k]):
            if points:
                mid = (k - i) / 2
                p = min(points, key=lambda x: abs(x - mid)) + i
                place(i, p)
                place(p, k)
                return

    # each sentence is a cue when it fits; longer sentences are split at commas, then in the middle
    starts = [0] + _split_points(toks)[0] + [m]
    for a, b in zip(starts, starts[1:]):
        place(a, b)
    return out


def subtitle_cues(d: Path, nar=None):
    """Cues [{start, end, lines}] from lines.json text and words.json timing, or None when the film has no voice lines."""
    nar = nar if nar is not None else narration(d)
    text_of = voice_lines(d, nar)
    if not nar or not text_of:
        return None
    cues = []
    for ln in nar["lines"]:
        cues += _cues_for_line(text_of.get(ln["id"], ""), ln["words"])
    cues.sort(key=lambda c: c["start"])
    for i, c in enumerate(cues):            # at least 1 s on screen, never over the next cue
        nxt = cues[i + 1]["start"] if i + 1 < len(cues) else float("inf")
        if c["end"] - c["start"] < CUE_MIN:
            c["end"] = min(c["start"] + CUE_MIN, nxt)
        c["end"] = min(c["end"], nxt)
    return cues


def write_srt(cues: list, path: Path) -> None:
    out = []
    for i, c in enumerate(cues, 1):
        out += [str(i), f"{srt_time(c['start'])} --> {srt_time(c['end'])}", *c["lines"], ""]
    path.write_text("\n".join(out), encoding="utf-8")


def read_srt(path: Path) -> list:
    cues = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").strip()):
        rows = block.split("\n")
        k = next((i for i, r in enumerate(rows) if "-->" in r), None)
        if k is None:
            continue
        m = re.findall(r"(\d+):(\d+):(\d+)[,.](\d+)", rows[k])
        if len(m) != 2:
            continue
        s, e = (int(h) * 3600 + int(mi) * 60 + int(se) + int(ms) / 1000 for h, mi, se, ms in m)
        cues.append({"start": s, "end": e, "lines": [r for r in rows[k + 1:] if r.strip()]})
    return cues


# ---------- sources and numbers ----------
def source_rows(d: Path) -> list:
    """Unique cited sources for the description: no fiction, no provided files (FR-004)."""
    s = scriptmod.read_sources(d / "SOURCES.md")
    seen, out = set(), []
    for r in s["rows"]:
        if r.get("kind") != "source" or r["url"].startswith("provided:") or r["url"] in seen:
            continue
        seen.add(r["url"])
        out.append(r)
    return out


ONES = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                   "fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}
SCALES = {"hundred": 100, "thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
DIGITS = re.compile(r"\d[\d.,]*\d|\d")


def _digit_values(tok: str) -> set:
    """A digit string read both ways ('1,200' and '1.200' are 1200 in en and vi; '1.2' and '1,2' are 1.2)."""
    for sep in (",", "."):                       # 3,000 or 3.000: thousands, never 3.0
        if re.fullmatch(r"\d{1,3}(?:" + re.escape(sep) + r"\d{3})+", tok):
            return {float(tok.replace(sep, ""))}
    try:
        return {float(tok.replace(",", "."))}     # 1.2 or 1,2
    except ValueError:
        return set()


def numbers(text: str, words_min: float = 10) -> list:
    """[(shown text, {values})]: digit numbers (with a following scale word) and English number words ≥ words_min."""
    found = []
    low = text.lower().replace("-", " ")
    for m in DIGITS.finditer(low):
        vals = _digit_values(m.group())
        nxt = re.match(r"\s*(hundred|thousand|million|billion|trillion|nghìn|ngàn|triệu|tỷ|tỉ)\b", low[m.end():])
        if nxt:
            mult = {"nghìn": 1e3, "ngàn": 1e3, "triệu": 1e6, "tỷ": 1e9, "tỉ": 1e9}.get(nxt.group(1)) or SCALES[nxt.group(1)]
            vals |= {v * mult for v in vals}
        found.append((m.group(), vals))
    words = re.findall(r"[a-z]+", low)
    i = 0
    while i < len(words):
        if words[i] in ONES or words[i] in TENS or words[i] in SCALES:
            total, cur, j, shown = 0.0, 0.0, i, []
            while j < len(words) and (words[j] in ONES or words[j] in TENS or words[j] in SCALES
                                      or (words[j] == "and" and shown)):
                w = words[j]
                prev = shown[-1] if shown else None
                if (w in ONES and (prev in ONES or (prev in TENS and ONES[w] >= 10))) or (w in TENS and (prev in ONES or prev in TENS)):
                    break                       # "one two three" is three numbers, not one
                if w in ONES:
                    cur += ONES[w]
                elif w in TENS:
                    cur += TENS[w]
                elif w == "hundred":
                    cur = (cur or 1) * 100
                elif w in SCALES:
                    total += (cur or 1) * SCALES[w]
                    cur = 0
                shown.append(w)
                j += 1
            v = total + cur
            if v >= words_min:
                found.append((" ".join(shown), {v}))
            i = j
        else:
            i += 1
    return found


def allowed_numbers(d: Path):
    """Every value the passed script and its sources name, or None when the film has neither file."""
    texts = []
    for f in ("SCRIPT.md", "SOURCES.md"):
        if (d / f).is_file():
            texts.append((d / f).read_text(encoding="utf-8"))
    if not texts:
        return None
    vals = set()
    for t in texts:
        for _, v in numbers(t, words_min=0):
            vals |= v
    return vals


# ---------- writing the pack ----------
def description_text(d: Path, pack: dict, chs: list) -> str:
    parts = ["\n".join(x.strip() for x in pack["hook"]), pack["summary"].strip()]
    if chs:
        parts.append("\n".join(f"{stamp(c['at'])} {c['title']}" for c in chs))
    src = source_rows(d)
    if src:
        parts.append("Sources:\n" + "\n".join(f"- {r['name']}, {r['year']}: {r['url']}" for r in src))
    parts.append(" ".join(pack["hashtags"]))
    return "\n\n".join(p for p in parts if p.strip()) + "\n"


def thumb_files(d: Path) -> list:
    """The thumbnail files that exist, in order (png or jpg)."""
    out = []
    for n in (1, 2, 3):
        f = next((d / "publish" / f"thumbnail-{n}.{e}" for e in ("png", "jpg")
                  if (d / "publish" / f"thumbnail-{n}.{e}").is_file()), None)
        out.append(f.name if f else f"thumbnail-{n}.png")
    return out


def write_titles(d: Path, pack: dict) -> None:
    files = thumb_files(d)
    rows = ["# Titles", ""]
    for i, t in enumerate(pack["titles"]):
        rows += [f"{i + 1}. **{ANGLE_LABEL.get(t['angle'], t['angle'])}:** {t['text']}",
                 f"   Thumbnail: {files[i]} (\"{t['thumb']['text']}\")"]
    (d / "publish" / "titles.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


def missing_notes(d: Path, nar, chapters_ok: bool, subs) -> list:
    notes = []
    if not nar:
        notes.append("Subtitles and chapters: the film has no narration.json (no narration, or made before the "
                     "studio wrote it).")
    else:
        if subs is None:
            notes.append("Subtitles: narration.json has no lines_file, so the spoken text is not known.")
        if not chapters_ok:
            notes.append("Chapters: the film is too short for 3 chapters of at least 10 s (YouTube's rule).")
    if not (d / "SCRIPT.md").is_file() and not (d / "SOURCES.md").is_file():
        notes.append("Numbers in the titles and description were not checked: the film has no SCRIPT.md or SOURCES.md.")
    return notes


def write_publish_md(d: Path, pack: dict, notes: list, problems: list) -> None:
    sc = script_or_none(d)
    title = sc["title"] if sc else d.name
    files = thumb_files(d)
    has_srt = (d / "publish" / "subtitles.srt").is_file()
    lang = pack.get("language") or (sc or {}).get("language") or ""
    rows = [f"# Publish: {title}", "",
            f"Video: ../{d.name}.mp4" + (f" · Subtitles: subtitles.srt ({lang})" if has_srt else ""), "",
            "## Pick one pair", "", "| # | Angle | Title | Thumbnail | Text on it |", "|---|---|---|---|---|"]
    for i, t in enumerate(pack["titles"]):
        cell = lambda s: str(s).replace("|", "\\|")        # noqa: E731
        rows.append(f"| {i + 1} | {ANGLE_LABEL.get(t['angle'], t['angle'])} | {cell(t['text'])} | {files[i]} | "
                    f"{cell(t['thumb']['text'])} |")
    desc = (d / "publish" / "description.md")
    rows += ["", "## Description (copy all)", "", "```text", desc.read_text(encoding="utf-8").rstrip() if desc.is_file() else "",
             "```"]
    repeated = sorted({int(n) for p in problems if p.startswith("lesson_rule") for n in re.findall(r"lesson #(\d+)", p)})
    if repeated:
        rows[1:1] = ["", "⚠ Do not publish yet: repeats lesson " + ", ".join(f"#{n}" for n in repeated)]
    if notes:
        rows += ["", "## Missing", "", *[f"- {n}" for n in notes]]
    if problems:
        rows += ["", "## Check problems", "", *[f"- {p}" for p in problems]]
    (d / "publish" / "PUBLISH.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


def render_thumbs(d: Path, pack: dict, lib) -> tuple:
    """Write thumbnail-1..3 and thumbs.json (R2, R3). Returns (rows, problem or None)."""
    pub = d / "publish"
    mp4 = mp4_of(d)
    if not mp4.is_file():
        raise PublishError(f"films/{d.name}/{d.name}.mp4 is missing")
    fw, fh = video_size(mp4)
    tw, th = thumb_size((fw, fh))
    js = Path(__file__).resolve().parent / "thumbs.mjs"
    why = None
    if not (d / "index.html").is_file():
        why = "the film has no index.html to draw from"
    elif not lib or not Path(lib, "core/render/page.mjs").is_file():
        why = "the film library is not installed"
    elif not shutil.which("node"):
        why = "node is not installed"
    if why:
        (pub / "thumbs.json").write_text(json.dumps({"error": why}), encoding="utf-8")
        return [], f"thumb_not_rendered: {why}"
    raw = pub / ".raw"
    shutil.rmtree(raw, ignore_errors=True)
    raw.mkdir()
    job = {"w": fw, "h": fh, "thumbs": [{k: t["thumb"].get(k) for k in
                                        ("t", "text", "position", "color", "plate", "plate_opacity", "font")}
                                       for t in pack["titles"]]}
    (raw / "job.json").write_text(json.dumps(job), encoding="utf-8")
    try:
        p = subprocess.run(["node", str(js), str(d), str(lib), str(raw / "job.json"), str(raw)],
                           capture_output=True, text=True, timeout=300)
        got = json.loads(p.stdout.strip().splitlines()[-1])["thumbs"]
    except (subprocess.TimeoutExpired, ValueError, IndexError, KeyError) as e:
        err = (locals().get("p").stderr.strip()[-300:] if locals().get("p") else str(e))
        (pub / "thumbs.json").write_text(json.dumps({"error": err}), encoding="utf-8")
        shutil.rmtree(raw, ignore_errors=True)
        return [], f"thumb_not_rendered: {err}"
    rows = []
    vf = f"scale={tw}:{th}:force_original_aspect_ratio=increase:flags=lanczos,crop={tw}:{th}"
    for i, g in enumerate(got, 1):
        out = pub / f"thumbnail-{i}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw / f"raw-{i}.png"), "-vf", vf, str(out)], check=True)
        if out.stat().st_size >= THUMB_BYTES:
            out.unlink()
            out = pub / f"thumbnail-{i}.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw / f"raw-{i}.png"), "-vf", vf, "-q:v", "2",
                            str(out)], check=True)
        glyphs, _ = qc.missing_glyphs(d, [g["text"]])
        rows.append({"file": out.name, "t": g["t"], "w": tw, "h": th, "bytes": out.stat().st_size, "text": g["text"],
                     "font": g.get("font"), "font_loaded": g.get("font_loaded", True),
                     "text_height_ratio": g.get("text_height_ratio"), "contrast": g.get("contrast"),
                     "bg_luma": g.get("bg_luma"), "missing_glyphs": glyphs,
                     "texts_checked": g.get("texts_checked", False), "covers": g.get("covers", [])})
    shutil.rmtree(raw, ignore_errors=True)
    (pub / "thumbs.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return rows, None


def build(d: Path, lib, draw: bool = True) -> list:
    """Write every file of the pack from pack.json. Returns problems found while making it (not the rules).
    draw=False keeps the thumbnails and thumbs.json as they are (tests, and the online test agent)."""
    d = Path(d)
    pack = read_pack(d)
    if not mp4_of(d).is_file():
        raise PublishError(f"films/{d.name}/{d.name}.mp4 is missing")
    pub = d / "publish"
    for f in pub.iterdir():
        if OWN_FILES.match(f.name) and (draw or not (f.name.startswith("thumb"))):
            f.unlink()
    problems = []
    if draw:
        _, why = render_thumbs(d, pack, lib)
        if why:
            problems.append(why)
    nar = narration(d)
    duration = qc.probe_duration(mp4_of(d))
    chs, applicable, _ = chapters(d, pack, nar, duration)
    cues = subtitle_cues(d, nar)
    if cues is not None:
        write_srt(cues, pub / "subtitles.srt")
    (pub / "description.md").write_text(description_text(d, pack, chs if applicable else []), encoding="utf-8")
    write_titles(d, pack)
    write_publish_md(d, pack, missing_notes(d, nar, applicable, cues), [])
    return problems


def finish(d: Path, result: dict) -> None:
    """Rewrite PUBLISH.md with the check's problems."""
    d = Path(d)
    pack = read_pack(d)
    nar = narration(d)
    write_publish_md(d, pack, missing_notes(d, nar, result["applicable"]["chapters"],
                                            [] if result["applicable"]["subtitles"] else None), result["problems"])


# ---------- the check (FR-009, contracts/cli.md) ----------
def _ngrams(ws: list, n: int) -> set:
    return {tuple(ws[i:i + n]) for i in range(len(ws) - n + 1)}


def repeats_title(thumb: str, title: str) -> bool:
    if is_cjk(thumb):
        a, b = "".join(qc.norm_words(thumb)), "".join(qc.norm_words(title))
        return a == b or any(a[i:i + 6] in b for i in range(len(a) - 5))
    a, b = qc.norm_words(thumb), qc.norm_words(title)
    return a == b or bool(_ngrams(a, 3) & _ngrams(b, 3))


def thumb_word_count_ok(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    return len(t.replace(" ", "")) <= THUMB_CJK if is_cjk(t) else len(t.split()) <= THUMB_WORDS


def title_break_ok(text: str) -> bool:
    if units(text) <= TITLE_VISIBLE:
        return True
    for b in BREAKS:
        i = text.find(b)
        while i >= 0:
            if 0 < units(text[:i + len(b.rstrip())]) <= TITLE_VISIBLE:
                return True
            i = text.find(b, i + 1)
    return False


def check(d: Path, pack: dict = None) -> dict:
    d = Path(d)
    pack = pack or read_pack(d)
    pub = d / "publish"
    nar = narration(d)
    mp4 = mp4_of(d)
    if not mp4.is_file():
        raise PublishError(f"films/{d.name}/{d.name}.mp4 is missing")
    duration = qc.probe_duration(mp4)
    problems, m = [], {}
    chs, ch_applicable, ch_problems = chapters(d, pack, nar, duration)
    subs_applicable = bool(nar and voice_lines(d, nar))
    applicable = {"chapters": ch_applicable, "subtitles": subs_applicable}

    # files (thumbnails that could not be drawn are reported once, as thumb_not_rendered)
    try:
        rows = json.loads((pub / "thumbs.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rows = {"error": "thumbs.json is missing"}
    need = (thumb_files(d) if isinstance(rows, list) else []) + ["titles.md", "description.md", "PUBLISH.md"]
    if subs_applicable:
        need.append("subtitles.srt")
    m["files_missing"] = [f for f in need if not (pub / f).is_file()]
    if m["files_missing"]:
        problems.append("files_missing: " + ", ".join(m["files_missing"]))

    # thumbnails
    tw, th = thumb_size(video_size(mp4))
    m["thumbs"] = []
    if isinstance(rows, dict):
        problems.append(f"thumb_not_rendered: {rows.get('error', 'no thumbnails')}")
    else:
        for i, r in enumerate(rows):
            f = pub / r.get("file", "")
            w, h = image_size(f) if f.is_file() else (0, 0)
            size = f.stat().st_size if f.is_file() else 0
            title = pack["titles"][i] if i < len(pack["titles"]) else {"text": "", "thumb": {"text": r.get("text", "")}}
            text = title["thumb"]["text"]
            row = {"file": f.name, "w": w, "h": h, "bytes": size, "text_height_ratio": r.get("text_height_ratio"),
                   "contrast": r.get("contrast"), "font_loaded": r.get("font_loaded", True),
                   "repeats_title": repeats_title(text, title["text"]), "missing_glyphs": r.get("missing_glyphs", [])}
            m["thumbs"].append(row)
            if (w, h) != (tw, th) or size >= THUMB_BYTES:
                problems.append(f"thumb_size: {f.name} is {w}×{h}, {size} bytes; needs {tw}×{th} and under {THUMB_BYTES} bytes")
            if not thumb_word_count_ok(text):
                problems.append(f"thumb_text_words: {f.name} text \"{text}\" must have 1–{THUMB_WORDS} words")
            if (row["text_height_ratio"] or 0) < TEXT_HEIGHT - TOL:
                problems.append(f"thumb_text_height: {f.name} text is {row['text_height_ratio'] or 0:.3f} of the picture's "
                                f"height; at least {TEXT_HEIGHT}")
            if (row["contrast"] or 0) < CONTRAST - TOL:
                problems.append(f"thumb_contrast: {f.name} contrast {row['contrast'] or 0:.1f}; at least {CONTRAST}")
            if row["missing_glyphs"]:
                problems.append(f"thumb_glyphs: {f.name} has characters with no font: "
                                + " ".join(g["codepoint"] for g in row["missing_glyphs"]))
            if not row["font_loaded"]:
                problems.append(f"thumb_font: {f.name} font \"{r.get('font')}\" did not load in the film's page")
            row["covers"] = [c for c in r.get("covers") or [] if c.get("ratio", 0) > COVER_MAX]
            row["texts_checked"] = r.get("texts_checked", False)
            if row["covers"]:
                problems.append(f"thumb_covers_text: {f.name} text covers the film's own text "
                                + "; ".join(f"\"{c['text']}\" {c['ratio']:.0%}" for c in row["covers"])
                                + f" (at most {COVER_MAX:.0%}); move it with position")
            if row["repeats_title"]:
                problems.append(f"thumb_repeats_title: {f.name} text repeats its title; it should add to the title")
    ts = [t["thumb"]["t"] for t in pack["titles"]]
    if any(abs(a - b) < 1 - TOL for i, a in enumerate(ts) for b in ts[i + 1:]):
        problems.append(f"thumb_same_time: thumbnails at {', '.join(f'{t:g}' for t in ts)} s; keep them at least 1 s apart")

    # titles
    angles = [t["angle"] for t in pack["titles"]]
    if tuple(angles) != ANGLES:
        problems.append(f"title_count: the 3 titles must be {', '.join(ANGLES)} in that order (got {', '.join(angles)})")
    m["title_lengths"] = [len(t["text"]) for t in pack["titles"]]
    m["title_breaks_ok"] = [title_break_ok(t["text"]) for t in pack["titles"]]
    for t, n, ok in zip(pack["titles"], m["title_lengths"], m["title_breaks_ok"]):
        if n > TITLE_MAX or not t["text"].strip():
            problems.append(f"title_length: \"{t['text'][:40]}…\" has {n} characters; 1–{TITLE_MAX}")
        if not ok:
            problems.append(f"title_break: \"{t['text'][:40]}…\" is over {TITLE_VISIBLE} wide with no break (: - | ? !) "
                            f"in the first {TITLE_VISIBLE}, so it is cut on phones")

    # description
    hook = [x.strip() for x in pack["hook"]]
    m["hook_chars"] = sum(len(x) for x in hook)
    if len(hook) != 2 or not all(hook) or m["hook_chars"] > HOOK_MAX:
        problems.append(f"hook_length: the opening must be 2 lines of at most {HOOK_MAX} characters together "
                        f"(got {len(hook)} lines, {m['hook_chars']} characters)")
    desc = (pub / "description.md").read_text(encoding="utf-8") if (pub / "description.md").is_file() else ""
    m["description_chars"] = len(desc)
    if len(desc) > DESC_MAX or len(pack["summary"]) > SUMMARY_MAX:
        problems.append(f"description_length: {len(desc)} characters (at most {DESC_MAX}); summary {len(pack['summary'])} "
                        f"(at most {SUMMARY_MAX})")
    tags = pack["hashtags"]
    m["hashtags"] = len(tags)
    if not 3 <= len(tags) <= 5 or not all(re.fullmatch(r"#[^\s#]{1,29}", x) for x in tags):
        problems.append(f"hashtags: needs 3–5 tags like #science, each at most 30 characters (got {tags})")
    shown = " ".join(t["text"] for t in pack["titles"]) + "\n" + desc
    m["angle_brackets"] = shown.count("<") + shown.count(">")
    if m["angle_brackets"]:
        problems.append("angle_brackets: YouTube does not accept < or > in titles or descriptions")

    # numbers
    allowed = allowed_numbers(d)
    m["numbers_checked"] = allowed is not None
    m["numbers_unsourced"] = []
    if allowed is not None:
        texts = [t["text"] for t in pack["titles"]] + [t["thumb"]["text"] for t in pack["titles"]] + hook \
            + [pack["summary"]] + [c["title"] for c in pack.get("chapters") or []] + tags
        for txt in texts:
            for shown_n, vals in numbers(txt):
                if not any(any(abs(v - a) <= 1e-9 * max(1, abs(a)) for a in allowed) for v in vals):
                    m["numbers_unsourced"].append(shown_n)
        for n in m["numbers_unsourced"]:
            problems.append(f"number_unsourced: \"{n}\" is not in SCRIPT.md or SOURCES.md")

    # the channel's rules and lessons (specs/012)
    from filmcheck import channels
    snap = channels.snapshot(d)
    m["lessons_repeated"] = []
    if snap:
        rules = snap["rules"]
        have = {t.lower() for t in tags}
        missing = [t for t in rules.get("hashtags") or [] if t.lower() not in have]
        if missing:
            problems.append(f"channel_hashtags: the channel always uses {' '.join(missing)}")
        shown_texts = [t["text"] for t in pack["titles"]] + [t["thumb"]["text"] for t in pack["titles"]] + hook \
            + [pack["summary"]] + [c["title"] for c in pack.get("chapters") or []]
        banned = sorted({w for txt in shown_texts for w, _ in channels.find_banned(txt, rules.get("banned") or [])})
        if banned:
            problems.append("channel_banned: never-use words of the channel: " + ", ".join(f'"{w}"' for w in banned))
        most = rules.get("title_max")
        for t in pack["titles"]:
            if most and len(t["text"]) > most:
                problems.append(f"channel_title_max: \"{t['text'][:40]}…\" has {len(t['text'])} characters; the channel allows {most}")
        for n, scope, phrase in channels.lesson_rules(snap, "phrase"):
            if any(channels.find_banned(txt, [phrase]) for txt in shown_texts):
                m["lessons_repeated"].append(n)
                problems.append(f"lesson_rule: repeats lesson {channels.lesson_label(n, scope)}: \"{phrase}\"")
        for n, scope, most in channels.lesson_rules(snap, "max_title_chars"):
            for t in pack["titles"]:
                if len(t["text"]) > most:
                    m["lessons_repeated"].append(n)
                    problems.append(f"lesson_rule: repeats lesson {channels.lesson_label(n, scope)}: a title of "
                                    f"{len(t['text'])} characters (at most {most})")
        m["lessons_repeated"] = sorted(set(m["lessons_repeated"]))

    # language
    sc = script_or_none(d)
    if sc and pack.get("language", "").lower().split("-")[0] != sc["language"]:
        problems.append(f"language: pack.json says '{pack.get('language')}' but the film is in '{sc['language']}'")

    # chapters
    m["chapters"] = [{"at": c["at"], "title": c["title"], "length": c.get("length")} for c in chs]
    m["chapters_bad"] = ch_problems
    problems += ch_problems

    # subtitles
    m["subtitles_match"], m["subtitle_cues_bad"], m["subtitle_start_offset_max"] = None, [], None
    if subs_applicable and (pub / "subtitles.srt").is_file():
        cues = read_srt(pub / "subtitles.srt")
        said = "".join(qc.norm_words(" ".join(" ".join(c["lines"]) for c in cues)))
        want_src = " ".join(p["text"] for p in sc["paragraphs"]) if sc else \
            " ".join(voice_lines(d, nar).get(ln["id"], "") for ln in nar["lines"])
        want = "".join(qc.norm_words(want_src))
        m["subtitles_match"] = said == want
        if not m["subtitles_match"]:
            i = next((k for k, (a, b) in enumerate(zip(said, want)) if a != b), min(len(said), len(want)))
            problems.append(f"subtitles_text: the subtitles differ from the script near \"{want[max(0, i - 10):i + 20]}\"")
        prev_end = 0.0
        for k, c in enumerate(cues, 1):
            why = []
            if len(c["lines"]) > CUE_LINES:
                why.append(f"{len(c['lines'])} lines")
            if any(units(x) > CUE_UNITS for x in c["lines"]):
                why.append(f"a line over {CUE_UNITS}")
            length = c["end"] - c["start"]
            if length < CUE_MIN - TOL or length > CUE_MAX + TOL:
                why.append(f"{length:.2f} s on screen")
            if c["start"] < prev_end - TOL:
                why.append("starts before the previous cue ends")
            prev_end = c["end"]
            if why:
                m["subtitle_cues_bad"].append({"cue": k, "at": round(c["start"], 2), "why": why})
                problems.append(f"subtitles_cue: cue {k} at {c['start']:.1f} s: " + ", ".join(why))
        starts = [w[1] for ln in nar["lines"] for w in ln["words"]]
        if cues and starts:
            m["subtitle_start_offset_max"] = round(max(min(abs(c["start"] - s) for s in starts) for c in cues), 3)
    return {"pass": not problems, "cut": None, "applicable": applicable, "measures": m, "problems": problems}


def save(d: Path, result: dict, at: str) -> None:
    def put(x):
        x["publish"] = {**result, "at": at}
    report.update(Path(d), put)
