# Data Model: Xưởng phim online

Chỉ có ở chế độ `online`. Dữ liệu nằm trong SQLite `/data/studio.db` (research R6). Giờ lưu theo UTC. Riêng hạn mức tính theo tháng giờ Việt Nam.

## Account
| Trường | Kiểu | Ràng buộc |
|---|---|---|
| id | text | `a-<ngày giờ>-<4 hex>`, khoá chính |
| email | text | duy nhất, chữ thường, ≤ 254 ký tự |
| password_hash | text | argon2 |
| email_verified_at | time \| null | phải có mới giao được việc (FR-001) |
| role | `customer` \| `admin` | đúng một `admin` |
| locked_at | time \| null | có thì từ chối đăng nhập và API (US3/AC4) |
| quota_films, quota_learns | int \| null | null thì dùng mặc định trong Settings (FR-005) |
| email_notify | bool | mặc định true (FR-023) |
| terms_accepted_at | time | khi đăng ký |
| created_at, deleted_at | time | `deleted_at` có thì đang chờ xoá hẳn, chậm nhất 30 ngày (FR-026) |

## Session · Token
- **Session**: `token_hash`, `account_id`, `created_at`, `expires_at` (30 ngày), `ip`.
- **Token** (dùng một lần): `token_hash`, `account_id`, `purpose` (`verify` \| `reset`), `expires_at` (`verify` 24 giờ, `reset` 1 giờ), `used_at`.

## Settings
Chỉ một hàng, chủ xưởng sửa trên trang quản trị.

| Khoá | Mặc định |
|---|---|
| signup_open | true |
| quota_films_default / quota_learns_default | 2 / 1 mỗi tháng |
| film_max_seconds | 60 |
| learn_max_videos | 5 |
| upload_max_mb / upload_max_minutes | 500 / 20 mỗi video |
| daily_cost_cap_usd | 20 |
| job_cost_cap_usd | 5 |
| concurrency (N) | 2 |
| review_timeout_days | 7 |
| model | `claude-opus-5-5` |
| price_table | giá mỗi triệu token theo model: vào, ra, ghi đệm, đọc đệm |

## Quota usage
Tính ra từ Job, không lưu riêng.
- Số lượt đã dùng trong tháng = số Job của khách đó, cùng loại, có `charged = true`, nhận từ 00:00 ngày 1 tháng này (giờ Việt Nam).
- Kiểm hạn mức và tạo Job nằm trong cùng một giao dịch `BEGIN IMMEDIATE` (SC-008).

## Job
Mở rộng Job của 003. Giữ nguyên các trường cũ: `id`, `kind`, `name`, `status`, `step`, `progress`, `log`, `links`, `error`, `review_ids`.

| Trường mới | Kiểu | Ghi chú |
|---|---|---|
| owner | account id | thay cho `"local"` (003 FR-016) |
| input | json | mẫu khách điền: phim (`style`, `idea`, `seconds`, `review_treatment`, `revise_of`, `note`) hoặc học phong cách (`source`: `youtube` \| `upload`, `channel`, `count`, `uploads[]`) |
| charged | bool | đã trừ lượt; thành false khi trả lượt (FR-006) |
| cost_usd | real | cộng dồn từ bộ chuyển tiếp (R3) |
| queued_at, run_count | time, int | hàng đợi (FR-008a) |
| agent_session | text \| null | mã phiên của Agent SDK để nối lại (R5) |
| failure_kind | `studio` \| `customer` \| null | `studio` thì trả lượt; luật phân loại theo spec FR-006a |
| qa | json \| null | kết quả kiểm chất lượng phim: `lufs`, `true_peak`, `readcheck` (R14) |
| media_removed_at | time \| null | lúc đã xoá video, ảnh ghép, lời chép (FR-019) |

**Trạng thái** (thêm `queued` vào danh sách của 003):

```
queued ─(worker nhận)→ running ─(tạo yêu cầu duyệt)→ waiting_review ─(khách quyết định)→ queued
running → done | failed | stopped
waiting_review ─(quá review_timeout_days)→ stopped (gửi email)
queued | waiting_review ─(khách bấm Stop, hoặc tài khoản bị khoá)→ stopped
```

`waiting_resume` của giai đoạn 1 không dùng ở chế độ online.

## Review · Decision
Như 003. Thêm 3 loại yêu cầu duyệt:
- `question`: Claude hỏi lại; tối đa 3 câu cho mỗi việc (FR-014).
- `treatment`: duyệt kịch bản; quyết định Approve hoặc Request changes.
- `style-1`, `style-2`: như cũ.

Giá trị quyết định giữ nguyên. Với `question`, khách trả lời trong trường `note` cùng giá trị `approve`. Nguồn quyết định luôn là `ui`.

## Rights confirmation
| Trường | Ràng buộc |
|---|---|
| account_id, job_id, channel_url, confirmed_at, text_version | tạo cùng lúc với Job học từ YouTube (FR-017); xoá cùng tài khoản (Clarifications) |

## Film · Style · Reference set
Vẫn là thư mục như giai đoạn 1, đặt theo khách: `/data/accounts/<account_id>/{films,my-styles,references}/`.
- Khi sửa phim, bản mới có tên `<tên>-r<n>` và giữ bản cũ (FR-015).
- Thư mục làm việc của một Job là `/data/jobs/<job_id>/`, được gắn vào container của việc. Khi việc xong, kết quả (phim hoặc phong cách) được chép về thư mục của khách.

## Usage day
Một hàng cho mỗi ngày (UTC) và mỗi khách: `day`, `account_id`, `cost_usd`, `jobs`. Dùng cho trần chi phí ngày (FR-008) và báo cáo (FR-009).

## Outbox (thư chờ gửi)
`id`, `to`, `template` (`verify` \| `reset` \| `job_done` \| `job_failed` \| `review_needed` \| `review_timeout` \| `account_deleted`), `data`, `sent_at`, `tries`.
