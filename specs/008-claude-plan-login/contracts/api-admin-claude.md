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

**ClaudeAccount** = `{slot, email, plan, state, rest_until, same_as, plan_warning: bool, tokens_5h}`. `ready` là true khi có ít nhất một tài khoản dùng được hoặc có khoá API (FR-110).

## Thành viên (FR-111–FR-113)
| Phương thức · Đường dẫn | Trả về | Lỗi |
|---|---|---|
| `POST /auth/signup` | luôn `403 signup_closed` | |
| `POST /auth/invite` `{token, password, accept_terms}` | `200`: đặt mật khẩu, xác minh email, đặt cookie phiên | `410 token_expired` (đã dùng, quá 7 ngày hoặc bị thu hồi) · `422 weak_password` · `422 terms_required` |
| `GET /admin/invites` | `{invites: [{id, email, created_at, expires_at}]}`: lời mời chưa dùng, chưa hết hạn | |
| `POST /admin/invites` `{email}` | `201`, gửi thư `invite` | `409 email_taken` |
| `DELETE /admin/invites/{id}` | `204`: thu hồi | `404` |

Trang web: `/#/invite/<token>` hiện ô đặt mật khẩu. Trang đăng ký bị bỏ.

## Mức dùng (FR-114–FR-116)
| Đường dẫn | Thay đổi |
|---|---|
| `GET /jobs/{id}` | thêm `tokens` (thành viên thấy việc của mình); `cost_usd` chỉ admin thấy, chỉ là phần qua khoá API |
| `GET /admin/usage?from=&to=` | `{days: [{day, calls, tokens, cost_usd}], by_account: [{account_id, email, calls, tokens, cost_usd}], by_claude: [{via, calls, tokens, cost_usd}], storage_mb_total}`. Số nào cũng tính từ Call |
| `GET /admin/accounts` | `cost_month_usd` đổi thành `tokens_month` |
| `PUT /admin/settings` | bỏ `signup_open`, `daily_cost_cap_usd`, `job_cost_cap_usd`; thêm `job_token_cap` (1 triệu … 500 triệu) |
| `POST /jobs` | bỏ lỗi `503 daily_cap`; thêm `503 studio_not_ready` khi `ready` là false và không kiểm được nội dung (research R6) |
