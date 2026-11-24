# Data model: Sửa ghi chú phim After Effects tự động

## film.json (thư mục phim)
| Trường | Kiểu | Luật |
|---|---|---|
| `engine` | `"page"` \| `"ae"` | vắng = `"page"` (phim cũ) |
| `fps` | số | phim AE: 30 mặc định |
| `size` | `[w, h]` | phim AE: `[1920, 1080]` mặc định |
| `shots` | danh sách mã | phim AE: thứ tự shot `S1…Sn`; mỗi mã có hàm `CU.shot<n>` trong `ae/*.jsx` |
| `ae_files` | danh sách tên tệp | các `ae/*.jsx` của phim, theo thứ tự nạp (tệp sau đè hàm tệp trước) |
| `audio` | đường dẫn tương đối | tiếng của bản tổng (phim tập luyện: tệp tiếng có sẵn) |

## Yêu cầu dựng AE (`$STUDIO_DATA/ae/requests/<mã>/request.json`)
| Trường | Luật |
|---|---|
| `id` | `ae-<thời gian>-<4 hex>` |
| `owner`, `job`, `film` | ai gửi, việc nào, phim nào |
| `shots` | 1–100 mã shot; hoặc `["MASTER"]` cho bản tổng |
| `state` | `queued` → `claimed` → `running` → `done` \| `failed` \| `expired` |
| `progress` | `{shot, index, total, started}` |
| `results` | `{"S13": "out/S13.mp4", …}` |
| `checks` | các dòng `CHECK …` của luật dàn cảnh từ log AE |
| `error` | `{code, message, log_tail}`: `ae_missing` · `ae_scripting_off` · `ae_stalled` · `shot_timeout` · `build_error` · `render_error` · `bridge_lost` |
| `created`, `claimed_at`, `finished_at`, `heartbeat` | ISO; `claimed` không có heartbeat 60 s → trả lại `queued` (app desktop chết) |

Một yêu cầu `running` mỗi lúc (khoá trong app desktop; phần lõi chỉ giao yêu cầu mới khi không còn `claimed/running` có heartbeat).

## Cấu hình AE của máy (`config.json` của app desktop → `ae`)
`{ "afterfx": "<đường dẫn>", "aerender": "<đường dẫn>", "work": "<thư mục làm việc>", "shotTimeoutSec": 300 }`; vắng thì tự tìm.

## Lượt sửa (`shot-notes.json` → `lot`)
`{ "job": "<mã việc>", "notes": ["n-…"], "since": "<ISO>" }`; có `lot` thì nút "Fix with Claude" hiện "Fixing…" và không tạo việc mới. Ghi chú không thuộc `notes` sửa thoải mái; khi việc xong chỉ ghi chú thuộc `notes` được cập nhật từ bản trong việc.

## Việc `fix` (sổ việc)
Như việc hiện có: `kind: "fix"`, `links.film`, `input.notes` (danh sách mã), `tokens`, `cost_usd`; không tốn lượt phim trong hạn mức (chủ xưởng không giới hạn trong chế độ app).
