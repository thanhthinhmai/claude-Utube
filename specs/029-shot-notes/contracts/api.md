# API: phần Shots của trang phim

Tiền tố `/api/v1`. Cả chế độ local và online (online: chỉ phim của người đăng nhập, `store.as_account`). Mọi lỗi theo dạng có sẵn `{"error": {"code", "message"}}`. Tên phim theo `NAME` của `resources.py`; sai → 400 `bad_name`; không có phim → 404 `not_found`. Ghi (POST/PUT) cần CSRF như các đường ghi hiện có; mã API chỉ đọc (nếu có vai bị giới hạn) → 403 `forbidden`.

## GET /films/{name}

Thêm vào kết quả hiện có: `has_shots` (bool), `has_prev` (bool).

## GET /films/{name}/shots[?prev=1]

200:
```json
{ "valid": true, "problems": [], "duration": 137.6, "fps": 30, "source": "ae",
  "shots": [ { "n": 1, "id": "S1", "set": "", "t0": 0.0, "t1": 2.5 } ],
  "thumbs": "ready|building", "video_stamp": "15644380-1795…" }
```
- Không có `shots.json`: 200 `{ "valid": false, "missing": true, "problems": [], "shots": [] }`.
- Tệp sai luật: 200 `valid: false`, `problems: [{row, rule, detail}]`, `shots: []`.
- `prev=1`: đọc `shots.prev.json`; không có → 404 `not_found`.

## GET /films/{name}/shots/thumbs/{n}/{a|b|c}.jpg

Ảnh JPEG 320 px của shot `n` (1-based). Ảnh chưa có → bắt đầu tạo đệm (nếu chưa chạy) và trả 202 `{"status":"building"}`; giao diện thử lại sau 1 s. `n` ngoài khoảng → 404. Header `Cache-Control: max-age=86400` kèm `video_stamp` trong truy vấn để đổi video là đổi URL.

## GET /films/{name}/video?prev=1

Bản video trước (`<tên>.prev.mp4`); không có → 404.

## GET /films/{name}/notes

200:
```json
{ "base": "<sha256>", "doc": { "version": 1, "shots": { … } }, "orphans": ["S41"] }
```
`doc` theo data-model.md (sổ chưa có → `{"version":1,"shots":{}}`).

## PUT /films/{name}/notes

Body: `{ "base": "<sha256>", "doc": { … } }`.
- Máy chủ kiểm `doc` (data-model.md), áp luật tự suy cho shot có `status_by = auto`, điền `by`/`updated` cho ghi chú mới hoặc đổi chữ, dọn ảnh mồ côi > 1 giờ, ghi nguyên tử trong khoá tệp.
- 200 `{ "base": "<sha256 mới>", "doc": { … } }`.
- 409 `changed`: `base` không khớp; body lỗi kèm `current: {base, doc}`.
- 422 `invalid`: sai luật (chữ quá dài, quá 4 ảnh, ảnh không có trong `shot-notes/`, trạng thái lạ…), nói rõ trường.

## POST /films/{name}/notes/images

`multipart/form-data`, trường `file`. Kiểm byte đầu (PNG/JPEG/WebP) và cỡ ≤ 10 MB.
- 201 `{ "file": "img-0a1b2c3d4e5f.png" }`
- 413 `too_large`, 415 `bad_image`.

## GET /films/{name}/notes/images/{file}

Ảnh đính kèm; `file` phải khớp `img-[0-9a-f]{12}\.(png|jpg|webp)` → khác thì 400 `bad_name`; không có → 404.
