# Data Model: Thư viện phong cách trên Film Studio

Không có dữ liệu lưu mới. Các thực thể dưới đây chỉ là dạng dữ liệu API trả về, đọc từ file có sẵn.

## LibraryStyle

Nguồn: `lib/lemo-opuscar/styles/<slug>/style.json`, `STYLE.md`, `poster.jpg`.

| Trường | Kiểu | Nguồn / quy tắc |
|---|---|---|
| `slug` | string | tên thư mục; khớp `^[a-z0-9-]{1,60}$`; khác `_template` |
| `num` | string | `style.json`; dùng để sắp xếp (so theo số) |
| `en`, `cn` | string | `style.json` |
| `category` | string | `style.json` → `category_en` |
| `film` | string | tên phim mẫu |
| `line` | string | câu mô tả phim mẫu (tiếng Anh) |
| `uses` | string[] | mục đích dùng |
| `dur` | number | độ dài phim mẫu (giây), 0 nếu không có |
| `has_poster` | bool | `poster.jpg` có trên đĩa |
| `github_url` | string \| null | research §5 |
| `style_html` | string | chỉ ở chi tiết: `STYLE.md` đã làm sạch (như 003) |

Quy tắc:
- Thiếu `style.json`, JSON hỏng, thiếu `en`: bỏ qua, đếm vào `skipped`.
- Không trả trường nào ngoài bảng trên.

## Library (danh sách)

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `installed` | bool | có thư viện do xưởng quản lý |
| `version` | string | 7 ký tự đầu của commit |
| `styles` | LibraryStyle[] (không có `style_html`) | sắp theo `num` |
| `groups` | `[{name, count}]` | theo thứ tự xuất hiện đầu tiên khi sắp theo `num` |
| `posters` | `{have, total}` | để hiện gợi ý chạy `setup` khi `have < total` |
| `skipped` | int | số phong cách bị bỏ qua |

## MyStyle (đã có ở 003, thêm trường)

| Trường thêm | Kiểu | Ghi chú |
|---|---|---|
| `based_on_in_library` | bool | `based_on` là một `slug` có trong thư viện → giao diện tạo link |

## StylePrompt (chỉ ở giao diện)

`Make a 40-second film in the <en> style about …` — không lưu, không gửi đi đâu ngoài bộ nhớ tạm của trình duyệt.
