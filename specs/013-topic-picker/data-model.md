# Data Model: Chọn đề bằng số liệu YouTube (013)

## Topic (`channels/<slug>/topics.json` → `{"topics": [Topic…]}`)

| Trường | Kiểu | Luật |
|---|---|---|
| `n` | số nguyên | lớn nhất + 1 trong tệp; không dùng lại |
| `text` | chuỗi | 3–120 ký tự |
| `source` | `user` \| `suggested` | |
| `type` | `explainer` \| `comparison` \| `list` \| `true story` \| `q&a` \| `other` | người dùng sửa được |
| `status` | `queued` \| `dropped` \| `blocked_reference` \| `in_progress` \| `made` \| `unscored` | `unscored` khi hết hạn mức hay lỗi |
| `scores` | `{demand, heat, competition, overlap, fit}` | mỗi mục là số nguyên 0–10; riêng `fit` có thể là `null` |
| `fit_by` | `claude` \| `user` \| null | |
| `fit_reason` | chuỗi | ≤ 160 ký tự |
| `total` | số nguyên | tổng 5 mục (`fit` là `null` thì tính là 0) |
| `verdict` | `PRIORITY` \| `GO` \| `HOLD` \| `DROP` | theo FR-003 và R2 |
| `evidence` | Evidence | |
| `raw` | Raw | số liệu thô để chấm lại |
| `scored_at` | thời điểm ISO | quá 14 ngày thì là "cũ" |
| `film` | chuỗi hoặc null | phim gắn khi `in_progress` hoặc `made` |
| `taken_at` | thời điểm ISO hoặc null | |
| `note` | chuỗi hoặc null | lý do bị chặn, bị bỏ qua, hay chưa chấm |

**Evidence**: `top_video {id, title, channel, views, age_days, url}`, `counts {y365, n30, n60, channels90, weight90, outliers}`, `closest_film {name, similarity}` hoặc null, `reference_hit {channel_id, title, age_days}` hoặc null.

**Raw**: `y365: [Video]`, `n90: [Video]`, `channels: {id: {subs, median_views}}`, `fetched_at`. Mỗi Video gồm `{id, title, channel_id, channel, published, views}`.

## Reference channels (`channels/<slug>/references.json`, bị git bỏ qua)

`{"channels": [{"id": "UC…", "title": "…", "added": "YYYY-MM-DD"}]}`, tối đa 10. Mỗi `id` khớp `^UC[\w-]{22}$`.

## Quota usage

- **Local**: `.studio/youtube-usage.json`.
- **Online**: `$STUDIO_DATA/youtube/usage.json`.

Khuôn dạng: `{"day": "YYYY-MM-DD" (giờ Thái Bình Dương), "units": int}`. Sang ngày mới thì đếm lại từ 0. Giá: `search` 100, các endpoint khác 1.

## Cache

Mỗi mục số liệu tạm là một tệp `<sha256(endpoint+params)>.json`, gồm `{at, body}`. Mục quá 24 giờ thì bị bỏ qua và ghi đè.

## Settings (online, mở rộng)

| Khoá | Mặc định | Luật |
|---|---|---|
| `youtube_daily_units` | 9000 | 100–10000 |
| `topics_per_day` | 40 | 0–500 (0 là tắt chấm đề) |
| `youtube_key_set` | (tính ra) | bool cùng `youtube_key_last4`; khoá không bao giờ trả về |

## Job (online, loại mới `topics`)

`kind: "topics"`, `charged: false`, `input: {channel, topics: [str], suggest: bool, made: [str], references: [...]}`. Kết quả nằm ở `work/topics-result.json`, rồi được gộp vào `topics.json`. Việc phim mở rộng thêm `input.topic`: số đề được lấy.
