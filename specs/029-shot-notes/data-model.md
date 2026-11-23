# Data model: Ghi chú từng shot

## Mốc shot (`shots.json`)

| Trường | Kiểu | Luật |
|---|---|---|
| `version` | số | `1` |
| `video` | chuỗi | tên tệp video trong thư mục phim (`<tên>.mp4`) |
| `duration` | số (giây) | độ dài video khi ghi |
| `fps` | số | tốc độ khung (để đổi "1 khung") |
| `source` | chuỗi | `page` (SHOTS của trang) · `ae` (bản tổng After Effects) |
| `shots` | danh sách `[t0, t1, set, id]` | cùng dạng `window.SHOTS`; `id` là mã shot duy nhất (chuỗi), `set` là bối cảnh (chuỗi, có thể rỗng) |

Luật kiểm: 1–300 shot; `shots[0].t0 = 0`; `t1 > t0`; `shots[i].t0 = shots[i-1].t1` (lệch ≤ 1 khung); `shots[-1].t1` lệch `duration` ≤ 1 khung; `id` không trùng. Sai thì trả danh sách lỗi `{row, rule, detail}`.

Số shot hiển thị = vị trí trong danh sách (1-based). Ghi chú gắn theo `id`.

## Sổ ghi chú (`shot-notes.json`)

```json
{
  "version": 1,
  "shots": {
    "<id>": {
      "status": "none|fix|fixed|ok",
      "status_by": "auto|user",
      "notes": [ { "id": "n-<8 hex>", "at": 5.0, "text": "…", "images": ["img-…png"], "done": false,
                   "by": "<tên hoặc email | local>", "created": "<ISO>", "updated": "<ISO>", "reply": "…" } ]
    }
  }
}
```

- `at`: giây tính từ đầu shot (1 chữ số thập phân) hoặc `null` (cả shot).
- `text`: 0–2.000 ký tự; ghi chú phải có `text` không rỗng hoặc ≥ 1 ảnh.
- `images`: 0–4 tên tệp trong `shot-notes/`, dạng `img-[0-9a-f]{12}\.(png|jpg|webp)`.
- `reply`: dòng trả lời của Claude (≤ 2.000 ký tự) hoặc vắng.
- Shot vắng trong sổ = trạng thái `none`.

### Trạng thái shot

| Giá trị | Nhãn giao diện |
|---|---|
| `none` | No notes (chưa có) |
| `ok` | No issue |
| `fix` | Needs fix |
| `fixed` | Fixed |

Luật tự suy (khi `status_by = auto`, áp sau mỗi lần đổi ghi chú của shot): còn ghi chú `done = false` → `fix`; có ghi chú và tất cả `done` → `fixed`; không còn ghi chú → `none`. Người dùng bấm nút trạng thái → đặt `status`, `status_by = user`. Lần đổi ghi chú kế tiếp của shot đó → `status_by = auto` và tự suy lại (FR-007).

### Dấu nội dung

`base` = sha256 hex của byte tệp `shot-notes.json` (tệp chưa có: sha256 của chuỗi rỗng). Mọi lần ghi kèm `base`; khác thì từ chối `changed`.

### Ghi chú mồ côi

Ghi chú có `id` shot không còn trong `shots.json` hiện tại: vẫn giữ trong sổ; API trả ở `orphans` để giao diện hiện mục "Ghi chú của shot không còn" (FR-015).

## Ảnh đính kèm (`shot-notes/`)

Tệp ảnh do máy chủ đặt tên; ≤ 10 MB; PNG/JPEG/WebP theo byte đầu. Không còn ghi chú nào nhắc tới và cũ hơn 1 giờ → bị xoá khi lưu sổ.

## Bản video trước

`<tên>.prev.mp4` + `shots.prev.json`, có tối đa một bộ. Tạo bởi `film replace`; bị thay ở lần replace sau.

## Đệm ảnh nhỏ (`.shots/thumbs/<dấu video>/`)

`<chỉ số shot 1-based>_<a|b|c>.jpg` ở 12%, 50%, 88% thời lượng shot; `<dấu video>` = `<kích thước>-<mtime ns>` của tệp video. Thư mục với dấu khác bị xoá khi tạo đệm mới.
