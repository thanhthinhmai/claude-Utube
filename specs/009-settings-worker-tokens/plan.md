# Implementation Plan: Settings → Worker và API tokens

**Branch**: `009-settings-worker-tokens` | **Date**: 2026-11-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/009-settings-worker-tokens/spec.md`

## Summary

Xây trên 008 (xưởng online nội bộ, Settings có General, Users, Usage). Thêm:

- **Tab Worker** (chỉ Owner): worker ghi lần báo sống vào SQLite mỗi 5 giây; web đọc ra trạng thái từng tiến trình (coi là dừng sau 30 giây), bốn ô đếm và 20 việc mới nhất; giao diện đọc lại mỗi 5 giây (R4).
- **Mã API** cho mọi người dùng, tự tạo cho chính mình ở Your account; Owner xem và thu hồi mọi mã ở Settings → API tokens. Mã đi qua middleware sẵn có như một phiên của người sở hữu, bị giới hạn bởi vai trò thực, quyền dùng lượt, danh sách đường cấm và số yêu cầu mỗi phút (R1–R3, R9).
- **Máy chủ MCP** ở `/api/mcp` bằng thư viện `mcp` đã có sẵn; mỗi công cụ là một lệnh gọi REST của chính xưởng với cùng mã, nên không có logic thứ hai (R5). Tải video lên và tải phim về qua MCP bằng **vé dùng một lần** (R6).
- Khung **For agents**: Base URL, header, OpenAPI, lệnh `claude mcp add`, cấu hình JSON; sau khi tạo mã có Copy token, Copy MCP command, Copy for an agent (R7).
- **Nhật ký từng yêu cầu của mã** (30 ngày) và **Idempotency-Key** cho giao việc; máy chủ MCP có thêm 3 công cụ chung như neb (R3, R5, R10). Đối chiếu đầy đủ với neb: R11.

Chi tiết: [research.md](research.md) · [data-model.md](data-model.md) · [contracts/](contracts/) · [quickstart.md](quickstart.md).

## Technical Context

**Language/Version**: Python 3.12; JavaScript thuần có `@ts-check` (giao diện); POSIX sh

**Primary Dependencies**: như 008 (FastAPI, uvicorn, httpx, argon2-cffi, claude-agent-sdk). Thêm dòng ghim `mcp==2.3.0` vào `tools/requirements-online.txt`; thư viện này **đã được cài** vì `claude-agent-sdk` cần nó, nên không thêm gói mới vào môi trường.

**Storage**: SQLite của 008, lược đồ phiên bản 3: bảng `api_token`, `token_request`, `idempotency`, `worker_beat`, `ticket`.

**Testing**: `unittest` như 007/008; trình duyệt bằng Playwright (`tests/online/browser_*.cjs`); máy chủ MCP kiểm bằng client MCP của chính thư viện `mcp` (gọi trong tiến trình); tác tử giả cho SC-208.

**Target Platform**: như 008 (Ubuntu 24.04, Docker Compose, một máy; chạy được trên máy của chủ xưởng không cần Docker).

**Project Type**: dịch vụ web và worker (sửa 008)

**Performance Goals**: SC-201 (biết tình trạng worker trong ≤ 5 giây), SC-202 (≤ 40 giây phát hiện worker dừng). Một lần ghi SQLite cho mỗi yêu cầu có mã là đủ với nhóm dưới 20 người.

**Constraints**:
- Mã đầy đủ chỉ hiện một lần; không có trong cơ sở dữ liệu, nhật ký, API (FR-210, SC-204).
- Mã không làm được các việc ở FR-213 bằng bất kỳ đường nào, kể cả qua MCP.
- `/api/mcp` không giữ phiên, không dùng SSE, để đi qua Caddy và chạy được nhiều tiến trình web về sau.

**Scale/Scope**: dưới 20 người dùng, mỗi người tối đa 20 mã Active, 1–2 tiến trình worker.

## Constitution Check

| Nguyên tắc | Kết quả |
|---|---|
| I. Spec là nguồn sự thật | ✓ Spec đã làm rõ 4 câu (MCP, ai tạo mã, học phong cách qua MCP, những phần lấy theo neb). Cách tải video lên qua MCP (R6) là cách hiểu FR-220 trong giới hạn của giao thức, ghi rõ ở research |
| II. Không đoán | ✓ có điều kiện. API của `mcp` 2.3.0 đã kiểm trên máy (`MCPServer`, `streamable_http_app(stateless_http=True)`, `Context.headers`). Một mục "Kiểm khi implement": Caddy có ghi header `Authorization` không (R8) |
| III. MVP theo story | ✓ US1 (tab Worker) độc lập. US2 (mã API) chạy được không cần US1. US3 (quản lý, For agents, MCP) thêm trên US2 |
| IV. Đo được | ✓ SC-201 … SC-208 đều có test tự động (đồng hồ giả cho báo sống, tìm chuỗi mã, client MCP, tác tử giả) |
| V. Đơn giản | ✓ Không thêm dịch vụ, không thêm gói mới vào môi trường. Mã đi qua middleware sẵn có. Công cụ MCP gọi lại REST. Hai mục ở Complexity Tracking |
| VI. Thư viện gốc | ✓ Không chạm `lib/` |
| VII–IX | ✓ Không đổi cách dựng hình, học phong cách hay làm phim |
| Bản quyền, nội dung | ✓ Học từ YouTube qua MCP vẫn bắt xác nhận quyền như web (FR-220); video tham chiếu vẫn bị xoá khi học xong |

Kiểm lại sau thiết kế: đạt.

## Project Structure

### Documentation (this feature)

```text
specs/009-settings-worker-tokens/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/
│   ├── api-tokens-worker.md   # xác thực bằng mã, /me/tokens, /admin/tokens, /admin/worker, vé tải lên/tải về, OpenAPI
│   └── mcp.md                 # máy chủ MCP: địa chỉ, xác thực, công cụ
├── checklists/requirements.md
└── tasks.md                   # /speckit-tasks
```

### Source Code (repository root)

```text
tools/studio/studio/
├── db.py              # sửa: lược đồ 3 (api_token, token_request, idempotency, worker_beat, ticket)
├── tokens.py          # mới: tạo, tìm theo băm, thu hồi, liệt kê, vai trò thực, nhật ký, giới hạn mỗi phút; vé dùng một lần;
│                      #      Idempotency-Key
├── ratelimit.py       # sửa: hit() nhận giới hạn và cửa sổ riêng
├── server.py          # sửa: online_guard nhận Bearer (bỏ qua cookie và CSRF), danh sách đường cấm mã, gắn /api/mcp,
│                      #      ẩn đường cấm mã khỏi OpenAPI
├── api_online.py      # sửa: /me/tokens (+ /log), /admin/tokens (+ /log), /admin/worker, Idempotency-Key ở POST /jobs, /uploads/tickets, /uploads/t/{vé},
│                      #      /films/{name}/tickets, /films/t/{vé}; spend_not_allowed ở POST /jobs; admin() theo vai trò thực
├── mcp_server.py      # mới: MCPServer, công cụ riêng và 3 công cụ chung ở contracts/mcp.md, tài nguyên OpenAPI;
│                      #      gọi REST trong tiến trình bằng httpx ASGITransport
└── web/               # sửa: Settings → Worker, Settings → API tokens (mọi mã), Your account → API tokens, khung For agents
tools/runner/
└── worker.py          # sửa: báo sống mỗi 5 giây và khi bắt đầu hay xong việc; xoá hàng khi dừng êm
tools/requirements-online.txt   # sửa: ghim mcp==2.3.0
deploy/Caddyfile                # sửa nếu cần (R8: không ghi Authorization)
tests/online/
├── test_tokens.py · test_worker_status.py · test_mcp.py · test_tickets.py · test_idempotency.py
└── browser_tokens.cjs · browser_worker.cjs
```

**Structure Decision**: Mọi phần mới nằm trong gói `studio` của web (mã, vé, MCP) và một thay đổi nhỏ ở worker (báo sống). Không có dịch vụ mới; MCP chạy trong tiến trình web.

## Complexity Tracking

| Thêm | Vì sao cần | Cách đơn giản hơn bị loại vì |
|---|---|---|
| Máy chủ MCP trong web | FR-219 (người dùng chọn B: có MCP như neb) | Chỉ OpenAPI và đoạn mẫu: người dùng đã chọn có MCP |
| Vé tải lên và tải về dùng một lần | FR-220: tải video lên và tải phim về qua MCP; máy chủ MCP không đọc được tệp của tác tử, một lệnh gọi MCP giới hạn 4 MB | Gửi video base64 qua MCP: vượt giới hạn. Để tác tử tự gửi mã trong `curl`: mã phải nằm trong shell của tác tử |
