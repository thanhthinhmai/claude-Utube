# Tasks: Học phong cách từ video tham chiếu

**Input**: Design documents from `specs/002-style-learning/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (learn-cli.md, profile-schema.md, skill-flow.md), quickstart.md

**Tests**: Bắt buộc theo hiến pháp IV. Test chạy bằng `sh tests/learn/run.sh`, offline, trên video tổng hợp tạo bằng ffmpeg; không cần mạng hay mô hình chép lời.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Tạo `tools/requirements-learn.txt` (`numpy`, `Pillow`) và `tools/requirements-learn-extra.txt` (`yt-dlp`, `faster-whisper`); thêm `tools/.venv/` vào `.gitignore`
- [ ] T002 Thêm `deps learn [--extra]` vào `bin/studio`: tạo `tools/.venv` (`uv venv` nếu có, không thì `python3 -m venv`; Python ≥ 3.11), cài requirements, đánh dấu bằng checksum để chạy lại không cài lại; không động tới `lib/`
- [ ] T003 Thêm `learn <lệnh> …` vào `bin/studio`: chạy `tools/.venv/bin/python tools/style-learn/learn.py`; chưa có venv → mã 1 kèm "sh bin/studio deps learn"
- [ ] T004 [P] Tạo khung `tools/style-learn/learn.py` (argparse, các lệnh con theo contracts/learn-cli.md, mã thoát 0/1/2) và gói `tools/style-learn/sl/__init__.py`

## Phase 2: Foundational (Blocking Prerequisites)

- [ ] T005 Viết `tools/style-learn/sl/refset.py`: đọc/ghi `set.json` theo data-model.md (slug `[a-z0-9-]` 3–40 ký tự; `max_seconds` mặc định 180, giới hạn 30–1800; `state` `fetched → measured → transcribed` hoặc `skipped` kèm `skip_reason`; `source_sig = size:mtime`); ghi file nguyên tử
- [ ] T006 [P] Viết `tools/style-learn/sl/probe.py`: ffprobe (`width,height,fps,duration,nb_frames`), `orientation`, chọn `segments` theo research.md §2 (≤ 180 s toàn bộ; > 180 s: 60 s đầu + 4 × 30 s cách đều), số khung mong đợi
- [ ] T007 [P] Viết `tools/style-learn/sl/frames.py`: sinh từng khung numpy `H×320×3` qua `ffmpeg -ss -t … scale=320:-2:flags=area,format=rgb24 -f rawvideo` cho mỗi đoạn, kèm thời điểm gốc
- [ ] T008 Tạo `tests/learn/make_fixtures.py` (ffmpeg `lavfi`, 30 fps): `cuts.mp4` (5 cắt cứng, 1 chớp sáng 4 khung, 1 hoà tan 12 khung), `pan_fast.mp4` (2 px/khung ở rộng 320), `pan_slow.mp4` (0,3 px/khung ở 720), `flat.mp4` (màu đặc, luma biết trước), `long.mp4` (300 s, để kiểm `segments`), `tone.mp4` (âm 1 kHz có 2 khoảng lặng 0,5 s và 1 s), `portrait.mp4` (1080×1920); tuỳ chọn `--perf` tạo bộ khoảng 18 phút (20 video 54 s, có cắt, pan, màu thay đổi) cho SC-005; và `tests/learn/run.sh` gọi `python -m unittest discover tests/learn`

**Checkpoint**: Đọc được video và chọn được phần được đo.

## Phase 3: User Story 1 - Đo bộ video tham chiếu (Priority: P1) 🎯 MVP

**Goal**: `learn fetch --files` + `measure` + `summary` (+ `transcribe` khi có faster-whisper) tạo hồ sơ đo đủ.

**Independent Test**: `sh tests/learn/run.sh` phần US1 xanh.

### Tests for User Story 1

- [ ] T009 [P] [US1] `tests/learn/test_probe_frames.py`: số khung đọc = mong đợi đúng bằng với video đo toàn bộ, ±1 mỗi đoạn với video đo theo đoạn (SC-001); `long.mp4` → 5 đoạn, tổng 180 s; `portrait.mp4` → `orientation=portrait`, ảnh 320×568
- [ ] T010 [P] [US1] `tests/learn/test_motion.py`: `pan_fast` đo 2 px/khung ±10% đúng hướng; `pan_slow` tính là đứng yên (ngưỡng `motion·720 < 0,5`); `cuts.mp4` phát hiện 5/5 cắt, 0 báo nhầm, chớp sáng vào `flashes`, hoà tan vào `soft_transitions` (SC-002)
- [ ] T011 [P] [US1] `tests/learn/test_color_audio.py`: `flat.mp4` luma sai ≤ 0,02, `dark`/`bright` đúng; bảng màu của khung 3 màu đặc ra đúng 3 màu ΔE < 5 kèm `palette_note`; video nhiều màu (dải màu) ra đủ 6 màu; `tone.mp4` LUFS là số hữu hạn, khoảng lặng tổng 1,5 s ±0,1, `silence_count = 2`
- [ ] T012 [P] [US1] `tests/learn/test_speech.py`: tốc độ đọc từ `words.json` giả (40 từ trong 10 s, 1 khoảng ngắt 1 s) = 4,44 từ/s ±10%; đơn vị `chars/s` với văn bản tiếng Trung giả
- [ ] T013 [US1] `tests/learn/test_pipeline.py`: `fetch --files` 3 video → `set.json` đúng; `measure` ghi `frames.csv` (đúng thứ tự cột của profile-schema.md), `video.json` (`schema: "style-learn/1"`), bảng ảnh mỗi 2 giây; video hỏng → `skipped`, video khác vẫn đo; chạy lại không đo lại video đã xong (FR-011); `summary.json` có `median/min/max`, `low_count_warning=true` khi < 5 video; `fetch --channel --count 2` hoặc `31` → mã 2 (FR-002, giới hạn 3–30)

### Implementation for User Story 1

- [ ] T014 [P] [US1] Viết `tools/style-learn/sl/motion.py`: phase correlation (Hann, nội suy parabol, độ tin cậy đỉnh, `motion_ok` khi ≥ 0,05) và phát hiện cắt, chớp sáng, hoà tan theo research.md §5
- [ ] T015 [P] [US1] Viết `tools/style-learn/sl/color.py`: luma Rec.709, tương phản, bão hoà HSV, `dark` (< 0,06), `bright` (> 0,94), sRGB→Lab D65, k-means k = 8 seed cố định 25 vòng, gộp cụm ΔE76 < 5, giữ 6 cụm lớn nhất (`palette_note` khi ít hơn), ΔE76
- [ ] T016 [P] [US1] Viết `tools/style-learn/sl/audio.py`: `ebur128` (I, LRA) trên các đoạn; RMS 50 ms ở 16 kHz, lặng < −45 dBFS ≥ 250 ms; `first_voice_t`
- [ ] T017 [P] [US1] Viết `tools/style-learn/sl/speech.py`: tốc độ đọc từ `words.json` (research.md §8); hàm chép lời bằng faster-whisper chỉ nạp khi gọi (thiếu gói → lỗi rõ ràng)
- [ ] T018 [P] [US1] Viết `tools/style-learn/sl/sheets.py`: ảnh ghép mỗi 2 giây, lưới 10 cột, ô 128 px (ngang) / 72 px (dọc), nhãn thời gian, JPEG q80, tên `<id>_<NNNN>.jpg`
- [ ] T019 [US1] Viết `tools/style-learn/sl/measure.py`: đo một video trong một lượt đọc khung (motion, color, sheets), ghi `frames.csv` và `video.json` (data-model.md VideoProfile); ghi vào file tạm rồi đổi tên; cập nhật `state` và `source_sig`
- [ ] T020 [US1] Viết `tools/style-learn/sl/summary.py`: gộp theo `orientation`, `majority_orientation`, `dispersion_warnings`, `skipped`, `low_count_warning`; ghi `summary.json` và `summary.md`
- [ ] T021 [US1] Viết `tools/style-learn/sl/fetch.py`: `--files` (chép vào `videos/`), `--videos`/`--channel` qua yt-dlp (`--count` mặc định 12, ngoài 3–30 → mã 2) (nạp khi gọi; `--playlist-end`, ≤ 720p, `--write-info-json`, ghi `audio_language`, `title`, `channel`); in thông báo FR-001a trước khi tải; nền tảng bị chặn hoặc thiếu yt-dlp → mã 1 kèm hướng dẫn `--files`
- [ ] T022 [US1] Nối các lệnh `fetch`, `measure`, `transcribe`, `summary` trong `tools/style-learn/learn.py` theo contracts/learn-cli.md (in tiến độ khung/giây)

**Checkpoint**: US1 chạy và test độc lập được.

## Phase 4: User Story 2 - Viết phong cách từ hồ sơ đo (Priority: P2)

**Goal**: Skill hướng dẫn Claude phân tích bằng 3 agent, kiểm tra chéo, viết `STYLE.md` có bằng chứng, chặn tên, dừng duyệt lần 1.

**Independent Test**: `check-names` xanh trong test; skill và template đủ theo contracts/skill-flow.md.

- [ ] T023 [P] [US2] `tests/learn/test_names.py`: bắt tên kênh, `@handle`, tiêu đề, tên có dấu viết không dấu, chuỗi 6 từ trùng bản chép lời; không bắt cụm 5 từ; mã thoát 0/1 và vị trí `file:dòng` (SC-003)
- [ ] T024 [US2] Viết `tools/style-learn/sl/names.py` và lệnh `check-names` theo research.md §12
- [ ] T025 [P] [US2] Viết `.claude/skills/style-learn/templates/aspect-report.md` (Claim · Evidence · Confidence; mục cho từng khía cạnh của nhóm), `corrections.md` (before · after · evidence · found_by), `review-vi.md` (tóm tắt duyệt tiếng Việt: bản chất, 10 luật quan trọng kèm số, kết luận đã sửa, cảnh báo)
- [ ] T026 [US2] Viết `.claude/skills/style-learn/SKILL.md`: kích hoạt, bước 0–6 của contracts/skill-flow.md; lời gọi 3 agent song song kèm phạm vi đọc/ghi; quy tắc kiểm tra chéo; khung 11 mục (đọc `lib/lemo-opuscar/styles/_template/STYLE.md`); `(evidence: …)` cho mọi luật; phụ đề hay chữ cháy vào hình của kênh **không** được coi là chữ của phong cách trừ khi người dùng xác nhận; chạy `check-names`; dừng **duyệt 1**

**Checkpoint**: US1 và US2 hoạt động.

## Phase 5: User Story 3 - Chứng minh và lưu phong cách (Priority: P3)

**Goal**: `compare`, `save`, `clean` và phần skill bước 7–10.

**Independent Test**: test `compare`, `save`, `clean` xanh; sau `save`, `my-styles/README.md` có dòng mới.

- [ ] T027 [P] [US3] `tests/learn/test_compare.py`: hai ảnh tổng hợp gần nhau → `pass`; lệch độ sáng 0,1 → `fail` với `luma_diff` đúng; `palette_matched` đếm đúng; `compare.jpg` được tạo (SC-004)
- [ ] T028 [P] [US3] `tests/learn/test_save_clean.py`: `save` từ chối slug trùng thư viện giả hoặc `my-styles/`, slug hay tên chứa tên kênh (FR-021), gói có `.mp4`/`words.json`, vi phạm tên; khi đạt thì chép đúng file theo research.md §13, `measurements/summary.json` không có `title/channel/origin/id`, thêm đúng một dòng vào `my-styles/README.md` (SC-008); `clean` chỉ xoá trong `references/<set>/`, giữ số liệu, mặc định xoá media (SC-006)
- [ ] T029 [US3] Viết `tools/style-learn/sl/compare.py` và lệnh `compare` (ngưỡng SC-004, ghép ảnh trái–phải kèm bảng chỉ số, `round`)
- [ ] T030 [US3] Viết `tools/style-learn/sl/save.py` và các lệnh `save`, `clean` theo contracts/learn-cli.md; `save` chạy `check-names` trên cả slug, `--en`, `--cn` (FR-021)
- [ ] T031 [US3] Hoàn thiện `.claude/skills/style-learn/SKILL.md` bước 7–10: chọn khung gốc tiêu biểu; viết `proof/index.html` theo hợp đồng `render(t)` (URL tuyệt đối `/core/lib.js`); chụp bằng `cd $LIB && node core/render/still.mjs <proof> 0 --size WxH --out <proof>/out`; `compare`, tối đa 2 vòng sửa; dừng **duyệt 2**; `save`; hỏi giữ hay xoá (mặc định xoá) → `clean`; thiếu `node`/deps thì dừng ở bước 7 và báo

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T032 [P] Cập nhật `CLAUDE.md`: luồng "Học phong cách" trỏ tới skill `style-learn` (bỏ "chưa có"); cấu trúc thêm `tools/style-learn/`, `tests/learn/`
- [ ] T033 [P] Cập nhật `README.md`: cách dùng học phong cách, `deps learn [--extra]`, trạng thái 002
- [ ] T034 Chạy `sh tests/run.sh` (001 không hỏng) và `sh tests/learn/run.sh`; chạy kiểm hiệu năng SC-005 trên bộ tổng hợp 18 phút (`make_fixtures.py --perf`); ghi kết quả (đạt / đạt một phần / thất bại / chưa chạy được kèm lý do) vào cuối file này

## Dependencies & Execution Order

- Phase 1 → Phase 2 → US1 → US2 → US3 → Polish.
- US2 dùng hồ sơ đo của US1; US3 dùng `STYLE.md` của US2 và `names.py` (T024).
- T008 (fixtures) trước mọi test.

## Parallel Opportunities

- T006, T007 song song (khác file).
- Test US1 T009–T012 song song; module US1 T014–T018 song song (khác file); T019–T022 tuần tự (dùng các module trên).
- T023 và T025 song song; T027 và T028 song song; T032 và T033 song song.

## Implementation Strategy

MVP = Phase 1 + 2 + US1: đo được một bộ video và có hồ sơ đo. Sau đó là US2 (skill viết phong cách, chặn tên), rồi US3 (chứng minh, lưu, dọn).
