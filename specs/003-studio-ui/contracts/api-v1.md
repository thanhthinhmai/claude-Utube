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
| `GET /films` | `{films: [{name, has_video, has_poster, has_subtitles, rendering, has_shots, has_prev}]}` (`has_shots`, `has_prev`: 029) | |
| `GET /films/{name}` | `{name, credits, treatment_html, …}` | `404` |
| `GET /films/{name}/video` | `video/mp4`, hỗ trợ `Range` (206) | `404` |
| `GET /films/{name}/video?prev=1` | bản video trước giữ bởi `film replace` (specs/029) | `404` |
| `GET /films/{name}/shots?prev=1` | mốc shot: `{valid, missing, problems: [{row, rule, detail}], duration, fps, source, shots: [{n, id, set, t0, t1}], thumbs: ready\|building, video_stamp}` (029); `prev=1`: của bản trước | `400 bad_name` · `404` |
| `GET /films/{name}/shots/thumbs/{n}/{which}.jpg` | ảnh nhỏ 320 px của shot `n` ở 12/50/88% (`which` = `a\|b\|c`), `Cache-Control: max-age=86400`; `202 {status: building}` khi đang cắt (029) | `404` · `400 bad_name` |
| `GET /films/{name}/notes` | sổ ghi chú: `{base, doc, orphans}` (029) | `400 bad_name` · `404` |
| `PUT /films/{name}/notes` body `{base, doc}` | `{base, doc}`: ghi cả sổ nếu `base` còn đúng (029) | `409 changed` (kèm `current`) · `422 invalid` (kèm `field`) · `403 forbidden` (mã chỉ đọc) · `404` |
| `POST /films/{name}/notes/images` multipart `file` | `201 {file}`: ảnh PNG/JPEG/WebP ≤ 10 MB cho ghi chú (029; cũng nhận `multipart/form-data` có `X-Studio: 1`) | `413 too_large` · `415 bad_image` · `403 forbidden` · `404` |
| `GET /films/{name}/notes/images/{file}` | ảnh đính kèm, `file` dạng `img-<12 hex>.(png\|jpg\|webp)` (029) | `400 bad_name` · `404` |
| `POST /films/{name}/fix` body `{}` | `201 {job, notes, left}`: việc `fix` "Fix with Claude" trên ≤ 10 ghi chú mở theo thứ tự trong phim (specs/032, chỉ trong app); `GET /films/{name}` của phim AE có thêm `engine`, `lot`, `ae_ready`, `ae_message` | `422 not_ae` · `422 no_open_notes` · `409 in_progress` · `409 ae_unavailable` · `409 ae_missing` · `409 app_only` (chế độ local) |
| `GET /films/{name}/poster` | `image/jpeg` | `404` |
| `GET /films/{name}/subtitles.vtt` | WebVTT (chuyển từ `.srt`) | `404` |
| `GET /films/{name}/publish` | gói đăng: `{titles, description, subtitles, files, check}` (specs/011) | `404` |
| `GET /films/{name}/publish/{file}` | một tệp của gói: `thumbnail-[123].(png\|jpg)`, `subtitles.srt`, `titles.md`, `description.md`, `PUBLISH.md` (011) | `404` |
| `GET /films/{name}/publish.zip` | `application/zip`, cả gói (011) | `404` |
| `GET /ae/bridge/next` | `200 {id, shots, film, …}` (nhận một yêu cầu dựng AE) hoặc `204`. Mọi đường `/ae/bridge/*`: chỉ app desktop của chính máy, header `X-CU-Bridge` + từ 127.0.0.1, không cần phiên hay `X-Studio` (specs/032) | `403 forbidden` |
| `POST /ae/bridge/hello` body `{version, os, afterfx, aerender, found}` | `{ok}` (032) | `403` |
| `GET /ae/bridge/{id}/bundle` | `application/x-tar`: gói jsx của yêu cầu (032) | `404` · `409 not_active` |
| `POST /ae/bridge/{id}/progress` body `{state, shot, index, total}` hoặc `{}` (nhịp) | yêu cầu (032) | `409 not_active` |
| `PUT /ae/bridge/{id}/result/{name}` thân mp4 ≤ 500 MB, `name` = `MASTER` hoặc mã shot | `201 {bytes}` (032) | `413` · `422` · `409` |
| `POST /ae/bridge/{id}/finish` body `{ok, checks, marks, duration}` hoặc `{ok: false, error}` | yêu cầu (032) | `409` · `422` |
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
