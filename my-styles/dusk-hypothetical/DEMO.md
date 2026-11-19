# Dusk Hypothetical — our demo

One example among many. Don't reuse its story, arc, shots, props or timings.

Demo: *What If Gravity Got 10% Weaker Overnight?* (23.6 s) · `test.mp4` (poster `test.jpg`) · source in [`demo/`](demo/) · credits [`demo/CREDITS`](demo/CREDITS) · checks [`demo-checks.json`](demo-checks.json)

## Story & structure

You wake up on an ordinary morning and the planet holds you a little looser: nothing breaks, everything is slightly off. It uses one of the style's own openings and endings (§11: "an ordinary morning that goes subtly wrong", "a wide pull-out to the whole planet with one last number"), not the reference set's triumph-to-crisis shape.

Five paragraphs, one beat each: the morning (alarm, the hop that lands late) → the premise on a fact card (−10 %) → the Moon for scale (1/6 g) → three small consequences, each with a number (scale −10 %, jump +11 %, the coffee arc) → the quiet pull-out to a small planet (0.9 g).

Native moves spent: **the rule card** (the void insert, "EARTH'S PULL −10%"), **counter tick** (the scale counts 70.0 → 63.0 kg inside a held shot), **fact aside** (the Moon card over the rooftop). Not spent here: scale jump, mood flood.

## Shots

The shot table was planned from `shots.json` before the page was written (scale and angle shares, scale change between neighbours, subject sharp), then checked by `qc shots` with the studio's independent labeler. Final labels:

| # | Time | Shot | Scale · angle | Place | Native move / note |
|---|---|---|---|---|---|
| S01 | 0.00–1.68 | the alarm clock at 7:00, blinking | ECU · eye | bedroom | aperture 1.5 so the clock face and its small labels stay sharp |
| S02 | 1.68–4.68 | the hop off the bed, an arc that lasts too long | wide · high | bedroom | camera ≈ 40° down; the arc is 0.5 m, not a float to the ceiling (the line says "a beat late") |
| S03 | 4.68–7.45 | flat Earth icon, "EARTH'S PULL −10%" counting up | insert | void | the rule card; a flat graphic, so it reads as an insert, not a huge wide |
| S04 | 7.45–9.43 | the hero under a big Moon, "1/6 G" | med · eye | rooftop | fact aside; hero centre-right, card top-left |
| S05 | 9.43–14.25 | on the scale, the counter ticks to 63.0 kg | med · eye | bathroom | counter tick; holds two sentences (P03 ends here, ≥ 2.5 s) |
| S06 | 14.25–16.42 | a small jump in the street, "+11%" | med · eye | street | med → med → med on purpose: the style keeps the scale across ≈ 30 % of cuts |
| S07 | 16.42–20.39 | coffee poured in an arc into the flatmate's cup | CU · OTS | kitchen | the flatmate's head is the blurred foreground (aperture 9) |
| S08 | 20.39–23.60 | the hero on top of a small planet, "EARTH TODAY 0.9 G" | huge · eye | small planet | slow pull-back at the hero's eye height (a higher camera was labelled "high") |

Result: ECU 14 %, CU 14 %, medium 43 %, wide 14 %, huge 14 % (one insert left out); eye level 71 %, high 14 %, over the shoulder 14 %; scale change 60 % of cuts; longest same-scale run 3; median focused share 0.58 (style: 0.50–0.83).

Cuts fall only between sentences (the studio's plan check), so a 2–3 s rhythm needs short sentences: each shot holds one or two of them, and a paragraph's last shot lasts at least 2.5 s.

## Score structure

Synthesized in `demo/mix.py`, no samples: a continuous pad bed at 96 BPM (Em – C – G – D, one chord per 2.5 s bar) with a muted eighth-note pluck and a soft kick on each bar, ducked about 45 % under the voice. Foley: two-tone alarm beeps, a rising tone under the long hop, a thump on each landing, a whoosh on the jump, UI ticks under the counters, pops on card reveals, a filtered trickle for the pour, faint whooshes on cuts. No silence: the bed runs from frame 0 to the fade.

Voice: Kokoro `am_michael` at speed 1.1 (the channel's voice), eleven lines, one per sentence ("Same body. Same breakfast." is one line), gaps 0.1 s inside a paragraph and 0.3 s between paragraphs; every line checked by speech recognition. Mastered by the library's `mux.sh` to −14 LUFS, no grain.

## Palette & props

- Grade: the shared post chain (`makePost`, vignette 0.42, saturation 0.72, contrast 0.25, bloom 0.3); the film measures luma ≈ 0.27, saturation ≈ 0.46.
- Hero: sphere head `#efe6f0`, mustard hoodie `#d9b23a` (the film's one saturated accent); the flatmate wears teal `#3f9a9a`.
- Sets: bedroom walls `#55426e`, floor `#6a5068`; bathroom tiles `#7a6a96`; rooftop and street buildings `#4a3c66`–`#5a4878` with lit windows; void `#2a1e42`; planet `#5a4a78` on `#1e1634`.
- Surface detail on purpose: wallpaper stripes, floorboards, tile grout, building windows, bookshelf, bottles, stars. Smooth walls left the in-focus part of the frame flat, and the focus measure (Laplacian variance per tile) read the whole frame as soft (median 0.08 before, 0.58 after).

## End card

None: the film ends on the planet pull-out with the last number. No LemoLab credit (a studio film).

## Build notes

- `demo/index.html` (page: sets, figure, shot plan `PLAN`, cards, subtitles, `window.SHOTS`/`CARDS`/`CUES`/`TEXTS`, `window.CLEAN`), `demo/mix.py` (bed, foley, voice), `demo/lines.json` (the voice lines), `demo/events.json` (sound events exported from the page), `demo/build.sh`, `demo/CREDITS`.
- `sh demo/build.sh` (or with `OUT=<folder>`): makes the voices with Kokoro if they're missing, records the page at 30 fps, mixes and muxes `dusk-demo.mp4` into `$OUT` (default: a folder next to the style, never inside `demo/`).
- In the studio the film was made with `sh bin/studio render dusk-demo --fps 30` after tiers 0–2 passed: 708 frames in 71 s on the GPU (Intel UHD 730 through WSL2), 878 s in software WebGL. `build.sh` uses the library's `video.mjs`; set `PLAYWRIGHT_CHROME=<studio>/tools/render/chrome-gpu.sh` for the GPU (96 s for the whole build, voices included).
- Pitfalls: the page copies each WebGL frame into a 2D canvas (software WebGL layers can't be captured otherwise); the DOF focus follows the look target automatically (a hand-set focus 0.3 m off blurred the hero); the void must stay flat to be labelled an insert.
