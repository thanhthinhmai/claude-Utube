# Contract: API v1

Gốc: `http://127.0.0.1:<port>/api/v1`. Tài liệu máy đọc được: `GET /api/v1/openapi.json`; trang tài liệu: `/api/v1/docs`.

**Quy ước:**
- Mọi `POST` cần header `X-Studio: 1` và `Content-Type: application/json`; thiếu → `403 csrf`.
- `Host` sai → `403 bad_host`. Nguồn không phải loopback → `403 not_local`.
- Lỗi: `{"error": {"code": "<mã>", "message": "<tiếng Việt>"}}`.

| Phương thức · Đường dẫn | Trả về | Lỗi |
|---|---|---|
| `GET /health` | `{ok, version}` | |
| `GET /jobs?status=&kind=` | `{jobs: [Job]}`, mới nhất trước | |
| `GET /jobs/{id}` | `Job` kèm `reviews: [Review]` | `404 not_found` |
| `GET /reviews?status=pending` | `{reviews: [Review]}` | |
| `GET /reviews/{id}` | `Review` kèm `summary_html`, `decision\|null` | `404` |
| `POST /reviews/{id}/decision` body `{value, note?}` | `201 Decision` (`source: ui`) | `409 already_decided` · `422 note_required` · `422 value_not_allowed` · `404` |
| `GET /films` | `{films: [{name, has_video, has_poster, has_subtitles, rendering}]}` | |
| `GET /films/{name}` | `{name, credits, treatment_html, …}` | `404` |
| `GET /films/{name}/video` | `video/mp4`, hỗ trợ `Range` (206) | `404` |
| `GET /films/{name}/poster` · `/subtitles.vtt` | ảnh · WebVTT | `404` |
| `GET /sets` | `{sets: [{set, videos, measured, media_removed}]}` | |
| `GET /sets/{set}` | `summary`, `videos[]` (không có `origin`, `title`, `channel`) | `404` |
| `GET /sets/{set}/sheets` | `{sheets: [file]}` hoặc `{removed: true}` | |
| `GET /sets/{set}/sheets/{file}` · `/proof/{file}` | `image/jpeg` | `404` · `400 bad_name` |
| `GET /styles` | `{styles: [style.json + slug]}` | |
| `GET /styles/{slug}` | `style.json`, `style_html`, `evidence_html` | `404` |
| `GET /styles/{slug}/styleframe` | `image/jpeg` | `404` |
| `GET /events` | `text/event-stream`: `job.updated`, `review.created`, `review.decided` với `data: {"id": "…"}`; `: ping` mỗi 15 s | |

**Phi chức năng:**
- Không điểm truy cập nào trả nội dung tệp ngoài `films/`, `references/`, `my-styles/`, `tools/studio/studio/web/`.
- Mã tài nguyên: `[a-z0-9-]{1,60}`; tên ảnh ghép `v\d{2}_\d{4}\.jpg`; tên ảnh chứng minh `(ref|ours_r\d+_[\d.]+)\.jpg`.
