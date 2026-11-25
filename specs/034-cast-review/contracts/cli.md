# Contract: lệnh

Tất cả qua `sh bin/studio`. Mã thoát chung: 0 đạt · 1 kiểm chưa đạt hoặc bị chặn · 2 sai tham số hoặc tệp hỏng · 3 thiếu điều kiện (chưa duyệt, app không chạy, AE chưa sẵn sàng) · 4 nội dung đã đổi (`--base` lệch). `--dir <thư mục phim>` như các lệnh `notes`.

## Phim

| Lệnh | Làm gì |
|---|---|
| `cast check <phim>` | Kiểm `cast/cast.json` theo `contracts/files.md` và danh mục rig. In từng lỗi kèm mã nhân vật. |
| `cast status <phim> [--json]` | Bảng nhân vật: trạng thái (new, ready, approved, changed), số ghi chú mở, nguồn (film/library v<n>), rig. Dòng cuối `point cast: <state>`. |
| `ae sheet <phim> [--only id,id]` | Dựng bảng mẫu (mọi nhân vật, hoặc chỉ các id) qua AE; ghi `cast/catalog.json`, `cast/sheets/<id>/`, chuyển bản cũ sang `<id>.prev/`. Mã 3 khi AE chưa sẵn sàng. Trong việc của app đi qua cầu nối. |
| `cast approve <phim> (<id>…\|--all) [--save\|--no-save] [--source chat\|ui]` | Duyệt nhân vật. `--all` duyệt cả dàn và gọi duyệt điểm `cast`. Mã 1 khi nhân vật chưa có bảng mẫu hoặc còn ghi chú mở. `--save` (mặc định theo `save_to_library`) ghi vào kho nếu app đang chạy; app không chạy thì in cảnh báo, vẫn duyệt. |
| `cast notes show <phim> [--all] [--json]` | Ghi chú mở (hoặc tất cả), theo nhân vật: số, hình, ghim (x, y), chữ. Dòng cuối `base: …`. In đường dẫn ảnh của hình được ghim. |
| `cast notes reply <phim> <id> "<chữ>" [--done\|--open] --base <b>` | Trả lời một ghi chú. |
| `cast use <phim> <kênh>/<id>[@v]` | Lấy nhân vật từ kho vào phim (R9). Mã 3 khi app không chạy hoặc không có nhân vật. |
| `voice make <phim>` | (sửa) Sau cổng script, gọi cổng `cast`: mã 1 kèm "characters not approved: hero, friend". |

## Kho nhân vật

| Lệnh | Làm gì |
|---|---|
| `cast library [<kênh>] [--json]` | Liệt kê nhân vật, bản mới nhất, rig, ngày duyệt, số phim, nhãn `new rig version`. |
| `cast preview <kênh>/<id> --rig ball@N` | Dựng bảng mẫu bằng rig mới vào `v<n+1>.preview/`. |
| `cast update <kênh>/<id> --from-preview` | Biến bản xem trước thành bản `v<n+1>` chưa duyệt; duyệt bằng `cast library-approve`. |
| `cast library-approve <kênh>/<id>` | Duyệt bản mới nhất trong kho. |

## Rig

| Lệnh | Làm gì |
|---|---|
| `ae rigs [--check]` | Liệt kê phiên bản rig trong `rigs.lock`; `--check` mã 1 khi một thư mục đã khoá bị đổi. |
| `ae rigs --lock ball@N` | Khoá một phiên bản mới (chỉ khi chưa có trong `rigs.lock`). |
