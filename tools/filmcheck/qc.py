"""Measure a finished film (specs/010 FR-011, FR-012; research R5, R7; contracts/cli.md `qc`).

Narration: from narration.json plus the library's words.json and dur.json (absolute time = line start + word time).
Picture: ffmpeg freezedetect (stills) and scdet (cuts, when narration.json has none). Text: window.TEXTS and the .srt
against the fonts fontconfig and the film folder have. No Claude, no network."""
import json
import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

SILENCE_MAX, LONG_PAUSE, CUT_AFTER, KEY_SHOT, TAIL_MAX, STILL_MAX = 0.20, 0.8, 0.4, 2.5, 1.5, 6.0
EPS = 0.05
FONT_EXT = (".ttf", ".otf", ".woff", ".woff2", ".ttc")
STYLES_FILE = Path(__file__).resolve().parent / "styles.json"


class QcError(Exception):
    """The film cannot be measured (exit code 2)."""


# ---------- narration ----------
def load_narration(d: Path):
    p = d / "narration.json"
    if not p.is_file():
        return None
    try:
        n = json.loads(p.read_text(encoding="utf-8"))
        words = json.loads((d / n["words_file"]).read_text(encoding="utf-8"))
        durs = json.loads((d / n["durations_file"]).read_text(encoding="utf-8")) if n.get("durations_file") else {}
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise QcError(f"narration.json or its voice files cannot be read: {e}") from None
    lines = []
    for ln in n.get("lines") or []:
        lid = ln.get("id")
        if lid not in words or not words[lid]:
            raise QcError(f"narration.json does not match the voice files: no words for line {lid}")
        ws = [(str(w[0]), float(ln["at"]) + float(w[1]), float(ln["at"]) + float(w[2])) for w in words[lid]]
        if durs:          # each line's words end within 0.5 s of its audio (both ways; research R5, T037)
            if lid not in durs:
                raise QcError(f"narration.json does not match the voice files: line {lid} is not in {n['durations_file']}")
            if abs(float(words[lid][-1][2]) - float(durs[lid])) > 0.5:
                raise QcError(f"narration.json does not match the voice files: line {lid} lasts {float(durs[lid]):.2f} s "
                              f"but its words end at {float(words[lid][-1][2]):.2f} s")
        lines.append({"id": lid, "para": ln.get("para") or "?", "at": float(ln["at"]), "words": ws})
    if not lines:
        raise QcError("narration.json has no lines")
    cuts = n.get("cuts")
    return {"lines": sorted(lines, key=lambda x: x["at"]), "cuts": [float(c) for c in cuts] if cuts else None,
            "lines_file": n.get("lines_file")}


def norm_words(text: str) -> list:
    return re.sub(r"[^\w\s]", " ", text.lower().replace("’", "'").replace("'", "")).split()


_norm = norm_words      # the old name, kept for 010 code


def voice_matches_script(d: Path, nar: dict):
    """None when it matches; else a problem. The voice lines (the library's lines.json, in narration order) must say
    exactly the passed script (specs/010 US1/AC6, T035). Case, punctuation and spacing do not count."""
    if not (d / "SCRIPT.md").is_file():
        return None
    if not nar.get("lines_file"):
        return "narration.json has no lines_file, so the voice cannot be checked against SCRIPT.md"
    try:
        rows = json.loads((d / nar["lines_file"]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return f"the voice lines ({nar['lines_file']}) cannot be read: {e}"
    from filmcheck import script as scriptmod
    try:
        sc = scriptmod.read_script(d / "SCRIPT.md")
    except scriptmod.ScriptError as e:
        return f"SCRIPT.md cannot be read: {e}"
    text_of = {r.get("id"): r.get("text", "") for r in rows if isinstance(r, dict)}
    voice = [w for ln in nar["lines"] for w in _norm(text_of.get(ln["id"], ""))]
    said, owner = [], []
    for p in sc["paragraphs"]:
        ws = _norm(p["text"])
        said += ws
        owner += [p["id"]] * len(ws)
    if voice == said:
        return None
    i = next((k for k, (a, b) in enumerate(zip(voice, said)) if a != b), min(len(voice), len(said)))
    para = owner[min(i, len(owner) - 1)] if owner else "P01"
    got = " ".join(voice[i:i + 6]) or "(nothing)"
    want = " ".join(said[i:i + 6]) or "(nothing)"
    return f"the voice does not say the passed script from {para}: it says \"{got}\" where the script has \"{want}\""


def sentences(lines: list) -> list:
    """(start, end, para) of every sentence: a line ends a sentence, and so does a word ending in . ? ! …"""
    out = []
    for ln in lines:
        start = None
        for i, (w, s, e) in enumerate(ln["words"]):
            start = s if start is None else start
            if re.search(r"[.?!…。？！][\"'”’)]*$", w) or i == len(ln["words"]) - 1:
                out.append((start, e, ln["para"]))
                start = None
    return sorted(out)


def narration_measures(nar: dict, duration: float, cuts: list) -> tuple:
    words = sorted((s, e, ln["para"]) for ln in nar["lines"] for (_, s, e) in ln["words"])
    first, last = words[0][0], max(e for _, e, _ in words)
    if last > duration + EPS:
        raise QcError(f"narration.json does not match the film: the last word ends at {last:.2f} s, after the film ({duration:.2f} s)")
    m, problems = {}, []
    # silence: the span from the first word to the last, minus the time covered by words
    covered, cur_s, cur_e = 0.0, None, None
    for s, e, _ in words:
        if cur_e is None or s > cur_e:
            covered += (cur_e - cur_s) if cur_e is not None else 0
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    covered += cur_e - cur_s
    span = max(last - first, 1e-6)
    m["silence_ratio"] = round(1 - covered / span, 3)
    if m["silence_ratio"] > SILENCE_MAX:
        problems.append(f"the narration is silent {m['silence_ratio']:.0%} of the time; at most {SILENCE_MAX:.0%}")
    # long pauses only between paragraphs
    m["long_pauses_bad"] = []
    for (s0, e0, p0), (s1, _, p1) in zip(words, words[1:]):
        gap = s1 - e0
        if gap >= LONG_PAUSE - 1e-9 and p0 == p1:
            m["long_pauses_bad"].append({"at": round(e0, 2), "length": round(gap, 2)})
    for b in m["long_pauses_bad"]:
        problems.append(f"a {b['length']:.1f} s pause at {b['at']:.1f} s inside one paragraph; long pauses belong between paragraphs")
    # cuts: never inside a sentence, and not too soon after one ends
    sents = sentences(nar["lines"])
    m["cuts_bad"] = []
    for c in cuts:
        if c <= EPS or c >= duration - EPS:
            continue
        inside = [x for x in sents if x[0] + EPS < c < x[1] - EPS]
        if inside:
            m["cuts_bad"].append({"at": round(c, 2), "sentence_end": round(inside[0][1], 2)})
            continue
        before = [x[1] for x in sents if x[1] <= c + EPS]
        after = [x[0] for x in sents if x[0] >= c - EPS]
        if before:
            gap = (min(after) - max(before)) if after else float("inf")
            if c - max(before) < min(CUT_AFTER, gap) - EPS:
                m["cuts_bad"].append({"at": round(c, 2), "sentence_end": round(max(before), 2)})
    for b in m["cuts_bad"]:
        problems.append(f"a cut at {b['at']:.1f} s comes before the sentence ending at {b['sentence_end']:.1f} s has settled "
                        f"(cut at least {CUT_AFTER} s after a sentence, never inside one)")
    # the shot holding each paragraph's last word
    bounds = sorted({0.0, duration, *[c for c in cuts if EPS < c < duration - EPS]})
    last_word = {}
    for s, e, p in words:
        last_word[p] = max(last_word.get(p, 0), e)
    m["key_shots_bad"] = []
    for p, t in sorted(last_word.items(), key=lambda kv: kv[1]):
        for a, b in zip(bounds, bounds[1:]):
            if a <= t - 1e-6 < b or (b == bounds[-1] and t <= b):
                if b - a < KEY_SHOT - 1e-6:
                    m["key_shots_bad"].append({"para": p, "shot_length": round(b - a, 2)})
                break
    for b in m["key_shots_bad"]:
        problems.append(f"the shot with the last words of {b['para']} lasts {b['shot_length']:.2f} s; at least {KEY_SHOT} s")
    m["tail_s"] = round(duration - last, 2)
    if m["tail_s"] > TAIL_MAX:
        problems.append(f"the film ends {m['tail_s']:.1f} s after the last word; at most {TAIL_MAX} s")
    return m, problems


# ---------- picture ----------
def probe_duration(mp4: Path) -> float:
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)],
                       capture_output=True, text=True)
    try:
        return float(p.stdout.strip())
    except ValueError:
        raise QcError(f"{mp4.name} cannot be read: {p.stderr.strip()[-200:]}") from None


def picture(mp4: Path, still_max: float, want_cuts: bool) -> tuple:
    """(stills [{from, to}], cuts) from one ffmpeg pass on a small copy of the picture."""
    vf = f"scale=480:-2,freezedetect=n=0.003:d={still_max}" + (",scdet=threshold=10" if want_cuts else "")
    p = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-i", str(mp4), "-map", "0:v:0", "-vf", vf, "-an",
                        "-f", "null", "-"], capture_output=True, text=True)
    if p.returncode != 0:
        raise QcError(f"ffmpeg could not read the picture: {p.stderr.strip()[-200:]}")
    starts = [float(x) for x in re.findall(r"freeze_start:\s*([\d.]+)", p.stderr)]
    durs = [float(x) for x in re.findall(r"freeze_duration:\s*([\d.]+)", p.stderr)]
    stills = [{"from": round(s, 2), "to": round(s + d, 2)} for s, d in zip(starts, durs)]
    if len(starts) > len(durs):                   # frozen up to the very end
        stills.append({"from": round(starts[-1], 2), "to": None})
    cuts = sorted({round(float(x), 3) for x in re.findall(r"lavfi\.scd\.time:\s*([\d.]+)", p.stderr)}) if want_cuts else []
    return stills, cuts


def style_slug(d: Path):
    t = d / "TREATMENT.md"
    if t.is_file():
        m = re.search(r"^\s*Style:\s*`?([\w-]+)`?", t.read_text(encoding="utf-8"), re.M | re.I)
        if m:
            return m.group(1)
    work = Path(os.environ.get("STUDIO_WORK", "/work"))
    try:
        return json.loads((work / ".input.json").read_text()).get("style")
    except (OSError, ValueError):
        return None


def still_limit(d: Path) -> float:
    slug = style_slug(d)
    if not slug:
        return STILL_MAX
    for p, key in ((STYLES_FILE, slug), (d.parents[1] / "my-styles" / slug / "qc.json", None)):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            v = (data.get(key) or {}).get("still_max") if key else data.get("still_max")
            if isinstance(v, (int, float)) and v > 0:
                return float(v)
        except (OSError, ValueError, AttributeError):
            continue
    return STILL_MAX


# ---------- text and fonts ----------
def film_texts(d: Path, lib) -> tuple:
    """(texts, on_screen_checked): window.TEXTS when the film has a page, plus the .srt."""
    texts, checked = [], False
    if (d / "index.html").is_file() and lib and Path(lib, "core/render/page.mjs").is_file() and shutil.which("node"):
        p = subprocess.run(["node", str(Path(__file__).resolve().parent / "texts.mjs"), str(d), str(lib)],
                           capture_output=True, text=True, timeout=300)
        try:
            got = json.loads(p.stdout.strip().splitlines()[-1]).get("texts")
        except (ValueError, IndexError):
            got = None
        if got is not None:
            texts += got
            checked = True
    for srt in d.glob("*.srt"):
        for ln in srt.read_text(encoding="utf-8", errors="replace").splitlines():
            if ln.strip() and not ln.strip().isdigit() and "-->" not in ln:
                texts.append(ln.strip())
    return texts, checked


def charset_ranges(spec: str) -> set:
    out = set()
    for part in spec.split():
        a, _, b = part.partition("-")
        try:
            lo, hi = int(a, 16), int(b or a, 16)
        except ValueError:
            continue
        out.update(range(lo, hi + 1))
    return out


def font_env() -> dict:
    import tempfile
    return {**os.environ, "XDG_CACHE_HOME": os.environ.get("XDG_CACHE_HOME") or tempfile.gettempdir()}


def missing_glyphs(d: Path, texts: list) -> tuple:
    """([{char, codepoint, text}], fonts_checked)."""
    chars = {}
    for t in texts:
        for ch in t:
            if ch.isspace() or ord(ch) < 0x20 or 0x7f <= ord(ch) < 0xa0 or ord(ch) in (0x200b, 0x200c, 0x200d, 0xfeff):
                continue
            chars.setdefault(ch, t)
    if not chars:
        return [], True
    if not shutil.which("fc-list"):
        return [], False
    have = set()
    if shutil.which("fc-scan"):
        for f in (p for p in d.rglob("*") if p.suffix.lower() in FONT_EXT):
            p = subprocess.run(["fc-scan", "--format", "%{charset}\n", str(f)], capture_output=True, text=True, env=font_env())
            for line in p.stdout.splitlines():
                have |= charset_ranges(line)
    missing = []
    for ch, t in chars.items():
        if ord(ch) in have:
            continue
        if unicodedata.category(ch) in ("Cn", "Co", "Cs") or ch == "\ufffd":
            # unassigned, private use, broken text: no system font draws these as text (GNU Unifont, which the job
            # image has, "covers" them with a box showing the code), so only a font shipped with the film counts
            missing.append({"char": ch, "codepoint": f"U+{ord(ch):04X}", "text": t[:40]})
            continue
        p = subprocess.run(["fc-list", f":charset={ord(ch):x}", "file"], capture_output=True, text=True, env=font_env())
        if not p.stdout.strip():
            missing.append({"char": ch, "codepoint": f"U+{ord(ch):04X}", "text": t[:40]})
    return missing, True


# ---------- all ----------
def measure(d: Path, lib=None) -> dict:
    d = Path(d)
    name = d.name
    mp4 = d / f"{name}.mp4"
    if not mp4.is_file():
        raise QcError(f"films/{name}/{name}.mp4 was not made")
    duration = probe_duration(mp4)
    nar = load_narration(d)
    limit = still_limit(d)
    stills, found_cuts = picture(mp4, limit, want_cuts=bool(nar) and not nar["cuts"])
    measures, problems = {}, []
    if nar:
        cuts = nar["cuts"] if nar["cuts"] else found_cuts
        m, p = narration_measures(nar, duration, cuts)
        measures.update(m)
        problems += p
        measures["cuts"] = [round(c, 2) for c in cuts]
        mismatch = voice_matches_script(d, nar)
        measures["voice_matches_script"] = mismatch is None if (d / "SCRIPT.md").is_file() else None
        if mismatch:
            problems.append(mismatch)
    measures["stills_bad"] = stills
    for s in stills:
        problems.append(f"the picture stands still from {s['from']:.1f} s to "
                        + (f"{s['to']:.1f} s" if s["to"] is not None else "the end") + f"; at most {limit:g} s")
    texts, on_screen = film_texts(d, lib)
    glyphs, fonts_ok = missing_glyphs(d, texts)
    measures["missing_glyphs"] = glyphs
    measures["texts_checked"] = on_screen
    measures["fonts_checked"] = fonts_ok
    for g in glyphs:
        problems.append(f"{g['codepoint']} has no font and shows as a box (in \"{g['text']}\")")
    return {"pass": not problems, "narration": bool(nar), "duration": round(duration, 2), "measures": measures,
            "problems": problems}
