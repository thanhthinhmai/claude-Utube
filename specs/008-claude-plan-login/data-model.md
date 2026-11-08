# Data Model: Xưởng online nội bộ chạy bằng gói Claude

Thay đổi trên [data model của 007](../007-online-studio/data-model.md). Mục nào không nhắc ở đây thì giữ nguyên.

## Claude account (mới)
Một hàng cho mỗi tài khoản đang có (slot 1 luôn có). Thông tin đăng nhập **không** nằm trong cơ sở dữ liệu. Nó nằm trong thư mục `/data/claude/slot-<n>/`, quyền 700 (research R1, R2).

| Trường | Kiểu | Ràng buộc |
|---|---|---|
| slot | int | 1…5, khoá chính |
| email | text \| null | từ `auth status`; null khi chưa đăng nhập |
| plan | text \| null | `pro`, `max`… Gói khác Pro và Max thì trang quản trị hiện cảnh báo |
| state | `signed_out` \| `signed_in` \| `limited` \| `needs_signin` | xem sơ đồ dưới |
| rest_until | time \| null | khi `limited`: giờ dùng lại, hoặc giờ hết lần chờ tăng dần |
| rest_step | int | lần chờ tăng dần hiện tại (2 giây → 5 phút); về 0 khi gọi thành công |
| same_as | int \| null | **tính ra, không lưu**: slot nhỏ hơn có cùng email |
| signin_mailed_at | time \| null | đã gửi thư "Needs sign-in" cho lần hỏng này (FR-109) |
| checked_at | time | lần đọc `auth status` gần nhất |
| usage | json \| null | hạn mức 5 giờ và tuần đọc từ lần gọi gần nhất: `{five_hour: {percent, resets_at}, seven_day: {percent, resets_at}, at}` (FR-119) |

**Trạng thái**:
```
signed_out ─(đăng nhập xong)→ signed_in
signed_in ─(429 của gói)→ limited ─(quá rest_until)→ signed_in
signed_in | limited ─(401, làm mới không được)→ needs_signin ─(đăng nhập lại)→ signed_in
mọi trạng thái ─(Sign out)→ signed_out ; slot ≥ 2 ─(Remove)→ xoá hàng và thư mục
```

**Dùng được** khi `state = signed_in`, hoặc `limited` mà đã quá `rest_until`, và `same_as` là null.

## Claude login (chỉ trong bộ nhớ của tiến trình web)
Lần đăng nhập đang chờ, chỉ một lần cho cả xưởng: `slot`, tiến trình, `url`, `started_at`. Tự huỷ sau 10 phút (FR-101).

## Call (mới)
Mỗi lần gọi Claude một hàng (research R7).

| Trường | Kiểu | Ghi chú |
|---|---|---|
| id | int | tự tăng |
| job_id | text \| null | null với lệnh kiểm nội dung (R6) |
| account_id | text \| null | thành viên sở hữu việc |
| via | text | `plan:<slot>` hoặc `api` |
| model | text | |
| tokens_in, tokens_out, cache_write, cache_read | int | từ `usage` của phản hồi |
| cost_usd | real | chỉ khi `via = api` (bảng giá như 007); `plan:*` là 0 |
| at | time | UTC |

Chỉ mục trên `(via, at)` để chọn tài khoản (R4), và trên `(account_id, at)`.

## Job (sửa)
| Trường | Thay đổi |
|---|---|
| tokens | **mới**, int: tổng 4 loại token của mọi lần gọi, so với `job_token_cap` (FR-116) |
| cost_usd | giữ, chỉ cộng các lần gọi qua khoá API |
| error | thêm lý do "No Claude account is available until <giờ>" (FR-110) |

## Settings (sửa)
| Khoá | Thay đổi |
|---|---|
| signup_open | **bỏ** (FR-111) |
| daily_cost_cap_usd | **bỏ** |
| job_cost_cap_usd | **bỏ**, thay bằng `job_token_cap`, mặc định 40 000 000 (R7) |

## Account · Token (sửa)
- **Account**: `password_hash` được null khi lời mời chưa dùng. Account chưa có mật khẩu thì không đăng nhập được.
- **Token**: thêm `purpose = invite`, sống 7 ngày (R8).

## Usage day
Không ghi nữa. Báo cáo tính từ Call. Bảng cũ để nguyên, không xoá dữ liệu.

## Outbox
Thêm mẫu thư `invite` (gửi thành viên) và `claude_signin` (gửi chủ xưởng: tài khoản slot n cần đăng nhập lại).

## Chuyển phiên bản lược đồ
Tăng phiên bản trong `db.py`:
- thêm bảng `claude_account` (tạo sẵn slot 1, có cột `usage`) và bảng `call`;
- thêm cột `job.tokens`;
- cho `password_hash` được null;
- bỏ các khoá cài đặt cũ, thêm `job_token_cap`.

Tài khoản khách có từ 007 giữ nguyên (FR-113).
