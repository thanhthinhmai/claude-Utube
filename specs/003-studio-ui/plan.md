# Implementation Plan: Giao diện và API của xưởng (giai đoạn 1)

**Branch**: `003-studio-ui` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/003-studio-ui/spec.md`

## Summary

Ba phần:

1. **Sổ việc và yêu cầu duyệt** (`tools/studio/`, Python): lưu trạng thái trong `.studio/` (không vào git), ghi nguyên tử. Lệnh `sh bin/studio job …` để Claude ghi việc và bước, và `sh bin/studio review …` để gửi yêu cầu duyệt rồi **chờ chặn** (`review wait`) tới khi có quyết định từ giao diện hoặc khung chat. Quyết định đầu tiên thắng nhờ tạo file độc quyền.
2. **Máy chủ** FastAPI + uvicorn chỉ nghe `127.0.0.1`: API `/api/v1/…` có tài liệu OpenAPI tự sinh, Server-Sent Events cho cập nhật trực tiếp, phục vụ phim, ảnh và hồ sơ đo theo **mã tài nguyên**, không theo đường dẫn tự do. Kiểm `Host` và bắt buộc header riêng cho mọi lệnh ghi (chống DNS rebinding và CSRF). `job start` tự bật máy chủ chạy nền; `ui stop` tắt.
3. **Giao diện** HTML + JavaScript thuần, không bước build, tiếng Việt: danh sách việc, trang việc, trang duyệt lần 1 và lần 2, trang phim, hồ sơ đo, phong cách riêng; tiêu đề tab và thông báo trình duyệt khi có việc chờ duyệt.

Cập nhật skill `style-learn` (bước 0–10) và luồng làm phim trong `CLAUDE.md` để ghi việc, bọc lệnh dài bằng `job run`, và đưa 2 lần duyệt qua `review request` / `review wait`.

## Technical Context

**Language/Version**: Python 3.11+ (máy chủ, CLI, trong `tools/.venv` sẵn có); JavaScript ES2020 thuần (trình duyệt); POSIX sh (`bin/studio`)
**Primary Dependencies**: `fastapi`, `uvicorn`, `markdown` (hiển thị `STYLE.md`, tóm tắt duyệt); `httpx` chỉ cho kiểm thử. Cài bằng `sh bin/studio deps ui` (tầng `tools/requirements-ui.txt`)
**Storage**: File JSON trong `.studio/jobs/<id>.json`, `.studio/reviews/<id>.json`, `.studio/reviews/<id>.decision.json`, `.studio/server.json`; đọc tài nguyên có sẵn trong `films/`, `references/`, `my-styles/`
**Testing**: `tests/ui/run.sh` → `unittest` + FastAPI `TestClient` (API, bảo mật, sự kiện), kiểm thử CLI qua subprocess (`job`, `review wait`/`decide`, quyết định đầu tiên thắng, bật và tắt máy chủ); một kiểm thử trình duyệt tuỳ chọn dùng Playwright của thư viện (bỏ qua nếu không có)
**Target Platform**: WSL2 (mở từ trình duyệt Windows qua `localhost`), Linux, macOS
**Project Type**: Ứng dụng web cục bộ (máy chủ và giao diện tĩnh) cùng CLI
**Performance Goals**: Việc mới hiện trên giao diện < 5 s; sau quyết định, việc chạy tiếp < 10 s; danh sách 50 việc < 2 s; thông báo chờ duyệt < 10 s
**Constraints**: Chỉ truy cập từ chính máy; không phục vụ tệp ngoài `films/`, `references/`, `my-styles/`; không sửa `lib/`; không thêm bước build cho giao diện
**Scale/Scope**: 1 người dùng; vài chục việc; khoảng 15 điểm API; 6 trang giao diện

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Kiểm tra | Kết quả |
|---|---|---|
| I. Spec là nguồn sự thật | Spec có 2 câu làm rõ đã ghi; công nghệ chỉ ở plan | ✅ |
| II. Không đoán | Các điểm cần kiểm chứng khi code (WSL chuyển tiếp `localhost`, `Range` cho video) có kiểm thử hoặc bước quickstart | ✅ |
| III. MVP trước | US1 (theo dõi) chạy độc lập; US2 (duyệt) và US3 (xem kết quả) xây trên đó | ✅ |
| IV. Đo được | SC-001…009 đều có kiểm thử tự động hoặc bước quickstart đo thời gian | ✅ |
| V. Đơn giản | Không cơ sở dữ liệu, không bước build, không framework giao diện; FastAPI có giải trình | ✅ (có giải trình) |
| VI. Thư viện giữ nguyên | Không đụng `lib/`; chỉ đọc kết quả phim trong `films/` | ✅ |
| VII. Một bộ máy dựng hình | Không liên quan (chỉ hiển thị) | N/A |
| VIII. Học bằng đo | Hai lần duyệt giữ nguyên nội dung của skill 002, chỉ đổi kênh duyệt | ✅ |
| IX. Spec-kit không cho phim | Không tạo spec cho phim; chỉ ghi việc | ✅ |
| Bản quyền | Ảnh ghép và khung gốc chỉ phục vụ cho `127.0.0.1`; `.studio/` không vào git; không gửi gì ra ngoài | ✅ |

**Re-check sau Phase 1**: không phát sinh vi phạm.

## Project Structure

### Documentation (this feature)

```text
specs/003-studio-ui/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/
│   ├── api-v1.md          # điểm truy cập, mã lỗi, sự kiện
│   ├── cli.md             # sh bin/studio ui | job | review
│   └── skill-integration.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
bin/studio                       # thêm: ui [open|stop|status] · job … · review … · deps ui
tools/requirements-ui.txt        # fastapi, uvicorn, markdown, httpx
tools/studio/
├── studio_cli.py                # điểm vào cho job / review / ui
└── studio/
    ├── store.py                 # .studio/: ghi nguyên tử, khoá, đọc danh sách
    ├── jobs.py                  # Việc: tạo, bước, nhật ký, trạng thái, không còn hoạt động
    ├── reviews.py               # Yêu cầu duyệt: tạo, chờ, quyết định đầu tiên thắng
    ├── resources.py             # phim, bộ tham chiếu, phong cách: tìm và kiểm đường dẫn
    ├── server.py                # FastAPI app: /api/v1, SSE, tệp tĩnh, bảo mật
    ├── launcher.py              # bật nền, kiểm còn sống, tắt
    └── web/                     # index.html, app.js, style.css (tiếng Việt)
tests/ui/
├── run.sh
└── test_*.py
.claude/skills/style-learn/SKILL.md   # thêm ghi việc và duyệt qua review
CLAUDE.md                              # luồng làm phim: ghi việc; nhắc giao diện
.gitignore                             # .studio/
```

**Structure Decision**: Mã giao diện nằm cạnh công cụ học phong cách trong `tools/`, dùng chung `tools/.venv`. `studio/` là một gói riêng để giai đoạn 2 có thể đưa lên máy chủ mà không kéo theo công cụ đo.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Thêm FastAPI + uvicorn | FR-015 cần tài liệu API máy đọc được, có phiên bản; FastAPI tự sinh OpenAPI từ mã và kiểm dữ liệu vào; giai đoạn 2 chạy được trên máy chủ thật mà không viết lại | `http.server` của Python: phải tự viết định tuyến, kiểm dữ liệu, tài liệu OpenAPI, `Range` cho video và SSE; nhiều mã tự viết hơn, dễ sai bảo mật |
| Lệnh chờ chặn `review wait` thay vì để Claude tự hỏi lại | Claude Code chỉ đợi được khi một lệnh đang chạy; lệnh chặn có giới hạn thời gian giúp việc tiếp tục < 10 s mà không cần người dùng gõ gì | Bắt người dùng quay lại khung chat gõ "tiếp": trái FR-008 và SC-009 |
