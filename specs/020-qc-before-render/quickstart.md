# Quickstart: kiểm chứng 020

## Chuẩn bị
- `sh bin/studio status` báo đã sẵn sàng; `sh bin/studio deps voice` đã cài.
- Đã tải mô hình `small.en` (`sh bin/studio app models`, hoặc tự tải khi chạy lần đầu).
- Đã có `films/pet-swap` (192 cảnh, ngoài git) và phim thử `tests/filmcheck/fixtures/tiers/` (do tasks tạo):
  - `plan-10`: 10 lỗi nhịp cài sẵn;
  - `shots-6`: 6 cảnh có lỗi hình, cộng 30 cảnh tốt;
  - `voice-pause`: một khoảng nghỉ 0,9 s bên trong một dòng;
  - `asr-comma`: công cụ nhận dạng viết dấu phẩy chỗ kịch bản có dấu chấm, và có mốc âm;
  - `still-8`: có một cảnh đứng yên 8 s.

## Test tự động
```sh
sh tests/filmcheck/run.sh     # rhythm, plan, shots (đo bằng số đo giả), cổng, ngoại lệ, gói đăng
sh tests/render/run.sh        # chunkcheck, dừng sớm, dùng lại đoạn, --no-stop, --skip-checks
sh tests/run.sh && sh tests/learn/run.sh && sh tests/ui/run.sh   # không có gì hỏng ở chỗ khác
git diff --stat main -- lib/  # SC-010: phải trống
```

## Kịch bản chạy thật

| # | Lệnh | Kết quả mong đợi | SC |
|---|---|---|---|
| 1 | `qc plan` trên `plan-10` | báo đủ 10 lỗi, đúng mã cảnh, 0 lỗi nhầm, ≤ 10 s; `render` sau đó: mã 1, chưa mở trình duyệt | SC-001 |
| 2 | sửa `plan-10` rồi chạy lại `qc plan` và `render --until 2` | đạt; render chạy | US1 |
| 3 | `qc plan pet-swap` (kế hoạch cuối) | 0 lỗi nhịp; ghi thời gian chạy (mục tiêu ≤ 10 s) | SC-002, FR-008 |
| 4 | `qc plan` trên `pet-swap` với quy tắc cắt của lần render đầu (test tái tạo các mốc cắt: −0,06 s trước câu, cảnh đầu đoạn bắt đầu giữa khoảng nghỉ) | ≥ 80 lỗi `cut_*`, và mọi cảnh chứa câu cuối < 2,5 s đều bị báo | SC-002 |
| 5 | `qc shots` trên `shots-6` | đủ 6 lỗi, ≤ 1 cảnh tốt bị báo nhầm, có `sheet-1.jpg` ghi mã cảnh | SC-003 |
| 6 | `qc shots pet-swap` (GPU) | ≤ 3 phút; `style_luma` 0,13 ngoài 0,198–0,299, `style_saturation` 0,53 ngoài 0,319–0,504 | SC-003, SC-004 |
| 7 | `render pet-swap` khi còn cảnh báo phong cách | mã 1; `qc accept-style … --reason "…"` xong thì cổng đạt | FR-013 |
| 8 | `qc voice` trên `voice-pause` (70 dòng) | báo `pause_in_line` 0,9 s đúng mã dòng, ≤ 30 s | SC-007 |
| 9 | `qc plan` hai lần trên `asr-comma` | ranh giới câu sau "seven", 0 lỗi cắt giả; `silence_ratio` và mốc câu giống hệt nhau giữa hai lần | SC-006 |
| 10 | `render` trên `still-8` | dừng trong vòng 1 đoạn sau đoạn lỗi, báo mã cảnh, giữ các đoạn trước; sửa rồi chạy lại: log ghi `reused N chunks` | SC-009 |
| 11 | phim qua tầng 1–3, mux, rồi `qc` | 0 lỗi nhịp | SC-005 |
| 12 | (sau khi thêm `CLEAN` vào trang: `qc plan pet-swap` lại) `publish pet-swap` | `subtitles.srt` giống phụ đề của phim từng dòng, 0 dòng dưới 1 s; 3 thumbnail có sai khác trung bình < 2/255 ở vùng phụ đề so với khung đã ẩn hết chữ | SC-008 |

Phải mở bằng mắt ít nhất một bảng ảnh (`.check/shots/sheet-1.jpg`) và một thumbnail (hiến pháp IV).
