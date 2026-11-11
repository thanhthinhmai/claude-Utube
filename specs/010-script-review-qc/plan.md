# Implementation Plan: Kịch bản được chấm và QC video tự động

**Branch**: `010-script-review-qc` | **Date**: 2026-11-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/010-script-review-qc/spec.md`

## Summary

Thêm một bộ công cụ chấm và đo của xưởng, `tools/filmcheck/`, gọi qua `bin/studio`. Bộ công cụ này dùng chung cho chế độ local và online (R1).

- **Bước `Script`** giữa Treatment và Look. Agent viết `SCRIPT.md` và `SOURCES.md`, rồi chạy:
  - `script check`: máy chấm bằng Python thuần, không gọi Claude (R2);
  - `script review`: một tiến trình `claude -p` riêng với lời nhắc cố định của xưởng, không thấy quá trình viết (R3).
  - Tối đa 2 vòng sửa. Đoạn không bị ghi lỗi phải giữ nguyên, có máy kiểm (R9). Hết vòng mà chưa đạt thì dừng; online thì việc lỗi do xưởng và trả lượt.
- **Nguồn thật**: bật `WebSearch` của Claude Code (đi qua proxy như mọi lần gọi). Thêm `web fetch`: proxy tải trang thay cho container, có chặn địa chỉ nội bộ và giới hạn. Container vẫn không có internet (R4).
- **`qc`**: đo phim cuối.
  - Lời đọc: từ `narration.json` cộng `words.json` của thư viện (R5).
  - Hình đứng im và mốc cảnh: bằng ffmpeg.
  - Chữ ô vuông: chữ của `window.TEXTS` so với phông qua fontconfig (R7).
  - Worker gộp `qc` vào cổng QC của 007, nên vòng sửa và trả lượt giữ nguyên (R8).
- **Theo dõi**: `checks.json` và `CHECKS.md` trong thư mục phim; worker chép tóm tắt vào `job.qa` để trang việc hiện (R10). Cài đặt `editor_model` (R6).

Chi tiết: [research.md](research.md) · [data-model.md](data-model.md) · [contracts/](contracts/) · [quickstart.md](quickstart.md).

## Technical Context

**Language/Version**: Python 3.12 (thư viện chuẩn cho máy chấm và `qc`); một tệp Node ESM nhỏ để gom chữ trên màn hình (import `core/render/page.mjs` của thư viện, không sửa); POSIX sh; JavaScript thuần có `@ts-check` cho giao diện.

**Primary Dependencies**:
- Có sẵn: ffmpeg (`freezedetect`, `scdet`), fontconfig (`fc-list`, `fc-scan`), Claude Code đi kèm `claude-agent-sdk` (008), `httpx` trong proxy.
- Không thêm thư viện mới. Chỉ thêm `fonttools` nếu `fc-scan` không đọc được `.woff2` (R7, kiểm khi implement).

**Storage**: tệp trong thư mục phim (contracts/files.md). Online: thêm cài đặt `editor_model` và mở rộng `job.qa` trong SQLite của 007/008, không thêm bảng.

**Testing**: `unittest`.
- Kịch bản mẫu và phim mẫu tạo bằng ffmpeg trong test (không commit media nặng).
- Biên tập giả qua `STUDIO_CLAUDE_BIN` (`fake_claude` của 008, thêm lược đồ biên tập và các thẻ `[editor-fail]`, `[editor-p1]`).
- Proxy giả cho `web fetch`.
- Bài chạy thật bằng tay theo quickstart.

**Target Platform**: như 007/008: Ubuntu 24.04 (WSL2 trên máy này), ảnh `studio-job`, Docker Compose.

**Project Type**: công cụ dòng lệnh và sửa dịch vụ online có sẵn.

**Performance Goals**:
- `script check` < 5 giây cho kịch bản 300 giây (SC-002).
- `qc` < 60 giây cho phim 60 giây (SC-006).

**Constraints**:
- Không sửa `lib/` (VI).
- Container không có đường ra internet; `web fetch` chỉ qua proxy, chặn địa chỉ nội bộ (R4).
- Máy chấm và `qc` không gọi Claude.
- Token thêm của bước kịch bản ≤ 15% việc (SC-005).

**Scale/Scope**: phim 5–300 giây; một lượt biên tập cho mỗi lần chấm; tối đa 60 trang mở mỗi việc.

## Constitution Check

| Nguyên tắc | Kết quả |
|---|---|
| I. Spec là nguồn sự thật | ✓ Spec đã làm rõ 4 câu. Công nghệ chỉ nằm trong plan và research |
| II. Không đoán | ✓ có điều kiện. Ba hành vi chưa thử được ghi "Kiểm khi implement": `claude -p` chạy song song trong container (R3), `WebSearch` qua proxy (R4), `fc-scan` đọc `.woff2` (R7). Task đầu kiểm; kết quả khác thì dừng và hỏi |
| III. MVP theo story | ✓ US1 (kịch bản được chấm) tự chạy và tự test được. US2 (QC) và US3 (theo dõi) thêm sau |
| IV. Đo được | ✓ Mọi luật có ngưỡng số (contracts/cli.md). SC-001 … SC-004, SC-006 có test tự động; SC-005 đo ở bài chạy thật |
| V. Đơn giản | ✓ Một gói công cụ, thư viện chuẩn, dùng lại cổng QC và cách gọi `claude -p` của 008. Hai mục ở Complexity Tracking |
| VI. Thư viện gốc | ✓ Chỉ đọc `words.json`, `dur.json` và import `core/render/page.mjs`; không sửa tệp nào trong `lib/` |
| VII. Một bộ máy dựng hình | ✓ Không thêm bộ máy vẽ. `qc` chỉ đo |
| VIII. Học phong cách | ✓ Không đổi |
| IX. Spec-kit cho phần mềm | ✓ Bước `Script` là một phần của quy trình làm phim, không tạo spec cho từng phim |
| Bản quyền, nội dung | ✓ Không clone giọng. Nguồn là trang công khai, chỉ trích để dẫn. Không commit media mẫu: test tạo bằng ffmpeg |

Kiểm lại sau thiết kế: đạt.

## Project Structure

### Documentation (this feature)

```text
specs/010-script-review-qc/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/
│   ├── cli.md       # lệnh script / web fetch / qc / config, điểm, ngưỡng, mã thoát
│   └── files.md     # SCRIPT.md, SOURCES.md, narration.json, checks.json, .check/
├── checklists/requirements.md
└── tasks.md         # /speckit-tasks
```

### Source Code (repository root)

```text
tools/filmcheck/                 # mới, thư viện chuẩn
├── cli.py                       # script check|review|status|skip, web fetch, qc, config
├── script.py                    # đọc SCRIPT.md / SOURCES.md, máy chấm, so đoạn (R2, R9)
├── editor.py                    # chạy claude -p với lời nhắc và lược đồ cố định (R3)
├── webfetch.py                  # tải trang, chặn địa chỉ nội bộ, rút chữ (R4); proxy dùng lại
├── qc.py                        # lời đọc, mốc cảnh, hình đứng im, phông (R5, R7)
├── texts.mjs                    # gom chữ của window.TEXTS (import page.mjs của thư viện)
├── report.py                    # checks.json và CHECKS.md (R10)
├── cliches/en.txt · vi.txt
└── styles.json                  # still_max theo phong cách (lúc đầu rỗng)
bin/studio                       # sửa: chuyển script | web | qc | config tới tools/filmcheck/cli.py
tools/runner/
├── agent.py                     # sửa: bật WebSearch, truyền STUDIO_EDITOR_MODEL, lời nhắc nói về bước Script
├── JOB.md                       # sửa: bước Script, narration.json, qc trước job done
├── proxy.py                     # sửa: POST /internal/web/fetch, đếm web_search_requests
└── worker.py                    # sửa: quality() gọi qc, kiểm script.verdict, failed khi verdict failed
tools/studio/studio/
├── jobs.py · reviews.py         # sửa: bước Script; review treatment gắn kịch bản (FR-019)
├── quotas.py · db.py            # sửa: cài đặt editor_model; giá lượt tìm web (khoá API)
├── studio_cli.py                # sửa: review request --film gắn SCRIPT.md và điểm
└── web/app.js · style.css       # sửa: khối Quality hiện điểm kịch bản và số đo; Settings có editor_model
CLAUDE.md                        # sửa: luồng làm phim thêm bước Script, qc ở Self-check
tests/
├── filmcheck/                   # mới: test máy chấm, qc (phim mẫu tạo bằng ffmpeg), webfetch
└── online/                      # sửa: fake_claude (biên tập), test việc có bước Script, test_web_fetch
```

**Structure Decision**:
- `tools/filmcheck/` đứng riêng, không nằm trong `tools/studio`. Chế độ local không cần cài giao diện (FastAPI) mới chạy được `script` và `qc`; chỉ cần Python 3.
- Proxy import `webfetch.py` để dùng chung luật chặn địa chỉ.
- `tests/filmcheck/` có `run.sh` riêng. Từ nay chạy 5 bộ test, và `CLAUDE.md` ghi thêm bộ này.

## Complexity Tracking

| Thêm | Vì sao cần | Cách đơn giản hơn bị loại vì |
|---|---|---|
| Proxy tải trang thay cho container (`/internal/web/fetch`) | FR-007a đòi mở được trang nguồn, mà container không có internet | Cho container ra internet qua `egress`: mở đường ra cho cả agent. Bỏ việc mở trang: trái câu trả lời A của clarify |
| Biên tập là một tiến trình `claude -p` riêng, không phải subagent | FR-007: biên tập không thấy quá trình viết; lời nhắc phải cố định để test được | Subagent qua công cụ `Agent`: agent tự viết lời nhắc cho biên tập, nên tính độc lập phụ thuộc vào agent |
