# Data model: 020

Mọi dữ liệu là file JSON trong thư mục phim. Không có cơ sở dữ liệu mới.

## Shot (Cảnh)
Lấy từ `window.SHOTS` của trang phim, được ghi vào `.check/plan-input.json`.

| Trường | Kiểu | Luật |
|---|---|---|
| `id` | chuỗi | duy nhất trong phim (ví dụ `P27.2`). Thiếu thì gán `S<thứ tự>` và cảnh báo |
| `t0`, `t1` | số (s) | `0 ≤ t0 < t1 ≤ DUR`; các cảnh nối liền, không chồng nhau (lệch tối đa 1/fps) |
| `set` | chuỗi | tuỳ phim, chỉ để hiển thị |
| `para` | chuỗi \| null | đoạn của câu đầu tiên trong cảnh (tính ra, không đọc từ trang) |

## Sentence (Câu)
Tính bởi `rhythm.sentences()` từ `lines.json` (lời) và `voices/words.json` (mốc). Không lưu riêng; nằm trong `tiers.plan.measures.sentences` để xem lại.

| Trường | Kiểu | Luật |
|---|---|---|
| `para` | chuỗi | đoạn của dòng |
| `line` | chuỗi | mã dòng (`l01`) |
| `n` | số nguyên | thứ tự trong dòng, đếm từ 0 |
| `start`, `end` | số (s, theo phim) | `at + mốc từ`, mỗi mốc từ đã kẹp vào `[0, dur dòng]` |
| `text` | chuỗi | câu của kịch bản (30 ký tự đầu) |

## Cue (Phụ đề) và Card (Thẻ chữ)
- Cue: `[t0, t1, text]`, lấy từ `window.CUES`, nếu không có thì `cues.json`, rồi `<phim>.srt`.
- Card: `[t0, t1, id, text]`, lấy từ `window.CARDS`, nếu không có thì từ `readcheck`.

## Issue (Lỗi)
```json
{"tier": "plan", "ref": "P27.2", "at": 312.48, "rule": "cut_in_sentence", "severity": "block",
 "measure": 0.12, "limit": 0.4, "text": "\"The neighbours start…\"",
 "fix": "move the cut to ≥ 314.06 s", "excepted": null}
```
- `tier`: một trong `voice` · `plan` · `shots` · `render` · `final`.
- `ref`: mã cảnh, mã dòng (`l07`) hoặc mã phụ đề (`cue 41`).
- `rule`: tên luật, lấy từ bảng luật trong [contracts/checks.md](contracts/checks.md).
- `severity`: `block` (chặn render) hoặc `warn` (chỉ cảnh báo, như lệch phong cách).
- `excepted`: `{reason, at}` khi cảnh có ngoại lệ cho luật đó. Lỗi đã có ngoại lệ không tính vào `pass`.

## Tier result (Kết quả tầng)
Nằm trong `checks.json → tiers.<tầng>`.

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `pass` | bool | không còn lỗi `block` nào chưa có ngoại lệ |
| `fingerprint` | chuỗi 16 hex | nguồn phim lúc kiểm (R7). Tầng `voice`: chỉ tính `lines.json` và `voices/` |
| `at` | ISO 8601 | |
| `issues` | Issue[] | |
| `measures` | object | số đo của tầng (ví dụ `silence_ratio`, `luma_p50`) |
| `skipped` | chuỗi[] | phần đã bỏ qua, kèm lý do (ví dụ `"style: no measurements"`) |
| `seconds` | số | thời gian chạy |

Riêng `tiers.shots` có thêm `style_accept: {reason, at} | null`. Riêng `tiers.render` có thêm `skipped_checks: {reason, at} | null`, `stopped: {chunk, shot, at, rule} | null`, `reused_chunks`.

**Chuyển trạng thái**:
- Nguồn đổi: dấu vân tay khác, nên cổng coi tầng `plan` và `shots` là "chưa kiểm".
- `qc except`: tính lại `pass` của tầng `plan` và `shots` từ `issues` đã lưu. Dấu vân tay không đổi, vì file ngoại lệ không nằm trong phần tính vân tay.

## Exception (Ngoại lệ)
`films/<tên>/qc-exceptions.json`: `[{"shot": "P31.0", "rule": "flat", "reason": "title card on purpose", "at": "…"}]`.
- `shot` phải có trong `SHOTS`.
- `rule` phải thuộc danh sách luật cho phép ngoại lệ (R10).
- `reason` không được rỗng, tối đa 200 ký tự.

## Style references (Số đo phong cách)
Tính bởi `stylerefs.load(slug)`. Mọi khoá đều không bắt buộc:

```json
{"luma_p50": [0.198, 0.299], "saturation_p50": [0.319, 0.504], "cuts_per_min": [16, 26],
 "loudness_range": [2.4, 3.3], "shot_max": 6.0, "still_max": 6.0,
 "subtitle_zone": [0.82, 1.0], "dark_p50": 0.04, "blown_share": 0.25, "source": "EVIDENCE.md"}
```

## Stop marker (Dấu dừng render)
`out/.chunks/STOPPED.json`: `{fingerprint, chunk_size, fps, size, first_bad, shot, rule, at, shots_hash}`. File bị xoá khi một lần ghi chạy hết mà đạt.
