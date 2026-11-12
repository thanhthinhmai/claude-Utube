# Implementation Plan: QC theo từng cảnh trước khi render

**Branch**: `020-qc-before-render` | **Date**: 2026-11-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/020-qc-before-render/spec.md`

## Summary

Chia việc kiểm phim thành 5 tầng theo dữ liệu mà mỗi phép kiểm cần:

| Tầng | Lệnh | Dữ liệu cần |
|---|---|---|
| 0 | `qc voice` | giọng |
| 1 | `qc plan` | kế hoạch, không cần dựng hình |
| 2 | `qc shots` | mỗi cảnh một ảnh, kèm so phong cách |
| 3 | trong `render` | từng đoạn 10 s vừa ghi |
| 4 | `qc` | bản đã ghép tiếng |

Cách làm:
- Luật nhịp chuyển từ `qc.py` sang một module chung (`rhythm.py`), có câu tính theo kịch bản. Tầng 1 và tầng 4 cùng dùng module này, nên một kế hoạch đạt tầng 1 thì không bị báo lỗi nhịp sau khi ghép tiếng.
- `sh bin/studio render` chặn khi tầng 1 hoặc luật khung của tầng 2 chưa đạt cho nguồn hiện tại. Lệch phong cách chỉ cảnh báo, cần một dòng lý do mới render được.
- Cả xưởng dùng một mô hình nhận dạng: `small.en`, chọn theo số đo ở research R1.
- Gói đăng dùng phụ đề tầng 1 đã kiểm. Thumbnail chụp khi đã ẩn hết chữ của phim.

## Technical Context

**Language/Version**: Python 3.12, chỉ thư viện chuẩn (`tools/filmcheck/`, như 010–013). Node 20+ ES modules có `@ts-check` (`tools/render/`, `tools/filmcheck/*.mjs`, như 019). POSIX sh (`bin/studio`).

**Primary Dependencies**: có sẵn từ trước:
- playwright-core và các module `core/render/*.mjs` của thư viện (chỉ gọi, không sửa);
- ffmpeg và ffprobe (`blackdetect`, `freezedetect`, `silencedetect`, `ebur128`);
- faster-whisper qua `core/tts/asr_check.py` của thư viện.

Không thêm gói mới.

**Storage**: file JSON trong thư mục phim:
- `checks.json → tiers`;
- `qc-exceptions.json`;
- `.check/plan-input.json` và `.check/shots/`;
- `out/.chunks/STOPPED.json`.

Thêm `tools/asr.json`.

**Testing**: `sh tests/filmcheck/run.sh` (unittest, phim thử trong `tests/filmcheck/fixtures/tiers/`) và `sh tests/render/run.sh` (`node --test`). Cả 5 bộ test của xưởng phải đạt. Chạy thật theo [quickstart.md](quickstart.md) trên `films/pet-swap`.

**Target Platform**: Linux và WSL2 (máy phát triển, GPU qua WSLg), container của worker online, phần lõi của app desktop (Linux trong WSL, macOS).

**Project Type**: CLI và công cụ của xưởng.

**Performance Goals**:
- `qc plan` ≤ 10 s với phim 10 phút (FR-008);
- `qc shots` ≤ 3 phút với 192 cảnh khi có GPU (SC-003);
- `qc voice` ≤ 30 s với 70 dòng (SC-007);
- tầng 3 thêm ≤ 5% thời gian ghi (một lượt ffmpeg 320 px trên mỗi đoạn 10 s).

**Constraints**:
- Không sửa `lib/` (hiến pháp VI).
- Một bộ máy dựng hình: trình duyệt của 019 (hiến pháp VII).
- Phần đo của filmcheck không cần Claude và không cần mạng.

**Scale/Scope**: phim tới khoảng 15 phút, khoảng 300 cảnh, khoảng 120 dòng giọng.

## Constitution Check

| Nguyên tắc | Đánh giá |
|---|---|
| I. Spec là nguồn sự thật | Đạt. Spec đã duyệt và đã làm rõ (2026-11-12). Công nghệ chỉ nằm trong plan |
| II. Không đoán | Đạt, với 1 điểm cần người dùng xác nhận: spec nói "ngưỡng theo phim ngắn của `qc` hiện nay", nhưng `qc` không có ngưỡng riêng cho phim ngắn. Research R3 đề xuất: dùng cùng ngưỡng nhịp, chỉ bỏ so số lần cắt mỗi phút khi phim < 30 s |
| III. MVP theo story | Đạt. US1 (tầng 1 + cổng) tự chạy được. US3 (câu theo kịch bản) là nền của US1, nên phần `rhythm.sentences` làm trong giai đoạn nền; phần còn lại của US3 (tầng 0, mô hình chung) để sau |
| IV. Đo được | Đạt. Mọi SC có số. Quickstart có chạy thật trên `pet-swap` và xem bằng mắt bảng ảnh và thumbnail |
| V. Đơn giản | Có 2 điểm phức tạp, ghi ở Complexity Tracking |
| VI. Thư viện gốc | Đạt. Chỉ gọi `asr_check.py`, `readcheck.mjs`, `page.mjs` với tham số có sẵn. SC-010 kiểm `git diff lib/` |
| VII. Một bộ máy dựng hình | Đạt. Tầng 2 và 3 dùng trình duyệt và `render_env` của 019 |
| VIII. Học bằng đo | Đạt. Số đo phong cách lấy từ `EVIDENCE.md` mà style-learn đã ghi |
| IX. Không spec cho từng phim | Đạt |
| Phần mềm hệ thống | Đạt. Không cài gì; mô hình Whisper tải như hiện nay (`app models`, hoặc tải khi dùng lần đầu) |

**Sau Phase 1**: vẫn đạt. Hợp đồng trang phim (`SHOTS`, `CUES`, `CARDS`, `CLEAN`) nằm trong code của phim, không trong thư viện.

## Project Structure

### Documentation (this feature)

```text
specs/020-qc-before-render/
├── plan.md
├── research.md          # R1–R11
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md           # voice asr, qc voice|plan|shots|except|accept-style|final, render gate/flags
│   ├── checks.md        # bảng luật, checks.json → tiers, cổng render
│   └── film-page.md     # window.SHOTS / CUES / CARDS / TEXTS / CLEAN
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
tools/asr.json                      # mới: mô hình nhận dạng theo ngôn ngữ (R1)
tools/filmcheck/
├── rhythm.py                       # mới: câu theo kịch bản, bộ luật nhịp chung (R2, R3)
├── tiers.py                        # mới: dấu vân tay, kết quả tầng, ngoại lệ, cổng render (R7, R10)
├── voicecheck.py                   # mới: tầng 0
├── plancheck.py                    # mới: tầng 1 (gọi plan.mjs, readcheck khi thiếu CARDS)
├── plan.mjs                        # mới: đọc SHOTS/DUR/CUES/CARDS từ trang
├── shotcheck.py                    # mới: tầng 2, chấm từ số đo của shots.mjs, so phong cách
├── shots.mjs                       # mới: ảnh giữa cảnh, đo trong trang, bảng ảnh
├── stylerefs.py                    # mới: số đo phong cách từ EVIDENCE.md và qc.json (R6)
├── qc.py                           # sửa: dùng rhythm.py, thêm loudness_range và av_sync
├── publish.py                      # sửa: phụ đề từ tầng 1 (R9)
├── thumbs.mjs                      # sửa: CLEAN và ẩn chữ DOM (R9)
├── report.py                       # sửa: mục Tiers trong CHECKS.md
└── cli.py                          # sửa: qc voice|plan|shots|except|accept-style|final, render-gate
tools/render/
├── chunkcheck.mjs                  # mới: kiểm một đoạn, nối hình đứng yên qua ranh giới (R8)
├── record.mjs                      # sửa: tầng 3, STOPPED.json, --no-stop, --fresh, dùng lại đoạn
└── lib.mjs                         # sửa: bỏ qc-exceptions.json khỏi dấu vân tay
tools/style-learn/sl/speech.py      # sửa: đọc tools/asr.json
tools/studio/studio/host.py         # sửa: app models tải small.en, small
bin/studio                          # sửa: voice asr, cổng và cờ của render
tools/runner/JOB.md, CLAUDE.md      # sửa: thứ tự các tầng trong luồng làm phim (FR-020)
tests/filmcheck/                    # test_rhythm, test_plan, test_shots, test_tiers, test_voice, fixtures/tiers/
tests/render/                       # chunkcheck.test.mjs, thêm ca vào record.test.mjs
```

**Structure Decision**: dùng các thư mục công cụ hiện có. Phép đo và luật nằm ở `tools/filmcheck/` (Python thuần, giống `qc`). Phần cần trình duyệt nằm trong các file `.mjs` cạnh đó, như `texts.mjs` và `thumbs.mjs`. Phần trong lúc ghi nằm ở `tools/render/`.

## Thứ tự làm (gợi ý cho /speckit-tasks)

1. **Nền**:
   - `rhythm.py`: chuyển luật từ `qc.py` và thêm câu theo kịch bản, kèm test so với `qc` cũ trên phim thử;
   - `tiers.py`: dấu vân tay, `checks.json → tiers`;
   - `tools/asr.json`.
2. **US1**: `plan.mjs`, `plancheck.py`, `qc plan`, cổng của `render` và `--skip-checks`; SC-001, SC-002.
3. **US2**: `shots.mjs`, `shotcheck.py`, `stylerefs.py`, `qc shots`, `accept-style`, `except`; SC-003, SC-004.
4. **US3**: `voice asr`, `qc voice`, mô hình chung ở `speech.py` và `host.py`; SC-006, SC-007.
5. **US4**: `chunkcheck.mjs`, `record.mjs` (dừng sớm, dùng lại đoạn); SC-009.
6. **US5**: `qc` dùng `rhythm` và có thêm `loudness_range`, `av_sync`; gói đăng và thumbnail; SC-005, SC-008.
7. **Luồng**: `CLAUDE.md`, `JOB.md`, trang việc; chạy đủ 5 bộ test và quickstart.

## Complexity Tracking

| Điểm phức tạp | Vì sao cần | Cách đơn giản hơn bị loại vì |
|---|---|---|
| Dùng lại các đoạn đã ghi qua một lần đổi dấu vân tay (`STOPPED.json` và so mã băm `SHOTS` của các cảnh trước chỗ lỗi) | US4 yêu cầu: sửa xong "chỉ các đoạn từ chỗ lỗi trở đi được ghi lại". Theo 019, mọi thay đổi nguồn đều xoá hết đoạn | Ghi lại tất cả: phim 10 phút mất thêm 24 phút GPU (hoặc khoảng 12 giờ bằng phần mềm) cho một lỗi ở cuối phim. Đổi code dùng chung (không phải danh sách cảnh) mà vẫn dùng lại đoạn cũ là rủi ro: log ghi rõ số đoạn dùng lại, `--fresh` để ghi lại hết, và tầng 4 vẫn kiểm cả phim |
| Hợp đồng trang phim mới (`CUES`, `CARDS`, `CLEAN`) bên cạnh `SHOTS` và `TEXTS` | Tầng 1 phải đọc phụ đề và thẻ chữ mà không dựng hình. Thumbnail cần một cách ẩn chữ vẽ lên canvas | Chỉ dùng `readcheck` và ẩn chữ bằng CSS: vẫn giữ làm đường dự phòng cho phim cũ, nhưng chậm (readcheck dựng hình) và không ẩn được chữ vẽ thẳng lên canvas |
