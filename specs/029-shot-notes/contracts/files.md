# Tệp trong thư mục phim (029)

| Tệp | Ai ghi | Ai đọc | Vào git |
|---|---|---|---|
| `shots.json` | `render` / `shots export` (phim web); bước ghép bản tổng (phim AE); `film replace` | app, `notes show`, Claude | không (`films/` không vào git) |
| `shot-notes.json` | app (PUT notes), `notes reply` | app, `notes show`, Claude | không |
| `shot-notes/img-*.png|jpg|webp` | app (POST images) | app, Claude (mở ảnh khi sửa) | không |
| `<tên>.prev.mp4`, `shots.prev.json` | `film replace` | app (Xem bản trước) | không |
| `.shots/thumbs/<dấu>/…jpg` | máy chủ app (đệm) | app | không |

Định dạng chi tiết: [data-model.md](../data-model.md).

Ví dụ `shots.json` (phim AE 40 shot):
```json
{ "version": 1, "video": "ae-crayon-test.mp4", "duration": 137.6, "fps": 30, "source": "ae",
  "shots": [[0, 2.5, "", "S1"], [2.5, 3.9, "", "S2"], [134.533, 137.6, "", "S40"]] }
```

Thư mục `shot-notes/` và `.shots/` thuộc danh sách tệp mà trang "Done so far" (specs/025) không liệt kê.
