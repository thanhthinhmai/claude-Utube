# Contract: mã API, tình trạng worker, tải lên bằng vé (009)

Thay đổi trên [API của 008](../../008-claude-plan-login/contracts/api-admin-claude.md). Quy ước giữ nguyên: tiền tố `/api/v1`, lỗi dạng `{"error": {"code", "message"}}`, `404` cho tài nguyên của người khác.

## Xác thực bằng mã (FR-211, research R1, R2)

- Mọi đường `/api/v1/*` (trừ đường công khai) nhận `Authorization: Bearer fs_…` như một phiên của người sở hữu mã. Có header này thì bỏ qua cookie và không kiểm `X-Studio`/Origin.
- Mã sai, đã thu hồi, hết hạn, hoặc người sở hữu bị tắt hay xoá → `401 bad_token` (cùng một câu trả lời cho mọi trường hợp).
- Vượt `rate_per_min` → `429 rate_limited`, header `Retry-After`.
- Vai trò thực Member gọi API quản trị → `403 forbidden`.
- Mọi mã gọi các đường sau → `403 token_forbidden` (FR-213): `/me/tokens*`, `/admin/tokens*`, `/admin/users*`, `/admin/claude*`, `PUT /me`, `DELETE /me`.
- Mã có `can_spend = false` gọi `POST /jobs` → `403 spend_not_allowed`, không trừ lượt, không kiểm nội dung (FR-212).

## Mã của chính mình (mọi người dùng, chỉ bằng cookie; FR-208, FR-209)

| Phương thức · Đường dẫn | Trả về | Lỗi |
|---|---|---|
| `GET /me/tokens` | `{tokens: [Token]}` (mã của chính mình) | |
| `POST /me/tokens` `{name, role, can_spend, rate_per_min, expires}` | `201 {token: Token, secret: "fs_…"}`. `secret` chỉ có ở đây, một lần | `422 invalid` (tên rỗng hoặc > 60, giá trị ngoài danh sách) · `403 forbidden` (Member xin `role = admin`) · `409 too_many_tokens` (đã có 20 mã Active) |
| `DELETE /me/tokens/{id}` | `204`: thu hồi | `404` |

`expires` ∈ `30d`, `90d` (mặc định), `1y`, `never`. `rate_per_min` ∈ 10, 30, 60 (mặc định), 120, 300. `role` ∈ `customer` (mặc định), `admin`.

**Token** = `{id, name, prefix, owner: {id, email}, role, can_spend, rate_per_min, created_at, expires_at, revoked_at, last_used_at, requests_today, status: "active" | "ended" | "revoked"}`. Không bao giờ có mã đầy đủ hay bản băm.

## Mọi mã (chỉ Owner, chỉ bằng cookie; FR-208, FR-216)

| Phương thức · Đường dẫn | Trả về | Lỗi |
|---|---|---|
| `GET /admin/tokens` | `{tokens: [Token]}` của mọi người dùng | |
| `DELETE /admin/tokens/{id}` | `204`: thu hồi mã của bất kỳ ai | `404` |

## Tình trạng worker (chỉ Owner; FR-201–FR-206)

`GET /admin/worker` →

```json
{
  "workers": [{"id": "host:1234", "state": "running" | "not_responding", "busy_with": ["j-…"], "beat_ago_s": 3, "started_at": "…"}],
  "counts": {"queued": 2, "running": 1, "waiting_review": 0, "waiting_claude": 0},
  "latest": [{"id": "j-…", "status": "…", "kind": "film" | "learn", "name": "…", "email": "…", "updated_at": "…", "error": "…" | null}]
}
```

- `workers`: tiến trình báo sống trong 10 phút qua. Rỗng thì giao diện hiện "No worker is running" kèm lệnh bật worker.
- `latest`: 50 việc mới nhất của mọi người dùng, theo `updated_at` giảm dần.
- Mã Owner dùng được (chỉ đọc).

## Tải lên và tải về bằng vé (FR-220, US2, research R6)

| Phương thức · Đường dẫn | Trả về | Lỗi |
|---|---|---|
| `POST /uploads/tickets` `{filename, size_bytes}` (cookie hoặc mã) | `201 {upload_url, expires_at, curl}`: vé dùng một lần, sống 30 phút | `422 bad_video` (đuôi tệp) · `413 too_large` (vượt `upload_max_mb`) |
| `PUT /uploads/t/{vé}` (đường công khai, thân là tệp video) | `201 {upload_id}` như `POST /uploads` | `404` (vé sai, đã dùng, hết hạn) · `413` · `422 bad_video` (kiểm như `POST /uploads`) |
| `POST /films/{name}/tickets` (cookie hoặc mã) | `201 {download_url, expires_at, curl}`: vé tải về dùng một lần, sống 30 phút | `404` (không có phim xong của mình) |
| `GET /films/t/{vé}` (đường công khai) | tệp MP4 như `GET /films/{name}/download` | `404` (vé sai, đã dùng, hết hạn) |

## OpenAPI (FR-217, research R7)

`GET /openapi.json` và `/docs` nhận cookie hoặc mã. Các đường cấm mã (ở trên) không có trong OpenAPI.
