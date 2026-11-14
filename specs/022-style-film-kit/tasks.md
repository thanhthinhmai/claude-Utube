---
description: "Tasks for 022 — film kit for the learned style"
---

# Tasks: Bộ code mẫu cho phong cách học được (film kit)

**Input**: các tài liệu thiết kế ở `specs/022-style-film-kit/`:
- `plan.md`, `spec.md`, `research.md` (R1–R9), `data-model.md`, `quickstart.md`;
- `contracts/kit-api.md`, `contracts/cli.md`.

**Tests**: bắt buộc. Hiến pháp IV đòi test tự động cho logic quan trọng, và spec có Independent Test cho mỗi story.
- Phần thuần của bộ dựng: `node --test` trong `my-styles/dusk-hypothetical/kit/test/`, được gọi từ `tests/render/run.sh`.
- Hình: chụp thật bằng `page still` và `qc shots`, xem bảng ảnh bằng mắt. Mọi lần dựng phải trên GPU (`sh bin/studio status` có `dựng hình: GPU`); không có thì dừng và hỏi người dùng.

**Ký hiệu**: `[P]` = chạy song song được. `[USn]` = user story của spec. `K` = `my-styles/dusk-hypothetical/kit`.

---

## Phase 1: Setup

- [X] T001 Tạo thư mục `K/`, `K/sets/`, `K/test/`; thêm vào `tests/render/run.sh` một dòng chạy `node --import ./tests/render/three-resolve.mjs --test my-styles/*/kit/test/*.test.mjs` (bỏ qua khi không có tệp nào; hook resolve để `import 'three'` tìm được three của thư viện, vì gốc dự án không có `node_modules/three` và module ES bỏ qua `NODE_PATH`), cùng kiểu báo đạt/không đạt của file.
- [X] T002 [P] Viết `K/catalog.json` đúng data-model.md, mục `catalog.json`: `version: 1`; `sets` (8 tên), `poses` (11), `faces` (8), `hair`, `hats`, `cams` (7 tên, khớp nhãn cỡ/góc của `my-styles/dusk-hypothetical/shots.json`), `gfx` (8), `moods` (4), `hero_default` `{"hoodie":"#d9b23a","strings":"#ffffff","hair":"bald","hat":null,"glasses":false}`, `avoid_hero` `{hoodie, min_delta_e: 25}`. Màu `avoid_hero.hoodie` đo từ bằng chứng của phong cách (`EVIDENCE.md`, khung tham chiếu của bộ học lại); không ghi tên kênh.

---

## Phase 2: Foundational (chặn mọi story)

- [X] T003 Tạo `K/stage.js` (research R5), tách từ `my-styles/dusk-hypothetical/styleframe/index.html`: `makeStage(size)` → `{renderer, scene, cam, post, grade(mood), draw()}`. Giữ đúng: ACES, `toneMappingExposure` 0,8, PCF soft shadow, sương `#2a1e40` 8–24 m, nền `#241a36`, `makePost(renderer, scene, cam, W, H, {ssaa:1, ao:false})` với bloom 0,3, vignette và bão hoà của khung chứng minh, chép sang canvas 2D mỗi khung, hai dải đen 6,4%. `grade(mood)` cho `dusk|alarm|night|lilac`, chỉ đổi trong khoảng của phong cách.
- [X] T004 [P] Viết `K/GRADE.md`: bảng mỗi số mặc định của T003, nguồn (vòng sửa của khung chứng minh) và số đo đối chiếu (độ sáng trung vị 0,26, khoảng 0,22–0,29; bão hoà 0,35, khoảng 0,32–0,41).
- [X] T005 Viết phần thuần trong `K/plan.js` (không import three; `film.js` dùng lại): `plan(scenes, cues)` → `{DUR, SHOTS, CARDS, CUES}`; `sceneAt(t)`; kiểm mỗi cảnh theo data-model.md, mục "Cảnh": `id` duy nhất; `dur` 1,1–6 s; `set` trong `catalog.sets` hoặc `custom:<tên>`; `cam`, `pose`, `face`, `gfx.type`, `mood` trong danh mục; `crowd.n` ≤ 5.000; `grade.exposure` 0,6–1,0 và `grade.saturation` 0,85–1,15 (chỉnh riêng cảnh, không đổi mặc định); `gfx` nằm trong cảnh; `fade` ≤ 2 lần mỗi phim. Lỗi ném `Error("<id>: <lý do>")`, ví dụ `S014: unknown pose "hold-lamp"`.
- [X] T006 [P] Test `K/test/film.test.mjs`: `SHOTS` liền nhau từ 0 tới `DUR`; `CARDS` sinh đúng từ `gfx` có chữ; mỗi luật của T005 có một ca lỗi kèm mã cảnh; `sceneAt` ở biên cảnh.
- [X] T007 Tạo `tools/filmcheck/kit.py` và lệnh `kit use <film> [--style S] [--update] [--json]` trong `tools/filmcheck/cli.py` đúng contracts/cli.md (research R1): tìm phong cách từ `--style` rồi `film.style` của `films/<film>/channel.json`; chép `my-styles/<S>/kit/` trừ `test/`; ghi `kit/.from` `{"style","sha256","at"}`; cùng băm thì `kit: up to date`; khác băm mà không `--update` thì thoát 2. Thêm `kit` vào dòng `script | web | qc | … ) cmd_filmcheck` của `bin/studio` và vào `usage`.
- [X] T008 [P] Test `tests/filmcheck/test_kit.py`: chép lần đầu, cùng băm, khác băm (thoát 2), `--update`, phong cách không có kit (thoát 2), không có `channel.json` và không `--style` (thoát 2).

**Checkpoint**: trang trống gọi `film()` với vài cảnh `void` có `SHOTS`, `READY`; `kit use` chép được.

---

## Phase 3: User Story 1 — Bộ dựng dùng lại của phong cách (P1) 🎯 MVP

**Goal**: dựng được mọi cảnh từ vài dòng mô tả, đúng số đo của phong cách.

**Independent Test**: trang danh mục qua `qc shots` và so màu (quickstart #1–#3).

- [ ] T009 [US1] Tạo `K/figure.js` (research R3): cây khớp hông → thân → cổ → đầu; vai → khuỷu → bàn tay tròn; hông → gối → bàn chân; capsule bo tròn, nhựa mờ roughness 0,9; đầu cầu ≈ 1/3 chiều cao. `makeFigure({hoodie, strings, hair, hat, glasses, seed})` → `{group, pose(name, t), face(name), look(turn, tilt), hold(item)}`. Hoodie có mũ trùm sau gáy và hai dây rút. Mặt là texture canvas, 8 biểu cảm `dot|half|wow|happy|blank|angry|sad|sweat`, không mũi tai.
- [ ] T010 [US1] Bảng góc khớp cho 11 tư thế trong `K/figure.js`: `stand`, `sit` (hông đúng chiều cao ghế 0,45 m, thân không bị ghế che), `walk` (chu kỳ theo `t`), `hold-phone|book|bag|cup|paper`, `point`, `cheer`, `shrug`; đồ cầm tay dựng bằng hình khối, gắn vào khớp bàn tay; điện thoại có màn sáng yếu, không rọi cháy mặt.
- [ ] T011 [P] [US1] Test `K/test/figure.test.mjs` (dùng three trong node, không vẽ): mỗi tên của `catalog.poses`, `faces`, `hair`, `hats` có cài đặt; ở `sit`, đỉnh đùi nằm trên mặt ghế; ở mọi tư thế bàn tay cách đồ cầm ≤ 2 cm; tỉ lệ đầu/chiều cao 0,30–0,36.
- [ ] T012 [US1] Tạo `K/crowd.js` (research R4): `makeCrowd({n, area, seed, camera})` → `{group, update(camera, t)}`; gần (≤ 12 người, ≤ 6 m) dùng `makeFigure`; vừa (6–25 m) `InstancedMesh` 4 phần với `instanceColor`; xa (> 25 m) `Points`. Màu áo từ bảng màu phong cách bằng `mulberry(seed)`; tóc hoặc mũ khác nhau; đứng im hoặc cùng một nhịp nhún nhẹ theo `t`.
- [ ] T013 [P] [US1] Tạo `K/sets/parts.js`: sàn có vân, tường, lưới đồ vật lặp theo hàng (bàn, tủ, ghế, cửa sổ), đèn dây và dải đèn có bloom, trần tự sáng nhẹ, cửa sổ trời hoàng hôn; mỗi bối cảnh trả `{group, anchors, lights}` (`anchors`: hero, extras, crowd, máy).
- [ ] T014 [US1] Tạo 8 bối cảnh trong `K/sets/` bằng `parts.js`: `classroom.js`, `lockers.js`, `gym.js`, `street.js`, `bedroom.js`, `cafeteria.js`, `stadium.js` (khán đài cho ≥ 1.000 người), `void.js` (nền tím trống cho thẻ chèn). Mỗi bối cảnh có chi tiết lặp theo hàng và ≥ 1 nguồn đèn thật (FR-004, mục 2–3 `STYLE.md`).
- [ ] T015 [US1] Tạo `K/camera.js`: `place(cam, name, anchors, opts)` cho 7 cách đặt máy của `catalog.cams` (trung tầm mắt, toàn hơi cao, cận, rất cận, rất rộng, qua vai có đầu mờ tiền cảnh, thẻ chèn), máy hơi chéo; đặt tiêu điểm DOF vào chủ thể; chủ thể ở lớp trước, đám đông lớp sau, vật che tiền cảnh khi có `anchors.foreground`.
- [ ] T016 [US1] Tạo `K/graphics.js` (research R7): `drawGfx(ctx2d, g, localT, area)` cho 8 loại: `counter` (pill đếm lên ease-out ≈ 1,3 s rồi giữ), `menu` (góc kiểu game có ổ khoá), `diagram` (trên nền cảnh làm mờ: hình người phẳng, đồng hồ đo, biểu đồ hai cột), `bubble`, `stat` (nền tím), `title` (hai dòng, dòng hai lớn hơn và vàng), `chapter`, `end-choice` (hai ô lựa chọn, hàng nhân vật nhỏ). Chữ in hoa IM Fell English, kem `#f3e3b0` hoặc vàng nhạt, phát sáng nhẹ, giãn chữ rộng; hiện trong 0,07–0,15 s; chỉ trong vùng hình. `cardsOf(scene, t0)` là phần thuần, có ca trong `K/test/film.test.mjs`.
- [ ] T017 [US1] Phần three của `K/film.js` (contracts/kit-api.md): `film({scenes, cues, hero, custom, size})` nạp `./channel.json` (lấy `film.hero`, không có thì `hero_default` và một dòng cảnh báo console), dựng bối cảnh lười với bộ đệm 4 bối cảnh, đặt `window.DUR`, `SHOTS`, `CARDS`, `CUES`, `render(t)` (tất định, thứ tự bất kỳ), `READY` (sau khi phông và mọi bối cảnh dùng tới đã nạp), đọc `window.CLEAN` mỗi khung (không vẽ phụ đề và đồ hoạ có chữ); vẽ phụ đề từ `cues`.
- [ ] T018 [US1] Tạo `K/catalog.html`: trang phim hợp lệ dùng `film()`, mỗi mục của `catalog.json` một cảnh 1,2 s: mỗi bối cảnh ở cảnh toàn có người phụ; mỗi tư thế và mỗi biểu cảm ở cảnh trung; mỗi loại đồ hoạ; mỗi cách đặt máy.
- [ ] T019 [US1] Chạy thật quickstart #1: `kit use` vào `films/kit-catalog/` (chép `catalog.html` thành `index.html`, `--style dusk-hypothetical`), `qc shots kit-catalog` (gọi lượt gán nhãn Opus của specs/021, tốn tiền: báo người dùng một dòng và chờ đồng ý trước lần chạy đầu), xem `.check/shots/sheet-*.jpg` bằng mắt. Sửa tới khi mỗi bối cảnh có độ sáng 0,22–0,29, bão hoà 0,32–0,41 và 0 lỗi phẳng, tối, cháy, mờ (SC-001); thân, tay, chân liền nhau, tay cầm đúng đồ (US1 #2); chữ trong vùng hình và có trong `CARDS` (US1 #4). Ghi số vào quickstart.
- [ ] T020 [US1] Quickstart #2 (SC-002): dựng lại bố cục toa tàu của khung chứng minh bằng kit (một bối cảnh `custom:train` trong trang thử, chỉ dùng `parts.js`, `makeFigure`, `makeCrowd`, `stage`), `page still`, rồi `learn compare` với khung gốc đã dùng; phải đạt ngay lần chụp đầu. Không đạt thì sửa **kit** (không sửa trang thử) rồi ghi rõ là lần thứ mấy.
- [ ] T021 [US1] Quickstart #3 (SC-003): trang thử một cảnh `stadium` 1.000 người, 10 s; `sh bin/studio render <phim> --fps 60`, đo thời gian ≤ 3 phút trên GPU; xem ảnh: người phân biệt được bằng màu áo, tóc, mũ.

**Checkpoint**: US1 đạt; commit giai đoạn.

---

## Phase 4: User Story 3 — Skill học phong cách cho phép theo cấu trúc tham chiếu (P3)

(Làm trước US2 vì độc lập và nhỏ; chạy song song với Phase 3 được.)

**Goal**: `learn save` không chép tệp làm việc; skill cho phép `STRUCTURE.md`.

**Independent Test**: quickstart #6; đọc lại skill.

- [ ] T022 [P] [US3] Sửa `tools/style-learn/sl/save.py` (research R8): chép từ `references/<set>/style/` theo danh sách cho phép `STYLE.md`, `EVIDENCE.md`, `style.json`, `STRUCTURE.md`, `shots.json`, `styleframe/**`, `styleframe.jpg`; tệp khác in `skipped: <đường dẫn>`. `--update` giữ `kit/` cùng các tệp phim mẫu (`DEMO_FILES`). Gọi `check-names` trên `STRUCTURE.md` như `STYLE.md`.
- [ ] T023 [P] [US3] Test trong `tests/learn/` (thêm vào tệp test của `save`): bộ thử có `label.log`, `pipeline.log`, `review-1.md`, `review-2.md`, `.job`, `STRUCTURE.md` → phong cách đã lưu không có 5 tệp đầu, có `STRUCTURE.md`; `--update` giữ `kit/` và `demo/`; `STRUCTURE.md` có tên kênh thì `save` dừng.
- [ ] T024 [US3] Sửa `.claude/skills/style-learn/SKILL.md`, bước viết mục 11 (dòng "mục 11 gợi ý cấu trúc … khác kênh gốc"): khi phong cách học cho một kênh có quyết định theo cấu trúc tham chiếu (xem `sh bin/studio channel show <kênh>`), viết `references/<set>/style/STRUCTURE.md` (chỉ màn, tỉ lệ, mốc, nhịp; không câu chữ, không tên) và mục 11 trỏ tới đó; kênh khác giữ luật cũ. Kiểm bằng đọc (không có máy kiểm): đọc lại bước đã sửa, đối chiếu với `channel show dusk-hypothetical` (có quyết định 2026-11-13, phải ra nhánh STRUCTURE.md) và một kênh khác không có quyết định đó (phải ra luật cũ); ghi kết quả vào quickstart.

**Checkpoint**: commit giai đoạn.

---

## Phase 5: Nhân vật chính của kênh (FR-015, dùng cho US2 và US4)

- [ ] T025 Sửa `tools/filmcheck/channels.py`: trường `hero` theo data-model.md, mục "Nhân vật chính": `hoodie`, `strings` là `#rrggbb`; `hair` trong `catalog.hair`; `hat` trong `catalog.hats` hoặc `null`; `glasses` bool; thiếu `hero` vẫn hợp lệ. `normal()` giữ `hero`; `channel_md()` in `Hero: hoodie … · strings … · hair …`; `attach()` chép vào `film.hero` của bản chụp. Kiểm ΔE (CIE76 trên Lab, hàm trong `tools/filmcheck/kit.py`) ≥ `avoid_hero.min_delta_e` khi phong cách của kênh có `kit/catalog.json`.
- [ ] T026 Sửa `tools/filmcheck/cli.py`: `channel set <slug> hero <khoá=giá trị…>` đúng contracts/cli.md (`hat=none`, `glasses=yes|no`, chỉ đổi khoá nêu); `kit use` kiểm `film.hero` theo ΔE và in gợi ý khi kênh thiếu `hero`.
- [ ] T027 [P] Test trong `tests/filmcheck/test_channels.py`: `set hero` đổi một khoá; khoá hoặc giá trị sai thoát 2; áo gần `avoid_hero` (ΔE < 25) thoát 2; `attach` có `film.hero`; kênh cũ không có `hero` vẫn `show` được.
- [ ] T028 Đặt hero cho kênh: `sh bin/studio channel set dusk-hypothetical hero hoodie=#d9b23a strings=#ffffff hair=bald hat=none glasses=no`; kiểm `channels/dusk-hypothetical/channel.json` và `CHANNEL.md`.

---

## Phase 6: User Story 2 + 4 — Phim dài từ bộ dựng, và phim mẫu mới (P2, P4)

**Goal**: một phim ≈ 10,5 phút của kênh `dusk-hypothetical` dựng hoàn toàn bằng kit, đạt các tầng kiểm, 60 fps; lưu làm phim mẫu (FR-011: một lần chạy cho cả hai story).

**Independent Test**: quickstart #4, #5, #8.

- [ ] T029 [US2] Sửa `CLAUDE.md`, luồng làm phim, mục phong cách riêng (FR-009): phong cách có `kit/` thì chạy `sh bin/studio kit use <tên>` ngay sau `channel attach`, đọc `kit/catalog.json` và `contracts/kit-api.md` của 022, viết trang bằng `film({scenes})`; bảng cảnh ghi bối cảnh, tư thế, đồ hoạ theo tên danh mục; kịch bản theo `STRUCTURE.md` của phong cách (phim 4–7 phút dùng tỉ lệ "Compressed" của nó). Thêm một dòng vào mục Cấu trúc cho `kit use`. Sửa `my-styles/dusk-hypothetical/STYLE.md` thêm một dòng trỏ tới `kit/`.
- [ ] T030 [US2] Làm phim `films/dusk-demo/` theo luồng làm phim của `CLAUDE.md` (kênh `dusk-hypothetical`, ≈ 630 s): `job start`, `channel attach --new`, `kit use`, BRIEF, TREATMENT, SCRIPT + SOURCES theo `STRUCTURE.md` (`script check`, `script review`), giọng `am_michael` × 1,1, tầng 0. **Trước `script review`** (một lượt `claude -p` tốn tiền) và **trước `render`** (khoảng 1 giờ GPU), báo người dùng một dòng và chờ đồng ý.
- [ ] T031 [US2] Bảng cảnh khoảng 220 cảnh trong `films/dusk-demo/index.html` bằng `film({scenes})`, ≥ 18 bối cảnh (8 của kit cộng bối cảnh `custom:` dựng từ `parts.js`, ghi rõ trong bảng cảnh), cỡ cảnh và góc máy theo `shots.json`; tầng 1 `qc plan`, tầng 2 `qc shots` tới khi đạt (lượt gán nhãn khoảng 220 cảnh tốn tiền: báo người dùng trước lần chạy đầu).
- [ ] T032 [US2] Dựng `sh bin/studio job run <mã> --step Render -- sh bin/studio render dusk-demo --fps 60` trên GPU; trộn tiếng, tầng 4 `qc dusk-demo`; `ffprobe` ra 60 fps. Đo SC-004 (mốc màn từ `SCRIPT.md` và `narration.json` so với `STRUCTURE.md` ±5 điểm %, tỉ lệ cỡ cảnh và góc máy, số bối cảnh, lỗi nặng) và SC-005 (dòng bảng cảnh chia số cảnh ≤ 15; không có `new THREE.` ngoài `custom`). Xem bằng mắt vài phút phim.
- [ ] T033 [US4] Lưu phim mẫu vào `my-styles/dusk-hypothetical/` (research R9): thay `demo/` bằng `index.html`, `lines.json`, `cues.json`, `mix.py`, `CREDITS`, `build.sh` mới (`LIB=` tuyệt đối ở đầu; ghép `$HERE` và `$HERE/../kit` vào `$OUT/page/`; tạo giọng; dựng 60 fps; trộn; ghép tiếng); viết lại `DEMO.md` theo mẫu `DEMO.md` của thư viện; `demo-checks.json` (các tầng, mốc màn, số bối cảnh, fps); `test.jpg` là một khung của phim; `test.mp4` ngoài git.
- [ ] T034 [US4] Quickstart #8: chạy `demo/build.sh` với `OUT` trong scratchpad trên GPU; so phim ra với `DEMO.md` và `demo-checks.json` (thời lượng, số cảnh, 60 fps).

**Checkpoint**: commit giai đoạn.

---

## Phase 7: Polish

- [ ] T035 [P] `learn check-names` trên `my-styles/dusk-hypothetical/STRUCTURE.md`, mọi tệp `K/*.js`, `K/sets/*.js`, `K/catalog.json`, `K/GRADE.md`, `demo/*` (SC-007).
- [ ] T036 [P] Thêm phông IM Fell English (OFL, qua thư viện) vào `CREDITS` nếu chưa có; `desktop/core-build/credits-check.py` không báo.
- [ ] T037 Chạy đủ các bộ test: `sh tests/run.sh`, `tests/render/run.sh`, `tests/learn/run.sh`, `tests/ui/run.sh`, `tests/filmcheck/run.sh`, `tests/online/run.sh`; `git -C lib/lemo-opuscar status --short` trống.
- [ ] T038 Điền mục Kết quả của `quickstart.md` (đạt, đạt một phần, thất bại cho từng SC, kèm số đo); cập nhật memory dự án.

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → Phase 3 (US1).
- Phase 4 (US3) độc lập, làm song song với Phase 2–3 được.
- Phase 5 cần T002 (`avoid_hero`) và T007 (`kit.py`).
- Phase 6 cần Phase 3 và Phase 5.
- Phase 7 sau cùng.

## Parallel Examples

- Phase 1–2: T002, T004, T006, T008 song song (khác tệp).
- Phase 3: T011, T013 song song với T012; T016 song song với T014–T015.
- Phase 4: T022, T023 song song với toàn bộ Phase 3.

## Implementation Strategy

1. **MVP = US1**: kit + trang danh mục đạt SC-001–SC-003. Dừng, cho người dùng xem bảng ảnh danh mục.
2. US3 nhỏ, làm xen.
3. Hero của kênh, rồi phim ≈ 10,5 phút (US2 + US4) — phần tốn thời gian và tiền nhất (một lượt biên tập, khoảng 1 giờ GPU): hỏi người dùng trước hai bước đó.
4. Polish, đủ test, PR riêng cho 022.
