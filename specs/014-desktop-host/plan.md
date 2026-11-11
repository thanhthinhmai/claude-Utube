# Implementation Plan: Chế độ máy chủ trên một máy

**Branch**: `014-desktop-host` | **Date**: 2026-11-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/014-desktop-host/spec.md`

## Summary

Thêm lệnh `sh bin/studio app start|stop|status|import`, viết trong `tools/studio/studio/host.py`. Lệnh này chạy trọn bản online trên một máy, không cần Docker.

- **Khởi động** (R1): `app start` kiểm công cụ, chọn thư mục dữ liệu và cổng, rồi tách một **tiến trình giám sát** chạy nền. Tiến trình này mở 3 tiến trình con: giao diện (uvicorn `studio.server:create_app`), proxy (`tools/runner/proxy.py`) và worker (`tools/runner/worker.py` với `RUNNER=local`). Mọi tiến trình dùng `STUDIO_MODE=online`, `STUDIO_DATA=<thư mục dữ liệu>` và chỉ nghe ở `127.0.0.1`. Tiến trình giám sát ghi log xoay vòng cho từng phần và mở lại tiến trình con nào bị sập.
- **Trạng thái và dừng** (R2): tệp khoá `host.lock` (flock) và tệp trạng thái `host.json` (pid, cổng, thời điểm) nằm trong thư mục dữ liệu. Ngoài ra có một con trỏ ở `~/.config/claude-utube/host.json` để luồng chat tìm được máy chủ đang chạy. `app stop` đọc sổ việc: còn việc đang chạy thì từ chối, có `--force` thì đánh dấu việc "đã dừng". Sau đó gửi SIGTERM cho tiến trình giám sát, rồi tắt cả cây tiến trình.
- **Nâng cấp dữ liệu** (R3): trước khi `db.init` chạy bước nâng cấp, nếu số phiên bản lưu trong cơ sở dữ liệu nhỏ hơn `SCHEMA_VERSION`, sao lưu tệp cơ sở dữ liệu vào `backup/`.
- **Chủ xưởng không giới hạn phim** (R4): biến cấu hình `STUDIO_OWNER_UNLIMITED=1`. `accounts.setup` đặt hạn mức riêng của chủ xưởng là 1000 phim mỗi tháng, đúng cách đặt hạn mức riêng cho từng người có sẵn ở 007. Không có nhánh logic mới trong phần tính hạn mức.
- **Agent không có container** (R5): worker viết `.claude/settings.json` vào thư mục việc. `agent.py` thêm một `can_use_tool` chỉ cho `Write` và `Edit` trong thư mục việc, và bật `sandbox` cho Bash khi có cấu hình `STUDIO_AGENT_SANDBOX=1`. Bản Docker không đổi.
- **Nhập dữ liệu** (R6): `app import [--from <dự án>]` chép `films/`, `my-styles/` và `channels/` vào `accounts/<chủ xưởng>/`, bỏ qua mục đã có.
- **Luồng chat vào sổ việc của máy chủ** (R7): `studio_cli job|review` thấy con trỏ của một máy chủ đang chạy thì làm việc trên cơ sở dữ liệu của máy chủ đó, dưới tên chủ xưởng. `job done --film X` tạo liên kết `accounts/<chủ xưởng>/films/X` trỏ về `films/X` của dự án, để app mở được phim.

Chi tiết: [research.md](research.md) · [data-model.md](data-model.md) · [contracts/](contracts/) · [quickstart.md](quickstart.md).

## Technical Context

**Language/Version**: Python 3.12 (thư viện chuẩn cùng gói giao diện và online có sẵn); POSIX sh.

**Primary Dependencies**: uvicorn, FastAPI và claude-agent-sdk có sẵn (007, 008); `fcntl.flock`; `logging.handlers.RotatingFileHandler`. Không thêm thư viện.

**Storage**: thư mục dữ liệu (FR-005): `studio.db`, `accounts/`, `secrets/`, `logs/`, `backup/`, `cache/`, `jobs/`, `host.lock`, `host.json`. Cùng khuôn dạng với bản VPS.

**Testing**: `unittest` trong `tests/online/test_host.py`.
- Bật máy chủ thật bằng các tiến trình con, với agent giả và Claude giả.
- Kiểm: khởi động và dừng, chạy trùng, dừng khi đang có việc, giết tiến trình rồi khởi động lại, nhập dữ liệu, luồng chat, không ghi vào thư mục dự án.

**Target Platform**: Linux và WSL2 (máy hiện tại). macOS kiểm ở 015 và 016.

**Project Type**: công cụ dòng lệnh, cộng với sửa nhẹ dịch vụ có sẵn.

**Performance Goals**: sẵn sàng < 20 giây (SC-001); dừng < 10 giây.

**Constraints**:
- Cùng một bộ code với bản VPS: bộ test online đạt mà không phải sửa (FR-004).
- Không ghi vào thư mục dự án (SC-006). Không tự cài phần mềm hệ thống.

**Scale/Scope**: một chủ xưởng, vài việc chạy cùng lúc (cài đặt `concurrency` có sẵn).

## Constitution Check

| Nguyên tắc | Kết quả |
|---|---|
| I. Spec là nguồn sự thật | ✓ Đã làm rõ 2 câu. Công nghệ chỉ nằm trong plan |
| II. Không đoán | ✓ có điều kiện. Chưa thử: `sandbox` của Claude Code chạy được trong WSL không (cần bubblewrap). T001 sẽ kiểm. Nếu không chạy thì Bash không bị cách ly, chỉ còn chặn ghi tệp, và ghi rõ trong Assumptions |
| III. MVP theo story | ✓ US1 tự chạy và tự test được. US2, US3 thêm sau |
| IV. Đo được | ✓ SC-001 … SC-006 đều có test tự động |
| V. Đơn giản | ✓ Dùng lại toàn bộ web, proxy, worker và `RUNNER=local` có sẵn. Thêm một tệp `host.py`. Một mục ở Complexity Tracking |
| VI. Thư viện gốc | ✓ Không đụng `lib/` |
| VII–IX | ✓ Không đổi |
| Bản quyền, nội dung | ✓ Không đổi. Khoá bí mật nằm trong `secrets/` của thư mục dữ liệu, ngoài repo |

Kiểm lại sau thiết kế: đạt.

## Project Structure

### Documentation (this feature)

```text
specs/014-desktop-host/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/
│   └── cli.md       # lệnh app start|stop|status|import; host.json; luồng chat khi có máy chủ
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
tools/studio/studio/
├── host.py                      # mới: kiểm công cụ, thư mục dữ liệu, cổng, khoá, giám sát, log xoay vòng, dừng, nhập (R1–R6)
├── db.py                        # sửa: sao lưu trước khi nâng cấp (R3)
├── accounts.py                  # sửa: STUDIO_OWNER_UNLIMITED khi tạo chủ xưởng (R4)
tools/studio/studio_cli.py       # sửa: app …; job/review ghi vào máy chủ đang chạy (R7)
tools/runner/
├── agent.py                     # sửa: can_use_tool giới hạn ghi; sandbox theo cấu hình (R5)
└── worker.py                    # sửa: LocalRunner viết .claude/settings.json chặn ghi ngoài thư mục việc (R5)
bin/studio                       # sửa: app …
CLAUDE.md                        # sửa: luồng làm phim khi máy chủ đang chạy; lệnh app
tests/online/test_host.py        # mới
```

**Structure Decision**: `host.py` nằm trong gói `studio`, vì nó cần `db`, `accounts` và `jobs` để dừng an toàn và nhập dữ liệu. Vỏ desktop (015) chỉ gọi `app start` và `app stop`.

## Complexity Tracking

| Vi phạm | Vì sao cần | Cách đơn giản hơn bị loại vì |
|---|---|---|
| Thêm một tiến trình giám sát riêng, thay cho chạy thẳng 3 tiến trình nền | Cần một chỗ giữ khoá, ghi log xoay vòng, mở lại tiến trình sập, và tắt sạch cả cây khi dừng (FR-010–FR-013) | Ba tiến trình nền rời nhau thì không ai xoay log, không ai mở lại khi sập, và `stop` phải tự tìm từng pid. Vỏ desktop (015) cũng cần đúng một tiến trình để quản lý |
