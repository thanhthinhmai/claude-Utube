# Contract: API và trang việc cho gói đăng

Các đường API đặt trong `server.py`, dùng chung cho local (003) và online (007). Quyền xem giống `/films/{name}/poster`: phim phải nằm trong kho của người đang đăng nhập (`resources.film_dir`). Admin xem được như với file phim (FR-014). Mọi đường đều chỉ đọc.

## `GET /api/v1/films/{name}/publish`

**200**:

```json
{"titles": [{"angle": "curiosity", "text": "…", "thumbnail": "thumbnail-1.png", "thumb_text": "…"}],
 "description": "<toàn bộ description.md>",
 "subtitles": "subtitles.srt",
 "files": ["thumbnail-1.png", "thumbnail-2.png", "thumbnail-3.png", "titles.md", "description.md",
           "subtitles.srt", "PUBLISH.md"],
 "check": {"pass": true, "cut": null, "problems": []}}
```

- Không có phụ đề: `subtitles` là `null`.
- **404** `not_found`: phim không có, không thuộc người này, hoặc phim không có `publish/PUBLISH.md`.

## `GET /api/v1/films/{name}/publish/{file}`

- `file` phải khớp `^(thumbnail-[123]\.(png|jpg)|subtitles\.srt|titles\.md|description\.md|PUBLISH\.md)$`. Tên khác trả **404**, kể cả `pack.json` và `thumbs.json`.
- Loại nội dung trả về: `image/png`, `image/jpeg`, `application/x-subrip; charset=utf-8` (kèm `Content-Disposition: attachment; filename="<name>.srt"`), hoặc `text/markdown; charset=utf-8`.

## `GET /api/v1/films/{name}/publish.zip`

- **200** `application/zip`, tên tệp `<name>-publish.zip`. Gồm các tệp trong danh sách cho phép ở trên, cộng với `<name>.srt` lấy từ `subtitles.srt`.
- **404**: như đường đầu tiên.

## Trang việc (`app.js`)

- `STAGES` = `[… "Render", "Self-check", "Publish"]`.
- Việc phim đã `done` mà có `qa.publish`: hiện khối `<section id="publish">` ngay dưới khối Quality, gồm:
  - tiêu đề "Publish";
  - 3 thẻ ảnh. Mỗi thẻ có `<img loading="lazy">`, nhãn hướng (Curiosity, Number, Question), tiêu đề, chữ trên ảnh và nút **Copy title**;
  - mô tả trong `<pre>` với nút **Copy description**;
  - nút **Download subtitles** (ẩn khi `subtitles` là `null`) và nút **Download pack**;
  - một dòng kết quả kiểm: "Publish check: pass", hoặc "Publish check: 2 problems" kèm danh sách. Khi có `cut`: "The publish step was stopped: <lý do>".
- Bấm copy thì chữ được chép đúng nguyên văn, không kèm nhãn. Nút đổi thành "Copied" trong 2 giây.
- Màn hình 360 px: các thẻ xếp một cột, không có thanh cuộn ngang.
- Việc không có `qa.publish`, ví dụ việc cũ: không hiện khối này.
