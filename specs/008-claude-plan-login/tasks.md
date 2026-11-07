# Tasks: Xưởng online nội bộ chạy bằng gói Claude

**Input**: `specs/008-claude-plan-login/` (spec.md, plan.md, research.md, data-model.md, contracts/api-admin-claude.md, contracts/runner.md, quickstart.md). Nền là 007: `specs/007-online-studio/`.

**Tests**: có. Spec đòi test tự động cho SC-103 … SC-107. Test dùng Claude Code giả (`STUDIO_CLAUDE_BIN`) và dịch vụ Claude giả của 007, nên không cần mạng và không tốn hạn mức.

**Luật chung cho mọi task**:
- Chế độ `local` giữ nguyên. Sau mỗi phase, 4 bộ test phải đạt: `tests/run.sh`, `tests/learn/run.sh`, `tests/ui/run.sh`, `tests/online/run.sh`.
- Không sửa `lib/`. Không commit `deploy/.env` hay thư mục `/data/claude`.
- Không ghi mã đăng nhập, header `authorization` hay nội dung lời nhắc vào nhật ký (FR-104).
- Commit sau mỗi phase (hiến pháp, quy trình 4).

## Phase 1: Setup

- [ ] T001 Kiểm các mục "Kiểm khi implement" của research.md bằng một tài khoản Claude thật, trên máy này, với Claude Code đi kèm `claude-agent-sdk` trong `tools/.venv`. Dùng `CLAUDE_CONFIG_DIR` tạm, không có trình duyệt (`BROWSER=/bin/false`). Ghi kết quả vào `specs/008-claude-plan-login/research.md`, mục mới "Kết quả kiểm T001":
  - R1: `claude auth login --claudeai` in URL dạng `https://…/oauth/authorize?…` và đọc mã từ stdin; các trường JSON của `claude auth status --json`; `claude auth logout`.
  - R2: tên tệp và các trường của thông tin đăng nhập; lệnh nào làm mới mã truy cập mà không tốn hạn mức (thử `auth status` trước, bằng cách sửa `expiresAt` cho sắp hết hạn).
  - R3: Claude Code có `CLAUDE_CODE_OAUTH_TOKEN` cộng `ANTHROPIC_BASE_URL` trỏ tới một máy chủ ghi lại yêu cầu (chạy cục bộ) thì gửi những đường và header nào.
  - Claude Code ghi những tệp nào ngoài `CLAUDE_CONFIG_DIR` (ví dụ trong `$HOME`) khi đăng nhập, xem trạng thái và làm mới (cho T018).
  - R5: gửi một yêu cầu thật qua gói bằng Bearer, ghi các header `anthropic-ratelimit-*` của phản hồi. Nếu không gây được `429` thì ghi rõ là chưa kiểm được.
  - **Nếu một mục khác research thì dừng ở đây và hỏi người dùng** (hiến pháp II).
- [ ] T002 [P] Thêm `claude-agent-sdk` (ghim phiên bản giống `deploy/job.Dockerfile`) vào `tools/requirements-online.txt`. Thêm hàm `claude_bin()` vào `tools/studio/studio/claude_plan.py` (tệp mới): trả về `STUDIO_CLAUDE_BIN` nếu đặt, nếu không thì trả về tệp `claude` đi kèm gói `claude_agent_sdk` (tìm theo đường cài).
- [ ] T003 [P] Tạo `tests/online/fake_claude` (Python, có quyền chạy), giả các lệnh theo kết quả T001:
  - `auth login --claudeai`: in URL, đợi một dòng trên stdin. Mã `good-<email>` thì ghi `.credentials.json` giả (`accessToken = tok-<email>-<n>`, `expiresAt`) vào `$CLAUDE_CONFIG_DIR` và thoát 0. Mã khác thì in lỗi và thoát 1.
  - `auth status --json`: đọc tệp đó; mã truy cập sắp hết hạn thì tăng `<n>` (làm mới).
  - `auth logout`: xoá tệp.
  - `-p … --output-format json`: trả `{"structured_output": {"allowed": true, "reason": ""}}`.
  - Biến `FAKE_CLAUDE_REFRESH=fail` làm cho lệnh làm mới thất bại.
- [ ] T004 [P] Thêm vào `.gitignore`: `/data/claude/`. Thêm vào `tests/online/helpers.py`:
  - `fake_upstream()` nhận bảng `{mã truy cập: "ok" | "limit:<giây>" | "401"}`. `limit` trả `429` với header giờ dùng lại theo T001. Ghi mỗi yêu cầu nhận được (đường, header đã che giá trị `authorization`, mã nào đã dùng);
  - `sign_in(c, slot, email)` gọi API đăng nhập với `fake_claude`.

---

## Phase 2: Foundational (chặn mọi user story)

- [ ] T005 Sửa `tools/studio/studio/db.py`, tăng phiên bản lược đồ (data-model "Chuyển phiên bản lược đồ"):
  - bảng `claude_account(slot INTEGER PRIMARY KEY CHECK (slot BETWEEN 1 AND 5), email, plan, state CHECK IN ('signed_out','signed_in','limited','needs_signin'), rest_until, rest_step INTEGER DEFAULT 0, signin_mailed_at, checked_at)`, tạo sẵn slot 1 `signed_out`;
  - bảng `call(id INTEGER PRIMARY KEY, job_id, account_id, via, model, tokens_in, tokens_out, cache_write, cache_read, cost_usd REAL DEFAULT 0, at)`, chỉ mục `(via, at)` và `(account_id, at)`;
  - cột `job.tokens INTEGER DEFAULT 0`;
  - `password_hash` được null;
  - Settings: bỏ `signup_open`, `daily_cost_cap_usd`, `job_cost_cap_usd`; thêm `job_token_cap` mặc định `40000000`, khoảng hợp lệ 1 000 000 … 500 000 000.
  
  Thêm test chuyển từ cơ sở dữ liệu 007 có sẵn trong `tests/online/test_store_online.py`: tài khoản cũ còn nguyên (FR-113).
- [ ] T006 Viết phần lõi của `tools/studio/studio/claude_plan.py`:
  - `config_dir(slot)` = `$STUDIO_DATA/claude/slot-<n>`, tạo với quyền 700;
  - `run(slot, args, timeout, stdin=None)` chạy `claude_bin()` với `CLAUDE_CONFIG_DIR`, xoá `ANTHROPIC_API_KEY` và `ANTHROPIC_AUTH_TOKEN` khỏi môi trường, bọc trong `flock` của `$STUDIO_DATA/claude/slot-<n>.lock` (contracts/runner.md);
  - `status(slot, fresh)`: đọc `auth status --json`, ghi `email`, `plan`, `checked_at`; `signed_in` khi `loggedIn`;
  - `accounts()`: danh sách kèm `same_as` (slot nhỏ hơn cùng email), `plan_warning` (gói không phải Pro hay Max), `tokens_5h` (tổng token trong bảng Call của `plan:<n>` trong 5 giờ qua);
  - `usable(now)`: tài khoản dùng được theo data-model, xếp theo `tokens_5h` rồi theo slot (R4);
  - `ready()`: `usable()` khác rỗng hoặc có `ANTHROPIC_API_KEY`.
- [ ] T007 Thêm vào `claude_plan.py`:
  - `access_token(slot)`: đọc mã theo kết quả T001; còn dưới 10 phút thì chạy lệnh làm mới (T001) rồi đọc lại; không làm mới được thì trả None;
  - `mark_limited(slot, reset_at)`: không có giờ thì chờ tăng dần 2 → 4 → … → 300 giây theo `rest_step`;
  - `mark_ok(slot)`: `rest_step` về 0, `limited` quá hạn thành `signed_in`;
  - `mark_needs_signin(slot)`: xếp thư `claude_signin` cho admin nếu `signin_mailed_at` đang null;
  - `record_call(job_id, account_id, via, model, usage, cost)`.
- [ ] T008 [P] Thêm mẫu thư `invite` và `claude_signin` (tiếng Anh) vào `tools/studio/studio/mail.py`.
- [ ] T009 Viết `tests/online/test_claude_plan.py` cho T006–T007, chỉ dùng `fake_claude`:
  - quyền 700 của thư mục;
  - khoá tệp: hai lệnh `run` trên cùng slot không chạy chồng;
  - `same_as`, `plan_warning`;
  - thứ tự của `usable` theo `tokens_5h`;
  - chờ tăng dần;
  - làm mới mã;
  - đúng 1 thư cho mỗi lần hỏng.

**Checkpoint**: lõi tài khoản Claude chạy được với `fake_claude`; 4 bộ test đạt.

---

## Phase 3: User Story 1 - Đăng nhập gói Claude và chạy được một phim (P1) 🎯 MVP

**Goal**: một tài khoản Claude đăng nhập trên trang quản trị; phim chạy xong khi xưởng không có khoá API.

**Independent Test**: spec US1. Tự động thì dùng `fake_claude` và dịch vụ giả; bằng tay thì làm theo quickstart, bước 1–4.

- [ ] T010 [US1] Viết đăng nhập trong `tools/studio/studio/claude_plan.py` (research R1):
  - `start_login(slot)` huỷ lần đang chờ, chạy `auth login --claudeai` với `BROWSER=/bin/false`, đợi URL tối đa 30 giây, hẹn huỷ sau 10 phút (`STUDIO_CLAUDE_LOGIN_TTL`, mặc định 600 giây);
  - `submit_code(slot, code)` ghi mã vào stdin, đợi tiến trình thoát tối đa 30 giây. Thoát 0 thì gọi `status(fresh=True)`, đặt `signed_in`, xoá `signin_mailed_at`. Thoát khác 0 thì báo `bad_code`;
  - `logout(slot)`.
  
  Lần đăng nhập đang chờ chỉ giữ trong bộ nhớ của tiến trình web (data-model "Claude login").
- [ ] T011 [US1] Thêm vào `tools/studio/studio/api_online.py` (chỉ admin): `GET /admin/claude`, `POST /admin/claude/accounts/{slot}/login`, `POST …/code`, `POST …/logout`, `POST /admin/claude/refresh`, đúng mã lỗi của contracts/api-admin-claude.md. Lỗi `login_failed` lọc bỏ mọi chuỗi giống mã trước khi trả về.
- [ ] T012 [US1] Sửa `tools/runner/proxy.py`:
  - `job_of` nhận mã của việc qua `Authorization: Bearer` (chế độ gói) và qua `x-api-key` như cũ;
  - `forward` gọi một hàm mới `route(job, path, body, headers)`. Ở phase này hàm chỉ thử tài khoản đầu tiên của `usable()`: gửi `Authorization: Bearer <access_token>`, giữ nguyên `anthropic-beta`. Không có tài khoản nào thì đi qua khoá API như 007 (đổi sang `x-api-key`, bỏ `oauth-*` khỏi `anthropic-beta`);
  - ghi một hàng Call với `via`, cộng `job.tokens`; chỉ cộng `cost_usd` khi `via = api`;
  - đường lạ dưới `/v1/` và `/api/` trả `404` dạng lỗi Anthropic;
  - nhật ký chỉ ghi `via`, trạng thái và số token.
- [ ] T013 [US1] Sửa `tools/runner/worker.py` (contracts/runner.md):
  - container nhận `CLAUDE_CODE_OAUTH_TOKEN=<mã của việc>`, `ANTHROPIC_BASE_URL`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`, không còn `ANTHROPIC_API_KEY`;
  - vòng lặp chỉ nhận việc `queued` khi `claude_plan.ready()`;
  - trang việc hiện "Waiting for a Claude account" khi việc đang chờ vì lý do này.
  
  Sửa dòng chú thích đầu `tools/runner/agent.py` cho khớp.
- [ ] T014 [US1] Sửa `tools/studio/studio/moderation.py` theo research R6:
  - chạy `claude -p` với lời nhắc và lược đồ cũ trên tài khoản đầu tiên của `usable()`, ghi Call (`job_id` null);
  - không có tài khoản thì dùng khoá API như cũ;
  - không có cả hai thì `POST /jobs` trả `503 studio_not_ready`, không trừ lượt.
  
  `STUDIO_MODERATION=fake` giữ nguyên.
- [ ] T015 [US1] Thêm trang Admin → "Claude accounts" vào `tools/studio/studio/web/app.js`, `index.html`, `style.css`:
  - bảng tài khoản: slot, email, gói, trạng thái, giờ dùng lại, cảnh báo gói, đánh dấu trùng;
  - nút Sign in mở URL ở thẻ mới, kèm ô dán mã và nút Submit;
  - nút Sign out;
  - dòng cảnh báo "No Claude account signed in. Jobs cannot run." khi `ready` là false.
  
  Mọi chữ tiếng Anh. Có `@ts-check` như 006.
- [ ] T016 [US1] Viết `tests/online/test_claude_login.py`:
  - US1 #1–4, #6: đăng nhập với mã đúng và mã sai, đăng xuất, người không phải admin bị `403`;
  - phim giả chạy xong với `via = plan:1` khi không có `ANTHROPIC_API_KEY`;
  - container nhận đúng biến môi trường;
  - không có tài khoản và không có khoá API: `POST /jobs` trả `503 studio_not_ready`, không trừ lượt; việc đã `queued` từ trước thì nằm trong hàng;
  - dán mã đúng thì tài khoản thành `signed_in` trong ≤ 10 giây (US1 #2);
  - đăng nhập bỏ dở tự huỷ (rút 10 phút xuống vài giây bằng biến `STUDIO_CLAUDE_LOGIN_TTL`);
  - khởi động lại proxy và web: tài khoản vẫn `signed_in` (FR-105).
- [ ] T017 [US1] Viết `tests/online/test_secrets.py` cho SC-103 (US1 #5):
  - sau một việc giả, tìm chuỗi `tok-` thật của `fake_claude` trong: `/data/jobs/**`, nhật ký của proxy và worker, mọi phản hồi của `/admin/claude` và `/jobs/{id}`, biến môi trường và danh sách gắn (`-v`) của lệnh chạy container. Phải là 0 lần;
  - danh sách gắn không chứa `/data/claude` hay `studio.db`.
- [ ] T018 [US1] Sửa `deploy/web.Dockerfile` (cài `claude-agent-sdk` qua `deps online`, tạo `/data/claude` quyền 700 khi khởi động nếu chưa có) và `deploy/compose.yaml` (`ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}` và `HOME: /tmp/home` ở `web` và `proxy`, giữ web một tiến trình, sửa chú thích sơ đồ). Theo kết quả T001, nếu Claude Code cần ghi chỗ khác ngoài `/tmp` và `CLAUDE_CONFIG_DIR` thì thêm tmpfs cho chỗ đó.

**Checkpoint**: MVP. Một tài khoản gói chạy được phim. Commit.

---

## Phase 4: User Story 2 - Nhiều tài khoản, chia theo mức dùng, bỏ qua tài khoản hỏng (P2)

**Goal**: tối đa 5 tài khoản; mỗi lần gọi đi qua tài khoản dùng ít nhất; tự đổi tài khoản khi `429` hoặc `401`.

**Independent Test**: spec US2.

- [ ] T019 [US2] Thêm vào `claude_plan.py` và `api_online.py`:
  - `POST /admin/claude/accounts` tạo slot trống nhỏ nhất ≥ 2; đã đủ 5 thì `409 max_accounts`;
  - `DELETE /admin/claude/accounts/{slot}` đăng xuất, xoá thư mục và hàng; slot 1 thì `409 first_account`.
- [ ] T020 [US2] Viết đủ vòng thử của `route()` trong `tools/runner/proxy.py`, theo mã giả ở contracts/runner.md:
  - thử lần lượt các tài khoản của `usable()`;
  - `429` của gói (nhận biết theo T001): `mark_limited` rồi thử tài khoản kế tiếp;
  - `401`: làm mới một lần; vẫn `401` thì `mark_needs_signin` rồi thử tài khoản kế tiếp;
  - thành công thì `mark_ok`;
  - hết tài khoản: có khoá API thì gửi qua khoá. Không có khoá mà tài khoản sớm dùng lại nhất có `rest_until` trong ≤ 15 giây thì chờ rồi thử một lần. Còn lại thì `quotas.fail(job, "No Claude account is available until <giờ UTC>. Your credit was refunded.", "studio")`, thu hồi mã của việc, trả `429`;
  - chỉ gửi lại khi phản hồi chưa bắt đầu chạy dòng;
  - `529` và `5xx` trả nguyên.
- [ ] T021 [US2] Thêm vào trang "Claude accounts" (`web/app.js`): nút "Add Claude account" (ẩn khi đủ 5), nút Remove (không có ở slot 1, có hỏi xác nhận). Trạng thái `Limit reached` kèm giờ dùng lại theo giờ máy người xem, và `Needs sign-in`.
- [ ] T022 [US2] Viết `tests/online/test_rotation.py`:
  - US2 #1–7;
  - SC-104: tài khoản 1 trả `429` giữa việc, việc vẫn xong, tài khoản 1 thành `limited` kèm `rest_until`;
  - SC-105: 2 tài khoản, 10 việc giả như nhau, token lệch ≤ 20%;
  - `401` thì đúng 1 thư;
  - hết tài khoản: có khoá thì đi qua khoá (Call `via = api` có `cost_usd`); không có khoá thì việc lỗi do xưởng sau ≤ 15 giây, lượt được trả, lý do có giờ.

**Checkpoint**: commit.

---

## Phase 5: User Story 3 - Chỉ người được mời (P3)

**Goal**: bỏ đăng ký công khai; mời bằng email.

**Independent Test**: spec US3.

- [ ] T023 [US3] Sửa `tools/studio/studio/accounts.py` (research R8):
  - `signup()` luôn báo `403 signup_closed`;
  - `invite(email, by)` tạo Account `customer` có `password_hash` null cùng Token `purpose = invite` sống 7 ngày, xếp thư `invite`; email đã có thì `409 email_taken`;
  - `accept_invite(token, password, accept_terms)` đặt mật khẩu, ghi `email_verified_at` và `terms_accepted_at`, đánh dấu Token đã dùng, tạo phiên;
  - `revoke_invite(id)` xoá Account chưa có mật khẩu đó và Token của nó;
  - Account có `password_hash` null thì không đăng nhập được.
- [ ] T024 [US3] Thêm vào `api_online.py`: `POST /auth/invite`, `GET /admin/invites`, `POST /admin/invites`, `DELETE /admin/invites/{id}`, đúng mã lỗi của contract. Áp giới hạn tần suất của 007 cho `/auth/invite`.
- [ ] T025 [US3] Sửa `web/app.js`:
  - bỏ trang `#/signup` và liên kết "Create an account";
  - thêm trang `#/invite/<token>` (mật khẩu, đồng ý điều khoản);
  - thêm mục Admin → Members: ô mời, danh sách lời mời chưa dùng kèm nút Revoke.
- [ ] T026 [US3] Đổi `signup_verified()` trong `tests/online/helpers.py` thành tạo tài khoản qua lời mời, để các test của 007 vẫn chạy. Sửa `browser_us1.cjs` và `browser_account.cjs` nếu chúng mở `#/signup`.
- [ ] T027 [US3] Viết `tests/online/test_invites.py`:
  - SC-106: `POST /auth/signup` luôn `403`;
  - lời mời đúng; lời mời đã dùng, quá 7 ngày hoặc bị thu hồi thì `410`;
  - tài khoản chưa đặt mật khẩu không đăng nhập được;
  - tài khoản 007 cũ vẫn đăng nhập được (US3 #4).

**Checkpoint**: commit.

---

## Phase 6: User Story 4 - Mức dùng bằng token (P4)

**Goal**: báo cáo token theo việc, ngày, thành viên, tài khoản Claude; trần token mỗi việc.

**Independent Test**: spec US4.

- [ ] T028 [US4] Sửa `tools/studio/studio/quotas.py`:
  - bỏ trần chi phí ngày và việc ghi Usage day;
  - `usage(from, to)` tính từ Call: `days`, `by_account`, `by_claude` (contract);
  - `tokens_month` cho mỗi thành viên.
  
  Bỏ lỗi `503 daily_cap` ở `POST /jobs`.
- [ ] T029 [US4] Trong `tools/runner/proxy.py`, đổi kiểm trần chi phí thành `job.tokens >= job_token_cap`. Vượt trần thì việc lỗi do xưởng ("The job used more than its token limit and was stopped. Your credit was refunded.") và trả `429`.
- [ ] T030 [US4] Sửa `api_online.py` và `web/app.js`:
  - `GET /jobs/{id}` thêm `tokens`; `cost_usd` chỉ admin thấy;
  - trang Usage hiện calls và tokens theo ngày, theo thành viên, theo tài khoản Claude; chỉ phần `api` có USD;
  - danh sách thành viên hiện `tokens_month`;
  - Settings: bỏ 3 khoá cũ, thêm `job_token_cap`.
- [ ] T031 [US4] Sửa `tests/online/test_proxy.py`, `test_admin.py`, `test_quota.py`, `test_us4.py`, `browser_admin.cjs`:
  - bỏ các test trần chi phí ngày và trần chi phí của việc;
  - thêm test trần token;
  - SC-107: tổng token của `/admin/usage` bằng tổng bảng Call;
  - không dùng khoá API thì không chỗ nào hiện USD.

**Checkpoint**: commit.

---

## Phase 7: Polish & triển khai

- [ ] T032 [P] Sửa `deploy/README.md`:
  - đăng nhập gói trên trang quản trị;
  - khoá API là tuỳ chọn;
  - mời thành viên;
  - sao lưu `/data/claude`, và việc phải giữ kín thư mục này;
  - đoạn về điều khoản Anthropic: chỉ dùng nội bộ, chủ xưởng chịu trách nhiệm.
- [ ] T033 [P] Sửa `CLAUDE.md` (mục Cấu trúc, câu về chế độ online: gói Claude, `claude_plan.py`, lời mời) và `bin/studio` nếu lệnh `online admin` cần đổi.
- [ ] T034 Sửa `tests/online/live.py` và `live.sh`: in token theo việc và `via` thay cho `cost_usd`; không cần `ANTHROPIC_API_KEY` khi có tài khoản gói.
- [ ] T035 Chạy quickstart bằng tay với tài khoản thật: các bước 1–4 (SC-101, SC-102), rồi `live.sh` (007 T048) để ghi số token thực tế. Chỉnh mặc định `job_token_cap` nếu cần, ghi vào research R7. Ghi kết quả: đạt, đạt một phần hoặc thất bại (hiến pháp IV).

---

## Dependencies & Execution Order

- **Phase 1**: T001 chạy trước tiên. Nó có thể đổi chi tiết của T003, T004, T007, T020. T002–T004 chạy song song sau T001.
- **Phase 2** (T005 → T006 → T007 → T009; T008 song song) chặn mọi user story.
- **US1** (Phase 3) là MVP. T010 → T011 → T015; T012 → T013; T014 sau T006; T016, T017 sau T011–T014; T018 độc lập.
- **US2** cần T012 (hàm `route`). **US3** chỉ cần Phase 2, làm song song với US1 và US2 được. **US4** cần Call ghi đủ `via` (T012, T020).
- **Phase 7** sau cùng. T035 cần cả xưởng chạy được.

## Parallel Examples

- Phase 1: T002, T003, T004 cùng lúc.
- Sau Phase 2: một người làm US1 (proxy, worker), một người làm US3 (`accounts.py`, trang mời), vì hai phần sửa tệp khác nhau. Riêng `api_online.py` và `web/app.js` thì phải làm lần lượt.
- Phase 7: T032, T033 cùng lúc.

## Implementation Strategy

1. T001 trước: kiểm các giả định với tài khoản thật. Có gì khác thì hỏi người dùng rồi mới làm tiếp.
2. Phase 2 → US1 → dừng, kiểm MVP bằng quickstart bước 1–4.
3. US2 → US3 → US4, mỗi story xong thì chạy 4 bộ test và commit.
4. Phase 7, rồi `/speckit-converge`.
