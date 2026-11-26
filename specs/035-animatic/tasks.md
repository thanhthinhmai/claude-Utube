# Tasks: Điểm duyệt Animatic cho phim After Effects

**Input**: Design documents from `specs/035-animatic/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (cli.md, api.md, files.md), quickstart.md

**Tests**: Có. Hiến pháp IV bắt buộc test tự động cho logic quan trọng; mỗi story có test viết trước phần code.

**Organization**: theo user story của spec.md (US1, US2: P1; US3: P2).

**Điều kiện bắt đầu code**: 034 đã commit đủ phần đang dở (`castnotes.py`, ghim trên trang) và worktree này đã rebase lên đó (T001). US3 cần điều này; US1, US2 chỉ cần 034@049bc60.

## Phase 1: Setup

- [X] T001 Rebase nhánh `035-animatic` lên commit mới nhất của `034-cast-review`; khi 036 đã merge vào `main`, rebase tiếp lên `main` (036 cũng sửa `filmsteps.py`, `cli.py`, `app.js`: gỡ conflict rồi chạy lại test của cả 034, 036). Chạy `sh tests/filmcheck/run.sh` và `sh tests/ae/run.sh` để có mốc đạt trước khi sửa
- [X] T002 [P] Chép dữ liệu thử của `films/ae-sleepless-test` (`film.json`, `narration.json`, `lines.json`, `voices/dur.json`, một `words.json` dựng từ Whisper, `out/build-shots.json`) vào `tests/filmcheck/data/animatic-sleepless/` (không chép `.wav`; test tự tạo tệp giọng im lặng đúng độ dài từ `dur.json`)

## Phase 2: Foundational (chặn mọi story)

- [X] T003 [P] Test `tests/filmcheck/test_timing.py`: đọc/ghi `timing.json` (`version` 1, `frames` đủ mọi shot của `film.json → shots`, "mỗi giá trị ≥ 6 khung"), `t0/t1` dẫn xuất, `history` "tối đa 50", `origin`; ghi nguyên tử dưới `timing.lock`; tạo `timing.json` từ `shots_<proj>.json` khi chưa có (contracts/files.md "Chuyển phim cũ")
- [X] T004 Viết `tools/filmcheck/timing.py` theo data-model "Thời lượng shot" và research R1: `load(d)`, `save(d, doc)`, `bounds(doc) → [{id,t0,t1}]`, `from_marks(d, shots_json)`, `start(d)` (ghi `origin` một lần), khoá `timing.lock`
- [X] T005 [P] Test `tests/filmcheck/test_timing.py` (tiếp): `lines(d)` gán câu vào shot chứa phần lớn [at, end] (R2), câu kéo qua đường cắt; `shift(d, new_frames)` dời `narration.json → lines[].at` giữ khoảng cách tới đầu shot (`at_mới = t0_mới + (at_cũ − t0_cũ)`), ghi cùng lúc với `timing.json`
- [X] T006 Thêm `lines(d)` và `shift(d, new_frames)` vào `tools/filmcheck/timing.py` (R2), đọc `narration.json`, `voices/dur.json`, `words.json` qua `qc.py` sẵn có
- [X] T007 Điểm `animatic` trong `tools/filmcheck/points.py`: thêm vào `POINTS`, `STEP`, `AE_ON`; phim AE ẩn điểm `shots` (trạng thái `skipped`, lý do "AE films review the animatic"); `fingerprint(d, "animatic")` theo R11 (`timing.json → frames` + `narration.json` + ghi chú mở + `ae/*.jsx` + `cast/cast.json`); `reached()` = giọng đã duyệt hoặc tắt
- [X] T008 Bước "Animatic" trong `tools/filmcheck/steps.py`: `STEPS` thêm "Animatic" sau "Voice"; `POINT_STEP["animatic"]`; `GRAPH`: Voice → Animatic, Cast → Animatic, Animatic → Mix, Render; phim AE ẩn Look, Picture, Shots; phim web ẩn Animatic; phim AE hiện bước Mix với tên "Sound" và Render với tên "Final render" (thêm trường `label` cho mỗi bước, tên điểm duyệt vẫn là `mix`; 034 chưa có hai tên này); `base_states` cho Animatic: `todo|done|stale` theo `animatic/draft.json` (data-model "Bước Animatic")
- [X] T009 [P] Test `tests/filmcheck/test_steps.py` và `tests/filmcheck/test_points.py` (sửa): thứ tự bước phim AE = Script, Cast, Voice, Animatic, Mix, Render, Self-check, Publish; phim web không đổi; `impact("animatic")` = Mix, Render, Self-check, Publish (FR-004); đổi giọng/kịch bản/nhân vật → Animatic `stale` (FR-005)
- [X] T010 [P] `CU.shotFrames(id)` và `CU.keyScan(comp)` trong `tools/ae/kit/lib.jsx` (ES3; `keyScan` đệ quy `PropertyGroup`, chỉ thuộc tính `numKeys ≥ 2`, trả `[{layer, prop, t0, t1}]` theo giây trong comp); `tools/ae/bundle.py` gói `timing.json` thành `data/timing.json`
- [X] T011 `tools/ae/kit/build_core.jsx`: sau mỗi shot gọi `CU.keyScan` và ghi `keys_<proj>.json`; khi chưa có `timing.json`, `tools/ae/cli.py` (build/render) ghi nó từ `shots_<proj>.json` qua `timing.from_marks`
- [X] T012 [P] Test `tests/ae/test_keys.py`: `bundle.make` có `data/timing.json` khi phim có tệp; entry.jsx không đổi khi không có; đọc một `keys_<proj>.json` mẫu thành `animatic/keys.json`
- [X] T013 Chuyển phim thử: `films/ae-sleepless-test/ae/shots.jsx` lấy `CU.FR[n]` từ `CU.shotFrames("S"+n) || <giá trị cũ>`; `films/ae-sleepless-test/mix.py` đọc `FRAMES` từ `timing.json` (phim không vào git: ghi thay đổi vào `tools/ae/ANIMATIC.md` mục "Chuyển phim cũ" để làm lại được)

**Checkpoint**: thời lượng có một nguồn; điểm và bước Animatic hiện đúng; test đạt.

## Phase 3: User Story 1 - Xem bản nháp có giọng và duyệt nhịp (P1) 🎯 MVP

**Goal**: bản nháp ¼ độ phân giải có giọng thật, dải thời gian, phần trăm lặng, duyệt và cổng bản đẹp.

**Independent Test**: với `ae-sleepless-test` đã có giọng duyệt, bước Animatic có bản nháp phát được, dải 9 shot và 14 câu, silence khớp bước kiểm phim (≤ 1 điểm), duyệt được; `ae render` bị chặn khi chưa duyệt.

### Tests

- [X] T014 [P] [US1] Test `tests/filmcheck/test_animatic.py`: `animatic.timeline(d)` trả `shots[{id,t0,t1,lines[]}]`, `duration`; `animatic.silence(d)` bằng đúng `rhythm.measure(...)["silence_ratio"]` trên cùng dữ liệu (R4), giới hạn `rhythm.SILENCE_MAX`; các khoảng lặng dài nhất (top 3) khi > 0,20
- [X] T015 [P] [US1] Test `tests/filmcheck/test_points.py` (tiếp): `point approve animatic` khi silence > 0,20 mà không `--anyway` → mã 1 lý do "silence 25% > 20%: approve anyway?"; có `--anyway` → bản duyệt có `anyway: true, silence` (data-model "Điểm duyệt"); `--anyway` khi có biến môi trường `STUDIO_JOB` (chạy trong một việc) → mã 1 "only the owner can approve anyway, on the job page"; `gate(d, "animatic")` chặn khi chưa duyệt (FR-003)
- [X] T016 [P] [US1] Test `tests/ae/test_draft.py`: `bundle.make(..., draft=True)` đặt `CU.DRAFT = true` và tên `draft.mp4`; trộn giọng tạm từ `narration.json` ra đúng độ dài và mốc (ffmpeg, tệp im lặng + tiếng bíp ở mốc câu); cắt `clips/S*.mp4` và `frames/S*.jpg` theo `timing.json`; `draft.json` có `frames, narration_sha, built_at, shots_built, seconds, fps, size`; giữ đúng một `draft.prev.mp4`

### Implementation

- [X] T017 [US1] Viết `tools/filmcheck/animatic.py`: `timeline(d)`, `silence(d)` (dùng `qc.py` + `rhythm.clamp_words` + `rhythm.measure` với `shots` từ `timing.bounds`), `longest_gaps(d, n=3)`, `draft_current(d)` (so `draft.json` với `timing.json` và băm `narration.json`)
- [X] T018 [US1] Cờ draft trong `tools/ae/kit/build_core.jsx`: khi `CU.DRAFT`, `MASTER.resolutionFactor = [4,4]`, render item `setSettings({"Quality":"Draft","Resolution":[4,4],"Motion Blur":"Off for all layers"})`, nếu không có `setSettings` thì `applyTemplate("Draft Settings")` (R6); tệp ra `draft.mp4`
- [X] T019 [US1] Viết `tools/ae/draft.py` (R6, R8): dựng qua `local.build`/`remote.build` với `draft=True`, trộn giọng tạm bằng ffmpeg (`adelay` + `amix`, −16 LUFS), ghép vào video, cắt clip và khung từng shot, ghi `animatic/draft.json`, chép `keys_<proj>.json` → `animatic/keys.json`, giữ `draft.prev.mp4`
- [X] T020 [US1] Lệnh `ae draft <phim> [--shots …]` trong `tools/ae/cli.py` (contracts/cli.md): mã 3 khi giọng chưa duyệt (điểm voice bật) hoặc AE chưa sẵn sàng; in `… S2 (1/2)`, dòng cuối `draft: <giây> s · silence <x>%`; `ae render` gọi `points.gate(d, "animatic")` (mã 3, kèm lệnh duyệt)
- [X] T021 [US1] Lệnh `animatic status|start <phim> [--json]` và `point approve <phim> animatic [--anyway]` trong `tools/filmcheck/cli.py`; `points.approve` nhận `anyway` (FR-010), CLI từ chối `--anyway` khi có `STUDIO_JOB` (chỉ giao diện app đặt được `anyway`); `bin/studio` chuyển `animatic …` tới filmcheck
- [X] T022 [US1] API: `GET /jobs/{id}/steps` thêm khối `animatic` (contracts/api.md, chưa có `fit`/`notes`), cho phép `files/animatic/{draft.mp4,draft.prev.mp4,clips/*,frames/*}` có `Range`, quyết định `approve` kind `animatic` với `anyway` (422 `needs_anyway`) trong `tools/studio/studio/filmsteps.py`, `server.py`, `reviews.py`
- [X] T023 [US1] Khung Animatic trong `tools/studio/studio/web/app.js` và `style.css` theo bản mẫu: dải thời gian (hàng shot theo thời lượng, hàng câu, chú giải), nhãn "Silence x% · limit 20%" (màu cảnh báo khi vượt, đánh dấu khoảng lặng dài nhất), tổng thời lượng, trình phát `draft.mp4`, lưới shot (khung, tên, thời lượng, lời), cột "How Animatic works" và "If you change this" (Sound, Final render), nút Approve và hộp "Approve anyway"; thanh bước dùng `label` của bước (phim AE: "Sound", "Final render")
- [X] T024 [P] [US1] Test `tests/ui/test_animatic_api.py`: khối `animatic` của `/jobs/{id}/steps`, tải tệp bản nháp có `Range`, `approve` cần `anyway` khi silence > 0,20
- [X] T025 [US1] Bước Animatic trong việc làm phim AE: `tools/runner/agent.py` và `tools/runner/JOB.md` (sau Voice: `animatic start`, `ae draft`, gửi yêu cầu duyệt kind `animatic`, chờ; khi điểm Animatic tắt: vẫn `ae draft` và báo phần trăm lặng nhưng không dừng chờ; **cấm** dùng `--anyway` hay tự duyệt); `.claude/skills/film-make/SKILL.md` mục "Phim After Effects" và `tools/ae/ANIMATIC.md` (mới)

**Checkpoint**: US1 chạy độc lập; quickstart mục 2 và 5 đạt.

## Phase 4: User Story 2 - Khớp shot theo lời, từng shot (P1)

**Goal**: đề xuất cắt/kéo theo từng shot, nhận/bỏ/nhận hết, Undo, báo chuyển động bị ảnh hưởng, dựng lại chỉ shot đổi.

**Independent Test**: với dữ liệu `ae-sleepless-test`, nhận hết → silence ≤ 0,20 và mỗi shot có lời kết thúc 0,25 s ± 1 khung sau từ cuối, câu đầu ở đường cắt; bỏ S9 thì S9 giữ nguyên; Undo trả về đúng byte.

### Tests

- [X] T026 [P] [US2] Test `tests/filmcheck/test_animatic.py` (tiếp, R3): `fit(d)` cho shot có câu với |end_đích − end_hiện| > 1 khung (`end_đích` = từ cuối − head + 0,25 s, làm tròn khung; head > 1 khung cũng là một đề xuất); shot không câu → không đề xuất; shot ngắn hơn câu → `delta_s` dương; shot mới < 1 s → `very_short`; không đề xuất nào cắt trước từ cuối của shot
- [X] T027 [P] [US2] Test `tests/filmcheck/test_animatic.py` (tiếp): `accept(d, ["S2"])` chỉ đổi S2, shot sau dời, câu dời theo (R2), một mục `history`; `accept(d, "all")` → silence ≤ 0,20 trên dữ liệu thử (SC-002); `skip(d, "S9")` ghi `skipped_for`, đề xuất S9 hết hiện, hiện lại khi lời hoặc thời lượng S9 đổi (FR-013); `undo(d)` trả `timing.json` và `narration.json` về đúng byte; undo tại `origin` → lỗi mã 1 (FR-015); `--base` lệch → mã 4
- [X] T028 [P] [US2] Test `tests/filmcheck/test_animatic.py` (tiếp, R5): với `keys.json` mẫu, bớt làm chuyển động `t0 ≥ end_mới` → `drop`; `t0 < end_mới < t1` → `squeeze` kèm `ratio` = (t1 − t0)/(end_mới − t0), `clip` khi tỉ lệ > 2; tên hiện "layer · prop"
- [X] T029 [P] [US2] Test `tests/ae/test_draft.py` (tiếp, R7): `splice.by_shot()` ghép shot dựng lại vào bản nháp khi thời lượng shot trước đã đổi; khung các shot không dựng lại giống hệt bản cũ (`framemd5` theo shot)

### Implementation

- [X] T030 [US2] `fit`, `accept`, `skip`, `undo` trong `tools/filmcheck/animatic.py` (data-model "Đề xuất khớp shot": `animatic/fit.json` chỉ giữ `skipped`), dùng `timing.shift`; `motions` từ `animatic/keys.json` (R5)
- [X] T031 [US2] `splice.by_shot(old_video, old_bounds, new_bounds, pieces)` trong `tools/ae/splice.py`; `tools/ae/draft.py` dùng nó khi có `--shots`, và tự thêm vào danh sách dựng mọi shot đổi thời lượng (FR-016)
- [X] T032 [US2] Lệnh `animatic fit|accept|skip|undo` trong `tools/filmcheck/cli.py` (contracts/cli.md, `--base`, `--json`, in silence mới sau mỗi lệnh)
- [X] T033 [US2] API `POST /jobs/{id}/actions` `point: "animatic"`, `op: fit_accept|fit_skip|fit_undo|draft_rebuild` với `timing_base` (409 `changed`), sau `fit_*` xếp `ae draft --shots <shot đổi>`; khối `animatic` thêm `fit`, `can_undo`, `building` trong `tools/studio/studio/actions.py`, `filmsteps.py`
- [X] T034 [US2] Giao diện đề xuất trong `tools/studio/studio/web/app.js`: mỗi shot một dòng "S2: −1,1 s → lines start at the cut, ends 0.25 s after its last line" với Accept/Skip, "Accept all", dòng kết quả "Each shot now ends 0.25 s after its last line." kèm Undo, cảnh báo "very short shot", danh sách chuyển động bị mất/dồn và câu "Accepting cuts the motion; pin a note to have Claude retime it" (R5 ghi chú, FR-014: nhận không tự dồn); dải thời gian, nhãn lặng, tổng thời lượng cập nhật ngay; trạng thái "Rebuilding S2, S6…"
- [X] T035 [P] [US2] Test `tests/ui/test_animatic_api.py` (tiếp): `fit_accept`, `fit_skip`, `fit_undo`, base lệch → 409, xếp dựng lại đúng các shot đổi
- [X] T036 [US2] Bản đẹp dùng cùng thời lượng: `ae render` dựng theo `timing.json`; test `tests/ae/test_keys.py` (tiếp): `shots.json` của bản đẹp (từ `shots_<proj>.json` mẫu) trùng `timing.bounds` ± 1 khung (FR-017, SC-004); Mix đọc `narration.json` đã dời (ghi rõ trong `tools/ae/ANIMATIC.md`)

**Checkpoint**: US1 + US2 = MVP; quickstart mục 3 đạt.

## Phase 5: User Story 3 - Phát từng shot và ghim ghi chú (P2)

**Goal**: phát clip từng shot, ghim ghi chú, "Send notes to Claude" chỉ dựng lại shot có ghi chú.

**Independent Test**: ghim một ghi chú trên S2 và một ghi chú chung cho S6, gửi: chỉ S2, S6 dựng lại (shot khác giống hệt từng điểm ảnh), mỗi ghi chú có trả lời, trang tự hiện bản nháp mới.

**Cần**: 034 đã commit `castnotes.py` (T001).

### Tests

- [X] T037 [P] [US3] Test `tests/filmcheck/test_pins.py`: phần ghim dùng chung (đọc/ghi theo `base`, `x, y` ∈ [0, 100], ghi chú chung `frame: null`, lô, trả lời, ghi chú thêm khi lô đang chạy có `lot: null` và chờ lô sau); `tests/filmcheck/test_castnotes.py` của 034 vẫn đạt
- [X] T038 [P] [US3] Test `tests/filmcheck/test_animatic.py` (tiếp): `animatic/notes.json` khoá theo shot, `at` ∈ [0, độ dài shot], ghi chú mở làm đổi vân tay animatic (Animatic về chưa duyệt, FR-021); lượt thất bại giữ ghi chú mở (FR-022)

### Implementation

- [X] T039 [US3] Trước khi làm, nhắn session 034 (ListAgents/SendMessage) để chắc `castnotes.py` không còn đang sửa. Tách phần ghim của `tools/filmcheck/castnotes.py` thành `tools/filmcheck/pins.py` (R9), `castnotes.py` gọi lại không đổi hành vi
- [X] T040 [US3] Sổ ghi chú animatic trong `tools/filmcheck/animatic.py` dùng `pins.py`; lệnh `animatic notes add|delete|show|reply` trong `tools/filmcheck/cli.py` (contracts/cli.md)
- [X] T041 [US3] API: `op: note_add|note_delete` với `notes_base`; quyết định `revise` kind `animatic` (note tự điền "N notes on: S2, S6"); `POST /films/{film}/animatic/fix` tạo việc `fix` `input.target="animatic"`, `input.shots` (409 `ae_unavailable`) trong `tools/studio/studio/actions.py`, `reviews.py`, `server.py`
- [X] T042 [US3] Việc `fix` `target: "animatic"` và quyết định `revise` trong `tools/runner/agent.py`, `tools/runner/JOB.md`: sửa mã các shot có ghi chú, `ae draft --shots …`, trả lời từng ghi chú, không duyệt; xong → Animatic `waiting`
- [X] T043 [US3] Giao diện trong `tools/studio/studio/web/app.js`, `style.css`: bấm shot phát `clips/S*.mp4`; dừng ở khung rồi bấm → ghim có số (phần trăm + mốc giây), ô ghi chú chung, xoá; "Send notes to Claude"; trạng thái việc sửa đang chạy; tự tải lại bản nháp và câu trả lời khi xong; lỗi + "Send again" khi lượt thất bại
- [X] T044 [P] [US3] Test trình duyệt `tests/ui/browser_animatic.cjs`: ghim lệch ≤ 2% chiều rộng khung ở 1280 px và 400 px (SC-007); gửi ghi chú tạo đúng một yêu cầu với đúng các shot

**Checkpoint**: cả ba story chạy; quickstart mục 4 đạt.

## Phase 6: Polish & kiểm chứng thật

- [X] T045 Chạy đủ `sh tests/run.sh`, `sh tests/filmcheck/run.sh`, `sh tests/ae/run.sh`, `sh tests/ui/run.sh`, `sh tests/online/run.sh`; ghi kết quả
- [X] T046 Lượt AE thật trên `ae-sleepless-test` theo `quickstart.md` mục 2–5: ghi thời gian bản nháp so với bản đẹp (SC-001), silence trước/sau (SC-002), silence của `qc final` (SC-003), mốc cắt bản đẹp (SC-004), so điểm ảnh sau một lượt ghi chú (SC-005); ghi vào `specs/035-animatic/quickstart.md` mục "Kết quả"
- [X] T047 [P] Cập nhật `tools/CLAUDE.md` (lệnh `ae draft`, `animatic …`), `CLAUDE.md` gốc mục "Phim After Effects" (một dòng: bước Animatic), `tools/ae/ANIMATIC.md`

## Dependencies & Execution Order

- Setup (T001–T002) → Foundational (T003–T013) → US1 (T014–T025) → US2 (T026–T036) → US3 (T037–T044) → Polish.
- US2 cần US1 (bản nháp, `animatic.py`, khung giao diện). US3 cần US1 và 034 đã commit `castnotes.py`; độc lập với US2.
- Trong mỗi story: test trước, rồi `filmcheck` → `ae` → CLI → API → giao diện → agent.

## Parallel Opportunities

- Foundational: T003, T005, T009, T010, T012 song song (khác tệp).
- US1: T014, T015, T016 song song; T024 song song với T023.
- US2: T026–T029 song song; T035 song song với T034.
- US3: T037, T038 song song; T044 song song với T042.

## Implementation Strategy

- **MVP = US1 + US2**: đủ để sửa lỗi lặng của phim thử trước bản đẹp. Dừng kiểm theo quickstart mục 2, 3, 5 trước khi làm US3.
- US3 làm khi 034 đã commit phần ghim; nếu 034 còn đổi `castnotes.py`, giữ T039 ở cuối.
- Merge sau 034 và 036; rebase lại trước PR.

## Phase 7: Convergence

- [X] T048 Đề xuất khớp shot không rút shot chứa lời cuối của một đoạn xuống dưới `rhythm.KEY_SHOT` (2,5 s, cùng hằng số với `qc final`); phần dư thành lặng cuối đoạn, ghi lý do trong đề xuất; sửa `tools/filmcheck/animatic.py` (`fit`), câu chữ FR-011/SC-002 trong `specs/035-animatic/spec.md` (quyết định người dùng 2026-11-26), test trong `tests/filmcheck/test_animatic.py`; chạy lại khớp trên `ae-sleepless-test` và xác nhận `qc final` không còn lỗi shot cuối đoạn per FR-011, SC-002 (partial)
- [ ] T049 Đo từng bước của `ae draft` (AE dựng, `splice.segment`, `splice.by_shot`, `voice_track`, mux, `cut` clip và ảnh) rồi bỏ việc mã hoá thừa, chạy song song phần cắt clip/ảnh trong `tools/ae/draft.py` (và `tools/ae/splice.py` nếu cần), giữ nguyên kết quả (framemd5 từng shot) để bản nháp cả phim nhanh hơn ≥ 3 lần bản đẹp trên `ae-sleepless-test` (bản đẹp 87,7 s); ghi số đo mới vào `quickstart.md` mục "Kết quả" per SC-001 (partial)
- [ ] T050 Chạy một lượt "Send notes to Claude" thật trên `ae-sleepless-test` (app chạy, việc `fix` target `animatic`, Opus 5.5; hỏi người dùng trước vì tốn tiền): 100% ghi chú có câu trả lời, chỉ shot có ghi chú được dựng lại; ghi vào `quickstart.md` mục "Kết quả" per SC-005 (partial)
- [ ] T051 Tìm bài trong `sh tests/ae/run.sh` đã tạo thư mục `ae-…` của phim giả `f1` trong thư mục làm việc AE thật (`/mnt/e/claude-utube-ae/work`, 2026-11-26 09:57) dù đặt `STUDIO_AE_WORK`; cho mọi test dùng thư mục tạm per Constitution (test không đụng dữ liệu người dùng) (contradicts)
