# Evidence — Dusk Hypothetical

Learned from 10 landscape reference videos (≈ 10.5 min each), measured over 5 windows per video (0–60 s, then four 30 s windows, 1800 s in all). Full reports: `analysis/visual.md`, `analysis/motion-depth.md`, `analysis/sound-script.md` (kept with the reference set, not in the style).

## Key numbers (median, range)

| Metric | Median | Range |
|---|---|---|
| luma p50 | 0.261 | 0.198–0.299 |
| contrast p50 | 0.196 | 0.177–0.213 |
| saturation p50 | 0.355 | 0.319–0.504 |
| bright share | 0.002 | 0.001–0.005 |
| still ratio | 0.81 | 0.72–0.88 |
| motion p50 / p90 | 0.111 / 1.05 | — |
| cuts/min (re-measured) | ≈ 25 | 21–29 |
| loudness | −14.05 LUFS | −14.4 to −13.8 |
| loudness range | 2.85 LU | 2.4–3.3 |
| first voice | 0.0 s | 0.0–0.0 |
| speech rate | 3.73 w/s | 3.36–3.85 |
| medium share | 0.34 | 0.23–0.47 |
| wide share | 0.27 | 0.20–0.44 |
| close-up share | 0.20 | 0.05–0.30 |
| huge wide share | 0.14 | 0.05–0.22 |
| extreme close-up share | 0.05 | 0.00–0.11 |
| eye-level share | 0.66 | 0.49–0.75 |
| high-angle share | 0.19 | 0.11–0.28 |
| scale change between neighbours | 0.69 | 0.63–0.76 |
| longest same-scale run | 4 | 3–6 |
| focused share p50 | 0.67 | 0.50–0.83 |
| subject in focus | 1.00 | 0.99–1.00 |
| foreground blur share | 0.16 | 0.03–0.41 |
| places per video | 16 | 9–24 |
| busiest place share | 0.26 | 0.13–0.48 |

Palette (share of pixels): #271937 29 %, #07050a 21 % (bars + vignette), #493369 11 %, #796a8c 9 %, #5a4744 6 %, #4e2e38 5 %.

## Summary of the three reports

- **Visual:** violet dusk grade with magenta cast (G lowest in every video); no outlines; smooth matte low-poly 3D; strong vignette (corner/centre ≈ 0.53); one sphere-headed chibi figure design with dot eyes, no nose or ears, hoodie and stick limbs, checked on 10+ frames per video; saturated colour only on props and costumes; flat data inserts in a violet void; gold serif all-caps captions; 2.05:1 letterbox.
- **Motion & depth:** locked camera with slow push-ins, no whips; hard cuts only; real 3D with constant shallow DOF and blurred foreground occluders; shot scale alternates extreme close-up ↔ huge wide; ≈ 10–15 % of shots are flat inserts; only the hero acts, eyes and lids carry expression, no lip-sync; bloom pops on impacts.
- **Sound & script:** voice from frame 0, continuous bed, no silence, heavy compression; ≈ 160 wpm steady; second person present tense; short sentences (median 5–8 words); structure patterns recorded abstractly (hook, escalation beats with fact asides, crisis with a binary choice). Endings were not sampled.

## Corrections log

| # | Before | After | Evidence | Found by |
|---|---|---|---|---|
| 1 | Median shot ≈ 5.6 s, ≈ 5.8 cuts/min | Cuts every 2–3 s, ≈ 16–26 cuts/min; the stored detector misses cuts between similar dark violet setups | `v01` 60–180 s re-run: scene > 0.3 → 33 cuts, > 0.15 → 53 vs stored 7.67/min; cell-level pass median 22.5/min | both |
| 2 | Letterbox ≈ 44 px | 48 px of 720 (6.7 % each, 2.05:1); 72 px at 1080p | `cropdetect` → `crop=1280:624:0:48` | numbers |
| 3 | 81 % still = long holds | Locked camera inside short shots | `still_ratio` 0.81 with cuts every 2–3 s | both |
| 4 | v04 lightning counted as cuts | Light accents, not cuts | `v04_0077.jpg#38–41, #50–51, #98–101` | sheets |
| 5 | Ending structure inferred | Not a rule (never sampled) | `segments[4]` ends ≈ 84 % of runtime | numbers |
| 6 | No outlines anywhere | Thin dark contour on the hero's head in close-ups only | frames v03 38.5 s, v08 5 s vs v01 175.9 s | sheets |
| 7 | Captions in serif | Wide-tracked caps in a serif and a geometric sans | frames v01 52 s, v03 38.5 s | sheets |
| 8 | Shot scale alternates extreme close-up ↔ huge wide | Mostly medium (34 %) and wide (27 %); close-up 20 %, huge wide 14 %, extreme close-up only 5 %; the scale changes in 69 % of cuts, runs of up to 4–6 | shot grammar of 772 labelled shots (2026-11-13 set); ECU `v01_shots_2.jpg#19–20`, huge `v01_shots_1.jpg#11`, medium `v01_shots_1.jpg#3` | numbers |
| 9 | Constant shallow DOF | The subject is always in focus (100 % of shots), about two thirds of the frame sharp (median 0.67, 0.50–0.83); a blurred foreground in 16 % of shots | `focus.py` on every mid-shot frame (12 tiles, sharp from 200); foreground blur `v01_shots_1.jpg#1, #6` | numbers |
| 10 | ≈ 16–26 cuts/min | ≈ 21–29 cuts/min on the 2026-11-13 set (scene > 0.15) | `learn shots`: 69–91 shots per 180 s | numbers |
| 11 | Low angle and top-down are the main grammar | Eye level 66 %, high 19 %, over-the-shoulder 7 %, low 5 %, straight down 1 % | shot grammar; low `v01_shots_2.jpg#27`, top `v01_shots_1.jpg#27`, ots `v01_shots_1.jpg#7` | numbers |

Tool note: the style-learn cut detector undercounts cuts in dark, low-contrast footage; `learn shots` (specs/021) splits shots with the scene score > 0.15 instead.

## Shot grammar

Re-learned on 2026-11-13 from the ten most recent videos of the same reference channel (5 windows each, 1800 s): 807 shots, 772 labelled by the studio's independent shot labeler (one Opus run per video, from contact sheets of one mid-shot frame per shot), focus measured by `tools/filmcheck/focus.py`. Two independent labellings of 40 shots agreed on the scale for 70 %, within one step for 100 %, on the angle for 68 % (77 % leaving out text cards). The numbers the checks compare with are in `shots.json`.

## Why `based_on: brick-toy`

Candidates read: `brick-toy`, `lowpoly-island`, `tilt-shift`. The measured look needs a **perspective** three.js camera, a **character rig** and **physical DOF** with foreground blur. `lowpoly-island` is orthographic isometric (wrong lens); `tilt-shift` has no character rig. `brick-toy` has the perspective camera, the rig with pose objects and the DOF set-up; only its engine is taken, not its rules (no bricks, no stop-motion stepping, no macro-desk world).
