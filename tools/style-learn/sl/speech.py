"""Transcription (optional, faster-whisper) and speaking rate (research.md §8)."""
import re
import subprocess
from pathlib import Path

import numpy as np

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


def decode_16k(path: Path, span=None) -> np.ndarray:
    """Mono float32 samples at 16 kHz, decoded by ffmpeg (what Whisper expects)."""
    cmd = ["ffmpeg", "-v", "error", "-nostdin"]
    if span:
        cmd += ["-ss", f"{span[0]:.4f}", "-t", f"{span[1] - span[0]:.4f}"]
    r = subprocess.run(cmd + ["-i", str(path), "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True)
    if r.returncode != 0:
        raise StepError(f"ffmpeg không đọc được âm thanh: {r.stderr.decode(errors='replace').strip()[:200]}")
    return np.frombuffer(r.stdout, np.float32).copy()


ASR_FILE = Path(__file__).resolve().parents[2] / "asr.json"


def model_for(lang: str = None) -> str:
    """The studio's one recogniser model (tools/asr.json, specs/020 FR-002): per language, else the multilingual one."""
    import json
    try:
        cfg = json.loads(ASR_FILE.read_text(encoding="utf-8"))
        return cfg.get(lang) or cfg["*"] if lang else cfg["*"]
    except (OSError, ValueError, KeyError):
        return "small"


def transcribe(path: Path, meta: dict, segs: list, model: str = None, lang: str = None) -> dict:
    model = model or model_for(lang)
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise StepError("chưa cài faster-whisper. Chạy: sh bin/studio deps learn --extra")
    if not meta.get("has_audio"):
        return {"language": lang, "words": [], "note": "video không có tiếng"}
    m = WhisperModel(model, compute_type="int8")
    words, language = [], lang
    whole = is_whole(segs, meta["duration"])
    for a, b in segs:
        audio = decode_16k(path, None if whole else (a, b))
        if audio.size == 0:
            continue
        # Pass samples, not a file path: faster-whisper then never opens the file with PyAV,
        # whose 19.x release breaks it (TypeError: metadata_errors)
        segments, info = m.transcribe(audio, language=lang, word_timestamps=True)
        language = language or info.language
        for s in segments:
            for w in s.words or []:
                words.append({"word": w.word.strip(), "start": round(a + w.start, 3), "end": round(a + w.end, 3)})
    return {"language": language, "words": words}
