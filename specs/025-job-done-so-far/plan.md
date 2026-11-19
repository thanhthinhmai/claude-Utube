# Implementation Plan: Phần đã xong trên trang việc làm phim

**Branch**: `025-job-done-so-far` | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/025-job-done-so-far/spec.md`

**Mức**: Nhẹ. Quyết định và hợp đồng nằm trong plan này (không có `research.md`, `data-model.md`, `contracts/` riêng).

## Summary

Hai đường API chỉ đọc theo mã việc: `GET /api/v1/jobs/{id}/done` trả tóm tắt các bước và số của từng mục (tính từ tệp trong thư mục phim), và `GET /api/v1/jobs/{id}/files/{path}` trả một tệp trong thư mục phim nếu đường dẫn khớp danh sách cho phép. Quyền giống `GET /jobs/{id}` (online: chủ việc hoặc chủ xưởng). Logic nằm trong module mới `tools/studio/studio/donesofar.py` (thư viện chuẩn). Trang việc (`web/app.js`) thêm khu "Done so far" theo trang mẫu đã duyệt; khi có sự kiện `job.updated` trên trang việc, trang cập nhật tại chỗ (bước, tiến độ, log, nút, số) thay vì vẽ lại cả trang, để không ngắt tiếng đang phát và giữ mục đang mở.

## Technical Context

**Language/Version**: Python 3.12 (FastAPI hiện có), JavaScript thuần có `@ts-check` (`web/app.js`), CSS (`web/style.css`)

**Primary Dependencies**: không thêm gói; độ dài WAV đọc bằng module `wave` của Python

**Storage**: chỉ đọc tệp có sẵn trong thư mục phim; thêm trường `film_dir` (đường dẫn tuyệt đối) vào việc, do CLI và worker ghi

**Testing**: `unittest` (`tests/ui` cho local, `tests/online` cho quyền online), test trình duyệt Playwright hiện có của `tests/ui` (mở trang việc, bấm nút, đếm dòng)

**Target Platform**: local (`127.0.0.1`), online (container worker), app (host)

**Project Type**: web app nội bộ

**Performance Goals**: `/done` < 300 ms với phim 175 cảnh, 339 dòng (đọc vài tệp JSON nhỏ, không đọc ảnh); trang hiện mục Script < 2 s

**Constraints**: không đọc ngoài thư mục phim; không sửa `lib/`; không đổi quy trình làm phim

## Quyết định

- **R1. Tìm thư mục phim của một việc** (`donesofar.film_dir(job)`):
  1. `job["film_dir"]` nếu có và là thư mục. CLI `job start --film X` ghi `film_dir = <dự án>/films/X` (chế độ chat, kể cả khi app đang chạy và sổ việc nằm ở app). Worker online ghi `film_dir = <data>/jobs/<id>/films/X` khi bắt đầu việc. Trường này chỉ do CLI và worker ghi, API tạo việc không nhận nó.
  2. Không có: `store.root()/films/<links.film>` (phim đã xong, phim cũ).
  3. Không thấy thư mục: `/done` trả `{"film": null}` và trang không hiện khu.
- **R2. Danh sách tệp cho phép** (đường dẫn tương đối, so khớp toàn bộ):
  `SCRIPT.md`, `SOURCES.md`, `lines.json`, `voices/l\d{3,4}\.wav`, `out/mix\.wav`, `\.check/review-r\d+\.json`, `\.check/shots/(sheet|label-sheet)-\d+\.jpg`, `\.check/shots/S\d{3,4}(~[A-Za-z0-9.~_-]+)?\.jpg`, `\.check/labels\.json`, `checks\.json`, `CHECKS\.md`.
  Kiểm thêm: không chứa `..`, không bắt đầu bằng `/`, `resolve()` (theo liên kết) phải nằm trong thư mục phim đã `resolve()`, là tệp thường. Kiểu nội dung theo đuôi (`.md` text/markdown, `.json`, `.wav` audio/wav, `.jpg`). Trả bằng `FileResponse` (hỗ trợ Range nên tua được bản trộn 10 phút).
- **R3. Trạng thái nút** (`steps` trong `/done`): mỗi bước `done | running | waiting | none` (none = không áp dụng, ví dụ phim không lời).
  - Script: `done` khi `checks.json.script.verdict` là `pass`/`skipped`, hoặc có `SCRIPT.md` mà không có `checks.json` (phim cũ); `running` khi bước của việc là `Script`.
  - Voice: `done` khi `tiers.voice.pass`; `running` khi bước là `Voice` hoặc có `voices/*.wav` mà chưa đạt; `none` khi phim không lời.
  - Shots: `done` khi có `.check/shots/sheet-1.jpg` và `tiers.shots`; `running` khi bước là `Storyboard`/`Picture` và chưa có.
  - Mix: `done` khi có `out/mix.wav` và (bước của việc không phải `Mix` và không có lần chạy `Mix` trong `runs`) hoặc tệp không đổi ≥ 5 s.
  - Render: `done` khi `tiers.render.pass` và có video (`<phim>.mp4` hoặc `out/video.mp4`); `running` khi có `runs`/bước `Render` hoặc `out/render.log` có dòng mới hơn video; kèm `progress` {done, total}.
  - Self-check: `done` khi có `tiers.final`; Publish: `done` khi có `publish/pack.json` và `checks.json.publish`.
- **R4. Các số** (`sections` trong `/done`), mỗi mục chỉ có khi bước đó `done` hoặc `running`:
  - Script: `machine` (điểm vòng cuối), `editor` (điểm, số vòng sửa = `fix_rounds`, model), `words` (số chữ trong các đoạn `[Pnn]`), `paragraphs`, `target_seconds` (dòng `Target:`), `title`, `sources` (số dòng bắt đầu bằng `- ` hoặc số mục trong `SOURCES.md`), `excerpt` (9 đoạn đầu + dòng `>` đi kèm), `rounds` (danh sách `review-rN.json` có).
  - Voice: `lines`, `voice`, `speed` (của dòng đầu), `pass` (tầng voice), `respelled` (số dòng có `say`), `paras` (danh sách mã đoạn theo thứ tự). Bảng dòng lấy từ `lines.json` + `voices/dur.json` qua đường `files`.
  - Shots: `shots` (số `S###.jpg` không có `~`), `extras` (số có `~`), `sheets` (số `sheet-N.jpg`), `plan_pass`, `shots_pass`, `accepted` (lý do chấp nhận phong cách nếu có), `labels` (có `labels.json`).
  - Mix: `seconds` (độ dài WAV).
  - Render: `chunks_total`, `chunks_done`, `mode` (`gpu`/`software`, từ dòng `render: <mode> · …` cuối của `render.log`), `workers`.
- **R5. Cập nhật tại chỗ**: `onChange()` khi đang ở `#/jobs/<id>` gọi `refreshJob(id)` (lấy lại việc và `/done`, sửa nội dung các khối có `id` cố định: bước, thanh tiến độ, log, tóm tắt, hàng nút, số của mục đang mở). Mục đang mở chỉ vẽ lại khi dấu `version` của mục đó trong `/done` đổi và không có tiếng nào trong mục đang phát. Các trang khác vẫn `route()` như cũ.
- **R6. Bảng dòng giọng chia theo nhóm đoạn**: mỗi nhóm 10 đoạn (P01–P10, P11–P20, …), chọn nhóm bằng ô chọn; lọc "Respelled only" bỏ qua nhóm, hiện mọi dòng có `say`. Một đối tượng `Audio` dùng chung, bấm dòng khác thì dừng dòng cũ.
- **R7. Chế độ từng cảnh** tải 24 ảnh mỗi lần (`loading="lazy"`), nút "Show more"; ảnh phóng to là lớp phủ bấm để đóng (như trang mẫu).

## Hợp đồng

`GET /api/v1/jobs/{id}/done` (quyền như `GET /jobs/{id}`; việc không phải `film` → 404):

```json
{"film": "pause-ten-seconds",
 "steps": [{"key": "script", "label": "Script", "state": "done"}, …,
           {"key": "render", "label": "Render", "state": "running", "progress": {"done": 21, "total": 61}}],
 "sections": {"script": {"version": "…", "machine": 10.0, "editor": {"score": 8.0, "fix_rounds": 2, "model": "…"},
                         "words": 2173, "paragraphs": 113, "target_seconds": 630, "title": "…", "sources": 8,
                         "excerpt": [{"kind": "dir", "text": "…"}, {"kind": "para", "id": "P01", "text": "…"}], "rounds": [1, 2, 3]},
              "voice": {"version": "…", "lines": 339, "voice": "am_michael", "speed": 1.1, "pass": true, "respelled": 12},
              "shots": {"version": "…", "shots": 175, "extras": 39, "sheets": 5, "plan_pass": true, "shots_pass": true, "accepted": "…", "labels": true},
              "mix": {"version": "…", "seconds": 606.06},
              "render": {"version": "…", "chunks_done": 21, "chunks_total": 61, "mode": "gpu", "workers": 2}}}
```

`GET /api/v1/jobs/{id}/files/{path}`: 200 với tệp; 400 khi đường dẫn sai dạng hoặc ra ngoài; 404 khi không có tệp, không khớp danh sách, hoặc không có quyền với việc (online, như trang việc).

## Constitution Check

| Nguyên tắc | Đánh giá |
|---|---|
| I. Spec là nguồn sự thật | Spec 025 đã duyệt 2026-11-18 |
| II. Không đoán | Bố cục theo trang mẫu đã duyệt; nhóm 10 đoạn và 24 cảnh là mặc định ghi ở đây |
| III. MVP, chia story | US1 (Script, Voice, Mix) chạy được trước US2 (Shots, Render), US3 (cập nhật tại chỗ, quyền online) |
| IV. Đo được | SC-001 so số trên trang với tệp phim thật bằng test trình duyệt; SC-004 bằng test API |
| V. Đơn giản | Một module đọc tệp, hai đường API, một khu giao diện; không lưu thêm dữ liệu ngoài `film_dir` |
| VI. Thư viện giữ nguyên | Không đụng `lib/` |

Kết quả: đạt.

## Project Structure

```text
specs/025-job-done-so-far/  spec.md · plan.md · quickstart.md · tasks.md · checklists/
tools/studio/studio/donesofar.py     # mới: film_dir(job), summary(job), allowed(path), file(job, path)
tools/studio/studio/server.py        # 2 đường API (local và online dùng chung, quyền như get_job)
tools/studio/studio_cli.py           # job start --film ghi film_dir
tools/runner/worker.py               # ghi film_dir của việc online khi bắt đầu
tools/studio/studio/web/app.js       # khu Done so far, refreshJob tại chỗ
tools/studio/studio/web/style.css    # kiểu cho nút bước, bảng dòng, lưới đoạn, lớp phủ ảnh
tests/ui/test_done_so_far.py         # mới: /done trên phim mẫu, danh sách tệp, các ca từ chối
tests/ui/browser_done.cjs            # mới: mở trang việc, bấm Script/Voice/Shots/Mix, kiểm số
tests/online/test_done_access.py     # mới: thành viên khác bị từ chối, chủ xưởng xem được
```

## Complexity Tracking

Không có.
