# Quickstart: kiểm chứng ghi chú từng shot

## Chuẩn bị

- App đang chạy: `sh bin/studio app status` → `running`, đăng nhập chủ xưởng ở `http://127.0.0.1:8790`.
- Phim `ae-crayon-test` có trong kho của app (video 137,6 s, 40 shot); phim web `pet-swap` có trong kho.

## 1. Mốc shot (US1)

1. Phim AE: ghép lại bản tổng của dự án AE (comp MASTER) để có `shots.json`, rồi
   `sh bin/studio film replace ae-crayon-test films/ae-crayon-test/out/shot1-40_tieng-goc_720p.mp4 --shots <shots.json>`.
   Kỳ vọng: mã 0, 40 shot; `ffprobe` độ dài video lệch `shots[-1][1]` ≤ 1/30 s.
2. Phim web cũ: `sh bin/studio shots export pet-swap` → mã 0, có `shots.json`; không có tệp mới trong `out/.chunks/` (không dựng lại).
3. Mở `#/films/ae-crayon-test`: thanh thời gian 40 ô; danh sách 40 dòng có ảnh (lần đầu ≤ 15 s, mở lại ≤ 3 s).
4. Chọn shot 37, bấm "Play this shot": dừng ở 2:02.1 ± 0,2 s (đọc `currentTime` trong console), 10 shot khác nhau đều đạt.
5. Xoá tạm `shots.json` của một phim thử: phần Shots báo "Phim này chưa có mốc shot" kèm lệnh tạo.

## 2. Ghi chú (US2)

1. Shot 37: gõ "tay người ngồi bị bàn che", bật ghim giây, thêm. Tải lại trang: ghi chú còn, shot 37 "Needs fix", ô 37 màu cam, bộ lọc Needs fix có 37.
2. Chụp màn hình có khoanh đỏ, bấm vào ô ghi chú, Ctrl+V: ảnh nhỏ hiện; thêm ghi chú; tải lại: ảnh còn, bấm mở to được.
3. Dán tệp 12 MB hoặc tệp PDF: bị từ chối kèm thông báo, chữ đang gõ còn nguyên.
4. Tick mọi ghi chú của shot 37: shot chuyển "Fixed"; bỏ tick một cái: về "Needs fix".
5. Mở hai tab, thêm ghi chú khác nhau ở hai tab: cả hai ghi chú còn sau khi tải lại.

## 3. Vòng sửa với Claude (US3)

1. Bấm Copy ở "Fix with Claude", dán vào chat: Claude chạy `sh bin/studio notes show ae-crayon-test`, liệt kê đúng các ghi chú mở.
2. Sau khi Claude sửa, dựng lại và chạy `film replace`: trang phim phát video mới; "Xem bản trước" ở shot 37 phát bản cũ; ghi chú đã sửa có tick và dòng trả lời; ghi chú chưa sửa còn mở kèm lý do.
3. Trang việc của một phim đã có video: có đường dẫn "Ghi chú shot" mở trang phim.

## Test tự động

```sh
sh tests/ui/run.sh          # gồm test_shot_notes.py, test_typecheck.py
sh tests/filmcheck/run.sh   # gồm test_shots_export.py
sh tests/run.sh; sh tests/render/run.sh; sh tests/learn/run.sh
```
