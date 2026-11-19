# Evidence — Dusk Hypothetical

Re-learned on 2026-11-13 from the **ten most-viewed** landscape films of the reference set, **full length** (6654 s in all: eight films ≈ 10.5 min, one 6 min, one 20 min), 2192 shots split by scene score > 0.15, 2167 labelled by the studio's independent shot labeler (Opus). Full reports: `analysis/visual.md`, `analysis/motion-depth.md`, `analysis/sound-script.md` (kept with the reference set, not in the style). Eight films are 3D; two (v03, v08) are flat 2D with outlines: the look rules come from the 3D films, pacing, shot grammar and structure from all ten.

## Key numbers (median, range)

| Metric | Median | Range |
|---|---|---|
| luma p50 | 0.252 | 0.221–0.292 |
| luma p2 / p98 | 0.095 / 0.459 | — |
| contrast p50 | 0.189 | 0.176–0.209 |
| saturation p50 | 0.375 | 0.318–0.410 |
| bright share | 0.001 | 0.001–0.003 |
| still ratio | 0.86 | 0.72–0.93 |
| cuts/min (shots.json) | ≈ 21 | 18–26 (20-min film 13.7) |
| median shot | 2.3 s | 1.95–3.38 |
| loudness | −14.0 LUFS | −14.4 to −14.0 |
| loudness range | 2.95 LU | 2.5–3.7 |
| first voice | 0.0 s | 0.0–0.0 |
| speech rate | 3.81 w/s | 3.70–3.95 |
| longest gap between words | ≈ 1.0 s | 0.82–1.26 |
| words per sentence | 6 (mean 6.5) | per film 4.5–7 |
| real facts per minute | ≈ 1.1 | 0.8–1.5 |
| medium share | 0.32 | 0.14–0.39 |
| wide share | 0.25 | 0.16–0.44 |
| close-up share | 0.22 | 0.06–0.38 |
| huge wide share | 0.13 | 0.09–0.28 |
| extreme close-up share | 0.06 | 0.03–0.15 |
| eye-level share | 0.74 | 0.57–0.98 |
| high-angle share | 0.12 | 0.00–0.14 |
| over-the-shoulder share | 0.09 | 0.00–0.24 |
| scale change between neighbours | 0.68 | 0.59–0.78 |
| longest same-scale run | 5 | 3–11 |
| focused share p50 | 0.67 | 0.58–0.67 |
| subject in focus | 0.99 | 0.96–1.00 |
| foreground blur share | 0.14 | 0.01–0.26 |
| places per film | 29.5 | 18–49 |
| busiest place share | 0.19 | 0.10–0.38 |
| place change | 4.9 s | 4.0–6.3 |
| graphic inserts per minute | ≈ 1.6 | — |

Palette (share of pixels): #2d2241 30 %, #0f0b17 22 % (bars + vignette), #5d414b 17 %, #443964 10 %, #937e94 6 %, #938dbb 4 %, #d6c7ba 2 %, #beabae 2 %.

## Summary of the three reports

- **Visual:** violet dusk grade, shadows blue-violet and lit sides pink-peach; warm colour only from practical lights and costumes; about a third of shots leave violet briefly (warm floors, green fields, white clinics). One body plan for every character (sphere head ≈ 1/3 of height, dot eyes, hoodie, stick limbs, ball hands), side characters told apart by hoodie colour, then hair or headwear, then a prop. Richness comes from crowds (10 to thousands), repeated prop grids, light points as bokeh, 3–4 depth layers and props in hand. 16 kinds of graphics, ≈ 6–10 graphic moments per minute; serif or sans caps titles, number pills, white speech bubbles.
- **Motion & depth:** locked camera in ≈ 80 % of shots, slow drifts, big moves only for set pieces; hard cuts, a 0.15 s light-streak swap for state changes, rare fades. First minute fastest, minute two slows, a burst around minutes 8–9, the last shot held 4.5–12.7 s. ≈ 30 places per film with an A-B-A-C-A spine; new places open wide; ≈ 1 in 3 in-place cuts goes to a reaction close-up.
- **Sound & script:** voice from frame 0 to the end, no gap over 1.3 s, continuous bed, −14 LUFS. Full act structure measured (now in STRUCTURE.md): hook 8 %, explainer 8 %, personal gain 19 %, public scale 29 %, cost 9 %, crisis 16 %, resolution 6 %, sting 4 %, closing card 1.5 %; 12–16 vignettes, a chapter turn every 1:20–1:45, ≈ 1.1 facts per minute, side characters as bubbles at five fixed points.

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
| 12 | Shares of #8, #9, #11 from a first labelling without a guide (two labellings agreed on 70 % of scales) | Relabelled with a code-drawn guide and frame-edge rules (agreement 80 % scale, 97 % within one step, 88 % angle): medium 30 %, wide 26 %, huge wide 18 %, close-up 14 %, extreme close-up 10 %; eye 73 %, high 12 %, over-the-shoulder 11 %, low 3 %, top 1 %; scale changes in 70 % of cuts, runs up to 4–8; blurred foreground 14 % | `profile/agreement.json`; `tools/filmcheck/labeler-guide.png` | numbers |
| 13 | Letterbox 48 px of 720 (2.05:1) | 46 px of 720 (6.4 % each side, 2.04:1) | `cropdetect` on v01, v06, v09 at 120 s → `crop=1280:628:0:46` (2026-11-13 set) | numbers |
| 14 | Learned from the 3 first minutes of ten recent films | Re-learned from the ten most-viewed films, full length (6654 s, 2192 shots); the earlier set saw 15 places per film, the full films have ≈ 30 (18–49) | `summary.json → sets` 29.5 | numbers |
| 15 | v03, v05, v08 are flat 2D (motion report) | v03 and v08 are flat 2D with outlines; v05 is 3D rendered at 24 fps. The look rules come from the eight 3D films (user choice); shot grammar, pacing and script use all ten, since they match | `v05_shots_2.jpg` (3D, DOF), `v03_shots_2.jpg` (flat, outlined) | sheets |
| 16 | ≈ 5 cuts/min, median shot 7 s (`video.json`) | ≈ 21 cuts/min, median 2.3 s; the frame-difference detector undercounts in this dark footage | `shots.json` per video 18–26 cuts/min (v10, 20 min: 13.7) | numbers |
| 17 | Captions in a serif and a geometric sans (corrections #7) | Titles in a caps serif, cream or gold with a glow; the reference splits 5/5 between a serif and a heavy sans, the user chose the serif | visual on-screen text #2 | both |
| 18 | Saturated colour only on props and costumes; the violet grade holds | About 2/3 of shots violet; ≈ 12 % warm orange, ≈ 4 % green, ≈ 3 % white-lilac as short story beats, violet walls or sky still in frame | visual colour #9 (own hue pass over 2166 shots, medium confidence) | both |
| 19 | Only the hero acts; extras are rare | Wide shots almost always hold extras (10–30 in a room, up to thousands), repeated prop grids and practical lights; this density is the main gap of the earlier demo | visual detail level #1–4; `v04_shots_1.jpg#S012`, `v10_shots_6.jpg#S243` | sheets |
| 20 | §11 asks for structures, openings and endings different from the reference | The film follows the reference act structure (STRUCTURE.md); variation lives inside it | channel decision 2026-11-13 (user) | user |
| 21 | Hero is a sphere-headed figure in a hoodie (any) | The body plan is shared by every character; the reference's own hero (bald, one fixed hoodie colour) is its character and is not copied: each channel keeps its own hero costume | visual character kit #1 | both |
| 22 | Typeface split 5/5 serif vs sans; 30 fps enough | The channel's current look: the three newest uploads all use the gold/cream caps serif; every film from late October on is 3D at 60 fps, the 24 fps films (v03, v05, v08) are the oldest of the set | upload dates (v03 2026-10-23, v05 10-25, v08 10-11 vs others 10-26 to 11-05); frames of the three newest uploads at 20–70 s (viewed, not kept) | both |
| 23 | Graphic inserts sit on the violet void | Also over the defocused, darkened scene (diagrams with a flat figure icon, gauges, two-bar charts, dotted arc plans), most often in the newest films | newest uploads 20–70 s; `pass2/pass2_1.jpg` v04-S028, v09-S133 | sheets |
| 24 | Scale agreement 65 % between the two labellings | Adjudicated by eye: the first labelling (the one the shares come from) is right in 9 of the 14 scale disagreements, ≈ 87 % (35/40) of the sample; the rest are graphics over a defocused scene (count as insert) and medium vs wide on figures cut by props | `pass2/pass2_1.jpg` all 14 cells of `agreement.json → disagreements` | sheets |
| 25 | Foley on story actions: impacts, whooshes on pops, a glow sound on reveals, UI ticks on counters, crowd murmurs (STYLE §7) | Removed (2026-11-17, specs/023 FR-001): no evidence; the sound report says most foley is unscripted and was not counted. Sound effects come back once measured (specs/023 US2) | `analysis/sound-script.md` §6.7 | both |
| 26 | The continuous bed has "no swells" (STYLE §7) | Removed (2026-11-17): no measure or frame behind it; the bed itself stays (sound §6.5) | — | both |
| 27 | Framing: subject centre or centre-right (STYLE §6) | Centre: the sharpest tile is in the two middle columns in 74–92 % of shots per scale, left and right middle columns about equal; off-centre most in extreme close-ups (26 %) | `profile/craft-summary.json → framing.by_scale` (8 3D films) | numbers |
| 28 | Subtitles inside the picture, reading time (STYLE §4) read as a rule of the style | A studio rule: the reference films do not burn in subtitles; kept because the channel chose it (2026-11-14) and labelled [xưởng]; every STYLE rule now carries [bằng chứng: …] or [xưởng] | user choice 2026-11-14; specs/023 FR-001, FR-015 | user |
| 29 | Warm raking light as a look of the style (comparison sheet 2026-11-14) | Not a general rule: warm highlights cover a median 0.2 % of the picture (p75 1.6 %); one side clearly brighter in ≈ 55 % of shots, as often from the left as from the right; warm stays in practicals (visual §1.7) | `profile/craft-summary.json → light.all` (1670 cells) | numbers |
| 30 | Camera locked in ≈ 80 % of shots (still ratio 0.86) | The still ratio only saw shifts (phase correlation), not zoom. Measured with a camera model that includes zoom: a truly still camera covers 0.24–0.84 of each film (median 0.36); a slow push-in is the default (about half of close-ups and mediums, 1–5 %/s) | `profile/craft-summary.json → motion` (learn craft, 2026-11-17); frames of v01 S003, S010, S012, S006 | both |
| 31 | Figures are mostly posed; life from lids, tilts and mouth flaps | Every shot makes one thing happen (expression, gesture, tilt, talk, a prop acting); still-camera shots with a person show movement in 89 %; gestures rise in ≈ 0.4 s | `profile/craft-summary.json → motion.person_still_cam`; 80 strips (`style/craft-notes.md`) | both |

Tool note: the style-learn cut detector undercounts cuts in dark, low-contrast footage; `learn shots` (specs/021) splits shots with the scene score > 0.15 instead.

## Shot grammar

Re-learned on 2026-11-13 from the ten most-viewed films, full length: 2192 shots, 2167 labelled by the studio's independent shot labeler (Opus, code-drawn guide and frame-edge rules), focus measured by `tools/filmcheck/focus.py`. Two independent labellings of 40 shots agreed on the scale for 65 %, within one step for 92 %, on the angle for 90 % (89 % leaving out text cards). Scale agreement is lower than the earlier set's 80 %: the full films hold more crowd and two-figure shots where medium and wide are close; the shares are kept, with medium and wide read together where they matter. Adjudicated by eye, the first labelling is right in 9 of the 14 disagreements (≈ 87 % of the sample, corrections #24). The numbers the checks compare with are in `shots.json`.

## Why `based_on: brick-toy`

Candidates read: `brick-toy`, `lowpoly-island`, `tilt-shift`. The measured look needs a **perspective** three.js camera, a **character rig** and **physical DOF** with foreground blur. `lowpoly-island` is orthographic isometric (wrong lens); `tilt-shift` has no character rig. `brick-toy` has the perspective camera, the rig with pose objects and the DOF set-up; only its engine is taken, not its rules (no bricks, no stop-motion stepping, no macro-desk world).

## Craft shares (specs/027)

learn craft-label dusk-hypothetical-3, 2026-11-19, 1650 shots of 8 videos (skipped v03, v08), craftlabel 56331af26eb1.
Action and prop: share of shots with people; outdoor and ots: share of shots that are not cards. Action min = p25 of the videos (error in qc plan); others warn outside min–max.

| video | shots | action | prop | outdoor | ots |
|---|---|---|---|---|---|
| v01 | 199 | 0.11 | 0.141 | 0.397 | 0.241 |
| v02 | 210 | 0.134 | 0.113 | 0.286 | 0.105 |
| v04 | 158 | 0.144 | 0.075 | 0.399 | 0.044 |
| v05 | 201 | 0.152 | 0.152 | 0.756 | 0.08 |
| v06 | 203 | 0.068 | 0.13 | 0.3 | 0.133 |
| v07 | 247 | 0.352 | 0.247 | 0.498 | 0.093 |
| v09 | 190 | 0.148 | 0.109 | 0.295 | 0.195 |
| v10 | 242 | 0.07 | 0.09 | 0.376 | 0.058 |
| min | | 0.068 | 0.075 | 0.286 | 0.044 |
| p25 | | 0.1 | 0.104 | 0.299 | 0.075 |
| p50 | | 0.139 | 0.121 | 0.387 | 0.099 |
| p75 | | 0.149 | 0.144 | 0.424 | 0.149 |
| max | | 0.352 | 0.247 | 0.756 | 0.241 |

## Brightness inside the picture (specs/027 R8, 2026-11-19)

The frame-level numbers above include the reference's letterbox bars (≈ 13 % of the frame, black), so they read darker than what is inside the picture. Measured again with the same tool (`sl.color.frame_stats`) on the picture area only (bars cut), one mid-shot frame per shot, 1668 non-card shots of the eight 3D films: **luma p25/p50/p75 0.253 / 0.327 / 0.403, saturation 0.293 / 0.360 / 0.458**. On the same picture-only measure the kit 023 grade gave luma p50 0.242 (six shots of films/pause-ten-seconds): darker than the reference although its frames had passed the frame-level comparison. The kit v3 grade (`kit/GRADE.md`) gives luma p50 0.354, saturation 0.387 on 22 shots of the eleven sets (films/kit-sets), inside the reference's middle range. The frame-level table stays as it is: films are measured with their bars too, so tier 4 compares like with like.
