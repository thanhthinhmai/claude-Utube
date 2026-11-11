"""SCRIPT.md / SOURCES.md and the machine script check (specs/010 R2, R9; contracts/cli.md, contracts/files.md).

Plain Python, no network, no Claude. check() returns one machine round; the CLI saves it in checks.json."""
import json
import re
from pathlib import Path

CHAR_LANGS = {"zh", "ja", "ko"}                       # counted by character, not by word
SPEED = {"en": 150, "vi": 170, "zh": 4.5, "ja": 4.5, "ko": 4.5}   # words/min, or characters/second for CHAR_LANGS
DEFAULT_WPM, DEFAULT_CPS = 150, 4.5
PASS_SCORE = 7.0
LONG_WORDS, LONG_CHARS = 25, 40
HOOK_WINDOW, RETENTION_GAP, RETENTION_MIN_FILM = 30.0, 90.0, 90.0

DEDUCT = {"long_sentence": 0.5, "no_hook": 2.0, "intro_opening": 2.0, "retention_gap": 1.0, "cliche": 0.5,
          "risky_number": 0.5, "punctuation": 0.5}

NUMBER_WORDS = {
    "en": r"\b(?:ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|"
          r"fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|trillion)s?\b",
    "vi": r"(?<!\w)(?:mười|mươi|trăm|nghìn|ngàn|triệu|tỷ|tỉ)(?!\w)",
    "zh": r"[十百千万萬亿億]", "ja": r"[十百千万億]", "ko": r"[십백천만억]",
}
TWIST = {
    "en": r"\b(?:but|yet|actually|never|only|why|what if|how come|surprisingly|secret)\b",
    "vi": r"(?<!\w)(?:nhưng|thật ra|thực ra|chưa từng|chưa bao giờ|tại sao|vì sao|bí mật|ngờ đâu|hóa ra|hoá ra)(?!\w)",
    "zh": r"(?:但是|可是|其实|为什么|竟然|从未|秘密)",
}
INTRO = {
    "en": r"^(?:welcome|hi\b|hello|hey\b|in this video|today we|today i|today,? we|don't forget to subscribe|subscribe)",
    "vi": r"^(?:xin chào|chào mừng|chào các bạn|trong video này|hôm nay chúng ta|hôm nay mình|đăng ký kênh)",
    "zh": r"^(?:大家好|欢迎|今天我们|在这个视频)",
}
RISKY = [   # numbers that Kokoro and Whisper read differently from how they are written (lib core/tts/asr_check.py)
    (r"\b\d{1,3}(?:,\d{3})+\b|\b\d{4,}\b", "large number or year written in digits"),
    (r"\b\d+[.,]\d+\b", "decimal written in digits"),
    (r"\d+\s?%", "percentage written in digits"),
    (r"\b\d+(?:st|nd|rd|th)\b", "ordinal written in digits"),
    (r"\b\d{1,2}:\d{2}\b", "time written in digits"),
    (r"\b\d+\s?(?:km/h|km|kg|mph|kph|cm|mm|lbs?|ft|mi|°[CF])(?!\w)", "unit abbreviation after a number"),
]
SENT_END = re.compile(r"(?<=[.?!…])[\"'”’)]*\s+|(?<=[。？！])")
CLICHES_DIR = Path(__file__).resolve().parent / "cliches"


class ScriptError(Exception):
    """The script cannot be read (missing file, bad header): exit code 2."""


# ---------- reading ----------
def read_script(path: Path) -> dict:
    if not path.is_file():
        raise ScriptError(f"{path.name} is missing")
    head, paras, cur = {}, [], None
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith(">"):
            continue
        m = re.match(r"^\[(P\d+)\]\s*(.*)$", line)
        if m:
            cur = {"id": m.group(1), "text": m.group(2).strip(), "line": n}
            paras.append(cur)
        elif cur is None:
            k = re.match(r"^(\w+):\s*(.*?)\s*(?:#.*)?$", line)
            if not k:
                raise ScriptError(f"SCRIPT.md line {n}: expected 'Key: value' before the first paragraph")
            head[k.group(1).lower()] = k.group(2)
        else:
            cur["text"] = (cur["text"] + " " + line).strip()
    for key in ("title", "target", "language"):
        if not head.get(key):
            raise ScriptError(f"SCRIPT.md: the '{key.capitalize()}:' line is missing")
    if len(head["title"]) > 100:
        raise ScriptError("SCRIPT.md: the title is longer than 100 characters")
    t = re.fullmatch(r"(\d+)s", head["target"])
    if not t or not 5 <= int(t.group(1)) <= 900:
        raise ScriptError("SCRIPT.md: 'Target:' must be whole seconds from 5 to 900, like 45s")
    lang = head["language"].lower().split("-")[0]
    if not re.fullmatch(r"[a-z]{2,3}", lang):
        raise ScriptError("SCRIPT.md: 'Language:' must be a language code such as en, vi or zh")
    speed = None
    if head.get("speed"):
        try:
            speed = float(head["speed"])
        except ValueError:
            raise ScriptError("SCRIPT.md: 'Speed:' must be a number") from None
        if speed <= 0:
            raise ScriptError("SCRIPT.md: 'Speed:' must be above 0")
    return {"title": head["title"], "target": int(t.group(1)), "language": lang,
            "speed": speed or SPEED.get(lang, DEFAULT_CPS if lang in CHAR_LANGS else DEFAULT_WPM), "paragraphs": paras}


def read_sources(path: Path) -> dict:
    """{'none': bool, 'rows': [...], 'bad': [(line, why)]}"""
    if not path.is_file():
        return {"none": False, "rows": [], "bad": [(0, "SOURCES.md is missing")], "missing": True}
    rows, bad, none = [], [], False
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.strip().startswith(">")]
    if len(lines) == 1 and lines[0].lower().rstrip(".") == "no factual claims":
        return {"none": True, "rows": [], "bad": []}
    for n, line in enumerate(lines, 1):
        m = re.match(r'^-\s*\[(P\d+)\]\s*"([^"]+)"\s*:\s*(.+)$', line)
        if not m:
            bad.append((n, f'expected - [Pnn] "quote": source, year, link — got: {line[:60]}'))
            continue
        para, quote, rest = m.groups()
        if rest.strip().lower() == "fiction":
            rows.append({"para": para, "quote": quote, "kind": "fiction"})
            continue
        parts = [p.strip() for p in rest.rsplit(",", 2)]
        if len(parts) != 3 or not re.fullmatch(r"\d{4}", parts[1]):
            bad.append((n, f"{para}: expected 'name, year (4 digits), link'"))
            continue
        name, year, link = parts
        if not (link.startswith(("http://", "https://")) or link.startswith("provided:")):
            bad.append((n, f"{para}: the link must start with http(s):// or provided:"))
            continue
        rows.append({"para": para, "quote": quote, "name": name, "year": year, "url": link, "kind": "source"})
    return {"none": none, "rows": rows, "bad": bad}


def read_opened(film_dir: Path) -> set:
    try:
        rows = json.loads((film_dir / ".check" / "opened.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    ok = set()
    for r in rows if isinstance(rows, list) else []:
        if isinstance(r, dict) and 200 <= int(r.get("status") or 0) < 300:
            ok.update(u for u in (r.get("url"), r.get("final_url")) if u)
    return ok


# ---------- text ----------
def sentences(text: str) -> list:
    return [s.strip() for s in SENT_END.split(text) if s and s.strip()]


def count(text: str, lang: str) -> int:
    if lang in CHAR_LANGS:
        return len(re.findall(r"[^\s\W]", text))
    return len(text.split())


def seconds(units: int, sc: dict) -> float:
    return units / sc["speed"] if sc["language"] in CHAR_LANGS else units / sc["speed"] * 60


def has_number(s: str, lang: str) -> bool:
    return bool(re.search(r"\d", s) or re.search(NUMBER_WORDS.get(lang, NUMBER_WORDS["en"]), s, re.I))


def signal(s: str, lang: str) -> bool:
    """A hook or retention marker: a question, a number, or a twist word."""
    return "?" in s or "？" in s or has_number(s, lang) or bool(re.search(TWIST.get(lang, TWIST["en"]), s, re.I))


def cliches(lang: str) -> list:
    p = CLICHES_DIR / f"{lang}.txt"
    if not p.is_file():
        return []
    return [ln.strip().lower() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]


def flat(sc: dict) -> list:
    """Every sentence with its paragraph, index in the paragraph (1-based), start time and length in units."""
    out, units = [], 0
    for p in sc["paragraphs"]:
        for i, s in enumerate(sentences(p["text"]), 1):
            n = count(s, sc["language"])
            out.append({"para": p["id"], "n": i, "text": s, "start": seconds(units, sc), "units": n})
            units += n
    return out


# ---------- paragraphs kept between review rounds (R9) ----------
def para_map(sc: dict) -> dict:
    return {p["id"]: re.sub(r"[ \t]+$", "", p["text"]) for p in sc["paragraphs"]}


def last_review(film_dir: Path):
    """(round, snapshot path, flagged paragraphs) of the newest editor round, or None."""
    chk = film_dir / ".check"
    rounds = sorted(int(m.group(1)) for p in chk.glob("review-r*.json") if (m := re.fullmatch(r"review-r(\d+)\.json", p.name)))
    if not rounds:
        return None
    n = rounds[-1]
    try:
        rv = json.loads((chk / f"review-r{n}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rv = {}
    flagged = {i.get("para") for i in rv.get("issues", []) if isinstance(i, dict) and i.get("level") in ("P1", "P2")}
    return n, chk / f"script-r{n}.md", flagged


def unchanged_issues(film_dir: Path, sc: dict) -> list:
    lr = last_review(film_dir)
    if not lr or not lr[1].is_file():
        return []
    try:
        before = para_map(read_script(lr[1]))
    except ScriptError:
        return []
    now = para_map(sc)
    out = []
    for pid in sorted(set(before) | set(now)):
        if before.get(pid) != now.get(pid) and pid not in lr[2]:
            what = "was added" if pid not in before else "was removed" if pid not in now else "changed"
            out.append({"para": pid, "sentence": 0, "rule": "unchanged",
                        "detail": f"{pid} {what} but the editor did not flag it (P1 or P2)"})
    return out


# ---------- the check ----------
def check(film_dir: Path, customer_round: bool = False) -> dict:
    film_dir = Path(film_dir)
    sc = read_script(film_dir / "SCRIPT.md")
    lang, issues = sc["language"], []
    hard = {"format": True, "sources": True, "length": True, "unchanged": True}

    def add(para, n, rule, detail):
        issues.append({"para": para, "sentence": n, "rule": rule, "detail": detail})

    # format: paragraph numbers P01, P02 … in order, none empty
    for i, p in enumerate(sc["paragraphs"], 1):
        if p["id"] != f"P{i:02d}":
            hard["format"] = False
            add(p["id"], 0, "format", f"expected [P{i:02d}] here (paragraphs are numbered P01, P02 … in order)")
        if not p["text"]:
            hard["format"] = False
            add(p["id"], 0, "format", "the paragraph is empty")
    if not sc["paragraphs"]:
        hard["format"] = False
        add("P01", 0, "format", "the script has no [P01] paragraph")

    sents = flat(sc)
    total = seconds(sum(s["units"] for s in sents), sc)
    texts = para_map(sc)

    # sources
    src = read_sources(film_dir / "SOURCES.md")
    opened = read_opened(film_dir)
    for n, why in src["bad"]:
        hard["sources"] = False
        add("P01" if not n else "SOURCES", n, "sources", why)
    by_para = {}
    for r in src["rows"]:
        if r["para"] not in texts:
            hard["sources"] = False
            add(r["para"], 0, "sources", f"SOURCES.md names {r['para']}, which the script does not have")
            continue
        if r["quote"].lower() not in texts[r["para"]].lower():
            hard["sources"] = False
            add(r["para"], 0, "sources", f'the quote "{r["quote"][:40]}" is not in {r["para"]}')
        if r["kind"] == "source" and r["url"].startswith("http") and r["url"] not in opened:
            hard["sources"] = False
            add(r["para"], 0, "sources", f"{r['url'][:80]} was never opened with `studio web fetch --film`")
        by_para.setdefault(r["para"], []).append(r)
    for s in sents:
        if has_number(s["text"], lang) and not by_para.get(s["para"]):
            hard["sources"] = False
            add(s["para"], s["n"], "sources", "this sentence has a number but SOURCES.md has no line for "
                + s["para"] + ' (a source, provided:<file>, or "fiction" for an invented detail)')

    # length
    lo, hi = sc["target"] * 0.85, sc["target"] * 1.15
    if not lo <= total <= hi:
        hard["length"] = False
        add("P01", 0, "length", f"reads in about {total:.0f} s; the target is {sc['target']} s (allowed {lo:.0f}–{hi:.0f} s)")

    # unchanged paragraphs since the last editor round (not for a round the customer asked for)
    if not customer_round:
        for i in unchanged_issues(film_dir, sc):
            hard["unchanged"] = False
            issues.append(i)

    # the channel's rules and lessons (specs/012), only for a film with a channel snapshot
    from filmcheck import channels
    snap = channels.snapshot(film_dir)
    if snap:
        rules = snap["rules"]
        hard["channel_language"] = lang == (rules.get("language") or lang)
        if not hard["channel_language"]:
            add("P01", 0, "channel_language", f"the script is in '{lang}' but the channel is in '{rules['language']}'")
        hard["banned_word"] = True
        for s in sents:
            for w, _ in channels.find_banned(s["text"], rules.get("banned") or []):
                hard["banned_word"] = False
                add(s["para"], s["n"], "banned_word", f'"{w}" is on the channel\'s never-use list')
        hard["lesson_rule"] = True
        for n, scope, phrase in channels.lesson_rules(snap, "phrase"):
            for s in sents:
                if channels.find_banned(s["text"], [phrase]):
                    hard["lesson_rule"] = False
                    issues.append({"para": s["para"], "sentence": s["n"], "rule": "lesson_rule", "lesson": n,
                                   "detail": f'repeats lesson {channels.lesson_label(n, scope)}: "{phrase}"'})
        for n, scope, most in channels.lesson_rules(snap, "max_sentence_words"):
            for s in sents:
                if s["units"] > most:
                    hard["lesson_rule"] = False
                    issues.append({"para": s["para"], "sentence": s["n"], "rule": "lesson_rule", "lesson": n,
                                   "detail": f"repeats lesson {channels.lesson_label(n, scope)}: {s['units']} {'characters' if lang in CHAR_LANGS else 'words'} (at most {most})"})

    score = 10.0
    # long sentences
    limit = LONG_CHARS if lang in CHAR_LANGS else LONG_WORDS
    unit = "characters" if lang in CHAR_LANGS else "words"
    for s in sents:
        if s["units"] > limit:
            score -= DEDUCT["long_sentence"]
            add(s["para"], s["n"], "long_sentence", f"{s['units']} {unit} (at most {limit})")
    # hook
    window = HOOK_WINDOW if sc["target"] >= 30 else sc["target"] * 0.2
    if sents and not any(signal(s["text"], lang) for s in sents if s["start"] < window):
        score -= DEDUCT["no_hook"]
        add(sents[0]["para"], 1, "no_hook", f"no question, number or twist in the first {window:.0f} s")
    if sents and re.search(INTRO.get(lang, INTRO["en"]), sents[0]["text"], re.I):
        score -= DEDUCT["intro_opening"]
        add(sents[0]["para"], 1, "intro_opening", "the film opens with a greeting or a channel introduction")
    # retention markers (films of 90 s or more)
    if sc["target"] >= RETENTION_MIN_FILM and sents:
        marks = [0.0] + [s["start"] for s in sents if signal(s["text"], lang)] + [total]
        prev_para = sents[0]["para"]
        for a, b in zip(marks, marks[1:]):
            if b - a > RETENTION_GAP:
                where = next((s for s in sents if s["start"] >= a), sents[0])
                prev_para = where["para"]
                score -= DEDUCT["retention_gap"]
                add(prev_para, where["n"], "retention_gap", f"{b - a:.0f} s without a question, number or twist "
                    f"(from {a:.0f} s to {b:.0f} s; at most {RETENTION_GAP:.0f} s)")
    # cliches
    for s in sents:
        low = s["text"].lower()
        for c in cliches(lang):
            if re.search(r"(?<!\w)" + re.escape(c) + r"(?!\w)", low):
                score -= DEDUCT["cliche"]
                add(s["para"], s["n"], "cliche", f'"{c}"')
    # numbers the voice reads wrong
    if lang not in CHAR_LANGS:
        for s in sents:
            for rx, why in RISKY:
                for m in re.finditer(rx, s["text"]):
                    score -= DEDUCT["risky_number"]
                    add(s["para"], s["n"], "risky_number", f'"{m.group(0)}": {why}; write it the way it is read')
    # brackets and dashes
    words = max(1, sum(count(p["text"], lang) for p in sc["paragraphs"]))
    marks_n = sum(p["text"].count("(") + p["text"].count("（") + len(re.findall(r"—|–|\s-\s", p["text"])) for p in sc["paragraphs"])
    if marks_n / words * 100 > 1:
        score -= DEDUCT["punctuation"]
        add("P01", 0, "punctuation", f"{marks_n} brackets or dashes in {words} {unit} (at most 1 per 100); the voice reads them badly")

    score = round(max(0.0, score), 1)
    return {"score": score, "hard": hard, "issues": issues, "pass": score >= PASS_SCORE and all(hard.values()),
            "est_seconds": round(total, 1), "language": lang}
