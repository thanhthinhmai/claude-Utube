---
description: "Tasks for 020 — QC per shot before render"
---

# Tasks: QC theo từng cảnh trước khi render

**Input**: các tài liệu thiết kế ở `specs/020-qc-before-render/`:
- `plan.md`, `spec.md`, `research.md` (R1–R11), `data-model.md`, `quickstart.md`;
- `contracts/cli.md`, `contracts/checks.md`, `contracts/film-page.md`.

**Tests**: bắt buộc. Hiến pháp IV đòi test tự động cho logic quan trọng, và spec có mục Independent Test cho mỗi story.
- Test Python: unittest trong `tests/filmcheck/`, chạy bằng `sh tests/filmcheck/run.sh`.
- Test Node: `node --test` trong `tests/render/`, chạy bằng `sh tests/render/run.sh`.
- Phim thử được sinh bằng code trong `tests/filmcheck/samples.py`, không commit file media.

**Ký hiệu**: `[P]` = chạy song song được (khác file, không phụ thuộc). `[USn]` = user story của spec.

---

## Phase 1: Setup

- [X] T001 Tạo `tools/asr.json` với `{"en": "small.en", "*": "small"}`. Ghi lý do chọn (research R1) trong khoá `"_note"` của file đó và trong docstring của `tools/filmcheck/rhythm.py` (tạo ở T004).
- [X] T002 [P] Thêm `qc-exceptions.json` vào `SKIP_FILE` của `tools/render/lib.mjs`. Thêm ca test vào `tests/render/lib.test.mjs`: file đó đổi thì dấu vân tay không đổi.
- [X] T003 [P] Thêm hàm sinh phim thử vào `tests/filmcheck/samples.py`: `make_tier_film(root, name, *, shots, lines, words, cues=None, cards=None, script=None)`.
  - Hàm ghi `index.html` tối giản (2D canvas) xuất `window.DUR`, `SHOTS`, `CUES`, `CARDS`, `TEXTS`, `READY` theo `contracts/film-page.md`.
  - Hàm cũng ghi `lines.json`, `voices/words.json`, `voices/dur.json`, `narration.json`, `SCRIPT.md`.

---

## Phase 2: Foundational (chặn mọi story)

- [X] T004 Tạo `tools/filmcheck/rhythm.py`: chuyển các hằng `SILENCE_MAX, LONG_PAUSE, CUT_AFTER, KEY_SHOT, TAIL_MAX, EPS` và phần thân của `narration_measures` từ `tools/filmcheck/qc.py` sang.
  - Đổi thành `measure(sentences, words, shots, dur, cues=None, cards=None, style=None) -> (measures, issues)`.
  - Mỗi issue có dạng Issue trong `data-model.md`: `tier, ref, at, rule, severity, measure, limit, text, fix`.
  - Tên luật lấy đúng theo bảng "plan" trong `contracts/checks.md`.
  - `cut_in_sentence` và `cut_too_soon` có `fix` = "move the cut to ≥ <mốc sớm nhất hợp lệ>". Mốc đó là `end + min(0.4, khoảng tới câu sau)`, hoặc đúng lúc câu sau bắt đầu.
- [X] T005 Trong `tools/filmcheck/rhythm.py`, thêm `sentences(lines_rows, words, narration)`:
  - tách lời của `lines.json` theo `. ? ! …` (và `。？！`);
  - gắn từ đầu và từ cuối của mỗi câu lên mốc từ bằng `difflib.SequenceMatcher(autojunk=False)` trên từ đã chuẩn hoá (khối `replace` chia theo tỉ lệ, như `films/pet-swap/timeline.py`);
  - kẹp mốc từ vào `[0, dur dòng]` (FR-004);
  - trả về `[{para, line, n, start, end, text}]` theo `data-model.md`.

  Không dùng dấu câu của bản nhận dạng (FR-003).
- [X] T006 Trong `tools/filmcheck/rhythm.py`, thêm các luật mới:
  - `shot_short` (< 1,1 s);
  - `shot_long` (> `style.shot_max`, mặc định 6 s);
  - `cue_short` (< 1,8 s; tắt trước khi từ cuối của nó nói xong; phụ đề cuối đoạn, trước khoảng nghỉ ≥ 0,6 s, tắt sớm hơn 0,6 s sau từ cuối — đổi ngày 2026-11-12, xem Clarifications);
  - `card_read` (đầu vào là danh sách `{id, at, need, got}`).
  
  Phim < 30 s: không có thay đổi ngưỡng nào (research R3).
- [X] T007 Sửa `tools/filmcheck/qc.py` để `narration_measures` gọi `rhythm.measure` (giữ khoá `measures` cũ: `silence_ratio`, `cuts_bad`, `key_shots_bad`, `long_pauses_bad`, `tail_s`), và `sentences` gọi `rhythm.sentences`. Chạy `sh tests/filmcheck/run.sh`; `tests/filmcheck/test_qc.py` phải đạt nguyên (sửa test chỉ khi lỗi nhịp giả do dấu câu Whisper biến mất, và ghi rõ trong commit).
- [X] T008 Tạo `tools/filmcheck/tiers.py`:
  - `fingerprint(film_dir, part="all"|"voice")`: SHA-256 16 hex, cùng quy tắc bỏ file như `tools/render/lib.mjs` (thư mục `out stills publish .check node_modules`, file `*.mp4 *.log checks.json CHECKS.md qc-exceptions.json`). `part="voice"` chỉ tính `lines.json` và `voices/`.
  - `save_tier(film_dir, tier, result)` ghi qua `report.update` vào `checks.json → tiers.<tier>`, với các trường `pass, fingerprint, at, issues, measures, skipped, seconds`.
  - `load_exceptions` và `add_exception` cho `qc-exceptions.json`. Luật: "`shot` phải có trong `SHOTS`"; "`rule` phải thuộc danh sách luật cho phép ngoại lệ" (`flat dark blown still shot_long text_over_subtitle`); "`reason` không được rỗng, tối đa 200 ký tự".
  - `apply_exceptions(issues, exceptions)`: gắn `excepted`, rồi tính lại `pass` (chỉ lỗi `block` chưa có ngoại lệ mới tính).
- [X] T009 Sửa `tools/filmcheck/report.py`: thêm `tiers: {}` vào `empty()`; thêm mục "Tiers" vào `markdown()` theo `contracts/checks.md`. Mục gồm bảng 5 hàng `voice plan shots render final`; dưới bảng là lỗi còn mở, ngoại lệ kèm lý do, lệch phong cách đã chấp nhận kèm lý do.
- [X] T010 [P] Tạo `tests/filmcheck/test_rhythm.py`:
  - (a) câu theo kịch bản: lời "Your alarm goes off at seven. But it sounds wrong." với bản nhận dạng "at 7, but it sounds wrong," → ranh giới sau "seven", và một cắt đặt ở đó + 0,4 s không bị báo (US3 AC2);
  - (b) mốc âm → 0, mốc vượt dur → dur (US3 AC3);
  - (c) `rhythm.measure` và `qc.narration_measures` cho cùng issues trên phim mẫu của `samples.make_film` (FR-010);
  - (d) hai lần chạy cho kết quả giống hệt (SC-006);
  - (e) mỗi luật mới có một ca đạt và một ca lỗi.
- [X] T011 [P] Tạo `tests/filmcheck/test_tiers.py`:
  - dấu vân tay đổi khi sửa `index.html`, không đổi khi sửa `qc-exceptions.json` hay `checks.json`;
  - ngoại lệ bị từ chối khi sai mã cảnh, sai luật hoặc lý do rỗng;
  - `apply_exceptions` tính lại `pass`.

**Checkpoint**: `sh tests/filmcheck/run.sh` đạt. Commit.

---

## Phase 3: User Story 1 — Kiểm kế hoạch trước khi render (P1) 🎯 MVP

**Mục tiêu**: `qc plan` báo mọi lỗi nhịp theo mã cảnh trong ≤ 10 s; `render` từ chối chạy khi chưa đạt.

**Independent Test**: phim thử `plan-10` có 10 lỗi cài sẵn → báo đủ 10, đúng mã cảnh, 0 lỗi nhầm, ≤ 10 s. `render` khi đó trả mã 1 và chưa mở trình duyệt. Sửa xong thì đạt và render chạy.

### Tests

- [X] T012 [P] [US1] Tạo `tests/filmcheck/test_plan.py`:
  - phim `plan-10` (sinh bằng `make_tier_film`) có 10 lỗi: 3 `cut_in_sentence`, 2 `cut_too_soon`, 2 `key_shot_short`, 1 `shot_long`, 1 `silence`, 1 `tail`;
  - `qc plan --json` → đúng 10 issue, đúng `ref`, mã 1, ≤ 10 s;
  - bản sửa → mã 0;
  - phim không giọng → chỉ có `shot_short`, `shot_long`, `tail`, `card_read` (US1 AC6);
  - phim không có `SHOTS` → in `no shot list`, các luật cảnh bị bỏ qua.
- [X] T013 [P] [US1] Thêm vào `tests/filmcheck/test_cli.py` các ca cổng render (gọi `cli.py render-gate`):
  - chưa kiểm → mã 1, in lệnh cần chạy;
  - đã đạt → mã 0;
  - đạt rồi sửa `index.html` → mã 1 (US1 AC4);
  - `render --skip-checks ""` → mã 2;
  - `--skip-checks "test"` → ghi `tiers.render.skipped_checks` (US1 AC5).

### Implementation

- [X] T014 [US1] Tạo `tools/filmcheck/plan.mjs` (`@ts-check`, dùng `openDemo` của `core/render/page.mjs` như `texts.mjs`):
  - đọc `window.DUR`, `SHOTS`, `CUES`, `CARDS` sau `READY`, không gọi `render(t)`;
  - in một dòng JSON `{dur, shots|null, cues|null, cards|null}`.
- [X] T015 [US1] Tạo `tools/filmcheck/plancheck.py`:
  - `run(film_dir, lib)` gọi `plan.mjs` và chuẩn hoá `SHOTS` theo data-model: "duy nhất trong phim", "`0 ≤ t0 < t1 ≤ DUR`", "nối liền (lệch tối đa 1/fps)". Thiếu `id` thì gán `S<n>` và cảnh báo.
  - phụ đề: `CUES`, nếu không có thì `cues.json`, rồi `<phim>.srt`.
  - thẻ chữ: `CARDS`; không có thì chạy `node core/render/readcheck.mjs` của thư viện, đọc dòng `OK/FAIL … need … got …`, và ghi `skipped`/ghi chú "cards via readcheck".
  - lưu `.check/plan-input.json` gắn dấu vân tay; nguồn chưa đổi thì đọc lại file này.
  - gọi `rhythm.sentences` và `rhythm.measure`, áp ngoại lệ, rồi `tiers.save_tier(…, "plan", …)` với `measures.sentences` và `seconds`.
- [X] T016 [US1] Sửa `tools/filmcheck/cli.py`: trong parser `qc`, đọc từ đầu tiên. Nếu nó thuộc `voice plan shots except accept-style final` thì đó là lệnh con; nếu không thì là tên phim (như cũ).
  - Thêm `cmd_qc_plan`: in mỗi issue một dòng theo mẫu của `contracts/cli.md`, cuối cùng `✓/✗ plan: …`.
  - Thêm `--json`; mã thoát 0/1/2.
- [X] T017 [US1] Sửa `tools/filmcheck/cli.py`: thêm lệnh ẩn `render-gate <phim> [--skip-checks R]` theo mục "Cổng render" của `contracts/checks.md`. Ở bước này chỉ kiểm `tiers.plan`; phần `shots` được thêm ở T026. Lệnh in các dòng `✗ render: …` và trả mã 1/0/2.
- [X] T018 [US1] Sửa `cmd_render` trong `bin/studio`:
  - tách `--skip-checks <lý do>` khỏi đối số;
  - gọi `python cli.py render-gate` trước `record.mjs`; mã ≠ 0 thì thoát với cùng mã;
  - khi có `--skip-checks` thì đặt `STUDIO_RENDER_SKIPPED_CHECKS` để `record.mjs` ghi dòng `render: checks skipped — <lý do>` vào `render.log`.
- [X] T019 [US1] Sửa `tools/render/record.mjs`: nếu có `STUDIO_RENDER_SKIPPED_CHECKS` thì ghi dòng đó ngay sau khi tạo `render.log`.
- [ ] T020 [US1] Chạy thật trên `films/pet-swap`:
  - trước khi đo, thêm `window.CARDS` (`[[t0, t1, id, text]]`, lấy từ các thẻ mà `TEXTS` đang đọc) vào `films/pet-swap/main.js` (file của phim, ngoài git), để `qc plan` không phải chạy `readcheck`. FR-008 chỉ cam kết với phim có `CARDS`; ghi thêm thời gian của đường `readcheck` để so;
  - `sh bin/studio qc plan pet-swap`: kỳ vọng 0 lỗi nhịp; ghi lại thời gian (FR-008 ≤ 10 s).
  - Thêm ca test `tests/filmcheck/test_plan.py::test_pet_swap_first_render`, bỏ qua khi không có `films/pet-swap`. Ca test dựng lại các mốc cắt của lần render đầu (mỗi cắt = đầu câu − 0,06 s, cảnh đầu đoạn bắt đầu giữa khoảng nghỉ) trên `timeline.json`, rồi kiểm ≥ 80 lỗi `cut_*` và mọi cảnh chứa câu cuối < 2,5 s đều bị báo (SC-002).
  - Kết quả ghi vào `specs/020-qc-before-render/quickstart.md` (mục Kết quả).

**Checkpoint**: US1 dùng được độc lập. Commit.

---

## Phase 4: User Story 2 — Mỗi cảnh một ảnh, kèm kiểm phong cách (P2)

**Mục tiêu**: `qc shots` chụp ảnh giữa mỗi cảnh, báo lỗi khung theo mã cảnh, so phong cách, tạo bảng ảnh. Cổng render chặn khi còn lỗi khung; lệch phong cách cần lý do.

**Independent Test**: phim `shots-6` có 6 cảnh lỗi và 30 cảnh tốt → báo đủ 6, ≤ 1 cảnh tốt bị báo nhầm, có bảng ảnh ghi mã cảnh.

### Tests

- [X] T021 [P] [US2] Tạo `tests/filmcheck/test_shots.py`:
  - phim `shots-6` (2D canvas, sinh bằng `make_tier_film`): một cảnh một màu, một cảnh quá tối, một cảnh cháy, một chữ thiếu phông (U+E000), một thẻ đè vùng phụ đề lúc có phụ đề, cả phim tối hơn khoảng `luma_p50` của một `qc.json` thử; thêm 30 cảnh tốt và 1 thẻ chữ tối trơn hợp lệ (US2 AC4);
  - kỳ vọng: đủ 6 lỗi, ≤ 1 báo nhầm, có `.check/shots/sheet-1.jpg`, thẻ chữ hợp lệ không bị `flat`.
  
  Phần chấm (`shotcheck.score`) được test thêm bằng số đo giả, không cần trình duyệt.
- [X] T022 [P] [US2] Tạo `tests/filmcheck/test_stylerefs.py`:
  - đọc `my-styles/dusk-hypothetical/EVIDENCE.md` → `luma_p50 [0.198, 0.299]`, `saturation_p50 [0.319, 0.504]`, `cuts_per_min [16, 26]`, `loudness_range [2.4, 3.3]`;
  - `qc.json` ghi đè từng khoá;
  - phong cách không có số đo → `{}`, kèm "bỏ qua so phong cách".

### Implementation

- [X] T023 [P] [US2] Tạo `tools/filmcheck/stylerefs.py`: `load(film_dir) -> dict` theo research R6 và mục Style references của data-model.
  - slug lấy từ `qc.style_slug`;
  - khoảng `a–b` đọc từ bảng "Key numbers" của `my-styles/<slug>/EVIDENCE.md` (chấp nhận `–`, `-`, `to`, dấu `−`);
  - `my-styles/<slug>/qc.json` ghi đè.

  Sửa `qc.still_limit` để dùng `stylerefs.load(d).get("still_max")`.
- [X] T024 [US2] Tạo `tools/filmcheck/shots.mjs` (`@ts-check`, chạy bằng trình duyệt của `render_env` như `record.mjs`, ở 960×540):
  - với mỗi cảnh: `render((t0+t1)/2)`; cảnh có thẻ trong `CARDS` thì thêm ảnh ở giữa khoảng thẻ;
  - chụp `.check/shots/<id>.jpg` và đọc `TEXTS(t)`;
  - đo trong trang bằng canvas: dải letterbox (hàng có độ sáng < 0,03 và độ lệch < 0,01), tỉ lệ màu nhiều nhất sau lượng tử 4 bit (bỏ hộp chữ và letterbox), độ lệch chuẩn độ sáng, `luma_p50`, `saturation_p50`, tỉ lệ điểm > 0,98, tỉ lệ diện tích chữ;
  - vẽ bảng ảnh (6 cột, ≤ 48 ô mỗi tấm, nhãn mã cảnh, viền đỏ cho cảnh mà Python báo lỗi qua tham số `--mark`) vào `.check/shots/sheet-<n>.jpg`;
  - in JSON `{mode, renderer, frames: [...]}`.
- [X] T025 [US2] Tạo `tools/filmcheck/shotcheck.py`:
  - `score(frames, cues, style) -> issues` theo bảng "shots" của `contracts/checks.md`:
    - `flat`: > 0,60 hoặc độ lệch < 0,04, và không có chữ chiếm ≥ 2% khung;
    - `dark`: p50 < `dark_p50` (mặc định 0,04);
    - `blown`: > `blown_share` (mặc định 0,25);
    - `text_over_subtitle`: hộp chữ cắt `subtitle_zone` (mặc định 18% dưới) lúc có phụ đề;
    - `missing_glyph`: dùng `qc.missing_glyphs` trên chữ `TEXTS` và phụ đề.
  - So phong cách (`warn`): trung vị theo trọng số độ dài cảnh của `luma_p50` và `saturation_p50`, và số cắt mỗi phút (bỏ khi phim < 30 s). Không có số đo thì ghi `skipped: "style: no measurements"`.
  - `run()`: in thời gian ước tính trước (≈ 0,4 s mỗi ảnh khi GPU, 1 s khi phần mềm); gọi `shots.mjs` hai lượt (đo, rồi vẽ bảng ảnh có đánh dấu); áp ngoại lệ; `tiers.save_tier(…, "shots", …)`.
- [X] T026 [US2] Sửa `tools/filmcheck/cli.py`:
  - thêm `cmd_qc_shots`, `cmd_qc_accept_style` và `cmd_qc_except` (`--list`, `--remove`) theo `contracts/cli.md`. `accept-style` ghi `tiers.shots.style_accept` và từ chối (mã 2) khi lý do rỗng hoặc không có cảnh báo. `except` tính lại `pass` của tầng `plan` và `shots` từ issues đã lưu;
  - mở rộng `render-gate`: lỗi `block` của `shots` đã sửa hoặc có ngoại lệ, cùng dấu vân tay, và mọi `warn` có `style_accept.reason`.
- [X] T027 [US2] Sửa `cmd_filmcheck` trong `bin/studio`: gọi `render_env` cho `qc shots` (và `qc plan`, vì nó mở trang). Hiện chỉ `qc` và `publish` có.
- [X] T028 [US2] Chạy thật `sh bin/studio qc shots pet-swap` với GPU:
  - ≤ 3 phút (SC-003);
  - `style_luma` ≈ 0,13 ngoài 0,198–0,299, `style_saturation` ≈ 0,53 ngoài 0,319–0,504 (SC-004);
  - mở `sheet-1.jpg` bằng mắt;
  - `render` bị chặn; `accept-style --reason` xong thì cổng đạt.
  
  Ghi kết quả vào quickstart.

**Checkpoint**: US2 xong. Commit.

---

## Phase 5: User Story 3 — Kiểm giọng ngay sau khi tạo (P3)

**Mục tiêu**: `voice asr` dùng mô hình chung; `qc voice` báo khoảng nghỉ trong dòng, lệch lời, lệch đuôi theo mã dòng.

**Independent Test**: dòng có khoảng nghỉ 0,9 s → bị báo đúng mã dòng, 70 dòng ≤ 30 s. Hai ca US3 AC2 và AC3 không có lỗi cắt giả.

### Tests

- [ ] T029 [P] [US3] Tạo `tests/filmcheck/test_voice.py`:
  - phim `voice-pause`: 70 dòng wav sinh bằng ffmpeg (sine + 0,9 s lặng ở giữa `l17`) và `words.json` khớp → một `pause_in_line` ở `l17`, ≤ 30 s (SC-007);
  - dòng `"recorded": true` → lời khuyên là "check the recording";
  - `tail_mismatch` khi |từ cuối − dur| > 0,5 s;
  - `asr_mismatch` khi từ lệch lời.
- [ ] T030 [P] [US3] Thêm vào `tests/filmcheck/test_cli.py` ca `voice asr`: dùng biến thử `STUDIO_ASR_DRY=1` để chỉ in lệnh. Kiểm `--model small.en` cho `en` và `--model small` cho `zh`, đọc từ `tools/asr.json`.

### Implementation

- [ ] T031 [US3] Tạo `tools/filmcheck/voicecheck.py`:
  - đọc `lines.json`, `voices/words.json`, `voices/dur.json`, kẹp mốc như `rhythm`;
  - `pause_in_line`: khoảng ≥ 0,8 s giữa hai từ, được `ffmpeg silencedetect=n=-40dB:d=0.6` trên file wav xác nhận;
  - `asr_mismatch`: độ giống của từ (difflib) < 0,92;
  - `tail_mismatch`: lệch > 0,5 s;
  - ghi `tiers.voice` với `fingerprint(part="voice")`.
- [ ] T032 [US3] Sửa `tools/filmcheck/cli.py`: thêm `cmd_qc_voice` (mẫu dòng theo `contracts/cli.md`) và lệnh `voice-asr <phim> [--lang]`. `voice-asr` đọc `tools/asr.json`; ngôn ngữ lấy từ `--lang`, rồi `CHANNEL_BRIEF.md`, rồi `en`. Lệnh chạy `$LIB/.venv/bin/python $LIB/core/tts/asr_check.py lines.json voices --lang L --model M` và in `model: M`.
- [ ] T033 [US3] Sửa `bin/studio`: thêm lệnh `voice` (`voice asr <phim>`), chuyển cho `cmd_filmcheck voice-asr`. Thêm vào `usage`.
- [ ] T034 [P] [US3] Sửa `tools/style-learn/sl/speech.py`: lấy tên mô hình mặc định từ `tools/asr.json` theo ngôn ngữ, thay cho giá trị viết cứng. Sửa `tools/studio/studio/host.py`: `WHISPER_MODELS = ("small.en", "small")`, cập nhật chú thích. Cập nhật test liên quan trong `tests/learn/` và `tests/ui/` nếu chúng kiểm tên mô hình.
- [ ] T035 [US3] Chạy thật `sh bin/studio voice asr pet-swap` rồi `sh bin/studio qc voice pet-swap`. Chạy `qc plan pet-swap` hai lần và so `silence_ratio` và các mốc câu (SC-006). Ghi kết quả vào quickstart.

**Checkpoint**: US3 xong. Commit.

---

## Phase 6: User Story 4 — Kiểm từng đoạn trong lúc render (P4)

**Mục tiêu**: mỗi đoạn vừa ghi được kiểm khung đen và hình đứng yên; lỗi thì dừng sớm và giữ các đoạn trước.

**Independent Test**: phim có cảnh đứng yên 8 s ở giữa → dừng trong vòng 1 đoạn sau đoạn lỗi, báo mã cảnh, giữ các đoạn trước. Sửa rồi chạy lại: chỉ ghi lại từ chỗ lỗi.

### Tests

- [ ] T036 [P] [US4] Tạo `tests/render/chunkcheck.test.mjs` cho các hàm thuần của `chunkcheck.mjs`:
  - đọc log ffmpeg → khoảng đen, khoảng đứng yên;
  - nối hình đứng yên qua ranh giới đoạn khi đoạn kề đã kiểm (cả khi kiểm lệch thứ tự);
  - ngưỡng `still_max`, bỏ qua cảnh có ngoại lệ `still`;
  - map thời điểm → mã cảnh theo `SHOTS`.
- [ ] T037 [P] [US4] Thêm vào `tests/render/record.test.mjs` (phim `tests/render/fixtures/still-8`, 2D, khoảng 30 s, cảnh đứng yên 8 s từ giây 12; `STUDIO_RENDER_CHUNK` nhỏ):
  - dừng với mã 1, báo mã cảnh, các đoạn trước còn, có `STOPPED.json` (SC-009);
  - `--no-stop` ghi hết và liệt kê lỗi;
  - sửa cảnh (đổi một tham số của cảnh lỗi) rồi chạy lại → log có `reused N chunks`, N = số đoạn trước chỗ lỗi;
  - `--fresh` → `reused 0`.

### Implementation

- [ ] T038 [US4] Tạo `tools/render/chunkcheck.mjs`:
  - `checkChunk(file, {fps, t0})` chạy `ffmpeg -vf scale=320:-2,blackdetect=d=0.25:pix_th=0.06,freezedetect=n=0.003:d=0.5`, rồi ghi `c_NNNN.json` với `{black: [], stills: [], head_still, tail_still}`;
  - `combine(results, {stillMax, shots, exceptions})` trả về lỗi `black_frames` và `still` có `{chunk, shot, at, rule, measure}`.
- [ ] T039 [US4] Sửa `tools/render/record.mjs`:
  - sau `renameSync` của mỗi đoạn, gọi `checkChunk`, rồi `combine`;
  - lỗi và không có `--no-stop`: đặt `abort`, xoá đoạn lỗi và các đoạn sau, ghi `out/.chunks/STOPPED.json` (`{fingerprint, chunk_size, fps, size, first_bad, shot, rule, at, shots_hash}`), in `✗ render: chunk N (<shot>, <t> s) <rule> …`, mã 1;
  - `--no-stop`: gom lỗi, in ở cuối, mã 1 nếu có lỗi;
  - đọc `SHOTS` từ trang (đã mở sẵn trong `openPage`) và `still_max`, ngoại lệ (qua biến `STUDIO_QC_LIMITS` mà `bin/studio` đặt từ `stylerefs` và `qc-exceptions.json`).
- [ ] T040 [US4] Sửa `tools/render/record.mjs` để dùng lại đoạn (research R8):
  - khi bắt đầu, nếu có `STOPPED.json` cùng `chunk_size`, `fps`, `size` và không có `--fresh`: chép các đoạn của thư mục cũ có `z ≤ first_bad.a`, và nằm trước cảnh đầu tiên có dòng `SHOTS` khác `shots_hash` cũ, sang thư mục mới;
  - log `reused N chunks from the stopped run`;
  - ghi `tiers.render.reused_chunks` qua `tools/filmcheck/cli.py render-done` (lệnh ẩn mới, cũng ghi `tiers.render.pass` và `stopped`);
  - xoá `STOPPED.json` khi ghi xong mà đạt.
- [ ] T041 [US4] Sửa `cmd_render` trong `bin/studio`: chuyển `--no-stop` và `--fresh` cho `record.mjs`; đặt `STUDIO_QC_LIMITS` (JSON `{still_max, exceptions}` do `cli.py qc-limits <phim>` in ra); sau `record.mjs` gọi `cli.py render-done`. Cập nhật `usage`.

**Checkpoint**: `sh tests/render/run.sh` đạt. Commit.

---

## Phase 7: User Story 5 — Kiểm cuối và gói đăng dùng lại kết quả đã đạt (P5)

**Mục tiêu**: `qc` cuối dùng cùng luật nhịp và so dải âm lượng; gói đăng dùng phụ đề đã kiểm; thumbnail không có phụ đề.

**Independent Test**: bản mix có dải âm lượng 1,5 LU trên phong cách 2,4–3,3 → bị báo. Gói đăng `pet-swap` có 0 dòng dưới 1 s. Thumbnail không dính phụ đề.

### Tests

- [ ] T042 [P] [US5] Thêm vào `tests/filmcheck/test_qc.py`:
  - `loudness_range` (`warn`) với `qc.json` thử `[2.4, 3.3]` trên bản mix nén mạnh;
  - `av_sync` khi tiếng dài hơn hình 0,3 s;
  - `qc` dùng mốc cắt của `.check/plan-input.json` khi có;
  - một phim đạt `qc plan` thì có 0 lỗi nhịp trong `qc` (SC-005).
- [ ] T043 [P] [US5] Thêm vào `tests/filmcheck/test_publish.py` và `tests/filmcheck/test_thumbs.py`:
  - phụ đề gói đăng giống `CUES` của tầng 1 từng dòng (US5 AC2);
  - tầng 1 chưa đạt (có `CUES`) → lỗi `subtitles_not_passed`;
  - thumbnail của phim thử có phụ đề DOM: vùng phụ đề sai khác < 2/255 so với khung đã ẩn hết chữ (SC-008);
  - trang nhận `window.CLEAN === true`.

### Implementation

- [ ] T044 [US5] Sửa `tools/filmcheck/qc.py`:
  - mốc cắt lấy từ `SHOTS` trong `.check/plan-input.json` khi có (không chạy `scdet`), luật từ `rhythm.measure`;
  - thêm `loudness_range`: đo bằng `ffmpeg ebur128` (LRA), so với `stylerefs` thành `warn`;
  - thêm `av_sync`: dùng `ffprobe` độ dài stream tiếng và hình, lỗi khi lệch > 0,1 s;
  - ghi thêm `tiers.final` qua `tiers.save_tier`;
  - báo cáo liệt kê cảnh báo phong cách còn mở và lý do đã chấp nhận (FR-013).
  
  Thêm ngưỡng mới vào `report.THRESHOLDS`.
- [ ] T045 [US5] Sửa `tools/filmcheck/publish.py` (`subtitle_cues`):
  - phim có `.check/plan-input.json` với `cues`: dùng đúng các dòng đó (tách 2 dòng ≤ 42 bằng `wrap`, giữ mốc) khi `tiers.plan.pass` đúng và cùng dấu vân tay; nếu không thì trả lỗi `subtitles_not_passed` ("run: sh bin/studio qc plan <phim>");
  - phim cũ không có tầng 1: giữ cách cắt hiện có, kèm ghi chú.
- [ ] T046 [US5] Sửa `tools/filmcheck/thumbs.mjs`: trước `render(t)`, đặt `window.CLEAN = true`; sau đó thêm thẻ `<style>` có `body *{visibility:hidden} canvas,#studio-thumb,#studio-thumb *{visibility:visible}` trước khi chụp (research R9).
- [ ] T047 [US5] Thêm `window.CLEAN` vào `films/pet-swap/main.js`: không vẽ phụ đề và thẻ khi `CLEAN`. Đây là file của phim, ngoài git, không phải `lib/`. Sửa trang làm đổi dấu vân tay, nên chạy lại `sh bin/studio qc plan pet-swap` (phải đạt) trước. Rồi chạy `sh bin/studio publish pet-swap`: 0 dòng phụ đề < 1 s, 3 thumbnail sạch, mở bằng mắt (SC-008). Ghi kết quả vào quickstart.

**Checkpoint**: US5 xong. Commit.

---

## Phase 8: Polish & luồng làm phim

- [ ] T048 [P] Sửa `CLAUDE.md`, luồng làm phim:
  - bước 3 và mục Dựng hình theo thứ tự `voice asr` → `qc voice` → `qc plan` → `qc shots` → `render` → mux → `qc` → `publish`;
  - hợp đồng trang `SHOTS/CUES/CARDS/CLEAN`;
  - `qc except` và `accept-style`;
  - `--skip-checks` chỉ cho bản thử;
  - thêm lệnh vào mục Cấu trúc (FR-020).
- [ ] T049 [P] Sửa `tools/runner/JOB.md` cùng thứ tự đó cho worker online, mỗi tầng một `job step` trong các bước sẵn có (`Voice`, `Picture`, `Render`, `Self-check`). Thay dòng "Self-check … `qc`" hiện tại.
- [ ] T050 [P] Cho worker online và phần lõi của app dùng `small.en` (FR-002):
  - đọc `deploy/job.Dockerfile`, `deploy/core.Dockerfile`, `desktop/core-build/build-linux.sh`, `build-mac.sh`, `smoke-core.sh`; chỗ nào tải trước hoặc gọi mô hình Whisper thì đổi sang mô hình của `tools/asr.json`;
  - `smoke-core.sh` thêm `--model small.en`;
  - chỗ nào không cần đổi thì ghi lý do vào commit;
  - kiểm `desktop/core-build/credits-check.py` không báo gì mới.
- [ ] T051 [P] Hiện kết quả các tầng trên app (edge case "Chế độ online"):
  - `tools/studio/studio/resources.py` trả thêm `checks.json → tiers` (5 tầng: đạt hay không, số lỗi, số cảnh báo, ngoại lệ, thời điểm; tối đa 20 lỗi còn mở);
  - `tools/studio/studio/web/app.js` vẽ bảng "Checks by stage" trên trang phim và trang việc có `links.film`;
  - thêm test vào `tests/ui/` (API trả `tiers`; trang có bảng khi phim có `tiers`, không có bảng khi chưa có).
- [ ] T052 Chạy đủ 5 bộ test của xưởng: `sh tests/run.sh`, `sh tests/render/run.sh`, `sh tests/learn/run.sh`, `sh tests/ui/run.sh`, `sh tests/filmcheck/run.sh`. Thêm `sh tests/online/run.sh` nếu `JOB.md` đổi. Ghi kết quả.
- [ ] T053 Kiểm SC-010: `git diff --stat main -- lib/` trống. Chạy kịch bản 11 của quickstart (phim qua tầng 1–3, mux, `qc` → 0 lỗi nhịp, SC-005). Đối chiếu từng SC-001 … SC-010 trong `quickstart.md`, ghi đạt, đạt một phần hoặc thất bại.

---

## Dependencies & Execution Order

- Setup (T001–T003) → Foundational (T004–T011) → các story.
- **US1** (T012–T020) chỉ cần Foundational. Đây là MVP.
- **US2** cần T015 (`plan-input.json` cho `CUES` và `SHOTS`) và T017 (cổng).
- **US3** chỉ cần Foundational (T005). Làm song song với US1 được.
- **US4** cần T018 (`cmd_render`) và T023 (`stylerefs` cho `still_max`).
- **US5** cần T015 (phụ đề tầng 1) và T023.
- Polish sau khi các story xong.

## Parallel Examples

- Foundational: T010 ∥ T011 (hai file test khác nhau) sau khi T004–T009 xong.
- US1: T012 ∥ T013 (test), rồi T014 → T015 → T016 → T017 → T018 ∥ T019.
- US2: T021 ∥ T022 ∥ T023, rồi T024 → T025 → T026.
- US3: T029 ∥ T030 ∥ T034, rồi T031 → T032 → T033.
- US4: T036 ∥ T037, rồi T038 → T039 → T040 → T041.
- Polish: T048 ∥ T049 ∥ T050 ∥ T051.

## Implementation Strategy

1. **MVP** = Phase 1–3: câu theo kịch bản, luật chung, `qc plan`, cổng render. Đây là phần đã gây cả hai lần render lại của `pet-swap`. Dừng và kiểm chứng SC-001, SC-002 trước khi đi tiếp.
2. Thêm US2 (bắt góc máy hỏng, lệch màu), rồi US3, US4, US5. Mỗi story xong: chạy test và commit.
3. Mỗi lần chạy thật trên `pet-swap` ghi số đo vào quickstart (hiến pháp IV).
