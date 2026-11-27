# CLI contract: 039

Mã thoát: 0 đạt · 1 kiểm chưa đạt / lỗi dựng · 2 đầu vào sai (thiếu thư viện, phim không phải AE, giá trị sai) · 3 thiếu bộ máy, không có GPU hoặc mất cầu nối.

## `sh bin/studio learn camera <set> [--videos v01,v02] [--force]`

- Cần `learn shots` và video còn trên máy. Video đã xoá thì thoát mã 2 và in `run: learn refetch <set>`.
- Với mỗi video, ghi `profile/<vid>/camera.json` (data-model "Reference shot"). Nhãn cỡ cảnh, craft-label và depth chưa có thì để null và in lệnh cần chạy, không tự gọi Claude.
- In mỗi video một dòng: `v01: 15 shots, 0 skipped, parallax 0/15, cut 14/14`.
- Chạy lại khi `shots.json` không đổi và không có `--force` thì bỏ qua các video đã đo.

## `sh bin/studio learn craft-label <set>` (đổi)

- Schema bản 2 thêm `subject`. Cache của bản 1 không còn hợp lệ nên được gán nhãn lại.

## `sh bin/studio learn save <set> <style>` (đổi)

- Có `profile/*/camera.json` thì ghi thêm `my-styles/<style>/camera.json` và `my-styles/<style>/camera/*.jpg` (≤ 150 shot, rộng 360 px). Các phần khác của phong cách không đổi.

## `sh bin/studio camera suggest <film> [--style S | --set SET] [--shots S3,S5] [--keep-others] [--json]`

- Chỉ chạy cho phim AE có `shot_plan`. Phim trang web thì mã 2.
- Nguồn: `--set`, rồi `--style`, rồi phong cách của phim. Không có `camera.json` thì mã 2 kèm lệnh cần chạy.
- Ghi `films/<f>/camera/options.json`:
  - `--shots` chỉ làm lại các shot đó.
  - `--keep-others` giữ nguyên từng byte phần của các shot khác.
  - Lựa chọn cũ (`choice`) được giữ nếu phương án cùng mã vẫn còn, nếu không thì về `auto`.
- In theo shot: `S3  1* med push 5.6% ease .13/.48/.85 drift 0,8  ← v03:S041 (0.86)`.

## `sh bin/studio camera stills <film> [--shots …]`

- Vẽ `camera/stills/S#-o<n>.jpg` cho mọi phương án (R8). Không cần giọng.
- Thiếu AE hoặc Blender thì mã 3. Dựng bằng phần mềm thì dừng và hỏi (mã 3).

## `sh bin/studio camera choose <film> S3 <n> [--by owner|claude] [--source user|note|auto]`

- Ghi `choice` và chép phương án vào `shot_plan.S3.camera` (+ `move`).
- `--by claude` chỉ được dùng khi điểm Camera tắt hoặc khi sửa theo ghi chú.

## `sh bin/studio camera retime <film>`

- Tính lại `zoom_pct`, `drift_px` theo `rate_pct_s` và thời lượng mới (R6).
- In `S3 2.8s→3.4s zoom 5.6→6.8%`. Không đổi dấu vân tay của điểm Camera.

## `sh bin/studio camera show <film> [--json]`

- In bảng phương án, lựa chọn, ghi chú mở và trạng thái điểm Camera.

## `sh bin/studio camera note <film> add S3 <n> <x> <y> "<text>" | remove <id> | list`

- Sổ ghi chú pins.py (R10).

## `sh bin/studio qc camera <film> [--except S3 "<lý do>"]`

- Tier `camera` (R12). Mã 1 khi còn shot lệch chưa được miễn.
- Lệnh miễn bị từ chối (mã 2) khi chạy trong việc của app (`STUDIO_JOB` có giá trị).

## Đổi ở lệnh có sẵn

- `voice make`: thêm `points.gate(…, "camera")` sau gate cast.
- `animatic accept` và `voice make`: có `camera/options.json` thì chạy `camera retime` sau khi `timing.json` đổi.
- `ae draft --still`: khung 1 ở ¼ cho các phương án, bỏ kiểm giọng.
- `points` / `review`: thêm điểm `camera` (bật mặc định cho phim AE, tắt được theo kênh hoặc theo phim).

## Op chỉnh sửa (`sh bin/studio edit <film> <op>`, dùng từ app)

| op | point | args |
|---|---|---|
| `camera_choose` | camera | `{shot, n}` |
| `camera_note_add` | camera | `{shot, n, x, y, text}` |
| `camera_note_remove` | camera | `{id}` |
