# Data Model: 039

Đơn vị: zoom theo phần trăm (`zoom_pct` 6.0 nghĩa là thang đo cuối 1,06); px quy về khung 1920×1080; vị trí bố cục là phần trăm khung (0–100); thời gian bằng giây.

## Reference shot (shot mẫu): `references/<set>/profile/<vid>/camera.json` → `shots[]`

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `id` | str | `vid:Sxxx`, từ `shots.json` (R3) |
| `t0`, `t1`, `dur` | float | |
| `size` | enum ecu/cu/med/wide/huge/insert | từ nhãn `scale` của `learn label` |
| `cam_height`, `lens` | enum | từ nhãn 038 (null khi chưa có) |
| `card`, `people`, `action`, `outdoor`, `prop` | bool/int | từ craft-label |
| `subject` | [x0,y0,x1,y1] % hoặc null | craft-label bản 2 (R2) |
| `subject_x`, `subject_y`, `subject_h`, `headroom` | float % hoặc null | suy từ `subject` |
| `move` | enum static/push/pull/pan/other | |
| `zoom_pct` | float | dấu âm là zoom ra |
| `rate_pct_s` | float | |
| `ease` | [q¼, q½, q¾] | tiến độ 0–1; null khi đứng |
| `drift_px` | [x, y] | |
| `parallax_px`, `parallax` | float, bool | R1 |
| `transition` | enum cut/fade/dip/streak/flash/wipe/dissolve | vào shot; shot đầu là null |
| `reliable` | bool | false khi dur < 1 s, chớp sáng, hoặc < 6 khối trong mô hình |
| `why_unreliable` | str hoặc null | |
| `evidence` | [jpg a, jpg b] hoặc null | chỉ trong thư viện của phong cách (R3) |

Tệp: `{version: 1, video, measured_at, measure: "camtrack/1", shots: [...], skipped: [{id, reason}]}`.

## Camera summary (bảng tổng): `my-styles/<style>/camera.json`

```json
{"version": 1, "source_set": "dusk-hypothetical-3", "measure": "camtrack/1",
 "transition_main": "cut", "transition_share": {"cut": 0.97, "fade": 0.03},
 "parallax_share": 0.0,
 "by_size": {"med": {"n": 41, "dur": [2.1, 3.0, 4.2], "zoom_pct": [3.1, 5.6, 8.0], "push_share": 0.83,
                      "pull_share": 0.05, "static_share": 0.12, "drift_px": [4, 8, 12], "ease_q": [0.13, 0.48, 0.85],
                      "subject_h": [38, 52, 66], "headroom": [6, 10, 15]}},
 "shots": [ /* Reference shot rows, có `evidence` cho ≤ 150 shot */ ]}
```
Các bộ ba là [p25, p50, p75]. Cỡ cảnh có `n < 5` được đánh dấu `"thin": true`: gợi ý vẫn dùng, nhưng khoảng p25–p75 chỉ để cảnh báo.

## Camera option (phương án): `films/<f>/camera/options.json`

```json
{"version": 1, "style": "dusk-hypothetical", "source": "style|set:<set>", "made_at": "…",
 "shots": {"S3": {"dur": 2.8, "options": [
   {"n": 1, "recommended": true, "size": "med", "engine": "ae",
    "start": {"scale": 1.12, "cx": 46, "cy": 44}, "move": "push", "zoom_pct": 5.6, "rate_pct_s": 2.0,
    "ease": [0.13, 0.48, 0.85], "ease_ae": [62, 70], "drift_px": [0, 8], "transition": "cut",
    "cam_height": "eye", "lens": "normal",
    "ref": "v03:S041", "ref_frames": ["camera/v03-S041-a.jpg", "camera/v03-S041-b.jpg"],
    "score": 0.86, "why": {"size": 1, "people": 1, "action": 1, "outdoor": 1, "prop": 0, "dur": 0.7},
    "reason": "giống v03:S041 (trung cảnh, 1 người, hành động); zoom 5,6 % trong p25–p75 của trung cảnh",
    "note": null, "still": "camera/stills/S3-o1.jpg"}],
   "choice": {"n": 1, "recommended": 1, "source": "auto|user|note", "by": "owner", "at": "…"}}}}
```

Luật:
- 1 ≤ len(options) ≤ 3; n = 1, 2, 3; đúng một `recommended`.
- Hai phương án khác nhau ở ít nhất một trong: size, move, |Δzoom| ≥ 1, |Δcx| hoặc |Δcy| ≥ 10.
- `parallax_share < 0.05` ⇒ `move ∈ {static, push, pull, pan}`.
- `note` bắt buộc khi zoom_pct, dur hoặc drift nằm ngoài p25–p75, hoặc khi `transition ≠ transition_main`.
- `ref` null ⇒ `reason` có "không có shot mẫu giống" kèm điểm cao nhất đã thử.
- Phương án "của người làm phim" (lấy từ `shot_plan.camera` có trước): `n` tiếp theo, `ref: "film"`.

Trạng thái `choice`: không có → `auto` (khi điểm Camera tắt hoặc agent chọn ở giai đoạn thử) → `user` hoặc `note`. Đổi `choice` sau khi đã duyệt thì điểm Camera thành "Must run again" (dấu vân tay đổi).

## Shot plan (film.json `shot_plan.<S>`), các trường mới

| Trường | Kiểu |
|---|---|
| `card`, `action`, `outdoor`, `prop` | bool, tuỳ chọn (R4) |
| `camera` | object, chép từ phương án đã chọn: `size, start{scale,cx,cy}, move, zoom_pct, rate_pct_s, ease, ease_ae, drift_px, transition, ref, option` |

`film.py` kiểm: các enum như trên; `0.5 ≤ start.scale ≤ 4`; `|zoom_pct| ≤ 40`; mỗi phần tử ease nằm trong [0,1] và tăng dần. Cờ `by_user_request: true` (đặt khi sửa theo ghi chú người dùng đòi chuyển động ngoài video mẫu) cho phép move khác static/push/pull/pan; `qc camera` không báo shot có cờ này. `camera apply` (nằm trong `camera choose`) là nơi duy nhất ghi khối này. `shot_plan.move` được đặt bằng `camera.move` để depthcheck và 038 đọc như cũ.

## Camera note: `films/<f>/camera/notes.json` (sổ pins.py)

Nhóm `shots`, mỗi ghim: `{id, shot, option, x, y, text, base, state: open|sent|done, lot, failed_lot}`.

## Tier `camera` (qc camera)

Theo shot: `{shot, measured: {zoom_pct, ease, drift_px, parallax, transition}, planned: {...}, rules: [cam_zoom|cam_dir|cam_ease|cam_parallax|cam_transition], fix}`. Miễn theo shot trong tiers (lý do, người miễn).
