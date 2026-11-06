# Data Model: Khung xưởng phim

## LibraryLock (`library.lock`)

| Trường | Kiểu | Ràng buộc |
|---|---|---|
| `LIB_REPO` | URL git | Bắt buộc |
| `LIB_COMMIT` | SHA | Bắt buộc, đúng 40 ký tự hex |

Biến môi trường `STUDIO_LIB_REPO` và `STUDIO_LIB_COMMIT` ghi đè được (chỉ dùng cho test). Thiếu hoặc sai định dạng → `setup` và `status` thoát mã 2 kèm thông báo.

## Library (`lib/lemo-opuscar/`)

Trạng thái được suy ra mỗi lần chạy:

| Trạng thái | Điều kiện |
|---|---|
| `missing` | Thư mục không tồn tại hoặc rỗng |
| `foreign` | Có nội dung nhưng không phải repo git có `studio.managed=true` |
| `modified` | Có file được theo dõi bị sửa (trừ `package-lock.json`) |
| `outdated` | `HEAD` ≠ `LIB_COMMIT` |
| `ok` | Không rơi vào các trạng thái trên |

Chuyển trạng thái do `setup`:
- `missing` → `ok` (tải mới).
- `outdated` → `ok` (fetch và checkout).
- `foreign`, `modified` → dừng, giữ nguyên, thoát mã 1.

## Tool

| Trường | Ví dụ |
|---|---|
| `name` | `node` |
| `found` | `20.11` hoặc rỗng |
| `min` | `20` |
| `state` | `ok` · `missing` · `old` · `unknown` |
| `hint` | gợi ý cài hoặc nâng cấp |

`unknown` (không đọc được phiên bản) chỉ cảnh báo, không chặn "sẵn sàng".

## StudioStatus (đầu ra `status`)

- `ready` (bool) = thư viện `ok` **và** không công cụ nào `missing` hoặc `old`.
- `library`: `{path, state, commit_expected, commit_found}`.
- `tools`: danh sách Tool.
- `counts`: `{library_styles, my_styles, films}`.
  - `library_styles`: số thư mục `lib/lemo-opuscar/styles/*/` có `STYLE.md`, trừ `_template`.
  - `my_styles`: số thư mục `my-styles/*/` có `STYLE.md`.
  - `films`: số thư mục con của `films/`.
- `deps_core` (bool, chỉ thông tin): thư viện đã có `node_modules/` và `.venv/`.
