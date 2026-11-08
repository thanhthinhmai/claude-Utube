# Implementation Plan: Xưởng online nội bộ chạy bằng gói Claude

**Branch**: `008-claude-plan-login` | **Date**: 2026-11-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/008-claude-plan-login/spec.md`

## Summary

Giữ kiến trúc 007: web, worker, bộ chuyển tiếp, mỗi việc một container. Đổi nguồn Claude từ khoá API sang gói Claude của chủ xưởng:

- **Đăng nhập** như neb-creative-tool. Trang quản trị chạy `claude auth login --claudeai` của Claude Code, mỗi tài khoản một thư mục `/data/claude/slot-<n>` (tối đa 5). Chủ xưởng dán mã vì máy chủ ở xa (R1).
- **Gọi**: container chạy Claude Code ở chế độ gói với mã riêng của việc. Bộ chuyển tiếp thay mã đó bằng mã thật của tài khoản đang dùng ít nhất (R2–R4). Chạm hạn mức hoặc hỏng đăng nhập thì gửi lại qua tài khoản khác. Hết tài khoản thì dùng khoá API dự phòng nếu có; không có khoá thì chờ tối đa 15 giây, quá thì việc lỗi do xưởng (R5).
- **Kiểm nội dung** chạy qua `claude -p` trên một tài khoản gói (R6).
- **Người dùng**: chủ xưởng thêm trong Settings → Users như neb, dùng lại bảng Account (R8). Bỏ đăng ký công khai.
- **Mức dùng** ghi theo từng lần gọi (bảng Call). Trần token mỗi việc thay cho trần tiền (R7).

Chi tiết: [research.md](research.md) · [data-model.md](data-model.md) · [contracts/](contracts/) · [quickstart.md](quickstart.md).

## Technical Context

**Language/Version**: Python 3.12; JavaScript thuần có `@ts-check` (giao diện); POSIX sh

**Primary Dependencies**: như 007. Ảnh `studio-web` cài thêm `claude-agent-sdk`, chỉ để có tệp chạy `claude` (R9). Bộ chuyển tiếp vẫn dùng `httpx`. Không thêm thư viện mới.

**Storage**: SQLite của 007, thêm bảng `claude_account`, `call` và cột `job.tokens`. Thông tin đăng nhập nằm trong tệp ở `/data/claude/slot-<n>/` (700), không nằm trong cơ sở dữ liệu.

**Testing**: `unittest` như 007. Thêm Claude Code giả (`STUDIO_CLAUDE_BIN`). Dịch vụ Claude giả trả được `429` của gói và `401`. Bài kiểm với tài khoản thật chạy bằng tay (quickstart).

**Target Platform**: như 007 (Ubuntu 24.04, Docker Compose, một máy)

**Project Type**: dịch vụ web và worker (sửa 007)

**Performance Goals**: SC-101 (đăng nhập < 2 phút); đổi tài khoản không làm chậm lệnh gọi quá thời gian của một lần gửi lại

**Constraints**:
- Thông tin đăng nhập không vào container, nhật ký hay API (FR-104, SC-103).
- Chỉ một lần đăng nhập đang chờ.
- Không hai lệnh Claude Code chạy chồng trên cùng một slot (khoá tệp).

**Scale/Scope**: nhóm dưới 20 người, tối đa 5 tài khoản Claude, N = 2 việc cùng lúc

## Constitution Check

| Nguyên tắc | Kết quả |
|---|---|
| I. Spec là nguồn sự thật | ✓ Spec đã làm rõ 3 câu. Spec sửa 007 qua bảng "Thay đổi so với 007" |
| II. Không đoán | ✓ có điều kiện. Hành vi của Claude Code mà tài liệu chưa nói rõ (R1, R2, R3, R5) được ghi "Kiểm khi implement". Task T001 kiểm bằng tài khoản thật; kết quả khác thì dừng và hỏi |
| III. MVP theo story | ✓ US1 (một tài khoản, chạy được phim) tự chạy được. US2 (nhiều tài khoản), US3 (người dùng), US4 (mức dùng) thêm dần |
| IV. Đo được | ✓ SC-103 … SC-107 có test tự động với Claude giả. SC-101, SC-102 kiểm bằng tay với tài khoản thật |
| V. Đơn giản | ✓ Không thêm dịch vụ hay thư viện. Lời mời dùng lại bảng cũ. Xoay vòng nằm trong bộ chuyển tiếp có sẵn. Một mục ở Complexity Tracking |
| VI. Thư viện gốc | ✓ Không chạm `lib/` |
| VII–IX | ✓ Không đổi cách dựng hình, học phong cách hay làm phim |
| Bản quyền, nội dung | ✓ Không commit thông tin đăng nhập. `/data/claude` nằm ngoài repo |
| Điều khoản Anthropic (không phải nguyên tắc, ghi để nhớ) | ⚠ Spec giả định chủ xưởng chịu trách nhiệm. Bỏ đăng ký công khai (FR-111) để chỉ dùng nội bộ. Gọi gói luôn qua Claude Code (R3, R6), không gửi thẳng mã của gói từ code của xưởng |

Kiểm lại sau thiết kế: đạt.

## Project Structure

### Documentation (this feature)

```text
specs/008-claude-plan-login/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/
│   ├── api-admin-claude.md   # tài khoản Claude, người dùng, mức dùng
│   └── runner.md             # biến của container, cách chọn tài khoản trong bộ chuyển tiếp
├── checklists/requirements.md
└── tasks.md                  # /speckit-tasks
```

### Source Code (repository root)

```text
tools/studio/studio/
├── claude_plan.py      # mới: slot, chạy Claude Code (login, status, logout, -p) có khoá tệp, đọc và làm mới mã,
│                       #      chọn tài khoản (R4), đánh dấu limited / needs_signin (R5)
├── db.py               # sửa: lược đồ mới (data-model "Chuyển phiên bản lược đồ")
├── accounts.py         # sửa: bỏ signup, thêm quản lý người dùng (R8)
├── quotas.py           # sửa: bỏ trần chi phí ngày, thêm trần token, báo cáo từ Call
├── moderation.py       # sửa: claude -p trên gói, dự phòng khoá API (R6)
├── mail.py             # sửa: mẫu claude_signin
├── api_online.py       # sửa: /admin/claude*, /admin/users, /auth/setup, mức dùng
└── web/                # sửa: trang AI accounts, Settings có tab (General, Users, Usage), mức dùng bằng token; bỏ trang đăng ký
tools/runner/
├── proxy.py            # sửa: chọn tài khoản, gửi lại khi 429/401, khoá dự phòng, ghi Call, trần token
└── worker.py           # sửa: biến môi trường chế độ gói, chỉ nhận việc khi ready
deploy/
├── web.Dockerfile      # sửa: cài claude-agent-sdk
├── compose.yaml        # sửa: ANTHROPIC_API_KEY không bắt buộc
└── README.md           # sửa: đăng nhập gói, người dùng, điều khoản
tests/online/
├── fake_claude         # mới: Claude Code giả
└── test_claude_plan.py · test_users.py · sửa test_proxy.py, test_admin.py, test_quota.py, live.py
```

**Structure Decision**: Logic gói nằm trong một mô-đun `claude_plan.py` trong gói `studio`, vì cả web (đăng nhập, kiểm nội dung) và proxy (gọi) đều dùng nó. Proxy đã import `studio` như 007.

## Complexity Tracking

| Thêm | Vì sao cần | Cách đơn giản hơn bị loại vì |
|---|---|---|
| Bộ chuyển tiếp gửi lại lệnh gọi sang tài khoản khác khi `429` hoặc `401` | FR-108, SC-104: việc dài hàng chục phút không được lỗi chỉ vì một tài khoản chạm hạn mức | Trả `429` cho container để SDK tự thử lại: SDK thử lại cùng đường, nên vẫn rơi vào tài khoản đó, hoặc phải chờ nhiều giờ |
