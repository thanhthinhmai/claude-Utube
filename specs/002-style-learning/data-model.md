# Data Model: Học phong cách từ video tham chiếu

Mọi thứ dưới `references/<set>/` nằm trên máy, không vào git. `<set>` là slug do người dùng đặt hoặc tự sinh (`[a-z0-9-]`, 3–40 ký tự).

## ReferenceSet (`references/<set>/set.json`)

| Trường | Kiểu | Ràng buộc |
|---|---|---|
| `set` | string | slug, trùng tên thư mục |
| `source` | object | `{kind: "channel"\|"videos"\|"files", inputs: [string]}` |
| `max_seconds` | number | mặc định 180, 30–1800 |
| `deny` | [string] | tên cấm thêm bởi người dùng |
| `videos` | [Video] | ≥ 1 |
| `created` | ISO date | |

## Video (phần tử của `set.json.videos`)

| Trường | Kiểu | Ràng buộc |
|---|---|---|
| `id` | string | `v01`, `v02`… theo thứ tự nhận |
| `file` | string | đường dẫn tương đối trong `references/<set>/videos/` |
| `origin` | string | URL hoặc `"local"`; chỉ dùng nội bộ, không bao giờ vào `my-styles/` |
| `title`, `channel` | string \| null | từ info JSON; chỉ để `check-names` |
| `audio_language` | string | mã ngôn ngữ hoặc `"unknown"` |
| `width`, `height`, `fps`, `duration` | number | từ ffprobe |
| `orientation` | enum | `landscape` · `portrait` · `square` |
| `segments` | [[a, b]] | phần được đo (giây); tổng ≤ `max_seconds` |
| `state` | enum | `fetched` → `measured` → `transcribed`; hoặc `skipped` kèm `skip_reason` |
| `source_sig` | string | `size:mtime` của file, để biết có cần đo lại không (FR-011) |

## FrameMetrics (`profile/<id>/frames.csv`)

Một dòng mỗi khung đã đo:

| Cột | Ý nghĩa |
|---|---|
| `i`, `t` | số thứ tự khung, thời điểm (giây, theo video gốc) |
| `dx`, `dy` | dịch chuyển so với khung trước (px ở rộng 320) |
| `motion` | `hypot(dx,dy)/320` |
| `motion_ok` | 0/1, độ tin cậy đỉnh ≥ 0,05 |
| `hist_d` | khoảng cách histogram với khung trước (0–1) |
| `cut`, `flash` | 0/1 |
| `luma`, `contrast`, `sat` | 0–1 |
| `dark`, `bright` | tỷ lệ 0–1 |

## VideoProfile (`profile/<id>/video.json`)

- `frames_expected`, `frames_measured` (SC-001)
- `cuts: [t]`, `flashes: [t]`, `soft_transitions: [[a,b]]`, `shot_len: {median, min, max}`
- `still_ratio` (khung đứng yên ÷ khung có `motion_ok`), `motion_720: {p50, p90, max}` (px/khung ở 720p)
- `luma`, `contrast`, `sat`, `dark`, `bright`: mỗi cái `{p2, p50, p98}`
- `palette: [{hex, lab, share}]`: 6 cụm lớn nhất; ít hơn chỉ khi sau khi gộp (ΔE76 < 5) còn ít hơn 6 cụm, kèm `palette_note`
- `audio: {lufs, lra, silence_total, silence_count, first_voice_t}`
- `speech: {words, rate, unit: "words/s"|"chars/s", pause_total} | null`
- `sheets: [file]`

## SetSummary (`profile/summary.json`)

- `by_orientation: {<orientation>: {videos: n, metrics: {<metric>: {median, min, max}}}}`
- `majority_orientation`
- `dispersion_warnings: [metric]`: chỉ số có (max − min) > 3 × độ lệch tuyệt đối trung vị, gợi ý bộ không đồng nhất (Edge case)
- `skipped: [{id, reason}]`
- `low_count_warning: bool` (< 5 video đã đo)

## AspectReport (`analysis/{visual,motion-depth,sound-script}.md`)

Mỗi kết luận: `Claim` · `Evidence` (số trong `summary.json`/`video.json`, hoặc `sheets/<file>#<ô>`) · `Confidence` (high/medium/low).

## Correction (`analysis/corrections.md`)

`before` · `after` · `evidence` · `found_by` (số đo / nhìn bảng ảnh).

## StyleDraft (`references/<set>/style/`)

`STYLE.md`, `style.json`, `EVIDENCE.md`. Trạng thái:

```
draft → approved_1 (duyệt lần 1) → proven (compare đạt hoặc người dùng chấp nhận) → approved_2 → saved
```

Bị từ chối ở bất kỳ bước duyệt nào thì quay về `draft` với góp ý.

## ProofComparison (`proof/compare.json`)

| Trường | Ngưỡng (SC-004) |
|---|---|
| `luma_diff` | ≤ 0,05 |
| `sat_median_diff` | ≤ 0,08 |
| `dark_diff_pp` | ≤ 5 |
| `palette_matched` | ≥ 4 trên 6 (ΔE76 < 15) |
| `pass` | cả bốn đều đạt |
| `round` | 1–3 (tối đa 2 vòng sửa sau vòng đầu) |

## SavedStyle (`my-styles/<slug>/`)

Theo research.md §13. Ràng buộc:
- `slug` không trùng `lib/lemo-opuscar/styles/*` hay `my-styles/*`.
- `check-names` đạt.
- Không có file media hay bản chép lời.
- Được thêm một dòng vào bảng trong `my-styles/README.md`: `| slug | Tên | based_on | learned (n video) | YYYY-MM-DD |`.
