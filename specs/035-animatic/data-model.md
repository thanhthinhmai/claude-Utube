# Data Model: Điểm duyệt Animatic (035)

## Thời lượng shot — `films/<phim>/timing.json`

| Trường | Kiểu | Luật |
|---|---|---|
| `version` | 1 | |
| `fps` | số | bằng `film.json → fps` |
| `frames` | `{shot id: int}` | đủ mọi shot của `film.json → shots`; mỗi giá trị ≥ 6 khung (0,2 s ở 30 fps) |
| `history` | `[{frames, narration_at, at, by, why}]` | trạng thái **trước** mỗi lần nhận; tối đa 50; phần tử cuối là lần nhận gần nhất (Undo lấy ra) |
| `origin` | `{frames, at}` | thời lượng lúc bước Animatic bắt đầu (FR-015: Undo không lùi quá) |

Dẫn xuất: `t0(shot)` = tổng khung các shot trước / fps; `t1 = t0 + frames/fps`.

Chuyển trạng thái: `accept(shot)` → đẩy `{frames, narration_at}` vào `history`, đổi `frames[shot]`, dời `narration.json → lines[].at` (R2). `undo` → lấy phần tử cuối, ghi lại cả hai tệp. Ghi nguyên tử dưới một khoá chung `timing.lock`.

## Câu thoại có mốc (dẫn xuất)

`{id, at, end, last_word_end, shot}`: `at` từ `narration.json`, `end = at + dur.json[id]`, `last_word_end` từ `words.json` (nếu có), `shot` = shot chứa phần lớn [at, end] (R2).

## Đề xuất khớp shot — `animatic/fit.json`

| Trường | Kiểu | Luật |
|---|---|---|
| `shot` | id | shot có ít nhất một câu |
| `delta_s` | số | âm = bớt, dương = thêm; |delta| > 1 khung |
| `end_new` | số | giây trong shot = từ cuối − `head` + 0,25 s, làm tròn khung |
| `head` | số | giây từ đường cắt tới câu đầu, bị bỏ khi nhận (0 với shot đầu phim) |
| `very_short` | bool | shot mới < 1 s |
| `motions` | `[{layer, prop, t0, t1, effect: drop\|squeeze\|clip, ratio?}]` | từ `animatic/keys.json` (R5) |
| `state` | `new\|accepted\|skipped` | |
| `skipped_for` | băm | băm (frames[shot] + mốc câu của shot) lúc bỏ; khác băm hiện tại → trở về `new` |

Tệp chỉ giữ trạng thái `skipped`; đề xuất `new` được tính lại mỗi lần đọc.

## Bản nháp — `animatic/`

| Tệp | Nội dung |
|---|---|
| `draft.mp4` | cả phim, 480×270, giọng tạm (R8) |
| `draft.prev.mp4` | đúng một bản trước (so trước/sau) |
| `draft.json` | `{frames, narration_sha, code_sha, built_at, shots_built: [id], seconds, fps, size, checks, segments: {shot: frames}}`; bản nháp "hiện hành" khi `frames`, `narration_sha` và `code_sha` (băm `ae/*.jsx` + `cast/cast.json`) trùng hiện tại |
| `shots/S2.mp4` | đoạn 480×270 của từng shot, mã hoá một lần; bản nháp = các đoạn nối liền (copy), nên shot không dựng lại giữ đúng khung (`segments` ghi độ dài lúc dựng; khác `timing.json` thì dựng lại) |
| `clips/S2.mp4` | clip từng shot (có tiếng) |
| `frames/S2.jpg` | khung đại diện 50% shot, ≤ 60 KB |
| `keys.json` | `{shot: [{layer, prop, t0, t1}]}` từ lần dựng gần nhất của shot đó |
| `notes.json` | sổ ghi chú (dưới) |

## Ghi chú shot nháp — `animatic/notes.json`

Cùng mẫu `pins.py` (tách từ `cast-notes.json`, 034): `{version: 1, shots: {S2: {notes: [note]}}, lot?, last_lot?, failed_lot?}`, note = `{id, kind: "note", frame: "clip"|null, x, y, at, text, done, by, created, updated, reply}`. `x, y` ∈ [0, 100]; `at` ∈ [0, độ dài shot]; `frame: null` = ghi chú chung (có thể có `at`). Mở = `done: false`. Mọi lần ghi kèm `base` (sha256 16 ký tự của tệp). Lô `lot = {job, notes: [id], since}` gom mọi ghi chú mở lúc bấm "Send notes to Claude"; ghi chú thêm khi lô đang chạy không vào lô, chờ lô sau; lô hỏng → `failed_lot = {job, error, at}`, ghi chú vẫn mở (FR-022).

## Điểm duyệt `animatic` — `checks.json → reviews`

Như specs/026: `on/off`, `approved.animatic = {fingerprint, at, by, source, review_id, anyway?: bool, silence?: số}`. `anyway` chỉ đặt được khi `silence > 0,20` và `source` là `ui` hoặc lệnh người dùng có `--anyway`.

Trạng thái điểm: `not_reached` (giọng chưa duyệt) → `waiting` (bản nháp hiện hành, chờ duyệt) → `approved` → `stale` (vân tay đổi, R11).

## Bước "Animatic" (thanh bước)

Chỉ phim AE. Trạng thái cơ sở: `todo` (chưa có bản nháp hiện hành) · `done` (có) · `stale` (bản nháp cũ hơn `timing.json`/`narration.json`/mã phim). Với phim AE, các bước Look, Picture, Shots ẩn; bước Mix hiện tên "Sound", Render hiện "Final render" (như bản mẫu). 034 **chưa** đổi hai tên này; 035 đổi (T008, T023). Tên điểm duyệt vẫn là `mix`, chỉ tên hiện trên giao diện là "Sound".
