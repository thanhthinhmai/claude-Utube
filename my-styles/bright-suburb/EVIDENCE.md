# Evidence

Set: 12 landscape videos (1280×720, 30 fps, 10.7–20 min each), five 30–60 s windows measured per video (2160 s in all), plus a transcript of the last 20 % of each video for the ending. Three independent analysis reports (visual, motion-depth, sound-script) and a cross-check against the numbers and sheets.

## Key numbers

| Metric | Median | Range | Source |
|---|---|---|---|
| luma p50 | 0.528 | 0.443–0.575 | summary.json |
| contrast p50 | 0.192 | 0.166–0.229 | summary.json |
| saturation p50 | 0.206 | 0.137–0.261 | summary.json |
| shots per minute (shots.json) | ≈ 19–21 | 18–22.3 | v*/shots.json |
| median shot length | 2.77 s | — | v*/craft.json (n=753) |
| camera push / still / follow / pull / drift | 61.8 / 18.9 / 13.8 / 4.0 / 1.6 % | — | v*/craft.json |
| push speed | 1.67 %/s | 9 % > 5 %/s | v*/craft.json |
| scale medium / wide / huge / close / extreme close | 44.5 / 31 / 11.6 / 5.3 / 3.6 % | — | summary.json → shot grammar |
| angle eye / high / ots / low / top | 82.3 / 6.7 / 5.7 / 1.7 / 0.8 % | — | summary.json |
| scale change between shots | 64.6 % | 52–77 % | summary.json |
| longest same-scale run | 5 | 3–9 | summary.json |
| frame in focus | 79 % | 58–83 % | summary.json |
| subject sharp | 100 % | 96.5–100 % | summary.json |
| foreground blur | 8 % | 2–29 % | summary.json |
| sets per film | 14.5 | 10–20 | summary.json |
| home-set share | 25.8 % | 13–48 % | summary.json |
| loudness | −13.8 LUFS | −14.1 to −13.5 | summary.json |
| loudness range | 3.55 LU | 2.9–4.3 | summary.json |
| speech rate (speaking) | 3.57 words/s | 3.04–3.64 | summary.json |
| first voice | 0.0 s | 0.0 | summary.json |
| music under voice | 94 % of windows | 72–100 % | v*/sound.json |
| confident SFX | 12–13 /min | v01–v04 | v*/sfx.json |
| closer question start | 4.9 s before end | 4.3–6.2 s (8 videos) | v*/words-end.json |

## Report summaries

- **Visual.** One universal sphere-head rig, yellow hero, colour-coded cast, instanced crowds; 19 set types, one home set per film; toon-shaded 3D with thin outlines (corrected, #9), glossy heads, warm off-white ground, blue-violet near-ink; graphics in the room (neon labels, bubbles, pops, phone and paper inserts, infographic panels).
- **Motion-depth.** Most shots are slow eased centred pushes; hard cuts ~every 3 s; one action per shot with constant eye life; frozen crowds; mostly deep focus with prop close-ups shallow.
- **Sound-script.** Voice from frame 0, fast steady second-person narration, steady music bed, literal spot effects; seven-part structure with a fixed beat grid (see STRUCTURE.md).

## Corrections log

| # | Before | After | Evidence | Found by |
|---|---|---|---|---|
| 1 | Camera is mostly still (`still_ratio` 0.796, `motion720_p50` 0.15) | Camera is still in only 18.9 % of shots; 61.8 % are slow centred pushes (median 1.67 %/s zoom). Frame-slide metrics miss centred zooms | v*/craft.json → shots[].cam.type (n=753) | numbers |
| 2 | Cut rate 5.2/min, median shot 5.6 s | ≈ 19–21 cuts/min, median shot 2.77 s; video.json cuts miss same-set cuts | v*/shots.json, v*/craft.json | numbers |
| 3 | shots.json covers the whole video | It covers the five measured windows only (753/753 shots inside `segments`) | t0 vs segments | numbers |
| 4 | ~80 % of shots are indoors | Indoor share depends on the premise (≈ 90 %+ in single-building films, ≈ 60 % in road-heavy films); the home set decides | v*/shots.json → place; v11_shots_1#S033–S047 | both |
| 5 | 16 cross-dissolves | 16 of 18 are window-join artifacts; hard cuts only, dissolves only into archive inserts | video.json → soft_transitions vs segments | numbers |
| 6 | Hero = bald dark head + yellow hoodie | The constant is yellow (hoodie or yellow-toned uniform); hair varies | v06_shots_1#S003, v07 | sheets |
| 7 | Ending is probably a callback (low) | Measured on last-20 % transcripts: quiet coda, time jumps, home scene, motif returns, premise question as the last sentence ≈ 4.9 s before the end | v*/words-end.json | numbers |
| 8 | Set changes faster than shots | The labeller splits one room into sub-sets; one set is held for 2–6 shots at changing scales | v*/shots.json → place runs | both |
| 9 | Soft 3D, no outlines (visual §2) | Thin even dark outlines on every figure, prop and set edge; flat fills with one soft gradient; toon-shaded 3D rooms | proof/out/ref.jpg (v09 53.2 s, full size), v01 150 s, v06 20 s, v11 420 s full-size frames; sheets are too small to show the line | sheets |

## Why based_on = memphis-diorama

The reference is toon-shaded 3D: perspective rooms with a thin outline on every edge and flat fills. Of the library styles, memphis-diorama has the closest technique: three.js with a normal-and-depth outline pass and a flat material. Only that technique is taken; its colour, pattern, frame and diorama rules are not. brick-toy (glossy plastic, no line) was first chosen and dropped after the cross-check found the outlines (#9); scifi-toon (flat vector, boiling line) was rejected because these rooms are true 3D. In the studio the film itself is built with the After Effects sphere-head rigs and Blender rooms with a line-art pass (§10).

- 2026-11-28 correction #10: proportions re-measured in pixels (analysis/rig-measure.md); adults 3.16 heads, not 4.5; capsule limbs; head without outline. STYLE §1 and §10 updated (rig ball@3).
