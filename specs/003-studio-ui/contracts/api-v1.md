# Contract: API v1

Gốc: `http://127.0.0.1:<port>/api/v1`. Tài liệu máy đọc được: `GET /api/v1/openapi.json`; trang tài liệu: `/api/v1/docs`.

**Quy ước:**
- Mọi `POST` cần header `X-Studio: 1` và `Content-Type: application/json`; thiếu → `403 csrf`.
- `Host` sai → `403 bad_host`. Nguồn không phải loopback → `403 not_local`.
- Lỗi: `{"error": {"code": "<mã>", "message": "<tiếng Việt>"}}`.

| Phương thức · Đường dẫn | Trả về | Lỗi |
|---|---|---|
| `GET /health` | `{ok, version, app, root}` | `root`: project folder the server serves (the launcher only stops servers of its own project) |
| `GET /jobs?status=&kind=` | `{jobs: [Job]}`, mới nhất trước | |
| `GET /jobs/{id}` | `Job` kèm `reviews: [Review]` | `404 not_found` |
| `GET /jobs/{id}/done` | việc làm phim: `{film, steps: [{key, label, state, progress?}], sections: {script, voice, shots, mix, render}}` (specs/025) | `404` (không phải việc làm phim, không có quyền) |
| `GET /jobs/{id}/files/{path}` | một tệp của thư mục phim trong danh sách cho phép (`SCRIPT.md`, `SOURCES.md`, `lines.json`, `voices/l…wav`, `out/mix.wav`, `.check/review-r…json`, `.check/labels.json`, `.check/shots/…jpg`, `checks.json`, `CHECKS.md`), `Range` cho âm thanh (025) | `400 bad_name` (`..`, tuyệt đối, liên kết ra ngoài) · `404` |
| `GET /jobs/{id}/steps` | việc làm phim: `{film, steps, points, impact, busy, editable, catalog, voices, mix_ranges, review}`, có `ETag` (specs/026) | `404` |
| `POST /jobs/{id}/actions` body `{point, op, args, base}` | `202 {id, status: queued}`: một thao tác sửa, chạy bằng `sh bin/studio edit` (026) | `422 invalid` · `409 finished` · `429 too_many` · `404` |
| `GET /jobs/{id}/actions/{aid}` | thao tác: `{status: queued\|running\|done\|failed\|invalid\|conflict\|busy, result}` (026) | `404` |
| `PUT /jobs/{id}/points` body `{on: [điểm]}` | `{on}`: điểm duyệt của phim (026) | `409 point_locked` · `404` |
| `GET /reviews?status=pending` | `{reviews: [Review]}` | |
| `GET /reviews/{id}` | `Review` kèm `summary_html`, `decision\|null` | `404` |
| `POST /reviews/{id}/decision` body `{value, note?, base?}` | `201 Decision` (`source: ui`); điểm duyệt (026): `approve` cần `base` | `409 already_decided` · `409 changed` · `422 checks_not_passed` · `422 note_required` · `422 value_not_allowed` · `404` |
| `GET /films` | `{films: [{name, has_video, has_poster, has_subtitles, rendering}]}` | |
| `GET /films/{name}` | `{name, credits, treatment_html, …}` | `404` |
| `GET /films/{name}/video` | `video/mp4`, hỗ trợ `Range` (206) | `404` |
| `GET /films/{name}/poster` | `image/jpeg` | `404` |
| `GET /films/{name}/subtitles.vtt` | WebVTT (chuyển từ `.srt`) | `404` |
| `GET /films/{name}/publish` | gói đăng: `{titles, description, subtitles, files, check}` (specs/011) | `404` |
| `GET /films/{name}/publish/{file}` | một tệp của gói: `thumbnail-[123].(png\|jpg)`, `subtitles.srt`, `titles.md`, `description.md`, `PUBLISH.md` (011) | `404` |
| `GET /films/{name}/publish.zip` | `application/zip`, cả gói (011) | `404` |
| `GET /sets` | `{sets: [{set, videos, measured, media_removed}]}` | |
| `GET /sets/{set}` | `summary`, `videos[]` (không có `origin`, `title`, `channel`) | `404` |
| `GET /sets/{set}/sheets` | `{sheets: [file]}` hoặc `{removed: true}` | |
| `GET /sets/{set}/sheets/{file}` | `image/jpeg` | `404` · `400 bad_name` |
| `GET /sets/{set}/proof/{file}` | `image/jpeg` | `404` · `400 bad_name` |
| `GET /styles` | `{styles: [style.json + slug + based_on_in_library]}` | |
| `GET /styles/{slug}` | `style.json`, `style_html`, `evidence_html`, `based_on_in_library` | `404` |
| `GET /styles/{slug}/styleframe` | `image/jpeg` | `404` |
| `GET /library` | `{installed, version, styles: [LibraryStyle], groups: [{name, count}], posters: {have, total}, skipped}` (004) | |
| `GET /library/styles/{slug}` | `LibraryStyle` kèm `style_html` (004) | `404 not_found` · `400 bad_name` |
| `GET /library/styles/{slug}/poster` | `image/jpeg`, `Cache-Control: max-age=86400`, `ETag` (004) | `404` · `400 bad_name` |
| `GET /events` | `text/event-stream`: `job.updated`, `review.created`, `review.decided` với `data: {"id": "…"}`; `: ping` mỗi 15 s | |

**Phi chức năng:**
- Không điểm truy cập nào trả nội dung tệp ngoài `films/`, `references/`, `my-styles/`, `lib/lemo-opuscar/styles/` (chỉ `style.json`, `STYLE.md`, `poster.jpg`; 004), `tools/studio/studio/web/`.
- Mã tài nguyên: `[a-z0-9-]{1,60}`; tên ảnh ghép `v\d{2}_\d{4}\.jpg`; tên ảnh chứng minh `(ref|ours_r\d+_[\d.]+)\.jpg`.
