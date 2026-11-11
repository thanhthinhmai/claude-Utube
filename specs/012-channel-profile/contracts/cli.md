# Contract: lệnh `channel` và `lesson` của `bin/studio`

Các lệnh chạy được ở local, với gốc là thư mục dự án (`STUDIO_ROOT`). Thông báo in ra bằng tiếng Anh, ngắn. Với `--json`, lệnh in đúng một đối tượng JSON. Mã thoát dùng chung: 0 là xong, 2 là sai đầu vào hoặc không làm được (kèm lý do), 1 là lệnh kiểm thấy lỗi.

## Kênh

| Lệnh | Việc |
|---|---|
| `channel list [--json]` | danh sách kênh: mã, tên, ngôn ngữ, số bài học `active` |
| `channel new <slug> --name N --language L --seconds S --style X [--voice V] [--speed 1.0]` | tạo hồ sơ; mã trùng hoặc sai luật thì thoát 2 |
| `channel show <slug> [--json]` | in hồ sơ; kiểm lại tệp (người dùng có thể đã sửa tay); sai luật thì thoát 1 và in lỗi |
| `channel set <slug> <field> <value…>` | sửa một trường. `hashtags` và `banned` nhận nhiều giá trị; `--add` và `--remove` thêm hoặc bớt một mục |
| `channel decide <slug> "<text>"` | thêm một quyết định kèm ngày hôm nay |
| `channel attach <film> <slug> [--style S] [--seconds N] [--language L] [--voice V] [--speed X]` | viết bản chụp `channel.json` và `CHANNEL_BRIEF.md` vào thư mục phim. Brief bị cắt thì in cảnh báo (thoát 0) |

## Bài học

`<scope>` là mã kênh, hoặc `shared` cho bài học chung.

| Lệnh | Việc |
|---|---|
| `lesson list <scope> [--all] [--json]` | bài học `active` và `draft`; có `--all` thì liệt kê cả `retired` |
| `lesson draft <scope> --what W --why Y --stop S [--film F] [--rule R]` | thêm bài học `draft`, in số bài học. Luật sai thì thêm kèm `rule_valid: false` và in cảnh báo |
| `lesson add <scope> …` | như `draft` nhưng lưu thẳng là `active`, khi người dùng tự viết |
| `lesson approve <scope> <n>` | `draft` → `active` |
| `lesson retire <scope> <n>` | `draft` hoặc `active` → `retired` |

## Luật mới trong các máy chấm

Các luật này chỉ chạy khi thư mục phim có `channel.json`.

**`script check`**: thêm điều kiện cứng, trượt một điều là không đạt (010 FR-004):

| Mã | Luật |
|---|---|
| `channel_language` | `Language` của SCRIPT.md ≠ ngôn ngữ của kênh |
| `banned_word` | từ cấm của kênh có trong lời đọc (in `Pnn.câu "từ"`) |
| `lesson_rule` | vi phạm luật `phrase:` hoặc `max_sentence_words:` của một bài học (in `#n`). Đây là lỗi lặp lại, tức lỗi nặng |

**`publish`**: thêm mã lỗi vào contracts/cli.md của 011:

| Mã | Luật |
|---|---|
| `channel_hashtags` | thiếu hashtag bắt buộc của kênh |
| `channel_banned` | từ cấm của kênh trong tiêu đề, hook, tóm tắt, tên chương hay chữ trên thumbnail |
| `channel_title_max` | tiêu đề dài hơn `title_max` của kênh |
| `lesson_rule` | vi phạm luật `phrase:` hoặc `max_title_chars:` của một bài học (in `#n`). `PUBLISH.md` có dòng đầu `⚠ Do not publish yet: repeats lesson #n` |

**`qc`**:

| Mã | Luật |
|---|---|
| `channel_voice` | một dòng của `lines.json` có `voice` khác giọng của kênh (không ghi thì tính là `af_bella`), hoặc `speed` lệch hơn 0,01, khi `voice_override` là `false` |
