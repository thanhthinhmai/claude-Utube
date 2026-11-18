"""Mix of a kit film (specs/023 FR-008, FR-017; TEMPLATE.md §14): voice, original score, effects → out/mix.wav.

Run with the library's Python from the library root:  cd $LIB && .venv/bin/python <film>/kit/sound/mix.py <film>
Reads <film>/narration.json (line starts), voices/<id>.wav, events.json ({dur, ev: [{type, t, …}]}), optional
beats.json ([[beat, t0, t1]], the film's own beat marks) and kit/template.json. The score ducks under the voice so
that in the pauses it sits template.json → sound.music_under_voice_db below the voice; the whole mix goes to −14 LUFS."""
import json
import os
import subprocess
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

sys.path.insert(0, os.getcwd())
from core.audio import sfx as X  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import score  # noqa: E402
import sfx as fxmod  # noqa: E402

SR = X.SR


def load(path):
    sr, x = wavfile.read(path)
    x = x.astype(np.float64)
    if x.ndim > 1:
        x = x.mean(1)
    if np.abs(x).max() > 1.5:
        x /= 32768.0
    return resample_poly(x, SR, sr) if sr != SR else x


def rms(x):
    return float(np.sqrt(np.mean(x ** 2))) if len(x) else 0.0


def mix(film: str) -> str:
    j = lambda f: json.load(open(os.path.join(film, f)))
    ev = j("events.json")
    dur = float(ev["dur"])
    n = int(dur * SR)
    tpl = json.load(open(os.path.join(film, "kit", "template.json"))) if os.path.exists(os.path.join(film, "kit", "template.json")) else {}
    beats = j("beats.json") if os.path.exists(os.path.join(film, "beats.json")) else [["benefit", 0, dur]]
    voice = np.zeros((n, 2))
    for e in ev["ev"]:
        if e["type"] == "voice":
            X.add(voice, load(os.path.join(film, "voices", e["id"] + ".wav")), e["t"], gain=1.0)
    music = np.zeros((n, 2))
    sc = score.compose(beats, dur, tpl, seed=7)
    music[:len(sc)] += sc[:n]
    fx = fxmod.place([e for e in ev["ev"] if e["type"] != "voice"], n)
    # duck the score under the voice (−9 dB while speaking, 80 ms smoothing)
    env = np.abs(voice).mean(1)
    k = int(.08 * SR)
    sm = np.convolve(env, np.ones(k) / k, "same")
    speaking = sm > .02 * (sm.max() + 1e-9)
    duck = np.where(speaking, 10 ** (-9 / 20), 1.0)
    duck = np.convolve(duck, np.ones(k) / k, "same")
    music *= duck[:, None]
    # level: the score in the pauses sits at the style's level under the voice
    target = np.mean(((tpl.get("sound") or {}).get("music_under_voice_db")) or [-8.5, -3.3])
    v, mgap = rms(voice[speaking]), rms(music[~speaking])
    if v > 0 and mgap > 0:
        music *= (v * 10 ** (target / 20)) / mgap
    out = voice + music + fx
    out = np.stack([X.limit(out[:, c], .95) for c in (0, 1)], 1)
    fade = int(.4 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    os.makedirs(os.path.join(film, "out"), exist_ok=True)
    raw = os.path.join(film, "out", "mix-raw.wav")
    wavfile.write(raw, SR, (out * 32767).astype(np.int16))
    dst = os.path.join(film, "out", "mix.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", "loudnorm=I=-14:TP=-1:LRA=4:linear=true", "-ar", str(SR), dst], check=True)
    os.remove(raw)
    return dst


if __name__ == "__main__":
    print(mix(os.path.abspath(sys.argv[1])))
