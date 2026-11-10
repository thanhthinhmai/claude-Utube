# Contract: API v1, chế độ online

Thêm vào [api-v1 của 003](../../003-studio-ui/contracts/api-v1.md). Mọi điểm truy cập cũ giữ nguyên hình dạng (FR-028). Ở chế độ online chúng cần đăng nhập và chỉ trả dữ liệu của khách đang đăng nhập (FR-003); `admin` thấy được tất cả.

**Quy ước:**
- Gốc: `https://<tên miền>/api/v1`. HTTPS bắt buộc.
- `POST`, `PUT`, `DELETE` cần `X-Studio: 1` và `Origin` khớp tên miền; sai thì `403 csrf`.
- Chưa đăng nhập → `401 auth_required`. Tài khoản bị khoá → `403 locked`. Không phải admin → `403 forbidden`.
- Tài nguyên của khách khác trả `404 not_found`, không trả `403`, để không lộ là tài nguyên đó tồn tại.
- Quá tần suất → `429 rate_limited` kèm `Retry-After`.
- Lỗi theo dạng cũ: `{"error": {"code", "message"}}`.

## Tài khoản
| Phương thức · Đường dẫn | Trả về | Lỗi |
|---|---|---|
| `POST /auth/signup` `{email, password, accept_terms}` | `201`, gửi thư xác minh | `403 signup_closed` · `409 email_taken` · `422 weak_password` (< 10 ký tự) · `422 terms_required` |
| `POST /auth/verify` `{token}` | `200` | `410 token_expired` · `404` |
| `POST /auth/login` `{email, password}` | `200`, đặt cookie phiên | `401 bad_login` (một thông báo chung) · `403 locked` |
| `POST /auth/logout` | `204` | |
| `POST /auth/forgot` `{email}` | luôn `202` | |
| `POST /auth/reset` `{token, password}` | `200`, huỷ mọi phiên cũ | `410` · `422` |
| `GET /me` | `{email, verified, role, quota: {films: {used, limit}, learns: {used, limit}, resets_at}, email_notify}` | |
| `PUT /me` `{email_notify?, password?, old_password?}` | `200` | `401 bad_login` |
| `DELETE /me` `{password}` | `202`, đăng xuất, xoá hẳn trong ≤ 30 ngày | `401` |

## Giao việc
| Phương thức · Đường dẫn | Trả về | Lỗi |
|---|---|---|
| `POST /jobs` `{kind: "film", style, idea, seconds, review_treatment?}` | `201 Job` (`queued`, kèm `queue_position`) | `403 unverified` · `402 quota_exceeded` (kèm `resets_at`) · `503 daily_cap` · `409 too_many_queued` (mỗi khách tối đa 3 việc chưa xong; việc thứ hai trở đi xếp hàng sau việc đang chạy) · `422 content_rejected` (kèm `reason`) · `422 too_long` · `404 style_not_found` |
| `POST /jobs` `{kind: "film", revise_of: <film>, note}` | `201 Job`, tốn 1 lượt (FR-015) | như trên |
| `POST /jobs` `{kind: "learn", source: "youtube", channel, count, rights_confirmed: true}` | `201 Job` | `422 rights_required` · `422 too_many_videos` |
| `POST /uploads` (multipart, 1 video) | `201 {upload_id, seconds}` | `413 too_large` · `422 bad_video` · `422 too_long` |
| `POST /jobs` `{kind: "learn", source: "upload", uploads: [upload_id…]}` | `201 Job` | |
| `POST /jobs/{id}/stop` | `200` | `409 finished` |
| `GET /jobs/{id}` | Job như 003, thêm `queue_position`, `cost_usd` (chỉ admin thấy), `input` | |
| `GET /films/{name}/download` | `video/mp4` kèm `Content-Disposition: attachment` | |
| `DELETE /films/{name}` · `DELETE /styles/{slug}` | `204` | `409 in_use` khi một việc đang dùng |

`POST /reviews/{id}/decision` giữ nguyên. Thêm loại `question` và `treatment` (data-model).

**Không có** điểm truy cập nào trả video hay âm thanh gốc của bộ tham chiếu, kể cả tệp khách tự tải lên (FR-018).

`/sets/*` như 003, với hai giới hạn: `sheets` và lời chép chỉ trả khi việc học **còn chạy**; sau đó `GET /sets/{set}/sheets` trả `{removed: true}`. `proof` trả tối đa 6 khung.

## Quản trị (chỉ `admin`)
| Phương thức · Đường dẫn | Trả về |
|---|---|
| `GET /admin/settings` · `PUT /admin/settings` | Settings (data-model); `422` khi giá trị ngoài khoảng cho phép |
| `GET /admin/accounts?q=` | `{accounts: [{id, email, verified, locked, quota, used, cost_month_usd, storage_mb}]}` |
| `PUT /admin/accounts/{id}` `{quota_films?, quota_learns?, locked?}` | `200`; khoá tài khoản thì dừng việc đang chạy |
| `GET /admin/usage?from=&to=` | `{days: [{day, cost_usd, jobs}], by_account: [...], storage_mb_total}` |

## Khác
`GET /health` trả thêm `mode` (`local` hoặc `online`) để giao diện biết nên hiện trang nào.

## Sự kiện
`GET /events` như 003, chỉ gửi sự kiện của khách đang đăng nhập. Thêm `job.queued` với `data: {"id", "position"}`.
