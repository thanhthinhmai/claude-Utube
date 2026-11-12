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

from filmcheck import rhythm
from filmcheck.rhythm import SILENCE_MAX, LONG_PAUSE, CUT_AFTER, KEY_SHOT, TAIL_MAX, EPS  # noqa: F401 (010 names)

STILL_MAX = 6.0
FONT_EXT = (".ttf", ".otf", ".woff", ".woff2", ".ttc")


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
        length = float(durs[lid]) if durs and lid in durs else None
        ws = [(w, float(ln["at"]) + s, float(ln["at"]) + e) for w, s, e in rhythm.clamp_words(words[lid], length)]   # FR-004
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


def line_texts(d: Path, nar: dict) -> dict:
    """{line id: the line's script text} from the voice lines file, or {} (specs/020 FR-003)."""
    if not nar.get("lines_file"):
        return {}
    try:
        rows = json.loads((d / nar["lines_file"]).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {r.get("id"): r.get("text", "") for r in rows if isinstance(r, dict) and r.get("text")}


def sentences(lines: list, texts=None) -> list:
    """(start, end, para) of every sentence; the script's sentences when texts are given (rhythm.sentences)."""
    return [(x["start"], x["end"], x["para"]) for x in rhythm.sentences(lines, texts)]


def shots_from_cuts(cuts: list, duration: float) -> list:
    bounds = sorted({0.0, duration, *[c for c in cuts if EPS < c < duration - EPS]})
    return [{"id": f"S{i + 1}", "t0": a, "t1": b} for i, (a, b) in enumerate(zip(bounds, bounds[1:]))]


def narration_measures(nar: dict, duration: float, cuts: list, texts=None, shots=None, cues=None, style=None) -> tuple:
    """(measures, problems, issues): the shared rhythm rules (rhythm.measure, specs/020 FR-010) on a finished film."""
    words = sorted((s, e, ln["para"]) for ln in nar["lines"] for (_, s, e) in ln["words"])
    last = max(e for _, e, _ in words)
    if last > duration + EPS:
        raise QcError(f"narration.json does not match the film: the last word ends at {last:.2f} s, after the film ({duration:.2f} s)")
    sents = rhythm.sentences(nar["lines"], texts)
    m, issues = rhythm.measure(sents, words, duration, shots=shots or shots_from_cuts(cuts, duration), cues=cues, style=style)
    for i in issues:
        i["tier"] = "final"
    return m, [rhythm.message(i) for i in issues], issues


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
        txt = t.read_text(encoding="utf-8")
        m = re.search(r"^\s*Style:\s*`?([\w-]+)`?", txt, re.M | re.I)
        if m:
            return m.group(1)
    try:                                         # the channel snapshot (specs/012) names the film's style
        st = json.loads((d / "channel.json").read_text(encoding="utf-8")).get("film", {}).get("style")
        if st:
            return st
    except (OSError, ValueError, AttributeError):
        pass
    if t.is_file():
        m = re.search(r"\bstyle\s+`([\w-]+)`", txt, re.I)
        if m:
            return m.group(1)
    work = Path(os.environ.get("STUDIO_WORK", "/work"))
    try:
        return json.loads((work / ".input.json").read_text()).get("style")
    except (OSError, ValueError):
        return None


def still_limit(d: Path) -> float:
    from filmcheck import stylerefs
    v = stylerefs.load(d).get("still_max")
    return float(v) if isinstance(v, (int, float)) and v > 0 else STILL_MAX


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
        from filmcheck import stylerefs
        m, p, _ = narration_measures(nar, duration, cuts, texts=line_texts(d, nar), style=stylerefs.load(d))
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
    from filmcheck import channels               # the channel's voice and speed (specs/012 FR-006a)
    snap = channels.snapshot(d)
    if snap and nar and snap["rules"].get("voice") and not snap["rules"].get("voice_override"):
        want_v, want_s = snap["rules"]["voice"], float(snap["rules"].get("speed") or 1.0)
        try:
            rows = json.loads((d / nar["lines_file"]).read_text(encoding="utf-8")) if nar.get("lines_file") else []
        except (OSError, ValueError):
            rows = []
        bad = [r.get("id") for r in rows if isinstance(r, dict) and ((r.get("voice") or channels.DEFAULT_VOICE) != want_v
                                                                     or abs(float(r.get("speed") or 1.0) - want_s) > 0.01)]
        measures["channel_voice_bad"] = bad
        if bad:
            problems.append(f"channel_voice: lines {', '.join(map(str, bad[:5]))} do not use the channel's voice "
                            f"{want_v} at speed {want_s:g}")
    texts, on_screen = film_texts(d, lib)
    glyphs, fonts_ok = missing_glyphs(d, texts)
    measures["missing_glyphs"] = glyphs
    measures["texts_checked"] = on_screen
    measures["fonts_checked"] = fonts_ok
    # specs/019: how the page was rendered for the on-screen text pass (set by `sh bin/studio qc`)
    measures["render"] = {"mode": os.environ.get("STUDIO_RENDER_MODE") or "software",
                          "renderer": os.environ.get("STUDIO_RENDER_RENDERER") or None}
    for g in glyphs:
        problems.append(f"{g['codepoint']} has no font and shows as a box (in \"{g['text']}\")")
    return {"pass": not problems, "narration": bool(nar), "duration": round(duration, 2), "measures": measures,
            "problems": problems}
