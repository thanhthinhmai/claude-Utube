# Implementation Plan: Thư viện phong cách trên Film Studio

**Branch**: `004-style-library` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/004-style-library/spec.md`

## Summary

Ba phần, xây trên máy chủ và giao diện của 003:

1. **Tải poster** (`bin/studio`): bỏ dòng `!/styles/*/poster.jpg` khỏi danh sách sparse. Máy mới nhận poster ngay khi `setup`. Máy cũ: `setup` thấy danh sách sparse khác hoặc còn thiếu poster thì ghi danh sách mới rồi chạy `git sparse-checkout reapply`, chỉ lấy thêm 66 ảnh (đo được 22 MB, xem research §1). `status` báo `posters: n/66`.
2. **API chỉ đọc** (`tools/studio`): `resources.py` thêm phần thư viện (đọc `lib/lemo-opuscar/styles/*/style.json`, `STYLE.md`, `poster.jpg`, bỏ `_template`); `server.py` thêm `GET /api/v1/library`, `/library/styles/{slug}`, `/library/styles/{slug}/poster`. Chỉ nhận mã đúng mẫu và có trong danh sách.
3. **Giao diện** (`web/`): mục "Library" (lưới thẻ, lọc nhóm, tìm, trạng thái trong địa chỉ trang, poster tải lười), trang chi tiết, nút "Use this style"; mục "Styles" đổi tên "My styles", thêm "Use this style" và link phong cách nền.

## Technical Context

**Language/Version**: Python 3.11+ (máy chủ, trong `tools/.venv`); JavaScript ES2020 thuần; POSIX sh (`bin/studio`); git ≥ 2.27 (`sparse-checkout reapply`, đã có 2.43 trong phiên này)
**Primary Dependencies**: không thêm gói mới (dùng `fastapi`, `markdown` của tầng `ui`). Không dùng Pillow (chỉ có ở tầng `learn`), nên không tạo ảnh thu nhỏ
**Storage**: Không có dữ liệu mới. Đọc file có sẵn trong `lib/lemo-opuscar/styles/`; mã commit đọc từ `lib/lemo-opuscar/.git/HEAD`, địa chỉ kho từ `library.lock`
**Testing**: `tests/run.sh` (setup tải poster, máy cũ nhận poster, poster lỗi không làm hỏng thư viện, `status` đếm poster); `tests/ui/` (API thư viện, từ chối tên lạ, OpenAPI khớp contract, trình duyệt: lọc, tìm, chép câu lệnh)
**Target Platform**: WSL2, Linux, macOS (như 003)
**Project Type**: Ứng dụng web cục bộ + CLI (như 003)
**Performance Goals**: Trang Library 66 thẻ < 2 s; lọc và tìm < 0,2 s (lọc trên trình duyệt, không gọi lại máy chủ)
**Constraints**: Không sửa file trong `lib/` (VI); chỉ phục vụ `style.json` (đã chọn trường), `STYLE.md` (đã làm sạch) và `poster.jpg` của thư viện; không tải phim mẫu
**Scale/Scope**: 66 phong cách (11 nhóm); 3 điểm API mới; 2 trang mới, 2 trang sửa

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Kiểm tra | Kết quả |
|---|---|---|
| I. Spec là nguồn sự thật | Spec có 1 câu làm rõ đã ghi (hai mục riêng); công nghệ chỉ ở plan | ✅ |
| II. Không đoán | Dung lượng poster và cách cập nhật máy cũ đã đo và thử thật (research §1, §2) | ✅ |
| III. MVP trước | US1 (xem, tìm) dùng được một mình; US2, US3 xây trên đó | ✅ |
| IV. Đo được | SC-001…007 có test tự động hoặc bước quickstart | ✅ |
| V. Đơn giản | Không gói mới, không ảnh thu nhỏ, không bộ nhớ đệm phía máy chủ; lọc ở trình duyệt | ✅ |
| VI. Thư viện giữ nguyên | Chỉ đổi danh sách sparse (cấu hình git của bản sao, không phải file thư viện); test kiểm `git status` của thư viện sạch | ✅ |
| VII. Một bộ máy dựng hình | Không liên quan | N/A |
| VIII. Học bằng đo | Không liên quan | N/A |
| IX. Spec-kit không cho phim | Không tạo spec cho phim | ✅ |
| Bản quyền | Poster và luật thư viện (MIT) chỉ phục vụ cho `127.0.0.1`; phim mẫu (CC BY 4.0) chỉ link về GitHub | ✅ |

**Re-check sau Phase 1**: không phát sinh vi phạm.

## Project Structure

### Documentation (this feature)

```text
specs/004-style-library/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/
│   └── api-library.md     # 3 điểm API mới + thay đổi setup/status
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
bin/studio                         # SPARSE có poster; setup cập nhật máy cũ; status đếm poster
tools/studio/studio/
├── resources.py                   # + library(), library_style(), library_poster()
├── server.py                      # + /api/v1/library, /library/styles/{slug}, /poster
└── web/
    ├── index.html                 # thanh bên: Library, My styles, Measurements
    ├── app.js                     # + trang Library, chi tiết, Use this style; My styles
    └── style.css                  # + lưới thẻ thư viện, thanh lọc, ô thay thế poster
specs/003-studio-ui/contracts/api-v1.md   # thêm 3 dòng; thêm lib/lemo-opuscar/styles/ vào danh sách thư mục được đọc
tests/run.sh                       # + poster: máy mới, máy cũ, lỗi tải, status
tests/ui/test_library.py           # API thư viện, an toàn, dữ liệu thiếu
tests/ui/browser_check.cjs         # + Library: lọc, tìm, Use this style
tests/ui/helpers.py                # + thư viện giả trong dự án tạm
README.md                          # mục giao diện: Library
```

**Structure Decision**: Không có gói hay thư mục mới. Phần thư viện nằm trong `resources.py` cạnh phần phong cách riêng, vì cả hai cùng dạng (đọc file, kiểm mã, trả JSON).

## Complexity Tracking

Không có vi phạm cần giải trình.
