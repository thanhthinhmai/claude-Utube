# Data model: 023

## Trong bộ tham chiếu (`references/<set>/`, ngoài git)

### `set.json` → mỗi video: thêm `url`

`url` (chuỗi) được ghi khi `learn fetch` hoặc `learn refetch`. `refetch` ghép URL với `vNN` theo độ dài (lệch ≤ 1 s) và 5 khung giữa cảnh (ΔE trung bình ≤ 12), xem research R1.

### `profile/<v>/craft.json` (mới, `learn craft`)

```json
{"video": "v01", "fps_sample": 12, "noise": 0.011,
 "shots": [{"id": "S001", "t0": 0.0, "t1": 1.267,
   "cam": {"type": "still|drift-h|drift-v|push|pull|follow", "px_s": 3.1, "zoom_pct_s": 0.0, "ease_in_s": null, "ease_out_s": null},
   "inner": {"active_share": 0.42, "peak": 0.08, "spans": [[0.31, 0.71, 0.06, [0.62, 0.48]]], "rise_s": [0.38]},
   "trans_in": {"type": "cut|streak|dip|fade|wipe|flash|dissolve", "dur": 0.0},
   "person": true}]}
```

- `active_share`: phần thời gian của cảnh có cử động bên trong (sau khi bù máy).
- `spans`: `[t0, t1, độ lớn, tâm (x, y) theo tỉ lệ khung]`.
- `person`: lấy từ nhãn của 021 (cảnh không phải `insert`, có người theo bằng chứng). Nếu không biết thì `null`.

### `profile/<v>/strips/Sxxx.jpg` (mới)

Dải 8 khung đều nhau của một cảnh, mỗi khung rộng 320 px. Khoảng 80 cảnh mẫu trên cả bộ. Trích dẫn dạng `vNN/strips/Sxxx.jpg#k` (k = 0–7).

### `profile/<v>/evidence/*.jpg` (mới)

Khung lẻ 640 px được trích dẫn trong `TEMPLATE.md` dạng `vNN/evidence/<tên>.jpg`.

### `profile/<v>/sound.json` (mới, `learn sound`)

```json
{"video": "v01",
 "speech": {"wpm_10s": [[0, 158], [10, 171]], "pause_in": [0.12, 0.18], "pause_sent": [0.32, 0.45], "pause_para": [0.7, 1.2], "pre_number": [0.28, 0.41]},
 "music": {"windows": [[0, 5, true, -14.2]], "tempo": 92, "tempo_conf": "low|ok"},
 "sfx": {"onsets": [1.42, 3.9], "per_min": 11.5}}
```

Mỗi phần tử của `music.windows` là `[t0, t1, có nhạc, mức nhạc so với giọng (dB)]`. `pause_*` và `pre_number` là danh sách độ dài nghỉ (s); bản tổng hợp lấy p25, p50, p75.

### `profile/beats.json` (mới, Claude ghi; `learn beats --check` kiểm)

```json
[{"video": "v01", "beats": [["hook", 0, 34.5], ["explain", 34.5, 120.0], …, ["end-card", 620.1, 637.3]]}]
```

Luật:
- tên nhịp nằm trong 9 nhịp của `STRUCTURE.md` (hook, explain, benefit, scale, cost, crisis, ending, sting, end-card);
- các nhịp liền nhau, phủ từ 0 tới hết video;
- nhịp vắng mặt thì bỏ hẳn, không ghi độ dài 0.

### `profile/craft-summary.json` (mới)

Gom số của cả bộ:
- theo cỡ cảnh: máy, cử động, ô nét, độ sâu;
- theo nhịp: độ dài cảnh, chuỗi cỡ cảnh hay gặp, tỉ lệ máy động, tỉ lệ cảnh có cử động, chuyển cảnh, từ/phút, nhạc, tiếng động/phút;
- toàn bộ: `still_ratio`, `motion720_p50`, tỉ lệ từng loại chuyển cảnh.

Đây là nguồn số cho `template.json`.

### `pairs/<đợt>/<thành phần>.jpg|.mp4` (mới, `learn pairs`)

Bảng so; không vào git, không gửi đi (FR-009).

## Trong phong cách (`my-styles/<slug>/`, vào git)

### `TEMPLATE.md`

Xem contracts/template-format.md. Gồm 15 mục thành phần và 9 công thức nhịp.

### `template.json`

Các khoảng số mà máy đọc được. Mỗi số kèm nguồn.

```json
{"version": 1, "set": "dusk-hypothetical-3",
 "motion": {"still_ratio": [0.24, 0.84], "motion720_p50": [0.008, 0.176],
            "still_person_min_s": 2.0, "dead_share_max": 0.055, "person_still_cam_active": [0.25, 1.0], "person_still_cam_none": 0.108,
            "cam_by_scale": {"wide": {"moving": 0.27, "px_s": [8, 40]}, "close": {"moving": 0.08, "px_s": [4, 16]}},
            "rise_s": [0.3, 0.6]},
 "transitions": {"cut": 0.96, "streak": 0.02, "dip": 0.01, "fade": 0.01, "streak_s": [0.12, 0.18], "fade_max_per_film": 2},
 "framing": {"by_scale": {"close": {"off_centre": 0.71, "focused_share": [0.08, 0.25]}}},
 "voice": {"wpm": [150, 175], "pause_in": [0.10, 0.20], "pause_sent": [0.28, 0.50], "pause_para": [0.6, 1.2], "pre_number": [0.25, 0.45]},
 "sound": {"sfx_per_min": [6, 18], "music_under_voice_db": [-18, -10]},
 "beats": {"hook": {"shot_s": [1.2, 2.6], "cam_moving": 0.2, "music": "on", "tempo": [85, 100]}},
 "source": {"motion": "craft-summary.json → motion", "motion.dead_share_max": "craft-notes: highest film 0.055"}}
```

Các số trong mẫu trên chỉ minh hoạ; số thật lấy từ `craft-summary.json`.

Luật: số nào cũng có nguồn trong `source`, hoặc là số gốc của `summary.json`. `qc` và bộ dựng chỉ đọc tệp này, không đọc `TEMPLATE.md`.

### `STYLE.md`: nhãn từng luật

Mỗi luật (dòng bảng hoặc gạch đầu dòng ở các mục 1–11) mang một trong hai nhãn:
- `[bằng chứng: <bảng#ô | tệp→khoá | báo cáo §n.m>]`
- `[xưởng]`

Luật bị bỏ được ghi vào `EVIDENCE.md` → "Nhật ký sửa" (ngày, luật, lý do).

### `kit/REVIEW.md` (mới)

Sổ duyệt của 4 đợt (FR-010).

| Đợt | Thành phần | Lần | Ngày | Quyết định | Ghi chú của người dùng |
|---|---|---|---|---|---|
| 1 | mặt | 1 | 2026-11-… | sửa | "mắt to quá" |
| 1 | mặt | 2 | … | duyệt | |

Luật:
- Đợt N+1 chỉ bắt đầu khi mọi thành phần của đợt N có dòng "duyệt".
- Một thành phần sửa tới lần 3 mà chưa duyệt thì dừng và hỏi (Edge Cases).

## Bảng cảnh của bộ dựng v2: trường thêm (contracts/kit-api-v2.md)

| Trường | Ở đâu | Kiểu | Luật |
|---|---|---|---|
| `act` | mỗi người trong `cast` | `[[giây trong cảnh, động tác], …]` | động tác trong `catalog.acts`; thời điểm nằm trong cảnh |
| `path` | mỗi người | `[[giây, x, z], …]` | chỉ cho tư thế `walk` |
| `talk` | mỗi người | `[[t0, t1], …]` | miệng mấp máy; mặc định theo bong bóng của người đó |
| `swap` | mỗi người | `{hoodie, hair, hat, glasses}` | cần act `swap` |
| `light` | cảnh | `-1`, `0`, `1` | bên của đèn chính; mặc định theo hạt giống |
| `move` | cảnh | `{type, speed?}` hoặc `"auto"` | `type` trong `catalog.moves`; `auto` chọn theo `template.json` |
| `trans` | cảnh | `cut\|streak\|dip\|fade` | `fade` ≤ 2 lần mỗi phim |
| `frame` | cảnh | `{x, y}` hoặc `"auto"` | vị trí chủ thể theo tỉ lệ khung; `auto` theo phân bố ô của cỡ cảnh |
| `icon` | gfx `stat` | tên | trong `catalog.icons` |

Trang phim xuất thêm `window.CAST = [[t0, t1, id, số người]]` cho tầng 2, và đọc `window.SUBJECT` (công cụ đặt: không vẽ đám đông khi chụp khung cho `still_person`).

## Phim (`films/<tên>/`, ngoài git)

- `lines.json`: thêm trường tuỳ chọn `say` (chữ gửi cho bộ tạo giọng). `text` vẫn là chữ của kịch bản.
- `voices/.say.json`: tệp do `voice make` sinh ra, không sửa tay.
- `.check/shots/motion/<id>-<k>.jpg`: 4 khung mỗi cảnh cho luật `still_person`.
- `compare/`: bảng so ba cột (cũ | mới | mẫu) và `before-after.json`. Bảng có khung mẫu nên chỉ để xem trong máy.
