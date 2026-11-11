# Data Model: License key và tự cập nhật (017)

## Máy chủ license (SQLite)

| Bảng | Cột | Luật |
|---|---|---|
| `licenses` | `id` (text, uuid), `key_hash` (unique), `key_last4`, `label` (≤ 80), `note` (≤ 500), `max_devices` (1–20, mặc định 1), `expires_at` (giây hoặc null), `revoked_at` (giây hoặc null), `created_at` | Trạng thái: `revoked` nếu `revoked_at`, rồi `expired` nếu `expires_at ≤ now`, còn lại `active` |
| `devices` | `id`, `license_id` (FK, xoá theo key), `device_id` (64 hex), `device_name` (≤ 80), `os` (≤ 40), `app_version` (≤ 20), `last_ip`, `first_seen_at`, `last_seen_at`, `removed_at` | unique (`license_id`, `device_id`). Gỡ lần đầu đặt `removed_at` (máy đó bị từ chối); gỡ lần hai xoá hàng (máy đó kích hoạt lại được) |
| `admin` | `password_hash` (argon2), `updated_at` | Một hàng |
| `sessions` | `token_hash`, `created_at`, `expires_at` | 12 giờ |
| `events` | `at`, `kind`, `license_id`, `detail` | Nhật ký: tạo, sửa, thu hồi, xoá, gỡ máy, đăng nhập |

## App (config.json, thêm trường)

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `installId` | chuỗi | khi không đọc được mã máy |
| `lease` | chuỗi hoặc null | lease mới nhất (đã kiểm) |
| `licenseClock` | số (giây) | mốc giờ lớn nhất từng thấy |
| `licenseRefused` | `{code, at}` hoặc null | máy chủ đã từ chối; giữ khoá cả khi mất mạng |
| `licenseLabel`, `licenseExpires` | chuỗi, số hoặc null | để hiện trong "License…" |
| `pendingUpdate` | `{version, file}` hoặc null | bản mới đã tải và kiểm xong |
| key | (không lưu ở đây) | Windows: `safeStorage` (DPAPI) trong `license.key`; macOS: Keychain, dịch vụ "claude-Utube license" |

## gate.json (app → phần lõi)

`{"deviceId": "<64 hex>", "lease": "<lease>", "clock": <giây>, "refused": null | "<code>"}`. Ghi lại sau mỗi lần gia hạn hoặc khoá (ghi ra tệp tạm rồi đổi tên).

## release.json (mỗi bản phát hành)

`{"version": "0.2.0", "tag": "desktop-v0.2.0", "files": [{"name": "claude-Utube-Setup-0.2.0.exe", "size": 1307602491, "sha256": "…"}, …]}`. `release.json.sig` là base64url của chữ ký Ed25519 trên đúng các byte của `release.json`.
