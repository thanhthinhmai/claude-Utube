# Sketch Explainer — our demo

One example among many. Don't reuse its story, arc, shots, props or timings.

Demo: *The Five-Dollar Latte* (48.9 s) · `test.mp4` (not in git; rebuilt by `demo/build.sh`) · source in [`demo/`](demo/)

## Story & structure

A latte sells for five dollars and its cup, coffee and milk cost about one dollar twenty: where does the rest go? Hook with a number in the first second, the question at 6.5 s, then one café's month split slice by slice on a chalkboard, then the answer (about nineteen percent left, most cafés aim for ten to fifteen) and a closing turn to volume. Every number comes from one cited source (`demo/SOURCES.md`). The film shows the kit's native moves: a sign held by a white-faced customer, a board that builds while the guide points, a speech-bubble exchange, an over-the-shoulder shot, a meeting table, a queue walking in.

## Shots

| # | Time | Set | Size | People and graphics |
|---|---|---|---|---|
| S001 | 0.0–2.3 | custom:cafe (sky, skyline, grass, stall) | medium | white-faced customer holds the "$5" sign; barista (worker); till ding |
| S002 | 2.3–6.5 | whiteboard-room | medium | the guide points; list "the cup" builds row by row, total highlighted |
| S003 | 6.5–10.7 | custom:cafe | close | the guide shocked, bubble "$4?!"; the barista answers "Nope." |
| S004 | 10.7–12.5 | street-day | very wide | a well-run café in the city; an extra walks in |
| S005 | 12.5–16.8 | living-room | wide | the guide holds "$30,000 / sales a month" |
| S006 | 16.8–19.9 | chalk-room | medium | pie builds: ingredients 30%, staff 30% |
| S007 | 19.9–24.4 | chalk-room | insert | full pie with rent 12% |
| S008 | 24.4–28.4 | office (seated) | medium | the auditor at her desk; label "power, ads, more" |
| S009 | 28.4–32.7 | tv-room | medium | "~19%" on the wall TV; the guide hops |
| S010 | 32.7–36.8 | ots-office | over the shoulder | the guide holds "~95¢ per $5 latte" past a dark shoulder |
| S011 | 36.8–39.7 | meeting | wide | four people at a table; label "aim: 10–15%" |
| S012 | 39.7–43.7 | custom:cafe | very wide | a queue of extras walks to the stall; coin stack |
| S013 | 43.7–48.9 | sunset-city | wide | the guide holds "200 a day"; the barista cheers |

Camera moves come from the kit (`kit/camera.js`): push, pull, still or follow by the measured mix, linear, with the last 20% held; board shots only creep (≤ 3%) so the words stay in frame.

## Score structure

Original piano bed (Salamander Grand Piano, CC BY 3.0) in F major, F–C–Dm–B♭, two bars of 2.2 s per chord, a soft arpeggio over a low root, ducked under the voice to about 11 dB below it; a three-note F-major chord to end. Effects: a whoosh on each cut, a till ding on the payment, clicks as list rows and pie slices appear, a ding on "~19%". Light compression (ratio 2), mixed to −14 LUFS, true peak −3.2 dB, loudness range 2.0 LU (the style measures 2.8–4.7 LU: a known gap, see Checks).

## Palette & props

Kit palette (style §3): muted grey and slate sets, wood floors, flat pale-blue day sky, purple-to-orange sunset; money green only on "~19%" and "~95¢". The guide (narrator) wears the kit's default muted orange hoodie; the barista is the kit's `worker` role; customers and the queue are white-faced extras. Props: the stall part, a coin stack.

## End card

None: the film ends on the guide's sign in the sunset street.

## Build notes

- `demo/index.html`: the scene table only (13 scenes), made by `demo/build.py` from `lines.json` and the voice durations; `demo/plan.json` carries the line times and shots for `mix.py`.
- `sh demo/build.sh` (writes to `$OUT`, default `../demo-out`): copies `../kit/` next to the page, makes the voice with Kokoro (`say` replaces a line's text where set), renders with `core/render/video.mjs`, mixes with `mix.py`, muxes at 30 fps. On this machine the GPU render took 57 s.
- In the studio the film was made with the film flow of `CLAUDE.md`: `script check` 10/10 and `script review` 8.0/10 (round 2, no P1; open P2: three numbers in a row in P06, the volume ending in P07 not fully argued), tier 0 voice, tier 1 plan, tier 2 shots (no frame problem, no shot-grammar warning: medium 50%, wide 33%, very wide 8%, close 8%, over the shoulder 17%), tier 3 per render chunk, tier 4 final. Results: `demo-checks.json`.
- Pitfalls met while making it: the kit's "palm" pose put the hand across the mouth (moved to shoulder height); a pushing camera with drift pushed a board's words out of frame (board shots now only creep); the whiteboard fill was clipped white (toned down); the labeller read full-figure "medium" shots as wide (medium now cuts at the waist).

## Checks

| Tier | Result |
|---|---|
| Script | check 10/10, review 8.0/10 (no P1) |
| 0 voice | pass |
| 1 plan | pass (silence 20%, 13 shots, 1.9–5.2 s) |
| 2 shots | pass, 0 style warnings |
| 3 render | pass (GPU) |
| 4 final | pass; one style warning: loudness range 2.0 LU vs 2.8–4.7 LU |
