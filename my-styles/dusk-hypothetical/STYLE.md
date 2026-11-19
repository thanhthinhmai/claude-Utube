# Dusk Hypothetical — Style Prompt

> Second-person "what would happen if" stories acted by big-headed, faceless-but-for-dots 3D figures in a soft low-poly world graded to permanent dusk violet, cut fast under a narrator who never stops talking.
> References (grammar only): measured from a set of ten landscape 3D-animated hypothetical explainers (see EVIDENCE.md). Take the grade, the figure proportions, the cut rhythm and the voice-first mix; copy none of their characters, sets, captions, stories or lines, and never name the source.

## 1. Essence, and what it is not

One glance reads as this style when:
- the whole frame sits in a **violet dusk grade**: dark mid-tones, nothing near white, soft contrast, a strong vignette (evidence: `luma_p50` 0.26, `bright_p50` 0.002, `contrast_p50` 0.196, corner/centre luma ≈ 0.53);
- the hero is a **sphere-headed chibi figure** with dot eyes, no nose, no ears, a hoodie and stick limbs (evidence: visual characters #1–3, 10+ frames each);
- the world is **real 3D with the subject always in focus**: about two thirds of the frame is sharp, and about one shot in six has a blurred foreground head or shoulder at one edge (evidence: shot grammar `subject_sharp_share` 1.0, `focused_share_p50` 0.67 (0.50–0.83), `foreground_blur_share` 0.14 (0.08–0.37); corrections #9);
- shots **change every 2–3 s by hard cut** (≈ 21–29 cuts/min), mostly **medium and wide**, and the shot scale changes between most neighbours (evidence: shot grammar, corrections #8, #10);
- a **2.05:1 letterbox** sits inside the 16:9 frame (evidence: corrections #2).

Not a cel toon either: only the hero's head in close-up carries a contour. Not a brick film (no studs, no stop-motion stepping, smooth animation). Not a flat vector toon (true perspective, depth blur, no outlines). Not a keynote or data film: data appears only as short inserts inside a story.

## 2. Materials & rendering

- three.js perspective scenes; sets and props have **no outlines**, separation by value and shading only (evidence: visual outlines #1). Exception: in close-ups the hero's head gets a **thin dark contour** (≈ 2–3 px at 720p, a back-face hull or screen-space edge), dropped in medium and wide shots (evidence: corrections #6).
- All surfaces are smooth **matte low-poly** with soft gradients; no grain, paper or texture maps (materials #1). Heads get a faint satin highlight; cloth stays flat matte (materials #2).
- Facial features are flat black shapes painted on the head (decal or a thin dark mesh just above the surface): dot or ellipse eyes, short brow and lid arcs, a thin mouth curve or none (outlines #2).
- Post chain from `core/three/post.js`: physical DOF focused on the subject, shallow enough to separate layers but never so shallow that the subject softens (at least half of the frame sharp, `focused_share_p50` 0.67; corrections #9), soft bloom only on emissive props, then grade and vignette. Vignette and letterbox are screen-space; everything else is in the world.
- Crowds: instanced copies of the same simplified figure at small scale, mostly frozen (materials #3, character animation #4).
- Data inserts: flat cards, counters, globes or diagrams floating in a dark misty violet void with faint particles (materials #4, backgrounds #3).

## 3. Colour logic

- Ground is **deep indigo-violet**; mid violet carries walls and skies; the warm side is a **dusty rose-brown**, never clean orange (colour #1–2).
- Green is always the weakest channel: grade every shot so mean R and B sit above G (colour #3).
- Keep luma between ≈ 0.12 (p2, excluding bars) and ≈ 0.45 (p98); no pure white, no hard black inside the picture (colour #4–5).
- Saturation moderate (≈ 0.35). Saturated colour is spent on **small props and costumes** (one bright hoodie, a glowing object) against the violet field (colour #6, #8).
- Location changes (green turf, warm wood, night blue) stay pulled toward violet (colour #9). Mood beats may tint the whole frame for one shot: red for anger, magenta for desire, blue for night or screens (lighting #5).
- Example only: ground #271937, mid #493369, haze #796a8c, warm #5a4744, accent hoodie in one saturated hue.

## 4. Type & subtitles

- On-screen titles: **all caps, wide letter-spacing**, warm gold or pale cream with a soft glow, small, at the top of the picture area. Two licence-free faces: a classic serif for rules and labels, a geometric sans for time and place lines (composition #6, corrections #7). Numbers sit in rounded capsules or HUD-like cards.
- Subtitles live **inside the letterbox picture area**, never in the black bars; pale cream sans, 34–44 px at 1080p, soft dark shadow.
- Side-character lines may use a small white speech bubble beside the head (the bubble form only; composition #7).
- Reading time: hold ≥ max(1.8 s, speech + 0.6 s). With 2–3 s shots, a caption may run across a cut but never jumps position on it.

## 5. Motion quality

- Smooth animation on ones at 30 fps; no stepping, no boil.
- Camera locked for most of each shot; when it moves it is a **slow steady push-in** tightening ≈ 10–15 % over 2 s (camera #1–3). No whips, crash zooms or handheld shake (camera #4).
- Only the hero acts: short cycles or single gestures (a kick, a push-up, a head drop) inside a held frame (character animation #3). No lip-sync; mouths hold a shape (character animation #1).
- Acting is in the **eyes and lids**: swap dot eyes ↔ closed lines ↔ squints, tilt brow arcs (character animation #2).
- Secondary motion from props and light: spinning objects, pulsing glows, a ≈ 0.2 s bloom pop on impacts or reveals (transitions #3, character animation #5).
- Graphics pop or scale in, fade in, or tick up as counters; they never slide across the frame (transitions #4).

## 6. Camera grammar

Measured shot by shot on 772 shots of 10 reference videos (median, range between videos; evidence: `shot-sheets/<video>_shots_<n>.jpg#<cell>` of the reference set, see EVIDENCE.md "Shot grammar"):

| Shot scale | Share | Angle | Share |
|---|---|---|---|
| medium (waist or knees up) | 30 % (18–51) | eye level | 73 % (61–81) |
| wide (whole figure and place) | 26 % (13–37) | high, looking down at a slant | 12 % (5–24) |
| huge wide (figure under 1/4 of the frame) | 18 % (10–24) | over the shoulder, blurred foreground | 11 % (3–17) |
| close-up (head and shoulders) | 14 % (6–42) | low, looking up | 3 % (0–8) |
| extreme close-up (part of a face, one object) | 10 % (1–17) | straight down | 1 % (0–5) |

- The scale changes between neighbouring shots in **70 % (57–77 %)** of cuts; never more than **4–8** shots of the same scale in a row.
- About **15 places** per video, the busiest holding a quarter of the shots (26 %, 13–44 %); the place changes every ≈ 4 s.
- Text cards and flat inserts come on top of these shares (≈ 8 % of shots).

| Move | What it expresses | Can serve |
|---|---|---|
| Medium on the hero, eye level, locked | the viewer living the premise | most narration; a reaction; an explanation |
| Wide of the place, slightly high | where "you" are and who is around | a new place; a consequence; a crowd |
| Close-up on the face | the viewer's own reaction; a thought | a realisation; a temptation; a joke landing |
| Huge wide, figure small | consequence at scale | a city or world reacting; loneliness |
| Over-the-shoulder with a blurred foreground head | the other person's view of "you" | a conversation; being watched |
| Flat insert card in the violet void | a fact from the real world | a number; a comparison; a rule of the premise |

Framing: subject centre or centre-right and in focus. Text stays inside the picture area. Transitions: hard cuts only; white flashes ≤ 1/min and only as in-shot camera-flash pops (transitions #1–2). No dissolves, wipes or slides.

## 7. Sound palette

- **Voice-first mix**: one narrator speaks almost continuously from frame 0, ≈ 3.7 words per voiced second (≈ 160 wpm), micro-pauses ≤ 0.8 s only (sound-script loudness #4, voice #2, #4). Voice character is the film's choice; never imitate a real person's voice.
- A **continuous low music bed** fills every gap: no true silence (silence/min ≈ 0) and no swells (LRA ≈ 3 LU) (loudness #2–3, music #1–2).
- Foley on story actions: impacts, whooshes on pops, a glow/ignite sound on reveals, soft UI ticks on counters.
- Master at **−14 LUFS**, heavy compression, bed ducked under the voice.
- Energy comes from **short sentences** (median 5–8 words), not from speeding up (voice #3, script #9).

## 8. Native moves

- **The rule card.** The premise's rules appear as 2–3 short gold all-caps lines on the violet void, one per beat. *Fits content like:* a superpower's limits; a law of a strange world; the terms of a bet.
- **Scale jump.** Cut from an extreme close-up of one face to a top-down wide where the same figure is a dot among thousands of frozen copies. *Fits content like:* going viral; a city-wide effect; a population number.
- **Counter tick.** A number in a capsule ticks up inside a held shot while the hero acts. *Fits content like:* money earned per action; days passing; followers; a countdown.
- **Mood flood.** One shot re-tinted entirely red, magenta or blue, then back. *Fits content like:* anger; a screen at night; danger arriving.
- **Fact aside.** A 2–4 s flat insert (globe, chart, labelled diagram) breaks the story for a real-world fact, then a hard cut back. *Fits content like:* the science behind the premise; a statistic; a historical comparison.

## 9. Pitfalls of the medium

- **Mush in the dark.** Violet on violet loses the subject: keep the hero's head the brightest large shape and use DOF and the vignette to separate it.
- **Clean daylight creeping in.** Default three.js lights look neutral; always grade toward violet and keep G lowest.
- **Uncanny faces.** Adding a nose, ears or lip-sync breaks the figure; act with eyes and brows only.
- **Long holds.** Shots over ≈ 5 s feel dead in this style; split with a reverse angle or an insert.
- **Busy crowds.** Animating every crowd member competes with the hero; freeze them or give them one shared tiny cycle.
- **Text in the bars.** Captions placed in the letterbox look like a bug; keep them in the picture.

## 10. Engine

Read this style's own demo first: [`DEMO.md`](DEMO.md) and [`demo/`](demo/) (`index.html` draws the figure, the sets, the post settings and a shot plan that follows §6; `mix.py` the voice-first mix). Its camera, aperture and surface detail are the ones that passed the studio's shot checks (`demo-checks.json`). Then: built on the three.js contract of the library (`TECHNIQUE.md` §2), taking the perspective-camera, rig and DOF approach of `brick-toy` (fetch its demo with `setup.sh demo brick-toy` to read `actors.js` and `set.js` as recipes) but replacing bricks with smooth primitives. Post: `makePost(renderer, scene, camera, w, h, { ssaa: 2, ao: true })` from `/core/three/post.js` for DOF, bloom, grade and vignette; helpers `eio`/`eo`/`ss` and `mulberry` from `/core/lib.js`.

Minimal recipe (not from any demo): `figure({hoodie, cap, eyes})` = `SphereGeometry` head (radius 0.2 of height) on a short neck, a rounded-box hoodie torso, `CapsuleGeometry` arms and legs, sphere mitten hands, flat black eye and brow meshes 1 mm above the head; set floor + two boxes as a room; key `DirectionalLight` warm pink from one side, violet `HemisphereLight` fill; focus on the subject with an aperture that keeps it and about half of the frame sharp (§2; `brick-toy`'s macro-desk depth of field is far shallower and is not this style's); grade to the palette in §3, vignette corners to ≈ 0.5, draw the 2.05:1 bars last.

## 11. Variation space

The film decides its premise, characters, sets, opening, ending, beat count, accent hue and where the fact asides fall. The source set always opens mid-triumph in second person and climbs to a life-or-death choice; this style asks for different shapes:
- **Structures:** a day-by-day diary that counts up to one quiet consequence; a two-path split screen comparing "with" and "without" the premise; a ranking of five escalating side effects, smallest to largest.
- **Openings:** a fact card first, then the premise lands on the viewer; an ordinary morning that goes subtly wrong; a question from a side character that the narrator answers.
- **Endings:** the premise quietly switches off and life is better; an open choice handed to the viewer on a rule card; a wide pull-out to the whole planet with one last number.
