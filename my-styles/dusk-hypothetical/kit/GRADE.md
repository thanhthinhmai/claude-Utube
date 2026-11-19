# Grade of the Dusk Hypothetical kit (v3, specs/027)

The default numbers of `stage.js`. Do not change a default to fix one scene: nudge that scene (`grade: {exposure, saturation}` in the scene table, within the limits below) or pick a mood.

**Target (specs/027 R8, `EVIDENCE.md` → "Brightness inside the picture"):** inside the picture (letterbox bars cut), the reference's 3D shots have luma p50 **0.327** (p25–p75 0.253–0.403) and saturation p50 **0.360** (0.293–0.458). The 023 grade read 0.242 on the same measure: too dark. v3 reads **0.354 / 0.387** on the 22 wide and medium shots of the eleven sets (`films/kit-sets`, 2026-11-19).

| Setting | Default | Checked against | What it fixes |
|---|---|---|---|
| Tone mapping | ACES filmic, exposure 0.80 × `expMul` 0.80 | luma p50 0.354 vs 0.327 (three rounds: × 1.16 → 0.439, × 0.9 → 0.380, × 0.8 → 0.354) | v2 trial ×1.16 was too bright on the outdoor sets |
| Background / fog | `#d9a6c8` / `#c9a0c4`, 6–34 m (sets set their own near/far) | the reference's far planes are light warm haze, not dark violet (v2 trial board) | far ends of rooms went dark violet |
| Saturation (post) | 0.62 × 1.22 | saturation p50 0.387 vs 0.360 | v2 sets read 0.30, washed out |
| Contrast / vignette | 0.12 / 0.20 | — (kept near the 023 look) | corners and mush in the dark |
| Bloom | 0.38, threshold 0.85, radius 0.7 | lamps and lit windows glow, faces do not | — |
| Warm cast | 0.35 | the reference's peach light | — |
| Fill and front light | hemisphere 45 %, front 60 % toward white | faces near white in the light, lilac only in shade (reference cells) | lilac faces |
| Ambient occlusion | GTAO amount 0.6, radius 0.35, scale 2, **8 samples** | 16 samples cost 63 ms a frame at 1080p (+54 % a minute at 60 fps, over SC-006); 8 samples cost 14 ms (≈ +12 %) | no soft shadow where things meet |
| Depth of field | focus on the subject, aperture 4.5, max blur 14 px | round 9 of the 023 proof | — |
| Key shadow | 0.25 | 023 round 4 | — |

`?ao=0` in the page's address turns AO off (timing runs only).

Moods (one shot each): `alarm` red-pink, `night` blue, `lilac` bright after-beat; each multiplies exposure by 0.95–1.05 and saturation by 0.95–1.06.

Set nudges (inside 0.6–1.0, before `expMul`): `gym` 0.60, `street` 0.70, `stadium` 0.64, the outdoor dusk sets `court` 0.60, `rooftop`, `parking`, `street-dusk` 0.66. Per-scene nudge: `exposure` replaces the exposure (0.6–1.0); `saturation` multiplies the post saturation (0.85–1.15).

Sky: outdoor sets carry their own `skyDome` (lilac overhead, warm horizon, a sun disc); rooms with windows have `sunBeam` shafts and `windowGlow` panes (`sets/parts.js`).
