"""Tier 0: check the voice right after it is made (specs/020 US3; FR-001 – FR-004; contracts/cli.md `qc voice`).

Reads lines.json, voices/words.json (written by the library's asr_check with the studio's model, `voice asr`) and
voices/dur.json. A pause of ≥ 0.8 s inside a line counts only when ffmpeg silencedetect on the line's file agrees (a
recogniser gap over a word it missed is not a pause). Text agreement: word similarity ≥ 0.92, numbers said in words
and written in digits count as the same. Does not run speech recognition itself."""
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

from filmcheck import rhythm, tiers

PAUSE, TAIL_DIFF, SIMILAR = 0.8, 0.5, 0.92
SIL_DB, SIL_MIN = -40, 0.3        # a real silence inside the recogniser's gap confirms the pause (pet-swap l38: 0.43 s audible in a 0.80 s gap)


class VoiceError(Exception):
    """The voice cannot be checked (exit code 2)."""


NUM_WORDS = set("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
                "seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand million "
                "billion and point".split())


def _tokens(text: str, digits_as_number: bool) -> list:
    """Normalised words; a run of number words, or a written number, becomes one "#" (twenty-three thousand ↔ 23,000)."""
    out = []
    for raw in re.split(r"[\s\-–—]+", text.lower()):
        w = rhythm.norm(raw)
        if not w:
            continue
        is_num = (digits_as_number and re.fullmatch(r"\d+(st|nd|rd|th|s)?", w)) or (w in NUM_WORDS and w != "and")
        if w == "and" and out and out[-1] == "#":
            continue
        if is_num:
            if not (out and out[-1] == "#"):
                out.append("#")
            continue
        out.append(w)
    return out


def similar(want: str, got: str) -> float:
    """Word similarity of the script line and what the recogniser heard (asr_check's 0.92 rule, word by word)."""
    import difflib
    return difflib.SequenceMatcher(None, _tokens(want, True), _tokens(got, True), autojunk=False).ratio()


def silences(wav: Path) -> list:
    """[(start, end)] of silences ≥ 0.3 s in a voice file (ffmpeg silencedetect at −40 dB)."""
    p = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-i", str(wav), "-af",
                        f"silencedetect=n={SIL_DB}dB:d={SIL_MIN}", "-f", "null", "-"], capture_output=True, text=True)
    st = [float(x) for x in re.findall(r"silence_start:\s*([-\d.]+)", p.stderr)]
    en = [float(x) for x in re.findall(r"silence_end:\s*([-\d.]+)", p.stderr)]
    return [(max(0.0, s), e) for s, e in zip(st, en)]


def _issue(rule, ref, at, measure, limit, text="", fix=""):
    return {"tier": "voice", "ref": ref, "at": round(at, 2) if at is not None else None, "rule": rule, "severity": "block",
            "measure": measure, "limit": limit, "text": text, "fix": fix, "excepted": None}


def run(film_dir: Path, lib=None, lang="en") -> dict:
    t0 = time.time()
    d = Path(film_dir)
    try:
        rows = json.loads((d / "lines.json").read_text(encoding="utf-8"))
        words = json.loads((d / "voices" / "words.json").read_text(encoding="utf-8"))
        durs = json.loads((d / "voices" / "dur.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise VoiceError(f"lines.json, voices/words.json or voices/dur.json cannot be read: {e} "
                         "(run: sh bin/studio voice asr <film>)") from None
    have_ffmpeg = bool(shutil.which("ffmpeg"))
    issues, skipped, m = [], [], {"lines": 0, "pauses": []}
    for r in rows:
        if not isinstance(r, dict) or not r.get("id"):
            continue
        lid, text = r["id"], r.get("text", "")
        recorded = bool(r.get("recorded"))
        redo = "check the recording" if recorded else f"regenerate {lid}"
        m["lines"] += 1
        if lid not in words or not words[lid]:
            issues.append(_issue("asr_mismatch", lid, 0.0, "no words", "the line's text", fix=redo))
            continue
        length = float(durs.get(lid, 0)) or None
        ws = rhythm.clamp_words(words[lid], length)                                  # FR-004
        said = re.sub(r"\s+([,.!?;:%])", r"\1", " ".join(w for w, _, _ in ws))   # "23 ,000" → "23,000"
        sim = round(similar(text, said), 3)
        m["similarity_min"] = min(m.get("similarity_min", 1.0), sim)
        if sim < SIMILAR:
            issues.append(_issue("asr_mismatch", lid, 0.0, sim, SIMILAR, text=said[:40], fix=redo))
        if length is not None:
            diff = abs(float(words[lid][-1][2]) - length)
            if diff > TAIL_DIFF:
                issues.append(_issue("tail_mismatch", lid, length, round(diff, 2), TAIL_DIFF,
                                     fix=f"{redo} (the file and its last word disagree)"))
        gaps = [(a[2], b[1]) for a, b in zip(ws, ws[1:]) if b[1] - a[2] >= PAUSE - 1e-9]
        if gaps:
            wav = d / "voices" / f"{lid}.wav"
            sil = silences(wav) if have_ffmpeg and wav.is_file() else None
            if sil is None:
                skipped.append(f"{lid}: no audio check of its pauses (no ffmpeg or no {wav.name})")
            for a, b in gaps:
                if sil is not None and not any(min(b, e) - max(a, s) >= SIL_MIN - 0.02 for s, e in sil):
                    continue
                m["pauses"].append({"line": lid, "at": round(a, 2), "length": round(b - a, 2)})
                issues.append(_issue("pause_in_line", lid, a, round(b - a, 2), PAUSE,
                                     fix=redo + " (long pauses belong between paragraphs)"))
    res = tiers.result("voice", issues, m, skipped, time.time() - t0, tiers.fingerprint(d, "voice"))
    tiers.save_tier(d, "voice", res)
    return res
