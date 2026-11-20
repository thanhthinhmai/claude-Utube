# Sketch Explainer — Evidence

Set: 12 landscape videos of one 2D cartoon explainer channel, 180 s measured per video (0–60 s plus four 30 s windows), 2160 s in total. Shots labelled by an independent model pass (second pass on 40 shots: same scale 0.80, within one step 1.00, same angle 0.975).

## Key numbers

| Measure | Median | Range |
|---|---|---|
| saturation (sat_p50) | 0.118 | 0.067–0.317 |
| brightness (luma_p50) | 0.461 | 0.401–0.625 |
| clipped whites (bright_p50) | 0.0069 | 0.0009–0.0476 |
| cuts per minute | 14.2 | 8.7–20.0 |
| shot length median | 3.0 s | 2.57–4.97 s |
| still_ratio | 0.62 | 0.55–0.80 |
| motion720_p50 | 0.26 | 0.11–0.39 |
| shots with a moving camera | 78% | push 33%, pull 23%, follow 21%, still 22% |
| push rate | 3.3 %/s | q1 1.4 – q3 6.0 |
| hard cuts | 95% | dissolve 2%, streak 1.4%, flash (bright dissolve) 1.4% |
| scale: medium / wide / very wide / close / extreme close | 47 / 19 / 14 / 11 / 3 % | — |
| graphic inserts | 20% of shots | — |
| angle: eye / over-the-shoulder / high | 82 / 12 / 3 % | — |
| scale change between shots | 66% | 33–75% |
| longest run of one scale | 4 | 2–8 |
| focused share | 0.917 | 0.833–1.0 |
| foreground blur share | 0.059 | 0–0.159 |
| sets per 3 minutes | 23.5 | 13–44 |
| set change every | 4.3 s | 2.5–7.5 s |
| in-frame motion share of a shot | 0.93 | q1 0.66 |
| inner events per second | 0.41 | — |
| speech rate | 3.53 words/s | 3.30–3.89 |
| pauses (in / after sentence / paragraph) | 0.42 / 0.52 / 0.80 s | — |
| silence per minute | 0.68 s | 0–4.6 s |
| loudness | −18.2 LUFS | −21.4 – −15.5 |
| loudness range | 3.95 LU | 2.8–4.7 |
| music bed under voice | −11.4 dB | −6.2 – −16.5 |
| sound effects (in segments) | 15.8 /min | 2–35 (upper bound; `learn sound --recompute`, specs/028) |
| sentence length | 7 words | IQR 4–12 |

Palette (share of pixels): #1a191a 21%, #e4e6e7 16%, #91989a 10%, #51575b 10%, #a9bacb 8%, #2b303e 6%, #575145 4%, #5b4030 3%.

## Reports

- Visual (`analysis/visual.md`): flat cel shading with one shadow tone; near-black even outline ≈ 0.5% of frame width on figures; round no-neck heads, bean torsos, stick limbs; white faces for extras, skin tone for leads; real people by 2–3 signature features plus a name plate; muted grey ground with red/green meaning accents; many line-drawn sets; charts as props; black chapter cards with white handwriting.
- Motion and depth (`analysis/motion-depth.md`): slow constant pushes, bigger pulls as reveals, 95% hard cuts, pose-to-pose acting with an event about every 2.4 s, three flat layers with dark foreground silhouettes, no blur.
- Sound and script (`analysis/sound-script.md`): one fast narrator from frame 0 with tight pauses, acted character lines with dry asides, a constant music bed ≈ 11 dB under the voice, short sentences (median 7 words), sparse framed numbers. Script structure is recorded as types only.

Not style: sponsor segments made of real app screenshots and brand pages (4 of 12 videos).

## based_on

`halftone-dossier`: of the library styles it is the closest technique — an SVG DOM page with `render(t)`, a character rig with a face interface, stamps and paper props. Only the engine technique is taken, not its rules (halftone, paper grain and dossier look are not part of this style). The studio's own SVG kit (two studio films) is the working engine.

## Corrections log


| # | Before | After | Evidence | Found by |
|---|---|---|---|---|
| 1 | The camera is static most of the time (still_ratio 0.62). | Per-frame change is small, but only 21.7% of shots are locked; a slow push, pull or follow runs in the rest (77.5% of measured time). | pooled `vNN/craft.json → cam.type`: push 204, pull 145, still 136, follow 129, drift 14 of 628 (re-counted in the main session) | numbers |
| 2 | Lateral follow/pan is 20.5% of shots. | True camera pans are about 10–15% of shots; part of the "follow" class is a figure or prop moving inside a locked frame. Kept as a range, not a rule. | `v02/strips/S031.jpg#1–4`, `v12/strips/S020.jpg#0–7` vs a real pan `v11/strips/S008.jpg` | sheets |
| 3 | Sound effects run at 19–62 per minute (`sound.json → sfx.per_min`). | About 16 per minute (2–35) inside the measured segments; the stored value counted speech outside the segments as effects. Still an upper bound (music hits). | sfx onsets filtered to `video.json → segments`; confirmed by the fixed tool (`learn sound sketch-ref --recompute`, specs/028): median 15.8/min | numbers |
| 4 | Transitions: 562 cuts, 36 dissolves, 9 flashes, 8 streaks of 628. | 47 junctions are sampler splices between measured segments, not edits. Real transitions: cut 539 / dissolve 12 / streak 8 / flash 8 / fade 1 (94.9% hard cut). | `video.json → segments` starts vs `trans_in` times | numbers |
| 5 | "Flash" transitions (9) are white flash cuts. | They are bright dissolves; `flashes_per_min` is 0 in every video. No flash cut is part of the style. | `summary.json → flashes_per_min` 0.0; craft flash dur 0.33–0.63 s | numbers |
| 6 | Sheets `v06_0046`, `v10_0046` show a per-frame strobe. | Not a rule of the style: an isolated alternation (decoding artefact or one-off intercut); excluded. | viewed `v06/sheets/v06_0046.jpg#0–29` in the main session; `flashes_per_min` 0 | sheets |
| 7 | Videos v03, v05, v08–v12 (cuts/min below 16) may have missed cuts. | The low rates are real long holds (over-the-shoulder screen shots, held dialogue), not missed cuts. The style takes the set range 8.7–20 with median 14. | `v05/sheets/v05_0030.jpg` (one held OTS laptop shot over 2 s), `v05/strips/S015.jpg` | sheets |
| 8 | Line width 0.45–0.6% of frame width. | Kept, marked medium confidence: measured at 960 px on 12 frames; scale with figure size. | visual report §Outlines row 2 | numbers |

