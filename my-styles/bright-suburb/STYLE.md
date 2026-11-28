# Bright Suburb Hypothetical — Style Prompt

> Long second-person "what if" stories acted by sphere-headed toy figures in clean, softly lit 3D rooms of an everyday suburb: a yellow-hooded hero, a colour-coded cast, huge instanced crowds, glowing labels floating in the room, and a slow eased push on almost every shot.
> References (grammar only): soft-shaded 3D explainer animation with a single universal character rig; toy-like architectural sets; narrated hypothetical stories. Copy no character, set, line, title or music, and never name a source in a film.

## 1. Essence, and what it is not

- One rig for everyone: a perfect glossy sphere head with no neck, nose or ears on a matte tube body, ball hands, white sneakers [bằng chứng: visual §3.1, §3.7].
- The hero always wears yellow (hoodie, or a yellow-toned version of any uniform); no one else wears yellow [bằng chứng: visual §4.1–4.2; corrections #6].
- Bright, mid-key, low-contrast rooms in full 3D perspective at eye height (luma p50 0.53, contrast 0.19, saturation 0.21) [bằng chứng: summary.json → luma_p50, contrast_p50, sat_p50, angle_eye 0.82].
- A slow centred push-in on most shots, hard cuts about every 3 s [bằng chứng: corrections.md → #1, #2].
- Graphics live in the room: floating neon labels, word-by-word speech bubbles, inserts of phones and paper [bằng chứng: visual §6.1–6.8].
- **Not** a dark mood piece (no night-violet grade over the whole film: night is a scene, not the look), **not** a flat side-on 2D cartoon (rooms are real perspective), **not** a glossy photoreal 3D render (thin outlines, flat fills), **not** a brick or clay toy film (no studs, no stop-motion stepping) [bằng chứng: proof/out/ref.jpg; v09_shots_1.jpg#S019; corrections #9].

## 2. Materials & rendering

- Toon-shaded 3D: every figure, prop and set edge has a thin, even, dark outline (≈ 1.5–2 px at 720p, a darker shade of the fill, not pure dark); fills are flat colour with one soft gradient for form; heads have a glossy rim and one small highlight [bằng chứng: v09_shots_1.jpg#S019, v01_shots_1.jpg#S023, v11_shots_1.jpg#S040; corrections #9].
- Soft, even key with warm light and cool shadows; contact shadows under feet; a strong soft vignette darkens every corner [bằng chứng: visual §1–2].
- Faces are 2D marks on the sphere (white eyes with small dark pupils ≈ 0.25–0.3 of head width each; thin white/pink brows and mouth; pink blush; blue tears), placed off-centre toward the facing direction so ¾ turns read from eye position; from behind the head is a blank ball [bằng chứng: visual §3.3–3.6].
- Proportions: kids and adults ≈ 3.15 heads tall (2.95–3.35), toddlers ≈ 2.1; heads stay the same size; adults have a wider (0.67 vs 0.56 head width) and longer torso. Limbs are straight capsules (arm ≈ 0.20, leg ≈ 0.22 head width) with a hard darker band on the screen-right side, no ball joints, no neck; the head has no dark outline, only a brown-grey rim [bằng chứng: rig-measure.json → figures (20 figures, 15 frames, 7 videos); corrections #10].
- Identity = hair or hat shell + garment colour; role = costume (suit, scrubs, police navy, jumpsuit) [bằng chứng: visual §3.8, §4.4].
- Depth: about 79 % of the frame in focus, the subject always sharp; shallow focus only on prop close-ups; a blurred foreground head/shoulder in ≈ 8 % of shots; 2–3 layers, often one-point perspective [bằng chứng: summary.json → focused_share_p50 0.79, subject_sharp_share 1.0, foreground_blur_share 0.08; motion-depth §Depth].
- Crowds are instanced copies of the rig varied by 6–8 hoodie hues × head tones × hair shells; at stadium scale they become a dot texture with full figures only in the near rows [bằng chứng: visual §4.6–4.7].

## 3. Colour logic

- Neutral ground: warm off-white walls and floors; darkest value is a blue-violet near-ink (heads, hair), never pure dark; almost no clipped whites or darks [bằng chứng: summary.json → palette #d1cbc5 28 %, #312c3a 18 %; dark_p50 0.001, bright_p50 0.0002].
- Yellow is reserved for the hero. Pink/magenta is reserved for glow graphics (labels, rim glow on the character in focus); purple for inner-voice rings [bằng chứng: visual §4.2–4.3, §6.1–6.3].
- Each film's palette is set by its home set (lockers blue, bank teal + wood, office wood + peach…), at low-to-mid saturation (0.14–0.26) [bằng chứng: visual §5.8; summary.json → sat_p50 range].
- Night scenes shift the whole frame blue-violet but stay readable; stages are navy + gold + red spots; flashbacks go grayscale or sepia [bằng chứng: visual §2; visual §5a "Stage", "Historical"].
- Example palette (example only): wall #d1cbc5, head #312c3a, slate #6b6e7c, hero yellow #f2c230, glow pink #ff4fa3. [xưởng]

## 4. Type & subtitles

- In-world type only: a floating neon label (glowing pink outline letters with a soft halo) to tag who or what matters, held across shots [bằng chứng: visual §6.1].
- Dialogue bubble: white rounded rectangle with a tail, bold dark sans, revealed word by word with the line; shout/inner voice: white scalloped bubble in caps with concentric purple rings round the head [bằng chứng: visual §6.2–6.3].
- Value pop: short bold number, white with purple outline, beside the object; small white time tag top-left for elapsed time [bằng chứng: visual §6.4, §6.9].
- Subtitles: the studio burns a lower subtitle line in a clean bold sans; bubbles and labels must not overlap it [xưởng].
- Reading time: hold any text ≥ max(1.8 s, speech + 0.6 s) [xưởng].
- Fonts: licence-free bold geometric sans (e.g. Nunito/Fredoka for bubbles, Montserrat for numbers) [xưởng].

## 5. Motion quality

- 30 fps, smooth (not stepped) [bằng chứng: video.json → fps 30].
- Each shot carries one clear action (a gesture, prop handling, a walk into depth, a slap, a swing); eyes and blinks keep moving the whole shot — something moves inside a still shot for ≈ 90 % of its length [bằng chứng: motion-depth.md → Character acting].
- Limbs move as stiff tubes; poses are simple and held after the action [bằng chứng: visual §3.9].
- Big body moves come with a still or very slow camera [bằng chứng: motion-depth.md → Character acting].
- Background crowds are frozen; only leads act [bằng chứng: motion-depth.md → Crowd motion].
- Graphics pop in (scale overshoot) and fade out; bubbles reveal word by word [bằng chứng: visual §6.2].

## 6. Camera grammar

Measured shot grammar (per-video medians): medium 44.5 %, wide 31 %, huge 11.6 %, close 5.3 %, extreme close 3.6 %; eye level 82 %, high 6.7 %, over-the-shoulder 5.7 %, low 1.7 %, top 0.8 %; scale changes on 65 % of cuts, mostly one step; longest same-scale run 5 shots [bằng chứng: summary.json → scale_*, angle_*, scale_change_share, longest_same_scale].

| Move | What it expresses | Can serve |
|---|---|---|
| Slow centred 2D push-in (median 1.67 %/s, 0.2–0.3 s ease each end) — 62 % of shots | quiet attention, "keep watching" | a rule being shown; a reaction; a reveal building [bằng chứng: craft.json → cam.type push 0.618, zoom_pct_s median 1.67] |
| Locked frame — 19 % of shots | weight, a big body action | a slap, a fall, a dance, a crowd tableau [bằng chứng: craft.json → still 0.189] |
| Follow / lateral track (with parallax) — 14 % | travel, momentum | a walk down a corridor; a chase; a ride [bằng chứng: craft.json → follow 0.138] |
| Slow pull-back — 4 % | scale, consequence | the crowd grows; the cost spreads [bằng chứng: craft.json → pull 0.04] |
| Fast punch-in (> 5 %/s) — 9 % of pushes | shock, a number landing | a price, an alarm, a stare [bằng chứng: motion-depth.md → push speed] |
| Prop close-up with shallow focus | the one object that matters | a phone message, a ticket, a document [bằng chứng: motion-depth.md → Depth] |

- One set is covered at 2–6 shots of changing scale before moving on [bằng chứng: corrections.md → #8].
- Subjects sit at eye height; heroes in medium shots fill about a third of frame height [bằng chứng: summary.json → angle_eye; visual §5.5].
- Transitions: hard cuts only; dissolves only into archive/flashback inserts [bằng chứng: corrections.md → #5].

## 7. Sound palette

- Narrator: one warm, quick, steady voice in second person present; ≈ 3.6 words/s while speaking, pauses ≈ 0.34 s (in sentence) / 0.52 s (between sentences) / 0.77 s (between beats); first word at 0.0 s [bằng chứng: sound-script.md → #5–#8].
- Character lines: short quotes every 2–4 sentences, shown as bubbles; small vocal reactions (gasps) at voice level [bằng chứng: sound-script.md → #12–#13].
- Music: a light, upbeat mid-tempo bed under ≈ 94 % of the film, well under the voice, no act swells; brief hushes (≈ 0.9 s) before a reveal [bằng chứng: sound-script.md → #4, #14–#16].
- SFX: one literal sound per on-screen action (coins, sneakers, doors, phone clicks, alarm), a ding on each reveal or number, a swish on many cuts; ≈ 12–13 confident effects per minute, ≈ 17 dB under the voice [bằng chứng: sound-script.md → #17–#20].
- Mix: −14 LUFS integrated, loudness range ≈ 3–4 LU, no dead air [bằng chứng: summary.json → lufs −13.8, lra 3.55, silence_per_min 0].

## 8. Native moves

- **Neon tag.** A glowing pink word floats above one figure in a crowd and follows it across shots. *Fits content like:* who holds the secret; the one person who can see the power; the target of a rumour [bằng chứng: visual §6.1].
- **Rim-glow in a crowd.** The character in focus gets a soft pink rim among identical figures. *Fits content like:* the new kid; the only one who noticed; the winner in a stadium [bằng chứng: visual §4.3].
- **One-colour crowd, odd hero.** Everyone in one colour, the hero in yellow. *Fits content like:* inmates, fans, uniformed staff, a choir [bằng chứng: visual §4.8].
- **Gauge or value pop.** A neon meter or number appears next to the hero and climbs. *Fits content like:* luck level, money earned, followers, days left [bằng chứng: visual §6.4–6.5].
- **Phone/paper insert.** Ball hand holds a phone or paper in an extreme close-up. *Fits content like:* a bank alert, a test score, a letter, a viral post [bằng chứng: visual §6.6, §6.8].
- **Clock insert.** A wall or digital clock in its own shot to jump time. *Fits content like:* deadlines, mornings, countdowns [bằng chứng: visual §5.7].
- **Fact cutaway.** A flat navy infographic panel or a grayscale period scene for one real-world fact, then straight back. *Fits content like:* a statistic, a record, a historical case [bằng chứng: sound-script.md → #36–#37].
- **Split screen / grid.** Two panels or a grid of the hero repeated. *Fits content like:* parallel lives; a viral spread; many tries [bằng chứng: visual §6.11].

## 9. Pitfalls of the medium

- Static crowd shots read as dead: give the leads an action and the camera a slow push [bằng chứng: motion-depth.md → Crowd motion].
- "Still camera" numbers lie for zooms: measure pushes per shot, not frame slide [bằng chứng: corrections.md → #1].
- Faces centred on a turned head look pasted: offset the face toward the facing direction [bằng chứng: visual §3.6].
- Outline missing or too thick: a 3D room without the thin line pass reads as another style; keep one even line weight for figures and set [bằng chứng: corrections.md → #9].
- Too dark a grade kills the look: keep luma p50 0.44–0.58 even at night [bằng chứng: summary.json → luma_p50 range].
- Hero lost in a crowd: never give a side character yellow; add rim glow when the crowd is dense [bằng chứng: visual §4.2–4.3].

## 10. Engine

The studio builds this style as an After Effects film (`film.json → engine "ae"`): the shared sphere-head rigs in `tools/ae/kit/` (`CU.who`, `CU.place`, `CU.mate`, `CU.carry`; rig `ball@3` with `age` kid | adult | toddler, built to the measured proportions of this style), Blender rooms from `tools/blender/kit/` (`k.set`, `k.cam`, `k.cast`, `k.crowd`, `k.light`) as plates behind them, the measured 2D eased push from the Camera review, and graphics (labels, bubbles, pops) as AE layers. A minimal start: one Blender `livingroom` or `kitchen` plate, a hero in yellow and two classmates from `CU.mate`, a 1.7 %/s eased push, a pink neon tag over one classmate. For a code-only page (`render(t)`), see the proof page in this style's evidence and the base style's engine (based on memphis-diorama: three.js with a normal-and-depth outline pass and flat materials; take its outline pass and flat shading, none of its colour or pattern rules). In AE, outlines come from the rig strokes and a Blender Freestyle/line-art pass on the rooms.

## 11. Film structure

The channel follows the reference structure: see [STRUCTURE.md](STRUCTURE.md) (acts, time shares, beat grid, ending). Stories, lines, characters and names are always our own [bằng chứng: channels/dusk-hypothetical → decisions 2026-11-13].
