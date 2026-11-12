---
description: "Tasks for 021 — learn the reference channel's shot grammar"
---

# Tasks: Học cách quay của kênh tham chiếu

**Input**: các tài liệu thiết kế ở `specs/021-learn-shot-grammar/`:
- `plan.md`, `spec.md`, `research.md` (R1–R9), `data-model.md`, `quickstart.md`;
- `contracts/cli.md`.

**Tests**: bắt buộc. Hiến pháp IV đòi test tự động cho logic quan trọng, và spec có mục Independent Test cho mỗi story.
- Lượt gán nhãn được thử bằng `claude` giả: `STUDIO_CLAUDE_BIN=tests/online/fake_claude`, như các test của người biên tập.
- Video thử tạo bằng `tests/learn/make_fixtures.py`, không commit file media.

**Ký hiệu**: `[P]` = chạy song song được. `[USn]` = user story của spec.

---

## Phase 1: Setup

- [ ] T001 Thêm `my-styles/*/test.mp4` vào `.gitignore` (research R7), kèm một dòng chú thích.
- [ ] T002 [P] Mở rộng `tests/online/fake_claude` để trả lời theo JSON schema của lượt gán nhãn khi prompt hệ thống có chữ `shot labeler`. Câu trả lời đọc từ file `FAKE_LABELS` (JSON `{id: [scale, angle, foreground_blur]}`); không có file thì gán `med`/`eye` cho mọi mã cảnh trong prompt. Ghi mỗi lần gọi vào `FAKE_CLAUDE_LOG`, như hiện nay.

---

## Phase 2: Foundational (chặn mọi story)

- [ ] T003 Tạo `tools/filmcheck/focus.py` (chỉ thư viện chuẩn và ffmpeg; research R1):
  - `measure(image, subtitle_band=0.18) -> {tiles, focused_share, sharpest, sharpest_at, letterbox}`;
  - ffmpeg thu ảnh về 480 px chiều ngang, xám, xuất `rawvideo`;
  - bỏ dải đen (các hàng có độ sáng < 0,03 và độ lệch < 0,01, tính từ mép) và dải phụ đề;
  - chia 4×3 ô, tính phương sai Laplace của từng ô; ô nét khi ≥ `FOCUS_T` (hằng số, ban đầu 40; T020 chốt lại).
- [ ] T004 [P] Tạo `tests/filmcheck/test_focus.py`, với ảnh vẽ bằng ffmpeg:
  - ảnh nét (`testsrc2`) → `focused_share` ≥ 0,9;
  - cùng ảnh qua `gblur=sigma=8` → 0;
  - ảnh nét nửa trái, mờ nửa phải → khoảng 0,5;
  - ảnh có dải đen 12% trên dưới và một dòng chữ trắng ở dải phụ đề trên nền mờ → dải đen bị bỏ, chữ không tính là nét;
  - mỗi ảnh ≤ 0,15 s.
- [ ] T005 Tạo `tools/filmcheck/labeler.py` theo mẫu `editor.run` (research R3):
  - prompt hệ thống `SYSTEM` (có chữ "shot labeler", định nghĩa cỡ cảnh và góc máy như R3; cảnh không có người thì xếp cỡ theo chủ thể được lấy nét, không rõ thì `unknown`; dặn chỉ xem các ảnh được đưa và không đoán ý đồ);
  - `SCHEMA`: `{shots: [{id, scale, angle, foreground_blur, confidence}]}` với enum như data-model;
  - lệnh: `claude -p --tools Read --allowedTools Read --json-schema … --output-format json --no-session-persistence` cùng `editor.model_args()` (Opus); môi trường online giống `editor.run`;
  - `label(sheets: [path], ids: [str], hints: {id: {focused_share, sharpest_at}}) -> {labels: {id: {...}}, model, usage}`; tối đa 4 bảng ảnh mỗi lần gọi; câu trả lời sai schema hoặc thiếu mã thì hỏi lại một lần, sai nữa thì `LabelError`;
  - `contradicts(label, focus) -> bool`: `ecu`/`cu` mà `focused_share` ≤ 1/12 và ô nét nhất ở hàng hoặc cột ngoài cùng; hoặc `huge` mà `focused_share` ≥ 0,9.
- [ ] T006 [P] Tạo `tests/filmcheck/test_labeler.py` (`claude` giả):
  - nhãn đọc đúng từ `FAKE_LABELS`;
  - prompt có đúng các đường dẫn bảng ảnh và mã cảnh, không có kịch bản hay tên phim;
  - câu trả lời sai schema 2 lần → `LabelError`;
  - có `--model claude-opus-5-5`;
  - `contradicts` có ca đúng và ca sai.
- [ ] T007 [P] Thêm `blurred` vào `EXCEPTABLE` trong `tools/filmcheck/tiers.py`; cập nhật `specs/020-qc-before-render/contracts/checks.md` (một dòng trong bảng luật: `shots`, `blurred`, `block`, không ô nào nét, ngoại lệ được) và test trong `tests/filmcheck/test_tiers.py`.

**Checkpoint**: `sh tests/filmcheck/run.sh` đạt. Commit.

---

## Phase 3: User Story 1 — Học cách quay từ video tham chiếu (P1) 🎯 MVP

**Mục tiêu**: mỗi cảnh của video tham chiếu có cỡ cảnh, góc máy, độ nét và bối cảnh; hồ sơ có phân bố kèm bằng chứng.

**Independent Test**: video thử có 6 cảnh biết trước → tách đúng 6 cảnh; độ nét đúng từng cảnh; nhãn (từ `claude` giả) vào `shots.json`; `summary` có `shot_grammar` đúng tỉ lệ; bảng ảnh ghi mã cảnh.

### Tests

- [ ] T008 [P] [US1] Thêm vào `tests/learn/make_fixtures.py` video `shots6.mp4` (1280×720, 24 fps, 18 s):
  - 6 cảnh 3 s, cắt cứng giữa hai cảnh tối giống nhau (để kiểm R2);
  - cảnh 1, 3, 5 nét; cảnh 2 mờ hết; cảnh 4 chỉ nét một góc;
  - cảnh 6 là thẻ chữ trên nền trơn;
  - hai cặp cảnh dùng cùng một nền (2 bối cảnh lặp lại);
  - có dải đen 2.05:1.
- [ ] T009 [P] [US1] Tạo `tests/learn/test_shots.py`:
  - `learn shots` trên `shots6.mp4` → 6 cảnh, mốc cắt lệch ≤ 1 khung;
  - `focused_share` đúng thứ tự (cảnh 2 = 0, cảnh 4 ≤ 1/12);
  - gom ra 4 bối cảnh;
  - bảng ảnh rộng < 1280 px, có 6 ô;
  - `learn label` (giả, `FAKE_LABELS` cho trước) ghi nhãn và `evidence`;
  - `--set v01:S002 scale=huge` ghi `edited_by: "user"`;
  - `summary` → `shot_grammar.scale_share` đúng, `inserts` = 1, `subject_sharp_share` = 4/5;
  - `--pass 2 --sample 6` → `agreement.json` có `scale_same`, `scale_within_one`, `angle_same` đúng với hai bộ nhãn giả khác nhau.

### Implementation

- [ ] T010 [US1] Tạo `tools/style-learn/sl/shots.py`:
  - `detect(path, segs, flashes)`: ffmpeg `scdet=threshold=15` trên từng đoạn đo; gộp các điểm cắt cách nhau < 0,3 s; bỏ chớp sáng (research R2);
  - `frames(path, shots)`: khung giữa mỗi cảnh ≥ 0,5 s, 960×540 (thêm viền nếu khác tỉ lệ), vào `profile/<vid>/shot-frames/S001.jpg`;
  - `focus.measure` cho từng khung;
  - `signature(img)`: biểu đồ màu 4×4×4 trên ảnh 64 px, cộng độ sáng 3×3 vùng; `group(sigs, SET_D)` gom bằng liên kết đơn ra `B1…`;
  - `sheets(...)`: Pillow, 6 cột × tối đa 8 hàng, ô 200×112, nhãn `S001` (thêm `· CU · eye` khi đã có nhãn), ra `shot-sheets/<vid>_shots_<n>.jpg`;
  - ghi `profile/<vid>/shots.json` theo data-model "ShotLabel".
- [ ] T011 [US1] Sửa `tools/style-learn/learn.py`:
  - lệnh `shots <set> [--only]`: gọi `sl/shots.py` cho từng video đã đo; in số cảnh và số cắt mỗi phút, ngoài 16–26 thì in `!` (contracts/cli.md); làm tiếp khi chạy lại;
  - lệnh `label <set> [--pass 2 --sample N] [--set vNN:Sxxx key=value …]`: gọi `filmcheck.labeler` (thêm `tools/` vào `sys.path`); ghi nhãn, `contradicts` thành `check: true` và in ra; `--pass 2` ghi `labels-pass2.json` và `agreement.json` (data-model "AgreementReport"; thứ tự bậc ecu < cu < med < wide < huge).
- [ ] T012 [US1] Sửa `tools/style-learn/sl/summary.py`: tính `shot_grammar` cho mỗi video từ `shots.json` (data-model "ShotGrammar"; chỉ tính cảnh có nhãn, không `insert`/`short`/`unknown`), rồi cho cả bộ theo định dạng (trung vị và khoảng giữa các video); thêm vào `summary.md` một bảng "Shot grammar".
- [ ] T013 [US1] Kiểm `sh bin/studio learn shots|label <set>` chạy được qua `bin/studio` (lệnh `learn` chuyển thẳng cho `learn.py`); thêm `shots|label` vào dòng `learn <lệnh>` ở phần trợ giúp đầu `bin/studio`.

**Checkpoint**: `sh tests/learn/run.sh` đạt. Commit.

---

## Phase 4: User Story 2 — Học lại Dusk Hypothetical (P2)

**Mục tiêu**: `dusk-hypothetical` có số đo cách quay kèm bằng chứng; nhật ký sửa cũ còn nguyên.

**Independent Test**: bảng "Key numbers" có các số cách quay; mục 6 của STYLE ghi con số; `shots.json` có; mọi dòng nhật ký sửa cũ còn; video tham chiếu đã xoá.

### Tests

- [ ] T014 [P] [US2] Thêm vào `tests/learn/test_save_clean.py`:
  - `save --update` ghi đè phong cách cùng slug, giữ `created`, thêm `updated`;
  - từ chối (mã 1) khi `EVIDENCE.md` mới thiếu một dòng của bảng "Corrections log" cũ;
  - `shots.json` được ghi từ `summary.json` với khoảng của mỗi tỉ lệ;
  - không slug nào bị ghi đè khi không có `--update`.

### Implementation

- [ ] T015 [US2] Sửa `tools/style-learn/sl/save.py`:
  - `--update`: cho slug đã có trong `my-styles/`; so các dòng bảng "Corrections log" cũ với mới, thiếu dòng nào thì `StepError` kèm dòng đó; giữ `created`, ghi `updated` vào `style.json`;
  - ghi `shots.json` (data-model "ShotGrammarRefs": khoảng của mỗi tỉ lệ = [min, max] giữa các video; `longest_same_scale_max` = max; `top_set_share_max` = max; `focus_t` = `focus.FOCUS_T`);
  - khi lưu, giữ `DEMO.md`, `demo/`, `test.jpg`, `test.mp4` và `demo-checks.json` đã có trong phong cách (học lại không làm mất phim mẫu).
- [ ] T016 [US2] Sửa `tools/filmcheck/stylerefs.py`: đọc `my-styles/<slug>/shots.json` vào khoá `shot_grammar` (giữ nguyên dạng lồng), và `has_shot_grammar(refs)`. Thêm test vào `tests/filmcheck/test_stylerefs.py`.
- [ ] T017 [US2] Sửa `tools/style-learn/learn.py`: thêm cờ `--update` cho `save`.
- [ ] T018 [US2] Chạy thật: `sh bin/studio learn fetch dusk-hypothetical-2 --channel <kênh trong channels/dusk-hypothetical/references.json> --count 10` (người dùng xác nhận quyền dùng như lời nhắc của `fetch`), rồi `measure`, `shots`. Ghi thời gian từng bước. Lấy thời gian các bước của lần học `dusk-hypothetical` trước (2026-11-12) từ sổ việc `.studio/jobs` để so cho SC-003; không còn thì ghi "không có số so" và chỉ báo thời gian lần này. Kiểm số cắt mỗi phút với khoảng 16–26.
- [ ] T019 [US2] Chạy thật: `learn label dusk-hypothetical-2`; xem các cảnh `check` trên bảng ảnh và sửa bằng `--set` nếu sai; rồi `learn label … --pass 2 --sample 40` (SC-001). Mở bằng mắt ít nhất 2 bảng ảnh có nhãn.
- [ ] T020 [US2] Chốt hai ngưỡng trên dữ liệu thật:
  - `FOCUS_T`: giá trị lớn nhất mà ít nhất 95% khung tham chiếu có ít nhất một ô nét;
  - `SET_D`: xem bảng ảnh theo nhóm, các nhóm phải là cùng một nơi.

  Ghi số và cách chọn vào `research.md` (R1, R4) và vào `focus.py` và `sl/shots.py`. Chạy lại `shots` nếu `SET_D` đổi.
- [ ] T021 [US2] `learn summary dusk-hypothetical-2`; cập nhật bản phong cách theo bước 4–5 của skill style-learn, **bắt đầu từ bản hiện có** của `my-styles/dusk-hypothetical/` (chép STYLE.md, EVIDENCE.md, style.json vào `references/dusk-hypothetical-2/style/`):
  - thêm các hàng cách quay vào "Key numbers";
  - viết lại mục 6 (và phần chiều sâu ở mục 2) bằng con số kèm `bảng#ô`;
  - sửa luật nào sai so với số mới, mỗi chỗ sửa thêm một dòng vào nhật ký sửa (giữ mọi dòng cũ);
  - mục 10 (Engine) chỉ tới `demo/` (có ở T030) rồi mới tới `brick-toy`.

  Chạy `learn check-names`.
- [ ] T022 [US2] `learn save dusk-hypothetical-2 --slug dusk-hypothetical --en "Dusk Hypothetical" --based-on brick-toy --update` (khung chứng minh: dùng lại khung đã duyệt nếu luật về hình không đổi, nếu không thì chạy `learn compare` như skill); rồi `learn clean dusk-hypothetical-2`. Ghi kết quả SC-001 – SC-004 và SC-007 (phần xoá video) vào `quickstart.md`.

**Checkpoint**: commit (phong cách đã học lại).

---

## Phase 5: User Story 3 — Tầng 2 so cách quay của phim (P3)

**Mục tiêu**: `qc shots` báo khung mờ (chặn) và lệch phân bố cách quay (cảnh báo), theo mã cảnh.

**Independent Test**: phim thử có nhãn biết trước → báo đủ mọi khung mờ và mọi lệch đã cài, ≤ 1 báo nhầm trên 30.

### Tests

- [ ] T023 [P] [US3] Thêm vào `tests/filmcheck/test_shots.py`, phim thử `grammar-30` (30 cảnh, `make_tier_film`):
  - 3 cảnh mờ hết (`look: "blur"`: canvas vẽ xong rồi `filter: blur(12px)`; thêm vào `TIER_PAGE` của `samples.py`);
  - nhãn giả (`FAKE_LABELS`): 70% cận, 90% ngang tầm mắt, một chuỗi 6 cảnh cùng cỡ;
  - phong cách thử có `shots.json` với khoảng khác.

  Kỳ vọng:
  - 3 lỗi `blurred` đúng mã cảnh, cổng render chặn, `qc except … blurred` gỡ được;
  - cảnh báo `style_scale_cu`, `style_angle_eye`, `style_same_scale_run` (kèm đủ 6 mã cảnh);
  - chạy lại khi nguồn không đổi → `labels: reused` (`claude` giả không bị gọi lần hai);
  - không có `shots.json` → `skipped` có "shot grammar";
  - `claude` giả lỗi → cảnh báo `shot_grammar_unchecked`;
  - đếm cảnh tốt bị báo nhầm (`blurred` hay cảnh báo có mã cảnh ngoài các cảnh đã cài): ≤ 1 (SC-005).

### Implementation

- [ ] T024 [US3] Sửa `tools/filmcheck/shots.mjs`:
  - nhận `--plain` trong job để vẽ bảng ảnh không viền đỏ và không nhãn kiểm, cho lượt gán nhãn (`.check/shots/label-sheet-<n>.jpg`);
  - bảng ảnh thường ghi `<mã> · <CỠ> · <góc>` khi job có `labels`.
- [ ] T025 [US3] Sửa `tools/filmcheck/shotcheck.py` (research R8):
  - `focus.measure` trên mỗi ảnh giữa cảnh, rồi luật `blurred` (`block`) khi `focused_share == 0`, kèm `sharpest`;
  - nhãn: nếu `.check/labels.json` có cùng `fingerprint` thì dùng lại; nếu không thì vẽ bảng `--plain`, gọi `labeler.label` (gợi ý độ nét theo mã), ghi `labels.json` (`fingerprint`, `model`, `at`, `labels`); `LabelError` thì cảnh báo `shot_grammar_unchecked`;
  - so với `refs["shot_grammar"]`:
    - mỗi cỡ và góc ngoài khoảng → `style_scale_<loại>` / `style_angle_<loại>` (`warn`), kèm gợi ý mã cảnh (thiếu: 5 cảnh dài nhất của loại thừa nhất; thừa: các cảnh của loại đó);
    - tỉ lệ đổi cỡ → `style_scale_change`;
    - mỗi chuỗi cùng cỡ dài hơn `longest_same_scale_max` → `style_same_scale_run` kèm mã từng cảnh;
    - trung vị `focused_share` → `style_focus`;
    - tỉ lệ bối cảnh nhiều nhất (theo `set` của `SHOTS`) → `style_top_set`.
  - Bỏ qua phần so (ghi `skipped`) khi phong cách không có `shot_grammar`.
- [ ] T026 [US3] Sửa `tools/filmcheck/cli.py` (`cmd_qc_shots`): in dòng `labels: …` và các tỉ lệ cỡ cảnh, góc máy của phim. Sửa `tools/filmcheck/report.py`: `CHECKS.md` có bảng "Shot grammar" (phim so với khoảng của phong cách).
- [ ] T027 [US3] Chạy thật `sh bin/studio qc shots pet-swap` với phong cách đã học lại (SC-006): ghi số khung mờ, tỉ lệ toàn rất rộng, ngang tầm mắt, chuỗi cùng cỡ, thời gian, số lượt gán nhãn. Mở bảng ảnh có nhãn bằng mắt. Ghi vào `quickstart.md`.

**Checkpoint**: commit.

---

## Phase 6: User Story 4 — Phim mẫu cho phong cách học được (P4)

**Mục tiêu**: `dusk-hypothetical` có phim mẫu như phong cách thư viện, và phim đạt mọi tầng kiểm.

**Independent Test**: `sh my-styles/dusk-hypothetical/demo/build.sh` dựng lại phim 15–30 s đúng số khung; phim đạt tầng 1–4 và phần so cách quay.

- [ ] T028 [US4] Làm phim mẫu `films/dusk-demo/` theo luồng làm phim của `CLAUDE.md` (Brief → Treatment → kịch bản được chấm → giọng của kênh → các tầng 0–4 của specs/020 → render → qc), câu chuyện riêng của xưởng (không giống kênh tham chiếu, không giống `pet-swap` hay `pause-time`), 15–30 s. Phim mẫu không đăng lên kênh, nên bỏ bước gói đăng (3a) và không gắn đề của hàng đợi. Bảng cảnh lập theo `shots.json` của phong cách (tỉ lệ cỡ cảnh, góc máy, đổi cỡ giữa hai cảnh liền nhau, chủ thể nét).
- [ ] T029 [US4] Đạt `qc shots` không có cảnh báo cách quay nào ngoài khoảng, và không có `blurred` nào ngoài ngoại lệ có lý do; đạt `qc plan` và `qc` (SC-008). Xem phim bằng mắt.
- [ ] T030 [US4] Lưu phim mẫu vào `my-styles/dusk-hypothetical/` theo bước 5 của `lib/lemo-opuscar/MY-STYLES.md`:
  - `demo/` có mã nguồn, `CREDITS` (kèm giấy phép MIT của mã chép từ thư viện) và `build.sh` (`LIB=<đường dẫn>` ở đầu, ghi ra `${OUT:-…}` ngoài `demo/`); chạy thử từ thư mục đã lưu với `OUT` tạm, rồi kiểm `demo/` không có file mới;
  - `DEMO.md` theo `lib/lemo-opuscar/styles/_template/DEMO.md`;
  - `test.jpg` (ảnh đại diện), `test.mp4` (ngoài git), `demo-checks.json`.

  Mục 10 (Engine) của `STYLE.md` chỉ tới `demo/` trước.
- [ ] T031 [US4] Cập nhật dòng của `dusk-hypothetical` trong `my-styles/README.md` (ghi có phim mẫu). Ghi kết quả SC-008 vào `quickstart.md`.

**Checkpoint**: commit.

---

## Phase 7: Polish

- [ ] T032 [P] Sửa `.claude/skills/style-learn/SKILL.md`:
  - thêm bước sau "Thu thập và đo": `learn shots`, `learn label`, xem các cảnh `check`, `learn label --pass 2 --sample 40`, báo độ nhất quán;
  - trong bước viết phong cách, mục 6 và chiều sâu ghi bằng số kèm `bảng#ô`;
  - thêm bước "Phim mẫu" sau khi lưu (theo `MY-STYLES.md` §5, đi đủ các tầng kiểm);
  - học lại một phong cách đã có thì dùng `save --update`.
- [ ] T033 [P] Sửa `CLAUDE.md`:
  - luồng làm phim: với phong cách riêng, đọc `DEMO.md` và `demo/` của nó trước phong cách gốc; bảng cảnh lập theo `shots.json` của phong cách nếu có;
  - mục Cấu trúc: `learn shots|label`, `focus.py`, `labeler.py`.
- [ ] T034 [P] Sửa `tools/runner/JOB.md` (worker online): cùng hai ý của T033 cho phim, và `qc shots` có thể gọi lượt gán nhãn (một lượt Claude riêng, tính vào việc).
- [ ] T035 Chạy đủ các bộ test: `sh tests/run.sh`, `sh tests/render/run.sh`, `sh tests/learn/run.sh`, `sh tests/ui/run.sh`, `sh tests/filmcheck/run.sh`, `sh tests/online/run.sh`, `sh tests/license/run.sh`. Ghi kết quả.
- [ ] T036 Kiểm SC-007 (`git -C lib/lemo-opuscar status --short` trống; `references/dusk-hypothetical-2/` không còn video); đối chiếu SC-001 … SC-008 trong `quickstart.md`, ghi đạt, đạt một phần hoặc thất bại.

---

## Dependencies & Execution Order

- Setup (T001–T002) → Foundational (T003–T007) → các story.
- **US1** (T008–T013) chỉ cần Foundational. Đây là MVP.
- **US2** cần US1 (lệnh `shots`, `label`, `summary`). T018–T022 là chạy thật, theo thứ tự.
- **US3** cần Foundational (`focus.py`, `labeler.py`) và T016 (`stylerefs`); phần test (T023) làm song song với US2 được. T027 cần US2 xong.
- **US4** cần US2 (phong cách đã học lại) và US3 (để kiểm cách quay).
- Polish sau các story.

## Parallel Examples

- Foundational: T004 ∥ T006 ∥ T007 sau khi T003 và T005 xong.
- US1: T008 ∥ T009, rồi T010 → T011 → T012 → T013.
- US2 và US3 (phần code): T014 ∥ T023, và T015–T017 ∥ T024–T026.
- Polish: T032 ∥ T033 ∥ T034.

## Implementation Strategy

1. **MVP** = Phase 1–3: đo độ nét, gán nhãn, tách cảnh, hồ sơ cách quay trên video thử. Dừng và kiểm.
2. US2 (học lại thật, có tải video và tốn lượt Claude): dừng, báo người dùng thời gian và số lượt Claude ước tính, chờ đồng ý rồi mới chạy T018. Làm như vậy trước T027 và T028.
3. US3, rồi US4 (phim mẫu thật). Mỗi phần xong thì chạy test và commit.
