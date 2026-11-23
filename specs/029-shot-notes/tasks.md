---

description: "Tasks: ghi chú từng shot trên trang phim (029)"
---

# Tasks: Ghi chú từng shot trên trang phim

**Input**: Design documents from `specs/029-shot-notes/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (api.md, cli.md, files.md), quickstart.md

**Tests**: Có. Hiến pháp IV yêu cầu test tự động cho logic quan trọng, và SC-004, SC-007, SC-008 đo bằng test tự động.

**Organization**: Theo user story (US1 xem theo shot, US2 ghi chú, US3 vòng sửa với Claude).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: chạy song song được (tệp khác nhau, không phụ thuộc việc chưa xong)
- **[Story]**: US1, US2, US3

---

## Phase 1: Setup

- [X] T001 Tạo khung `tools/filmcheck/shotnotes.py` (docstring, hằng số: `MAX_SHOTS = 300`, `MAX_TEXT = 2000`, `MAX_IMAGES = 4`, `MAX_IMAGE_BYTES = 10 * 1024 * 1024`, `IMAGE_NAME = r"img-[0-9a-f]{12}\.(png|jpg|webp)"`, `ORPHAN_IMAGE_AGE = 3600`) và tệp test rỗng `tests/ui/test_shot_notes.py` (dùng `tests/ui/helpers.py` như các test API khác)
- [X] T002 [P] Thêm `shot-notes/`, `.shots/`, `*.prev.mp4`, `shots.prev.json` vào danh sách loại trừ của trang "Done so far" trong `tools/studio/studio/donesofar.py` (contracts/files.md)

---

## Phase 2: Foundational (chặn mọi story)

- [X] T003 Viết hàm chọn tệp an toàn trong `tools/filmcheck/shotnotes.py`: `film_paths(film_dir)` trả đường dẫn `shots.json`, `shots.prev.json`, `shot-notes.json`, `shot-notes/`, `.shots/thumbs/`, `<tên>.mp4`, `<tên>.prev.mp4`; mọi đường dẫn `resolve()` và phải nằm trong `film_dir` (khác → `StudioError("bad_name")`-tương đương `ValueError`)
- [X] T004 Viết `write_atomic(path, bytes)` và `locked(path)` (khoá `fcntl` trên `<tệp>.lock`) trong `tools/filmcheck/shotnotes.py`, cùng cách `tools/studio/studio/store.py`
- [X] T005 Thêm vào `tools/studio/studio/resources.py`: `film_summary` trả thêm `has_shots` (có `shots.json`) và `has_prev` (có `<tên>.prev.mp4`); hàm `film_path(name, kind)` gọi `shotnotes.film_paths(film_dir(name))` để server dùng
- [X] T006 [P] Test bảo mật đường dẫn trong `tests/ui/test_shot_notes.py`: tên phim `../x`, `a/b`, `%2e%2e`, tên ảnh `../../etc/passwd`, `img-zz.png`, ký tự lạ → 400 `bad_name` ở mọi đường của contracts/api.md; không tệp nào ngoài thư mục phim bị đọc hay tạo (SC-007); chế độ online: người B không đọc, ghi được ghi chú phim của người A (404), mã API vai chỉ đọc PUT/POST → 403 (FR-016)

**Checkpoint**: nền đường dẫn an toàn và ghi nguyên tử sẵn sàng.

---

## Phase 3: User Story 1 - Xem phim theo từng shot (Priority: P1) 🎯 MVP

**Goal**: Trang phim có thanh thời gian, danh sách shot có ảnh nhỏ, phát riêng shot, Prev/Next; báo rõ khi chưa có mốc shot.

**Independent Test**: `shots.json` 40 shot cho `ae-crayon-test` → 40 ô, 40 dòng có ảnh; shot 37 phát từ 1:55.3 và dừng ở 2:02.1 ± 0,2 s.

### Tests for User Story 1

- [ ] T007 [P] [US1] Test `load_shots` trong `tests/ui/test_shot_notes.py`: tệp đúng (40 shot) → `valid`; các lỗi theo data-model "1–300 shot; `shots[0].t0 = 0`; `t1 > t0`; `shots[i].t0 = shots[i-1].t1` (lệch ≤ 1 khung); `shots[-1].t1` lệch `duration` ≤ 1 khung; `id` không trùng" mỗi lỗi một ca, trả `{row, rule, detail}`; tệp vắng → `missing`; tệp 300 shot hợp lệ → `valid`, 301 shot → lỗi
- [ ] T008 [P] [US1] Test API `GET /films/{name}/shots` và `/shots/thumbs/{n}/{a|b|c}.jpg` trong `tests/ui/test_shot_notes.py`: video giả 3 s tạo bằng ffmpeg (`testsrc`), 3 shot; lần đầu 202 `building` rồi 200 JPEG; `n` ngoài khoảng → 404; đổi video (mtime) → `video_stamp` đổi và đệm cũ bị xoá
- [ ] T009 [P] [US1] Test `tests/filmcheck/test_shots_export.py`: trang giả có `window.SHOTS`, `window.DUR` và video khớp → mã 0, `shots.json` `source: "page"`; trang thiếu `SHOTS` → mã 1, không ghi; lệch độ dài video > 1 khung → mã 1

### Implementation for User Story 1

- [ ] T010 [US1] Viết `load_shots(film_dir, prev=False)` trong `tools/filmcheck/shotnotes.py` theo data-model "Mốc shot": đọc, kiểm luật, trả `{valid, missing, problems, duration, fps, source, shots:[{n,id,set,t0,t1}]}`; độ dài video lấy bằng `ffprobe` khi kiểm
- [ ] T011 [US1] Viết đệm ảnh nhỏ trong `tools/filmcheck/shotnotes.py`: `video_stamp(video)` = `<kích thước>-<mtime ns>`; `thumb(film_dir, n, which)` trả đường dẫn ảnh nếu có, nếu không khởi động một luồng nền duy nhất cắt cả 3×N ảnh ở 12%, 50%, 88% bằng `ffmpeg -ss t -i video -frames:v 1 -vf scale=320:-2 -q:v 5`, xoá thư mục đệm của dấu cũ (research R3)
- [ ] T012 [US1] Thêm đường vào `tools/studio/studio/server.py` (mục films, cả local và online): `GET /films/{name}/shots[?prev=1]`, `GET /films/{name}/shots/thumbs/{n}/{which}.jpg` (202 khi đang tạo, `Cache-Control: max-age=86400`), `GET /films/{name}/video?prev=1` theo contracts/api.md
- [ ] T013 [P] [US1] Viết `tools/filmcheck/shotsexport.py`: `export(film_dir)` gọi `tools/filmcheck/plan.mjs` có sẵn để lấy `SHOTS`, `DUR`, so với `ffprobe` video, ghi `shots.json` (`source: "page"`) bằng `write_atomic`; mã thoát theo contracts/cli.md
- [ ] T014 [US1] Thêm lệnh `sh bin/studio shots export <phim> [--dir D]` vào `bin/studio` (chọn thư mục phim theo research R8: `--dir`, kho của chủ xưởng khi app chạy và có phim, rồi `films/<phim>`; in `film: <thư mục>`)
- [ ] T015 [US1] Trong `tools/render/record.mjs`: sau khi ghép video xong, ghi `out/shots.json` từ `shots` đã đọc (định dạng data-model, `fps` = FPS, `duration` = độ dài đã ghi). Trong tầng 4 `sh bin/studio qc <phim>` (`tools/filmcheck/qc.py`, chạy ở bước Self-check, sau khi đã ghép tiếng ra `<tên>.mp4`): nếu có `out/shots.json` và độ dài `<tên>.mp4` lệch ≤ 1 khung thì chép thành `shots.json` của phim, nếu không thì gọi `shotsexport.export`; ghi một dòng kết quả vào báo cáo qc (không chặn qc)
- [ ] T016 [US1] Trong `tools/studio/studio/web/app.js` `pageFilm`: khi `f.has_video`, gọi `/shots`; vẽ phần Shots: thanh thời gian (một `<button>` mỗi shot, `flex-grow` = độ dài, màu theo trạng thái ở US2, tạm xám), danh sách shot (số, 3 `<img>` ảnh nhỏ thử lại mỗi 1 s khi 202, khoảng m:ss.s, độ dài), khung shot đang chọn (ảnh giữa, "Play this shot", Prev/Next tắt ở hai đầu); `missing` → dòng "Phim này chưa có mốc shot" kèm lệnh `sh bin/studio shots export <tên>`; `valid:false` → liệt kê `problems`
- [ ] T017 [US1] Phát riêng shot trong `tools/studio/studio/web/app.js`: `currentTime = t0`, `play()`, vòng `requestAnimationFrame` dừng khi `currentTime >= t1 - 0.03`; bấm shot khác hoặc tua tay thì huỷ vòng (research R4)
- [ ] T018 [P] [US1] Kiểu cho phần Shots trong `tools/studio/studio/web/style.css` dùng token có sẵn (`--line`, `--accent`, `--warn`, `--ok`…), bố cục co về một cột ở bề ngang điện thoại

**Checkpoint**: US1 chạy độc lập (xem, phát theo shot) với phim có `shots.json`.

---

## Phase 4: User Story 2 - Ghi chú lỗi và trạng thái từng shot (Priority: P1)

**Goal**: Thêm, sửa, xoá ghi chú (chữ, mốc giây, ảnh dán Ctrl+V), tick đã sửa, trạng thái tự suy hoặc đặt tay, bộ lọc, không mất thay đổi khi lưu đồng thời.

**Independent Test**: thêm ghi chú ở shot 37 (ghim 0:05, dán một ảnh), tải lại: ghi chú và ảnh còn, shot 37 Needs fix, ô 37 màu cam, lọc Needs fix có 37.

### Tests for User Story 2

- [ ] T019 [P] [US2] Test kiểm sổ trong `tests/ui/test_shot_notes.py` theo data-model: `text` "0–2.000 ký tự", ghi chú phải có chữ hoặc ≥ 1 ảnh, `images` "0–4 tên tệp", tên ảnh khớp `img-[0-9a-f]{12}\.(png|jpg|webp)` và tồn tại, `status` ∈ `none|fix|fixed|ok`, `at` null hoặc 0 ≤ at ≤ độ dài shot → mỗi lỗi 422 `invalid` nói rõ trường
- [ ] T020 [P] [US2] Test luật tự suy và đặt tay trong `tests/ui/test_shot_notes.py`: còn ghi chú mở → `fix`; tất cả `done` → `fixed`; không còn ghi chú → `none`; đặt tay `ok` (`status_by=user`) giữ nguyên tới lần đổi ghi chú kế tiếp thì tự suy lại
- [ ] T021 [P] [US2] Test ghi đồng thời trong `tests/ui/test_shot_notes.py`: 20 lần, hai luồng cùng đọc `base` rồi PUT thêm hai ghi chú khác nhau; luồng thua nhận 409 `changed` kèm `current`, áp lại và lưu → cuối cùng đủ 40 ghi chú, 0 mất (SC-004)
- [ ] T022 [P] [US2] Test ảnh trong `tests/ui/test_shot_notes.py`: PNG, JPEG, WebP hợp lệ → 201 tên `img-…`; tệp 10 MB + 1 byte → 413 `too_large`; PDF hoặc PNG đổi đuôi giả (byte đầu sai) → 415 `bad_image`; ảnh không được ghi chú nào nhắc tới, cũ hơn 1 giờ (giả `store.clock`) bị xoá khi PUT, ảnh mới hơn còn giữ (SC-008)

### Implementation for User Story 2

- [ ] T023 [US2] Viết sổ ghi chú trong `tools/filmcheck/shotnotes.py`: `read_notes(film_dir)` → `{base, doc, orphans}` (`base` = sha256 byte tệp, tệp vắng = sha256 chuỗi rỗng); `validate(doc, shots)`; `derive(doc, prev_doc)` áp luật tự suy cho shot `status_by=auto` và chuyển `status_by` về `auto` ở shot có ghi chú đổi; `save_notes(film_dir, base, doc, by)` trong khoá: so `base` (khác → lỗi `changed` kèm hiện tại), điền `id` `n-<8 hex>`, `by`, `created`, `updated`, dọn ảnh mồ côi > 1 giờ, `write_atomic`
- [ ] T024 [US2] Viết lưu ảnh trong `tools/filmcheck/shotnotes.py`: `save_image(film_dir, data)` kiểm byte đầu (PNG `89 50 4E 47`, JPEG `FF D8 FF`, WebP `RIFF….WEBP`) và cỡ ≤ 10 MB, đặt tên `img-<12 hex ngẫu nhiên>.<png|jpg|webp>`, ghi vào `shot-notes/`
- [ ] T025 [US2] Thêm đường vào `tools/studio/studio/server.py`: `GET /films/{name}/notes`, `PUT /films/{name}/notes` (409 `changed` kèm `current`, 422 `invalid`), `POST /films/{name}/notes/images` (multipart `file`, 201/413/415), `GET /films/{name}/notes/images/{file}` theo contracts/api.md; `by` = email người đăng nhập (online) hoặc `local`; mã API vai chỉ đọc → 403
- [ ] T026 [US2] Giao diện ghi chú trong `tools/studio/studio/web/app.js`: tải `/notes`; tô màu ô thanh thời gian và nhãn dòng theo trạng thái (ba màu khác độ sáng: Needs fix cam sáng, Fixed xanh lá đậm, No notes xám, kèm chú thích); bộ lọc All / Needs fix / Fixed / No notes kèm số; khung shot: ba nút trạng thái, danh sách ghi chú (mốc giây bấm được → `currentTime` = t0 + at, ô tick, sửa chữ, xoá có xác nhận, dòng `reply` nếu có), ô thêm ghi chú (textarea ≤ 2.000 ký tự, ô "Pin to current time" lấy `currentTime − t0` khi video đang trong shot), mục "Ghi chú của shot không còn" cho `orphans`
- [ ] T027 [US2] Dán và chọn ảnh trong `tools/studio/studio/web/app.js`: sự kiện `paste` trên textarea lấy `clipboardData.items` loại `image/*` → `POST …/notes/images`, hiện ảnh nhỏ chờ thêm (≤ 4, nút gỡ); nút chọn tệp `<input type="file" accept="image/png,image/jpeg,image/webp">`; lỗi 413/415 hiện thông báo, chữ đang gõ giữ nguyên; bấm ảnh mở to (dùng `zoomable` có sẵn)
- [ ] T028 [US2] Lưu có `base` trong `tools/studio/studio/web/app.js`: mỗi thao tác = hàm áp lên `doc`; PUT với `base`; gặp 409 thì lấy `current`, áp lại thao tác, PUT lại một lần; vẫn 409 thì báo "Ghi chú vừa được người khác đổi, đã tải lại" và vẽ lại

**Checkpoint**: US1 + US2 dùng được trên app, chưa cần Claude.

---

## Phase 5: User Story 3 - Gửi ghi chú cho Claude và nhận phim mới (Priority: P2)

**Goal**: Ô "Fix with Claude"; lệnh `notes show|reply`, `film replace` giữ một bản trước; "Xem bản trước"; phim AE ghi `shots.json`; hướng dẫn trong CLAUDE.md.

**Independent Test**: một ghi chú mở ở shot 37 của `ae-crayon-test` → `notes show` liệt kê đúng; `film replace` với video mới → trang phát video mới, "Xem bản trước" phát bản cũ; `notes reply --done` → ghi chú tick, có trả lời.

### Tests for User Story 3

- [ ] T029 [P] [US3] Test CLI trong `tests/ui/test_shot_notes.py` (chạy `bin/studio` với `--dir` thư mục tạm): `notes show` in nhóm theo shot, mốc giây trong shot và trong phim, đường dẫn ảnh, dòng `base:`; `notes reply … --done --base <đúng>` → mã 0, ghi chú `done`, trạng thái shot `fixed`; `--base` sai → mã 4; `note-id` lạ → mã 1
- [ ] T030 [P] [US3] Test `film replace` trong `tests/ui/test_shot_notes.py`: lần 1 tạo `<tên>.prev.mp4` + `shots.prev.json` và video mới có inode mới (bản hard link cũ ở thư mục khác không đổi nội dung); lần 2 thay bộ prev cũ (chỉ còn một bản); video mới hỏng hoặc `shots.json` lệch độ dài → mã 1, không đổi gì; API `GET /shots?prev=1` và `/video?prev=1` trả bản trước

### Implementation for User Story 3

- [ ] T031 [US3] Viết `replace_video(film_dir, new_video, new_shots=None)` trong `tools/filmcheck/shotnotes.py` theo research R7 (ffprobe kiểm video, kiểm `shots.json` mới khớp độ dài, đổi tên sang `.prev`, `os.replace` video mới, xoá đệm ảnh nhỏ)
- [ ] T032 [US3] Thêm lệnh vào `bin/studio`: `notes show <phim> [--all] [--json] [--dir D]`, `notes reply <phim> <note-id> "<text>" [--done|--open] --base <sha256> [--dir D]`, `film replace <phim> <video> [--shots F] [--dir D]` theo contracts/cli.md, gọi `tools/filmcheck/shotnotes.py` (chọn thư mục theo research R8)
- [ ] T033 [US3] Trong `tools/studio/studio/web/app.js`: ô "Fix with Claude" (câu `Sửa theo ghi chú phim <tên>`, nút Copy dùng `navigator.clipboard.writeText`, báo "Copied" 1,5 s); nút "Xem bản trước" ở khung shot khi `has_prev`: phát đoạn của shot cùng `id` trong bản trước (mốc từ `/shots?prev=1`) trên một `<video>` tạm cạnh video chính
- [ ] T034 [US3] Trong trang việc của `tools/studio/studio/web/app.js`: khi việc làm phim đã có video phim (`/films/<tên>` `has_video`), hiện đường dẫn "Ghi chú shot" tới `#/films/<tên>` (FR-014b); điểm duyệt Shots không đổi
- [ ] T035 [US3] Cập nhật `CLAUDE.md`: mục luồng làm phim thêm bước "Sửa theo ghi chú phim <tên>" (chạy `notes show`, liệt kê lại cho người dùng, sửa, dựng lại, `film replace`, `notes reply --done` kèm câu đã đổi gì cho từng ghi chú sửa được, `notes reply` không `--done` kèm lý do cho ghi chú chưa sửa được); thêm `shots export`, `notes`, `film replace` vào danh mục lệnh trong mục Cấu trúc
- [ ] T036 [US3] (phim tập luyện, ngoài git) Trong `films/ae-crayon-test/ae/build_core.jsx`: khi tạo comp MASTER, ghi `E:/claude-utube-ae/crayon10/shots_master.json` theo contracts/files.md (`source: "ae"`, mỗi shot `[inPoint, outPoint, "", "S<n>"]`); dựng lại, rồi `film replace ae-crayon-test <video> --shots <tệp>` để phim mẫu có `shots.json`

**Checkpoint**: vòng sửa khép kín trên phim `ae-crayon-test`.

---

## Phase 6: Polish & Cross-Cutting

- [ ] T037 [P] Chạy `tests/ui/test_typecheck.py` cho `app.js` (sửa kiểu `@ts-check` nếu lỗi) và `node --test desktop/test/*.test.js` không vỡ
- [ ] T038 Chạy kiểm chứng theo `specs/029-shot-notes/quickstart.md` trên app thật, ghi kết quả đạt/không đạt vào cuối `quickstart.md`: thời gian và số thao tác ghi một ghi chú ở phim 40 shot (SC-001, ≤ 20 s, ≤ 4 thao tác); thời gian hiện phần Shots (SC-002); 10 lần dừng shot (SC-003); dán ảnh 10 lần (SC-008); khớp `shots.json` của `ae-crayon-test` với ffprobe ≤ 1 khung (SC-005, kiểm bằng tay vì dự án AE ngoài git); một lượt sửa thử với 3 ghi chú mở trên `ae-crayon-test`: Claude liệt kê đúng cả 3 trước khi sửa, sau khi xong mỗi ghi chú hoặc tick kèm trả lời hoặc còn mở kèm lý do (SC-006)
- [ ] T039 Chạy đủ 5 bộ test: `sh tests/run.sh`, `sh tests/render/run.sh`, `sh tests/learn/run.sh`, `sh tests/ui/run.sh`, `sh tests/filmcheck/run.sh`

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → US1 → US2 → US3 → Polish.
- US2 cần mốc shot và khung shot của US1 (ghi chú gắn theo `id` shot). US3 cần sổ ghi chú của US2.
- Trong mỗi story: test viết trước, chạy thấy đỏ, rồi làm phần mã.

## Parallel Opportunities

- T002 song song với T001; T006 song song với T003–T005 (khác tệp sau khi có khung).
- US1: T007, T008, T009 song song; T013 và T018 song song với T010–T012.
- US2: T019–T022 song song.
- US3: T029, T030 song song.

## Implementation Strategy

1. MVP = Phase 1–3 (US1): xem phim theo shot với `shots.json`; kiểm chứng, commit.
2. Thêm US2 (ghi chú): kiểm chứng, commit.
3. Thêm US3 (vòng sửa với Claude, `film replace`, CLAUDE.md): kiểm chứng trên `ae-crayon-test`, commit.
4. Polish, chạy đủ 5 bộ test, mở PR.
