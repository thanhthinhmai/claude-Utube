"""Mix of the Sketch Explainer demo: narration + an original Salamander piano bed about 11 dB under the voice
(style §7) + light effects for actions on screen. Run from the library root:
  .venv/bin/python <film>/mix.py   → <film>/out/mix.wav"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.environ.get('LIB') or os.path.abspath(os.path.join(HERE, '..', '..', 'lib', 'lemo-opuscar'))
sys.path.insert(0, LIB)
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
from core.audio import sampler as S  # noqa: E402
from core.audio.sfx import SR, add, limit, whoosh, click, ding, compress  # noqa: E402

plan = json.load(open(f'{HERE}/plan.json'))
DUR = plan['dur']
N = int(DUR * SR) + SR
voice = np.zeros((N, 2), np.float32)
for l in plan['lines']:
    a, sr = sf.read(f'{HERE}/voices/{l["id"]}.wav', dtype='float32')
    if a.ndim > 1:
        a = a.mean(1)
    if sr != SR:
        a = np.interp(np.arange(int(len(a) * SR / sr)) * sr / SR, np.arange(len(a)), a).astype(np.float32)
    add(voice, a, l['at'], 1.0, 0.0)

# a light, curious bed in F major: two bars per chord, soft arpeggio over a low root
PROG = [('F2', ['F3', 'A3', 'C4']), ('C3', ['E3', 'G3', 'C4']), ('D2', ['D3', 'F3', 'A3']), ('A#1', ['A#2', 'D3', 'F3'])]
ev, t, i, bar = [], 0.0, 0, 2.2
while t < DUR - 1:
    root, notes = PROG[i % len(PROG)]
    ev.append((t, 'piano', root, bar * 1.5, .34, -.15))
    for k, n in enumerate(notes * 2):
        ev.append((t + k * bar / 6, 'piano', n, bar * .7, .28 if k % 3 else .34, .2))
    t += bar; i += 1
ev += [(DUR - 2.6, 'piano', 'F2', 3, .32, 0), (DUR - 2.6, 'piano', 'C4', 3, .26, .2), (DUR - 2.6, 'piano', 'A4', 3, .22, .3)]
music = S.room(S.render(ev, dur=DUR + 1), size=.5, mix=.2)
music = music[:N] if len(music) >= N else np.pad(music, ((0, N - len(music)), (0, 0)))
env = np.convolve(np.abs(voice).mean(1), np.ones(int(.05 * SR)) / int(.05 * SR), 'same')
duck = 1 - .5 * np.clip(env / (env.max() * .25 + 1e-9), 0, 1)
music = music * duck[:, None] * .2

# effects: a soft whoosh on cuts, a till ding on the payment, pops as board rows and slices appear
fx = np.zeros((N, 2), np.float32)
shots = plan['shots']
for s in shots[1:]:
    add(fx, whoosh(.25, .5), max(0, s['t0'] - .1), .08, 0)
add(fx, ding(.8), shots[0]['t0'] + .5, .18, .2)
for k in range(4):
    add(fx, click(1.4, .35), shots[1]['t0'] + .3 + .3 + k * .45, .1, .2)
for idx, n in ((5, 2), (6, 3)):
    for k in range(n):
        add(fx, click(1.1, .4), shots[idx]['t0'] + .2 + k * .5, .1, -.2)
add(fx, ding(1.0), shots[8]['t0'] + .3, .14, .1)

mix = voice + music + fx
fade = int(1.0 * SR); mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
mix = np.stack([compress(mix[:, ch], thr=.3, ratio=2.0) for ch in (0, 1)], 1)   # light: the style keeps a loudness range of 2.8–4.7 LU
mix = limit(mix * 2.3, .66)
os.makedirs(f'{HERE}/out', exist_ok=True)
sf.write(f'{HERE}/out/mix.wav', mix[:int(DUR * SR)], SR)
print('mix', round(DUR, 2), 's')
