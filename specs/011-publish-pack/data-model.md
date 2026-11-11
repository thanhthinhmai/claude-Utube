# Data Model: Gói đăng YouTube (011)

Mọi tệp nằm trong `films/<tên>/publish/` (contracts/files.md). Online không có bảng mới; chỉ thêm trường vào việc.

## PublishPack (`publish/pack.json`, agent viết)

| Trường | Kiểu | Luật |
|---|---|---|
| `language` | chuỗi | Mã ngôn ngữ; phải bằng `Language` của `SCRIPT.md` khi có (FR-008) |
| `titles` | 3 × Title | Đúng 3, đúng thứ tự `curiosity`, `number`, `question` |
| `hook` | 2 chuỗi | Tổng ≤ 150 ký tự (FR-004) |
| `summary` | chuỗi | 1–600 ký tự |
| `chapters` | Chapter[] | Theo R4; rỗng khi không áp dụng |
| `hashtags` | chuỗi[] | 3–5, dạng `#chữ`, mỗi thẻ ≤ 30 ký tự |

**Title**: `angle` (`curiosity` \| `number` \| `question`), `text` (≤ 100 ký tự; > 60 đơn vị thì có chỗ ngắt ở vị trí ≤ 60), `thumb` (Thumbnail đi cặp).

**Thumbnail** (trong Title): `t` (giây, 0 ≤ t < thời lượng; 3 giá trị cách nhau ≥ 1 giây), `text` (≤ 6 từ hoặc 12 ký tự CJK; không trùng nguyên câu và không chung chuỗi 3 từ liền nhau với `text` của tiêu đề), `position` (`top` \| `bottom` \| `center`, mặc định `bottom`), `color` (màu CSS hex, mặc định `#ffffff`), `plate` (hex hoặc `null`, mặc định `#000000`), `plate_opacity` (0–1, mặc định 0.6), `font` (họ phông của phim, tuỳ chọn).

**Chapter**: `from` (`Pnn` có trong `SCRIPT.md`; tăng dần), `title` (1–40 ký tự).

## Tệp do lệnh `publish` viết

| Tệp | Khi nào có | Nguồn |
|---|---|---|
| `thumbnail-1..3.png` (hoặc `.jpg`) | luôn có | R2 |
| `thumbs.json` | luôn có | Số đo từng ảnh (R3): `file`, `w`, `h`, `bytes`, `text_height_ratio`, `contrast`, `missing_glyphs`, `font`, `font_loaded` |
| `titles.md` | luôn có | `pack.titles` |
| `description.md` | luôn có | hook + summary + chương + nguồn + hashtag |
| `subtitles.srt` | khi có `narration.json` và `lines_file` | R5 |
| `PUBLISH.md` | luôn có | gộp; ghi phần thiếu và lý do (FR-001a) |

Các tệp này luôn được viết lại cả bộ mỗi lần chạy `publish`, nên không còn tệp cũ khi phim đổi (FR-015).

## PublishCheck (`checks.json["publish"]`)

```json
{"at": "2026-11-11T10:00:00Z", "pass": false, "cut": null,
 "applicable": {"chapters": true, "subtitles": true},
 "measures": {"files_missing": [], "thumbs": [{"file": "thumbnail-1.png", "w": 1280, "h": 720, "bytes": 812345,
               "text_height_ratio": 0.11, "contrast": 7.2, "repeats_title": false, "missing_glyphs": []}],
              "title_lengths": [54, 71, 48], "title_breaks_ok": [true, true, true],
              "hook_chars": 132, "description_chars": 1420, "hashtags": 4, "angle_brackets": 0,
              "chapters": [{"at": 0.0, "title": "…", "length": 14.2}], "chapters_bad": [],
              "numbers_unsourced": [], "subtitles_match": true, "subtitle_cues_bad": [],
              "subtitle_start_offset_max": 0.12},
 "problems": ["thumbnail-2.png: contrast 3.1, needs at least 4.5"]}
```

- `pass` = không có `problems`.
- `cut`: lý do bước Publish bị dừng (R7), nếu có.
- `applicable` cho biết mục chương và phụ đề có áp dụng không. Mục không áp dụng thì không sinh lỗi.

## Job (online, mở rộng 007–010)

| Trường | Thay đổi |
|---|---|
| `step` | thêm giá trị `Publish` (sau `Self-check`) |
| `publish_cut` | mới: chuỗi lý do khi bị dừng ở bước Publish (R7), hoặc không có |
| `qa.publish` | mới: `{pass, cut, applicable, problems, titles: [3 chuỗi], files: [tên tệp]}`, tóm tắt từ `checks.json["publish"]` để trang việc hiện; `null` khi không có gói |

## Chuyển trạng thái của bước Publish

```
Self-check ─► Publish ─► (agent: job done) ─► cổng QC của worker ─► done
                │                                  │
                ├─ chạm trần / watchdog / hết giờ ─┘ (publish_cut, không vòng sửa QC)
                └─ gói trượt sau 1 vòng sửa ─► vẫn job done, qa.publish.pass = false
```
