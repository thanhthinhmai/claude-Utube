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

### Mục 3–4, ngày 2026-11-27, phim thử `films/ae-mix-038` (T028)

Phim thử: 6 shot AE (S1–S5, S9), 3 shot Blender chưa có nhân vật (S6 hành lang, S7 và S8 lớp học), 30 khung/giây.

**Mục 3 (`ae build`): đạt.**
- Ước tính in trước khi dựng: Blender 311 khung ≈ 10 phút, AE 6 shot ≈ 6 phút.
- Dựng thật mất khoảng 9 phút (23:56 → 00:05). GPU là Intel UHD 730 OPENGL, ghi trong `build-shots.json`.
- `out/build.mp4` có 739 khung, 1920×1080, dài 24,63 s.
- Clip Blender khớp số khung: S6 99, S7 119, S8 93.
- Xem tờ khung: chỗ chuyển giữa AE và Blender không có khung đen, không nhảy màu.

**Tốc độ Blender.** Đo một khung 1080p của shot S7:

| Cài đặt | Giây/khung |
|---|---|
| 48 mẫu | 10,1 |
| 16 mẫu | 3,6 |
| 8 mẫu, 1 tia bóng, bản đồ bóng ½, persistent data, PNG không nén (mặc định mới) | 1,6 |

So hai bản cạnh nhau thì hình như nhau.

**Mục 4 (`ae fix ae-mix-038 S8`): đạt một phần.**
- Bản dựng trộn được dùng làm video của phim, vì phim thử chưa render.
- Chỉ S8 được dựng lại, mất 2 phút 24 giây, nằm trong giới hạn S8 + 2 phút.
- Khung ngoài S8 **không trùng md5**: `splice` mã hoá lại cả video (libx264 crf 21, có từ 031).
  - PSNR so với bản trước: thấp nhất 44,7 dB, trung bình 47,2 dB.
  - Mắt không thấy khác, nhưng SC-002 ghi "giống hệt (md5)". Người dùng chọn (2026-11-27): ghép không mã hoá lại.
  - Đã làm: `ae render` đặt khung khoá ở đầu mỗi shot (closed GOP, tắt scenecut); `splice` cắt video cũ tại các khung
    khoá đó và chép nguyên, chỉ mã hoá shot dựng lại, rồi nối và chép tiếng. Video cũ không có khung khoá thì mã hoá
    lại một lần (có khung khoá), lần sửa sau chép nguyên.
  - Đo lại trên ae-mix-038 (`ae fix S8` hai lần): 739/739 khung trùng framemd5; mọi shot khác S8 trùng từng khung.
    Phần ghép mất < 1 s.
- Phát hiện thêm:
  - `k.fg` đặt vật tiền cảnh theo khung đầu.
  - Khi máy vòng (S8), cuối shot cây đến quá gần và che gần nửa khung.
  - Cần đặt theo cả đường máy chạy, giới hạn phần khung bị che.

