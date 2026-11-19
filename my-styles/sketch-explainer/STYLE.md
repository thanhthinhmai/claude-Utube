# Sketch Explainer — Style Prompt

> Flat, outlined 2D cartoon for business and history explainers: round-headed stick-limbed people act out the story in many small, line-drawn sets while a fast narrator talks; numbers live inside the scene on boards, screens, papers and signs.
> References (grammar only): editorial cartoon strips and newspaper caricature (signature-feature likeness), classroom chalk-talk (the board as a stage), cel animation pose-to-pose acting. Never copy their characters, layouts, typefaces or music, and never name them in the film.

## 1. Essence, and what it is not

- People are the story: one to three characters act in most shots; medium shots are the backbone (47% of shots) [bằng chứng: summary.json → shot_grammar.scale_med 0.4675; visual §Characters 7].
- Every figure: a near-circular head with no neck, a rounded bean torso, single-stroke arms and legs with no hands or feet, a soft ellipse shadow on the floor [bằng chứng: visual §Characters 1–2, checked on 14 frames in 11 videos].
- Solid near-black outline of even weight on everything; flat fills with one shadow tone; no texture [bằng chứng: visual §Outlines 1, §Materials 1].
- Many brief places: about 24 sets in 3 minutes, a new set every ~4.3 s [bằng chứng: shot_grammar.sets 23.5, set_change_s_p50 4.345].
- Something moves inside the frame almost all the time (93% of a shot), pose-to-pose with holds [bằng chứng: motion-depth §4.1].

It is not a whiteboard draw-on (nothing is drawn by a hand), not a motion-graphics slide deck (charts are props in a room, not full-frame slides), not a picture book (no paper grain, no painterly fills) [bằng chứng: visual §Materials 1, §Graphics 4].

## 2. Materials & rendering

- Vector shapes in SVG: stroke `#1a191a`, round caps and joins, never pure `#000` [bằng chứng: summary palette #1a191a 21%].
- Line weight ≈ 0.005 × frame width for a figure in a medium shot, scaled with the figure; set details ≈ half that [bằng chứng: visual §Outlines 2–3 (medium confidence, 960 px scan)].
- Shading: one base fill + one shadow tone of the same hue at 70–85% brightness; heads and hair get a side crescent (a second circle clipped to the head); rooms get one or two large soft shadow shapes [bằng chứng: visual §Lighting 1–3].
- Floor shadow: blurred ellipse at 30–40% opacity under figures and props — the only blur on characters [bằng chứng: visual §Lighting 4].
- Gradients only for sunset skies, a glow behind a key object, and a spotlight cone [bằng chứng: visual §Lighting 5–6, §Colour 5–6].
- Depth in three layers: flat backdrop, mid layer (set dressing and people on a floor line), optional dark foreground silhouette cut by the frame edge; no depth-of-field blur [bằng chứng: motion-depth §6.1–6.3; subject_sharp_share 1.0, foreground_blur_share 0.059].
- Hardware render rule of this studio: filled shapes use lines and Bézier curves only (no arc commands, no `rx` corners) [xưởng].

## 3. Colour logic

- Muted, greyish ground: median saturation 0.12, mid-key brightness 0.46, almost no clipped whites [bằng chứng: sat_p50 0.118, luma_p50 0.461, bright_p50 0.0069].
- Sets are greyer and lower in contrast than the people standing in them [bằng chứng: visual §Sets 1].
- Accents carry meaning only: red = loss, danger, stamps; money green = cash, growth, big money figures; yellow = lamps and highlights [bằng chứng: visual §Colour 7].
- Day sky = one flat pale cyan with outlined white clouds; night = flat navy with small yellow windows; sunset = soft purple-to-orange gradient [bằng chứng: visual §Colour 5–6].
- Extras have white faces; leads and real people get skin tone and hair colour [bằng chứng: visual §Characters 4].
- One overall tint per film (warm wood, cold grey, clinical blue-grey) chosen by the topic [bằng chứng: visual §Colour 8].
- Example palette (example only): ink `#1a191a`, backdrop `#e4e6e7`, greys `#91989a`/`#51575b`, slate `#a9bacb`, navy `#2b303e`, wood `#5b4030` [bằng chứng: summary palette].

## 4. Type & subtitles

- One casual handwritten face for labels, bubbles, numbers and cards (licence-free, e.g. Kalam, OFL); bold caps for newspaper headlines and signs [bằng chứng: visual §Graphics 3] [xưởng: font choice].
- Chapter cards: dark frame, short centred white handwritten title [bằng chứng: visual §Graphics 1]. Studio rule: the card ground is a near-black radial, not pure black, so tier 3 does not flag black frames [xưởng].
- Spoken lines in a scene: white handwritten text beside the speaker or a white outlined bubble with a tail [bằng chứng: visual §Graphics 2].
- Big numbers: large money-green handwritten figure on a card, board or screen, often counting up [bằng chứng: visual §Graphics 5].
- Subtitles are burned in by the studio, kept off the bottom band of drawn text; reading time ≥ max(1.8 s, speech + 0.6 s) [xưởng].

## 5. Motion quality

- Pose-to-pose: arms snap to a new pose and hold; faces change in 1–2 discrete steps (brows, mouth, blink); mouth flaps between 2–3 shapes only while a character speaks [bằng chứng: motion-depth §4.3, action table rows 1–3].
- A new event about every 2.4 s, lasting ~1.25 s, then a hold; the first event starts right after the cut; never a fully frozen character for a whole shot [bằng chứng: motion-depth §4.1–4.2; spans/s 0.41].
- Events per shot: ~1 under 4 s, 2–3 at 6 s and longer [bằng chứng: motion-depth §4.2].
- Pops: cards and labels scale in over ~0.2 s with slight overshoot; text types on; counters tick every frame; charts draw left to right; bars rise [bằng chứng: motion-depth action table].
- Walk-ins with a small bob; rise from behind furniture; symbol pops (!, ?, sweat drops) near the head [bằng chứng: motion-depth action table].
- Backgrounds never boil or wobble; the line is clean and still [bằng chứng: visual §Outlines 1].

## 6. Camera grammar

| Move | What it expresses | Can serve |
|---|---|---|
| slow constant push (1.5–6 %/s, ~7% total) | keeps a held frame alive; attention | a talking character; a number on a board; a close-up reaction |
| pull-out (4–13 %/s, ~25% total) | reveal the whole situation from a detail | a face to the crowd; one coin to the vault; a desk to the building |
| locked frame | reading | screens, documents, inserts |
| lateral follow or slide from set to set | linked places, a walk | a corridor of rooms; a facade into the office; a journey |
| over-the-shoulder | confrontation, being judged | an interview; a hearing; a pitch |

- Shares per shot: push 33%, pull 23%, locked 22% (mostly inserts), follow 10–20%, drift 2% [bằng chứng: craft cam.type pooled; corrections #1–2].
- Linear moves, no ease-in, optional 0.08–0.25 s ease-out; neighbouring shots alternate push and pull [bằng chứng: motion-depth §1.6, §7].
- Scales: medium 47%, wide 19%, very wide 14%, close-up 11%, extreme close-up 3%, plus graphic inserts ~20% of shots; angles: eye 82%, over-the-shoulder 12%, high 3% [bằng chứng: shot_grammar scale_*, angle_*; craft insert 128/628].
- Change scale on ~2/3 of cuts; never more than 4 shots at one scale [bằng chứng: scale_change_share 0.656, longest_same_scale 4].
- Shot length median ~3 s, about 14 cuts/min (8.7–20) [bằng chứng: cuts_per_min, shot_len_median].
- Transitions: hard cuts (95%); a 0.4–0.6 s dissolve only for a time or place jump; a 0.2 s whip at most once or twice per film; no flash cuts [bằng chứng: corrections #4–5; motion-depth §5].

## 7. Sound palette

- One narrator from the first frame, fast and even (≈ 3.5 words per second of speech), tight pauses (0.4 s inside, 0.5 s after a sentence, 0.8 s between paragraphs) [bằng chứng: first_voice_t 0.0; speech_rate 3.532; sound-script §Narration 4].
- Short acted lines by the characters break the narration, each closed by a dry narrator aside [bằng chứng: sound-script §Narration 3 (10/12 videos)].
- A tonal music bed under everything, ≈ 11 dB below the voice, present in the pauses [bằng chứng: sound-script §Music 1–2].
- Effects for actions on screen (pops, stamps, coins, whooshes): a house middle of 10–20 per minute [bằng chứng: corrections #3; sound-script §SFX 2].
- Mix: steady and compressed (LRA ~4). The reference sits near −18 LUFS; the studio delivers −14 LUFS [bằng chứng: lufs −18.2, lra 3.95] [xưởng: −14 LUFS].
- Almost no dead air (under 1 s of silence per minute) [bằng chứng: silence_per_min 0.683].

## 8. Native moves

- **The board scene.** A person stands beside a whiteboard, chalkboard or mounted TV; the chart or number builds while they point. *Fits content like:* a revenue jump; a vote count; a recipe's ratio.
- **The case file.** A paper prop with a photo, clip and red stamp slams in. *Fits content like:* an audit result; a lawsuit; a lab finding.
- **The spotlight.** A dark stage, one soft cone from above on one character. *Fits content like:* a resignation; a verdict; a lonely founder at night.
- **The signature caricature.** A real person read from 2–3 features (hair, glasses, one garment) plus a name plate. *Fits content like:* a change of chief executive; a historic inventor; a politician's decision.
- **The reveal pull.** From one face or object out to the whole room, crowd or city. *Fits content like:* one buyer among millions; one chip in a data centre; one coin in a treasury.
- **Split panels.** Two to four panels with dark gutters compare people or places. *Fits content like:* two rivals; then and now; three markets.
- **Thought bubble with a picture.** Puffs grow into a cloud that holds a small scene. *Fits content like:* a plan; a fear; a memory.

## 9. Pitfalls of the medium

- Wide shots with tiny people everywhere lose the acting → keep medium shots near half of all shots; push in on reactions [bằng chứng: scale_med 0.4675].
- Charts as full-frame slides turn the film into a deck → put the chart on a board, screen or paper in a set, with a person beside it [bằng chứng: visual §Graphics 4].
- One room reused for minutes → rotate sets about every 4 s; build sets from parts [bằng chứng: set_change_s_p50 4.345].
- Frozen figures under a camera push read as a slideshow → schedule an event every ~2.4 s [bằng chứng: motion-depth §4.1].
- Saturated colours everywhere → keep the ground grey and spend red/green only on meaning [bằng chứng: sat_p50 0.118].
- Real people saying invented words → real people react with symbols; spoken words only for generic or invented characters, unless the line is a sourced quote [xưởng].
- Hardware-render fill gaps on arc commands and seams on thick stroked polylines → cubic curves, separate stroke segments [xưởng].

## 10. Engine

Engine based on `halftone-dossier` (SVG DOM, `render(t)`, a character rig with a face interface, stamps), rebuilt as the studio's SVG cartoon kit [xưởng]. Until the kit is packaged under `kit/` (spec to follow), the working code lives in the studio's films: `kit.js` (`makeChar`, `setChar`, poses, expressions, caption, labelArrow, bubble), `cast.js` (cast presets, `bumpy`, `ovalHead`, glasses, hair), `scenes3.js` (`act` scene: sets, boards, signs, bubbles, gestures, close-ups). Minimal example: an `act` shot with one character beside a board — `{set: 'wb', cast: [{w: 'max', x: 1520, pose: 'pointL'}], board: {k: 'num', text: '$5', sub: 'a coffee'}}`.

## 11. Variation space

The agent decides for each film: structure, cast and the real people to caricature (model sheet approved first), opening, ending, set list, camera path, overall tint, music mood. No channel has adopted the reference structure, so pick structures, openings and endings that differ from the reference films [xưởng].

- Three structures: a countdown of five decisions; a trial (charge, evidence, defence, verdict); a single day hour by hour.
- Three openings: an object close-up that pulls out; a question asked by an extra on the pavement; a ledger page that fills in.
- Three endings: the board wiped clean with one number left; the narrator's aside over an empty set; a split panel of then and now.

---

How our demo was made (story, shots, score, end card, build): [DEMO.md](DEMO.md). Read it after your treatment exists.
