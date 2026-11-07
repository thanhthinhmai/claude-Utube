# Implementation Plan: Xưởng phim online, bản dùng thử đầu tiên

**Branch**: `007-online-studio` | **Date**: 2026-11-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-online-studio/spec.md`

## Summary

Đưa xưởng lên một máy chủ cho khách dùng qua web. Cùng mã nguồn với giai đoạn 1, chọn chế độ bằng `STUDIO_MODE=online`; chế độ `local` giữ nguyên.

- **Web**: FastAPI của 003, thêm tài khoản (email và mật khẩu, cookie phiên), hạn mức, trang giao việc và trang quản trị. Dữ liệu trong SQLite.
- **Chạy việc**: một **worker** lấy việc từ hàng đợi (tối đa N việc cùng lúc, mỗi khách 1). Mỗi việc chạy **Claude Agent SDK** trong một **container Docker riêng**, dùng đúng `CLAUDE.md` và skill của xưởng, nên quy trình làm phim và học phong cách không phải viết lại.
- **Chi phí**: container không có khoá API. Mọi lệnh gọi Claude đi qua một **bộ chuyển tiếp** trên máy chủ; bộ này gắn khoá thật, đo chi phí và chặn khi vượt trần.
- **Chờ khách**: khi cần khách trả lời hoặc duyệt, việc kết thúc lượt và trả chỗ chạy. Khi khách quyết định thì việc chạy tiếp bằng cách nối lại phiên.

Chi tiết các lựa chọn: [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12 (máy chủ, worker, bộ chuyển tiếp); JavaScript thuần, không có bước biên dịch (giao diện, có `@ts-check`); POSIX sh (`bin/studio`)

**Primary Dependencies**:
- Có sẵn từ 003: FastAPI, uvicorn
- Thêm: `claude-agent-sdk` (chỉ trong ảnh container), `anthropic` (lệnh kiểm nội dung, R9), `httpx` (bộ chuyển tiếp), `argon2-cffi`, `python-multipart` (tải video lên)
- Công cụ hệ thống: Docker Engine và Compose, Caddy

**Storage**: SQLite (WAL) `/data/studio.db`; tệp phim, phong cách, bộ tham chiếu trong `/data/accounts/<id>/`; thư mục làm việc của việc trong `/data/jobs/<id>/`

**Testing**:
- `unittest` như 003, gộp vào `tests/ui/run.sh`, thêm `tests/online/`.
- Test online dùng một **tác tử giả** thay cho Claude (một script ghi bước, tạo yêu cầu duyệt, xuất phim mẫu) và một **API Claude giả** sau bộ chuyển tiếp, nên chạy không cần mạng và không tốn tiền.
- Container chỉ được test khi có Docker; không có thì bỏ qua kèm lý do.
- Một bài chạy thật với Claude (`tests/online/live.sh`) chỉ chạy bằng tay, có ghi chi phí.

**Target Platform**: Ubuntu 24.04 trên một máy chủ thuê (khoảng 8 vCPU, 16 GB RAM), dùng Docker Compose

**Project Type**: dịch vụ web, kèm worker chạy việc nền

**Performance Goals**: SC-006 (90% phim 30 giây xong trong 20 phút); SC-007 (cập nhật tiến độ ≤ 5 giây, dùng lại SSE của 003)

**Constraints**:
- Hạn mức đúng khi nhiều yêu cầu cùng lúc (SC-008).
- Không vượt N việc chạy cùng lúc (SC-009).
- Không có đường nào phát hay tải được video gốc (SC-004).
- Khoá API không bao giờ vào container.
- Chi phí mỗi ngày không vượt trần (SC-005).

**Scale/Scope**: bản dùng thử: tới vài trăm tài khoản, N = 2 việc cùng lúc, một máy

## Constitution Check

| Nguyên tắc | Kết quả |
|---|---|
| I. Spec là nguồn sự thật | ✓ Spec đã duyệt và làm rõ; công nghệ chỉ nằm trong plan và research |
| II. Không đoán | ✓ 7 câu đã hỏi người dùng. Tên tuỳ chọn của Agent SDK **PHẢI** kiểm lại trên tài liệu khi implement (R1, R5) |
| III. MVP theo story | ✓ US1 (tài khoản và làm phim) tự chạy và tự test được; US2–US4 thêm dần |
| IV. Đo được | ✓ SC-001…009 đều có test tự động, trừ SC-006 (đo bằng bài chạy thật) |
| V. Đơn giản | ⚠ Thêm Docker, worker, bộ chuyển tiếp, SQLite. Lý do ở Complexity Tracking. Đã chọn cách đơn giản nhất cho mỗi phần: SQLite thay PostgreSQL, hàng đợi trong cơ sở dữ liệu thay Redis, Compose thay Kubernetes |
| VI. Thư viện gốc giữ nguyên | ✓ Ảnh container chép thư viện theo `library.lock`, không sửa |
| VII. Một bộ máy dựng hình | ✓ Dùng đúng bộ máy của thư viện |
| VIII. Học bằng đo | ✓ Dùng lại skill `style-learn` |
| IX. Spec-kit cho phần mềm | ✓ Phim của khách đi theo quy trình của thư viện, không tạo spec |
| Bản quyền 2.1.0 | ✓ Xác nhận quyền (FR-017), không có đường lộ video gốc (FR-018), xoá sau khi học, có tác vụ quét lại (FR-019, R10); không commit khoá API |

Kiểm lại sau thiết kế: đạt, với một ngoại lệ có lý do (V).

## Project Structure

### Documentation (this feature)

```text
specs/007-online-studio/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/
│   ├── api-online.md     # điểm truy cập mới (tài khoản, giao việc, quản trị)
│   └── runner.md         # worker, container việc, bộ chuyển tiếp API
├── checklists/requirements.md
└── tasks.md              # /speckit-tasks
```

### Source Code (repository root)

```text
tools/studio/studio/
├── store.py            # sửa: chọn chế độ local (tệp JSON) hoặc online (SQLite)
├── db.py               # mới: lược đồ SQLite, giao dịch, chuyển phiên bản lược đồ
├── accounts.py         # mới: đăng ký, xác minh, đăng nhập, phiên, đặt lại mật khẩu, xoá tài khoản
├── quotas.py           # mới: hạn mức tháng, trần chi phí ngày, cài đặt
├── jobs.py · reviews.py  # sửa: owner thật, trạng thái queued, loại duyệt question/treatment
├── moderation.py       # mới: kiểm ý tưởng trước khi nhận (R9)
├── mail.py             # mới: hàng thư, SMTP hoặc ghi ra tệp
├── server.py           # sửa: middleware đăng nhập ở chế độ online, gắn các router mới
├── api_online.py       # mới: /auth, /me, POST /jobs, /uploads, /admin
└── web/                # sửa app.js, index.html, style.css: đăng nhập, giao việc, trả lời câu hỏi, quản trị
tools/runner/
├── worker.py           # mới: hàng đợi, bật container, khởi động lại, dọn định kỳ
├── proxy.py            # mới: bộ chuyển tiếp Messages API, đo chi phí, /internal
└── agent.py            # mới: chạy trong container, gọi Claude Agent SDK, ghi .result.json
tools/studio/studio_cli.py  # sửa: ở chế độ online, job/review gọi /internal
deploy/
├── compose.yaml · Caddyfile · job.Dockerfile · web.Dockerfile
└── README.md           # cách dựng máy chủ, biến môi trường, sao lưu
bin/studio              # sửa: thêm lệnh admin create, online up/down
tests/online/           # mới: test tài khoản, hạn mức, hàng đợi, cách ly, bộ chuyển tiếp, xoá video, tác tử giả
```

**Structure Decision**: Giữ một gói `studio` cho cả hai chế độ (R12). Phần chạy việc nằm riêng trong `tools/runner/`, vì nó có phụ thuộc riêng và chạy trong tiến trình hoặc container riêng. Phần triển khai nằm trong `deploy/`.

## Complexity Tracking

| Thêm | Vì sao cần | Cách đơn giản hơn bị loại vì |
|---|---|---|
| Container Docker cho mỗi việc | FR-027: tác tử có Bash và chạy theo ý tưởng không tin được của khách | Người dùng Linux riêng: không chặn được mạng ra ngoài, cách ly yếu |
| Bộ chuyển tiếp API | Không để khoá API trong container; đo và chặn chi phí theo việc (FR-008, SC-005) | Đưa khoá vào container: có thể bị lộ qua Bash |
| Worker riêng | FR-008a hàng đợi và giới hạn N; việc không mất khi web khởi động lại | Chạy việc trong tiến trình web: mất việc khi khởi động lại |
| SQLite | Giao dịch hạn mức đúng khi nhiều yêu cầu cùng lúc (SC-008), nhiều khách | Tệp JSON và khoá tệp: khó đúng khi nhiều khách; PostgreSQL: thêm một dịch vụ |
| Caddy | FR-024 HTTPS và tự gia hạn chứng chỉ | Tự cấu hình TLS: dễ sai, phải gia hạn bằng tay |
