"""Block channel names, people, titles and verbatim lines from style files (research.md §12, FR-015, FR-021)."""
import re
import sys
import unicodedata
from pathlib import Path

from . import refset

NGRAM = 6
TOKEN = re.compile(r"[a-z0-9]+|[぀-ヿ㐀-䶿一-鿿]")


def norm(s: str) -> str:
    s = (s or "").replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def tokens(s: str) -> list:
    return TOKEN.findall(norm(s))


GENERIC = {"the", "a", "an", "of", "and", "official", "channel", "tv", "studio", "studios", "media", "kenh", "vlog"}


def deny_terms(data: dict) -> list:
    """Each term as a token sequence: channel, handle, titles, and the user's own list.
    Channel names of 3+ words also block every 2-word piece, so "Mèo Lười Night" is caught for "Mèo Lười Studio"."""
    raw, names_ = list(data.get("deny", [])), []
    for v in data.get("videos", []):
        raw += [v.get("channel"), v.get("title"), v.get("handle")]
        names_.append(v.get("channel"))
    terms = []

    def add(tk):
        if tk and len("".join(tk)) >= 3 and tk not in terms:
            terms.append(tk)
    for t in raw:
        add(tokens(t or ""))
    for n in names_:
        tk = tokens(n or "")
        if len(tk) >= 3:
            for i in range(len(tk) - 1):
                if not set(tk[i:i + 2]) <= GENERIC:
                    add(tk[i:i + 2])
    return terms


def proper_nouns(name: str) -> list:
    """Capitalised words inside sentences (not at their start) that occur twice or more in the transcripts:
    likely names of people or characters, so they are blocked too (FR-015)."""
    counts = {}
    for f in (refset.set_dir(name) / "profile").glob("*/words.json"):
        words = [w.get("word", "").strip() for w in refset.read_json(f).get("words", [])]
        for i, w in enumerate(words):
            core = w.strip("\"'“”‘’()[],;:.!?")
            if i == 0 or not core[:1].isupper() or core == "I" or len(core) < 3:
                continue
            if words[i - 1].rstrip("\"'”’)").endswith((".", "!", "?")):
                continue                              # start of a sentence: capitalised anyway
            tk = tokens(core)
            if tk:
                counts[tuple(tk)] = counts.get(tuple(tk), 0) + 1
    return [list(k) for k, n in counts.items() if n >= 2]


def transcript_grams(name: str) -> set:
    grams = set()
    pdir = refset.set_dir(name) / "profile"
    for f in pdir.glob("*/words.json"):
        tk = []
        for w in refset.read_json(f).get("words", []):
            tk += tokens(w.get("word", ""))
        grams.update(tuple(tk[i:i + NGRAM]) for i in range(len(tk) - NGRAM + 1))
    return grams


def _scan(text: str, terms: list, grams: set) -> list:
    """[(line, phrase, reason)] over the whole text, so a quote split across lines is still caught."""
    seq = []
    for ln, line in enumerate(text.splitlines(), 1):
        seq += [(t, ln) for t in tokens(line)]
    words = [t for t, _ in seq]
    found, seen, covered = [], set(), set()
    terms = sorted(terms, key=len, reverse=True)          # report the longest match only
    for i in range(len(words)):
        for tk in terms:
            span = set(range(i, i + len(tk)))
            if words[i:i + len(tk)] == tk and not span & covered:
                covered |= span
                found.append((seq[i][1], " ".join(tk), "tên kênh, tiêu đề hoặc tên bị cấm"))
        g = tuple(words[i:i + NGRAM])
        if len(g) == NGRAM and g in grams and (seq[i][1], g) not in seen:
            seen.add((seq[i][1], g))
            found.append((seq[i][1], " ".join(g), f"trùng {NGRAM} từ liên tiếp với lời thoại gốc"))
    return found


def _context(name: str):
    data = refset.load(name)
    terms = deny_terms(data)
    terms += [t for t in proper_nouns(name) if t not in terms]
    return terms, transcript_grams(name)


def check_files(name: str, files) -> list:
    terms, grams = _context(name)
    out = []
    for f in files:
        f = Path(f)
        for ln, phrase, why in _scan(f.read_text(encoding="utf-8", errors="replace"), terms, grams):
            out.append({"file": str(f), "line": ln, "phrase": phrase, "reason": why})
    return out


def check_strings(name: str, strings) -> list:
    terms, grams = _context(name)
    return [{"file": "(tên)", "line": 1, "phrase": p, "reason": r}
            for s in strings if s for _, p, r in _scan(s.replace("-", " "), terms, grams)]


def report(violations) -> None:
    for v in violations:
        print(f"{v['file']}:{v['line']}: \"{v['phrase']}\" ({v['reason']})", file=sys.stderr)


def cli(name: str, files) -> int:
    v = check_files(name, files)
    if v:
        report(v)
        print(f"✗ {len(v)} vi phạm: sửa rồi chạy lại.", file=sys.stderr)
        return 1
    print("✓ không có tên kênh, tiêu đề hay câu thoại nguyên văn.")
    return 0
