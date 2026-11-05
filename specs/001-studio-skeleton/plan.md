# Implementation Plan: Khung xưởng phim (Studio Skeleton)

**Branch**: `001-studio-skeleton` | **Date**: 2026-11-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-studio-skeleton/spec.md`

## Summary

Một lệnh `bin/studio` (POSIX shell) với ba lệnh con:
- `setup` đưa thư viện lemo-opuscar về `lib/lemo-opuscar` ở commit ghim trong `library.lock`. Thư viện được tải dạng sparse, không có demo. Lệnh không bao giờ ghi đè thay đổi cục bộ, và báo công cụ hệ thống còn thiếu.
- `status [--json]` báo trạng thái xưởng.
- `deps [voice] [music]` chuyển tiếp an toàn sang trình cài gói của thư viện.

Kèm theo là các thư mục `my-styles/`, `films/`, `tools/`, `references/`, `.gitignore` tương ứng, và `CLAUDE.md` điều hướng 3 luồng. Bộ máy dựng hình được chốt là trang web với hàm `render(t)` của thư viện (xem [research.md](research.md) §1).

## Technical Context

**Language/Version**: POSIX `sh` (dash, bash, zsh ở chế độ sh); không dùng bashism
**Primary Dependencies**: `git` ≥ 2.25 (sparse-checkout; ≥ 2.35 để bỏ demo, thấp hơn thì tải đủ thư viện); coreutils chuẩn (`sed`, `awk`, `grep`, `find`)
**Storage**: Files: `library.lock` (key=value), thư viện trong `lib/lemo-opuscar/`
**Testing**: `tests/run.sh`: shell script, thư mục tạm, PATH giả chứa công cụ giả in phiên bản, thư viện giả là repo git cục bộ (không cần mạng)
**Target Platform**: macOS, Linux, WSL
**Project Type**: CLI nhỏ cùng cấu trúc dự án và tài liệu hướng dẫn agent
**Performance Goals**: `setup` lần đầu < 5 phút; chạy lại < 10 s và không tải; `status` < 5 s (SC-001…003)
**Constraints**: Không sửa file trong thư viện; không tự cài phần mềm hệ thống; `status` chạy offline; đường dẫn có dấu cách vẫn chạy
**Scale/Scope**: 1 script khoảng 250 dòng, 1 file test, 4 README thư mục, cập nhật `CLAUDE.md` và `.gitignore`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Kiểm tra | Kết quả |
|---|---|---|
| I. Spec là nguồn sự thật | Spec đã có, không nhắc công nghệ; công nghệ chỉ ở plan | ✅ |
| II. Không đoán | Spec không còn `[NEEDS CLARIFICATION]`; các mặc định ghi ở Assumptions | ✅ |
| III. MVP trước | P1 (`setup`) chạy và test độc lập; P2 (`status`), P3 (`CLAUDE.md`) làm sau | ✅ |
| IV. Đo được | SC-001…007 có số; `tests/run.sh` kiểm từng FR; bước cần mạng được ghi rõ | ✅ |
| V. Đơn giản | 1 script, không framework; một lệnh con thêm (`deps`) có lý do ở Complexity Tracking | ✅ (có giải trình) |
| VI. Thư viện giữ nguyên | Thư viện nằm trong `lib/`, ghim commit, không sửa; phát hiện và từ chối khi bị sửa | ✅ |
| VII. Một bộ máy dựng hình | Chốt `render(t)` của thư viện; Remotion bị loại, lý do ở research.md | ✅ |
| VIII. Học bằng đo | Không thuộc phạm vi (tính năng 002) | N/A |
| IX. Spec-kit không cho phim | `CLAUDE.md` ghi rõ phim theo quy trình thư viện, không spec | ✅ |
| Bản quyền | `references/`, `films/`, mọi media bị gitignore | ✅ |

**Re-check sau Phase 1**: không phát sinh vi phạm mới.

## Project Structure

### Documentation (this feature)

```text
specs/001-studio-skeleton/
├── spec.md
├── plan.md              # file này
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── studio-cli.md    # Phase 1: giao diện lệnh bin/studio
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
bin/
└── studio               # setup | status [--json] | deps [voice] [music] | help
library.lock             # LIB_REPO, LIB_COMMIT (có trong git)
lib/                     # gitignore; lib/lemo-opuscar/ do setup tạo
my-styles/README.md      # phong cách riêng (có trong git)
films/README.md          # phim (nội dung gitignore, chỉ giữ README)
tools/README.md          # công cụ tự viết (có trong git)
references/README.md     # video tham chiếu (nội dung gitignore, chỉ giữ README)
tests/
└── run.sh               # test cho bin/studio
CLAUDE.md                # điều hướng 3 luồng
.gitignore
```

**Structure Decision**: Một dự án đơn. Script đặt ở `bin/` và tự tìm gốc dự án từ vị trí của chính nó, nên chạy được từ thư mục con.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Lệnh con `deps` không có trong spec | Trình cài gói của thư viện tự đoán vị trí thư viện từ thư mục hiện tại. Chạy từ gốc dự án, nó sẽ tải **một bản thư viện khác** vào `~/lemo-opuscar` (research.md §4). `deps` đặt đúng biến môi trường rồi gọi trình cài đó | Chỉ ghi hướng dẫn trong README: dễ quên biến môi trường, hỏng âm thầm |
