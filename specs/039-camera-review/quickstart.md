# Quickstart: kiểm chứng 039

## Bộ thử

- Video mẫu `charisma-ref` (đang ở `~/claude-Utube-037/references/charisma-ref`): liên kết hoặc chép vào `references/` của worktree 039, không vào git.
- Số đo tay: `~/claude-Utube-038/films/charisma-30/out/measure/deep_ref.json` (pan ở 960 px → ×2).
- Phim thử: `charisma-30` (15 shot), liên kết vào `films/`.

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
time sh bin/studio camera suggest charisma-30 --set charisma-ref
time sh bin/studio camera stills charisma-30
sh bin/studio camera show charisma-30
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

Trên trang Camera của phim thử:
1. Đổi phương án của S3 rồi kiểm `options.json` (`choice.source: user`).
2. Ghim một ghi chú lên S5 rồi bấm "Send notes to Claude". Việc sửa chỉ làm lại S5: băm các shot còn lại không đổi.
3. Duyệt: `voice make` không còn bị chặn bởi điểm Camera.

## US4: kiểm máy quay (SC-005, SC-006)

```bash
sh bin/studio ae draft charisma-30
sh bin/studio qc camera charisma-30
```

Kết quả mong đợi:
- 0 shot lệch với bản dựng theo phương án.
- Ba shot cố ý sai (zoom tuyến tính, thị sai, đúng) cho ra đúng 2 báo cáo.

## Bộ test tự động

```bash
sh tests/run.sh && sh tests/learn/run.sh && sh tests/filmcheck/run.sh && sh tests/ae/run.sh && sh tests/ui/run.sh && sh tests/online/run.sh
```
