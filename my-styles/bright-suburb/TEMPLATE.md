# Template: Bright Suburb Hypothetical

Bộ tham chiếu: whatif-long · 12 video · học ngày 2026-11-28 · luật hình theo 12 phim 3D, nhịp và âm thanh theo 12 phim (tiếng động: 4 phim)

Written in the studio's own words from measurements; no story, line or name of the reference set.

## 1. Khuôn mặt và biểu cảm

Faces are 2D marks on a glossy dark sphere: two big white eyes with small dark pupils, thin white or pink brows and mouth, pink blush, blue tears. Expression comes from lids, brows and pupils, never from deforming the head. The face sits off-centre toward where the figure looks; from behind the head is a blank ball. Eyes stay alive (blinks, pupil shifts) through every shot.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| eye width / head width | 0.25–0.3 | 0.25–0.3 | visual §3.3 (11 frames) |
| head ÷ height (kid) | 0.30 | 0.27–0.31 | visual §3.2 |
| close-up subject centred | 0.964 | 0.964 | template.json → framing.by_scale.cu.middle |

Bằng chứng: v09/strips/S003.jpg#3, v05/strips/S006.jpg#4, v12/strips/S038.jpg#5, v01/strips/S035.jpg#2
Nên làm: offset the face toward the look direction; animate lids and pupils on every shot
Không nên làm: stretch or squash the head; draw a nose, ears or a neck
Trong bộ dựng: rig `ball@1` / `ball@2` face controls via `CU.who`, `CU.mate`

## 2. Thân và trang phục

One rig for all: a matte tube or box torso, stiff tube limbs, ball hands with no fingers, white sneakers. Kids and adults ≈ 3.15 heads tall (2.95–3.35), toddlers ≈ 2.1; head size stays the same, adults have a wider, longer torso (corrections #10). Identity is a hair or hat shell plus garment colour; role is the costume. The hero always wears yellow.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| head ÷ height (adult) | 0.22 | 0.22–0.23 | visual §3.2 |
| cast per film | ≈ 5 | 3–8 | visual §4.5 |

Bằng chứng: v07/strips/S010.jpg#3, v06/strips/S026.jpg#2, v12_shots_1.jpg#S004, v06_shots_1.jpg#S003
Nên làm: change hair, hat and colour to make a new character; keep yellow for the hero
Không nên làm: give anyone but the hero yellow; give hands fingers
Trong bộ dựng: `CU.who` (hero, `ball@2`), `CU.mate` (cast, `ball@1`), `CU.carry` for props in ball hands

## 3. Bố cục theo cỡ cảnh

Medium and wide shots keep the subject in the middle two columns with a small off-centre share; close-ups and inserts are centred. Eye height is the default.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| medium off-centre | 0.161 | 0.161 | template.json → framing.by_scale.med.off_centre |
| wide off-centre | 0.149 | 0.149 | template.json → framing.by_scale.wide.off_centre |
| huge off-centre | 0.178 | 0.178 | template.json → framing.by_scale.huge.off_centre |

Bằng chứng: v01_shots_1.jpg#S002, v11_shots_1.jpg#S026, v06_shots_1.jpg#S005
Nên làm: place the acting pair in the centre half of the frame
Không nên làm: push the subject to a frame edge
Trong bộ dựng: `CU.place`, camera option from the Camera review

## 4. Độ sâu theo cỡ cảnh

Deep focus in wide and huge shots; medium shots are mostly sharp with a blurred foreground head in about one shot in seven; shallow focus belongs to prop close-ups and phone inserts.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| medium in focus | 0.667–0.917 | 0.667–0.917 | template.json → framing.by_scale.med.focused_share |
| medium foreground blur | 0.137 | 0.137 | template.json → framing.by_scale.med.foreground_blur |
| extreme close-up in focus | 0.417–1.0 | 0.417–1.0 | template.json → framing.by_scale.ecu.focused_share |

Bằng chứng: v07_shots_1.jpg#S038, v12_shots_1.jpg#S004, v01_shots_1.jpg#S043, v06_shots_1.jpg#S027
Nên làm: add a soft blurred shoulder in front for over-the-shoulder talks
Không nên làm: blur the subject; shoot wide sets shallow
Trong bộ dựng: Blender `k.cam(dof=…)`, AE camera blur on foreground layers

## 5. Ánh sáng

Soft even key, warm light and cool shadow, a strong soft vignette. Mid-key frames with a narrow tonal range; night is a blue-violet scene grade that stays readable; stages are navy with gold spots.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| raking light share | 0.741 | 0.741 | template.json → light.raking |
| tonal range | 0.403–0.584 | 0.403–0.584 | template.json → light.range |
| luma p50 | 0.528 | 0.443–0.575 | summary.json |

Bằng chứng: v01_shots_1.jpg#S001, v11_shots_1.jpg#S013, v06_shots_1.jpg#S043
Nên làm: keep luma p50 near 0.53 even at night; vignette every shot
Không nên làm: grade the whole film dark; clip darks or whites
Trong bộ dựng: Blender `k.light`, AE look layer in `look.jsx`

## 6. Bối cảnh và đạo cụ kể chuyện

Clean toy-like rooms of an everyday suburb in full 3D: classroom, lockers hallway, kitchen, living room, bedroom, road, stage, stadium. One home set holds about a quarter of the shots and returns every act; 10–20 sets per film. Props are what the place needs, repeated in rows; a clock gets its own insert to jump time.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| sets per film | 14.5 | 10–20 | summary.json |
| home-set share | 0.258 | 0.133–0.484 | summary.json |

Bằng chứng: v01_shots_1.jpg#S023, v11_shots_1.jpg#S034, v06_shots_1.jpg#S020, v10_shots_1.jpg#S024
Nên làm: pick one home set from the premise; cover each set with 2–6 shots at changing scales
Không nên làm: invent grime or clutter; change set on every cut
Trong bộ dựng: Blender `k.set` rooms (classroom, gym, road…), `custom:` sets from kit parts

## 7. Đám đông

Crowds are instanced copies of the rig varied by hoodie hue, head tone and hair shell; at stadium scale a texture of dots. Crowds hold still; leads act. A uniform crowd in one colour makes the yellow hero pop.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| crowd colours | 6–8 | 6–8 | visual §4.6 |
| still-camera person shots with no motion | 0.01 | 0.01 | template.json → motion.person_still_cam_none |

Bằng chứng: v01_shots_1.jpg#S028, v06_shots_1.jpg#S020, v01_shots_2.jpg#S061, v09_shots_1.jpg#S034
Nên làm: freeze the crowd and give the leads one action; add pink rim glow to the focus figure
Không nên làm: animate every crowd figure; put a yellow figure in the crowd
Trong bộ dựng: Blender `k.crowd`, AE glow on the focus layer

## 8. Thẻ số liệu

Numbers live in the room: a bold white number with a purple outline pops beside the object, or a neon gauge climbs over the scene. Fact asides cut to a flat navy infographic panel.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| insert share in scale beat | 0.091 | 0.091 | template.json → beats.scale.insert_share |
| numbers per minute | ≈ 6 | 3–10.7 | sound-script #11 |

Bằng chứng: v07_shots_1.jpg#S024, v08_shots_1.jpg#S002, v11_shots_1.jpg#S011
Nên làm: pop the number next to the thing it counts, hold ≥ 1.8 s
Không nên làm: put a full-screen stat card over a story scene
Trong bộ dựng: AE text layer with overshoot pop (`look.jsx`)

## 9. Thẻ tiêu đề và thẻ câu hỏi cuối

There is no title card and no end card with text: the voice starts at frame 0, and the film closes with the narrator asking the title premise back to the viewer over the last coda shot, about 5 s before the end, then a short music tail.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| closer starts before end | 4.9 s | 4.3–6.2 s | words-end.json (8 films) |
| last word before end | 1.8 s | 1.7–1.9 s | words-end.json |

Bằng chứng: v01_shots_2.jpg#S066, v06_shots_2.jpg#S061
Ít bằng chứng: 2 khung
Nên làm: end on a warm home shot with a slow push while the closer question plays
Không nên làm: add a title card or a text end card
Trong bộ dựng: AE last shot `CU.end`

## 10. Cảnh không khí

Huge establishing shots open a new place: a yard, a road of houses, a stadium; usually high angle, with a slow push or pull.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| huge shots moving | 0.849 | 0.849 | template.json → motion.cam_by_scale.huge.moving |
| huge share | 0.116 | 0.048–0.234 | summary.json |

Bằng chứng: v06_shots_1.jpg#S002, v11_shots_1.jpg#S037, v01_shots_1.jpg#S031
Nên làm: open each new set with one huge or wide shot
Không nên làm: hold an empty establishing shot longer than 4 s
Trong bộ dựng: Blender plate + AE 2D push

## 11. Diễn xuất nhân vật

Each shot has one clear action — a gesture, a prop, a walk into depth, a slap — then a held pose; eyes and blinks never stop. Big moves come with a still or slow camera.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| active share, still-camera person shots | 0.531–1.0 | 0.531–1.0 | template.json → motion.person_still_cam_active |
| first motion after cut (s) | 0.75 | 0.271–1.167 | template.json → motion.rise_s |

Bằng chứng: v12/strips/S038.jpg#5, v07/strips/S010.jpg#3, v06/strips/S026.jpg#4, v05/strips/S006.jpg#2
Nên làm: start the action within 0.3–1.2 s of the cut, then hold
Không nên làm: leave a lead frozen for 2 s or more
Trong bộ dựng: `CU.who` poses, `CU.arc`, `CU.inHand`

## 12. Chuyển động máy

A slow centred eased push on most shots, a locked frame for big actions, lateral follow with parallax for travel, rare pulls.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| medium push share | 0.667 | 0.667 | template.json → motion.cam_by_scale.med.push |
| medium zoom %/s | 0.856–2.698 | 0.856–2.698 | template.json → motion.cam_by_scale.med.zoom_pct_s |
| still ratio | 0.208 | 0.131–0.291 | template.json → motion.still_ratio_p50 |

Bằng chứng: v09/strips/S024.jpg#0, v10/strips/S015.jpg#4, v03/strips/S022.jpg#2
Nên làm: use the Camera review option with a 1–3 %/s eased push
Không nên làm: pan across a static room; zoom fast without a reason
Trong bộ dựng: `camera suggest|choose`, planCam in `CU.end`

## 13. Chuyển cảnh

Hard cuts; a dissolve only into an archive or flashback insert; a swish sound often sits on the cut.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| cut share | 0.9757 | 0.9757 | template.json → transitions.cut |
| fades per film | 0 | 0 | template.json → transitions.fade_max_per_film |

Bằng chứng: v01_shots_1.jpg#S004, v06_shots_1.jpg#S049, v10_shots_1.jpg#S044
Nên làm: cut on the action; dip only on a long time jump
Không nên làm: cross-fade between story scenes
Trong bộ dựng: AE comp order in `ae build`

## 14. Âm thanh

A light upbeat bed under nearly the whole film, well under the voice; one literal spot effect per on-screen action, a ding on reveals, swishes on cuts; short hushes before a reveal. Master −14 LUFS, narrow loudness range.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| music share | 0.962 | 0.962 | template.json → sound.music_share |
| music under voice (dB) | -13.2…-7.9 | -13.2–-7.9 | template.json → sound.music_under_voice_db |
| confident sfx per minute | 11.8–13.4 | 11.8–13.4 | template.json → sound.sfx_per_min |

Bằng chứng: v07/strips/S010.jpg#3, v11/strips/S012.jpg#2, v01/strips/S061.jpg#3
Nên làm: anchor each effect to its motion key; duck the bed under the voice
Không nên làm: leave gaps of silence; let an effect cover a word
Trong bộ dựng: `sound cue add --motion`, `sound mix`, film `mix.py` bed

## 15. Nhịp đọc lời

Fast steady second-person narration from frame 0, short sentences, three pause steps, a pause before each number; character quotes every 2–4 sentences shown as bubbles.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| words per minute (overall) | 144 | 144–180 | template.json → voice.wpm |
| pause between sentences (s) | 0.42–0.56 | 0.42–0.56 | template.json → voice.pause_sent |
| pause before number (s) | 0.52–0.9 | 0.52–0.9 | template.json → voice.pre_number |

Bằng chứng: v11/strips/S012.jpg#4, v03_shots_1.jpg#S003, v09_shots_1.jpg#S020
Nên làm: keep sentences 4–8 words; put a quote bubble every few lines
Không nên làm: slow down for drama; ask the viewer questions before the closer
Trong bộ dựng: `lines.json` + `voice make`, bubble layers in AE

## Công thức nhịp

### hook

cold open, power shown 2–4 times

| Dòng | Giá trị | Nguồn |
|---|---|---|
| độ dài cảnh (p25–p75) | 1.61–3.1 s | template.json → beats.hook.shot_s |
| chuỗi cỡ cảnh hay gặp | wide → med → med; med → med → med; med → med → wide | template.json → beats.hook.top_scales |
| tỉ lệ máy động | 0.844 | template.json → beats.hook.cam_moving |
| diễn xuất | 1.0 of person shots act | template.json → beats.hook.acting |
| đồ hoạ | inserts 0.006; labels, bubbles, pops | template.json → beats.hook.insert_share |
| chuyển cảnh | hard cuts | template.json → transitions.cut |
| tiếng động mỗi phút | 12.5 | template.json → beats.hook.sfx_per_min |
| nhạc | bed on, -10.1 dB under voice, 115–148 BPM | template.json → beats.hook.music_db |
| từ mỗi phút | 138.0 | template.json → beats.hook.wpm |

### explain

one rule sentence + the pivot

| Dòng | Giá trị | Nguồn |
|---|---|---|
| độ dài cảnh (p25–p75) | 2.43–4.13 s | template.json → beats.explain.shot_s |
| chuỗi cỡ cảnh hay gặp | wide → wide → wide; med → wide → wide; med → med → wide | template.json → beats.explain.top_scales |
| tỉ lệ máy động | 0.96 | template.json → beats.explain.cam_moving |
| diễn xuất | 1.0 of person shots act | template.json → beats.explain.acting |
| đồ hoạ | inserts 0.0; labels, bubbles, pops | template.json → beats.explain.insert_share |
| chuyển cảnh | hard cuts | template.json → transitions.cut |
| tiếng động mỗi phút | 12.5 | template.json → beats.explain.sfx_per_min |
| nhạc | bed on, -9.8 dB under voice, 115–148 BPM | template.json → beats.explain.music_db |
| từ mỗi phút | 138.0 | template.json → beats.explain.wpm |

### benefit

upside montage, time-stamp openers

| Dòng | Giá trị | Nguồn |
|---|---|---|
| độ dài cảnh (p25–p75) | 1.98–3.6 s | template.json → beats.benefit.shot_s |
| chuỗi cỡ cảnh hay gặp | med → med → med; wide → med → wide; wide → wide → wide | template.json → beats.benefit.top_scales |
| tỉ lệ máy động | 0.731 | template.json → beats.benefit.cam_moving |
| diễn xuất | 1.0 of person shots act | template.json → beats.benefit.acting |
| đồ hoạ | inserts 0.0; labels, bubbles, pops | template.json → beats.benefit.insert_share |
| chuyển cảnh | hard cuts | template.json → transitions.cut |
| tiếng động mỗi phút | 12.5 | template.json → beats.benefit.sfx_per_min |
| nhạc | bed on, -9.0 dB under voice, 115–148 BPM | template.json → beats.benefit.music_db |
| từ mỗi phút | 150.0 | template.json → beats.benefit.wpm |

### scale

goes public; first fact aside

| Dòng | Giá trị | Nguồn |
|---|---|---|
| độ dài cảnh (p25–p75) | 2.01–3.8 s | template.json → beats.scale.shot_s |
| chuỗi cỡ cảnh hay gặp | wide → wide → med; wide → med → med; med → med → med | template.json → beats.scale.top_scales |
| tỉ lệ máy động | 0.791 | template.json → beats.scale.cam_moving |
| diễn xuất | 1.0 of person shots act | template.json → beats.scale.acting |
| đồ hoạ | inserts 0.091; labels, bubbles, pops | template.json → beats.scale.insert_share |
| chuyển cảnh | hard cuts | template.json → transitions.cut |
| tiếng động mỗi phút | 12.5 | template.json → beats.scale.sfx_per_min |
| nhạc | bed on, -11.0 dB under voice, 115–148 BPM | template.json → beats.scale.music_db |
| từ mỗi phút | 132.0 | template.json → beats.scale.wpm |

### cost

someone else pays

| Dòng | Giá trị | Nguồn |
|---|---|---|
| độ dài cảnh (p25–p75) | 2.25–3.71 s | template.json → beats.cost.shot_s |
| chuỗi cỡ cảnh hay gặp | wide → med → wide; med → med → med; wide → wide → med | template.json → beats.cost.top_scales |
| tỉ lệ máy động | 0.785 | template.json → beats.cost.cam_moving |
| diễn xuất | 0.905 of person shots act | template.json → beats.cost.acting |
| đồ hoạ | inserts 0.047; labels, bubbles, pops | template.json → beats.cost.insert_share |
| chuyển cảnh | hard cuts | template.json → transitions.cut |
| tiếng động mỗi phút | 12.5 | template.json → beats.cost.sfx_per_min |
| nhạc | bed on, -10.8 dB under voice, 115–148 BPM | template.json → beats.cost.music_db |
| từ mỗi phút | 150.0 | template.json → beats.cost.wpm |

### crisis

dark turn and public climax

| Dòng | Giá trị | Nguồn |
|---|---|---|
| độ dài cảnh (p25–p75) | 2.17–3.82 s | template.json → beats.crisis.shot_s |
| chuỗi cỡ cảnh hay gặp | med → med → med; med → med → wide; wide → med → med | template.json → beats.crisis.top_scales |
| tỉ lệ máy động | 0.836 | template.json → beats.crisis.cam_moving |
| diễn xuất | 0.971 of person shots act | template.json → beats.crisis.acting |
| đồ hoạ | inserts 0.038; labels, bubbles, pops | template.json → beats.crisis.insert_share |
| chuyển cảnh | hard cuts | template.json → transitions.cut |
| tiếng động mỗi phút | 12.5 | template.json → beats.crisis.sfx_per_min |
| nhạc | bed on, -11.3 dB under voice, 115–148 BPM | template.json → beats.crisis.music_db |
| từ mỗi phút | 147.0 | template.json → beats.crisis.wpm |

### ending

quiet coda, time jumps, motif returns (not sampled; shot numbers carried over from crisis)

| Dòng | Giá trị | Nguồn |
|---|---|---|
| độ dài cảnh (p25–p75) | 2.17–3.82 s | template.json → beats.ending.shot_s |
| chuỗi cỡ cảnh hay gặp | med → med → wide; wide → med → med; med → wide → wide | template.json → beats.ending.top_scales |
| tỉ lệ máy động | 0.836 | template.json → beats.ending.cam_moving |
| diễn xuất | 0.971 of person shots act | template.json → beats.ending.acting |
| đồ hoạ | inserts 0.0; labels, bubbles, pops | template.json → beats.ending.insert_share |
| chuyển cảnh | hard cuts | template.json → transitions.cut |
| tiếng động mỗi phút | 8.0 | template.json → beats.ending.sfx_per_min |
| nhạc | bed on, -11.3 dB under voice, 115–148 BPM | template.json → beats.ending.music_db |
| từ mỗi phút | 150.0 | template.json → beats.ending.wpm |

### sting

closer question to the viewer (not sampled; shot numbers carried over from crisis)

| Dòng | Giá trị | Nguồn |
|---|---|---|
| độ dài cảnh (p25–p75) | 2.17–3.82 s | template.json → beats.sting.shot_s |
| chuỗi cỡ cảnh hay gặp | med → med → wide; wide → med → med; med → wide → wide | template.json → beats.sting.top_scales |
| tỉ lệ máy động | 0.836 | template.json → beats.sting.cam_moving |
| diễn xuất | 0.971 of person shots act | template.json → beats.sting.acting |
| đồ hoạ | inserts 0.0; labels, bubbles, pops | template.json → beats.sting.insert_share |
| chuyển cảnh | hard cuts | template.json → transitions.cut |
| tiếng động mỗi phút | 8.0 | template.json → beats.sting.sfx_per_min |
| nhạc | bed on, -11.3 dB under voice, 115–148 BPM | template.json → beats.sting.music_db |
| từ mỗi phút | 150.0 | template.json → beats.sting.wpm |

### end-card

music tail, no text (not sampled; shot numbers carried over from crisis)

| Dòng | Giá trị | Nguồn |
|---|---|---|
| độ dài cảnh (p25–p75) | 2.17–3.82 s | template.json → beats.end-card.shot_s |
| chuỗi cỡ cảnh hay gặp | med → med → wide; wide → med → med; med → wide → wide | template.json → beats.end-card.top_scales |
| tỉ lệ máy động | 0.836 | template.json → beats.end-card.cam_moving |
| diễn xuất | 0.971 of person shots act | template.json → beats.end-card.acting |
| đồ hoạ | inserts 0.0; labels, bubbles, pops | template.json → beats.end-card.insert_share |
| chuyển cảnh | hard cuts | template.json → transitions.cut |
| tiếng động mỗi phút | 8.0 | template.json → beats.end-card.sfx_per_min |
| nhạc | bed on, -11.3 dB under voice, 115–148 BPM | template.json → beats.end-card.music_db |
| từ mỗi phút | 0.0 | template.json → beats.end-card.wpm |
