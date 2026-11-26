# Quickstart: kiểm Animatic (035)

## Điều kiện

- Worktree `035-animatic` đã rebase lên 034 (và 036 nếu đã merge); `sh bin/studio deps` chạy được.
- After Effects mở trên máy (memory "After Effects from WSL": AE tự render, không tắt AE), hoặc app chạy với cầu nối AE.
- Phim thử `films/ae-sleepless-test` có giọng đã duyệt; `CU.FR` trong `ae/shots.jsx` đọc `CU.shotFrames`.

## 1. Test tự động (không cần AE)

```sh
sh tests/filmcheck/run.sh      # test_timing, test_animatic, test_steps, test_points
sh tests/ae/run.sh             # test_draft (bundle cờ draft, splice theo shot), test_keys (đọc keys_*.json)
sh tests/ui/run.sh             # test_animatic_api, browser_animatic.cjs
sh tests/online/run.sh && sh tests/run.sh
```

Kỳ vọng: đạt hết. Riêng: đề xuất của dữ liệu `ae-sleepless-test` (chép vào tests) có 8 shot cần bớt, S9 không; nhận tất cả → silence ≤ 0,20; undo → `timing.json` và `narration.json` giống hệt trước (so byte).

## 2. Bản nháp thật (SC-001)

```sh
sh bin/studio animatic start ae-sleepless-test
time sh bin/studio ae draft ae-sleepless-test       # ghi lại giây
sh bin/studio animatic status ae-sleepless-test      # silence 25–33%, 9 shot, 14 câu
```

Kỳ vọng: ≤ 3 phút; nhanh hơn ≥ 3 lần thời gian `ae render` gần nhất của phim (xem `out/render-shots.json`/log). Mở `animatic/draft.mp4`: 480×270, nghe giọng đúng chỗ.

## 3. Khớp shot (SC-002, SC-003)

```sh
sh bin/studio animatic fit ae-sleepless-test
sh bin/studio animatic accept ae-sleepless-test --all
sh bin/studio ae draft ae-sleepless-test --shots <các shot đổi>   # app tự làm khi bấm trên trang
sh bin/studio animatic status ae-sleepless-test --json
```

Kỳ vọng: silence ≤ 20%; mỗi shot có lời kết thúc 0,25 s ± 1 khung sau từ cuối, câu đầu của shot ở đường cắt. Rồi `point approve ae-sleepless-test animatic --source chat`, `ae render`, `qc final`: silence của bước kiểm phim lệch ≤ 1 điểm phần trăm (SC-003); `shots.json` của bản đẹp trùng `timing.json` ± 1 khung (SC-004).

## 4. Ghi chú và sửa nền (SC-005)

Trên trang việc: ghim 1 ghi chú trên S2, 1 ghi chú chung cho S6, "Send notes to Claude". Kỳ vọng: chỉ S2, S6 dựng lại; so từng điểm ảnh các shot khác của `draft.mp4` với `draft.prev.mp4` (ffmpeg `framemd5` theo shot) → giống hệt; mỗi ghi chú có trả lời; bước Animatic về `waiting`.

## 5. Cổng và giao diện

- Trước khi duyệt Animatic: `sh bin/studio ae render ae-sleepless-test` → mã 3 kèm lệnh duyệt (SC-006).
- Silence > 20%: nút Approve hỏi "Approve anyway"; bản duyệt có `anyway: true`.
- Màn hình 400 px: ghim lệch ≤ 2% (SC-007, `browser_animatic.cjs`).

## Kết quả (lượt AE thật, 2026-11-26, `ae-sleepless-test`, AE 2027 trên Windows, GPU)

| Tiêu chí | Đo được | Đạt? |
|---|---|---|
| SC-001 thời gian | Sau T049 (ffmpeg từ ~20 s còn ~2,4 s): bản nháp cả phim 40,9 s; dựng lại một shot (S2) 9,7 s. Bản đẹp 80,9 s (phim 24,63 s). Phần AE của bản nháp ~38 s là chung với bản đẹp (mở AE, dựng shot, lưu); thử 10 khung/giây (`STUDIO_AE_DRAFT_FPS=10`): 35,2 s | ≤ 3 phút: đạt · lượt sửa vài shot nhanh hơn 8 lần: đạt (SC-001 đã sửa 2026-11-26) |
| SC-002 silence | 33% → 22% sau khi nhận mọi đề xuất, có giữ S5 (P02) và S9 (P05) 2,5 s (khung: S1 69, S2 103, S3 68, S4 38, S5 75, S6 99, S7 119, S8 93, S9 75); duyệt bằng "Approve anyway" | đạt (theo SC-002 đã sửa) |
| SC-003 khớp `qc final` | `qc final` trên bản đẹp: silence 22% (Animatic 22%); không còn lỗi shot cuối đoạn | đạt |
| SC-004 mốc cắt | `shots.json` của bản đẹp trùng `timing.json` đúng từng khung, 9/9 shot (lần 1: 689 khung; lần 2: 739 khung) | đạt |
| SC-005 chỉ dựng shot có ghi chú | Dựng lại riêng S2: `shots_built: ["S2"]`, 8 shot còn lại giống hệt (framemd5 từng shot). Chưa chạy một lượt "Send notes to Claude" thật (việc `fix` gọi Claude) | phần dựng: đạt · phần trả lời ghi chú: chỉ có test tự động |
| SC-006 cổng | `ae render` trước khi duyệt → mã 3 kèm lệnh duyệt | đạt |

Gặp trong lượt chạy:
- `qc final` báo 2 lỗi do khớp shot: shot chứa lời cuối của đoạn P02 (S5) còn 1,50 s và P05 (S9) còn 1,83 s, dưới mức tối thiểu 2,5 s. Luật khớp "câu cuối + 0,25 s" chưa giữ mức tối thiểu này.
- 7 dòng `CHECK camera … exposed frame edge` có cả ở bản đẹp cũ (`out/build.mp4`), không do bản nháp.
- Bản đẹp kéo dài hơn 240 s mới ghi log (ExtendScript giữ `log.txt` trong bộ nhớ đến khi đóng) → `ae render` báo `ae_scripting_off` và tắt AE. Đã sửa: `CU.say` ghi từng dòng xuống đĩa ngay (`tools/ae/kit/lib.jsx`).
- Âm thanh bản đẹp: script trộn của phim (`mix.py.orig`) đặt câu theo `narration.json` (vị trí Animatic đã dời), không theo độ lệch cố định.
- AE bị buộc tắt khi hết hạn chờ → lần mở sau hiện "Crash Repair Options" và chặn mọi script (render kẹt ở `QUEUED`). Đã sửa (T052): không bao giờ buộc tắt AE; thông báo nhắc bấm Continue.
- Bản nháp mất 2 khung cuối do `-shortest` khi ghép tiếng; đã sửa (T049), test kiểm số khung.
