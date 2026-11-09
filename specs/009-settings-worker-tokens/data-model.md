# Data Model: Settings → Worker và API tokens

Thay đổi trên [data model của 008](../008-claude-plan-login/data-model.md). Lược đồ lên phiên bản **3**; cơ sở dữ liệu cũ tự nâng cấp, không mất dữ liệu.

## API token (mới, bảng `api_token`)

| Trường | Kiểu | Ràng buộc |
|---|---|---|
| id | text | khoá chính, `tok-…` |
| owner_id | text | tài khoản sở hữu (cũng là người tạo và người được thay mặt), xoá theo tài khoản |
| name | text | bắt buộc, ≤ 60 ký tự |
| prefix | text | 8 ký tự đầu của mã, để nhận ra |
| hash | text | `sha256` của mã, duy nhất |
| role | text | `customer` hoặc `admin`; `admin` chỉ khi người tạo là Owner lúc tạo |
| can_spend | int | 0 hoặc 1, mặc định 0 (FR-212) |
| rate_per_min | int | 10, 30, 60, 120 hoặc 300; mặc định 60 |
| created_at | time | |
| expires_at | time \| null | null là Never |
| revoked_at | time \| null | |
| last_used_at | time \| null | |

**Trạng thái** (tính ra): Revoked khi có `revoked_at`; Ended khi quá `expires_at`; còn lại Active.

**Vai trò thực** của một yêu cầu = vai trò thấp hơn giữa `role` và vai trò hiện tại của người sở hữu. Người sở hữu bị tắt hay xoá thì mã bị từ chối (FR-214).

Mỗi người tối đa 20 mã Active (R9).

## Token usage day (mới, bảng `token_day`)

| Trường | Kiểu | Ràng buộc |
|---|---|---|
| token_id | text | khoá chính cùng `day` |
| day | text | `YYYY-MM-DD` theo giờ Việt Nam |
| requests | int | số yêu cầu, kể cả qua máy chủ MCP |

## Worker heartbeat (mới, bảng `worker_beat`)

| Trường | Kiểu | Ràng buộc |
|---|---|---|
| id | text | khoá chính: `<tên máy>:<mã tiến trình>` |
| started_at | time | |
| beat_at | time | ghi ít nhất mỗi 15 giây |
| busy | text | JSON: danh sách mã việc đang chạy |

Trạng thái (tính ra): Running (idle nếu `busy` rỗng) khi `beat_at` ≤ 60 giây trước; Not responding khi > 60 giây; ẩn khi > 10 phút. Worker dừng êm thì xoá hàng của mình.

## Ticket (mới, bảng `ticket`): vé tải lên và tải về dùng một lần

| Trường | Kiểu | Ràng buộc |
|---|---|---|
| hash | text | khoá chính, `sha256` của vé |
| kind | text | `upload` hoặc `download` |
| account_id | text | người sở hữu |
| token_id | text \| null | mã đã xin vé |
| filename | text | `upload`: tên tệp sẽ tải lên; `download`: tên phim |
| size | int \| null | `upload`: dung lượng khai báo, ≤ giới hạn của web |
| expires_at | time | 30 phút sau khi cấp |
| used_at | time \| null | dùng một lần |

## Không đổi

Account, Session, Job, Call, Claude account, Settings của 008 giữ nguyên. Việc giao qua mã vẫn là Job của người sở hữu.
