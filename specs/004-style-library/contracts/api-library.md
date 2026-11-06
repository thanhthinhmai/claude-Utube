# Contract: Thư viện (API v1 + setup/status)

Theo mọi quy ước của [003 api-v1](../../003-studio-ui/contracts/api-v1.md) (chỉ trên máy, kiểm `Host`, lỗi `{"error": {"code", "message"}}`). Ba dòng dưới đây được thêm vào bảng của api-v1.md để một bảng duy nhất mô tả API v1.

## Điểm truy cập mới (chỉ `GET`)

| Phương thức · Đường dẫn | Trả về | Lỗi |
|---|---|---|
| `GET /library` | `Library` (xem data-model.md); chưa có thư viện → `{installed: false, styles: [], groups: [], posters: {have: 0, total: 0}, skipped: 0}` | |
| `GET /library/styles/{slug}` | `LibraryStyle` kèm `style_html` | `404 not_found` · `400 bad_name` |
| `GET /library/styles/{slug}/poster` | `image/jpeg`, `Cache-Control: max-age=86400`, `ETag` | `404 not_found` · `400 bad_name` |

Thay đổi ở điểm đã có:

| Điểm | Thay đổi |
|---|---|
| `GET /styles`, `GET /styles/{slug}` | thêm `based_on_in_library: bool` |

**An toàn:**
- `slug` phải khớp `[a-z0-9-]{1,60}` (sai → `400 bad_name`) **và** là thư mục phong cách hợp lệ của thư viện (không → `404`). `_template` luôn `404`.
- Tệp được đọc: chỉ `lib/lemo-opuscar/styles/<slug>/{style.json,STYLE.md,poster.jpg}`. Danh sách thư mục được phép trong api-v1.md thêm `lib/lemo-opuscar/styles/`.

## `sh bin/studio setup` (thay đổi)

- Danh sách sparse không còn loại `styles/*/poster.jpg`; vẫn loại `styles/*/demo/`, `styleboard/`, `docs/frames/`, `docs/cover.jpg`, `docs/opuscar98.jpg`.
- Lần cài đầu tải thư viện **chưa kèm** poster (danh sách cũ), rồi chạy bước poster bên dưới; lỗi poster không làm hỏng lần cài.
- Thư viện vừa cài, `ok` hoặc `outdated` mà danh sách sparse khác hoặc thiếu poster: in `↓ đang tải poster của phong cách…`, ghi danh sách, `git sparse-checkout reapply`.
  - Thành công: `✓ đã có poster: 66/66`.
  - Lỗi: `✗ poster chưa tải được (mất mạng?). Làm phim vẫn được; chạy lại: sh bin/studio setup`. Không đổi mã thoát của `setup`.

## `sh bin/studio status` (thay đổi)

- Dòng chữ: `Phong cách thư viện: 66 · poster: 66/66 · phong cách riêng: 1 · phim: 0`.
- `--json`: thêm `"counts": {"library_posters": 66, …}`.
- Thiếu poster không làm `status` báo "chưa sẵn sàng" (poster chỉ dùng cho giao diện).
