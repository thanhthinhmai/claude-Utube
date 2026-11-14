# Grade of the Dusk Hypothetical kit

The default numbers of `stage.js`. They are the numbers of the proof frame (`../styleframe/index.html`) that passed `learn compare` on 2026-11-13 after nine rounds. Do not change a default to fix one scene: nudge that scene (`grade: {exposure, saturation}` in the scene table, within the limits below) or pick a mood.

Measured target of the style (`style.json`, `EVIDENCE.md`): median luma **0.26** (range 0.22–0.29), median saturation **0.35** (range 0.32–0.41), very dark area small, shadows blue-violet, lit sides pink-peach.

| Setting | Default | Round of the proof frame | What it fixed |
|---|---|---|---|
| Tone mapping | ACES filmic, exposure 0.80 | 3 | frames too bright and flat next to the reference |
| Background / fog | `#241a36` / `#2a1e40`, 8–24 m | 9 | far end of rooms went black; fog keeps depth violet, not black |
| Vignette amount | 0.26 | 3–4 | corners too bright |
| Saturation (post) | 0.62 | 3–4 | colour too loud: saturation 0.48 → 0.36 |
| Contrast (post) | 0.22 | 4 | mush in the dark |
| Bloom | 0.30 | 4 | practical strips glow without blowing out |
| Depth of field | focus on the subject, aperture 4.5, max blur 14 px | 9 | missing depth: layers behind the subject soft |
| Key shadow intensity | 0.25 | 4 | shadows too hard |
| Hemisphere fill | `#9d84d0` / `#7a5670`, 1.9 | 8 | violet fill, faces lavender not white |
| Key light | `#ffb08a`, 1.8, from behind left | 8 | warm pink key |
| Sun | `#ffa070`, 7, low from behind left, soft shadows | 8 | warm low light across the floor and backs |
| Warm rim | `#ff9e70`, 4.5, from behind | 8 | rim on heads and shoulders instead of a phone light that burnt the face |
| Front fill | `#b896e0`, 4, 4 m in front | 8 | faces readable in medium shots |

Moods (one shot each, STYLE.md lighting #5): `alarm` red-pink, `night` blue, `lilac` bright after-beat. Each multiplies exposure by 0.95–1.05 and saturation by 0.95–1.06.

Per-scene nudge (scene table `grade`): `exposure` replaces the exposure, 0.6–1.0; `saturation` multiplies the post saturation, 0.85–1.15.

Checked: the catalogue page (`catalog.html`), every set in a wide shot with extras, through `qc shots` (results in `specs/022-style-film-kit/quickstart.md`).
