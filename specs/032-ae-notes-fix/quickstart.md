# Quickstart: kiểm chứng spec 032

## US1 – bộ dựng chung (máy phát triển, dòng lệnh)
1. `sh bin/studio config ae --afterfx "/mnt/c/Program Files/Adobe/Adobe After Effects 2027/Support Files/AfterFX.exe" --aerender ".../aerender.exe" --work /mnt/e/claude-utube-ae/work`
2. Chuyển `ae-crayon-test` sang `film.json` + `ae/` (tệp riêng của phim).
3. `sh bin/studio ae fix ae-crayon-test S13` → ≤ 60 s; so với video hiện có: 4128 khung, 0 khung dưới 30 dB ở các shot khác, shot 13 trùng bản dựng bằng bộ code cũ.
   - **Kết quả 2026-11-24** (AE 2027, WSL): `ae build ae-crayon-test --shots S13` 32 s + ghép 11 s = 43 s; 4128 khung, 0 khung dưới 30 dB ngoài shot 13 (thấp nhất 39,1 dB), shot 13 trùng bản cũ (thấp nhất 41,9 dB, trung bình 43,6 dB).
4. Đổi tên tạm `AfterFX.exe` trong cấu hình → `ae build` báo thiếu AE trong ≤ 10 s, mã 3.

## US2 – cầu nối (Windows, rồi macOS)
1. Mở app desktop (bản dev: `env -u ELECTRON_RUN_AS_NODE npx electron .`); khay → "After Effects…": thấy đường dẫn AE tìm được, bấm "Test" chạy được.
2. `sh bin/studio ae status` → `bridge: ready · After Effects 2027`.
3. Gửi 2 yêu cầu cùng lúc (2 lần `ae build … --shots S1`): yêu cầu 2 "waiting for AE" rồi chạy sau.
4. Tắt app desktop giữa lúc dựng → yêu cầu `failed: bridge_lost` trong ≤ 60 s.

## US3 – Fix with Claude
1. Ghi 3 ghi chú ở 3 shot của `ae-crayon-test`; bấm "Fix with Claude".
2. Trang việc: danh sách 3 ghi chú, các shot dựng lại (chỉ shot bị ảnh hưởng), token đã dùng.
3. Xong: trang phim tự nạp video mới; 3 ghi chú có trả lời; "Watch the previous version" phát bản cũ.
   - **Kết quả 2026-11-24** (T027, app từ nhánh 032 + cầu nối chạy từ WSL `desktop/test/wsl-bridge.mjs` + AE 2027 thật): việc `j-20261124-030227-9444` với 3 ghi chú S6 (chữ CLAUDE bị đầu che), S23 (chân co lơ lửng), S27 (chữ đè nét não). Xong trong 3 phút: một lượt dựng AE cho đúng 3 shot (S6, S23, S27), ghép 4128 khung, video thay (giữ bản trước), 3 ghi chú tick kèm trả lời, `ae/` chép về kho; 19 lượt gọi, 742 665 token (phần lớn là cache). Nhìn khung trước/sau: cả 3 lỗi đã sửa.
   - Lỗi tìm ra khi chạy thật (đã sửa): worker tính việc làm phim bằng chat còn "running" là việc của người đó nên không nhận việc mới; `ae` trong việc tìm nhầm phim của dự án; tắt AE trước khi gửi script làm AE dừng ở hộp thoại khởi động lần sau (giờ chỉ tắt trước `aerender`); AE khởi động nguội ~90 s nên chờ script 240 s.

## US4 – bộ cài
1. Đẩy nhánh `032-desktop-ae` (hoặc chạy tay `desktop.yml`) → smoke `ae` qua trên Windows và macOS. **Tốn phút chạy: hỏi người dùng trước.**
   - **Kết quả 2026-11-24** (T030, run 45329859196, chạy tay trên nhánh 032-ae-notes-fix): smoke có `ae bridge ok` và `ae build ok` đạt trên Windows và macOS. Lần đầu bước cài im lặng của 017 trên Windows hết 3 phút chờ (chập chờn, không liên quan 032); chạy lại job Windows: đạt.
2. Cài bộ cài trên máy Windows có AE và trên máy Mac có AE (người dùng cung cấp) → chạy lại US3 bước 1–3 (SC-009).

## US5 – phim AE mới
1. New film → bộ máy "After Effects", ý tưởng 30 giây → duyệt kịch bản, bảng shot → video; `shots.json` khớp video ≤ 1 khung; `films/<tên>/ae/` không có tệp của `tools/ae/kit/`.

## Test tự động
`sh tests/run.sh`, `sh tests/render/run.sh`, `sh tests/learn/run.sh`, `sh tests/ui/run.sh` (gồm `node --test desktop/test/*.test.js`), `sh tests/filmcheck/run.sh`, `sh tests/ae/run.sh` (mới).
