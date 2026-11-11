# Data Model: Hồ sơ kênh và tệp bài học (012)

## Channel (`channels/<slug>/channel.json`)

| Trường | Kiểu | Luật |
|---|---|---|
| `slug` | chuỗi | `^[a-z0-9-]{1,40}$`; không trùng trong cùng một gốc |
| `name` | chuỗi | 1–80 ký tự |
| `niche`, `audience` | chuỗi | 0–500 ký tự |
| `language` | chuỗi | mã `^[a-z]{2,3}$` |
| `seconds` | số nguyên | 5–900 (online: không quá `film_max_seconds`, vượt thì dùng giới hạn của xưởng) |
| `style` | chuỗi | phong cách tồn tại trong `my-styles/` hoặc thư viện |
| `voice` | chuỗi | dạng tên giọng của R7; tuỳ chọn |
| `speed` | số | 0,5–2,0; mặc định 1,0 |
| `title_rules`, `thumbnail_rules` | chuỗi | 0–1500 ký tự, chữ tự do |
| `title_max` | số nguyên hoặc null | 20–100 |
| `hashtags` | chuỗi[] | 0–5, mỗi thẻ `#[^\s#]{1,29}`; không có thẻ nào nằm trong `banned` |
| `banned` | chuỗi[] | 0–50, mỗi mục 1–60 ký tự |
| `decisions` | `{date, text}`[] | `date` YYYY-MM-DD; `text` 1–300 ký tự; tối đa 100 mục |
| `updated` | chuỗi | thời điểm ISO, do xưởng ghi |

## Lesson (`channels/<slug>/lessons.json` hoặc tệp bài học chung)

`{"lessons": [Lesson…]}`, sắp theo `n` tăng dần.

| Trường | Kiểu | Luật |
|---|---|---|
| `n` | số nguyên | lớn nhất + 1 trong tệp; không bao giờ dùng lại |
| `date` | chuỗi | YYYY-MM-DD |
| `film` | chuỗi hoặc null | mã phim gặp lỗi |
| `what`, `why`, `stop` | chuỗi | mỗi trường 1–400 ký tự |
| `status` | `draft` \| `active` \| `retired` | chỉ `active` được đọc và kiểm |
| `rule` | chuỗi hoặc null | `phrase:…` \| `max_sentence_words:N` \| `max_title_chars:N` |
| `rule_valid` | bool | `false` khi luật không đọc được; luật đó không được kiểm |
| `retired_at`, `approved_at` | chuỗi hoặc null | thời điểm ISO |

**Chuyển trạng thái**: `draft` → `active` (duyệt), `active` → `retired`, `draft` → `retired` (bỏ nháp). Không có chiều ngược lại, và không xoá.

## Bản chụp trong thư mục phim (`films/<phim>/channel.json`)

```json
{"channel": "khoa-hoc-vui", "at": "2026-11-11T10:00:00Z",
 "film": {"style": "dark-keynote", "seconds": 45, "language": "vi", "voice": "af_bella", "speed": 1.0},
 "rules": {"language": "vi", "banned": ["sốc"], "hashtags": ["#khoahoc"], "title_max": 70,
           "voice": "af_bella", "speed": 1.0, "voice_override": false},
 "lessons": [{"n": 3, "scope": "channel", "rule": "phrase:you won't believe"},
             {"n": 1, "scope": "shared", "rule": "max_sentence_words:20"}]}
```

`CHANNEL_BRIEF.md` (≤ 6000 ký tự): xem R2.

## Kết quả chấm

- `checks.json["script"]["machine"][i]["hard"]` thêm khoá `channel_language`, `banned_word` và `lesson_rule` khi phim có bản chụp. Lỗi có `rule` = `banned_word` hoặc `lesson_rule`, kèm `lesson`: n.
- `checks.json["publish"]["problems"]` có các mã mới. `measures.lessons_repeated` = [n…].
- `checks.json["film"]["measures"]["channel_voice_bad"]` = các dòng giọng sai.

## Job (online, mở rộng)

| Trường | Thay đổi |
|---|---|
| `input.channel` | mới: mã kênh hoặc không có |
| `input.lesson` | mới: bool, chỉ ở việc sửa phim |
| `qa.publish.blocked_by_lesson` | mới: [n…] khi gói còn lặp lỗi bài học |
| `lesson_draft` | mới: `{scope, n}` của bài học nháp worker đã lưu |
