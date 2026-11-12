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

## Kết quả (2026-11-12, máy WSL2, GPU Intel UHD 730)

| SC | Kết quả | Số đo |
|---|---|---|
| SC-001 | **Đạt** | `plan-10`: đủ 10/10 lỗi, đúng mã cảnh, 0 lỗi nhầm, khoảng 1 s (`tests/filmcheck/test_plan.py`) |
| SC-002 | **Đạt một phần** (người dùng chấp nhận ngày 2026-11-13, không tái tạo lại) | Kế hoạch cuối của `pet-swap` cho 0 lỗi cắt (dùng dấu câu của công cụ nhận dạng thì có 36 lỗi cắt giả), nhưng vẫn có 70 lỗi khác: lặng 27%, 2 khoảng nghỉ trong dòng (`l38`, `l43`), 3 cảnh dài 6,04–6,23 s, 61 phụ đề cuối đoạn tắt sớm, 3 thẻ chữ hiện thiếu. Kế hoạch này chưa từng đạt `qc` (`checks.json` ghi `pass: false`). Tái tạo lần render đầu ra 68 lỗi cắt (spec cần ≥ 80; con số "≈ 85" của spec được đếm bằng `qc` cũ, có lỗi cắt giả); mọi cảnh chứa câu cuối < 2,5 s đều bị báo |
| FR-008 | **Đạt** | `qc plan pet-swap`: 3,5–5,0 s (192 cảnh, có `window.CARDS`) |
| SC-003 | **Đạt** | `shots-6`: đủ 6/6, 0 cảnh tốt bị báo nhầm. `pet-swap`: 209 ảnh trong 24–25 s bằng GPU. Một cảnh bị báo "quá tối" (`P01.2`: chữ "7:00" phát sáng vẽ thẳng lên canvas, cố ý) — dùng `qc except` được |
| SC-004 | **Đạt** (về kết luận) | `pet-swap` + Dusk Hypothetical: độ sáng 0,18 nằm ngoài 0,198–0,299, bão hoà 0,516 nằm ngoài 0,319–0,504. Số đo khác số trong spec (0,13 và 0,53): tầng 2 đo trên khung của trang, spec đo trên video đã ghép |
| SC-005 | **Đạt** | Phim thử đạt `qc plan`, rồi `qc` sau khi ghép tiếng có 0 lỗi nhịp (`test_sc005_…`) |
| SC-006 | **Đạt** | `pet-swap`, hai lần đọc lại trang từ đầu: lặng 0,271 cả hai lần, 261 câu giống hệt, cùng danh sách lỗi. Hai ca của US3 không có lỗi cắt giả |
| SC-007 | **Đạt** | `voice-pause`: báo `pause_in_line` 0,9 s ở `l17`; 70 dòng chạy dưới 1 s. Lỗi chỉ được tính khi file âm thanh có khoảng lặng thật (−40 dB, ≥ 0,3 s) trong chỗ hở |
| SC-008 | **Đạt một phần** | Thumbnail không còn phụ đề và thẻ chữ, dải letterbox vẫn giữ (xem bằng mắt trên `pet-swap`; test vùng dưới: YMAX < 60, so với 255 khi không ẩn). Gói đăng của `pet-swap` từ chối dùng phụ đề của phim vì 61 phụ đề cuối đoạn chưa đạt luật đã chốt, nên chưa tạo `subtitles.srt` mới. Phụ đề của phim có 0 dòng dưới 1 s |
| SC-009 | **Đạt** | `still-8`: dừng ngay khi đủ 6 s đứng yên, báo `S2`, giữ c0–c3; sửa rồi chạy lại thì log ghi `reused 4 chunks` |
| SC-010 | **Đạt** | `lib/lemo-opuscar`: `git status` sạch, đúng commit `bebbbe1` của `library.lock` |

Bộ test: `tests/run.sh` (87 ok) · `tests/render` (đạt) · `tests/learn` (43) · `tests/ui` (41 + 33 desktop) · `tests/filmcheck` (160) · `tests/online` (196, 2 bỏ qua) · `tests/license` (18): tất cả đạt.

Thay đổi ngoài git trên `films/pet-swap` (file của phim): `main.js` thêm `window.CARDS` và `window.CLEAN`. Bản cũ lưu ở scratchpad của phiên. Thư mục `publish/` đã được trả về như trước khi chạy.
