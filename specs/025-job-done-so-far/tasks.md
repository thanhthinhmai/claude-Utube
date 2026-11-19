# Tasks: Phần đã xong trên trang việc làm phim

**Input**: `specs/025-job-done-so-far/` (spec.md, plan.md, quickstart.md)

**Tests**: có (SC-001, SC-004 đòi test tự động).

## Phase 1: Foundational

- [X] T001 Ghi `film_dir` cho việc: `tools/studio/studio_cli.py` (`job start --film X` → `film_dir = PROJECT/films/X` khi thư mục có hoặc sẽ có; cả nhánh app/host) và `tools/runner/worker.py` (khi bắt đầu việc online có `input.film`: `film_dir = <work>/films/<film>`). API tạo việc không nhận trường này.
- [X] T002 Tạo `tools/studio/studio/donesofar.py`: `film_dir(job)` (plan R1), `ALLOWED` + `safe_path(base, rel)` (plan R2: so khớp toàn bộ, chặn `..`, `/`, liên kết ra ngoài, chỉ tệp thường), `content_type(rel)`.

## Phase 2: User Story 1 - Script, Voice, Mix (P1) 🎯 MVP

**Independent Test**: phim mẫu có SCRIPT.md, checks.json, lines.json, voices, out/mix.wav → `/done` đúng số; trang hiện và phát được.

- [X] T003 [US1] `donesofar.summary(job)`: `steps` (plan R3) và `sections.script|voice|mix` (plan R4, kèm `version` = mtime lớn nhất của tệp nguồn mục đó) trong `tools/studio/studio/donesofar.py`.
- [X] T004 [US1] Hai đường API trong `tools/studio/studio/server.py`: `GET {api}/jobs/{job_id}/done`, `GET {api}/jobs/{job_id}/files/{path:path}`; nạp việc như `get_job` (online: `jobs.load(id, None nếu admin, ngược lại id tài khoản)`), việc không phải `film` → 404; tệp trả bằng `FileResponse`.
- [X] T005 [US1] Khu "Done so far" trong `tools/studio/studio/web/app.js`: hàng nút (3 trạng thái, % khi có progress), mục Script (số, đoạn trích, nút mở toàn bộ kịch bản / nguồn / nhận xét từng vòng dưới dạng khối mở rộng), Voice (số; bảng dòng theo nhóm 10 đoạn; nút nghe dùng một `Audio`; lọc "Respelled only" hiện "Read as"), Mix (thẻ `<audio controls>` + độ dài mm:ss). Current step dùng `progress` có sẵn, thêm chữ `N/M`. Kiểu trong `tools/studio/studio/web/style.css` theo trang mẫu (dùng token sẵn có).
- [X] T006 [US1] Test `tests/ui/test_done_so_far.py`: phim mẫu dựng trong `Project` (SCRIPT.md 12 đoạn, SOURCES.md, checks.json có script+voice, lines.json 5 dòng có 1 `say`, voices/*.wav + dur.json, out/mix.wav 2 s) → số trong `/done`; trạng thái nút; tệp cho phép trả 200 đúng kiểu; ca từ chối: `..`, `%2e%2e`, đường dẫn tuyệt đối, liên kết trỏ ra ngoài, `channel.json`, tệp không có → 400/404.

## Phase 3: User Story 2 - Shots, Render (P2)

- [X] T007 [US2] `sections.shots|render` và trạng thái Shots/Render/Self-check/Publish trong `donesofar.py` (đọc `render.log`: dòng `render: <mode> · … · N chunks … · W workers` cuối và dòng `k/N chunks` cuối; xong khi có video và `tiers.render.pass`).
- [X] T008 [US2] Mục Shots (chọn bảng 1..N, chế độ từng cảnh 24 ảnh mỗi lần với mã, cỡ cảnh, bối cảnh từ `labels.json`, nút "Show more", lớp phủ phóng to) và Render (lưới ô đã ghi / đang ghi / chưa ghi, `k/N`, GPU hay software) trong `web/app.js` + `style.css`.
- [X] T009 [US2] Bổ sung test: phim mẫu có `.check/shots/` (2 bảng, 3 cảnh, 1 khung phụ), `labels.json`, `out/render.log` → số Shots/Render đúng, trạng thái Render `running` rồi `done` khi thêm video.

## Phase 4: User Story 3 - Cập nhật tại chỗ, quyền online (P3)

- [X] T010 [US3] `refreshJob(id)` trong `web/app.js` (plan R5): `onChange` trên trang việc cập nhật tại chỗ; giữ mục đang mở; không vẽ lại mục có tiếng đang phát.
- [X] T011 [US3] `tests/ui/browser_done.cjs` + ca trong `tests/ui/test_done_so_far.py`: mở trang việc, kiểm nút và số, bấm Voice → đếm dòng, bật lọc → chỉ dòng "Read as", bấm Shots → thấy bảng ảnh; đổi bước bằng `job step` và thêm kết quả tầng → nút đổi trong ≤ 10 s, mục đang mở còn.
- [X] T012 [US3] `tests/online/test_done_access.py`: chủ việc 200, chủ xưởng 200, thành viên khác 404 cho cả `/done` và `/files`; `film_dir` online trỏ vào thư mục việc.

## Phase 5: Polish

- [X] T013 Chạy đủ các bộ test và quickstart §2 trên `pause-ten-seconds` thật (số khớp SC-001, nghe một dòng và bản trộn, đo thời gian `/done`); ghi kết quả cuối file này. Cập nhật `CLAUDE.md` (dòng `tools/studio/`) và `specs/003-studio-ui/contracts/` nếu có danh sách API.

## Dependencies

T001, T002 → US1 (T003 → T004 → T005; T006 sau T004) → US2 (T007 → T008; T009) → US3 (T010 → T011; T012 bất kỳ sau T004) → T013.

## Implementation Strategy

MVP = US1: nghe giọng và đọc kịch bản trong lúc phim làm. US2 thêm cảnh và dựng hình; US3 làm trang mượt và khoá quyền online.

## Kết quả (2026-11-18)

- Test: `tests/run.sh` 87/87 · `tests/filmcheck` 209 OK · `tests/learn` OK · `tests/ui` 49 OK + node 33/33 (có `test_done_so_far`: tóm tắt, tệp cho phép, 6 ca từ chối gồm liên kết ra ngoài, trình duyệt, tự cập nhật) · `tests/online` 198 OK (có `test_done_access`). **Đạt.**
- SC-001 trên `pause-ten-seconds` thật (trình duyệt): Machine 10/10, Editor 8/10 sau 2 vòng, 1 826 chữ, 113 đoạn, đích 10:30, 8 nguồn; 339 dòng, am_michael 1.1, lọc ra 12 dòng "Read as"; 175 cảnh, 5 bảng ảnh, 39 khung phụ, 34 cảnh báo đã chấp nhận; bản trộn 10:06; 61/61 đoạn, GPU, 2 worker. **Đạt.** (Số chữ 1 826 là chữ trong các đoạn `[Pnn]`, khớp nhận xét của biên tập; trang mẫu ghi 2 173 là đếm cả tệp.)
- SC-002: dòng giọng bắt đầu phát sau 38 ms (nút chuyển trạng thái phát); bản trộn trả `Range` 206. **Đạt.**
- SC-003: nút Self-check đổi trong < 10 s sau `job step`, mục Shots đang mở còn nguyên (test trình duyệt). **Đạt.**
- SC-004: `..`, `%2e%2e`, đường dẫn tuyệt đối, liên kết ra ngoài, `channel.json`, thành viên khác → 400/404, không lộ nội dung. **Đạt.**
- SC-005: `/done` 8–9 ms trên phim 175 cảnh; chế độ từng cảnh tải 24 ảnh mỗi lần. **Đạt.**
- Ghi chú: `film_dir` và `runs` không bao giờ trả ra ngoài trong dữ liệu việc. Self-check và Publish chỉ có trạng thái (nội dung ở bảng kiểm và mục Publish sẵn có).
