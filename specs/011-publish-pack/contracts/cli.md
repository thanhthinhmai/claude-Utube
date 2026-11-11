# Contract: lệnh `publish` của `bin/studio`

Lệnh chạy được ở local và trong container (`STUDIO_MODE=online`). Thông báo in ra bằng tiếng Anh, ngắn. Với `--json`, lệnh in đúng một đối tượng JSON, giống `checks.json["publish"]` (data-model.md).

## `sh bin/studio publish <film> [--check-only | --no-draw] [--json]`

- **Không có `--check-only`:** đọc `publish/pack.json`, viết lại cả bộ tệp của gói (thumbnail, `thumbs.json`, `titles.md`, `description.md`, `subtitles.srt`, `PUBLISH.md`), rồi kiểm.
- **Có `--check-only`:** chỉ kiểm các tệp đang có, không render. Worker dùng chế độ này. Mục thumbnail lấy số đo từ `thumbs.json` và đo lại dung lượng và cỡ ảnh.
- Kết quả được ghi vào `checks.json["publish"]` và phần "Publish" của `CHECKS.md` (giữ nguyên mục `script`, `film`). Lệnh không gọi Claude và không dùng mạng.
- `--no-draw`: viết lại các tệp chữ (tiêu đề, mô tả, phụ đề, `PUBLISH.md`) nhưng giữ thumbnail và `thumbs.json` như đang có, rồi kiểm. Dùng cho test và agent giả của test online.
- `<film>` là tên trong `films/` hoặc đường dẫn thư mục phim, như các lệnh của 010.

| Mã thoát | Nghĩa |
|---|---|
| 0 | gói đạt mọi luật |
| 1 | gói trượt; mỗi lỗi in một dòng, ví dụ `thumbnail-2.png contrast 3.1 < 4.5` |
| 2 | không chạy được: không có `pack.json`, `pack.json` sai khuôn dạng, không có `<film>.mp4`. Không viết tệp nào |

**Phim thiếu dữ liệu** (FR-001a, phim cũ): không có `narration.json` thì không có phụ đề và chương, và mục đó là "không áp dụng". Không có `SCRIPT.md` thì số trong tiêu đề và mô tả được so với `SOURCES.md` nếu có, còn không thì bỏ luật số (`numbers_checked: false`). `PUBLISH.md` ghi từng phần thiếu và lý do.

## Luật kiểm và ngưỡng (FR-009)

| Mã lỗi | Luật |
|---|---|
| `files_missing` | thiếu tệp bắt buộc (tuỳ `applicable`) |
| `thumb_size` | không đúng 1280×720 (phim ngang) hoặc 720×1280 (phim dọc), hoặc ≥ 2 000 000 byte |
| `thumb_text_words` | chữ trên ảnh > 6 từ (hoặc > 12 ký tự CJK), hoặc rỗng |
| `thumb_text_height` | `text_height_ratio` < 0,08 |
| `thumb_contrast` | `contrast` < 4,5 (R3) |
| `thumb_glyphs` | chữ trên ảnh có ký tự thiếu phông |
| `thumb_font` | phông của chữ trên ảnh không nạp được trong trang (`font_loaded: false`), nên trình duyệt đã dùng phông khác |
| `thumb_repeats_title` | chữ trên ảnh trùng nguyên tiêu đề đi cặp hoặc chung chuỗi ≥ 3 từ liền nhau (≥ 6 ký tự với CJK); so sau khi chuẩn hoá chữ thường, bỏ dấu câu |
| `thumb_same_time` | 2 thumbnail cách nhau < 1 giây |
| `thumb_not_rendered` | không render được (kèm lý do); ở `--check-only` là thiếu `thumbs.json` |
| `title_count` | không đúng 3 tiêu đề, hoặc sai bộ hướng |
| `title_length` | > 100 ký tự |
| `title_break` | > 60 đơn vị mà không có chỗ ngắt ở vị trí ≤ 60 (R6). CJK tính 2 đơn vị mỗi ký tự |
| `hook_length` | 2 dòng mở đầu > 150 ký tự, hoặc không đủ 2 dòng |
| `description_length` | `description.md` > 5 000 ký tự |
| `hashtags` | không có 3–5 thẻ hợp lệ |
| `angle_brackets` | có `<` hoặc `>` trong tiêu đề hay mô tả |
| `number_unsourced` | số trong tiêu đề hay mô tả không có trong `SCRIPT.md` hoặc `SOURCES.md` |
| `language` | `pack.language` khác `Language` của `SCRIPT.md` |
| `chapters` | sai luật R4: chương đầu không phải đoạn đầu, < 3 chương, chương < 10 giây, `from` không tăng hoặc không có, tên rỗng hoặc > 40 ký tự; hoặc `chapters` rỗng khi chia được |
| `subtitles_text` | chữ phụ đề khác kịch bản đã đạt (in đoạn khác đầu tiên) |
| `subtitles_cue` | khối > 2 dòng, dòng > 42 đơn vị, khối < 1 giây hoặc > 7 giây, mốc đè nhau |

## Thay đổi ở các lệnh có sẵn

- `sh bin/studio qc` không đổi. Gói đăng không nằm trong cổng QC chặn việc giao phim.
- Usage của `bin/studio` thêm dòng `publish <phim> [--check-only] [--json]`.
