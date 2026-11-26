# Contract: lệnh

Tất cả qua `sh bin/studio`. Mã thoát chung (như 034): 0 đạt · 1 kiểm chưa đạt hoặc bị chặn · 2 sai tham số hoặc tệp hỏng · 3 thiếu điều kiện (chưa duyệt giọng, AE chưa sẵn sàng) · 4 nội dung đã đổi (`--base` lệch). `--dir <thư mục phim>` như các lệnh `notes`. `--json` in kết quả máy đọc được.

## Bản nháp

| Lệnh | Hành vi |
|---|---|
| `ae draft <phim> [--shots S2,S6]` | Dựng bản nháp ¼ độ phân giải qua AE (trên máy hoặc cầu nối). Không `--shots`: cả phim. Có `--shots`: chỉ các shot đó, ghép theo shot vào `animatic/draft.mp4` (R7). Ghi `draft.json`, `clips/`, `frames/`, `keys.json`; giữ một `draft.prev.mp4`. Mã 3 khi giọng chưa duyệt (điểm voice bật) hoặc AE chưa sẵn sàng. In `… S2 (1/2)` khi chạy, dòng cuối `draft: <giây> s · silence <x>%`. |
| `ae build|render <phim>` | (sửa) đọc `timing.json` qua `CU.shotFrames`; `render` bị chặn (mã 3) khi điểm animatic bật mà chưa duyệt, kèm lệnh duyệt. Mọi lần dựng ghi `keys_<proj>.json`. |

## Animatic

| Lệnh | Hành vi |
|---|---|
| `animatic status <phim> [--json]` | Dải thời gian (`shots[{id,t0,t1,lines[]}]`, `lines[{id,at,end,shot}]`), `silence`, `limit`, `duration`, bản nháp hiện hành hay cũ, đề xuất (`fit`), ghi chú mở. |
| `animatic fit <phim> [--json]` | Chỉ danh sách đề xuất (data-model "Đề xuất"). |
| `animatic accept <phim> <S2[,S6…]\|--all> [--base <sha>]` | Nhận đề xuất: ghi `timing.json` + `narration.json` (R2), một mục lịch sử cho cả lần nhận. In silence mới. |
| `animatic skip <phim> <S2> [--base <sha>]` | Bỏ đề xuất (ghi `skipped_for`). |
| `animatic undo <phim> [--base <sha>]` | Trả lại trạng thái trước lần nhận gần nhất; mã 1 khi đã về `origin`. |
| `animatic notes <phim> add <S2> [--at 1.2 --x 40 --y 30] --text "…"` · `delete <S2> <note>` · `show` · `reply <note> --text "…"` | Sổ ghi chú (R9). |
| `animatic start <phim>` | Ghi `origin` của `timing.json` (gọi khi bước Animatic bắt đầu; lặp lại không đổi gì). |

## Điểm duyệt

| Lệnh | Hành vi |
|---|---|
| `point approve <phim> animatic [--anyway] --source ui\|chat` | Duyệt. Khi silence > 20% mà không có `--anyway`: mã 1, lý do "silence 25% > 20%: approve anyway?". `--anyway` ghi `anyway: true, silence`. JOB.md cấm agent dùng `--anyway`. |
| `point on|off <phim> animatic` | Như specs/026. |
