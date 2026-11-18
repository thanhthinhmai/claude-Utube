"""Original score from the library's instruments (specs/023 FR-008, clarification 2026-11-14; TEMPLATE.md §14).

compose(beats, dur, template, seed) → (N, 2) float32 at 48 kHz: a continuous bed at the style's tempo
(template.json → sound.tempo), whose colour and density follow the film's beats: bright and driving for hook,
benefit and scale; thin and minor for the cost; tense and pulsing for the crisis; warm for the ending and the card.
Instruments: the Salamander piano (core/audio/sampler.py), plucked guitar (core/audio/pluck.py), kick and hat drawn
by core/audio/sfx.py. No outside music."""
import numpy as np
from core.audio import sampler as S, pluck as P, sfx as X

SR = X.SR
MAJOR = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]          # C G Am F
MINOR = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]          # Am F C G
TENSE = [[57, 60, 64], [57, 60, 64], [53, 57, 60], [52, 56, 59]]          # Am Am F E
MOOD = {"hook": (MAJOR, .8), "explain": (MAJOR, .55), "benefit": (MAJOR, 1.0), "scale": (MAJOR, 1.0),
        "cost": (MINOR, .3), "crisis": (TENSE, .9), "ending": (MAJOR, .5), "sting": (MAJOR, .65), "end-card": (MAJOR, .7)}


def beat_at(beats, t):
    for name, a, b in beats:
        if a <= t < b:
            return name
    return beats[-1][0] if beats else "benefit"


def compose(beats: list, dur: float, template: dict = None, seed: int = 1) -> np.ndarray:
    tr = ((template or {}).get("sound") or {}).get("tempo") or [114, 120]
    bpm = (tr[0] + tr[1]) / 2
    q = 60 / bpm
    S.seed(seed)                                   # same seed, same score: reset every random source used
    X._rng = np.random.default_rng(seed); P._rng = np.random.default_rng(seed + 1)
    n = int((dur + 2) * SR)
    out = np.zeros((n, 2))
    piano = []
    bar = 0
    t = 0.0
    while t < dur:
        name = beat_at(beats, t)
        prog, drive = MOOD.get(name, MOOD["benefit"])
        ch = prog[bar % 4]
        vel = .32 + .2 * drive
        piano.append((t, "piano", ch[0] - 24, 4 * q, .5, -.1))                   # bass root
        for m in ch:
            piano.append((t, "piano", m, 2 * q, vel, .1))
        if drive >= .6:
            for m in ch:
                piano.append((t + 2 * q, "piano", m, 2 * q, vel * .85, .1))
            piano.append((t + 2 * q, "piano", ch[0] - 24, 2 * q, .45, -.1))
        if drive >= .5:                                                           # plucked eighths
            for k in range(8):
                m = ch[[0, 1, 2, 1, 0, 2, 1, 2][k]] + 12
                y = P.pluck("acoustic_guitar", m, q * .9, vel=.35 + .15 * drive)
                X.add(out, y, t + k * q / 2, gain=.22, pan=(k % 2) * .4 - .2)
        for k in range(4):                                                        # drums
            if (drive >= .8 and k in (0, 2)) or (name == "crisis"):
                X.add(out, X.thump(.8), t + k * q, gain=.25 if name != "crisis" else .2)
            if drive >= .5:
                X.add(out, X.click(2.4, .4), t + k * q + q / 2, gain=.05, pan=.3)
        t += 4 * q
        bar += 1
    pr = S.render(piano, dur=dur + 2)
    m = min(len(pr), n)
    out[:m] += pr[:m]
    return out[:int(dur * SR)].astype(np.float32)
