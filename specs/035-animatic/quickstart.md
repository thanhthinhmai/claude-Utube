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
