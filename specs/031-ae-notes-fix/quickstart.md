# Quickstart: kiểm chứng spec 031

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

## US4 – bộ cài
1. Đẩy nhánh `031-desktop-ae` (hoặc chạy tay `desktop.yml`) → smoke `ae` qua trên Windows và macOS. **Tốn phút chạy: hỏi người dùng trước.**
2. Cài bộ cài trên máy Windows có AE và trên máy Mac có AE (người dùng cung cấp) → chạy lại US3 bước 1–3 (SC-009).

## US5 – phim AE mới
1. New film → bộ máy "After Effects", ý tưởng 30 giây → duyệt kịch bản, bảng shot → video; `shots.json` khớp video ≤ 1 khung; `films/<tên>/ae/` không có tệp của `tools/ae/kit/`.

## Test tự động
`sh tests/run.sh`, `sh tests/render/run.sh`, `sh tests/learn/run.sh`, `sh tests/ui/run.sh` (gồm `node --test desktop/test/*.test.js`), `sh tests/filmcheck/run.sh`, `sh tests/ae/run.sh` (mới).
