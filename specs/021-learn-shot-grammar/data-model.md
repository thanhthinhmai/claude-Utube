# Data model: 021

## ShotLabel (Nhãn cảnh)
Lưu ở `references/<set>/profile/<vid>/shots.json` cho video tham chiếu, và ở `films/<tên>/.check/labels.json` cho phim.

| Trường | Kiểu | Luật |
|---|---|---|
| `id` | chuỗi | video tham chiếu: `S001…`; phim: mã cảnh của `SHOTS` |
| `t0`, `t1`, `mid` | số (s) | `t1 - t0 ≥ 0.5`, trừ khi `short: true` |
| `frame` | đường dẫn | ảnh 960×540 ở giữa cảnh |
| `focus` | object | `{tiles: [12 số], focused_share: 0–1, sharpest: số, sharpest_at: [cột, hàng]}` (research R1) |
| `scale` | enum | `ecu` · `cu` · `med` · `wide` · `huge` · `insert` · `unknown` |
| `angle` | enum | `eye` · `low` · `high` · `top` · `ots` · `unknown` |
| `foreground_blur` | bool | |
| `confidence` | `high` · `low` | do lượt gán nhãn tự báo |
| `check` | bool | nhãn mâu thuẫn với số đo độ nét (research R3), cần người xem lại |
| `set` | chuỗi | video tham chiếu: `B<n>` do gom chữ ký màu (R4); phim: `set` của `SHOTS` |
| `evidence` | chuỗi | `<bảng ảnh>#<ô>`, ví dụ `v03_shots_2.jpg#17` |
| `short` | bool | cảnh dưới 0,5 s hoặc chớp sáng: không gán nhãn, đếm riêng |

`labels.json` của phim có thêm `fingerprint` (nguồn phim), `model` và `at`.

## ShotGrammar (Hồ sơ cách quay)
Thêm vào `profile/<vid>/video.json` dưới khoá `shot_grammar`, và vào `profile/summary.json` theo từng định dạng (trung vị và khoảng giữa các video):

```json
{"shots": 66, "labelled": 61, "inserts": 7, "short": 2, "unknown": 1,
 "scale_share": {"ecu": 0.21, "cu": 0.24, "med": 0.18, "wide": 0.17, "huge": 0.20},
 "angle_share": {"eye": 0.48, "low": 0.17, "high": 0.12, "top": 0.09, "ots": 0.14},
 "scale_change_share": 0.86, "longest_same_scale": 2,
 "focused_share_p50": 0.42, "subject_sharp_share": 0.97, "foreground_blur_share": 0.38,
 "sets": 5, "top_set_share": 0.31, "set_change_s_p50": 7.5}
```

Tỉ lệ cỡ cảnh và góc máy chỉ tính trên các cảnh có nhãn, không phải `insert`, `short` hay `unknown`. `subject_sharp_share` là tỉ lệ cảnh có ít nhất một ô nét.

## ShotGrammarRefs (số đo cách quay của phong cách)
`my-styles/<slug>/shots.json`; `stylerefs.load` đọc thành các khoá phẳng:

```json
{"source": "learned 2026-11-13, 10 videos", "focus_t": 40,
 "scale_share": {"huge": [0.12, 0.28], "ecu": [0.15, 0.30], "cu": [0.15, 0.32], "med": [0.10, 0.25], "wide": [0.10, 0.25]},
 "angle_share": {"eye": [0.35, 0.60], "low": [0.08, 0.25], "high": [0.05, 0.20], "top": [0.03, 0.15], "ots": [0.05, 0.20]},
 "scale_change_share": [0.75, 0.95], "longest_same_scale_max": 3,
 "focused_share_p50": [0.25, 0.60], "top_set_share_max": 0.40}
```

(Các số trên chỉ để minh hoạ; số thật lấy từ lượt học lại.)

## AgreementReport (SC-001)
`references/<set>/profile/agreement.json`: `{n: 40, scale_same: 0–1, scale_within_one: 0–1, angle_same: 0–1, disagreements: [{id, a, b}]}`. Thứ tự bậc dùng cho "lệch một bậc": ecu < cu < med < wide < huge.

## Demo (Phim mẫu)
`my-styles/<slug>/`:
- `DEMO.md`;
- `demo/` (mã nguồn, `build.sh`, `CREDITS`);
- `test.jpg` (vào git);
- `test.mp4` (ngoài git, dựng lại được);
- `demo-checks.json`: kết quả tầng 1–4 của phim mẫu, chép từ `checks.json`.
