# Quickstart: kiểm chứng 039

## Bộ thử

- Video mẫu `charisma-ref` (đang ở `~/claude-Utube-037/references/charisma-ref`): liên kết hoặc chép vào `references/` của worktree 039, không vào git.
- Số đo tay: `~/claude-Utube-038/films/charisma-30/out/measure/deep_ref.json` (pan ở 960 px → ×2).
- Phim thử: `charisma-30-cam` = bản chép của `charisma-30` (15 shot: 10 AE + 5 Blender) trong `films/` của worktree, không vào git. Lệnh `ae …` nhận **tên** phim, không nhận đường dẫn.

## US1: học máy quay (SC-001)

```bash
sh bin/studio learn shots charisma-ref
sh bin/studio learn label charisma-ref
sh bin/studio learn craft-label charisma-ref
sh bin/studio learn camera charisma-ref
```

Ghép 15 shot theo thời điểm cắt của `deep.py` (CUTS). Kết quả mong đợi:
- |zoom_pct − (zoom_tay − 1)·100| ≤ 1 ở ≥ 13/15 shot;
- `transition: cut` ở 14/14 lần cắt;
- 15/15 shot có `evidence`;
- `parallax` false ở 15/15.

## US2: gợi ý (SC-002, SC-003)

```bash
time sh bin/studio camera suggest charisma-30-cam --set charisma-ref
time sh bin/studio camera stills charisma-30-cam
sh bin/studio camera show charisma-30-cam
```

Kết quả mong đợi:
- 15/15 shot có 2–3 phương án, mỗi phương án có `ref`, `reason`, `still`;
- phương án ★ trong p25–p75 ở ≥ 14/15 shot;
- 0 phương án có move ngoài static/push/pull/pan;
- tổng thời gian ≤ 10 phút.

Mở vài ảnh thử để xem khung zoom có nằm đúng chỗ không.

## US3: trang Camera (SC-004)

```bash
sh bin/studio app start
```

Trên trang Camera của phim thử (một bản chép chưa duyệt Camera; đã chạy bằng trình duyệt thật trên bộ máy chủ của bộ test
UI, xem `checks/sc004.md`):
1. Chọn phương án cho cả 15 shot (bấm liền tay, không chờ) rồi Approve: ≤ 5 phút, `options.json` có `choice.source: user`
   ở 15/15 shot, không có "conflict".
2. Ghim một ghi chú lên S5 rồi bấm "Send notes to Claude" (việc Claude, tốn lượt: hỏi chủ xưởng trước). Việc sửa chạy
   `camera suggest <phim> --shots S5 --keep-others` rồi `camera stills <phim> --shots S5`: băm options + ảnh của 14 shot
   còn lại không đổi.
3. Duyệt: `voice make` không còn bị chặn bởi điểm Camera.

## US4: kiểm máy quay (SC-005, SC-006)

Cần: Camera đã duyệt, có giọng (`voice make charisma-30-cam --provider kokoro`, miễn phí), jsx của shot gọi `CU.planCam`
(hoặc `CU.end` của phim chuyển sang `CU.planCam` khi shot có `shot_plan.<S>.camera`), script Blender gọi `k.cam()` không
truyền move/zoom.

```bash
sh bin/studio ae draft charisma-30-cam
sh bin/studio camera fit charisma-30-cam      # đo → fit_k cho shot lệch zoom → dựng lại các shot đó, tối đa 3 vòng
sh bin/studio qc camera charisma-30-cam
```

Kết quả mong đợi (`checks/sc005.md`):
- Ba shot cố ý (đúng, zoom tuyến tính, thị sai) cho ra đúng 2 báo cáo (`tests/filmcheck/test_camcheck.py`).
- Phim dùng máy chỉnh tay (không gọi `CU.planCam`) bị báo lệch.
- Sau `camera fit`: 14/15 shot khớp phương án (S8 còn `cam_ease`: hành động trong khung đánh lừa phép đo ease;
  `camera fit` chỉ sửa zoom). Shot không đổi theo `fit_k` được báo "tự đặt máy".

## Bộ test tự động

```bash
sh tests/run.sh && sh tests/learn/run.sh && sh tests/filmcheck/run.sh && sh tests/ae/run.sh && sh tests/ui/run.sh && sh tests/online/run.sh && sh tests/render/run.sh
```
