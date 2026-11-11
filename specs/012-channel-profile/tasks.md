# Tasks: Hồ sơ kênh và tệp bài học

**Input**: `specs/012-channel-profile/` (spec.md, plan.md, research.md, data-model.md, contracts/cli.md, contracts/files.md, contracts/api.md, quickstart.md). Tính năng này xây trên 010 (`script check`, biên tập, `qc`), 011 (`publish`) và 007–009 (việc online, `store.root()`, trang việc).

**Tests**: có. SC-002, SC-003, SC-005 và SC-006 cần test tự động. Phim mẫu và kênh mẫu được tạo trong test, ở `tests/filmcheck/.tmp/` và `tests/online/.tmp/`.

**Luật chung cho mọi task**:
- Không sửa `lib/`. Không clone giọng. Chữ in ra màn hình bằng tiếng Anh, ngắn.
- Phim không có `channel.json` phải chấm y như trước. Không được sửa test của 010 và 011 để chúng đạt.
- Sau mỗi phase, 5 bộ test phải đạt. Commit sau mỗi phase.

## Phase 1: Setup

- [X] T001 [P] Thêm `channel` và `lesson` vào `case` của `bin/studio` (chuyển tới `cmd_filmcheck`) và thêm dòng `usage`. Trong `tools/filmcheck/cli.py`, thêm parser cho các lệnh của contracts/cli.md, tạm thời trả mã 2 với dòng "not built yet". Tạo `tools/filmcheck/channels.py` có docstring trỏ tới specs/012.
- [X] T002 [P] Trong `tests/filmcheck/samples.py`, thêm `make_channel(root, slug="khoa-hoc-vui", **over)` (ghi `channels/<slug>/channel.json` hợp lệ với `language` = `"en"`, `seconds` = 50, `style` = `"test-style"`, `hashtags` = `["#honey"]`, `banned` = `["shocking"]`, `title_max` = 70, `voice` = `"af_bella"`, `speed` = 1.0) và `make_lesson(root, scope, rule, status="active")`.

## Phase 2: Foundational

- [X] T003 Trong `tools/filmcheck/channels.py`, viết phần đọc, kiểm và ghi theo data-model.md và R1:
  - `root_dir()` (= `STUDIO_ROOT` hoặc gốc truyền vào), `shared_file(root, online=False)`;
  - `validate(ch) -> list[str]`, kiểm mọi luật của bảng Channel, gồm "không có hashtag nào nằm trong `banned`", phong cách tồn tại (`my-styles/<s>/style.json` hoặc `lib/lemo-opuscar/styles/<s>/`) và dạng tên giọng của R7;
  - `load(root, slug)`, `save(root, ch)` (ghi tệp tạm rồi đổi tên; viết lại `CHANNEL.md` và `channels/README.md`), `list_channels(root)`;
  - `load_lessons(path)`, `save_lessons(path, data, title)` (viết lại `LESSONS.md`);
  - `parse_rule(rule) -> (kind, value) | None` cho `phrase:` (1–80 ký tự), `max_sentence_words:` (5–60) và `max_title_chars:` (20–100);
  - `find_banned(text, words, cjk) -> list[(word, start)]`: chữ thường, NFC, trọn từ, hoặc chuỗi con với chữ CJK (R3).
- [X] T004 Trong `tests/filmcheck/test_channels.py::Store`, viết test cho T003:
  - mã sai, mã trùng, hashtag nằm trong `banned`, giọng dạng đường dẫn tệp → lỗi;
  - lưu rồi đọc lại giống hệt; `CHANNEL.md` có tên kênh; `README.md` có một dòng cho kênh;
  - `find_banned("sốt", ["sốc"])` = []; `find_banned("Thật SỐC!", ["sốc"])` có 1 chỗ.

## Phase 3: User Story 1 - Làm phim theo hồ sơ kênh (P1) 🎯 MVP

**Goal**: hồ sơ kênh, bản chụp trong thư mục phim, và các luật kênh trong `script check`, `publish`, `qc`, biên tập.

**Independent Test**: tạo kênh mẫu, `channel attach` một phim mẫu. Kết quả cần thấy: `script check` trượt `channel_language` và `banned_word` đúng chỗ; `publish` trượt `channel_hashtags`, `channel_banned`, `channel_title_max`; `qc` trượt `channel_voice`. Bỏ `channel.json` thì cả 3 máy chấm cho kết quả như cũ.

### Tests for User Story 1

- [X] T005 [P] [US1] Trong `tests/filmcheck/test_channels.py::Rules`, viết một test cho mỗi mã của contracts/cli.md (`channel_language`, `banned_word`, `channel_hashtags`, `channel_banned`, `channel_title_max`, `channel_voice`). Mỗi test sửa đúng một thứ trên phim mẫu đạt (`samples.make_publish_film` + `channel attach`) và kiểm chỉ đúng mã đó trượt. Phim mẫu đạt có kênh: 0 lỗi kênh. Thêm `test_no_snapshot_no_change`: cùng phim đó không có `channel.json` thì `script.check`, `publish.check` và `qc.measure` cho cùng kết quả như khi chưa có tính năng (SC-006).
- [X] T006 [P] [US1] Trong `tests/filmcheck/test_channels.py::Snapshot`, viết test cho `attach`:
  - giá trị riêng của phim thắng giá trị của hồ sơ;
  - `voice_override` là `true` khi phim chọn giọng khác;
  - `CHANNEL_BRIEF.md` ≤ 6000 ký tự, kể cả khi có 200 bài học dài;
  - khi bị cắt: dòng cuối "(N lessons not shown", bài học có luật máy được giữ trước;
  - chỉ bài học `active` và luật hợp lệ vào `channel.json`.

### Implementation for User Story 1

- [X] T007 [US1] Trong `tools/filmcheck/channels.py`, viết `attach(root, film_dir, slug, shared_path, **override) -> dict` theo R2: viết `channel.json` và `CHANNEL_BRIEF.md` (theo thứ tự: hồ sơ, quyết định, bài học có luật, bài học còn lại mới nhất trước; cắt ở 6000 ký tự) và trả cảnh báo khi bị cắt. Phong cách hay giọng của kênh (sau khi áp giá trị riêng) không còn hợp lệ thì báo lỗi và không viết gì (edge case của spec). Thêm `snapshot(film_dir) -> dict | None`.
- [X] T008 [US1] Trong `tools/filmcheck/cli.py`, viết các lệnh `channel list|new|show|set|decide|attach` theo contracts/cli.md (`--json` cho list và show). `set` hỗ trợ `--add` và `--remove` cho `hashtags` và `banned`. Mọi lần ghi đều qua `validate`.
- [X] T009 [US1] Trong `tools/filmcheck/script.py`, thêm vào `check()` khi `channels.snapshot(film_dir)` có:
  - điều kiện cứng `channel_language`;
  - `banned_word` (mỗi chỗ một lỗi `{"para", "sentence", "rule": "banned_word", "detail": "<từ>"}`; điều kiện cứng trượt khi có ít nhất một chỗ).

  Phim không có bản chụp thì không thêm khoá nào vào `hard`.
- [X] T010 [US1] Trong `tools/filmcheck/publish.py`, thêm vào `check()` khi có bản chụp:
  - `channel_hashtags` (so không phân biệt hoa thường);
  - `channel_banned` (tiêu đề, `hook`, `summary`, tên chương, chữ trên thumbnail);
  - `channel_title_max`.
- [X] T011 [US1] Trong `tools/filmcheck/qc.py`, thêm `channel_voice` vào `measure()` theo R3: đọc `lines_file`; `voice` không ghi thì tính là `af_bella`; `speed` mặc định 1,0, lệch hơn 0,01 là lỗi; bỏ qua khi `voice_override` là `true`. Thêm `measures.channel_voice_bad` và dòng lỗi.
- [X] T012 [US1] Trong `tools/filmcheck/editor.py`, đưa `CHANNEL_BRIEF.md` (nếu có) vào danh sách tệp của biên tập và thêm câu vào lời nhắc hệ thống theo R4. Test trong `tests/filmcheck/test_channels.py`: lời nhắc và danh sách tệp có `CHANNEL_BRIEF.md` khi phim có bản chụp, và không có khi phim không có.
- [X] T013 [US1] Trong `CLAUDE.md`, luồng làm phim thêm bước "Kênh": khi người dùng nói phim thuộc kênh nào thì chạy `channel attach <tên> <kênh> [giá trị riêng]` ngay sau khi có tên phim, đọc `films/<tên>/CHANNEL_BRIEF.md` trước Treatment, và dùng giọng, tốc độ của kênh trong `lines.json`. Người dùng chốt điều mới thì chạy `channel decide`. Thêm `channels/` vào mục Cấu trúc; thêm lệnh `channel` và `lesson` vào dòng `bin/studio`. Tạo `channels/README.md` (danh mục rỗng, có giải thích) và bỏ `channels/` khỏi `.gitignore` nếu đang bị bỏ qua.
- [X] T014 [US1] Trong `tools/runner/JOB.md` và `tools/runner/agent.py`: khi `films/<name>/CHANNEL_BRIEF.md` có, agent đọc nó trước Treatment, viết bằng ngôn ngữ của kênh (thay cho "All text in the film is in English"), và dùng giọng, tốc độ của kênh trong `lines.json`. Test trong `tests/online/test_agent_thrift.py`: lời nhắc của việc có kênh nói tới `CHANNEL_BRIEF.md` và ngôn ngữ của kênh.

**Checkpoint**: US1 chạy được ở local trên phim mẫu.

## Phase 4: User Story 2 - Ghi bài học và chặn lỗi lặp lại (P2)

**Goal**: bài học kênh và bài học chung; luật máy chặn lỗi lặp lại; nháp chỉ có hiệu lực sau khi duyệt.

**Independent Test**: bài học kênh A với `phrase:you won't believe`. Kịch bản của kênh A có cụm đó → `script check` trượt `lesson_rule #n`. Kênh B không bị chặn. Bài học chung chặn cả hai. Bài học `draft` và `retired` không chặn.

### Tests for User Story 2

- [X] T015 [P] [US2] Trong `tests/filmcheck/test_channels.py::Lessons`, viết test:
  - số bài học tăng dần và không dùng lại sau khi bỏ; nháp → duyệt → bỏ; không có chiều ngược lại;
  - luật sai → `rule_valid: false`, có cảnh báo, không được kiểm;
  - `lesson_rule` trong `script check` (`phrase:` và `max_sentence_words:`) và trong `publish` (`phrase:` và `max_title_chars:`), mỗi lỗi có `#n` (SC-003);
  - `PUBLISH.md` có dòng đầu `⚠ Do not publish yet: repeats lesson #n`;
  - bài học chung áp cho mọi kênh; bài học kênh A không áp cho kênh B; `draft` và `retired` không chặn.

### Implementation for User Story 2

- [X] T016 [US2] Trong `tools/filmcheck/channels.py`, viết `add_lesson(path, *, what, why, stop, film=None, rule=None, status)`, `approve(path, n)`, `retire(path, n)` và `edit_draft(path, n, **fields)` theo data-model.md (đủ độ dài các trường, tối đa 200 bài học mỗi tệp).
- [X] T017 [US2] Trong `tools/filmcheck/cli.py`, viết các lệnh `lesson list|draft|add|approve|retire` theo contracts/cli.md (`<scope>` = mã kênh hoặc `shared`; local dùng `channels/lessons.json`).
- [X] T018 [US2] `lesson_rule` trong `tools/filmcheck/script.py` (`phrase:` trên lời đọc, `max_sentence_words:` trên từng câu; điều kiện cứng) và trong `tools/filmcheck/publish.py` (`phrase:` trên cùng các chữ như `channel_banned`, `max_title_chars:` trên tiêu đề; thêm `measures.lessons_repeated`; `write_publish_md` thêm dòng cảnh báo ở đầu khi có lỗi `lesson_rule`).
- [X] T019 [US2] Trong `CLAUDE.md`, thêm cách ghi bài học ở local: người dùng kể lỗi → Claude soạn bằng `lesson draft <kênh|shared> …`, in bài học nháp, hỏi người dùng duyệt trong khung chat → duyệt thì `lesson approve`. Lỗi đúng cho mọi kênh thì dùng `shared`.

**Checkpoint**: US1 và US2 chạy ở local.

## Phase 5: User Story 3 - Quản lý kênh trên giao diện online (P3)

**Goal**: API kênh và bài học, việc có kênh, nháp bài học sau khi sửa phim, trang Channels (contracts/api.md).

**Independent Test**: qua API, tạo kênh, thêm 2 bài học, bỏ 1 bài; người khác nhận 404. Giao phim có kênh: bản chụp có trong phim. Sửa phim với `lesson: true`: kênh có 1 nháp.

### Tests for User Story 3

- [X] T020 [P] [US3] Trong `tests/online/test_channels_api.py`, viết test:
  - mọi đường của contracts/api.md, gồm lỗi `422`, `409 exists`, `409 limit` và `409 not_draft`;
  - người khác nhận 404 trên mọi đường kênh; người không phải admin nhận 403 trên `/lessons/shared` (SC-005);
  - việc phim có `channel` → `films/<phim>/channel.json` được chép về kho của người dùng; phong cách lấy từ hồ sơ khi không gửi;
  - sửa phim với `lesson: true` → kênh có một bài học `draft` và `job.lesson_draft`;
  - bài học chung của admin vào bản chụp của phim người khác.
- [X] T021 [P] [US3] Viết `tests/online/browser_channels.cjs` (gọi từ `test_channels_api.py`, bỏ qua khi không có trình duyệt): tạo kênh trên `#/channels`; thêm một bài học; trong form giao phim, chọn kênh thì ô phong cách và độ dài đổi theo; màn hình 360 px không có thanh cuộn ngang; không có `pageerror`.

### Implementation for User Story 3

- [X] T022 [US3] Trong `tools/studio/studio/api_online.py`, viết các đường API của contracts/api.md, dùng `channels.py` với gốc `store.root()` của người đang đăng nhập và bài học chung ở `db.data_dir() / "shared" / "lessons.json"`. `POST /jobs` nhận `channel` (điền `style` và `seconds` từ hồ sơ; `seconds` của kênh vượt `film_max_seconds` thì dùng giới hạn và ghi một dòng log; 404 khi không có kênh; 422 khi phong cách không còn); việc sửa phim nhận `lesson` (422 khi phim gốc không có kênh). Thêm `tools/` vào `sys.path` như `proxy.py`. Cập nhật danh sách đường được ghi lại nếu có test kiểm việc này.
- [X] T023 [US3] Trong `tools/runner/worker.py`:
  - `prepare()`: việc phim có `input.channel` (hoặc việc sửa phim có kênh của phim cũ) thì gọi `channels.attach(...)` vào `work/films/<phim>/`;
  - `finished()`: việc sửa phim có `input.lesson` và `films/<phim>/LESSON_DRAFT.json` hợp lệ thì gọi `add_lesson(..., status="draft")` vào kênh, ghi `job.lesson_draft` và một dòng log;
  - `publish_summary`: thêm `blocked_by_lesson`.

  Trong `tools/runner/agent.py`, lời nhắc của việc sửa phim có `lesson` dặn agent viết `LESSON_DRAFT.json` (contracts/files.md). Trong `tests/online/fake_agent.py`, viết `LESSON_DRAFT.json` khi được dặn.
- [X] T024 [US3] Trong `tools/studio/studio/web/app.js` và `style.css`, làm theo contracts/api.md:
  - route `#/channels` và `#/channels/<slug>` (form hồ sơ, quyết định, bảng bài học với Approve, Edit, Retire, form thêm bài học);
  - Settings → Shared lessons (admin);
  - link "Channels" trên thanh trên ở chế độ online;
  - `<select id="f-channel">` trong form giao phim, điền phong cách và độ dài;
  - ô "Save this as a lesson" trong Request changes;
  - dòng "⚠ Do not publish yet: repeats lesson #n" trong khối Publish; dòng nháp bài học.

  Mọi chữ của người dùng đi qua `esc`. Giữ `@ts-check` sạch.

**Checkpoint**: cả 3 story chạy đúng.

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T025 Chạy quickstart mục 2 ở local trên một phim có sẵn trong `films/` (attach, `script check` nếu có kịch bản, `publish` với gói có sẵn). Ghi kết quả vào cuối `specs/012-channel-profile/quickstart.md`. Xoá kênh thử khỏi `channels/` trước khi commit.
- [ ] T026 Chạy đủ 5 bộ test. Đối chiếu từng FR và SC với code và test; ghi bảng vào cuối `specs/012-channel-profile/tasks.md`. SC-004 cần bài chạy thật, nên **hỏi người dùng trước khi chạy**.

## Dependencies & Execution Order

- Phase 1 → Phase 2 → US1 → US2 → US3 → Polish.
- Trong US1: T009, T010, T011 và T012 sửa các tệp khác nhau, làm song song được sau T007. T013 và T014 làm song song được.
- US2 cần các hàm của US1 (bản chụp, `find_banned`). US3 cần US1 và US2.

## Implementation Strategy

1. **MVP**: Phase 1 + 2 + US1. Ở local đã giao phim theo kênh được, và các máy chấm kiểm luật kênh.
2. **US2**: bài học và luật máy.
3. **US3**: online.
4. Polish: chạy thật ở local; bài chạy online chỉ làm khi người dùng đồng ý.

## Đối chiếu sau implement (T026)

| Yêu cầu | Code | Kiểm chứng |
|---|---|---|
| FR-001 hồ sơ kênh đủ trường | `channels.save`, `normal`; lệnh `channel new|set|show`; API `POST/PUT /channels` | `Store.test_save_and_read_back`, `Store.test_cli`, `test_profile_and_lessons` |
| FR-002 kiểm khi lưu | `channels.validate` | `Store.test_bad_profiles_are_refused`; API 422 cho hashtag cấm, phong cách lạ |
| FR-003 phim gắn kênh, giá trị riêng thắng | `channel attach`, `make_job` điền từ hồ sơ | `Snapshot.test_film_values_win`, `test_film_for_a_channel` (SC-001: chỉ kênh và ý tưởng) |
| FR-004 thêm quyết định | `channel decide`, `POST /decisions`, trang kênh | `Store.test_cli`, `test_profile_and_lessons` |
| FR-005 đọc hồ sơ và bài học trước Treatment, ≤ 6000 ký tự | `CHANNEL_BRIEF.md`; CLAUDE.md 2a; JOB.md; agent.py | `Snapshot.test_brief_is_short`, `test_channel_films_read_the_brief` |
| FR-006 luật kênh trong `script check` | script.py `channel_language`, `banned_word` | `Rules.test_channel_language`, `test_banned_word` |
| FR-006a giọng của kênh | qc.py `channel_voice` | `Rules.test_channel_voice` (có cả trường hợp giọng riêng của phim) |
| FR-007 biên tập đọc hồ sơ | editor.py | `Rules.test_editor_reads_the_brief` |
| FR-008 luật kênh trong `publish` | publish.py `channel_hashtags`, `channel_banned`, `channel_title_max` | `Rules.test_channel_hashtags`, `test_channel_banned`, `test_channel_title_max`; T025 |
| FR-009 bài học kênh và chung, đủ trường | `add_lesson`, `lessons.json`, `LESSONS.md` | `Lessons.test_numbers_and_states` |
| FR-010 3 loại luật máy; luật sai là `invalid` | `parse_rule` | `Lessons.test_numbers_and_states`, `Snapshot.test_only_active_valid_rules` |
| FR-011 vi phạm có số bài học, là lỗi nặng; gói ghi "Do not publish" | script.py, publish.py `lesson_rule`; `blocked_by_lesson`; khối Publish | `Lessons.test_channel_lesson_blocks_only_its_channel`, `test_shared_lesson_blocks_every_channel`, `test_publish_lesson_rule_and_warning` (SC-003) |
| FR-012 biên tập ghi P1 khi lặp bài học | lời nhắc của biên tập | `test_editor_reads_the_brief` (chỉ kiểm lời nhắc; việc biên tập thật cho P1 cần bài chạy thật) |
| FR-013 nháp rồi duyệt | `lesson draft/approve`; `LESSON_DRAFT.json`; worker `save_lesson_draft` | `Lessons.test_lesson_cli`, `test_film_for_a_channel` (nháp sau khi sửa phim rồi duyệt) |
| FR-014 không xoá, chỉ bỏ | `retire`; không có lệnh xoá | `Lessons.test_draft_and_retired_do_not_block` |
| FR-015 local, vào git | `channels/` không bị `.gitignore`; `channels/README.md` | xem `git status` |
| FR-016 online theo người; bài học chung của admin | `store.root()`; `/lessons/shared` cần admin | `test_others_cannot_see_or_change` (SC-005) |
| FR-017 trang Channels, chọn kênh khi giao phim | app.js `pageChannels`, `pageChannel`, `f-channel` | `test_pages_in_a_browser` |
| FR-018 lỗi kênh và bài học trên trang việc và CHECKS.md | `problems` có mã và `#n`; khối Publish | `test_film_for_a_channel`; `report.markdown` in mọi lỗi |
| FR-019 giới hạn | giọng chỉ theo dạng tên của thư viện; không có phần đăng hay phân tích kênh khác | `Store.test_bad_profiles_are_refused` (giọng là tệp clone bị từ chối) |
| SC-002 bắt 100% vi phạm | | `Rules.*`, `Lessons.*` |
| SC-004 ≤ 6000 ký tự, ≤ 2% token | | 6000 ký tự: `test_brief_is_short`. 2% token: **chưa đo**, cần bài chạy thật, chờ người dùng |
| SC-006 phim không gắn kênh như cũ | | `Rules.test_no_snapshot_no_change`; test của 010 và 011 không bị sửa |
