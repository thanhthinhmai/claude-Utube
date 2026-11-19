"""Voice + synthesized bed + foley → out/mix.wav (48 kHz stereo). Run with the library's Python from the library root:
cd $LIB && .venv/bin/python <film>/mix.py"""
import json, os, sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly
LIB = os.environ.get('LIB') or os.getcwd()
sys.path.insert(0, LIB)
from core.audio import sfx as X
SR = X.SR
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get('OUT') or os.path.join(HERE, 'out')
VOICES = os.environ.get('VOICES') or os.path.join(HERE, 'voices')
ev = json.load(open(os.path.join(HERE, 'events.json')))
DUR = ev['dur']; EV = ev['ev']
N = int((DUR + .5) * SR)
bed = np.zeros((N, 2)); voice = np.zeros((N, 2)); fx = np.zeros((N, 2))
hz = lambda m: 440 * 2 ** ((m - 69) / 12)

def load(path):
    sr, x = wavfile.read(path); x = x.astype(np.float64)
    if x.ndim > 1: x = x.mean(1)
    if np.abs(x).max() > 1.5: x /= 32768.0
    return resample_poly(x, SR, sr) if sr != SR else x

for e in EV:
    if e['type'] == 'voice':
        X.add(voice, load(os.path.join(VOICES, e['id'] + '.wav')), e['t'], gain=1.0)

# bed: soft pads at 96 BPM, Em – C – G – D, one chord per bar (2.5 s), a muted pluck on eighths, continuous (no silence)
BAR = 2.5
CH = [[52, 55, 59, 64], [48, 52, 55, 60], [55, 59, 62, 67], [50, 54, 57, 62]]
t_bar = X.t_(BAR + .6)
for b in range(int(DUR / BAR) + 1):
    notes = CH[b % 4]
    pad = np.zeros_like(t_bar)
    for m in notes:
        for det in (-.1, .1):
            f = hz(m) * 2 ** (det / 12)
            pad += np.sin(2 * np.pi * f * t_bar) + .25 * np.sin(4 * np.pi * f * t_bar)
    env = np.minimum(1, t_bar / .4) * np.minimum(1, (BAR + .6 - t_bar) / .6)
    X.add(bed, X.lp(pad * env, 1300) * .05, b * BAR, pan=-.2 if b % 2 else .2)
    for k in range(8):
        m = notes[[0, 2, 1, 3, 2, 1, 3, 2][k]] + 12
        tt = X.t_(.45); pl = np.sin(2 * np.pi * hz(m) * tt) * np.exp(-tt / .1)
        X.add(bed, pl * .045, b * BAR + k * BAR / 8, pan=(k % 2) * .4 - .2)
    X.add(bed, X.thump(.35, 55), b * BAR, gain=.25)

for e in EV:
    t = e['t']
    if e['type'] == 'alarm':                      # two-tone beeps
        for k in range(int(e['d'] / .25)):
            tt = X.t_(.12); X.add(fx, np.sin(2 * np.pi * (1760 if k % 2 else 1320) * tt) * np.minimum(1, (.12 - tt) / .02) * .5, t + k * .25, gain=.18)
    if e['type'] == 'float':                      # a slow rising tone under the long hop
        tt = X.t_(e['d']); f = 300 + 260 * tt / e['d']
        tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / e['d'])
        X.add(fx, X.lp(tone, 1500) * .5, t, gain=.12)
    if e['type'] == 'land':
        X.add(fx, X.thump(.8, 65), t, gain=.5); X.add(fx, X.step(.6), t, gain=.3)
    if e['type'] == 'jump':
        X.add(fx, X.whoosh(.35, .6), t - .1, gain=.25)
    if e['type'] == 'count':
        for k in range(int(e['d'] / .1)): X.add(fx, X.click(1.6, .5), t + k * .1, gain=.1, pan=.1)
    if e['type'] == 'pop':
        X.add(fx, X.pop(.7), t, gain=.35); X.add(fx, X.ding(.4), t + .02, gain=.12)
    if e['type'] == 'pour':                       # a slow filtered trickle
        n = X.bp(X.noise(e['d']), 500, 2200) * np.minimum(1, X.t_(e['d']) / .2) * np.minimum(1, (e['d'] - X.t_(e['d'])) / .3)
        X.add(fx, n * .25, t, gain=.5, pan=.2)
    if e['type'] == 'cut':
        X.add(fx, X.whoosh(.18, .25), t - .09, gain=.05)

# the bed ducks under the voice
venv = np.abs(voice).mean(1)
k = int(.08 * SR); sm = np.convolve(venv, np.ones(k) / k, 'same')
duck = 1 - .7 * np.clip(sm / (sm.max() * .25 + 1e-9), 0, 1)
bed *= duck[:, None]
# the bed swells on the closing pull-out (S08) and sits low under the opening
T = np.arange(N) / SR
bed *= (0.45 + 0.55 * np.clip((T - 4.7) / 2, 0, 1) + 2.0 * np.clip((T - 20.4) / 1.5, 0, 1))[:, None]

mix = voice * .95 + bed + fx
mix = np.stack([X.compress(mix[:, c], thr=.5, ratio=1.6) for c in (0, 1)], 1)
mix = np.stack([X.limit(mix[:, c], .9) for c in (0, 1)], 1)
fade = int(.8 * SR); mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
os.makedirs(OUT, exist_ok=True)
wavfile.write(os.path.join(OUT, 'mix.wav'), SR, (mix * 32767).astype(np.int16))
print('mix.wav', round(len(mix) / SR, 2), 's')
