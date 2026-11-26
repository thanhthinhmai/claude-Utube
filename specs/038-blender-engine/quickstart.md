# Quickstart: kiểm chứng 038

## Chuẩn bị
- Có Blender 4.2 trở lên trên Windows, và đã chạy `sh bin/studio blender config --exe 'E:\tools\blender-5.2.5-windows-x64\blender.exe' --work /mnt/e/claude-utube-ae/blender`.
- `sh bin/studio blender status` thoát mã 0, và dòng `gpu:` không phải software.
- AE đã cấu hình như specs/032 (`sh bin/studio ae status`).

## 1. Test tự động (không cần Blender thật)

```sh
sh tests/blender/run.sh
sh tests/ae/run.sh
sh tests/filmcheck/run.sh
sh tests/ui/run.sh
sh tests/run.sh
(cd desktop && node --test test/blenderbridge.test.js)
```

Kết quả mong đợi: tất cả đạt. Riêng `test_old_film_identical` xác nhận phim AE cũ cho bundle giống từng byte (SC-009).

## 2. GPU bắt buộc (SC-008)

Chạy `STUDIO_BLENDER_FAKE=1 FAKE_BLENDER_MODE=gpu_software sh bin/studio blender build film30 S2`. Mong đợi: thoát mã 3, có dòng `ERR gpu_software`, và không ra khung nào.

## 3. Phim trộn 30 s (US1, SC-001)

```sh
sh bin/studio ae plan film30 --suggest
sh bin/studio ae build film30
```

- Ước tính được in trước khi dựng.
- `out/build.mp4` có ít nhất 3 shot AE và 3 shot Blender.
- Mỗi shot dài đúng theo `timing.json`, lệch không quá 1 khung (kiểm bằng `ffprobe` và `build-shots.json`).
- Xem thử thật: chỗ chuyển giữa hai bộ máy không nhảy màu, không có khung đen.

## 4. Sửa một shot Blender (SC-002)

Sửa `films/film30/blender/S3.py`, rồi chạy `sh bin/studio ae fix film30 S3`.

Mong đợi:
- Chỉ S3 được dựng lại.
- Thời gian ≤ thời gian dựng S3 + 2 phút.
- Các khung ngoài S3 giống hệt bản trước (so md5 khung).

## 5. Chiều sâu (US2, SC-003, SC-004)

```sh
sh bin/studio qc depth film30
sh bin/studio ae render film30
```

- `qc depth` liệt kê các shot nông, kèm cách sửa.
- `ae render` từ chối khi còn shot bị chặn.
- Chạy `STUDIO_JOB=x sh bin/studio qc except film30 S5 depth_shallow --reason t`: mong đợi thoát mã 2.
- Sửa shot rồi chạy `qc depth` lại cho tới khi đạt.
- Bảng so sánh cỡ cảnh: lệch không quá 10 điểm phần trăm. Người dùng chấm ít nhất 8/10.

## 6. Nhân vật giống nhau ở hai bộ máy (US3, SC-006)

Chạy `sh bin/studio ae sheet film30`. Bảng mẫu có hình AE và hình Blender của từng nhân vật đặt cạnh nhau. Số in ra phải đạt ΔE ≤ 5 và tỉ lệ viền trong khoảng 0,8–1,25. Người dùng duyệt bằng mắt.

## 7. Cầu nối app (US5)

Chạy app (`sh bin/studio app start`) và chọn Blender ở trang Blender. Tạo một việc `fix` cho shot Blender. Mong đợi: khay báo "Blender: rendering S3", việc xong và video được thay.

## Kết quả

(ghi sau khi chạy)
