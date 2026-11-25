"""The studio's voices from both providers (specs/036 research R4).

A voice id carries its provider: `kokoro:am_michael`, `el:21m00Tcm4TlvDq8ikWAM`. An id without a prefix is a Kokoro
voice (films made before 036)."""
import os
import zipfile
from pathlib import Path

_kokoro = None


def parse(voice_id: str):
    """(provider, name): ("kokoro", "am_michael") or ("elevenlabs", "<voice id>")."""
    v = (voice_id or "").strip()
    if v.startswith("el:"):
        return "elevenlabs", v[3:]
    if v.startswith("kokoro:"):
        return "kokoro", v[7:]
    return "kokoro", v


def kokoro_voices(root: Path = None) -> list:
    """The library's Kokoro voices (names inside voices-v1.0.bin, a zip of .npy files); [] when the model is missing."""
    global _kokoro
    if _kokoro is None or root is not None:
        base = Path(root or os.environ.get("STUDIO_ROOT") or Path(__file__).resolve().parents[2])
        f = base / "lib" / "lemo-opuscar" / "core" / "tts" / "voices-v1.0.bin"
        try:
            with zipfile.ZipFile(f) as z:
                names = sorted(n[:-4] for n in z.namelist() if n.endswith(".npy"))
        except (OSError, zipfile.BadZipFile):
            names = []
        if root is not None:
            return names
        _kokoro = names
    return _kokoro


# Kokoro names: <lang><gender>_<name>, e.g. af_heart = American female, bm_george = British male
_KLANG = {"a": "American", "b": "British", "e": "Spanish", "f": "French", "h": "Hindi", "i": "Italian",
          "j": "Japanese", "p": "Portuguese", "z": "Chinese"}


def kokoro_row(name: str) -> dict:
    g = {"f": "female", "m": "male"}.get(name[1:2]) if len(name) > 2 and name[2] == "_" else None
    return {"id": "kokoro:" + name, "provider": "kokoro", "name": name, "gender": g, "age": None,
            "accent": _KLANG.get(name[:1]) if g else None, "desc": None, "cloned": False, "preview": None}


def catalog(el_voices: list = None, kokoro: list = None) -> list:
    """Every voice the studio can use: Kokoro first, then the ElevenLabs account's (rows of eleven.public_voice)."""
    rows = [kokoro_row(n) for n in (kokoro if kokoro is not None else kokoro_voices())]
    return rows + list(el_voices or [])
