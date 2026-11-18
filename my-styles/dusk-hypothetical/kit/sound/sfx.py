"""Sound effects on events (specs/023 FR-008, TEMPLATE.md §14), drawn by the library's core/audio/sfx.py.
place(events, n) → (n, 2) float array; events are {type, t, d?}: pop (a fact card or the closing card appears; speech
bubbles and still counters make no sound, studio rule chosen by the user on 2026-11-18), count (a counter rolls for
d s), streak (a light-streak swap), whoosh (a cut with a move), step (a footfall), hit (an impact)."""
import numpy as np
from core.audio import sfx as X


def place(events: list, n: int, seed: int = 5) -> np.ndarray:
    fx = np.zeros((n, 2))
    X._rng = np.random.default_rng(seed)           # same events, same sound
    for e in events:
        t, kind = float(e["t"]), e["type"]
        if kind == "pop":                       # a fact card or the closing card appears: soft (studio rule, 2026-11-18)
            X.add(fx, X.pop(.6), t, gain=.16); X.add(fx, X.ding(.3), t + .02, gain=.035)
        elif kind == "count":
            for k in range(int(float(e.get("d", 1.2)) / .08)):
                X.add(fx, X.click(1.6, .5), t + k * .08, gain=.08, pan=.1)
        elif kind == "streak":
            X.add(fx, X.whoosh(.35, .8), t - .12, gain=.28); X.add(fx, X.ding(.6), t + .05, gain=.1)
        elif kind == "whoosh":
            X.add(fx, X.whoosh(.3, .6), t - .1, gain=.18)
        elif kind == "step":
            X.add(fx, X.step(.6), t, gain=.15)
        elif kind == "hit":
            X.add(fx, X.thump(.9), t, gain=.35)
    return fx
