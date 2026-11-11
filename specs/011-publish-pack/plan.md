# Implementation Plan: Gói đăng YouTube cho mỗi phim

**Branch**: `011-publish-pack` | **Date**: 2026-11-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/011-publish-pack/spec.md`

## Summary

Thêm bước `Publish` sau `Self-check`. Agent chỉ viết một tệp nhỏ, `publish/pack.json`, gồm: 3 tiêu đề, thời điểm và chữ cho 3 thumbnail, 2 dòng mở đầu, tóm tắt, tên chương và hashtag. Agent chọn khung hình từ bảng ảnh của bước Self-check, nên không phải xem thêm ảnh nào. Phần còn lại do một lệnh của xưởng làm, không gọi Claude (R1):

```
sh bin/studio publish <phim>     # dựng gói từ pack.json rồi kiểm; mã 0 đạt, 1 trượt, 2 không làm được
```

Lệnh này:
- **Thumbnail:** mở trang dựng hình của phim bằng `page.mjs` của thư viện, render khung hình tại thời điểm đã chọn, phủ một lớp chữ HTML dùng phông của phim, chụp rồi thu về 1280×720 hoặc 720×1280. Lệnh đo cỡ chữ và độ tương phản ngay trong trình duyệt (R2, R3).
- **Chương:** tính từ `narration.json`, tức mốc của dòng đầu tiên trong mỗi đoạn `[Pnn]` (R4).
- **Phụ đề:** chữ lấy từ các câu của `lines.json` (đúng kịch bản đã đạt), thời gian lấy từ `words.json` (R5).
- **Mô tả:** ghép phần chữ của agent với nguồn từ `SOURCES.md`.
- **`PUBLISH.md`:** gộp tất cả.
- **Máy kiểm:** chạy mọi luật FR-009 rồi ghi mục `publish` vào `checks.json` và `CHECKS.md` (R6).

Agent sửa một vòng theo lỗi máy kiểm báo, rồi gọi `job done`.

Worker:
- chạy lại `publish --check-only` sau cổng QC và chép kết quả vào `job.qa.publish`;
- **không bao giờ** làm việc lỗi vì gói đăng (FR-010).

Nếu chạm trần token, hết giờ hoặc watchdog dừng việc khi đang ở bước `Publish`, worker giao phim không có gói và ghi lý do (R7).

Online có thêm:
- 3 đường API chỉ đọc cho gói đăng;
- mục "Publish" trên trang việc (R8).

Chi tiết: [research.md](research.md) · [data-model.md](data-model.md) · [contracts/](contracts/) · [quickstart.md](quickstart.md).

## Technical Context

**Language/Version**: Python 3.12, chỉ dùng thư viện chuẩn, cho phần dựng chữ và máy kiểm. Một tệp Node ESM cho thumbnail, import `core/render/page.mjs` của thư viện mà không sửa nó, giống `texts.mjs` của 010. POSIX sh. JavaScript thuần có `@ts-check` cho giao diện.

**Primary Dependencies**:
- Có sẵn: playwright-core và Chromium của thư viện, ffmpeg và ffprobe (thu nhỏ ảnh, đọc cỡ phim), fontconfig (kiểm ký tự thiếu phông bằng `qc.missing_glyphs` của 010).
- FastAPI có sẵn cho API online, và `zipfile` của thư viện chuẩn cho file tải cả gói.
- Không thêm thư viện mới.

**Storage**:
- Tệp trong `films/<tên>/publish/`; khuôn dạng ở contracts/files.md.
- Mục `publish` trong `checks.json`.
- Online: mở rộng `job.qa` với `qa.publish`. Không thêm bảng, không thêm cài đặt.

**Testing**: `unittest`.
- Gói mẫu và phim mẫu được tạo trong test: trang HTML nhỏ có `window.render`, tệp `narration.json`, `words.json` và `lines.json` giả. Không commit media.
- Mỗi luật có một gói mẫu cố ý lỗi (SC-002).
- `fake_agent` của online thêm bước Publish và thẻ `[publish-bad]`, `[publish-cap]`.
- Phần trình duyệt chạy bằng playwright-core khi máy có, nếu không thì bỏ qua như 010.
- Bài chạy thật làm bằng tay theo quickstart.

**Target Platform**: như 007–010: Ubuntu 24.04 (WSL2 trên máy này), ảnh `studio-job`, Docker Compose.

**Project Type**: công cụ dòng lệnh, cộng với sửa dịch vụ online có sẵn.

**Performance Goals**:
- `publish --check-only` < 10 giây cho phim 60 giây (SC-003).
- Cả lệnh `publish`, gồm render 3 thumbnail, < 60 giây.
- Token của bước Publish ≤ 5% việc (SC-004).

**Constraints**:
- Không sửa `lib/` (VI).
- Không gọi Claude trong lệnh `publish`.
- Không nối với YouTube.
- Gói đăng không chặn việc giao phim (FR-010).

**Scale/Scope**: phim 5–300 giây; 3 thumbnail; tối đa vài chục chương và vài trăm khối phụ đề.

## Constitution Check

| Nguyên tắc | Kết quả |
|---|---|
| I. Spec là nguồn sự thật | ✓ Spec đã làm rõ 5 câu. Công nghệ chỉ nằm trong plan và research. Hai chỗ thiết kế phát hiện thiếu (phim dọc, PNG quá 2 MB) đã được sửa vào spec trước |
| II. Không đoán | ✓ có điều kiện. Một hành vi chưa thử: trang dựng hình của phim có vẽ đúng khi phủ thêm một lớp HTML không (R2). Task đầu sẽ kiểm trên 2 phim có sẵn; nếu kết quả khác thì dừng và hỏi |
| III. MVP theo story | ✓ US1 (gói đăng từ `pack.json`) tự chạy và tự test được. US2 (máy kiểm và vòng sửa) và US3 (trang việc) thêm sau |
| IV. Đo được | ✓ Mọi luật có ngưỡng số (contracts/cli.md). SC-001 … SC-003, SC-006 có test tự động. SC-004 và SC-005 đo ở bài chạy thật |
| V. Đơn giản | ✓ Agent chỉ viết một tệp JSON, phần còn lại là một lệnh. Dùng lại `page.mjs`, `report.update`, `qc.load_narration` và `missing_glyphs`. Một mục ở Complexity Tracking |
| VI. Thư viện gốc | ✓ Chỉ import `core/render/page.mjs` và đọc tệp giọng; không sửa tệp nào trong `lib/` |
| VII. Một bộ máy dựng hình | ✓ Thumbnail vẽ bằng chính trang HTML của phim trong Chromium của thư viện. Không có bộ máy vẽ mới, không có AI vẽ ảnh |
| VIII. Học phong cách | ✓ Không đổi |
| IX. Spec-kit cho phần mềm | ✓ `Publish` là một bước trong quy trình làm phim, không tạo spec cho từng phim |
| Bản quyền, nội dung | ✓ Phông lấy từ phim (đã có trong `CREDITS`). Không ảnh ngoài, không mặt người. Chữ không nêu tên kênh tham chiếu: lời dặn của bước Publish cấm điều này. Phong cách đã học không lưu tên kênh (`style.json` chỉ có số video và số giây), nên không có danh sách để máy so; ghi trong R6 |

Kiểm lại sau thiết kế: đạt.

## Project Structure

### Documentation (this feature)

```text
specs/011-publish-pack/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/
│   ├── cli.md       # lệnh publish, các luật kiểm, ngưỡng, mã thoát
│   ├── files.md     # pack.json và các tệp trong publish/, mục publish của checks.json
│   └── api.md       # 3 đường API online và mục Publish trên trang việc
├── checklists/requirements.md
└── tasks.md         # /speckit-tasks
```

### Source Code (repository root)

```text
tools/filmcheck/
├── publish.py                   # mới: đọc pack.json, chương, phụ đề, mô tả, PUBLISH.md, máy kiểm (R1, R4–R6)
├── thumbs.mjs                   # mới: render khung hình + lớp chữ, đo cỡ chữ và tương phản (R2, R3)
├── report.py                    # sửa: mục publish trong checks.json, phần "Publish" trong CHECKS.md
└── cli.py                       # sửa: lệnh publish [--check-only] [--json]
bin/studio                       # sửa: chuyển publish tới tools/filmcheck/cli.py
tools/runner/
├── JOB.md                       # sửa: bước Publish trước job done; vòng sửa QC chạy lại publish
├── agent.py                     # sửa: lời nhắc vòng sửa QC và bản sửa nói tới publish
├── proxy.py                     # sửa: over_cap ở bước Publish → giao phim không gói (R7)
└── worker.py                    # sửa: publish_summary() vào qa.publish; watchdog và hết giờ ở bước Publish (R7)
tools/studio/studio/
├── resources.py                 # sửa: publish_file(), danh sách tệp được phép
├── server.py · api_online.py    # sửa: GET /films/{name}/publish, /publish/{file}, /publish.zip
└── web/app.js · style.css       # sửa: STAGES thêm Publish; mục Publish trên trang việc
CLAUDE.md                        # sửa: luồng làm phim thêm bước Publish; tên giai đoạn
specs/003-studio-ui/contracts/skill-integration.md   # sửa: thêm tên giai đoạn Publish
tests/
├── filmcheck/test_publish.py    # mới: chương, phụ đề, mô tả, mọi luật kiểm, gói mẫu cố ý lỗi
├── filmcheck/test_thumbs.py     # mới: thumbnail trên trang mẫu (bỏ qua khi không có trình duyệt)
└── online/                      # sửa: fake_agent bước Publish; test_publish_view.py; browser_publish.cjs
```

**Structure Decision**:
- Gói đăng nằm trong `tools/filmcheck/`, vì nó dùng lại `report.py`, `qc.py` và `script.py`, và giống 010 chỉ cần Python 3 cùng thư viện. Không mở gói công cụ mới.
- Agent viết dữ liệu, lệnh của xưởng viết tệp. Như vậy agent ít token hơn, mọi tệp đúng khuôn dạng, và máy kiểm chạy được lại bất cứ lúc nào (FR-001a, R1).

## Complexity Tracking

| Vi phạm | Vì sao cần | Cách đơn giản hơn bị loại vì |
|---|---|---|
| Worker và proxy có nhánh riêng cho bước `Publish` khi chạm trần token hoặc hết giờ (R7) | Spec Q4: hỏng ở bước phụ thì vẫn giao phim, không trả lượt | Để mọi lỗi làm hỏng việc thì khách mất phim đã đạt QC chỉ vì gói đăng; còn làm gói đăng bằng một tiến trình riêng sau cổng QC thì phải nạp lại toàn bộ bối cảnh, tốn token hơn nhiều (R1) |
