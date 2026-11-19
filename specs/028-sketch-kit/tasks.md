---
description: "Tasks for 028 — SVG build kit of the Sketch Explainer style"
---

# Tasks: Bộ dựng SVG cho phong cách Sketch Explainer

**Input**: `specs/028-sketch-kit/` (spec.md, plan.md, research.md, data-model.md, contracts/, quickstart.md)

**Tests**: có, vì spec đòi test cho GPU (FR-019, FR-020), lịch hành động (SC-004), tầng 1 người thật (SC-006) và đo tiếng động (SC-008).

Nguồn mã khởi đầu (đọc, không sửa): `films/anthropic-ipo-15/{kit.js,cast.js,scenes3.js,film.js,index.html}` của thư mục chính `/home/thinhmt/claude-Utube`, và `my-styles/sketch-explainer/styleframe/` (phần lõi đã dọn, không tên người thật).

## Phase 1: Setup

- [X] T001 Tạo khung thư mục `my-styles/sketch-explainer/kit/` (`sets/`, `examples/`, `tools/`), `people/`, `tests/sketchkit/`; thêm `people/*/.sheet/` vào `.gitignore`
- [X] T002 [P] Chép phông `Kalam-Bold.ttf` vào `my-styles/sketch-explainer/kit/` và ghi dòng Kalam (OFL) vào `CREDITS`
- [X] T003 [P] Gọi `node --test tests/sketchkit/` từ `tests/filmcheck/run.sh` (bỏ qua khi không có `node`)

## Phase 2: Foundational (chặn mọi user story)

- [X] T004 Viết `my-styles/sketch-explainer/kit/core.js` (ES module, `// @ts-check`): `el`, `lerp`, `clamp01`, `ease`, `circ` (chỉ Bézier), `rrect` (góc Bézier, không `rx`), `bumpy`, `arcPts`, `ovalHead`, `segOutline(points, w)` vẽ viền dày thành đoạn rời; tách từ `kit.js`, `cast.js`, `scenes3.js` của phim Anthropic
- [X] T005 Viết `my-styles/sketch-explainer/kit/rig.js`: `makeChar`, `setChar`, `POSES`, `EXPRS` từ `kit.js`; nét `strokeFor(scale) = 0.0052 × 1920 × scale/0.6` (R5); **bỏ giày**: chân kết thúc bằng nét nhọn; bóng elip mờ dưới chân; bóng lưỡi liềm một bên đầu
- [X] T006 Viết `my-styles/sketch-explainer/kit/catalog.json` theo data-model.md "Danh mục": `version`, `sets`, `parts`, `roles`, `poses`, `exprs`, `props`, `boards`, `cams`, `trans`, `defaults` (mỗi số kèm `evidence` trỏ tới `EVIDENCE.md`), `hero_default` (Max: hoodie `#e8833a`, tóc nâu sẫm), `avoid_hero: {}`
- [X] T007 Viết `my-styles/sketch-explainer/kit/film.js`: `film({scenes, cues, hero, custom})` dựng hợp đồng trang (`DUR`, `SHOTS`, `CARDS`, `TEXTS`, `CUES`, `render`, `READY`, `CLEAN`); kiểm mọi tên theo `catalog.json`, gom lỗi vào `window.KIT_ERRORS` `[{shot, kind: unknown_set|unknown_pose|unknown_role|unknown_prop|unknown_person|bad_value, name, hint}]` (hint = tên gần nhất), vẽ ô đỏ cho cảnh lỗi và vẫn đặt `READY` (R3)

**Checkpoint**: trang trống với 1 cảnh dựng được, `READY` bật.

## Phase 3: User Story 1 — Bộ dựng dùng lại (P1) 🎯 MVP

**Goal**: phim mới chỉ viết bảng cảnh.
**Independent Test**: `kit use` một phim thử, bảng cảnh 6 cảnh chỉ dùng tên trong danh mục, trang dựng mọi cảnh, xuất đủ biến trang.

- [X] T008 [P] [US1] Test `tests/sketchkit/names.test.mjs`: tên sai trong bảng cảnh sinh `KIT_ERRORS` đúng `kind`, đúng mã cảnh và `hint` là tên gần nhất (phần kiểm tên tách thành hàm thuần `checkScene(scene, catalog)` trong `film.js`)
- [X] T009 [US1] Viết `my-styles/sketch-explainer/kit/sets/index.js`: `PARTS` (tường, sàn, cửa sổ có phố, giá sách, đèn bàn, bảng trắng, bảng đen, TV, bàn họp, bục, cột nhà chính phủ, dãy nhà, két, tủ máy chủ, quầy hàng, bản đồ, đèn rọi, ống khói, trời ngày/đêm/hoàng hôn, cỏ, đường, vỉa hè…) và `SETS` gồm ít nhất 24 bối cảnh của FR-006, mỗi bối cảnh là danh sách phần có `floor`, `fg`; `buildSet(name|parts, ctx)`; chuyển `room`, `wb`, `chalk`, `tv`, `stage`, `meet`, `floor`, `street`, `gov`, `studio`, `night`, `curb` từ `scenes3.js`/`proof.js`
- [X] T010 [P] [US1] Viết `my-styles/sketch-explainer/kit/boards.js`: `boardShape` (wb, chalk, tv, paper), `boardText` (num có đếm lên, bars bằng nét dày + viền đoạn rời, list, vs, pie, line), `signUI` (chữ tự thu nhỏ vừa biển), `bubbleUI`, `thinkUI`, `cardUI` (nền gần đen dạng radial, chữ trắng viết tay), số lớn xanh lá; tách từ `scenes3.js`
- [X] T011 [P] [US1] Viết `my-styles/sketch-explainer/kit/roles.js`: vai chung `narrator`, `banker`, `auditor`, `trader`, `critic`, `official`, `worker`, `extra:<n>` (mặt trắng `#f7f7f5`), `variant(base, {hair, glasses, hat, suit})`, `narrator(hero)` đọc `channel.json` (R10); tách từ `cast.js` (không người thật)
- [X] T012 [US1] Nối `film.js` với `sets`, `boards`, `roles`, `rig`: dựng từng cảnh theo data-model.md "Cảnh" và "Người trong cảnh" (`walk`, `still`, `seat`, `view: back`, `custom:<tên>`, `card`, `trans: dissolve` 0,4–0,6 s)
- [X] T013 [US1] Viết `my-styles/sketch-explainer/kit/catalog.html`: mỗi bối cảnh, vai, tư thế, biểu cảm, bảng, đạo cụ một ô, theo hợp đồng trang để `qc shots` chụp được
- [X] T014 [US1] Viết bảng cảnh mẫu `my-styles/sketch-explainer/kit/examples/try.html` (≈ 60 s, chỉ tên trong danh mục, có `custom:` một lần) và kiểm bằng `sh bin/studio kit use kit-try --style sketch-explainer` + `sh bin/studio qc plan kit-try` (quickstart §2)

**Checkpoint**: US1 chạy được độc lập.

## Phase 4: User Story 2 — Khớp số đo của phong cách (P1)

**Goal**: phim dựng từ bộ dựng nằm trong khoảng số đo của kênh mẫu.
**Independent Test**: phim thử 60 s qua `qc shots` và `learn compare --clip` trong khoảng (SC-002); bảng cảnh mẫu 3 phút đạt SC-003.

- [X] T015 [P] [US2] Test `tests/sketchkit/camera.test.mjs`: `camAt` đi thẳng (tốc độ không đổi trong phần chạy), giữ yên `hold` cuối cảnh, có dịch `cx1/cy1`; `camFor` xen kẽ đẩy/kéo giữa hai cảnh liền nhau; tỉ lệ mặc định trên 100 cảnh giả: đẩy 28–38%, kéo 18–28%, đứng 17–27%
- [X] T016 [P] [US2] Test `tests/sketchkit/acting.test.mjs`: `schedule` tất định theo `id`; hành động đầu ở 0,15 s; khoảng cách 2–3 s; cảnh ≥ 4 s có ≥ 1 hành động sau giây đầu, cảnh ≥ 6 s có ≥ 2; người `still` chỉ nhận `expr`/`blink`
- [X] T017 [US2] Viết `my-styles/sketch-explainer/kit/camera.js`: `camFor(scene, prev)` và `camAt(cam, lt, d)` theo R5 (đẩy 3,3 %/s, kéo 8,6 %/s, dịch, `hold` 0,3, không tăng tốc, tuỳ chọn ease-out ≤ 0,25 s); `size` → khung (ecu, cu, med, wide, huge, insert, ots có bóng tối tiền cảnh)
- [X] T018 [US2] Viết `my-styles/sketch-explainer/kit/acting.js`: `schedule(scene)` theo R6; `film.js` áp hành động (cử chỉ, biểu cảm, chớp mắt, dựng đồ hoạ, ký hiệu bật, bước vào, chữ hiện dần) và giữ tư thế giữa hai hành động
- [X] T019 [US2] Đổi màu `sets/index.js` và `roles.js` về luật mục 3 của `STYLE.md`: bối cảnh bão hoà ≤ 0,15 và ít tương phản hơn người; đỏ và xanh lá chỉ trong `boards.js` theo nghĩa (`loss`, `danger` → đỏ; `money`, `growth` → xanh lá)
- [X] T020 [P] [US2] Viết `my-styles/sketch-explainer/kit/tools/count.mjs`: đọc bảng cảnh của một phim, in tỉ lệ cỡ cảnh, chuỗi cùng cỡ dài nhất, số bối cảnh khác nhau; và `suggestSizes(n, seed)` gợi ý chuỗi cỡ cảnh (~47% trung, đổi cỡ ~2/3, ≤ 4 liền) trong `camera.js`
- [X] T021 [US2] Mở rộng `examples/try.html` thành bảng cảnh mẫu 3 phút (dùng `suggestSizes`), chạy `count.mjs` (SC-003), dựng bản 60 s, chạy `qc shots` và `learn compare sketch-ref --clip` (SC-002); đo nét viền trên khung của phim thử (độ dài đoạn điểm tối ở 1920 px, người ở trung cảnh: 0,45–0,6% bề ngang) và thời gian dựng 100 khung (mục tiêu < 40 ms/khung phần mềm); chỉnh số mặc định trong `catalog.json → defaults` tới khi đạt; ghi mọi kết quả vào `my-styles/sketch-explainer/kit/MEASURE.md`

**Checkpoint**: MVP (US1 + US2) đủ để làm phim mới.

## Phase 5: User Story 3 — Vai và luật người thật (P2)

**Goal**: người thật vẽ một lần vào thư viện chung, duyệt một lần, dùng lại; không nói lời bịa.
**Independent Test**: người chưa duyệt hoặc bong bóng chữ không nguồn bị chặn ở tầng 1; phim thứ hai dùng người đã duyệt mà không duyệt lại (SC-006, SC-010).

- [ ] T022 [P] [US3] Test `tests/filmcheck/test_people.py`: `new` tạo `person.json` chưa duyệt với `figure_hash`; `approve` ghi `{hash, at, by, note}`; sửa `figure.js` → trạng thái `changed since approval`; `use` chép và ghi `index.json`, chặn (mã 3) người chưa duyệt; `history` giữ lần duyệt cũ
- [ ] T023 [P] [US3] Test `tests/filmcheck/test_plan_people.py`: `person_unapproved` khi băm bản chép khác `approved.hash`; `person_words` khi bong bóng người thật có chữ không phải ký hiệu và không khớp trích dẫn trong ngoặc kép ở `SOURCES.md` (R4); ký hiệu `! ? $ … ♪` (≤ 3 ký tự) luôn được phép; vai chung có chữ được phép; `kit_name` từ `KIT_ERRORS`; trang không có `KIT_ERRORS`/`PEOPLE`/`BUBBLES` (phim cũ) cho kết quả tầng 1 giống hệt trước (FR-024)
- [ ] T024 [US3] Viết `tools/filmcheck/people.py` theo `contracts/people-cli.md` và data-model.md "Người thật": `list`, `new` (tải ảnh tham chiếu vào `.sheet/` khi có `--ref-url`), `sheet`, `approve`, `use`, `check`; chỉ thư viện chuẩn
- [ ] T025 [US3] Viết `my-styles/sketch-explainer/kit/tools/sheet.html` + hàm trong `people.py` vẽ bảng mẫu (nhìn thẳng, 3/4, sau lưng, 4 biểu cảm, cạnh ảnh tham chiếu) ra `people/<slug>/.sheet/sheet.jpg` bằng Chromium của thư viện
- [ ] T026 [US3] Nối lệnh `people` vào `tools/filmcheck/cli.py` và `bin/studio` (dòng trợ giúp)
- [ ] T027 [US3] `film.js` nạp `./people/index.json` và `./people/<slug>/figure.js` cho `who: 'person:<slug>'`, xuất `window.PEOPLE` và `window.BUBBLES`
- [ ] T028 [US3] `tools/filmcheck/plan.mjs` đọc thêm `KIT_ERRORS`, `PEOPLE`, `BUBBLES`; `tools/filmcheck/plancheck.py` thêm các luật `kit_name`, `person_unapproved`, `person_words` (mức chặn) theo `contracts/kit-api.md`; phim không có các biến này không đổi (FR-024)
- [ ] T029 [US3] Chuyển 7 người thật đã duyệt vào thư viện bằng `people new … --from`: `jensen-huang` (từ `films/jensen-out/scenes.js`), `dario-amodei`, `daniela-amodei`, `sam-altman`, `andy-jassy`, `sundar-pichai`, `elon-musk` (từ `films/anthropic-ipo-15/cast.js`); bỏ giày, chỉnh nét theo `rig.js`; ghi `ref` (URL Wikimedia, giấy phép, tác giả) khi có; hình đổi (không giày, nét mới) nên cả 7 người ở trạng thái chưa duyệt: làm **một bảng mẫu chung** cho 7 người, gửi người dùng, người dùng duyệt từng người theo tên; agent chỉ chạy `people approve` cho đúng những người đã được duyệt, không tự duyệt

## Phase 6: User Story 4 — An toàn GPU (P2)

**Goal**: mọi hình của bộ dựng hiện đúng khi ghi bằng GPU.
**Independent Test**: quét tĩnh chặn mẫu lỗi; ảnh danh mục GPU khớp phần mềm (SC-005).

- [ ] T030 [P] [US4] Viết `tests/filmcheck/test_sketch_gpu.py` phần quét tĩnh theo R8 trên `my-styles/sketch-explainer/kit/**/*.js` và `people/*/figure.js`: không lệnh `A`/`a` trong chuỗi `d`, không `rx` ngoài `ellipse`, hình tô có `stroke-width` ≥ 6 và > 4 đỉnh phải dùng `segOutline`; kèm ca mẫu lỗi để test tự chứng minh bắt được
- [ ] T031 [US4] Thêm phần so ảnh vào `tests/filmcheck/test_sketch_gpu.py`: chụp `catalog.html` bằng GPU (`PLAYWRIGHT_CHROME=tools/render/chrome-gpu.sh`) và phần mềm, lệch trung bình > 6/255 ở ô nào thì báo ô đó; bỏ qua khi `sh bin/studio status --json` không có GPU
- [ ] T032 [US4] Sửa mọi chỗ test báo trong bộ dựng và `people/` cho tới khi đạt

## Phase 7: User Story 5 — Phim mẫu (P3)

**Goal**: phim mẫu 30–60 s làm bằng bộ dựng, đi đủ luồng làm phim.
**Independent Test**: tầng 1–4 đạt, `qc shots` không cảnh báo cách quay ngoài khoảng (SC-007).

- [ ] T033 [US5] Làm phim mẫu theo luồng làm phim của `CLAUDE.md` trong `films/sketch-demo/` (câu chuyện riêng, không người thật hoặc chỉ người đã duyệt, kịch bản qua `script check/review`, giọng, tầng 0–4, render GPU), không làm gói đăng; kiểm SC-001: trong `films/sketch-demo/` ngoài `index.html` (bảng cảnh), mốc lời và `people/` không có tệp mã nào khác (đếm = 0)
- [ ] T034 [US5] Lưu vào `my-styles/sketch-explainer/`: `DEMO.md` (theo `lib/lemo-opuscar/styles/_template/DEMO.md`), `demo/` (mã nguồn, `CREDITS`, `build.sh` có `LIB=` ở đầu, ghi ra `${OUT:-…}` ngoài `demo/`), `demo-checks.json`, `test.jpg`; `test.mp4` không vào git
- [ ] T035 [US5] Sửa mục 10 của `my-styles/sketch-explainer/STYLE.md`: trỏ tới `kit/` và `demo/`, bỏ câu "until the kit is packaged"; chạy `sh bin/studio learn check-names` trên mọi tệp chữ của `kit/` và `demo/` (FR-023)

## Phase 8: User Story 6 — Đo tiếng động đúng (P3)

**Goal**: tiếng động chỉ đếm trong các đoạn đã đo.
**Independent Test**: video thử có lời ngoài đoạn không làm tăng số tiếng động; đo lại `sketch-ref` cho trung vị 12–20/phút (SC-008).

- [X] T036 [P] [US6] Thêm ca vào `tests/learn/test_soundcraft.py`: âm thanh tổng hợp có tiếng gõ trong và ngoài `segments`, `analyze(..., segments)` chỉ đếm tiếng trong đoạn và chia cho tổng thời lượng đoạn; `music.windows` ngoài đoạn bị bỏ
- [X] T037 [US6] Sửa `tools/style-learn/sl/soundcraft.py`: `analyze(audio, words, segments=None)` theo R9; `sound_set` truyền `segments` từ `video.json`; thêm `--recompute` lọc lại từ `sound.json` đã lưu (không cần video) và nối vào `tools/style-learn/learn.py`
- [X] T038 [US6] Chạy `sh bin/studio learn sound sketch-ref --recompute` ở thư mục chính, ghi trung vị mới vào `my-styles/sketch-explainer/EVIDENCE.md` (thay dòng sửa tay #3 bằng số đo của công cụ)

## Phase 9: Polish

- [ ] T039 Ghi luồng dùng bộ dựng SVG và lệnh `people` vào `CLAUDE.md` (mục luồng làm phim, mục Cấu trúc), theo `contracts/people-cli.md`
- [ ] T040 [P] Cập nhật `my-styles/README.md` (cột bộ dựng của `sketch-explainer`) và `specs/028-sketch-kit/contracts/kit-api.md` nếu tên thay đổi khi làm
- [ ] T041 Chạy đủ 5 bộ test: `sh tests/run.sh`, `sh tests/render/run.sh`, `sh tests/learn/run.sh`, `sh tests/ui/run.sh`, `sh tests/filmcheck/run.sh` (SC-009)
- [ ] T042 Chạy `quickstart.md` từ đầu tới cuối và đối chiếu SC-001…SC-010

## Dependencies & Execution Order

- Phase 1 → Phase 2 → US1 → US2 (US2 chỉnh trên mã của US1).
- US3, US4, US6 chỉ cần Phase 2 (+ `film.js` của US1 cho T027/T028) và chạy song song với US2.
- US5 cần US1, US2 (và US3 nếu phim mẫu có người thật).
- Polish sau cùng.

## Parallel Examples

- Sau T007: T008, T010, T011 song song (khác tệp).
- Trong US2: T015, T016, T020 song song; T017, T018 sau test của chúng.
- US3 (T022–T029), US4 (T030–T032), US6 (T036–T038) có thể giao cho ba lượt làm khác nhau.

## Implementation Strategy

1. **MVP** = Phase 1, 2, US1, US2: bộ dựng dùng lại, khớp số đo. Dừng kiểm theo quickstart §2.
2. US3 (người thật) trước khi làm phim có người thật tiếp theo.
3. US4 (test GPU) trước lần render dài tiếp theo.
4. US6 nhỏ, độc lập, làm lúc nào cũng được.
5. US5 (phim mẫu) cuối cùng, chứng minh trọn luồng.
