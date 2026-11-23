# Cầu nối AE: API

## App desktop ↔ phần lõi (`/api/v1/ae/bridge/*`)
Mọi yêu cầu: header `X-CU-Bridge: <khoá>` (khớp `STUDIO_AE_BRIDGE`), từ 127.0.0.1; sai → 403 `forbidden`. Không cần phiên, không cần `X-Studio`.

| Đường | Ý nghĩa |
|---|---|
| `GET /ae/bridge/next` | 200 `{request}` (chuyển sang `claimed`) hoặc 204 khi không có việc |
| `GET /ae/bridge/{id}/bundle` | tải `bundle.tar` |
| `POST /ae/bridge/{id}/progress` | `{state: "running", shot, index, total}` hoặc nhịp `{}`; 200 |
| `PUT /ae/bridge/{id}/result/{shot}` | thân là mp4 của shot (≤ 500 MB); 201 |
| `POST /ae/bridge/{id}/finish` | `{ok: true, checks: [...]}` hoặc `{ok: false, error: {code, message, log_tail}}` |
| `POST /ae/bridge/hello` | `{version, os, afterfx, aerender, found: bool}`: phần lõi nhớ app desktop có sẵn và có AE không (dùng cho FR-009, FR-018) |

## Việc ↔ proxy (`/internal/ae/*`, mã của việc)
| Đường | Ý nghĩa |
|---|---|
| `POST /internal/ae/requests` | multipart `bundle` + `{film, shots}` → 201 `{id}`; 409 `ae_unavailable` khi app desktop chưa `hello` trong 30 s qua (kèm lời "mở app desktop để dựng phim After Effects") |
| `GET /internal/ae/requests/{id}` | `request.json` hiện tại |
| `GET /internal/ae/requests/{id}/result/{shot}` | mp4 của shot |

## Trang phim ↔ phần lõi
| Đường | Ý nghĩa |
|---|---|
| `GET /films/{name}` | thêm `engine`, `lot` (nếu có), `ae_ready` (app desktop có AE) |
| `POST /films/{name}/fix` | tạo việc `fix` (≤ 10 ghi chú mở); 409 `in_progress` khi đã có `lot`; 422 `not_ae` / `no_open_notes`; 409 `ae_unavailable` |
