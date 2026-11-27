# CLI contract: 038

Mã thoát chung (giống `ae`):

| Mã | Nghĩa |
|---|---|
| 0 | đạt |
| 1 | lỗi dựng, hoặc kiểm chưa đạt |
| 2 | đầu vào sai |
| 3 | thiếu bộ máy, không có GPU, hoặc mất cầu nối |

## `sh bin/studio ae plan <phim> [--suggest] [--set S3 engine=blender size=wide …] [--json]`

- In bảng các shot với các cột: mã, bộ máy, gợi ý, lý do, cỡ, độ cao máy, ống kính, chiều sâu, số lớp, bối cảnh.
- `--suggest` ghi `suggested` và `reason` cho mọi shot. Shot chưa có `engine` thì ghi luôn `engine`.
- `--set` đổi trường của một shot. Giá trị sai thì thoát mã 2.

## `sh bin/studio ae build <phim> [--shots …] [--draft]`

- Phim không có shot Blender: hành vi như specs/032, ra cùng tệp.
- Phim trộn, chạy theo thứ tự:
  1. Lượt tính (Blender) cho các shot Blender có nhân vật.
  2. Lượt lớp (AE).
  3. Lượt AE cho các shot AE.
  4. Lượt Blender.
  5. Ghép.
- Trước khi dựng, in `estimate: blender <N> frames ≈ <m> min`.
- Kết quả: `out/build.mp4`, `build-shots.json` có `source:"mixed"` và `engines`.
- Shot đã `done` mà `version` không đổi thì bỏ qua (dựng tiếp).

## `sh bin/studio ae fix <phim> S5 [S9 …]`

- Dựng lại đúng các shot đó theo bộ máy của từng shot, rồi ghép theo khung vào video hiện có như specs/032.
- Shot Blender mà rig hoặc động tác đổi thì chạy lại cả lượt lớp.

## `sh bin/studio ae render <phim>`

- Chặn theo `points.gate(…,"animatic")` như cũ.
- Thêm `depthcheck.gate()`: còn luật chặn chưa sửa và chưa được người dùng miễn thì thoát mã 1 và in từng dòng `S5 depth_shallow: …`.

## `sh bin/studio ae status [<phim>]`

Thêm cột bộ máy và trạng thái "Must run again" cho các shot `stale`.

## `sh bin/studio ae uses <phim> <hàm…>`

Tìm cả trong script shot Blender: `k.<hàm>(` và `k.set("<tên>")`.

## `sh bin/studio blender status`

In các dòng `blender: <đường dẫn> <phiên bản>`, `gpu: <renderer>` hoặc `gpu: software (blocked)`, `work: <thư mục>`.

| Mã | Khi |
|---|---|
| 0 | sẵn sàng |
| 3 | thiếu Blender hoặc dựng bằng phần mềm |

## `sh bin/studio blender config [--exe PATH] [--work DIR] [--timeout SEC]`

Ghi `blender.json`. Không có tham số thì in cấu hình hiện tại.

## `sh bin/studio blender build <phim> S3 [--still F] [--quarter]`

Dựng lẻ một shot Blender, hoặc một khung (`--still`) để xem nhanh. `--quarter` dựng ở ¼ cỡ.

## `sh bin/studio blender plate <phim> S5 --from S4`

Dựng ảnh nền không có nhân vật từ bối cảnh của S4, với máy khai báo cho S5, ra `ae/data/plates/S5.png`.

## `sh bin/studio qc depth <phim> [--json]`

- Chạy labeler trên khung giữa của từng shot (lấy từ animatic nếu có, nếu không thì dựng khung ¼), so với khối `depth` của phong cách.
- Ghi `checks.json` → `tiers.depth`.

| Mã | Khi |
|---|---|
| 0 | đạt, có thể kèm cảnh báo |
| 1 | có shot bị chặn |
| 2 | phong cách không có khối `depth`: hướng dẫn chạy `learn` lại |

## `sh bin/studio qc except <phim> <shot> depth_close|depth_shallow|card_angle --reason "…"`

Như cũ. Từ chối với mã 2 khi biến `STUDIO_JOB` có mặt, vì chỉ người dùng được miễn.

## `sh bin/studio status`

Thêm hai dòng:
- `after effects: <đường dẫn> | not set`
- `blender: <đường dẫn> gpu <renderer> | not set`
