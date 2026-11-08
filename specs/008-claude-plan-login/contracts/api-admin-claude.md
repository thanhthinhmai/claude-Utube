# Contract: API thêm và sửa (008)

Thay đổi trên [api-online của 007](../../007-online-studio/contracts/api-online.md). Quy ước giữ nguyên: CSRF, `401`, `403`, `404` cho tài nguyên của người khác, dạng lỗi `{"error": {"code", "message"}}`.

## Tài khoản Claude (chỉ `admin`, FR-106)
Không điểm truy cập nào trả mã đăng nhập hay nội dung thư mục `/data/claude` (FR-104).

| Phương thức · Đường dẫn | Trả về | Lỗi |
|---|---|---|
| `GET /admin/claude` | `{accounts: [ClaudeAccount], login: {slot, url, started_at} \| null, api_key: bool, ready: bool}` | |
| `POST /admin/claude/accounts` | `201 ClaudeAccount` (slot trống nhỏ nhất ≥ 2, `signed_out`) | `409 max_accounts` (đã có 5) |
| `DELETE /admin/claude/accounts/{slot}` | `204`: đăng xuất, xoá thư mục và hàng | `409 first_account` (slot 1) · `404` |
| `POST /admin/claude/accounts/{slot}/login` | `200 {slot, url}`. Huỷ lần đăng nhập đang chờ nếu có | `502 login_failed` (Claude Code không in ra URL trong 30 giây, kèm 200 ký tự cuối của đầu ra đã lọc mã) |
| `POST /admin/claude/accounts/{slot}/code` `{code}` | `200 ClaudeAccount` khi đăng nhập xong trong 30 giây | `409 no_login` (không có lần đăng nhập nào đang chờ cho slot này) · `422 bad_code` (Claude Code từ chối; đăng nhập lại được) |
| `POST /admin/claude/accounts/{slot}/logout` | `200 ClaudeAccount` (`signed_out`) | |
| `POST /admin/claude/refresh` | `200` như `GET`, đọc lại `auth status` của mọi tài khoản | |

**ClaudeAccount** = `{slot, email, plan, state, rest_until, same_as, plan_warning: bool, tokens_5h, usage}`. `usage` = `{five_hour: {percent, resets_at}, seven_day: {percent, resets_at}, at}` hoặc null khi chưa có lần gọi nào (FR-119). `percent` là 0–100 hoặc null; giờ dạng ISO. `ready` là true khi có ít nhất một tài khoản dùng được hoặc có khoá API (FR-110).

## Tạo chủ xưởng lần đầu (FR-118)
| Phương thức · Đường dẫn | Trả về | Lỗi |
|---|---|---|
| `GET /auth/setup` | `{needed: bool}`: true khi chưa có tài khoản quản trị | |
| `POST /auth/setup` `{email, password}` | `201`: tạo tài khoản quản trị đã xác minh, đặt cookie phiên | `409 already_set_up` · `422 weak_password` · `429 rate_limited` (10 lần mỗi 15 phút mỗi IP) |

## Người dùng (FR-111–FR-113, Settings → Users)
Chỉ `admin` (Owner). Vai trò hiện trên giao diện: `admin` = Owner, `customer` = Member.

| Phương thức · Đường dẫn | Trả về | Lỗi |
|---|---|---|
| `POST /auth/signup` | luôn `403 signup_closed` | |
| `GET /admin/users` | `{users: [User], me}` | |
| `POST /admin/users` `{email, password, role}` | `201 User`: tài khoản đã xác minh email | `409 email_taken` · `422 weak_password` · `422 invalid` |
| `PUT /admin/users/{id}` `{role?, disabled?, password?}` | `200 User`. `disabled: true` hoặc `password` đăng xuất mọi phiên; tắt thì dừng việc đang chạy như khoá ở 007 | `409 last_owner` (đổi, tắt Owner cuối cùng) · `409 self` (tự tắt hoặc tự hạ mình) · `404` |
| `POST /admin/users/{id}/signout` | `204`: xoá mọi phiên | `404` |
| `DELETE /admin/users/{id}` | `204`: xoá như `DELETE /me` của 007 | `409 last_owner` · `409 self` · `404` |

**User** = `{id, email, role, disabled, created_at, last_login_at, sessions}`.

`PUT /admin/accounts/{id}` của 007 (hạn mức, khoá) giữ nguyên; `locked` và `disabled` là một trường (`locked_at`).

## Mức dùng (FR-114–FR-116)
| Đường dẫn | Thay đổi |
|---|---|
| `GET /jobs/{id}` | thêm `tokens` (thành viên thấy việc của mình); `cost_usd` chỉ admin thấy, chỉ là phần qua khoá API |
| `GET /admin/usage?from=&to=` | `{days: [{day, calls, tokens, cost_usd}], by_account: [{account_id, email, calls, tokens, cost_usd}], by_claude: [{via, calls, tokens, cost_usd}], storage_mb_total}`. Số nào cũng tính từ Call |
| `GET /admin/accounts` | `cost_month_usd` đổi thành `tokens_month` |
| `PUT /admin/settings` | bỏ `signup_open`, `daily_cost_cap_usd`, `job_cost_cap_usd`; thêm `job_token_cap` (1 triệu … 500 triệu) |
| `POST /jobs` | bỏ lỗi `503 daily_cap`; thêm `503 studio_not_ready` khi `ready` là false và không kiểm được nội dung (research R6) |
