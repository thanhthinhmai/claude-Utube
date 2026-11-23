# Tasks: Tiết kiệm token cho agent của việc

**Input**: `specs/030-agent-token-savings/` (spec.md, plan.md, data-model.md, quickstart.md)

**Tests**: Có (hiến pháp IV, SC-001…SC-006).

## Phase 1: Setup

Không cần (venv và test online đã có: `sh bin/studio deps online`).

## Phase 2: Foundational

Không có việc chặn chung; ba user story sửa ba chỗ khác nhau.

## Phase 3: User Story 1 - Một việc giữ một tài khoản Claude (P1) 🎯 MVP

**Goal**: mọi lượt của một việc đi qua cùng một slot tới khi slot đó lỗi hạn mức/đăng nhập; việc mới vẫn được phân tải.

**Independent Test**: `sh tests/online/run.sh -k Rotation`

- [x] T001 [US1] Thêm test vào tests/online/test_rotation.py: (a) SC-001 một việc 6 lượt, giữa chừng slot giữ trở thành slot dùng nhiều hơn (đặt token 5 giờ của slot đó cao) mà mọi `via` vẫn là slot đầu; (b) SC-002 slot giữ trả 429 ở lượt 3 → lượt 3 thành công qua slot kia, các lượt sau ở lại slot mới, việc `done`; (c) SC-003 hai việc chạy cùng lúc (`concurrency: 2`) được giao hai slot khác nhau; (d) FR-004 sau khi việc `done`, bảng giữ slot của proxy không còn việc đó sau lượt dọn
- [x] T002 [US1] Trong tools/runner/proxy.py: bảng `HELD: dict[str, int]` (job → slot) và hàm `order_slots(job_id, slots)` đưa slot giữ (nếu có trong `slots`) lên đầu; với việc chưa giữ slot và `claude_plan.order() == "auto"`, sắp xếp ổn định theo số việc đang giữ mỗi slot (ít trước), giữ thứ tự `usable()` khi bằng nhau; chế độ `manual` không đổi thứ tự
- [x] T003 [US1] Trong `forward()` của tools/runner/proxy.py: dùng `order_slots(job["id"], usable())`; ghi `HELD[job_id] = slot` khi lượt trả mã < 400 qua slot đó; giữ nguyên đường 429, 401, khoá API dự phòng và giới hạn token
- [x] T004 [US1] Trong tools/runner/proxy.py: `prune_held(now)` chạy ≤ 1 lần mỗi 60 giây ở đầu `forward()`, bỏ khỏi `HELD` các việc mà `store.doc_get("job", id)` không còn hoặc có `status` thuộc `jobs.FINAL`; cho phép test gọi trực tiếp với `force=True`
- [x] T005 [US1] Chạy `sh tests/online/run.sh -k Rotation`; các test cũ `test_sc104…`, `test_manual_order…`, `test_sc105…` (chênh ≤ 20%) phải vẫn đạt; nếu `sc105` lệch thì chỉnh thứ tự chọn ở T002, không nới ngưỡng

**Checkpoint**: US1 chạy và test độc lập được.

## Phase 4: User Story 2 - Agent gọn hội thoại sớm hơn và giữ đúng thứ (P2)

**Goal**: agent nhận ngưỡng gọn 300.000 token và giới hạn đầu ra 20.000 ký tự (đổi được), có hướng dẫn gọn.

**Independent Test**: `sh tests/online/run.sh -k Thrift`

- [x] T006 [P] [US2] Thêm test vào tests/online/test_agent_thrift.py: (a) `worker.compact_env({})` trả `{"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "300000", "BASH_MAX_OUTPUT_LENGTH": "20000"}`; (b) với `STUDIO_AUTO_COMPACT_WINDOW=500000`, `STUDIO_BASH_MAX_OUTPUT=8000` trả đúng giá trị đó; (c) giá trị sai (`abc`, `50000` cho ngưỡng gọn — dưới 100000) trả mặc định; (d) `agent.rules()` có "When the conversation is compacted", "keep", "film name", "pending review", "drop"; (e) một việc phim chạy qua Studio giả có hai biến trong env gửi cho bộ chạy (dùng `fake_agent.py` ghi env ra tệp hoặc kiểm `env` của runner giả)
- [x] T007 [P] [US2] Trong tools/runner/worker.py: hàm `compact_env(environ) -> dict` đọc `STUDIO_AUTO_COMPACT_WINDOW` (số nguyên ≥ 100000, mặc định 300000) và `STUDIO_BASH_MAX_OUTPUT` (số nguyên ≥ 1000, mặc định 20000), giá trị sai thì dùng mặc định và `log.warning`; gộp kết quả vào `env` của việc ngay sau khối `env = {...}`
- [x] T008 [P] [US2] Trong tools/runner/agent.py: nối vào cuối `rules()` mục "When the conversation is compacted": giữ tên phim, bước đang làm, yêu cầu duyệt đang chờ, bước kế tiếp, tệp đã ghi, kết quả kiểm gần nhất; bỏ nội dung tệp đã đọc, log và đầu ra lệnh dài; sau khi gọn đọc `.compact-state.md` trong thư mục việc nếu cần

**Checkpoint**: US2 test độc lập được.

## Phase 5: User Story 3 - Lưu trạng thái trước khi gọn (P3)

**Goal**: ghi `<thư mục việc>/.compact-state.md` ngay trước mỗi lần gọn, không gọi Claude.

**Independent Test**: `sh tests/online/run.sh -k Thrift`

- [x] T009 [US3] Thêm test vào tests/online/test_agent_thrift.py: với thư mục việc tạm có `films/f/` (3 tệp, `checks.json` có tầng đạt và tầng lỗi) và transcript giả chứa lệnh `job step <mã> "Picture"`, `agent.save_compact_state(work, {"transcript_path": …, "trigger": "auto"})` ghi `.compact-state.md` có "auto", "Last step: Picture", tên 3 tệp, tóm tắt kiểm; tệp ≤ 8 KB với 500 tệp đổi (cắt còn 20); chạy < 1 s; thư mục chỉ đọc thì không ném lỗi
- [x] T010 [US3] Trong tools/runner/agent.py: `save_compact_state(work: Path, data: dict) -> None` theo data-model.md ("Last step" từ lệnh `job step <mã> "<bước>"` cuối cùng trong 2 MB cuối của transcript; "max 20" tệp đổi mới nhất trong `work/films/` bỏ qua thư mục ẩn; tóm tắt `checks.json` của phim mới nhất; cắt để ≤ 8 KB; mọi lỗi bị bắt và in stderr)
- [x] T011 [US3] Trong tools/runner/agent.py: `async def before_compact(input_data, tool_use_id, context)` gọi `save_compact_state(WORK, input_data)` và trả `{}`; thêm `"PreCompact": [HookMatcher(hooks=[before_compact])]` vào `hooks` của `ClaudeAgentOptions`

**Checkpoint**: cả ba user story đạt.

## Phase 6: Polish

- [x] T012 [P] Cập nhật CLAUDE.md (mục chế độ online / `tools/runner/`) một dòng: proxy giữ một tài khoản cho mỗi việc; biến `STUDIO_AUTO_COMPACT_WINDOW`, `STUDIO_BASH_MAX_OUTPUT`; tệp `.compact-state.md` (specs/030)
- [x] T013 [P] Ghi hai biến mới vào hướng dẫn triển khai deploy/README.md (mục biến môi trường của worker), nếu có mục đó
- [x] T014 Chạy 5 bộ test theo quickstart.md (`tests/run.sh`, `tests/learn/run.sh`, `tests/ui/run.sh`, `tests/filmcheck/run.sh`, `tests/online/run.sh`) và đối chiếu SC-001…SC-006

## Dependencies

- US1 (T001–T005), US2 (T006–T008), US3 (T009–T011) độc lập với nhau. US3 dùng chung tệp agent.py với T008 nên làm sau T008.
- T014 sau tất cả.

## Parallel

- T006, T007, T008 khác tệp nhau → song song. T012, T013 song song.

## Implementation Strategy

MVP = US1 (lợi lớn nhất: giữ bộ nhớ đệm). Rồi US2, US3, Polish, chạy đủ test, mở PR.
