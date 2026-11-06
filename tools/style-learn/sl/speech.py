"""Transcription (optional, faster-whisper) and speaking rate (research.md §8)."""
import re
import subprocess
import tempfile
from pathlib import Path

from .probe import is_whole
from .refset import StepError

PAUSE = 0.25
CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿]")
NO_SPACE_LANGS = {"zh", "ja", "yue"}


def rate(words: list, language: str = None):
    """Words (or characters for Chinese/Japanese) per second of speech, not counting pauses > 0.25 s."""
    if not words:
        return None
    text = "".join(w["word"] for w in words)
    cjk = len(CJK.findall(text))
    by_char = (language in NO_SPACE_LANGS) or (cjk > 0.5 * len(re.sub(r"\s", "", text) or "x"))
    count = cjk if by_char else len(words)
    span = words[-1]["end"] - words[0]["start"]
    pause = sum(g for g in (words[i + 1]["start"] - words[i]["end"] for i in range(len(words) - 1)) if g > PAUSE)
    speak = max(span - pause, 1e-6)
    return {"words": count, "rate": round(count / speak, 3), "unit": "chars/s" if by_char else "words/s",
            "pause_total": round(pause, 3)}


def transcribe(path: Path, meta: dict, segs: list, model: str = "small", lang: str = None) -> dict:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise StepError("chưa cài faster-whisper. Chạy: sh bin/studio deps learn --extra")
    m = WhisperModel(model, compute_type="int8")
    words, language = [], lang
    whole = is_whole(segs, meta["duration"])
    with tempfile.TemporaryDirectory() as td:
        for a, b in segs:
            wav = Path(td) / "a.wav"
            cmd = ["ffmpeg", "-v", "error", "-y", "-nostdin"]
            if not whole:
                cmd += ["-ss", f"{a:.4f}", "-t", f"{b - a:.4f}"]
            subprocess.run(cmd + ["-i", str(path), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
            segments, info = m.transcribe(str(wav), language=lang, word_timestamps=True)
            language = language or info.language
            for s in segments:
                for w in s.words or []:
                    words.append({"word": w.word.strip(), "start": round(a + w.start, 3), "end": round(a + w.end, 3)})
    return {"language": language, "words": words}
