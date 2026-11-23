# Lệnh `bin/studio` cho mốc shot, ghi chú và thay video

Mọi lệnh nhận `--dir <thư mục phim>`. Không có `--dir`: dùng bản phim trong kho của chủ xưởng khi app đang chạy và có phim đó, nếu không thì `films/<phim>` của dự án (research R8). Dòng đầu luôn in `film: <thư mục>`.

## `sh bin/studio shots export <phim> [--dir D]`

Mở trang phim (`index.html` của thư mục phim) lấy `SHOTS`, `DUR`; ghi `shots.json` (`source: "page"`), kiểm luật data-model.
- 0: đã ghi, in số shot và tổng độ dài.
- 1: trang không xuất `SHOTS` hoặc `SHOTS` sai luật (in dòng sai) hoặc lệch độ dài video > 1 khung; không ghi gì.
- 2: thiếu phim, thiếu video, sai tham số.

`record.mjs` ghi `out/shots.json` khi render; tầng 4 `sh bin/studio qc <phim>` (sau khi ghép tiếng ra `<tên>.mp4`) chép nó thành `shots.json` của phim khi độ dài khớp ≤ 1 khung, nếu không thì chạy bước export này. Nhờ vậy phim web mới tự có `shots.json`.

## `sh bin/studio notes show <phim> [--all] [--json] [--dir D]`

In các ghi chú còn mở (thêm `--all`: cả đã sửa), nhóm theo shot: số shot, mã shot, khoảng thời gian, mốc giây trong shot và thời điểm trong phim, nội dung, đường dẫn tuyệt đối của ảnh. Dòng cuối: `base: <sha256>`. `--json` in nguyên `{base, doc, shots}`.
- 0: có hoặc không có ghi chú (in "0 open notes").
- 2: thiếu phim.

## `sh bin/studio notes reply <phim> <note-id> "<trả lời>" [--done|--open] --base <sha256> [--dir D]`

Ghi `reply` vào ghi chú, `--done` tick đã sửa, `--open` bỏ tick; trạng thái shot tự suy lại.
- 0: đã ghi, in `base` mới.
- 4: `base` không khớp (nội dung đã đổi): chạy `notes show` lại.
- 1: không có ghi chú `note-id`. 2: sai tham số.

## `sh bin/studio film replace <phim> <video mới> [--shots <shots.json>] [--dir D]`

Kiểm video mới (ffprobe đọc được, có hình) và `shots.json` mới (nếu có; khớp độ dài video mới). Đổi `<tên>.mp4` → `<tên>.prev.mp4`, `shots.json` → `shots.prev.json` (bỏ bộ prev cũ), chuyển video mới vào bằng `os.replace`, ghi `shots.json` mới. Xoá đệm ảnh nhỏ cũ.
- 0: đã thay, in độ dài cũ/mới và số shot.
- 1: video mới không đọc được hoặc `shots.json` sai luật; không đổi gì.
- 2: sai tham số.
