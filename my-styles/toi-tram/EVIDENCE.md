# Evidence — Quiet Night

Learned by measurement from a reference set of 5 landscape videos (1280×720, 30 fps). Each video was measured over 180 s (0–60 s plus four 30 s windows), 900 s in total and every frame. The videos are the five most recent long-form uploads of one channel; its short vertical clips were excluded to keep one format. Reference media is not part of this style.

## Set-level numbers (median, min–max)

| Metric | Median | Range |
|---|---|---|
| luma_p50 | 0.303 | 0.205–0.450 |
| luma_p98 | 0.568 | 0.440–0.609 |
| luma_p2 | 0.008 | 0.003–0.159 (v01 daylight outlier) |
| contrast_p50 | 0.183 | 0.134–0.200 |
| sat_p50 | 0.175 | 0.108–0.200 |
| dark_p50 | 0.078 | 0.041–0.109 |
| still_ratio | 0.78 | 0.77–0.86 |
| motion720_p50 / p90 | 0.12 / 1.19 px | p90 0.72–1.89 |
| cuts_per_min | 5.0 | 2.3–7.0 |
| flashes_per_min | 0 | 0 |
| shot_len median / mean | 5.35 / 9.0 s | median 5.0–13.9 (v02 outlier) |
| LUFS / LRA | −18.6 / 10.4 | −19.5 to −17.8 / 8.0–11.8 |
| silence_per_min | 0 | 0–0.08 |

Palette (share): #0e0e11 31 %, #4d504f 20 %, #2b2c31 19 %, #7f8681 12 %, #48362d 6 %, #c7c2b8 3 %, #6a6f76 3 %, #c0a67b 2 %.

Warnings carried: only 5 videos, so conclusions are less reliable than with 12. Dispersion in luma_p2 (explained by v01 being a daylight film; the rule is "true black allowed, not required") and in shot_len_median (explained by v02's long locked windscreen two-shots and fade-based scene changes). Only one video has real speech, so voice rules rest on one film and are marked optional.

## Analysis reports (summary)

**Visual** (all 456 sheets at cell 0, 5 full sheets, ~45 enlarged cells):
- low-key, muted, soft contrast, no clipped whites, about 80 % slightly cool greys with two warm swatches, heavy vignette (corner/centre 0.36–0.56)
- flat-black spherical-head characters, about 3 heads tall (12 measurements, median 0.33), white dot eyes and brow arcs, a pale 1–2 px rim on dark grounds
- light follows mood (blue tension, warm resolution)
- four on-screen text families: speech tags, thesis cards, time/place stamps, UI chips; plus diegetic phone UI

**Motion-depth** (59 sheets, around cuts):
- locked camera most of the time with slow follow-pans and drifts, about 5 hard cuts/min, no flashes or whips
- fade from black to open, dips to black for scene breaks, text cards on black, occasional diegetic wipes
- three-layer depth with blurred background and foreground, bimodal shot length
- economical character animation with no lip-sync
- the cut detector is noisy in both directions

**Sound-script** (29 sheets, word timings):
- continuous music bed, about −18.6 LUFS and LRA 10
- 4 of 5 films carry dialogue by captions only
- the one voiced film has in-scene dialogue at about 2.5 words/s, lines with a median of 3 words, and music-only bridges of 6–12 s
- structure: visual cold open, 5–7 beats, a densest confrontation block, a quiet two-shot ending
- recorded as structure only

## Corrections log

| # | Before | After | Evidence | Found by |
|---|---|---|---|---|
| 1 | visual · Textures 1: "worlds are simple low-poly 3D sets" | The worlds are **2D vector illustration**: flat fills, soft linear/radial gradients, perspective drawn by hand, and Gaussian-blurred background planes for depth of field. Nothing shows real 3D shading or specular light. | full-res v02 12.0 s (car interior: flat panels, drawn perspective), v05 40.0 s (flat counter planes, flat pendant lamps), v04 18.9 s (blurred flat gym planes) | sheets (full-res) |
| 2 | visual · Outlines 1: "environments have no ink lines" | Environments have no heavy ink, but some props carry a **thin, soft, slightly darker edge line** (hard hat, car body edges, windscreen frame). The rule is "no black contour; thin tonal edges allowed on props". | full-res v02 12.0 s (hard hat and car frame edges) | sheets (full-res) |
| 3 | visual · Text 1: speech tags are "small regular-weight clean sans on a dark semi-transparent rounded pill" | Speech tags use a **rounded, bold, casual hand-lettered sans** (comic-book feel). The fill is off-white/cream by default, or a pale tint with a coloured glow per speaker (pale pink fill + dark-red halo seen). Behind the glyphs is a **soft, feathered dark smudge/halo**, not a hard-edged pill. | full-res v04 18.9 s, v02 12.0 s, v05 40.0 s, v01 10.2 s | sheets (full-res) |
| 4 | visual · Text 4: "tags pop on with no visible fade (≤ 2–3 frames)"; motion · Text 1: "fade in over 3–5 frames" | Tags **fade in over 2–3 frames** (~0.07–0.1 s): frame 1 faint, frame 2 ~70 %, frame 3 full. That is a fast fade, close to a pop. Both agents were partly right. | v01 10.2 s strip (frames 6→7→8), v04 18.9 s strip (frames 2→3→4) | sheets (full-res) |
| 5 | visual · Text 2: tag cap height ≈ 2–2.5 % of frame height | Cap height is **≈ 4–4.5 %** of frame height (~24 px at 540 p), and line height is ≈ 6.5 %. | full-res v04 18.9 s, v05 40.0 s | sheets (full-res) |
| 6 | sound-script 16: "every film fades up from black" | **4 of 5** films fade up from black (v01 ≈ 1.3 s, v02 ≈ 1.0 s, v03 ≈ 0.3 s, v05 ≈ 0.8 s). v04 opens directly on a dark night shot at luma 0.115 from frame 0, then fades in a time stamp. The rule is "open from black or from a dark, still establishing frame". | `profile/v04/frames.csv` luma frames 0–44 = 0.115–0.124; v01/v02/v03/v05 start at luma ≈ 0 | numbers |
| 7 | summary.json `first_voice_t` median 58.56 s read as "voice enters late at ~1 min" | Only v01 has real speech, with its first word at **7.5 s**. The values for v02 (58.6 s, lang "nn"), v04 (157.7 s, "jw") and v05 (229.8 s) come from 3, 7 and 14 artefact "words". The set median is not meaningful. | `profile/v0N/video.json → speech.first_word_t`, `speech.language`; `words.json` counts 163/3/0/7/14 | numbers |
| 8 | summary.json `speech_rate` median 2.30 read as the voice rate | Only v01 is real: **2.46 words/s** over voiced time, 1.2–2.2 within blocks. The other values are artefacts. | `profile/v01/video.json → speech.rate` 2.458 | numbers |
| 9 | motion · Open question: the ~22 % moving frames "may be mostly characters" | Global frame shift (|dx|+|dy| > 0.3 px) occurs in **14–22 %** of measured frames per video (v01 729, v02 1168, v03 1102, v04 1128, v05 846 of ~5330). So most of the moving frames are **slow camera travel** (pans/drifts), not just character motion. The rule is "locked most of the time, with slow drifts in ~1 frame in 5". | `profile/v0N/frames.csv` dx/dy columns | numbers |
| 10 | visual · Text 7 / motion · Text 5: quote cards (no font detail) | Confirmed and refined: a book-style **serif italic** in warm off-white on pure black, centred about 2–5 % above the vertical middle. Cap height ≈ 4.5 %, set in one line where it fits. | full-res v03 90.5 s | sheets (full-res) |

Checked and kept as written: low key and muted colour (`luma_p50` 0.303, `sat_p50` 0.175, `bright_p50` 0); true black present in 4/5 videos (`luma_p2`); heavy vignette (visible at full res in v02, v04, v05); pale 1–2 px rim on black characters on dark grounds (full-res v05 40.0 s); flat-black spherical-head characters with white dot eyes and brow arcs (full-res v02, v04, v05); floating white UI chips (full-res v05 40.0 s); no flashes (`flashes_per_min` 0); ~5 cuts/min with a noisy detector; continuous music bed (`silence_per_min` 0).

Agent disagreement resolved: tag fade (#4). Dispersion resolved: `luma_p2` (v01 is the daylight film; true black is allowed, not required), `shot_len_median` (v02 holds long locked windshield two-shots).

## Why `based_on: scifi-toon`

The reference look is flat 2D vector shapes with gradients, not 3D (C#1), so the engine must be Canvas 2D vector drawing. The library candidates were:
- `scifi-toon`: a vector engine with a matrix stack, flat shading and parametric eyes and hands, built for dialogue-driven character scenes with reaction close-ups. This is the closest technique.
- `midcentury-toon`: also flat vector, but a scene style built around how-to content with two-plate print offset.
- `pictogram-motion`: disc-headed figures, but beat-locked graphic grids.

Only the engine is borrowed. Its rules (thick boiling outlines, lip-sync, sitcom timing, one palette per world) are not.

Films in this style render at the default 1920x1080 (user decision); the proof frame is drawn at the reference size 1280x720 for a like-for-like comparison.
