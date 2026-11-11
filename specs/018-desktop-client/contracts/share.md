# Contract: cổng chia sẻ của Host (018)

HTTPS bằng chứng chỉ riêng của Host. Mọi phản hồi của `/__cu/*` là JSON.

| Đường | Ai gọi | Trả về |
|---|---|---|
| `GET /__cu/hello` | bất kỳ | `{"app": "claude-Utube", "hostId", "pairing": bool}` |
| `POST /__cu/pair` `{nonceC: 32 hex, name}` | bất kỳ, khi đang có mã | `{hostId, nonceH, proofH}`; không có mã thì `409 {"code":"no_pairing"}` |
| `POST /__cu/pair/confirm` `{nonceH, proofC}` | bất kỳ | `{clientId, token}`; sai thì `403 {"code":"wrong_code"}`; quá giới hạn thì `429` |
| `GET /__cu/update`, `GET /__cu/update/{name}` | Client đã ghép đôi | chuyển tiếp từ máy chủ license (017); bản build không có license thì `404` |
| mọi đường khác | Client đã ghép đôi (`X-CU-Client: <id>.<token>`) | chuyển vào phần lõi; thiếu hoặc sai header thì `403` |

## `sh bin/studio app cert [--data D]`

In `{"cert": "<PEM>", "key": "<PEM>", "fingerprint": "<sha256 hex của DER>"}`. Tạo chứng chỉ ở lần đầu, các lần sau dùng lại.
