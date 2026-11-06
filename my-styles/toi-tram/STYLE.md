# Quiet Night — Style Prompt

> Small everyday dramas acted by flat-black, round-headed figures with white dot eyes, in muted, vignetted 2D vector rooms. Dialogue lives in soft rounded captions beside the speaker's head, and the film's thesis arrives as one serif-italic line on black.
> References (grammar only): limited-animation web shorts about relationships and work; silent-film intertitles (the thesis card); phone-screen storytelling (UI as plot). Learn the grammar, never copy any character, layout, wording or music.

Evidence keys: `S.` = `summary.json → by_orientation.landscape.metrics`, `vNN` = `profile/vNN/…`, `C#` = row in the corrections log (EVIDENCE.md).

## 1. Essence, and what it is not

- **Black silhouettes with two white dots.** Every character has pure flat-black skin and a near-spherical head, stands about 3 heads tall, and has stick limbs and mitten hands. Identity comes from one clothing block, a hair mass and one saturated accessory. (evidence: 12 head/height measurements, median 0.33; v02_0056#0, v04_0083#0, v05 full-res 40 s)
- **Low-key, muted, vignetted.** The median frame is about 30 % luma, saturation is low, whites are never clipped, and the corners fall to about half the centre's brightness. (evidence: S.luma_p50 0.303, S.sat_p50 0.175, S.bright_p50 0, derived corner/centre 0.36–0.56)
- **Captions are characters' voices.** Short rounded-sans lines float next to the speaker's head. There is no subtitle bar. (evidence: all 5 videos; C#3)
- **Calm, locked staging.** About 5 cuts a minute, no flashes, and the frame is still about 78 % of the time. (evidence: S.cuts_per_min 5.0, S.flashes_per_min 0, S.still_ratio 0.78)
- **A music bed that never stops** under quiet, wordless or near-wordless acting. (evidence: S.silence_per_min 0)

Not a stick-figure explainer: no pointer, numbers or diagram logic, and every frame is a lit, furnished room. Not pictogram motion: no beat-locked graphic grid. Not a sitcom toon: no thick outline, no lip-sync, no gag timing. Not 3D: everything is flat 2D shapes with gradients (C#1).

## 2. Materials & rendering

- **Flat vector shapes + soft gradients.** Sets are hand-drawn in perspective from flat fills, with gentle linear or radial gradients on walls and floors. There is no specular light, grain or paper texture. (evidence: C#1; v01_0002#0, v03_0041#0)
- **Depth by blur, in three layers:** an optional out-of-focus dark foreground silhouette at the frame edge, a sharp subject, and a Gaussian-blurred background (blur ≈ 4–10 px at 1080p). Practical lights in a blurred background become soft bokeh discs. (evidence: motion Depth 2–3; v04_0074#22, v05_0023)
- **Character skin is a pure black fill** (#0b0b0e class), never shaded by scene light. Light reads only on clothes and through a **pale rim of 1–2 px** (white to light grey, 60–90 % opacity) drawn around the silhouette, which is stronger on dark grounds. (evidence: visual Outlines 2–3; v05 full-res 40 s)
- **No black contours.** Props may carry a thin, soft edge line one tone darker than their fill. (evidence: C#2)
- **Faces:** two small white dot eyes, placed mid-low and wide apart on the sphere. Optional thin white brow and lid arcs carry all emotion. There is no mouth or only a tiny line. Glasses are white rings. (evidence: visual Characters 4)
- **Screen-space passes, in this order:** background blur → vignette (radial, corners ≈ 0.4–0.55 × centre luma) → optional faint haze on bright windows in day exteriors. The vignette is never off. (evidence: visual Lighting 3, 6)

## 3. Colour logic

- About 80 % of the frame is near-neutral, slightly cool grey (b* −2 to −4). One or two warm materials (brown wood, tan or amber) are the only broad hues. (evidence: palette #4d504f, #2b2c31, #7f8681, #48362d, #c0a67b)
- **Saturation is reserved for small accents:** a bandana, a hair bow, a hi-vis vest, a single prop. Keep frame saturation p50 ≤ 0.20 and accents ≤ 0.5. (evidence: S.sat_p50 0.108–0.200; vNN video.json sat.p98 0.34–0.48)
- **Values:** keep p98 luma ≤ 0.62, so even "sunny" scenes stay pastel and dusty. True black is allowed (characters, cards, night) but not required in daylight films. (evidence: S.luma_p98 0.568, max 0.609; v01 luma.p2 0.159)
- **The brightest clean white in a shot is a screen or UI card**, and it is the focal highlight. (evidence: visual Colour 8)
- **Light follows mood:** tension and loneliness play in blue-night or dim, desaturated interiors; resolution moves into warm practical light (lamps, string lights, golden hour). Highlights are warmer than shadows in warm scenes (R−B ≈ +15 vs ≈ 0). (evidence: visual Lighting 4, Colour 7)
- *Example palette only:* ground #4d504f / #2b2c31 / #7f8681, wood #48362d, warm light #c0a67b, skin #0e0e11, accent one of #c8463c / #e6c84a / #e98aa8.

## 4. Type & subtitles

Four text families, all overlaid in screen space (fixed, never riding a camera move; motion Text 2):

1. **Speech tags (the main voice).** Fredoka 600–700 (OFL, `core/fonts`), sentence case, cap height 4–4.5 % of frame height, 1–2 lines, 2–10 words, centred. Fill is off-white #f3efe6 by default, or a pale tint per speaker (pale pink, pale blue) with a soft coloured glow. Behind the glyphs sits a **feathered dark smudge** (black at 35–55 %, blur ≈ 1 × cap height), not a hard pill. Place the tag just above or beside the speaker's head, never in a bottom bar. Fade in over 2–3 frames, hold until the next line, fade out over 3–5 frames. Two tags may stack when a reply overlaps. (evidence: C#3, C#4, C#5; v04_0009#29)
2. **Thesis / chapter cards.** IM Fell English Italic, warm off-white #e8e2d4, on pure black (or on a shot darkened to ≤ 15 % luma). One centred line, or up to 3, sitting 2–5 % above the vertical middle, with cap height ≈ 4.5 %. A dimmer attribution line may follow 0.5–1 s later. Fade ≈ 0.3 s, hold 4–6 s, at most 1–2 per film. (evidence: C#10; visual Text 7–9)
3. **Time and place stamps.** Large bold rounded numerals (Fredoka 700, ≈ 14 % of height) with a tiny suffix, upper area, fading in over 4–8 frames. They may tick fast to compress time. (evidence: visual Text 10; v04_0014#27–59)
4. **UI overlays.** White rounded-rectangle chips with tiny dark sans text and a count badge, stacked 2–4 high beside a head (thought or notification UI). Phone threads build bubble by bubble; typed lines reveal letter by letter. (evidence: v05 full-res 40 s; motion Text 4)

Ambient chatter is 3–6 small tags at once, tinted orange or amber, scattered round a character. (evidence: visual Text 5)
Reading time: hold ≥ max(1.8 s, speech + 0.6 s). Captions may outlast their spoken line. (evidence: sound 28)

## 5. Motion quality

- **30 fps**, with smooth camera moves. Characters animate economically: in dialogue the body holds still for seconds while one gesture, head tilt or eye/brow change plays. There is no lip-sync. (evidence: motion Character 1–2)
- Full-body action (walks, jumps, crowds) is kept for wide shots. (evidence: motion Character 3)
- **Easing:** soft in-out on every gesture. UI elements pop with a small ease-out overshoot (≤ 6 %). Shots scaling up from a small rectangle ease out over ≈ 0.6 s. (evidence: motion Transitions 5)
- **What never moves:** the overlay text once it has landed; dialogue backgrounds.

## 6. Camera grammar

| Move | What it expresses | Can serve |
|---|---|---|
| Locked frame (the default; ~78 % of frames) | observation, patience, letting a silence play | a dialogue; a decision; a reaction |
| Slow lateral follow-pan, 20–55 px/s at 720p scale | going somewhere, routine | a commute; a walk-and-talk; a montage of days |
| Slow drift while the image dims | time slipping, mood falling | the end of a day; leaving a place |
| Phone POV insert (hand-held drift only) | private information | a message; a bill; a feed |
| Over-the-shoulder / from behind | what someone is looking at | waiting; longing; a discovery |
| Top-down tabletop insert | an object that matters | a note; a meal; a ticket |

Push-ins and whips are not part of the vocabulary. (evidence: motion Camera 3, 9; Transitions 1)
Framing: waist-up two-shots for dialogue, chest-up singles for reactions, deep one-point wides for places, a small dutch tilt and slightly high angle allowed indoors. A frame-within-a-frame (windscreen, doorway, window) is a strong recurring device. Keep the subject in the brighter centre that the vignette leaves.
Transitions: hard cuts (≈ 5/min, range 2–7); **dip to black** (0.4–0.8 s out, up to 1 s held) for scene breaks; text cards on black; occasional diegetic wipes (doors closing, a shot scaling up from a rectangle). Forbidden: flashes, whip pans, glitch, and spinning or zooming transitions. (evidence: S.cuts_per_min, S.flashes_per_min 0; motion Transitions 3–5)
Shot length is bimodal: inserts last 1–3 s; dialogue and establishing shots 8–30 s (median ≈ 5 s, mean ≈ 9 s). (evidence: S.shot_len_median 5.35, S.shot_len_mean 9.0)

## 7. Sound palette

- **A continuous music bed from frame 0 to the end:** soft piano, felt keys, light guitar or lo-fi pads, gentle and emotional, with no drops to digital silence. (evidence: S.silence_per_min 0; vNN first_voice_t ≈ 0)
- **Mix:** −14 LUFS at delivery. Keep a loudness range of 8–12 LU so swells breathe. The reference sits ≈ −18.6 LUFS, so the relative headroom matters, not the level. (evidence: S.lufs, S.lra 10.4)
- **Voice is optional.** Most films carry dialogue by captions alone. When voiced, it is in-scene character dialogue (no narrator): close, dry and conversational, ≈ 2.5 words/s, lines of 1–7 words (median 3), 0.35–1 s between lines, 1.2–2 s before a key line, and music-only stretches of 6–12 s between dialogue blocks. Captions duplicate the voice. (evidence: C#7, C#8; sound 7, 9, 24, 25)
- **Foley is light and sparse:** soft UI pops or pings for each message bubble, small taps, cups and doors, all tucked under the music. No impacts, no stings.

## 8. Native moves

- **Thesis card.** Cut to black and fade in one serif-italic line that names the film's idea, then return to the scene. *Fits content like:* the moment a habit turns into a problem; a chapter of a biography; the lesson in a workplace story.
- **Phone POV beat.** A mitten hand holds a glowing phone; bubbles stack upward one at a time. *Fits content like:* a rejection email; a bank alert; a group chat going quiet.
- **Notification halo.** 2–4 white UI chips or orange chatter tags appear round a head while the figure freezes. *Fits content like:* burnout; social pressure; a student before exams.
- **Ticking clock stamp.** A large time stamp jumps forward over a locked shot. *Fits content like:* insomnia; waiting for a call; a long shift.
- **Frame-within-frame two-shot.** Hold two figures behind a windscreen or window for 15–30 s while captions change. *Fits content like:* a parent and child talk; a breakup in a car; a reconciliation.
- **Light shift.** The same locked room moves from blue to warm across a cut or dip to black. *Fits content like:* forgiveness; recovery; morning after a crisis.

## 9. Pitfalls of the medium

- **Faces lit like normal skin.** This breaks the look. Keep skin pure black and put emotion in the white eyes, brows and posture.
- **A subtitle bar at the bottom.** Captions belong to the speaker's head. Move each tag with its speaker's screen position (one world→screen function).
- **Hard-edged pill boxes.** Use a feathered smudge instead; a sharp box looks like app UI and fights the UI chips.
- **Too bright or too saturated.** Check p50 luma 0.2–0.45, p98 ≤ 0.62 and sat p50 ≤ 0.2 on stills.
- **No vignette.** The frame then looks like a flat illustration; keep corners ≈ half the centre.
- **Busy camera.** Motion must stay rare and slow; let still frames and captions carry time.
- **Silence gaps in the music.** These read as errors. Duck under voice instead.
- **Black figure on a black ground.** Add the pale rim or lift the background.

## 10. Engine

Built on the **Canvas 2D** contract of the library (`TECHNIQUE.md` §2) and the vector approach of `scifi-toon` (matrix-stack shapes, flat fills, parametric eyes and hands; fetch its demo with `setup.sh demo scifi-toon` to read `toon.js` and `chars.js` as recipes). Drop its boiling thick outline and lip-sync. Helpers from `/core/lib.js`: `eio`/`eo`/`ss` for gestures, `mulberry`/`hash` for seeded crowd placement. Fonts from `/core/fonts/fonts.css`.

Minimal recipe for one frame (not from any demo): draw the set on an offscreen canvas → `ctx.filter = 'blur(6px)'` for the background layer → draw sharp figures (`figure(x, y, h, {shirt, hair, accent, eyes})`: black sphere radius 0.165 h, stick limbs, white dot eyes at 0.55 of head height, then a 1.5 px pale stroke) → vignette with a radial gradient (0 → black 0.55 alpha at the corners) → overlay captions (`tag(text, anchorX, anchorY, t0, t)`: blurred dark ellipse behind Fredoka 600, alpha = ss((t − t0) / 0.08), `ss` takes one argument). Layer order: background, blur, mid props, figures, rim, vignette, text.

## 11. Variation space

Per film, the agent decides the characters (their clothing block, hair and accessory), setting, palette within §3, voiced or caption-only, number of cards and pacing. Structures far from the reference:
- **Structures:** a single locked room seen across seven days; two parallel lives in split time that meet at the end; a list film of five small kindnesses, one per scene.
- **Openings:** a thesis card first, then the scene; a phone POV of a message before any figure is seen; a bright warm morning that will later turn blue.
- **Endings:** an open question left on a black card; a single figure alone in warm light, choosing to stay; a final phone notification, unopened, while the music resolves.
