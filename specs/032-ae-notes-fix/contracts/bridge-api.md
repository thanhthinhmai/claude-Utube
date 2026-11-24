# Cầu nối AE: API

## App desktop ↔ phần lõi (`/api/v1/ae/bridge/*`)
Mọi yêu cầu: header `X-CU-Bridge: <khoá>` (khớp `STUDIO_AE_BRIDGE`), từ 127.0.0.1; sai → 403 `forbidden`. Không cần phiên, không cần `X-Studio`.

| Đường | Ý nghĩa |
|---|---|
| `GET /ae/bridge/next` | 200 `{request}` (chuyển sang `claimed`) hoặc 204 khi không có việc |
| `GET /ae/bridge/{id}/bundle` | tải `bundle.tar` |
| `POST /ae/bridge/{id}/progress` | `{state: "running", shot, index, total}` hoặc nhịp `{}`; 200 |
| `PUT /ae/bridge/{id}/result/{name}` | thân là mp4 (≤ 500 MB); 201. App desktop dựng mọi shot của yêu cầu thành một comp `MASTER` (các shot nối nhau) và gửi một kết quả `MASTER`; mốc từng shot trong đó đi cùng `finish` |
| `POST /ae/bridge/{id}/finish` | `{ok: true, checks: [...], marks: [[t0, t1, "", "S13"], …], duration}` hoặc `{ok: false, error: {code, message, log_tail}}` (`code` thêm `disk_low`, `bad_work`) |
| `POST /ae/bridge/hello` | `{version, os, afterfx, aerender, found: bool}`: phần lõi nhớ app desktop có sẵn và có AE không (dùng cho FR-009, FR-018) |

## Việc ↔ proxy (`/internal/ae/*`, mã của việc)
| Đường | Ý nghĩa |
|---|---|
| `GET /internal/ae/status` | `{ready, code?, message?, afterfx?, queued, running}` (cho `ae status` trong việc) |
| `POST /internal/ae/requests` | multipart `bundle` + `{film, shots}` → 201 `{id}`; 409 `ae_unavailable` khi app desktop chưa `hello` trong 30 s qua (kèm lời "mở app desktop để dựng phim After Effects") |
| `GET /internal/ae/requests/{id}` | `request.json` hiện tại, thêm `ahead` (số yêu cầu đứng trước khi còn `queued`) |
| `GET /internal/ae/requests/{id}/result/{name}` | mp4 (`MASTER`) |

## Trang phim ↔ phần lõi
| Đường | Ý nghĩa |
|---|---|
| `GET /films/{name}` | thêm `engine`; phim AE thêm `lot` (của việc còn chạy, không thì `null`), `ae_ready`, `ae_message` |
| `POST /films/{name}/fix` | 201 `{job, notes, left}`: tạo việc `fix` (≤ 10 ghi chú mở); 409 `in_progress` khi đã có `lot` của việc còn chạy; 422 `not_ae` / `no_open_notes`; 409 `ae_unavailable` / `ae_missing`; 409 `app_only` ở chế độ local |
| `GET /me` | thêm `ae: {ready, message}` (trang New film) |

Cổng chia sẻ của Host (specs/018) bỏ header `X-CU-Bridge` và trả 403 cho `/api/v1/ae/bridge/*`: máy Client không gọi được cầu nối.
