# Tasks: Chọn đề bằng số liệu YouTube

**Input**: `specs/013-topic-picker/` (spec.md, plan.md, research.md, data-model.md, contracts/, quickstart.md). Tính năng này xây trên 012 (kênh), 010 (cách gọi `claude -p` của biên tập, proxy cho `web fetch`) và 007–009 (việc online).

**Tests**: có. SC-001, SC-002, SC-003, SC-004 và SC-006 cần test tự động. Không gọi YouTube thật trong test: dùng số liệu mẫu (`tests/filmcheck/youtube_samples.py`) và YouTube giả trong `fake_upstream` của test online.

**Luật chung cho mọi task**:
- Không in, không log, không commit khoá. Khoá mẫu trong test là `AIzaTEST-not-a-real-key-000000000000000` (39 ký tự).
- Không tải video. Không sửa `lib/`. Chữ in ra màn hình bằng tiếng Anh.
- Sau mỗi phase, 5 bộ test phải đạt. Commit sau mỗi phase.

## Phase 1: Setup

- [X] T001 [P] Thêm `topics` vào `case` của `bin/studio` (chuyển tới `cmd_filmcheck`) và thêm dòng `usage`. Trong `tools/filmcheck/cli.py`, thêm parser cho các lệnh của contracts/cli.md và `config youtube-key`. Thêm `channels/*/topics.json`, `channels/*/TOPICS.md` và `channels/*/references.json` vào `.gitignore`.
- [X] T002 [P] Viết `tests/filmcheck/youtube_samples.py`: một YouTube giả nhỏ (hàm `answer(endpoint, params) -> dict`) với 4 đề có kết quả tính tay theo bảng R2, gồm một đề cho từng kết luận: PRIORITY, GO, HOLD (có một mục ≤ 3) và DROP. Thêm một kênh mẫu có video cùng đề 9 ngày trước. Ghi kết quả tính tay vào docstring.

## Phase 2: Foundational

- [X] T003 Trong `tools/filmcheck/topics.py`, viết phần nền:
  - `PRICE` (`search` 100, các endpoint khác 1);
  - `Usage(path, limit)`: đếm theo ngày giờ Thái Bình Dương, có `charge(endpoint)` ném `QuotaError` khi vượt;
  - `Cache(dir)`: giữ 24 giờ, khoá là sha256 của endpoint và tham số;
  - `redact(text, key)`;
  - `Fetcher.local(key, usage, cache)` (gọi thẳng `https://www.googleapis.com/youtube/v3/…` bằng `urllib`, đổi được bằng `STUDIO_YOUTUBE_URL`) và `Fetcher.proxy(url, token)` (`POST /internal/youtube`);
  - `read_key()`: `YOUTUBE_API_KEY`, hoặc `~/.config/claude-utube/youtube.key`.
- [X] T004 Trong `tests/filmcheck/test_topics.py::Plumbing`, viết test:
  - sang ngày mới thì đếm lại; vượt giới hạn thì `QuotaError`;
  - số liệu tạm trong 24 giờ không cộng đơn vị;
  - `redact` bỏ khoá.

## Phase 3: User Story 1 - Chấm một danh sách đề (P1) 🎯 MVP

**Goal**: `topics score` ở local cho 5 điểm, kết luận và bằng chứng, rồi ghi `topics.json` và `TOPICS.md`.

**Independent Test**: với `youtube_samples` và `fake_claude` (chấm "hợp kênh"), 4 đề cho đúng điểm và kết luận như tính tay; chạy lại cho cùng điểm; mỗi đề tốn ≤ 400 đơn vị.

### Tests for User Story 1

- [X] T005 [P] [US1] Trong `tests/filmcheck/test_topics.py::Scores`, viết test:
  - mỗi bảng ngưỡng của R2 (nhu cầu, độ nóng, cạnh tranh, trùng) ở các điểm biên;
  - 4 đề mẫu cho đúng 5 điểm và kết luận (SC-001); chấm lại từ `raw` cho cùng kết quả;
  - đơn vị mỗi đề ≤ 400 (SC-002);
  - phim trùng nằm trong bằng chứng;
  - không có khoá → thoát 2, có hướng dẫn `config youtube-key`;
  - hết hạn mức giữa lô → thoát 3, các đề đã chấm được giữ, đề còn lại `unscored`.
- [X] T006 [P] [US1] Thêm vào `tests/filmcheck/test_topics.py::Secret`: chạy mọi lệnh `topics` (gồm cả lỗi 403 giả của YouTube có chứa khoá trong URL) và kiểm rằng khoá mẫu không có trong stdout, stderr, `topics.json`, `TOPICS.md` hay `.studio/` (SC-004).

### Implementation for User Story 1

- [X] T007 [US1] Trong `tools/filmcheck/topics.py`, viết `fetch_topic(fetcher, text, lang, ref_videos) -> raw` theo R1, gồm bộ lọc "cùng đề", trung vị lượt xem của 5 kênh đầu, và đơn vị đã dùng.
- [X] T008 [US1] Trong `tools/filmcheck/topics.py`, viết các hàm thuần, không mạng, đúng bảng R2: `score_demand`, `score_heat`, `score_competition`, `score_overlap(text, made)`, `verdict(scores)` (gồm PRIORITY), `similarity(a, b)` (Jaccard; tiếng không tách từ dùng cặp ký tự) và `guess_type(text)`.
- [X] T009 [US1] Viết `tools/filmcheck/topics_fit.py`: lời nhắc hệ thống cố định, lược đồ JSON và `run(channel_md, topics, suggest)` theo R3. Dùng `editor.claude_bin()` và `editor.model_args()`, với `--tools ""` và `--json-schema`; sai lược đồ thì gọi lại một lần, vẫn sai thì `fit = null`. Trong `tests/online/fake_claude`, thêm chế độ trả lời cho lược đồ này: mỗi đề `score` 7, có `[fit-low]` trong chữ của đề thì 2; khi có `suggest` thì gợi ý 2 đề.
- [X] T010 [US1] Trong `tools/filmcheck/topics.py`, viết `score_batch(channel, texts, fetcher, suggest, made, refs) -> result` và các hàm lưu `load/save(root, slug)` (`topics.json` và `TOPICS.md`, gộp đề trùng ≥ 0,8 theo R4). Đề có kiểu chữ khác ngôn ngữ kênh (chữ CJK với kênh không phải zh, ja, ko, hoặc ngược lại) thì có thêm `note` cảnh báo (edge case của spec). Trong `tools/filmcheck/cli.py`, viết `topics score|recheck|fit|type|usage` và `config youtube-key` (getpass, thử bằng `videos.list` một video, ghi tệp quyền 600, chỉ in 4 ký tự cuối).
- [X] T011 [US1] Trong `CLAUDE.md`, thêm mục "Chọn đề" vào luồng làm phim: người dùng muốn tìm đề cho kênh thì chạy `topics score <kênh> "<đề>"… [--suggest]`, đọc bảng điểm, rồi `topics take <kênh>` để lấy ý tưởng cho phim kế tiếp; nhắc người dùng tự chạy `config youtube-key` trong terminal của họ và không dán khoá vào chat. Thêm `topics …` vào dòng `bin/studio`.

**Checkpoint**: US1 chạy được ở local với số liệu mẫu.

## Phase 4: User Story 2 - Hàng đợi đề (P2)

**Goal**: hàng đợi theo thứ tự; luật kiểu đề, kênh mẫu và đề cũ; lấy đề; đề chuyển sang "đã làm".

**Independent Test**: hàng đợi mẫu có PRIORITY, 2 GO, HOLD, DROP và 2 phim gần nhất cùng kiểu → đúng thứ tự, đề cùng kiểu bị bỏ qua kèm lý do, đề kênh mẫu vừa đăng bị chặn.

### Tests for User Story 2

- [X] T012 [P] [US2] Trong `tests/filmcheck/test_topics.py::Queue`, viết test:
  - thứ tự PRIORITY → GO (tổng giảm dần) → HOLD, không có DROP;
  - kiểu đề của 2 phim gần nhất bị bỏ qua, có lý do;
  - `blocked_reference` khi kênh mẫu đăng cùng đề trong 30 ngày, và không chặn khi kênh mẫu đăng 40 ngày trước;
  - đề cũ hơn 14 ngày bị bỏ qua trừ khi có `--allow-stale`;
  - `take` chuyển đề sang `in_progress` và gắn phim; `made` → `made`;
  - đề `made` làm giảm điểm "trùng" của đề giống nó ở lần chấm sau;
  - không còn đề → thoát 1 kèm lý do (SC-003).

### Implementation for User Story 2

- [X] T013 [US2] Trong `tools/filmcheck/topics.py`, viết `queue(data)`, `take(data, film=None, allow_stale=False) -> (topic, skipped)`, `mark_made(data, n)`, `reference_hits(text, ref_videos)` và `refs load/save` (`references.json`, tối đa 10, `id` đúng dạng). Trong `tools/filmcheck/cli.py`, viết `topics queue|take|made|refs`.
- [X] T014 [US2] Ở local, phim gắn đề tự chuyển đề sang `made` khi `publish` của phim đạt: trong `tools/filmcheck/cli.py` `cmd_publish`, khi `channel.json` của phim có `topic`. Trong `tools/filmcheck/channels.py`, `attach` nhận thêm `topic` và ghi vào bản chụp. Lệnh `channel attach` có thêm `--topic N`.

**Checkpoint**: US1 và US2 chạy ở local.

## Phase 5: User Story 3 - Online (P3)

**Goal**: khoá và hạn mức ở proxy; loại việc `topics`; API và mục Topics trên trang kênh; Settings.

**Independent Test**: với YouTube giả, chủ xưởng đặt khoá → người dùng chấm 3 đề → việc `topics` xong → `GET /channels/{slug}/topics` có điểm và hàng đợi; vượt `topics_per_day` → 429; người khác nhận 404; khoá không có trong bất kỳ phản hồi hay log nào.

### Tests for User Story 3

- [X] T015 [P] [US3] Trong `tests/online/helpers.py` `fake_upstream`, thêm YouTube giả (`/youtube/v3/{search,videos,channels,playlistItems}`, trả số liệu của `youtube_samples`, ghi lại khoá nhận được) và đặt `STUDIO_YOUTUBE_URL` cho proxy trong test.
- [X] T016 [P] [US3] Viết `tests/online/test_topics_api.py`:
  - `PUT /admin/youtube-key` (người không phải admin nhận 403; chỉ trả `last4`);
  - chấm 3 đề → việc `topics` không trừ lượt phim → kết quả nằm trong `topics.json` của người đó;
  - chấm lại trong 24 giờ không tăng `youtube_units_today`;
  - `topics_per_day` → 429 kèm `retry_at`; chưa có khoá → 503;
  - người khác nhận 404 trên mọi đường của contracts/api.md (SC-006);
  - `take` rồi giao phim với `topic` → đề `in_progress`, việc xong → `made`;
  - `/internal/youtube` từ chối mã của việc phim (403);
  - khoá không có trong mọi phản hồi, `job.log` và log của proxy (SC-004).

  Thêm `tests/online/browser_topics.cjs`: mục Topics, dán đề, Score, bảng hiện ra, "Make a film" điền sẵn ý tưởng; màn hình 360 px không có thanh cuộn ngang.

### Implementation for User Story 3

- [X] T017 [US3] Trong `tools/runner/proxy.py`, viết `POST /internal/youtube` theo contracts/api.md: chỉ việc `topics`; 4 endpoint; `Usage` và `Cache` dưới `$STUDIO_DATA/youtube/`; khoá ở `$STUDIO_DATA/secrets/youtube.key`; `redact`; log chỉ ghi endpoint, đơn vị và có dùng số liệu tạm hay không.
- [X] T018 [US3] Trong `tools/studio/studio/quotas.py`, thêm cài đặt `youtube_daily_units` (9000; 100–10000) và `topics_per_day` (40; 0–500). Trong `tools/studio/studio/api_online.py`, viết:
  - `PUT/DELETE /admin/youtube-key` (thử khoá qua YouTube, ghi tệp quyền 600);
  - `GET /admin/settings` thêm `youtube_key_set`, `youtube_key_last4`, `youtube_units_today`;
  - các đường `/channels/{slug}/topics…` và `/references` của contracts/api.md (việc `topics` qua `jobs.build`, `charged: false`; đếm đề trong ngày từ các việc `topics` của người đó);
  - `POST /jobs` nhận `topic`.
- [X] T019 [US3] Trong `tools/runner/agent.py`, `kind == "topics"` thì gọi `topics.run_job(work)` (Fetcher qua proxy, `topics_fit` qua proxy với mã của việc), ghi `topics-result.json`, rồi thoát. Trong `tools/runner/worker.py`, việc `topics` kết thúc thì gộp kết quả vào `channels/<slug>/topics.json` của chủ việc và gọi `jobs.finish(done)`, không cần `job done`, không qua QC. `prepare()` của việc `topics` ghi `made` và `references` vào `.input.json`. Việc phim có `input.topic` thì đề chuyển sang `made` khi việc xong. Trong `tests/online/fake_agent.py`, việc `topics` gọi cùng `topics.run_job`.
- [X] T020 [US3] Trong `tools/studio/studio/web/app.js` và `style.css`, làm theo contracts/api.md:
  - mục Topics trên trang kênh (ô đề, ô chọn Suggest, nút Score, bảng điểm có kiểu đề và điểm "hợp kênh" sửa được, video bằng chứng, nhãn stale, hàng đợi, nút "Make a film");
  - mục Reference channels;
  - `#/new?channel=&topic=` điền sẵn ý tưởng và gửi `topic`;
  - Settings → General: ô khoá YouTube (chỉ ghi, hiện `…last4`), hai giới hạn và số đơn vị đã dùng hôm nay.

  Mọi chữ đi qua `esc`; đường dẫn video chỉ nhận `https://www.youtube.com/watch?v=<id>`.

**Checkpoint**: cả 3 story chạy đúng.

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T021 Chạy đủ 5 bộ test. Đối chiếu FR và SC với code và test; ghi bảng vào cuối `specs/013-topic-picker/tasks.md`. Quickstart mục 2 (khoá thật) cần người dùng tự đặt khoá trong terminal của họ, nên **hỏi người dùng trước khi chạy**.
  - 2026-11-11: bảng đối chiếu đã ghi; 5 bộ test đạt. Bài chạy với khoá thật chờ người dùng tự đặt khoá.

## Dependencies & Execution Order

- Phase 1 → 2 → US1 → US2 → US3 → Polish.
- Trong US1: T007, T008 và T009 làm song song được (khác hàm, T009 khác tệp). T010 cần cả ba. T011 làm song song được.
- US3: T015 và T016 viết trước, T017–T020 sau. T019 cần T017.

## Implementation Strategy

1. **MVP**: Phase 1 + 2 + US1. Chấm đề ở local với khoá của người dùng.
2. **US2**: hàng đợi và luật lấy đề.
3. **US3**: online.
4. Polish: bài chạy với khoá thật chỉ làm khi người dùng đã tự đặt khoá.

## Phase 7: Convergence

- [X] T022 Thêm nút "Check the queue again" vào mục Topics của trang kênh (`tools/studio/studio/web/app.js`): chấm lại tối đa 20 đề trong hàng đợi qua `POST /channels/{slug}/topics/score` per FR-010 (partial: ở bản online chưa có cách chấm lại cả hàng đợi)

## Đối chiếu sau implement (T021)

| Yêu cầu | Code | Kiểm chứng |
|---|---|---|
| FR-001 tối đa 20 đề, 3–120 ký tự | `score_batch`, `ScoreIn` | test_topics `Scores.test_cli`; API 422 |
| FR-001a gợi ý tối đa 10 đề | `topics_fit` (`suggested`), `--suggest`, ô Suggest | `Scores.test_cli` (có đề `suggested`), `test_score_queue_and_film` |
| FR-002 5 mục theo ngôn ngữ và vùng của kênh | `fetch_topic`, `score_*`, `topics_fit` | `Scores.test_tables_at_their_edges`, `test_sample_topics_match_the_hand_checks` |
| FR-003 GO, HOLD, DROP, PRIORITY | `verdict`, `cooling` | 4 đề mẫu, mỗi đề một kết luận (SC-001) |
| FR-004 bằng chứng và số liệu thô | `score_raw`, `raw` | đường dẫn video, `closest_film` (`test_overlap_names_the_film`) |
| FR-005 lặp lại được; không cần mạng | `score_raw` chỉ dùng `raw` | chấm lại từ `raw` cho cùng kết quả |
| FR-006 thứ tự hàng đợi | `queue` | `Queue.test_order` |
| FR-007 kiểu đề, luật 2 phim gần nhất | `guess_type`, Claude, `take` | `Queue.test_take_skips_the_last_two_types_and_stale`; API sửa kiểu |
| FR-008 kênh mẫu, không vào git | `references.json` trong `.gitignore`, `reference_hit` | `Scores.test_reference_channel_blocks`, `test_references` |
| FR-009 lấy đề → đang làm → đã làm | `take`, `mark_made`, `POST /jobs topic`, worker `topic_made`, `publish` local | `Queue.test_publish_marks_the_topic_made`, `test_score_queue_and_film` |
| FR-010 đề cũ, chấm lại | `stale`, `topics recheck`, nút Check again | `Queue.test_stale_needs_permission` |
| FR-011 khoá kín | `redact`, `save_key`/`save_online_key` quyền 600, `last4` | `Secret.test_the_key_never_shows`, `test_key_only_for_the_owner`, `test_proxy_refuses_film_jobs_and_hides_the_key` (SC-004) |
| FR-012 hạn mức, ≤ 400 đơn vị mỗi đề | `Usage`, `PRICE` | `Plumbing.test_usage_by_day_and_limit`, `test_quota_stops_and_keeps`, đơn vị mỗi đề (SC-002) |
| FR-013 số liệu tạm 24 giờ | `Cache` (local và proxy) | lần chấm lại tốn 0 đơn vị (local và online) |
| FR-014 lệnh local, TOPICS.md | cli `topics …` | `Scores.test_cli`, `Queue.test_refs_and_cli_take` |
| FR-015 mục Topics online | app.js `fillTopics` | `test_page_in_a_browser` |
| FR-016 theo người, giới hạn đề mỗi ngày | `channel_or_404`, `topics_today` | `test_others_get_404` (SC-006), `test_limit_per_day` |
| FR-017 không tải video | chỉ 4 endpoint số liệu, proxy chặn endpoint khác | đọc lại code |
| SC-001 … SC-006 | | đều có test tự động, như trên |
| Bài chạy với khoá thật | | **chưa chạy**: người dùng cần tự đặt khoá (`config youtube-key`) trong terminal của họ |
