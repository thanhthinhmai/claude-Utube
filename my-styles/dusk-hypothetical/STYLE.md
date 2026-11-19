# Dusk Hypothetical — Style Prompt

> Second-person "what would happen if" stories acted by big-headed, dot-eyed 3D toy figures in a busy low-poly world graded to permanent dusk violet, cut every two to three seconds under a narrator who never stops talking.
> References (grammar only): measured from the ten most-viewed films of a set of landscape 3D-animated hypothetical explainers, full length (see EVIDENCE.md). Take the grade, the figure proportions, the crowd and set density, the graphics grammar, the cut rhythm, the voice-first mix and the act structure (STRUCTURE.md); copy none of their characters, hero costume, sets, captions, stories or lines, and never name the source.

## 1. Essence, and what it is not

One glance reads as this style when:
- the whole frame sits in a **violet dusk grade**: dark mid-tones, nothing near white, soft contrast, strong vignette (evidence: `luma_p50` 0.25 (0.22–0.29), `luma_p98` 0.46, `bright_p50` 0.001, `contrast_p50` 0.19);
- the cast are **sphere-headed toy figures**: head ≈ 1/3 of the height, dot eyes, no nose or ears, a hoodie, stick limbs, ball hands (evidence: visual characters #1–2, 10 frames measured 0.32–0.39);
- the frame is **busy**: extras in almost every wide shot, repeated props in grids, warm practical lights as bokeh, three or four depth layers (evidence: visual detail level #1–4, 9);
- shots **change every 2–3 s by hard cut** (≈ 21 cuts/min) and **about every fifth second the place changes** (evidence: shots.json median 2.3 s; `set_change_s_p50` 4.9);
- a **2.04:1 letterbox** sits inside the 16:9 frame (evidence: corrections #13).

Not a flat vector toon (perspective, DOF, no outlines). Not a brick film (no studs, no stepping). Not a keynote or data film: graphics are short inserts and overlays inside a story. Not a lonely art film: a hero alone in an empty room is the exception, not the look.

## 2. Materials & rendering

- three.js perspective scenes. Everything is **matte toy plastic**: flat albedo, soft specular, rounded bevels, no image textures on figures (materials #1). No outlines on sets or props; the hero's head may carry a thin dark contour in close-ups only (corrections #6).
- Surface detail is **geometry, not texture**: plank lines on floors, vent slits on lockers, window grids on façades (30–60 % of windows lit warm), rows of seat blocks, shelf stock in grids (materials #2–3).
- Trees are clusters of dark spheres on a stick; buildings are boxes with an even window grid; cars are rounded boxes (materials #3).
- Faces are flat black decals on the sphere (eyes, lids, brows, mouth), pink blush ovals for some characters; no teeth, no nose (materials #4, characters kit #4).
- **Crowds are instanced copies** of the one figure with randomised hoodie colours and hair shells: 10–30 in a room, 40–100 on bleachers, hundreds in a hall, thousands in a stadium or square down to coloured dots (characters kit #10–11).
- Post chain from `core/three/post.js`: physical DOF focused on the subject (subject sharp in 99 % of shots, about two thirds of the frame sharp, `focused_share_p50` 0.67), bloom on practical lights, grade, vignette. Vignette and bars are screen space; everything else is in the world.
- Graphic inserts are flat cards either on the radial violet void with faint grain or **over the scene itself, defocused and darkened** (the newest films do this most), so cards and scenes share one colour world (graphics #4, corrections #23).

## 3. Colour logic

- Ground is **deep indigo-violet**, mid violet carries walls and skies, the warm side is a **dusty plum-rose**, never clean orange in the shadows (palette #2d2241 30 %, #0f0b17 22 %, #5d414b 17 %, #443964 10 %).
- Shadows go blue-violet, lit sides go warm pink-peach on every head (colour #6). Green stays the weakest channel in violet shots.
- Keep luma between ≈ 0.10 (p2) and ≈ 0.46 (p98); no pure white, no hard black inside the picture.
- Saturation ≈ 0.37 comes from **costumes and practical lights** (lit windows, string lights, lamps, floodlights, phone glow), never from the background (colour #3, #7–8).
- Leaving violet is a story beat, not a second look: about 2/3 of shots are violet, ≈ 12 % warm orange (gym floors, cafés, sunsets), ≈ 4 % green (lockers, fields, card tables), ≈ 3 % white-lilac (clinics, flash scenes). Even then violet walls or sky stay in frame (colour #9–10, set rules #2–4).
- Mood floods for one shot: red-pink for alarm, blue for night or tension, bright lilac for the after-beat (lighting #5).

## 4. Type & subtitles

- On-screen titles: **all caps, 1–5 words, wide tracking**, a classic high-contrast **serif** in cream or pale gold with a soft glow, centred above the subject or at the top of the picture; the title question card uses two lines, the second larger and gold (on-screen text #1–2; the three newest films all use it, corrections #22).
- Numbers sit in **pills**: a dark translucent rounded rectangle, thin light border, cream numerals, optional icon (heart, star, coin) (on-screen text #3).
- **Speech bubbles**: small white rounded box with a tail and dark text beside the speaker's head; they carry every side-character line (on-screen text #4).
- Subtitles live **inside the picture area**, never in the bars; pale cream sans, 34–44 px at 1080p, soft shadow. Reading time: hold ≥ max(1.8 s, speech + 0.6 s); a caption may run across a cut but never jumps position on it.
- Graphic density: ≈ 1.6 full graphic inserts per minute and an overlay (pill, label, bubble, counter) on 30–50 % of scene shots, ≈ 6–10 graphic moments per minute (graphics rules #1–2). Colours: cream text; pink-red for hearts and warnings; green for gains; gold for money and stars.

## 5. Motion quality

- Smooth animation on ones at **60 fps**, like the current reference films (the older 24 fps films were left out, corrections #22); render with `--fps 60`. No stepping, no boil.
- Camera **locked in ≈ 80 % of shots**; moves are slow drifts (median ≈ 16 px/s at 1280 px, sideways twice as often as vertical) or slow push-ins; big tilts and follows of 1.5–3 s are kept for set pieces. No whips, no handheld (motion camera #1–3).
- Figures are **posed**: life comes from lid droops, head tilts, mouth flaps on dialogue. Gestures rise in 0.3–0.6 s then hold; a fall-and-get-up gag takes ≈ 1 s; walks are a simple stride (animation #1–4).
- Objects act short and eased: a lid opens in ≈ 0.4 s, an item lifts with a 0.3 s bloom, a phone tilts to camera in ≈ 1 s (animation #5).
- Graphics pop or fade in within 0.07–0.15 s, bars fill with an ease-out over ≈ 1.3 s, counters roll up and hold (cuts #7, animation #6). Crowds stay frozen or share one tiny idle bob; only the hero acts.

## 6. Camera grammar

Measured on 2,167 labelled shots of ten full films (median, range between films):

| Shot scale | Share | Angle | Share |
|---|---|---|---|
| medium (waist or knees up) | 32 % (14–39) | eye level | 74 % (57–98) |
| wide (whole figure and place) | 25 % (16–44) | high, looking down | 12 % (0–14) |
| close-up (head and shoulders) | 22 % (6–38) | over the shoulder | 9 % (0–24) |
| huge wide (figure under 1/4) | 13 % (9–28) | low | 3 % (0–6) |
| extreme close-up | 6 % (3–15) | straight down | 1 % (0–2) |

- The scale changes in **68 % (59–78)** of cuts; runs of the same scale stop at about **5** (3–11). Cuts across three steps (ecu ↔ huge) are rare (4–8 %). Core units: wide → med → med, med → med → cu, cu → wide → cu.
- Shot length: median ≈ 2.3 s, 90 % between 1 and 6 s; ecu ≈ 1.8 s, insert ≈ 4.5 s. Holds over 10 s only for a dialogue two-shot or a narrated list.
- **About 30 places per film** (18–49); a visit lasts ≈ 5 s and 56 % of visits are one shot; 60 % of place changes return to a place already seen, ≈ 20 s later (a home set intercut with one-shot vignettes). A new place opens on a wide, huge or medium shot, almost never a close-up.
- Reaction close-ups: ≈ 1 in 3 in-place cuts goes to a face, ≈ 1.8 s after a place starts.
- Inserts (≈ 8 % of shots) are single shots that often bridge to a new place.

| Move | What it expresses | Can serve |
|---|---|---|
| Medium on the hero, eye level, locked | the viewer living the premise | most narration; an explanation; a bet |
| Wide of the place full of extras | where "you" are and who is watching | a new place; a consequence; a crowd's reaction |
| Close-up on a face | the viewer's own reaction | a realisation; a temptation; a joke landing |
| Huge wide, figure a dot among thousands | consequence at scale | going public; a city or world reacting; loneliness |
| Over the shoulder, blurred head, bubble on the speaker | another person talking to "you" | a dare; a plea; a verdict |
| Flat card in the violet void | a fact from the real world | a number; a comparison; a rule |

Framing: subject centre or centre-right and in focus; the hero is often small in a big symmetric space to sell scale. Text stays in the picture area. Transitions: hard cuts; a ≈ 0.15 s light-streak swap for a costume or state change; at most two short fades to black per film to close an act. No dissolves, wipes or slides.

## 7. Sound palette

- **Voice-first, wall to wall**: one narrator from frame 0 to the last 0.3 s, ≈ 3.8 words per voiced second, no gap between words longer than ≈ 1.3 s, no slowdown at the climax (sound #3–4). Voice character is the channel's; never imitate a real person.
- A **continuous bed** fills every pause (pauses ≈ 26 % of runtime, measured silence ≈ 0), no swells.
- Foley on story actions: impacts, whooshes on pops, a glow sound on reveals, UI ticks on counters, crowd murmurs and cheers under crowd shots.
- Master at **−14 LUFS**, loudness range 2.5–3.7 LU, bed ducked under the voice.
- Energy comes from **short sentences** (median 6 words), numbers restated as running counters and fragments used as beat stamps, not from speeding up.

## 8. Native moves

- **Crowd scale.** Cut from a face to a high wide where the same figure stands among hundreds or thousands of frozen copies. *Fits content like:* going viral; a stadium watching; a population number.
- **Running counter.** A pill counter ticks inside held shots and is restated at each beat. *Fits content like:* money; followers; heart rate; seconds left.
- **The rule card.** Two or three short gold caps lines on the violet void. *Fits content like:* a power's limits; the terms of a bet; a law of a strange world.
- **Fact aside.** A 2–5 s flat insert (globe, chart, ratio row of tiny figures, board) for one real number, then back to the story. *Fits content like:* the science behind the premise; odds; a historical comparison.
- **Bubble dialogue.** OTS shot / reverse shot with a white bubble on each line. *Fits content like:* a dare; a friend's doubt; an official's verdict.
- **Corner HUD.** A game-like panel (dark glass, thin teal or gold border, small caps rows, a lock icon on rows not yet unlocked) held in a corner for a whole act and updated as the power changes. *Fits content like:* a list of unlocked abilities; a live viewer count; a rank ladder.
- **Explainer diagram.** Over the defocused scene: a flat 2D figure icon beside a gauge, a two-bar "normal vs you" chart or a dotted arc plan, built up piece by piece. *Fits content like:* how the power works; strength used; the plan before the shot.
- **Light-streak swap.** A bright 0.15 s smear and the figure pops into a new costume or state. *Fits content like:* a transformation; a time skip; a new job.
- **Closing choice card.** Question at the top, two icon tiles, the episode's cast as a row of small figures along the bottom. *Fits content like:* "would you take it"; a vote; a comment prompt.

## 9. Pitfalls of the medium

- **Empty frames.** A hero alone on a bare floor reads cheap: fill wide shots with extras, grids of props and at least one practical light.
- **Mush in the dark.** Violet on violet loses the subject: keep the hero's head the brightest large shape, separate with DOF and rim light.
- **Clean daylight creeping in.** Default three.js lights look neutral; grade toward violet and keep warm only in practicals.
- **Uncanny faces.** A nose, ears, teeth or lip-sync break the figure; act with eyes, lids, brows and mouth decals.
- **Long holds.** Shots over ≈ 6 s go dead unless they are dialogue or a narrated list; split with a reaction or an insert.
- **Busy crowds.** Animating every extra fights the hero; freeze them or share one tiny cycle.
- **Text in the bars.** Captions in the letterbox look like a bug.

## 10. Engine

**Use the film kit:** [`kit/`](kit/) (specs/022) holds the jointed figures, crowds to thousands, eight sets, camera placements, graphics and the grade that passed the proof frame (`kit/GRADE.md`). Copy it into the film with `sh bin/studio kit use <film>`, write a scene table and call `film({scenes})`; the names a scene may use are in `kit/catalog.json`, the catalogue page is `kit/catalog.html`. Write new figures, lights or graphics only for a `custom:` set, from `kit/sets/parts.js`.

Read this style's own demo first: [`DEMO.md`](DEMO.md) and [`demo/`](demo/) (`index.html`: figure, sets, post settings, a shot plan following §6; `mix.py`: the voice-first mix). Then the three.js contract of the library (`TECHNIQUE.md` §2), taking the perspective camera, rig and DOF approach of `brick-toy` but replacing bricks with smooth primitives. Post: `makePost(renderer, scene, camera, w, h, { ssaa: 2, ao: true })` from `/core/three/post.js`; helpers `eio`/`eo`/`ss` and `mulberry` from `/core/lib.js`.

Minimal recipe (not from any demo): `figure({hoodie, hair, eyes})` = `SphereGeometry` head (≈ 1/3 of the height) on a thin neck, rounded-box hoodie torso, `CapsuleGeometry` limbs, sphere hands, flat black decals 1 mm above the head; `crowd(n, seed)` = `InstancedMesh` copies of that figure with `mulberry`-random hoodie colours, placed in rows; a room = floor + walls + one repeated prop grid (desks, lockers, seats) + a lit window grid; warm pink key from one side, violet hemisphere fill, one practical light with bloom; grade to §3, vignette ≈ 0.5, draw the 2.04:1 bars last.

## 11. Variation space

Every film follows the act structure in [`STRUCTURE.md`](STRUCTURE.md) (the channel chose on 2026-11-13 to keep the reference structure). The film decides its premise, hero costume, cast, places, the gains and the cost, the planted detail the climax pays off, the facts, the accent hue and which native moves it spends. The range inside that structure:
- **Structures:** the standard climb (personal gain → public scale → cost → crisis); the explainer-led variant (a longer premise explainer at 8–17 % before the gains); the compressed 6-minute variant (one gains block, one crisis).
- **Openings:** a live demo of the power with a small cash bet; a rescue or crisis already under way; an arrival before a silent crowd.
- **Endings:** a sacrifice that saves someone, a verdict line, a callback to the opening place, then a sting; a quiet reversal where the power passes to someone else; a choice handed to the viewer on the closing card.

---

How our demo was made (story, shots, score, end card, build): [DEMO.md](DEMO.md). Read it after your treatment exists.
