# Contract: máy chủ license (017)

Mọi phản hồi là JSON, có header `Cache-Control: no-store`. Thân yêu cầu tối đa 16 KB.

## `POST /api/license/lease`: kích hoạt và gia hạn (không cần đăng nhập)

Yêu cầu: `{"key": str, "deviceId": "<64 hex>", "deviceName"?: str, "os"?: str, "version"?: str}`. Các chuỗi bị cắt bớt cho vừa giới hạn của data-model.

| Mã | Thân | Khi nào |
|---|---|---|
| 200 | `{"lease", "label", "expiresAt": giây hoặc null, "serverTime": giây}` | key đúng, còn chỗ hoặc máy đã có |
| 403 | `{"code": "unknown" \| "revoked" \| "expired" \| "device_limit" \| "device_removed", "error": str}` | từ chối |
| 422 | `{"code": "invalid"}` | thiếu trường, `deviceId` sai dạng |
| 429 | `{"code": "rate_limited"}` | quá 10 lần `unknown` trong 10 phút từ một địa chỉ |

## `GET /api/license/releases` và `GET /api/license/releases/{name}`

Header `X-CU-Lease: <lease>`. Lease phải hợp lệ, và key cùng máy phải còn tốt lúc này; nếu không thì trả `403 {"code"}`.
- Danh sách: `{"tag", "version", "assets": [{"name", "size"}]}` (chỉ các tên được phép, R5). Chưa có bản phát hành nào thì trả `404`.
- Tệp: chuyển tiếp dạng luồng (`application/octet-stream`). Tên không được phép thì trả `404`.

## `GET /health`: `{"ok": true}`

## Trang quản lý `/admin` (HTML) và `/admin/api/*`

- `POST /admin/api/login` `{"password"}` → đặt cookie `cu_admin`; sai thì trả 401; quá giới hạn thì trả 429. `POST /admin/api/logout`.
- Các lời gọi dưới đây cần cookie hợp lệ. Lời gọi ghi cần thêm header `X-CU-Admin: 1` (thiếu thì trả 403).
  - `GET /admin/api/licenses` → `{"licenses": [{id, label, note, last4, maxDevices, expiresAt, revokedAt, status, createdAt, devices: [{deviceId, name, os, version, lastIp, firstSeenAt, lastSeenAt, removedAt}]}]}`
  - `POST /admin/api/licenses` `{label, note?, maxDevices?, expiresAt?}` → `{"key": "CU-…", "licenses": […]}`. Key chỉ trả về ở lời gọi này.
  - `PATCH /admin/api/licenses/{id}` `{label?, note?, maxDevices?, expiresAt?, revoked?}` → `{"licenses"}`
  - `DELETE /admin/api/licenses/{id}` → `{"licenses"}`
  - `DELETE /admin/api/licenses/{id}/devices/{deviceId}` → `{"licenses"}` (lần đầu gỡ, lần hai xoá)

## Lệnh trên VPS (`python cli.py …`)

- `keygen [--out tệp]`: in khoá công khai; ghi khoá riêng ra tệp (quyền 600).
- `admin-password`: hỏi mật khẩu hai lần (ít nhất 12 ký tự), không in ra.
- `sign-release <release.json>`: dùng khoá riêng trong biến `LICENSE_SIGNING_KEY`, ghi `<release.json>.sig`.

## App ↔ phần lõi

`sh bin/studio app start [--gate <tệp gate.json>] …`. Khi cổng đóng, web trả `423`: thân HTML với trình duyệt, `{"code": "license_locked"}` với lời gọi API. `/api/v1/health` luôn mở. Khi cổng đóng, worker không lấy việc mới.
