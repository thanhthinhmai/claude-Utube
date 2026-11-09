# Contract: máy chủ MCP (009, FR-219, FR-220, research R5, R6)

- **Địa chỉ**: `<STUDIO_URL>/api/mcp`, MCP Streamable HTTP, không giữ phiên, trả JSON (không dùng luồng SSE).
- **Xác thực**: chỉ `Authorization: Bearer fs_…` (không nhận cookie). Không có mã hoặc mã hỏng → `401`.
- **Nối Claude Code**: `claude mcp add --transport http film-studio <STUDIO_URL>/api/mcp --header "Authorization: Bearer <mã>"`.
- **Mỗi công cụ là một lệnh gọi REST của xưởng** với cùng mã: cùng quyền, cùng giới hạn, cùng lỗi. Lỗi REST trả về thành lỗi công cụ, kèm `code` và `message`.
- Mỗi lệnh gọi công cụ tính là một yêu cầu của mã (giới hạn mỗi phút, `requests_today`).
- Danh sách công cụ theo vai trò thực của mã.

## Công cụ cho mọi mã

| Công cụ | Tham số | Gọi REST | Trả về |
|---|---|---|---|
| `list_styles` | `query?` | `GET /library` và `GET /styles` | phong cách thư viện (slug, tên, nhóm, dòng mô tả) và phong cách của mình |
| `make_film` | `style, idea, seconds, review_treatment?` | `POST /jobs` (kind `film`) | `{job_id, status, film}` |
| `revise_film` | `film, note` | `POST /jobs` (sửa phim) | `{job_id, status, film}` |
| `start_upload` | `filename, size_bytes` | `POST /uploads/tickets` | `{upload_url, expires_at, curl}`. Tác tử chạy lệnh `curl` để tải tệp, nhận `upload_id` |
| `learn_style` | `source: "youtube" \| "upload", channel?, count?, upload_ids?, rights_confirmed?` | `POST /jobs` (kind `learn`) | `{job_id, status}`. `youtube` thiếu `rights_confirmed` → lỗi như web |
| `list_jobs` | `status?` | `GET /jobs` | việc của mình: id, loại, tên, trạng thái, bước, lỗi |
| `get_job` | `job_id` | `GET /jobs/{id}` | việc kèm bước, nhật ký ngắn, các yêu cầu duyệt đang chờ, link phim nếu xong |
| `get_review` | `review_id` | `GET /reviews/{id}` | nội dung cần duyệt (Markdown), các lựa chọn được phép |
| `answer_review` | `review_id, value, note?` | `POST /reviews/{id}/decision` | quyết định đã ghi |
| `film_download_url` | `film` | `POST /films/{name}/tickets` | `{download_url, expires_at, curl}`: link tải về dùng một lần, sống 30 phút; tác tử không cần mã trong shell |

## Công cụ thêm cho mã có vai trò thực Owner (chỉ đọc)

| Công cụ | Gọi REST | Trả về |
|---|---|---|
| `worker_status` | `GET /admin/worker` | như contract worker |
| `usage` | `GET /admin/usage` | như 008 |

Không có công cụ nào cho: mã API, Users, tài khoản Claude, đổi cài đặt (FR-213).
