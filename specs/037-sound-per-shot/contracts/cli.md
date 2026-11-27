# Contract: lệnh

Tất cả qua `sh bin/studio`. Mã thoát như 034/035: 0 đạt · 1 chưa đạt/bị chặn · 2 sai tham số · 3 thiếu điều kiện (chưa có kho, chưa duyệt animatic, thiếu `deps sound`) · 4 nội dung đã đổi (`--base`). `--json` cho kết quả máy đọc được.

## Kho tiếng

| Lệnh | Hành vi |
|---|---|
| `sound lib add <thư mục>` | Thêm thư mục Sonniss vào `roots.json` (từ chối thư mục dưới `references/`), rồi lập mục lục. |
| `sound lib index [--full]` | Lập lại mục lục; mặc định chỉ tệp mới/đổi. In `indexed N new · M changed · K gone · B broken · <giây> s`. |
| `sound lib status` | Thư mục, số mục theo nguồn, tệp hỏng, có khoá Freesound không (không in khoá). |
| `sound lib search "<query>" [--cat GLASS] [--dur 1.5] [--scope all\|cc0]` | 8 kết quả: id, tên, loại, độ dài, nguồn. |
| `sound key freesound` | Đọc khoá từ stdin, thử một lần gọi, lưu (CLI: vào `.env`; app: Settings). |

## Tiếng của phim

| Lệnh | Hành vi |
|---|---|
| `sound cue add <phim> <shot> --action "…" --query "…" [--cat C] (--motion "Layer · Prop" [--edge start\|end] \| --line l07 [--word w] \| --at 0.35 \| --span) [--offset-f n] [--len s] [--gain db] [--cut hard\|fade\|over [--fade s]]` | Thêm cue `by: claude` (agent) hoặc `user` (`--by user`); tìm tiếng ngay (kho → Freesound nếu thiếu, theo phạm vi). |
| `sound cue set <phim> <cue> [--entry id] [--offset-f n] [--gain db] [--cut …] [--len s] [--base sha]` | Sửa một cue; đánh `by: user` khi nguồn là trang hoặc `--by user`. |
| `sound cue rm <phim> <cue> [--base sha]` | Xoá. |
| `sound silence add <phim> <shot> (--line l05 [--word w] \| --at x) --len s [--db -57]` | Khoảnh khắc lặng. |
| `sound shot on\|off <phim> <shot>… [--base sha]` | Bật/tắt tiếng động của shot (FR-005a). `cue add` vào shot đang tắt: mã 5. |
| `sound plan <phim> [--json]` | In danh sách theo shot, `at` đã resolve, dropped/missing kèm lý do. |
| `sound mix <phim>` | Resolve + chép cache + trộn `out/mix.wav` + stems + khối CREDITS; ghép lại tiếng vào bản đẹp nếu đã có (không dựng hình). In `cues P placed · D dropped · M missing · [O off · ]<giây> s`. Mã 3 khi animatic bật mà chưa duyệt. |
| `sound notes add <phim> <shot> --text "…"` · `delete <phim> <shot> <note>` · `show <phim> [--json]` · `reply <phim> <note> --text "…" [--done\|--open]` (mỗi lệnh có `--base`, `--dir`) | Ghi chú Sound (`tools/filmcheck/soundnotes.py`, chưa dùng `pins.py` của 035). Base lệch → mã thoát 4; lỗi khác → 2. |

## Học tiếng

| Lệnh | Hành vi |
|---|---|
| `learn sfx <set> [--only v01]` | R8 cho từng video còn trên máy → `profile/<v>/sfx.json`, rồi tổng hợp vào phong cách nếu set đã lưu thành phong cách. Mã 3 khi thiếu `deps sound` hoặc thiếu `words.json`. In `✓ v01: 23 events · 11 agree · 2 silences`. |
| `learn sfx --file <wav> --words <words.json\|segs.json> [--shots <json>]` | Chế độ tệp rời (đo SC-003), in JSON, không ghi phong cách. |
| `deps sound` | Cài tầng `requirements-sound.txt` vào `tools/.venv`. |

## Cổng

| Lệnh | Hành vi |
|---|---|
| `ae render <phim>` | (sửa) thêm `points.gate(d, "mix")` cho phim AE khi điểm mix bật (FR-028). |
