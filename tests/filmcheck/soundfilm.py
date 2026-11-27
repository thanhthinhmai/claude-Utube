"""A small AE film for the 037 tests (T018): 3 shots at 30 fps, timing.json and animatic/keys.json in the format of
specs/035, two voice lines with words, out/music.wav. Standard library only (voices and music are tones)."""
import json
import math
import struct
import wave
from pathlib import Path

FPS = 30
FRAMES = {"S1": 60, "S2": 90, "S3": 60}            # 2 s, 3 s, 2 s
KEYS = {"S1": [{"layer": "Hero", "prop": "Position", "t0": 0.5, "t1": 1.0}],
        "S2": [{"layer": "Window", "prop": "Scale", "t0": 1.2, "t1": 1.5},
               {"layer": "Hand R", "prop": "Rotation", "t0": 2.4, "t1": 2.8}],
        "S3": [{"layer": "Ball", "prop": "Position", "t0": 0.3, "t1": 0.6}]}
LINES = [{"id": "l01", "para": "P01", "at": 0.3}, {"id": "l02", "para": "P02", "at": 2.4}]
WORDS = {"l01": [["The", -0.6, 0.1], ["window", 0.1, 0.5], ["breaks.", 0.5, 0.9]],
         "l02": [["People", 0.0, 0.3], ["cheer.", 0.3, 0.7]]}


def tone(path: Path, secs: float, hz: float, rate: int = 24000, amp: float = 0.3, channels: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        fr = bytearray()
        for i in range(int(secs * rate)):
            v = int(amp * 32767 * math.sin(2 * math.pi * hz * i / rate))
            fr += struct.pack("<h", v) * channels
        w.writeframes(bytes(fr))


def make(d: Path, timing: bool = True, keys: bool = True, music: bool = True) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    (d / "film.json").write_text(json.dumps({"engine": "ae", "fps": FPS, "size": [1920, 1080],
                                             "shots": list(FRAMES), "ae_files": ["shots.jsx"]}))
    if timing:
        (d / "timing.json").write_text(json.dumps({"version": 1, "fps": FPS, "frames": FRAMES, "history": [],
                                                   "origin": {"frames": FRAMES, "at": "2026-11-25T00:00:00Z"}}))
    else:
        t, rows = 0.0, []
        for s, n in FRAMES.items():
            rows.append([round(t, 4), round(t + n / FPS, 4), "", s])
            t += n / FPS
        (d / "out").mkdir(exist_ok=True)
        (d / "out" / "render-shots.json").write_text(json.dumps({"version": 1, "fps": FPS, "shots": rows}))
    if keys:
        (d / "animatic").mkdir(exist_ok=True)
        (d / "animatic" / "keys.json").write_text(json.dumps(KEYS))
    (d / "narration.json").write_text(json.dumps({"words_file": "voices/words.json", "lines": LINES}))
    (d / "voices").mkdir(exist_ok=True)
    (d / "voices" / "words.json").write_text(json.dumps(WORDS))
    tone(d / "voices" / "l01.wav", 0.9, 220)
    tone(d / "voices" / "l02.wav", 0.7, 260)
    if music:
        tone(d / "out" / "music.wav", 7.0, 110, rate=48000, amp=0.1, channels=2)
    return d


def set_frames(d: Path, frames: dict) -> None:
    t = json.loads((d / "timing.json").read_text())
    t["frames"] = frames
    (d / "timing.json").write_text(json.dumps(t))
