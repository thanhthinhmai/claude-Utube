"""A tiny sound library for the 037 tests, made at test time (no audio file is kept in git).

UCS-style names like Sonniss uses, a few files with bext / LIST INFO / iXML metadata, one broken file.
Standard library only: the signals are short noise bursts and tones."""
import math
import random
import struct
from pathlib import Path

RATE = 22050


def _pcm(kind: str, secs: float, seed: int) -> bytes:
    rnd = random.Random(seed)
    n = int(secs * RATE)
    out = bytearray()
    for i in range(n):
        t = i / RATE
        env = math.exp(-t * (18 if kind in ("hit", "glass", "pop") else 3))
        if kind == "tone":
            v = math.sin(2 * math.pi * 660 * t) * env
        elif kind == "whoosh":
            v = rnd.uniform(-1, 1) * math.sin(math.pi * t / secs)
        elif kind == "bubbles":
            v = math.sin(2 * math.pi * (300 + 200 * math.sin(40 * t)) * t) * (0.5 + 0.5 * math.sin(25 * t)) * 0.5
        else:
            v = rnd.uniform(-1, 1) * env
        out += struct.pack("<h", int(max(-1, min(1, v * 0.8)) * 32767))
    return bytes(out)


def _chunk(cid: bytes, data: bytes) -> bytes:
    pad = b"\0" if len(data) % 2 else b""
    return cid + struct.pack("<I", len(data)) + data + pad


def wav(path: Path, kind: str, secs: float, seed: int = 1, bext: str = None, info: dict = None, ixml: str = None) -> Path:
    data = _pcm(kind, secs, seed)
    fmt = struct.pack("<HHIIHH", 1, 1, RATE, RATE * 2, 2, 16)
    body = b"WAVE" + _chunk(b"fmt ", fmt)
    if bext is not None:
        b = bext.encode("latin-1")[:256].ljust(256, b"\0") + b"\0" * (602 - 256)
        body += _chunk(b"bext", b)
    if info:
        sub = b"".join(_chunk(k.encode(), v.encode("latin-1") + b"\0") for k, v in info.items())
        body += _chunk(b"LIST", b"INFO" + sub)
    if ixml is not None:
        body += _chunk(b"iXML", ixml.encode("utf-8"))
    body += _chunk(b"data", data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)
    return path


FILES = [
    ("GDC2024 Test Pack/GLASBrk_Window Shatter Large_TEST.wav", "glass", 0.8, {"bext": "Large window pane shatters, glass shards fall"}),
    ("GDC2024 Test Pack/GLASBrk_Bottle Smash_TEST.wav", "glass", 0.5, {}),
    ("GDC2024 Test Pack/WHSH_Fast Pass By_TEST.wav", "whoosh", 0.6, {"info": {"INAM": "Fast whoosh pass by", "IKEY": "swish; air; transition"}}),
    ("GDC2024 Test Pack/CRTNPop_Cork Pop Cartoon_TEST.wav", "pop", 0.3, {}),
    ("GDC2024 Test Pack/FOLYFoot_Sneaker Step Gym Floor_TEST.wav", "hit", 0.3, {}),
    ("GDC2024 Test Pack/BALLBnce_Rubber Ball Bounce Gym_TEST.wav", "hit", 0.4, {"ixml": "<BWFXML><USER><CATEGORY>BALLS</CATEGORY><SUBCATEGORY>BOUNCE</SUBCATEGORY><DESCRIPTION>Dodgeball bounce on gym floor</DESCRIPTION></USER></BWFXML>"}),
    ("GDC2026 Test Pack/WATRBubl_Aquarium Bubbles Loop_TEST.wav", "bubbles", 1.0, {"bext": "Office aquarium air pump bubbles, steady loop"}),
    ("GDC2026 Test Pack/CRWDCheer_Small Crowd Cheer_TEST.wav", "noise", 1.0, {}),
    ("GDC2026 Test Pack/PAPRScrbl_Pencil Scribble Paper_TEST.wav", "noise", 0.7, {}),
    ("GDC2026 Test Pack/UIClick_Soft Button Click_TEST.wav", "hit", 0.15, {}),
    ("GDC2026 Test Pack/BELLHand_Wrist Watch Ding_TEST.wav", "tone", 0.6, {}),
]
BROKEN = "GDC2026 Test Pack/IMPCMetl_Broken File_TEST.wav"


def make(root: Path) -> Path:
    """Write the test library under root; returns root. 11 good files + 1 broken one."""
    for i, (rel, kind, secs, meta) in enumerate(FILES):
        wav(root / rel, kind, secs, seed=i + 1, bext=meta.get("bext"), info=meta.get("info"), ixml=meta.get("ixml"))
    (root / BROKEN).write_bytes(b"RIFF\x10\0\0\0WAVEjunk")
    (root / "GDC2026 Test Pack" / "readme.txt").write_text("not a sound")
    return root
