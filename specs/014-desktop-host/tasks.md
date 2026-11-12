# Tasks: Chế độ máy chủ trên một máy

**Input**: `specs/014-desktop-host/` (spec.md, plan.md, research.md, data-model.md, contracts/cli.md, quickstart.md). Tính năng này xây trên 007–013 (web, proxy, worker, `RUNNER=local`, SQLite, trang thiết lập, đăng nhập Claude) và 003 (luồng chat `job`, `review`).

**Tests**: có, trong `tests/online/test_host.py`. Test bật máy chủ thật bằng tiến trình con, với `STUDIO_AGENT_CMD` (agent giả) và `STUDIO_CLAUDE_BIN` (Claude giả). Thư mục dữ liệu nằm trong `tests/online/.tmp/`.

**Luật chung cho mọi task**:
- Cùng một bộ code với bản VPS. Không có nhánh logic riêng cho máy chủ trong code nghiệp vụ; chỉ khác ở biến môi trường.
- Không ghi vào thư mục dự án khi chạy chế độ máy chủ. Không tự cài phần mềm hệ thống. Không sửa `lib/`.
- Sau mỗi phase, 5 bộ test phải đạt. Commit sau mỗi phase.

## Phase 1: Setup

- [X] T001 Kiểm mục "Kiểm khi implement" của research R5 và ghi kết quả vào cuối `specs/014-desktop-host/research.md`: trong WSL2 của máy này, `ClaudeAgentOptions(sandbox=…)` của claude-agent-sdk có chạy được Bash cách ly không (có bubblewrap không, lệnh ghi ra ngoài thư mục việc có bị chặn không). Không chạy được thì ghi lại, rồi làm tiếp với cảnh báo theo R5. Không dừng để hỏi, vì spec đã chấp nhận rủi ro này.
- [X] T002 [P] Trong `bin/studio`, thêm `app` vào `case` (chuyển tới `cmd_studio`) và thêm dòng `usage`. Trong `tools/studio/studio_cli.py`, thêm parser cho `app start|stop|status|import` theo contracts/cli.md. Tạo `tools/studio/studio/host.py` có docstring trỏ tới specs/014.

## Phase 2: Foundational

- [X] T003 Trong `tools/studio/studio/host.py`, viết:
  - `default_data_dir()` (Linux/WSL: `$XDG_DATA_HOME/claude-utube` hoặc `~/.local/share/claude-utube`; macOS: `~/Library/Application Support/ClaudeUtube`);
  - `check_data_dir(d, project)` (từ chối thư mục nằm trong dự án, hoặc không ghi được);
  - `free_port(range)`;
  - `check_tools() -> list[str]` theo R8;
  - `read_state(d)` và `pointer()` cho `host.json` và `~/.config/claude-utube/host.json`;
  - `lock(d)` (flock, không chặn, trả `None` khi đang bị giữ).
- [X] T004 Trong `tools/studio/studio/db.py`, sao lưu tệp cơ sở dữ liệu vào `backup/studio-<phiên bản cũ>-<thời điểm>.db` bằng `sqlite3 backup()` trước khi nâng cấp, khi phiên bản lưu < `SCHEMA_VERSION` (R3, FR-006). Test trong `tests/online/test_host.py::Upgrade`: cơ sở dữ liệu phiên bản 2 → có tệp sao lưu, và cơ sở dữ liệu lên phiên bản hiện tại.

## Phase 3: User Story 1 - Chạy cả xưởng bằng một lệnh (P1) 🎯 MVP

**Goal**: `app start|status|stop` chạy giao diện, proxy và worker không cần Docker; tạo chủ xưởng; giao phim bằng form; việc chạy xong với khối Quality.

**Independent Test**: thư mục dữ liệu trống → `app start` → giao diện trả lời < 20 giây → `/api/v1/auth/setup` tạo chủ xưởng → đăng nhập → giao phim (agent giả) → việc `done` có `qa` → `app stop` → không còn tiến trình nào.

### Tests for User Story 1

- [X] T005 [P] [US1] Trong `tests/online/test_host.py::Start`, viết test:
  - `app start --data <tmp>` thoát 0 và in `URL:`; giao diện trả lời < 20 giây (SC-001);
  - `app status --json` có 3 phần đang chạy;
  - tạo chủ xưởng qua `/auth/setup`, đăng nhập, giao phim → việc `done` có `qa.film` và `qa.publish` (SC-002);
  - `app stop` → mọi pid trong `host.json` đã chết, và `pgrep -f <thư mục dữ liệu>` không còn gì (SC-003);
  - thư mục dự án không có tệp nào mới hay bị đổi (so `git status --porcelain` trước và sau, SC-006);
  - thiếu công cụ (giả bằng `PATH` không có ffmpeg) → thoát 2, có dòng `✗ ffmpeg`.

### Implementation for User Story 1

- [X] T006 [US1] Trong `tools/studio/studio/host.py`, viết `supervise(data, web, proxy, project)` theo R1:
  - giữ khoá, ghi `host.json` và con trỏ;
  - mở 3 tiến trình con với biến môi trường của R1 (`STUDIO_MODE=online`, `STUDIO_DATA`, `STUDIO_OWNER_UNLIMITED=1`, `RUNNER=local`, `STUDIO_PROXY`), giao diện nghe `127.0.0.1:<web>`;
  - ghi log xoay vòng (10 MB × 5) cho mỗi phần;
  - mở lại tiến trình con bị sập (dừng hẳn khi sập quá 5 lần trong 60 giây);
  - SIGTERM → tắt cả cây, xoá `host.json` và con trỏ.
- [X] T007 [US1] Trong `tools/studio/studio/host.py` và `tools/studio/studio_cli.py`, viết:
  - `start(...)`: kiểm công cụ và thư mục; đang chạy rồi thì in địa chỉ; chọn cổng; tách tiến trình giám sát (`start_new_session`); đợi `/api/health`; in `URL:`. Có `--foreground` thì giám sát ngay trong lệnh;
  - `status(...)` theo contracts/cli.md;
  - `stop(...)` ở dạng đơn giản: SIGTERM rồi đợi nhả khoá. Phần từ chối khi có việc là T011.
- [X] T008 [US1] Trong `tools/studio/studio/accounts.py`, `setup()` đặt `quota_films = 1000` và `quota_learns = 1000` khi có `STUDIO_OWNER_UNLIMITED=1` (R4, FR-009). Test: chủ xưởng ở chế độ máy chủ có hạn mức 1000; bản VPS (không có biến này) giữ như cũ.
- [X] T009 [US1] Trong `tools/runner/agent.py`, viết `can_use_tool` chặn `Write`, `Edit` và `NotebookEdit` ra ngoài `WORK`, (R5, FR-016). Không bật sandbox (kết quả T001); `app start` in cảnh báo. Test (gọi thẳng hàm, không cần Claude): ghi vào `WORK/x` được, ghi vào thư mục studio hay `~` bị từ chối kèm lý do.

**Checkpoint**: US1 chạy được trên máy này.

## Phase 4: User Story 2 - Chạy an toàn và bền (P2)

**Goal**: không chạy trùng; dừng có hỏi; khởi động lại thì chạy tiếp việc dở; tự chọn cổng; log xoay vòng.

**Independent Test**: khởi động 2 lần → lần hai báo đang chạy; dừng khi có việc → bị từ chối, có `--force` thì dừng; giết tiến trình giám sát rồi khởi động lại → việc dở chạy xong.

### Tests for User Story 2

- [X] T010 [P] [US2] Trong `tests/online/test_host.py::Safety`, viết test:
  - lần khởi động thứ hai trên cùng thư mục → thoát 0, in cùng `URL:`, không có tiến trình giám sát thứ hai;
  - giữ bận cổng 8790 → giao diện lên ở 8791 và `host.json` ghi đúng;
  - có việc `[slow 30]` đang chạy → `app stop` thoát 1 và nêu tên việc; `app stop --force` → việc `stopped`, tiến trình tắt;
  - giết tiến trình giám sát (SIGKILL) khi đang có việc → `app start` lại → việc chạy xong (SC-004);
  - log: tiến trình giám sát với `maxBytes` nhỏ (biến môi trường cho test) tạo `web.log.1`.

### Implementation for User Story 2

- [X] T011 [US2] Trong `tools/studio/studio/host.py`, viết `stop` đầy đủ theo R2: đọc sổ việc, từ chối khi còn việc `running` (thoát 1, liệt kê tên), có `--force` thì đánh dấu `stopped`, rồi SIGTERM và đợi tối đa 15 giây. Khoá còn bị giữ bởi một tiến trình đã chết (SIGKILL) thì `start` vẫn mở được, vì flock tự nhả khi tiến trình chết.
- [X] T012 [US2] Kiểm `worker.recover()` hồi phục được việc dở sau khi tiến trình giám sát bị giết (thư mục việc còn, `restarts` < 1). Nếu cần thì dọn tiến trình con mồ côi của LocalRunner khi mở lại: ghi pid của việc vào `jobs/<id>/.pid`, và khi `recover` thì giết pid còn sống.

## Phase 5: User Story 3 - Mang dữ liệu cũ vào và luồng chat (P3)

**Goal**: `app import`; việc làm bằng chat hiện trong app khi máy chủ chạy.

**Independent Test**:
- dự án mẫu có 2 phim, 1 phong cách, 1 kênh (có đề) → `app import` → API của app có đủ; chạy lại không có bản trùng; dự án không đổi;
- máy chủ đang chạy → `sh bin/studio job start --kind film --name x --film f` trong dự án → việc có trong `/api/v1/jobs` của chủ xưởng; `review request` → duyệt trên app → `review wait` nhận quyết định; `job done --film f` → `/api/v1/films/f` mở được.

### Tests for User Story 3

- [X] T013 [P] [US3] Trong `tests/online/test_host.py::Import` và `::Chat`, viết test theo Independent Test ở trên. Thêm: máy chủ đã dừng → `job start` ghi vào `.studio/` như cũ.

### Implementation for User Story 3

- [X] T014 [US3] Trong `tools/studio/studio/host.py`, viết `import_project(data, project)` theo R6 (cần chủ xưởng; `copytree` từng mục, bỏ qua mục đã có, kể cả `channels/*/topics.json` và `references.json`). Viết lệnh `app import`.
- [X] T015 [US3] Trong `tools/studio/studio_cli.py`, viết luồng chat theo R7: trước khi import `studio`, nếu con trỏ đúng dự án và pid còn sống thì đặt `STUDIO_MODE=online` và `STUDIO_DATA`. `job start` tạo việc `source: "chat"` với `owner` là chủ xưởng và không có `charged`. `job done --film` tạo liên kết `accounts/<chủ xưởng>/films/<phim>` tới `films/<phim>` của dự án. In `URL:` là trang việc trên app.
- [X] T016 [US3] Trong `CLAUDE.md`:
  - thêm mục "Chạy app trên máy" với các lệnh `app start|status|stop|import` và địa chỉ;
  - ghi rằng khi app đang chạy thì việc làm bằng chat hiện trong app và duyệt được trên app;
  - thêm `app …` vào dòng `bin/studio` ở mục Cấu trúc.

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T017 Chạy đủ 5 bộ test. Kiểm FR-004: bộ test online hiện có đạt mà không sửa test nào (SC-005). Đối chiếu FR và SC, ghi bảng vào cuối `specs/014-desktop-host/tasks.md`.
- [X] T018 Chạy quickstart mục 2 trên máy này: `app start`, tạo chủ xưởng, `app import`, mở các trang phim, kênh và đề, `app stop`. Ghi kết quả vào cuối `specs/014-desktop-host/quickstart.md`. Phần đăng nhập Claude thật và giao phim thật tốn tiền, nên **hỏi người dùng trước khi làm**.

## Dependencies & Execution Order

- Phase 1 → 2 → US1 → US2 → US3 → Polish. Phải có T001 rồi mới làm T009.
- Trong US1: T008 và T009 làm song song được với T006, T007 (khác tệp).
- US2 cần T006 và T007. US3 cần US1 (máy chủ chạy được).

## Implementation Strategy

1. **MVP**: Phase 1 + 2 + US1. Chạy được cả xưởng trên máy, qua trình duyệt.
2. **US2**: an toàn khi tắt, mở, sập.
3. **US3**: chuyển dữ liệu cũ vào app, và luồng chat hiện trong app.
4. Polish: chạy thử trên máy thật.

## Đối chiếu sau implement (T017)

| Yêu cầu | Code | Kiểm chứng |
|---|---|---|
| FR-001 start, status, stop | `host.start/status/stop`, `app …` | `test_start_film_stop` |
| FR-002 không Docker, worker chạy việc trên máy | `RUNNER=local` trong `part_env` | phim giả chạy xong qua form |
| FR-003 chỉ `127.0.0.1` | uvicorn `--host 127.0.0.1`, `PROXY_HOST` | cấu hình trong `part_command` và `part_env` |
| FR-004 cùng một bộ code với VPS | chỉ biến môi trường; không sửa test cũ | bộ online 185 = 174 cũ + 11 mới, đều đạt (SC-005) |
| FR-005 mọi dữ liệu trong thư mục dữ liệu; không ghi vào dự án | `default_data_dir`, `check_data_dir` | `test_start_film_stop` (`git status` không đổi, SC-006), `test_data_folder_inside_the_project_is_refused` |
| FR-006 sao lưu rồi nâng cấp | `db._backup_before_upgrade` | `Upgrade.test_backup_before_upgrade` |
| FR-007 nhập dữ liệu dự án | `host.import_project` | `test_import` |
| FR-008 tạo chủ xưởng, đăng nhập | trang thiết lập của 008; không tự vào | `owner()` qua `/auth/setup`; login sau khi khởi động lại (`test_crash_then_start_again`) |
| FR-009 chủ xưởng không giới hạn phim | `STUDIO_OWNER_UNLIMITED` trong `accounts.setup` | hạn mức phim của chủ xưởng là 1000 |
| FR-010 không chạy trùng | `flock` trên `host.lock` | `test_twice_and_busy_port` |
| FR-011 dừng có hỏi, `--force` | `host.stop` | `test_stop_with_a_running_job` |
| FR-012 khởi động lại chạy tiếp việc dở | `worker.recover` có sẵn; `.pid` của việc | `test_crash_then_start_again` (SC-004) |
| FR-013 log xoay vòng | `RotatingFileHandler` | `test_logs_rotate` |
| FR-014 tự chọn cổng | `free_port` | `test_twice_and_busy_port` |
| FR-015 kiểm công cụ, không tự cài | `check_tools` | `test_missing_tool` |
| FR-016 agent không có container | hook `PreToolUse` chặn ghi ra ngoài thư mục việc; Bash không cách ly (T001) | `WriteGuard.test_only_the_job_folder`; `app start` in cảnh báo |
| FR-017 luồng chat vào sổ việc của app | `studio_cli` (`HOST`, `link_film`) | `test_chat_flow_goes_to_the_app` |
| SC-001 sẵn sàng < 20 giây | | đo được 1,9 giây trên máy này; test kiểm < 20 giây |
