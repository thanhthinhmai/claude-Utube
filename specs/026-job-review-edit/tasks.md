---
description: "Tasks for 026 — review points and edits on the film job page"
---

# Tasks: Điểm duyệt và chỉnh sửa trên trang việc làm phim

**Input**: `specs/026-job-review-edit/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md)

**Tests**: bắt buộc theo hiến pháp IV (logic quan trọng có test tự động). Test viết trước phần code của từng story.

**Organization**: theo user story của spec (US1 Script P1, US2 Shots P2, US3 Voice P3, US4 Mix P4, US5 Publish P5).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: chạy song song được (khác tệp, không chờ task chưa xong)
- **[Story]**: US1…US5

---

## Phase 1: Setup

- [X] T001 Tạo bộ phim mẫu cho test trong `tests/filmcheck/samples.py`: hàm `review_film(tmp)` tạo thư mục phim có `SCRIPT.md` (4 đoạn `[P1]…[P4]`), `SOURCES.md`, `lines.json` (8 dòng L01–L08 lấy từ kịch bản), `voices/*.wav` giả (1 s im lặng), `checks.json` rỗng, `kit/` chép từ `my-styles/dusk-hypothetical/kit` (bỏ `test/`), `scenes.json` 4 cảnh hợp lệ theo `contracts/film-files.md`
- [X] T002 [P] Thêm `mix.json` vào `SKIP_NAMES` trong `tools/filmcheck/tiers.py` và vào danh sách bỏ qua tương ứng trong `tools/render/lib.mjs`; thêm test trong `tests/filmcheck/test_tiers.py`: đổi `mix.json` không đổi `fingerprint(d)`

---

## Phase 2: Foundational (chặn mọi story)

- [X] T003 [P] Test `tests/filmcheck/test_points.py`: dấu theo phần (script đổi khi sửa `SCRIPT.md`, không đổi khi sửa `mix.json`; shots = `tiers.fingerprint(d)`); `approve` ghi `checks.json` → `reviews.approved[p]` với `fingerprint, at, by, source, review_id`; lần duyệt mất hiệu lực khi dấu đổi (trạng thái `stale`); `approve` với `base` cũ trả mã 4; phép kiểm chưa đạt trả mã 1; `set` từ chối đổi điểm `approved`/`waiting`; điểm tắt → `gate` trả `[]`; phim không lời đọc → script/voice `skipped`
- [X] T004 Viết `tools/filmcheck/points.py` theo data-model "Point" và "Film reviews": `POINTS`, `parts(point)`, `fingerprint(d, point)`, `load(d)`, `set_on(d, points)`, `state(d, point, review=None)`, `checks_pass(d, point) -> list[str]` (script: kết quả `script check` mới nhất đạt và dấu khớp; voice: `tiers.voice` đạt; shots: `tiers.plan` và `tiers.shots` đạt với dấu `all` hiện tại và không còn cảnh báo chưa chấp nhận; mix: `out/mix.wav` mới hơn `mix.json`; publish: `publish` đạt), `approve(d, point, base, source, by, review_id) -> (code, reasons)`, `gate(d, point) -> list[str]`, `skip(d, point, reason)`; ghi qua `report.update`; mặc định `["script","shots"]`
- [X] T005 [P] Test `tests/filmcheck/test_steps.py`: mười bước đúng thứ tự; `impact("script")` = Voice, Picture, Shots, Mix, Render, Self-check, Publish; `impact("mix")` = Self-check, Publish; Voice `stale` khi chữ một dòng trong `lines.json` khác `SCRIPT.md`; Shots `stale` khi `tiers.shots.fingerprint` khác dấu `all`; Mix `stale` khi `out/mix.wav` cũ hơn `mix.json`
- [X] T006 Viết `tools/filmcheck/steps.py` theo data-model "Step": `STEPS`, `GRAPH`, `impact(point)`, `status(d, job_step=None, busy=None) -> list[{name, state, note, point}]` (dùng `points.state`, kết quả tầng trong `checks.json`, mtime tệp)
- [X] T007 [P] Test `tests/filmcheck/test_edit.py` (khung chung): `base` sai → mã 4 và mọi tệp giữ nguyên SHA-256; `busy.json` còn sống cho bước liên quan → mã 5; `busy.json` của pid đã chết trên cùng `host` → bỏ qua; khác `host` → còn sống khi < 6 giờ và việc đang `running` với bước trùng; thao tác lạ → mã 2; lưu đạt ghi một dòng `.check/edits.jsonl` có `at, by, source, op, point, ref, old, new, result, stale`
- [X] T008 Viết khung `tools/filmcheck/edit.py`: `run(d, op, args, base, by, source) -> dict` (bảng `OPS` mỗi thao tác gồm điểm, kiểm hợp lệ, ghi, lệnh sau), khoá `.check/busy.json` `{"step","pid","host","since","by"}` (cùng `host`: sống khi pid còn chạy và < 6 giờ; khác `host`: sống khi < 6 giờ và việc đang `running` với bước trùng), ghi tệp tạm rồi `os.replace`, nhật ký `.check/edits.jsonl`, mã thoát 0/1/2/4/5 theo `contracts/cli.md`
- [X] T009 Thêm nhóm lệnh `point` (`status|set|approve|gate`) và `edit` vào `tools/filmcheck/cli.py` theo `contracts/cli.md`; chuyển `point` và `edit` sang `cmd_filmcheck` trong `bin/studio`; thêm vào `usage` và dòng `bin/studio` trong `CLAUDE.md` (mục Cấu trúc)
- [X] T010 [P] Thêm trường `reviews` vào hồ sơ kênh trong `tools/filmcheck/channels.py` (kiểm thuộc năm điểm, `none` = rỗng, mặc định `["script","shots"]` khi thiếu); `attach` ghi `reviews.on` và `reviews.from` vào `checks.json` của phim qua `points.set_on`; `channel set <kênh> reviews …` và `channel show` trong `tools/filmcheck/cli.py`; test trong `tests/filmcheck/test_channels.py`
- [X] T011 Thêm năm loại duyệt `script|voice|shots|mix|publish` vào `tools/studio/studio/reviews.py` (`KINDS`, nhãn "script review"…; `film` bắt buộc; `decide(approve)` với năm loại này cần `base`, gọi `points.approve(film_dir, point, base, source, by, rid)` trước khi tạo quyết định: mã 4 → `409 changed`, mã 1 → `422 checks_not_passed` kèm lý do); `review request --kind <điểm> --film` trong `tools/studio/studio_cli.py`; `REVIEW` trong `web/app.js`
- [X] T012 Viết `tools/studio/studio/actions.py` theo data-model "Action": `create(job, point, op, args, base)` (kiểm `op` thuộc `point`, việc chưa kết thúc, ≤ 30 thao tác/phút mỗi việc → `429`), `load`, `run_local(aid)` (luồng nền, mỗi việc một hàng đợi tuần tự, gọi `sh bin/studio edit <phim> <op> … --base --by --source ui --json` với `cwd` = gốc xưởng, map mã thoát → `done|failed|invalid|conflict|busy`, ghi `result`, ghi một dòng nhật ký việc `Edit <op> <ref>: …`)
- [X] T013 Thêm vào `tools/studio/studio/server.py`: `GET /jobs/{id}/steps` (gọi `steps.status`, `points`, `impact`, `catalog` từ `kit/catalog.json` + `scenes.json.custom`, `voices`, `mix_ranges`, `review` đang chờ; có `ETag`), `POST /jobs/{id}/actions` (`202`), `GET /jobs/{id}/actions/{aid}`, `PUT /jobs/{id}/points` (`409 point_locked`; gọi thẳng `points.set_on`, kể cả online, vì chỉ ghi `checks.json`); quyền như `GET /jobs/{id}` (025); mã API gọi được các đường này qua cơ chế hiện có (`tokens.is_forbidden`, không thêm phạm vi); dấu nội dung nhớ theo (đường dẫn, mtime, kích thước) để `/steps` < 300 ms với phim 175 cảnh, 339 dòng (test đo thời gian trong T014)
- [X] T014 [P] Test `tests/ui/test_review_points.py` (API): `/steps` trả mười bước và `impact`; `POST /actions` với `op` không thuộc `point` → `422`; người khác (online) → `404`; quyết định `approve` thiếu `base` → `422`, `base` cũ → `409 changed`, kiểm chưa đạt → `422 checks_not_passed`; `PUT /points` đổi điểm đã duyệt → `409`
- [X] T015 Trang việc trong `tools/studio/studio/web/app.js` và `style.css`: thanh tiến trình mười bước (trạng thái Done/Running/Waiting for you/Not yet/Must run again/Skipped/Not reviewed, nhãn `REVIEW` ở điểm bật), dòng trạng thái "Waiting for you: <bước>", khung theo bước bấm vào (mặc định bước đang chờ), cột "If you change this" từ `impact`, nhật ký; khu "Done so far" của 025 dùng làm phần chỉ đọc của khung; cập nhật tại chỗ khi có `job.updated` (gọi lại `/steps`); theo trang mẫu https://claude.ai/artifact/MxW7LE2jx1DMrYYMzJMNoD
- [X] T016 Khoá bận từ `job run`: khi việc có `film_dir`, `job run --step S` ghi `.check/busy.json` với `step=S`, `by="job run"`, `host` (tên máy hoặc container) và xoá khi xong (`tools/studio/studio_cli.py`); `/steps` trả `busy`; trang hiện "Busy: <bước>" và khoá nút sửa của bước bị ảnh hưởng

**Checkpoint**: lõi điểm duyệt, đồ thị, khung `edit`, API và thanh tiến trình chạy; chưa có thao tác sửa cụ thể.

---

## Phase 3: User Story 1 — Duyệt và sửa kịch bản (P1) 🎯 MVP

**Goal**: dừng ở Script, sửa đoạn có kiểm, duyệt, làm tiếp; `voice make` bị chặn khi chưa duyệt.

**Independent Test**: quickstart mục 1 và 2.

- [ ] T017 [P] [US1] Test trong `tests/filmcheck/test_edit.py`: `script-para P3 --text-file` thay đúng đoạn `[P3]` trong `SCRIPT.md`, các đoạn khác giữ nguyên byte; `P9` không có → mã 2, tệp không đổi; chữ rỗng, > 4000 ký tự hoặc chứa `[P` → mã 2; sau khi lưu chạy `script check` (theo luật, không gọi Claude: `checks.json` không có thêm lượt `editor`), JSON có `check.score`; kiểm chưa đạt → mã 1
- [ ] T018 [US1] Thao tác `script-para` trong `tools/filmcheck/edit.py` (dùng `script.para_map`/`read_script`, ghi `SCRIPT.md` qua tệp tạm, gọi `run_check` của `cli.py` hoặc `script.check`)
- [ ] T019 [P] [US1] Test trong `tests/filmcheck/test_voicemake.py`: `voice make` khi điểm script bật và chưa duyệt → mã 1, in "run: sh bin/studio point approve …" hoặc lệnh duyệt; điểm tắt → chạy (`STUDIO_TTS_DRY`); `--skip-review "lý do"` → chạy và ghi `reviews.skipped.script`
- [ ] T020 [US1] Cổng trong `cmd_voice_make` (`tools/filmcheck/cli.py`): gọi `points.gate(d, "script")`; thêm `--skip-review`
- [ ] T021 [US1] Khung Script trên trang (`web/app.js`): mỗi đoạn có mã, phần, điểm, ghi chú biên tập (P1/P2 từ `.check/review-r*.json`), nút Edit → ô sửa + "Run script check" (gửi `POST /actions` `script-para` với `base`), hiện kết quả thao tác (điểm, lỗi), nút "Approve script" khoá khi còn ô sửa chưa kiểm hoặc kiểm chưa đạt (ghi lý do), "Request changes" kèm ghi chú (`revise`); duyệt gửi quyết định có `base`
- [ ] T022 [US1] Luồng chat trong `CLAUDE.md` (bước 3 "Kịch bản được chấm"): sau `script review` đạt, nếu `point status <phim> --json` có script bật thì `review request <mã> --kind script --film <phim> --summary films/<phim>/SCRIPT.md` + `review wait` (có giao diện) hoặc hỏi trong chat rồi `point approve <phim> script --source chat`; sau khi duyệt chạy `point status` và làm lại bước `stale`; điểm đang bật mà ở trạng thái `stale` (bị mở lại vì sửa sau khi duyệt) thì gửi lại `review request` khi tới nó (FR-016a); `revise` → sửa theo ghi chú rồi gửi lại
- [ ] T023 [US1] Online trong `tools/runner/agent.py` và `tools/runner/worker.py`: hướng dẫn agent gửi `review request --kind script --film` rồi kết thúc lượt; `resume_answered` thêm lời nhắn cho năm loại mới ("The owner approved the <điểm> review. Run `point status <phim> --json`, redo the stale steps in order, send the review again for any review point that is on and stale, then go on." / với `revise`: ghi chú và "fix it, then send the review again")
- [ ] T024 [P] [US1] Test `tests/online/test_actions.py` (phần US1): việc chờ duyệt script ở `waiting_review` không có container chạy; quyết định `approve` → việc về `queued` với lời nhắn đúng loại trong vòng 60 s khi worker rảnh (SC-005, đo bằng `RUNNER=local`)
- [ ] T025 [US1] Chạy quickstart mục 1–2 trên `films/review-trial`; ghi kết quả (đạt / đạt một phần / thất bại) vào cuối `specs/026-job-review-edit/quickstart.md`

**Checkpoint**: US1 tự chạy được — MVP.

---

## Phase 4: User Story 2 — Duyệt và sửa cảnh trước khi dựng hình (P2)

**Goal**: sửa cảnh theo danh mục, kiểm lại, giữ cảnh kèm lý do, duyệt; `render` bị chặn khi chưa duyệt.

**Independent Test**: quickstart mục 3.

- [ ] T026 [P] [US2] Test bộ dựng `my-styles/dusk-hypothetical/kit/test/film.test.mjs` (hoặc tệp mới `scenes-file.test.mjs`): `film()` không truyền `scenes` thì đọc `./scenes.json`; `custom` trong tệp không có hàm dựng → lỗi `custom set "x" in scenes.json has no builder`; truyền mảng như cũ vẫn chạy
- [ ] T027 [US2] `my-styles/dusk-hypothetical/kit/film.js`: `scenes` mặc định `'./scenes.json'` (dạng `{custom, scenes}`), kiểm `custom` khớp; cập nhật `specs/022-style-film-kit/contracts/kit-api.md` một dòng về `scenes.json`
- [ ] T028 [P] [US2] Viết `tools/filmcheck/scenecheck.mjs <thư mục phim> [tệp]`: import `kit/plan.js` của phim, `check(scenes, CATALOG)`, kiểm tên `custom:*` thuộc `custom`; in `{"ok":true}` hoặc `{"ok":false,"error":"s07: …"}`
- [ ] T029 [P] [US2] Test trong `tests/filmcheck/test_edit.py`: `shot S02 cam=close` đổi đúng cảnh trong `scenes.json`; `cam=fisheye` (ngoài danh mục) → mã 2, `scenes.json` giữ nguyên SHA-256; phim không có `scenes.json` → mã 2 "no scene table"; `except S02 dark --reason ""` → mã 2; `accept-style --reason "deliberate dark beat"` → ghi như `qc accept-style`
- [ ] T030 [US2] Thao tác `shot`, `shots-check`, `except`, `accept-style` trong `tools/filmcheck/edit.py` (bản tạm → `scenecheck.mjs` → `os.replace`; sau đó `qc plan` và `qc shots --only <S#>`; `shots-check` chạy `qc shots` đầy đủ; `except`/`accept-style` gọi `tiers.add_exception` / `cmd_qc_accept_style`)
- [ ] T031 [US2] `qc shots --only S012[,S013]` trong `tools/filmcheck/shotcheck.py` và `cli.py`: chỉ vẽ ảnh các cảnh đó vào `.check/shots/`, không ghi `tiers.shots`; test trong `tests/filmcheck/test_shots.py` (Chrome giả hoặc bỏ qua khi thiếu Chromium, ghi rõ)
- [ ] T032 [P] [US2] Test trong `tests/filmcheck/test_tiers.py`: `render-gate` có lý do "the shots review is not approved (run: …)" khi điểm shots bật và chưa duyệt; không còn khi đã duyệt; `--skip-checks` bỏ qua và ghi lại
- [ ] T033 [US2] Cổng shots trong `cmd_render_gate` (`tools/filmcheck/cli.py`) gọi `points.gate(d, "shots")` sau `tiers.gate`
- [ ] T034 [US2] Khung Shots trên trang (`web/app.js`): lưới ảnh 24 cảnh mỗi trang (mã, thời điểm, lời, nhãn lỗi/cảnh báo), ba ô chọn bối cảnh/máy/động tác chỉ từ `catalog` (không ô gõ tự do; khoá khi `editable.shots=false` và ghi lý do), nhãn "changed" tới khi `shots-check` xong, nút "Run shot check", "Keep it this way…" mở ô lý do bắt buộc (thao tác `except` hoặc `accept-style`), "Approve and render" khoá khi còn lỗi/cảnh báo/cảnh chưa kiểm (ghi lý do)
- [ ] T035 [US2] Luồng chat `CLAUDE.md` (bước 3b, sau tầng 2): điểm duyệt shots như T022, trước `render`; agent online trong `tools/runner/agent.py` như T023
- [ ] T036 [US2] Chuyển `films/review-trial` sang `scenes.json` và chạy quickstart mục 3; ghi kết quả vào `quickstart.md`

---

## Phase 5: User Story 3 — Nghe và sửa giọng từng dòng (P3)

**Goal**: sửa `say`, làm lại một dòng, đổi giọng/tốc độ có xác nhận; lời luôn từ kịch bản.

**Independent Test**: quickstart mục 5 (phần giọng).

- [ ] T037 [P] [US3] Test trong `tests/filmcheck/test_voicemake.py`: `voice make --only L03` chỉ đổi `voices/L03.wav` (mtime các tệp khác giữ nguyên) và gộp `dur.json` (giữ khoá các dòng khác); `STUDIO_TTS_DRY` in lệnh với tệp tạm một dòng
- [ ] T038 [US3] `voice make --only` trong `tools/filmcheck/cli.py` theo research R8 (thư mục tạm, chép `wav`, gộp `dur.json`); `voice asr --only` gộp mốc từ của dòng
- [ ] T038a [US3] `voice make --changed` trong `tools/filmcheck/cli.py`: `voices/.made.json` ghi mỗi dòng `{text|say, voice, speed}` lúc tạo; `--changed` chỉ làm lại dòng khác hoặc thiếu `wav`; test trong `tests/filmcheck/test_voicemake.py`: đổi chữ 2 dòng → đúng 2 dòng làm lại (SC-004); `CLAUDE.md` dùng `voice make --changed` sau khi duyệt lại Script
- [ ] T039 [P] [US3] Test trong `tests/filmcheck/test_edit.py`: `voice-say L03 --say "R. E. M."` ghi `say`, `text` giữ nguyên; > 400 ký tự → mã 2; `voice-set voice=xx_fake` → mã 2; `voice-set` thiếu `--confirm all` → mã 2; tốc độ 1.5 → mã 2
- [ ] T040 [US3] Thao tác `voice-say`, `voice-remake`, `voice-set` trong `tools/filmcheck/edit.py` (giọng kiểm bằng `channels.voice_ok`, tốc độ [0.7, 1.3])
- [ ] T041 [P] [US3] Test trong `tests/filmcheck/test_voice.py`: `qc voice` báo lỗi khi chữ một dòng `lines.json` khác `SCRIPT.md` (FR-007)
- [ ] T042 [US3] Thêm phép so lời–kịch bản vào `tools/filmcheck/voicecheck.py` (dùng lại hàm so của `qc.py`)
- [ ] T043 [US3] Khung Voice trên trang (`web/app.js`): giọng và tốc độ (ô chọn từ `voices`, đổi thì hỏi xác nhận ngay trên trang "remakes all N lines"), mỗi dòng có nút nghe (`/files/voices/…`), chữ (không sửa được), ô `say`, kết quả tầng 0 của dòng, "Remake line"; lọc "With say or warnings"
- [ ] T044 [US3] Điểm voice trong `CLAUDE.md` (bước 3b, sau tầng 0) và `tools/runner/agent.py`

---

## Phase 6: User Story 4 — Chọn nhạc và mức tiếng (P4)

**Goal**: chọn nhạc theo seed hoặc không nhạc, chỉnh mức trong dải, trộn lại không dựng lại hình.

**Independent Test**: quickstart mục 5 (phần trộn).

- [ ] T045 [P] [US4] Test trong `tests/filmcheck/test_edit.py`: `mix under=-40` → mã 2 (ngoài dải của `template.json` ± 3 dB); `music=seed:2` ghi `mix.json`; dấu `all` không đổi sau khi đổi `mix.json`
- [ ] T046 [US4] `my-styles/dusk-hypothetical/kit/sound/mix.py` đọc `mix.json` (`music` seed hoặc `none`, `music_under_voice_db`, `music_between_db`, `sfx_db`); không có tệp thì như cũ; test nhỏ trong `my-styles/dusk-hypothetical/kit/test/` hoặc `tests/filmcheck/test_kit.py`
- [ ] T047 [US4] Thao tác `mix` trong `tools/filmcheck/edit.py`: kiểm dải (research R11), ghi `mix.json`, chạy `mix.py` bằng Python của thư viện (`cd $LIB && .venv/bin/python <phim>/kit/sound/mix.py <phim>`), nếu có `out/video.mp4` thì ghép lại bằng `$LIB/core/render/mux.sh`
- [ ] T048 [US4] Khung Mix trên trang (`web/app.js`): các lựa chọn nhạc từ `mix_ranges.music`, bốn thanh trượt trong dải, máy nghe bản trộn, ghi "does not redraw the picture"
- [ ] T049 [US4] Điểm mix trong `CLAUDE.md` và `tools/runner/agent.py`

---

## Phase 7: User Story 5 — Chọn tiêu đề và thumbnail (P5)

**Goal**: chọn tiêu đề chính, sửa mô tả và hashtag, kiểm lại gói đăng.

**Independent Test**: với phim đã có gói đăng, chọn tiêu đề 2, sửa hashtag, `publish --check-only` đạt.

- [ ] T050 [P] [US5] Test trong `tests/filmcheck/test_publish.py`: `pack.json` có `chosen: 2` → `PUBLISH.md` xếp tiêu đề 2 lên đầu; `chosen: 4` → lỗi; thao tác `publish hashtags=a,b` (2 hashtag) → mã 2
- [ ] T051 [US5] `chosen` trong `tools/filmcheck/publish.py` và `specs/011-publish-pack/contracts/files.md`; thao tác `publish` trong `tools/filmcheck/edit.py`
- [ ] T052 [US5] Khung Publish trên trang (`web/app.js`): ba tiêu đề kèm thumbnail (đường `/films/<tên>/publish/<tệp>` hiện có), chọn một, ô mô tả, ô hashtag, kết quả kiểm
- [ ] T053 [US5] Điểm publish trong `CLAUDE.md` và `tools/runner/agent.py`

---

## Phase 8: Online, app và hoàn thiện

- [ ] T054 Worker chạy thao tác online (`tools/runner/worker.py`): lấy `action` `queued` của việc `waiting_review`, chạy `sh bin/studio edit … --json` trong container của việc (cùng ảnh, cùng thư mục phim, không proxy Claude, không trừ hạn mức), ghi trạng thái và nhật ký; container dừng khi hết thao tác; `actions.create` online không chạy luồng local
- [ ] T055 [P] Test `tests/online/test_actions.py` (phần còn lại): thao tác online chạy bằng `RUNNER=local` không có biến proxy; lượt gọi Claude của việc không tăng; hai thao tác cùng việc chạy tuần tự
- [ ] T056 [P] `job start --points script,shots` trong `tools/studio/studio_cli.py` (ghi `reviews.on` khi có thư mục phim); trang "Make a film" (online) có 5 ô đánh dấu theo mặc định kênh; trang kênh trên giao diện có 5 ô `reviews` (`tools/studio/studio/api_online.py` và `web/app.js`)
- [ ] T057 [P] Test Playwright trong `tests/ui/` (theo cách test 025): mở trang việc của phim mẫu, thanh có 10 bước và 2 nhãn `REVIEW`, sửa đoạn P3 → nhật ký có `Edit script-para P3`, cột "If you change this" có 7 bước, nút duyệt khoá rồi mở
- [ ] T058 [P] MCP `answer_review` nhận `base` tuỳ chọn (`tools/studio/studio/mcp_server.py`); công cụ MCP `film_steps(job_id)` gọi `/steps`
- [ ] T059 Cập nhật `CLAUDE.md` (mục 5 "Ghi việc lên giao diện": điểm duyệt, `point`, `edit`; mục Cấu trúc: `points.py`, `steps.py`, `edit.py`, `actions.py`) và `specs/003-studio-ui/contracts/skill-integration.md` (năm loại duyệt mới)
- [ ] T060 Chạy năm bộ test (`sh tests/run.sh`, `sh tests/render/run.sh`, `sh tests/ui/run.sh`, `sh tests/filmcheck/run.sh`, `sh tests/online/run.sh`) và `node --test desktop/test/*.test.js`; ghi kết quả
- [ ] T061 Thử thật SC-006: một phim 5 phút bằng chat với ít nhất một lần sửa ở Script và một lần ở Shots trên trang, không dựng hình lại; đo SC-001 (thời gian điểm mới, ảnh mới); ghi kết quả vào `quickstart.md`

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → các story.
- US1 (Phase 3) chỉ cần Phase 2. US2 cần Phase 2 (độc lập US1, nhưng nên làm sau MVP). US3, US4, US5 cần Phase 2, độc lập nhau.
- T054–T055 (online) cần T012 và T023. T057 cần T015 và T021.
- Trong mỗi story: test → lõi (`edit.py`/cổng) → trang → hướng dẫn agent → thử thật.

## Parallel Opportunities

- Phase 2: T003, T005, T007, T010 song song (khác tệp); T014 sau T013.
- US1: T017 và T019 song song; T021 song song với T022–T023 khi T018 xong.
- US2: T026, T028, T029, T032 song song.
- US3–US5: có thể chia cho ba người sau Phase 2.

## Implementation Strategy

1. **MVP**: Phase 1 + 2 + US1 → kiểm chứng (quickstart 1–2) → commit → báo người dùng.
2. US2 (lợi nhất sau MVP: chặn dựng hình khi cảnh chưa duyệt) → commit.
3. US3, US4, US5 theo thứ tự → commit sau mỗi story.
4. Phase 8 (online, app, test trình duyệt, thử thật) → `/speckit-converge`.
