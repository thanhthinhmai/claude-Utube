---
description: "Task list: Duyệt nhân vật cho phim After Effects (034-cast-review)"
---

# Tasks: Duyệt nhân vật cho phim After Effects

**Input**: `specs/034-cast-review/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md)

**Tests**: có. Spec yêu cầu test tự động (SC-002, SC-003, SC-004, SC-006); plan liệt kê các tệp test.

**Organization**: theo user story. P1 = US1 + US2 (MVP), P2 = US3, US4.

## Format: `[ID] [P?] [Story] Mô tả`

- **[P]**: chạy song song được (khác tệp, không chờ việc chưa xong)
- Đường dẫn tính từ gốc repo. Định dạng tệp: `contracts/files.md`; lệnh: `contracts/cli.md`; API: `contracts/api.md`; rig: `contracts/rig.md`.

---

## Phase 1: Setup

- [X] T001 Chuyển rig của phim thử vào bộ dựng chung: tạo `tools/ae/kit/rigs/ball/v1/ball.jsx` từ `films/ae-sleepless-test/ae/ballchar.jsx`, bọc toàn bộ hàm trong factory `CU.RIGS["ball@1"] = function (CU) { … return {catalog, make, pose, place, carry}; }` (không gán vào `CU.*`), tên comp do rig tạo bắt đầu bằng `"B "`; `catalog()` trả `{views:["front","back","34"], expressions:[…], poses:[…], walk:true}` đúng các biểu cảm và tư thế rig vẽ được (contracts/rig.md)
- [X] T002 [P] Thêm lệnh `cast` vào danh sách chuyển cho `cmd_filmcheck` ở `bin/studio` dòng 595 và dòng trợ giúp ở đầu tệp (`cast check|status|approve|notes|use|library|preview|update|library-approve`, `ae sheet`, `ae rigs`)

---

## Phase 2: Foundational (chặn mọi story)

- [X] T003 Viết `tools/ae/rigs.py`: `load()` đọc `tools/ae/rigs.lock`; `digest(id)` = sha256 của mọi tệp trong `tools/ae/kit/rigs/<họ>/v<N>/` sắp theo tên (tên + nội dung); `check()` trả danh sách id bị đổi; `lock(id)` chỉ khi id chưa có; `latest(family)`; `parse("ball@1")` → `("ball", 1)`, sai dạng → `ValueError`
- [X] T004 Tạo `tools/ae/rigs.lock` = `{"ball@1": "<sha256>"}` bằng `rigs.lock("ball@1")` (phụ thuộc T001, T003)
- [X] T005 Sửa `tools/ae/bundle.py`: gói mọi `rigs/ball/v<N>/` mà `cast/cast.json` của phim nhắc tới cộng bản mới nhất theo `rigs.lock`; sinh trong `entry.jsx` dòng `CU._rig = {}; CU.rig = function (id) { return CU._rig[id] || (CU._rig[id] = CU.RIGS[id](CU)); };` trước khi nạp jsx của phim; sinh thêm `CU.CAST` (nhân vật của `cast/cast.json`) và `CU.char = function (id, o) { var c = CU.CAST[id]; return CU.rig(c.rig).make(merge(c.spec, o)); }` để shot luôn gọi nhân vật đúng bản rig và thông số đã duyệt (FR-016, FR-020) (contracts/rig.md)
- [X] T006 Viết `tools/filmcheck/cast.py` phần lõi: `load(d)`, `validate(d)` theo luật: `id` khớp `[a-z0-9-]{1,32}` và duy nhất; `name` ≤ 40; `role` ∈ `hero|support|background`; `kind` ∈ `one|group`, `group` có `members` 2–8 spec; `rig` có trong `rigs.lock`; khoá `spec` chỉ trong `hoodie, pants, shoes, headColor, rimColor, hat{kind: beanie|cap|curly|puffs|bun|none, color}, stripe, tie, hood, brows (false|true|"angry"|"worried"), scale (0.6–1.4)`, màu `#rrggbb`, khoá lạ → `bad_spec`; `needs` = `{expressions[], poses[], walk}` mỗi mục `{key, label, para}`; `fingerprint(d, id)` = sha256[:16] của `spec`+`rig`+`needs` + băm `cast/sheets/<id>/sheet.json`; `state(d, id)` ∈ `new|ready|approved|changed` (data-model.md); ghi nguyên tử
- [X] T007 Sửa `tools/filmcheck/points.py`: `POINTS = ("script","cast","voice","shots","mix","publish")`; `fingerprint(d,"cast")` = băm `cast.json` bỏ trường `approved` + băm mọi `cast/sheets/*/sheet.json`; `cast` mặc định bật khi `film.json → engine == "ae"` (trong `set_on`/mặc định kênh) trừ khi kênh tắt rõ; `skipped` với lý do `"no characters"` khi `characters` rỗng, và luôn `skipped` cho phim trang web; `approved` ⇔ mọi nhân vật `approved` với dấu hiện tại; `gate(d,"cast")` trả tên các nhân vật chưa duyệt
- [X] T008 [P] Sửa `tools/filmcheck/steps.py`: `STEPS` thêm `"Cast"` sau `"Script"`; `GRAPH`: `"Script": ["Cast", "Voice"]`, `"Cast": ["Picture"]` (không Cast→Voice, FR-005); bước Cast chỉ hiện cho phim AE
- [X] T009 [P] Sửa `tools/filmcheck/channels.py`: `REVIEW_POINTS` nhận `cast`
- [X] T010 [P] Nâng giới hạn điểm duyệt lên 6 và thêm `"cast"` vào Literal ở `tools/studio/studio/server.py:50`, `tools/studio/studio/api_online.py:176` và `:383`; thêm `"cast"` vào `KINDS` và `POINT_KINDS` ở `tools/studio/studio/reviews.py`
- [X] T011 [P] Test lõi: `tests/filmcheck/test_cast.py` (mọi luật của T006, `bad_spec`, trạng thái), cập nhật `tests/filmcheck/test_points.py` (POINTS có cast, mặc định bật cho AE, `skipped` cho phim web và phim không nhân vật) và `tests/filmcheck/test_steps.py` (đổi Cast làm Shots/Render "stale", không làm Voice stale)

**Checkpoint**: rig v1 nạp được qua `CU.rig("ball@1")`, điểm `cast` có trong `point status` của phim AE.

---

## Phase 3: User Story 1 - Duyệt nhân vật trước khi làm giọng (P1) 🎯 MVP

**Goal**: mỗi nhân vật có bảng mẫu dựng từ rig; người dùng duyệt từng nhân vật hoặc cả dàn; giọng bị chặn khi chưa duyệt.

**Independent Test**: quickstart mục 1–2: `cast check`, `ae sheet`, `cast status` báo 3 dòng `ready`; `voice make` mã 1 kèm "characters not approved: hero, friend, classmates"; `cast approve --all` rồi `voice make` chạy được.

### Tests US1

- [X] T012 [P] [US1] `tests/ae/test_sheet.py`: tạo `master.mp4` giả bằng ffmpeg (khung đánh số màu) + `sheet_<proj>.json` giả; kiểm `sheet.py` tách đúng khung → `cast/sheets/<id>/<key>.jpg` (cạnh dài 720 px, ≤ 300 KB), `walk.mp4` (H.264, ≤ 400 px, 2,5 s, không tiếng), `sheet.json` đúng contracts/files.md, khung `missing` → `file: null` + `missing_reason`, nhóm → một khung `group`
- [X] T013 [P] [US1] Thêm vào `tests/filmcheck/test_cast.py`: cổng `voice make` trên phim AE có nhân vật chưa duyệt trả mã 1 kèm tên (SC-002); `cast approve --all` đặt `approved` cho từng nhân vật và duyệt điểm `cast`; `cast approve` mã 1 khi nhân vật chưa có bảng mẫu; nhân vật `approved` → `changed` khi `spec` đổi

### Implementation US1

- [X] T014 [US1] Viết `tools/ae/kit/castsheet.jsx`: `CU.castSheet(cast, only)` theo contracts/rig.md: 1920×1080, 30 fps, nền `#ecebf0`, nhân vật giữa khung, chân ở 92% chiều cao, cao 80%; thứ tự `front, back, 34, expr-<key>` (cận đầu), `pose-<key>` (toàn thân); clip đi bộ 75 khung nếu `needs.walk`; nhóm một khung `group`; hình lỗi → khung trống + `missing`; ghi `CU.WORK + "/sheet_<proj>.json"`
- [X] T015 [US1] Viết `tools/ae/sheet.py`: tạo bundle với entry gọi `CU.castSheet` (dùng `bundle.py`, thêm `castsheet.jsx` vào `KIT_FILES`), chạy qua `local.py` hoặc `remote.py` (cầu nối app) như `ae build`, rồi tách khung bằng ffmpeg (R1); chuyển bản cũ `cast/sheets/<id>/` sang `<id>.prev/` (đúng một bản, FR-014); ghi `cast/catalog.json` từ `catalog` của rig; `--only id,id` chỉ đụng tới các thư mục đó
- [X] T016 [US1] Sửa `tools/ae/cli.py`: lệnh `ae sheet <phim> [--only id,id]`; mã 3 khi AE hoặc cầu nối chưa sẵn sàng (in cách bật lại), mã 2 khi `cast.json` hỏng; từ chối phim trang web
- [X] T017 [US1] Sửa `tools/filmcheck/cli.py`: lệnh `cast check <phim>` (in lỗi kèm mã nhân vật, `key` của `needs` ngoài `cast/catalog.json` là cảnh báo), `cast status <phim> [--json]` (bảng id, trạng thái, số ghi chú mở, nguồn, rig; dòng cuối `point cast: <state>`), `cast approve <phim> (<id>…|--all) [--save|--no-save] [--source chat|ui]` (`--all` gọi `points.approve(d,"cast")`; phần lưu kho để T040); mã thoát 0/1/2/3/4 theo contracts/cli.md
- [X] T018 [US1] Cổng cast trong `voice make` ở `tools/filmcheck/cli.py`: sau cổng script gọi `points.gate(d,"cast")`; còn nhân vật chưa duyệt → mã 1, in `characters not approved: <id, id>`
- [X] T019 [US1] Sửa `tools/filmcheck/edit.py`: `point "cast"` với `op` `cast_approve {character}` và `cast_save {on}`; có `base` = dấu cast; lệch → mã 4
- [X] T020 [US1] Sửa `tools/studio/studio/filmsteps.py` và route `GET /jobs/{id}/steps` trong `tools/studio/studio/server.py`: thêm bước `Cast`, `points.cast`, khối `cast` = `{characters:[{id,name,role,kind,state,source,rig,spec|members,needs,sheet:{frames[]}|null,notes_open}], notes, notes_base, save_to_library, library_available}`; mở danh sách tệp cho phép của specs/025 cho `cast/sheets/<id>/<file>` và `<id>.prev/`
- [X] T021 [US1] Kind `cast` cho yêu cầu duyệt trong `tools/studio/studio/reviews.py`, `api_online.py`, `mcp_server.py`, `donesofar.py`: `approve` = duyệt mọi nhân vật (gọi `cast approve --all --source ui`)
- [X] T022 [US1] Khung Cast trong `tools/studio/studio/web/app.js` và `web/style.css` theo bản mẫu (tpl.html trong scratchpad, artifact GQ5frgBviPPC8Sb4xMY434): thanh bước có nhãn REVIEW, danh sách nhân vật (tên, vai, trạng thái), bảng mẫu theo nhóm (Turnaround, Expressions, Poses, Walk loop), ô thiếu hình "No picture yet", bảng màu kèm mã, đoạn kịch bản có nhân vật, nút "Approve" từng nhân vật và "Approve cast", ô "Save approved characters to the channel's cast" (tắt kèm lý do khi `library_available` false), cột "How it works" và "If you change this"; thông báo rõ khi AE hoặc cầu nối chưa sẵn sàng (cách bật lại)
- [X] T023 [US1] Sửa `tools/runner/agent.py` (`AE_PICTURE`): sau điểm Script, viết `cast/cast.json` (nhân vật rút từ kịch bản, `needs` theo đoạn kịch bản, R8), `cast check`, `ae sheet`, `review request --kind cast`, `review wait`; điểm cast `skipped` khi không có nhân vật; `ae sheet` mã 3 (AE hoặc cầu nối chưa sẵn sàng) → báo lỗi lên trang việc kèm cách bật lại, không bỏ qua bước; kịch bản đổi sau khi Cast đã duyệt → cập nhật `cast.json` (thêm nhân vật mới, bỏ nhân vật không còn, thêm `needs` mới) rồi chỉ dựng các nhân vật hoặc hình mới
- [X] T024 [P] [US1] Sửa `.claude/skills/film-make/SKILL.md` mục "Phim After Effects": bước Cast (viết `cast.json`, `ae sheet`, duyệt qua `review request --kind cast` hoặc chat + `cast approve --source chat`), thứ tự Script → Cast → Voice
- [X] T025 [US1] `tests/ui/test_cast_api.py`: `/jobs/{id}/steps` có khối `cast` và bước Cast cho phim AE, không có cho phim web; action `cast_approve` đổi trạng thái; quyết định `approve` của review kind `cast` duyệt cả dàn; tệp `cast/sheets/...` đọc được, đường dẫn ngoài bị chặn

**Checkpoint**: US1 chạy độc lập (quickstart mục 1–2).

---

## Phase 4: User Story 2 - Ghi chú có ghim và Claude vẽ lại (P1)

**Goal**: ghim ghi chú lên hình, ghi chú chung, yêu cầu vẽ góc, xoá; "Send notes to Claude" vẽ lại đúng các nhân vật có ghi chú.

**Independent Test**: quickstart mục 3: ghim 1 ghi chú lên friend/front, 1 ghi chú chung, xoá 1, gửi; chỉ `cast/sheets/friend/` đổi (có `friend.prev/`), ảnh của hero và classmates giữ nguyên sha256, mọi ghi chú có `reply`.

### Tests US2

- [X] T026 [P] [US2] `tests/filmcheck/test_castnotes.py`: thêm, xoá, sửa chữ, dời ghim; `x`,`y` ngoài 0–100 → `bad_pin`; ghim trên hình `file: null` bị từ chối; `kind: view` bắt buộc `frame`, tối đa một `view` mở mỗi `frame`, toggle bỏ được; `text` 1–2000; `base` lệch → `changed` kèm `current`; ghi chú mở trên nhân vật `approved` → `changed` (FR-012); ghi chú thêm khi có `lot` không vào lô (FR-013); `reply --done`
- [X] T027 [P] [US2] `tests/ui/browser_cast.cjs`: ở 1280 px và 400 px, bấm một điểm trên hình → ghim lệch ≤ 2% chiều rộng (SC-004); bấm hình phóng to dời ghim, chữ giữ nguyên; Delete xoá và đánh số lại; "Request this view"/"Undo" thêm và bỏ; bấm ô trống ngoài nút không thêm gì; đăng ký trong `tests/ui/run.sh`
- [X] T028 [P] [US2] Thêm vào `tests/ae/test_sheet.py`: `sheet.py --only friend` giữ nguyên byte mọi tệp của nhân vật khác, giữ đúng một `friend.prev/` (SC-003, FR-014)

### Implementation US2

- [X] T029 [US2] Viết `tools/filmcheck/castnotes.py` theo contracts/files.md và data-model.md: `load/save` có `base` = sha256 nội dung, id `n-<8hex>`, `add(character, kind, frame, x, y, text)` (x, y làm tròn một chữ số thập phân), `delete`, `toggle_view`, `reply(id, text, done)`, `open_by_character()`, `start_lot(job)` / `end_lot()`; dùng lại hàm băm và ghi nguyên tử của `tools/filmcheck/shotnotes.py`; khi thêm ghi chú mở lên nhân vật `approved` thì xoá `approved` của nhân vật đó trong `cast.json`
- [X] T030 [US2] Lệnh `cast notes show <phim> [--all] [--json]` (theo nhân vật: số, hình, ghim, chữ, đường dẫn ảnh của hình; dòng cuối `base: …`) và `cast notes reply <phim> <id> "<chữ>" [--done|--open] --base <b>` (mã 4 khi lệch) trong `tools/filmcheck/cli.py`
- [X] T031 [US2] Sửa `tools/filmcheck/edit.py`: `op` `cast_note_add {character, kind, frame?, x?, y?, text}`, `cast_note_delete {character, note}`, `cast_view_toggle {character, frame}` với `base` của `cast-notes.json`; `bad_pin` → mã 2
- [X] T032 [US2] "Send notes to Claude" trong `tools/studio/studio/server.py` / `reviews.py`: quyết định `revise` của review kind `cast` tự điền `note` = "N notes on: friend, hero", gọi `castnotes.start_lot(job)`; trang việc hiện trạng thái đang vẽ lại; khi Claude gửi lại yêu cầu duyệt, `end_lot()`; lượt lỗi giữ ghi chú mở và hiện lỗi
- [X] T033 [US2] Ghim và ghi chú trong `tools/studio/studio/web/app.js` + `style.css`: bấm hình đặt ghim có số tại x%/y%, khung ghi chú mở ngay dưới nhóm hình với hình phóng to (bấm để dời ghim), "Add note"/"Cancel"; ghi chú chung cho nhân vật; danh sách ghi chú có "✕ Delete" và đánh số lại; nút "Request this view"/"Undo" chỉ ở trong ô thiếu hình (ô không bấm được); "Send notes to Claude"; câu trả lời của Claude dưới từng ghi chú; so bản trước (`<id>.prev/`) cạnh bản mới; xử lý 409 `changed` bằng tải lại
- [X] T034 [US2] Sửa `tools/runner/agent.py`: khi review cast bị `revise`, chạy `cast notes show`, sửa `cast.json` (hoặc `ae/kit_fixes.jsx` nếu cần, không sửa `tools/ae/kit` trong việc), `ae sheet --only <các id có ghi chú>`, `cast notes reply` cho mọi ghi chú (`--done` hoặc lý do), rồi gửi lại `review request --kind cast`; yêu cầu `view` mà rig vẽ được thì chỉ dựng lại bảng mẫu (US4 kịch bản 4)

**Checkpoint**: US1 + US2 = MVP (quickstart mục 3).

---

## Phase 5: User Story 3 - Kho nhân vật của kênh (P2)

**Goal**: nhân vật đã duyệt vào kho của kênh trong kho app; phim sau dùng lại không phải duyệt.

**Independent Test**: quickstart mục 4: `cast approve --all --save`, `cast library default` có hero, friend, classmates v1; `cast use ae-cast-reuse default/hero` → hero `approved (library v1)`; `front.jpg` giống hệt bản trong kho.

### Tests US3

- [X] T035 [P] [US3] `tests/filmcheck/test_castlib.py` (kho tạm qua `STUDIO_DATA`): `save` ghi `v1` với `character.json` + `sheet/` + `index.json`; lưu lại cùng thông số chỉ nối `films`; thông số khác → `v2`, `v1` không đổi (FR-017); hai lần lưu cạnh tranh → hai bản, không ghi đè; `root()` trả `None` khi app không chạy → `cast approve --save` cảnh báo nhưng vẫn duyệt; `cast use` → `approved` khi `needs` ⊆ `frames_approved`, nếu không chỉ hình thiếu ở `ready`
- [X] T036 [P] [US3] Thêm vào `tests/ui/test_cast_api.py`: `GET /cast-library` (`available: false` ngoài chế độ app), `GET /cast-library/{ch}/{id}`, tệp `v{n}/{file}`, đường dẫn ngoài bị chặn

### Implementation US3

- [X] T037 [US3] Viết `tools/filmcheck/castlib.py` theo R6 và contracts/files.md: `root()` (tài khoản của request → app đang chạy qua `host.running_pointer` + `owner_id` như `app_film` → `None`); `list(channel)`, `get(channel, id, v=None)`, `save(channel, character, sheet_dir, film)` (bản mới khi thông số khác bản mới nhất, nếu không nối `films`; bản đã ghi không sửa); `index.json` ghi nguyên tử có khoá tệp
- [X] T038 [US3] Lưu khi duyệt: `cast approve … --save` (mặc định theo `save_to_library`) gọi `castlib.save` cho từng nhân vật vừa duyệt trong `tools/filmcheck/cli.py`; đặt `from_library` sau khi lưu; nhân vật từ kho có thêm hình mới thì lưu thành bản mới gồm cả hình cũ và hình mới; app không chạy → in "the app is not running", vẫn duyệt
- [X] T039 [US3] Lệnh `cast use <phim> <kênh>/<id>[@v]` và `cast library [<kênh>] [--json]` trong `tools/filmcheck/cli.py`: chép `character.json` vào `cast.json` (giữ `from_library`, `rig` của bản trong kho), chép ảnh vào `cast/sheets/<id>/`; nhân vật `approved` (source `library`) nếu `needs` ⊆ `frames_approved`; mã 3 khi app không chạy hoặc không có nhân vật
- [X] T040 [US3] Sửa `tools/ae/sheet.py` và `tools/filmcheck/cast.py`: nhân vật từ kho chỉ dựng các hình chưa có trong `frames_approved` (`--only` theo mã hình), các hình đã duyệt chép nguyên từ kho; việc thêm hình mới vào kho khi duyệt do T038 lo
- [X] T041 [US3] Viết `tools/studio/studio/castapi.py` (GET `/cast-library`, `/cast-library/{channel}/{id}`, `/cast-library/{channel}/{id}/v{n}/{file}`) và đăng ký vào `server.py` và `api_online.py`; quyền như route ghi chú của specs/029
- [X] T042 [US3] Trang Cast library trong `tools/studio/studio/web/app.js` + `style.css`: nhân vật theo kênh, bảng mẫu, ngày duyệt, phiên bản rig, các phim đã dùng; trong khung Cast của trang việc, nhân vật từ kho hiện "From the channel, approved"

**Checkpoint**: US3 chạy độc lập (quickstart mục 4).

---

## Phase 6: User Story 4 - Phiên bản rig và cập nhật nhân vật (P2)

**Goal**: nhân vật giữ bản rig lúc duyệt; kho báo bản mới, cho xem trước và chọn cập nhật.

**Independent Test**: quickstart mục 5: `ae rigs --check` mã 0; thêm `ball/v2`, `ae rigs --lock ball@2`; `cast library` báo `new rig version`; dựng lại shot cũ cho khung giống hệt; sửa một tệp trong `v1/` → `ae rigs --check` mã 1.

### Tests US4

- [X] T043 [P] [US4] `tests/ae/test_rigs.py`: `rigs.lock` khớp mọi thư mục đã khoá trong repo; sửa một tệp trong bản sao tạm của `v1/` → `check()` báo `ball@1`; `lock` từ chối id đã có; `bundle.py` gói cả `v1` và `v2` khi `cast.json` nhắc `ball@1` và lock có `ball@2`, `entry.jsx` có `CU.rig`, `CU.CAST` và `CU.char`; nhân vật `ball@1` trong `cast.json` được `CU.char` dựng bằng `ball@1` dù lock có `ball@2`
- [X] T044 [P] [US4] `tests/online/test_cast_fix_job.py` (agent giả `tests/online/fake_agent.py`): `POST /cast-library/{ch}/{id}/preview {rig}` tạo việc `fix` `target:"cast"`, `mode:"preview"` → `v<n+1>.preview/`; `update` biến preview thành `v<n+1>` chưa duyệt, 422 `no_preview` khi không có; `approve`; `fix {notes}` → `mode:"library"` → `v<n+1>` chưa duyệt; 409 `ae_unavailable` khi cầu nối chưa sẵn sàng; đăng ký trong `tests/online/run.sh`

### Implementation US4

- [X] T045 [US4] Lệnh `ae rigs [--check]` và `ae rigs --lock ball@N` trong `tools/ae/cli.py` (dùng `tools/ae/rigs.py`; `--check` mã 1 khi có bản đã khoá bị đổi)
- [X] T046 [US4] `castlib.py`: cờ `new_rig` (nhân vật `rig = ball@N`, lock có `ball@M`, M > N); `preview_dir`, `update_from_preview` (preview → `v<n+1>` chưa duyệt, xoá preview), `approve_latest`; lệnh `cast preview <kênh>/<id> --rig ball@N`, `cast update <kênh>/<id> --from-preview`, `cast library-approve <kênh>/<id>` trong `tools/filmcheck/cli.py`
- [X] T047 [US4] `castapi.py`: POST `/cast-library/{channel}/{id}/preview|update|approve|fix` theo contracts/api.md; `tools/studio/studio/jobs.py`: `build("fix", …)` nhận `input = {kind:"fix", target:"cast", mode:"preview"|"library", channel, character, rig?, notes?}`
- [X] T048 [US4] `tools/runner/worker.py`: việc `fix` `target:"cast"` dựng thư mục tạm `work/cast/<channel>-<id>/` (`cast/cast.json` một nhân vật từ kho, `cast-notes.json` nếu có); `finish_fix` chép `cast/sheets/<id>/` vào `v<n+1>.preview/` (preview) hoặc `v<n+1>/` chưa duyệt (library), kèm câu trả lời ghi chú
- [X] T049 [US4] `tools/runner/agent.py` `fix_prompt` nhánh cast: đổi `rig` khi `mode=preview`, sửa thông số theo ghi chú khi `mode=library`, `ae sheet`, trả lời từng ghi chú
- [X] T050 [US4] Trang Cast library trong `web/app.js` + `style.css`: nhãn "New rig version", nút xem trước, bảng mẫu bản mới cạnh bản đã duyệt, "Update" từng nhân vật, "Approve"; ghi chú lên nhân vật trong kho gửi `fix`

**Checkpoint**: US4 chạy độc lập (quickstart mục 5).

---

## Phase 7: Polish & Cross-Cutting

- [X] T051 [P] Cập nhật `tools/CLAUDE.md` (rigs, castsheet, sheet.py, castnotes, castlib, castapi) và mục "Phim After Effects" ở `CLAUDE.md` gốc (một dòng về bước Cast và kho nhân vật)
- [X] T052 [P] Chuyển `films/ae-sleepless-test/ae/shots.jsx` sang `CU.rig("ball@1")`, viết `films/ae-sleepless-test/cast/cast.json` (hero, friend, classmates) để làm phim thử của quickstart (thư mục phim không vào git)
- [X] T053 Chạy đủ 5 bộ test: `sh tests/run.sh`, `sh tests/filmcheck/run.sh`, `sh tests/ae/run.sh`, `sh tests/ui/run.sh`, `sh tests/online/run.sh`; sửa tới khi đạt
  - 2026-11-25: run 87/87, filmcheck 308 OK (sửa test_castlib.test_root: đặt STUDIO_ROOT tạm, không bắt app thật đang chạy), ae 34 OK, ui 83 OK, online 232 OK.
- [X] T054 Chạy quickstart mục 2–5 với AE thật trên phim thử (SC-001 ≤ 5 phút, SC-003 so sha256, SC-005, SC-006 so điểm ảnh); xem bảng mẫu bằng mắt (đầu cầu, mắt có con ngươi, mũ không che mắt)
  - 2026-11-25: mục 2 đạt (20 hình/30 s). Mục 3: lượt 1 ghi chú ngoài khả năng ball@1 (cỡ mắt, tàn nhang) được trả lời là không làm được; lượt 2 (áo #2f9e9a, lông mày worried): chỉ 6 hình của friend đổi, 13 hình của hero và classmates giữ nguyên sha256, có friend.prev/. Mục 4: approve --all --save → kho default v1; `cast use ae-cast-reuse default/hero` → front.jpg giống hệt kho (sai khác 0). Mục 5 (SC-006) do test_rigs phủ, không tạo rig tạm.

---

## Dependencies & Execution Order

- Setup (T001–T002) → Foundational (T003–T011) → các story.
- **US1** (T012–T025) cần Foundational. **US2** (T026–T034) cần US1 (bảng mẫu, khung Cast, review kind cast). **US3** (T035–T042) cần US1 (duyệt); độc lập với US2. **US4** (T043–T050) cần T003–T005 và US3 (kho).
- Trong mỗi story: test viết trước và thất bại → lõi Python → lệnh → API → giao diện → agent.
- Polish sau cùng; T052 làm sớm được ngay sau T001 nếu cần phim thử cho T054.

### Parallel

- Foundational: T008, T009, T010, T011 song song sau T006–T007.
- US1: T012, T013 song song; T014 (jsx) song song với T017–T019 (Python); T024 song song với mọi việc.
- US2: T026, T027, T028 song song; T029 trước T030–T032.
- US3: T035, T036 song song; T041–T042 sau T037.
- US4: T043, T044 song song; T045 song song với T046.

## Implementation Strategy

1. **MVP**: Setup + Foundational + US1 + US2 → chạy 5 bộ test, quickstart mục 1–3, commit.
2. **US3** kho nhân vật → test, commit.
3. **US4** phiên bản rig → test, commit.
4. Polish, quickstart với AE thật, mở PR (không tự merge).
