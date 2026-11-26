# Animatic of an After Effects film (specs/035)

Between Voice and Sound, an AE film stops at the **Animatic**: a quarter-size draft with the real voice, a timeline of
shots and lines, the silence of the narration (the film check's number, limit 20%), per-shot fit suggestions, and pinned
notes. The final render waits until the animatic is approved.

## One source for shot lengths: `timing.json`

- `films/<film>/timing.json` holds the frames of each shot (`{version 1, fps, frames {S1: 75, …}, history, origin}`).
  `tools/filmcheck/timing.py` reads and writes it under `timing.lock`; a change moves `narration.json`'s line starts
  with their shots.
- The bundle carries it as `data/timing.json`. Film code reads a shot length with `CU.shotFrames("S2")`, which is
  `undefined` when the film has no timing.json yet:

  ```js
  CU.shot2 = function () { var n = CU.shotFrames("S2") || 117; var c = CU.comp("S2", n / CU.FPS); … };
  ```

- A new AE film never keeps its own list of lengths in `mix.py` or the jsx: read `timing.json` (Python) or
  `CU.shotFrames` (jsx).
- Each build writes `keys_<proj>.json` (every keyframed property per shot, `CU.keyScan`), so a suggestion that cuts a
  shot can say which motions it drops or squeezes.

## Moving an old film

The first whole build of a film without `timing.json` (`ae build`, `ae draft`, `ae render`) writes it from the real
shot lengths that build measured; `origin` is that state. Then make the film read it:

1. jsx: after the film's own list, overwrite it from `CU.shotFrames`. For `films/ae-sleepless-test/ae/shots.jsx`:

   ```js
   CU.FR = [75, 117, 83, 48, 78, 120, 138, 108, 90];   // frames per shot, 30 fps, before the film had timing.json
   (function () { var i, n; for (i = 0; i < CU.FR.length; i++) { n = CU.shotFrames("S" + (i + 1)); if (n) { CU.FR[i] = n; } } })();
   ```

2. Python (a film's own `mix.py`): read `FRAMES` from `timing.json` when it is there. For
   `films/ae-sleepless-test/mix.py.orig`:

   ```python
   FRAMES = [75, 117, 83, 48, 78, 120, 138, 108, 90]          # before the film had timing.json (specs/035)
   try:
       import json as _json
       _t = _json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "timing.json")))["frames"]
       FRAMES = [_t[f"S{i + 1}"] for i in range(len(FRAMES))]
   except (OSError, ValueError, KeyError):
       pass
   ```

The files before this change are kept next to them as `*.pre035`.
