# Tasks: Xưởng online nội bộ chạy bằng gói Claude

**Input**: `specs/008-claude-plan-login/` (spec.md, plan.md, research.md, data-model.md, contracts/api-admin-claude.md, contracts/runner.md, quickstart.md). Nền là 007: `specs/007-online-studio/`.

**Tests**: có. Spec đòi test tự động cho SC-103 … SC-107. Test dùng Claude Code giả (`STUDIO_CLAUDE_BIN`) và dịch vụ Claude giả của 007, nên không cần mạng và không tốn hạn mức.

**Luật chung cho mọi task**:
- Chế độ `local` giữ nguyên. Sau mỗi phase, 4 bộ test phải đạt: `tests/run.sh`, `tests/learn/run.sh`, `tests/ui/run.sh`, `tests/online/run.sh`.
- Không sửa `lib/`. Không commit `deploy/.env` hay thư mục `/data/claude`.
- Không ghi mã đăng nhập, header `authorization` hay nội dung lời nhắc vào nhật ký (FR-104).
- Commit sau mỗi phase (hiến pháp, quy trình 4).

## Phase 1: Setup

> **Đổi thứ tự (2026-11-08, người dùng duyệt)**: chủ xưởng muốn đăng nhập tài khoản thật từ giao diện của xưởng, không qua chat. Vì vậy:
> - Phần T001 không cần tài khoản đã kiểm xong (research "Kết quả kiểm T001").
> - Phần T001 cần tài khoản thật (trạng thái khi đã đăng nhập, tệp đăng nhập, cách làm mới mã, header hạn mức) làm sau T015, bằng tài khoản đăng nhập qua trang Admin → Claude accounts.
> - Làm trước: T003, T004 (phần `sign_in`), T005, T006, T008, T010, T011, T015 và test của chúng. `access_token` (T007) và mọi phần của bộ chuyển tiếp làm sau khi kiểm xong.
> - Bỏ các khoá cài đặt cũ (`signup_open`, `daily_cost_cap_usd`, `job_cost_cap_usd`) ở task dùng tới chúng (T023 cho `signup_open`, T028–T029 cho trần chi phí), không ở T005, để các bộ test vẫn đạt sau mỗi bước.

- [X] T001 Kiểm các mục "Kiểm khi implement" của research.md bằng một tài khoản Claude thật, trên máy này, với Claude Code đi kèm `claude-agent-sdk` trong `tools/.venv`. Dùng `CLAUDE_CONFIG_DIR` tạm, không có trình duyệt (`BROWSER=/bin/false`). Ghi kết quả vào `specs/008-claude-plan-login/research.md`, mục mới "Kết quả kiểm T001":
  - R1: `claude auth login --claudeai` in URL dạng `https://…/oauth/authorize?…` và đọc mã từ stdin; các trường JSON của `claude auth status --json`; `claude auth logout`.
  - R2: tên tệp và các trường của thông tin đăng nhập; lệnh nào làm mới mã truy cập mà không tốn hạn mức (thử `auth status` trước, bằng cách sửa `expiresAt` cho sắp hết hạn).
  - R3: Claude Code có `CLAUDE_CODE_OAUTH_TOKEN` cộng `ANTHROPIC_BASE_URL` trỏ tới một máy chủ ghi lại yêu cầu (chạy cục bộ) thì gửi những đường và header nào.
  - Claude Code ghi những tệp nào ngoài `CLAUDE_CONFIG_DIR` (ví dụ trong `$HOME`) khi đăng nhập, xem trạng thái và làm mới (cho T018).
  - R5: gửi một yêu cầu thật qua gói bằng Bearer, ghi các header `anthropic-ratelimit-*` của phản hồi. Nếu không gây được `429` thì ghi rõ là chưa kiểm được.
  - **Nếu một mục khác research thì dừng ở đây và hỏi người dùng** (hiến pháp II).
- [X] T002 [P] Thêm `claude-agent-sdk` (ghim phiên bản giống `deploy/job.Dockerfile`) vào `tools/requirements-online.txt`. Thêm hàm `claude_bin()` vào `tools/studio/studio/claude_plan.py` (tệp mới): trả về `STUDIO_CLAUDE_BIN` nếu đặt, nếu không thì trả về tệp `claude` đi kèm gói `claude_agent_sdk` (tìm theo đường cài).
- [X] T003 [P] Tạo `tests/online/fake_claude` (Python, có quyền chạy), giả các lệnh theo kết quả T001:
  - `auth login --claudeai`: in URL, đợi một dòng trên stdin. Mã `good-<email>` thì ghi `.credentials.json` giả (`accessToken = tok-<email>-<n>`, `expiresAt`) vào `$CLAUDE_CONFIG_DIR` và thoát 0. Mã khác thì in lỗi và thoát 1.
  - `auth status --json`: đọc tệp đó; mã truy cập sắp hết hạn thì tăng `<n>` (làm mới).
  - `auth logout`: xoá tệp.
  - `-p … --output-format json`: trả `{"structured_output": {"allowed": true, "reason": ""}}`.
  - Biến `FAKE_CLAUDE_REFRESH=fail` làm cho lệnh làm mới thất bại.
- [X] T004 [P] Thêm vào `.gitignore`: `/data/claude/`. Thêm vào `tests/online/helpers.py`:
  - `fake_upstream()` nhận bảng `{mã truy cập: "ok" | "limit:<giây>" | "401"}`. `limit` trả `429` với header giờ dùng lại theo T001. Ghi mỗi yêu cầu nhận được (đường, header đã che giá trị `authorization`, mã nào đã dùng);
  - `sign_in(c, slot, email)` gọi API đăng nhập với `fake_claude`.

---

## Phase 2: Foundational (chặn mọi user story)

- [X] T005 Sửa `tools/studio/studio/db.py`, tăng phiên bản lược đồ (data-model "Chuyển phiên bản lược đồ"):
  - bảng `claude_account(slot INTEGER PRIMARY KEY CHECK (slot BETWEEN 1 AND 5), email, plan, state CHECK IN ('signed_out','signed_in','limited','needs_signin'), rest_until, rest_step INTEGER DEFAULT 0, signin_mailed_at, checked_at)`, tạo sẵn slot 1 `signed_out`;
  - bảng `call(id INTEGER PRIMARY KEY, job_id, account_id, via, model, tokens_in, tokens_out, cache_write, cache_read, cost_usd REAL DEFAULT 0, at)`, chỉ mục `(via, at)` và `(account_id, at)`;
  - cột `job.tokens INTEGER DEFAULT 0`;
  - `password_hash` được null;
  - Settings: bỏ `signup_open`, `daily_cost_cap_usd`, `job_cost_cap_usd`; thêm `job_token_cap` mặc định `40000000`, khoảng hợp lệ 1 000 000 … 500 000 000.
  
  Thêm test chuyển từ cơ sở dữ liệu 007 có sẵn trong `tests/online/test_store_online.py`: tài khoản cũ còn nguyên (FR-113).
- [X] T006 Viết phần lõi của `tools/studio/studio/claude_plan.py`:
  - `config_dir(slot)` = `$STUDIO_DATA/claude/slot-<n>`, tạo với quyền 700;
  - `run(slot, args, timeout, stdin=None)` chạy `claude_bin()` với `CLAUDE_CONFIG_DIR`, xoá `ANTHROPIC_API_KEY` và `ANTHROPIC_AUTH_TOKEN` khỏi môi trường, bọc trong `flock` của `$STUDIO_DATA/claude/slot-<n>.lock` (contracts/runner.md);
  - `status(slot, fresh)`: đọc `auth status --json`, ghi `email`, `plan`, `checked_at`; `signed_in` khi `loggedIn`;
  - `accounts()`: danh sách kèm `same_as` (slot nhỏ hơn cùng email), `plan_warning` (gói không phải Pro hay Max), `tokens_5h` (tổng token trong bảng Call của `plan:<n>` trong 5 giờ qua);
  - `usable(now)`: tài khoản dùng được theo data-model, xếp theo `tokens_5h` rồi theo slot (R4);
  - `ready()`: `usable()` khác rỗng hoặc có `ANTHROPIC_API_KEY`.
- [X] T007 Thêm vào `claude_plan.py`:
  - `access_token(slot)`: đọc `claudeAiOauth.accessToken`; còn dưới 5 phút thì chạy `auth status` (T001: Claude Code làm mới ở mốc này) rồi đọc lại; không làm mới được thì trả None;
  - `mark_limited(slot, reset_at)`: không có giờ thì chờ tăng dần 2 → 4 → … → 300 giây theo `rest_step`;
  - `mark_ok(slot)`: `rest_step` về 0, `limited` quá hạn thành `signed_in`;
  - `mark_needs_signin(slot)`: xếp thư `claude_signin` cho admin nếu `signin_mailed_at` đang null;
  - `record_call(job_id, account_id, via, model, usage, cost)`.
- [X] T008 [P] Thêm mẫu thư `invite` và `claude_signin` (tiếng Anh) vào `tools/studio/studio/mail.py`.
- [X] T009 Viết `tests/online/test_claude_plan.py` cho T006–T007, chỉ dùng `fake_claude`:
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

- [X] T010 [US1] Viết đăng nhập trong `tools/studio/studio/claude_plan.py` (research R1):
  - `start_login(slot)` huỷ lần đang chờ, chạy `auth login --claudeai` với `BROWSER=/bin/false`, đợi URL tối đa 30 giây, hẹn huỷ sau 10 phút (`STUDIO_CLAUDE_LOGIN_TTL`, mặc định 600 giây);
  - `submit_code(slot, code)` ghi mã vào stdin, đợi tiến trình thoát tối đa 30 giây. Thoát 0 thì gọi `status(fresh=True)`, đặt `signed_in`, xoá `signin_mailed_at`. Thoát khác 0 thì báo `bad_code`;
  - `logout(slot)`.
  
  Lần đăng nhập đang chờ chỉ giữ trong bộ nhớ của tiến trình web (data-model "Claude login").
- [X] T011 [US1] Thêm vào `tools/studio/studio/api_online.py` (chỉ admin): `GET /admin/claude`, `POST /admin/claude/accounts/{slot}/login`, `POST …/code`, `POST …/logout`, `POST /admin/claude/refresh`, đúng mã lỗi của contracts/api-admin-claude.md. Lỗi `login_failed` lọc bỏ mọi chuỗi giống mã trước khi trả về.
- [X] T012 [US1] Sửa `tools/runner/proxy.py`:
  - `job_of` nhận mã của việc qua `Authorization: Bearer` (chế độ gói) và qua `x-api-key` như cũ;
  - `forward` gọi một hàm mới `route(job, path, body, headers)`. Ở phase này hàm chỉ thử tài khoản đầu tiên của `usable()`: gửi `Authorization: Bearer <access_token>`, giữ nguyên `anthropic-beta`. Không có tài khoản nào thì đi qua khoá API như 007 (đổi sang `x-api-key`, bỏ `oauth-*` khỏi `anthropic-beta`);
  - ghi một hàng Call với `via`, cộng `job.tokens`; chỉ cộng `cost_usd` khi `via = api`;
  - đường lạ dưới `/v1/` và `/api/` trả `404` dạng lỗi Anthropic;
  - nhật ký chỉ ghi `via`, trạng thái và số token.
- [X] T013 [US1] Sửa `tools/runner/worker.py` (contracts/runner.md):
  - container nhận `CLAUDE_CODE_OAUTH_TOKEN=<mã của việc>`, `ANTHROPIC_BASE_URL`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`, không còn `ANTHROPIC_API_KEY`;
  - vòng lặp chỉ nhận việc `queued` khi `claude_plan.ready()`;
  - trang việc hiện "Waiting for a Claude account" khi việc đang chờ vì lý do này.
  
  Sửa dòng chú thích đầu `tools/runner/agent.py` cho khớp.
- [X] T014 [US1] Sửa `tools/studio/studio/moderation.py` theo research R6:
  - chạy `claude -p` với lời nhắc và lược đồ cũ trên tài khoản đầu tiên của `usable()`, ghi Call (`job_id` null);
  - không có tài khoản thì dùng khoá API như cũ;
  - không có cả hai thì `POST /jobs` trả `503 studio_not_ready`, không trừ lượt.
  
  `STUDIO_MODERATION=fake` giữ nguyên.
- [X] T015 [US1] Thêm trang Admin → "Claude accounts" vào `tools/studio/studio/web/app.js`, `index.html`, `style.css`:
  - bảng tài khoản: slot, email, gói, trạng thái, giờ dùng lại, cảnh báo gói, đánh dấu trùng;
  - nút Sign in mở URL ở thẻ mới, kèm ô dán mã và nút Submit;
  - nút Sign out;
  - dòng cảnh báo "No Claude account signed in. Jobs cannot run." khi `ready` là false.
  
  Mọi chữ tiếng Anh. Có `@ts-check` như 006.
- [X] T016 [US1] Viết `tests/online/test_claude_login.py`:
  - US1 #1–4, #6: đăng nhập với mã đúng và mã sai, đăng xuất, người không phải admin bị `403`;
  - phim giả chạy xong với `via = plan:1` khi không có `ANTHROPIC_API_KEY`;
  - container nhận đúng biến môi trường;
  - không có tài khoản và không có khoá API: `POST /jobs` trả `503 studio_not_ready`, không trừ lượt; việc đã `queued` từ trước thì nằm trong hàng;
  - dán mã đúng thì tài khoản thành `signed_in` trong ≤ 10 giây (US1 #2);
  - đăng nhập bỏ dở tự huỷ (rút 10 phút xuống vài giây bằng biến `STUDIO_CLAUDE_LOGIN_TTL`);
  - khởi động lại proxy và web: tài khoản vẫn `signed_in` (FR-105).
- [X] T017 [US1] Viết `tests/online/test_secrets.py` cho SC-103 (US1 #5):
  - sau một việc giả, tìm chuỗi `tok-` thật của `fake_claude` trong: `/data/jobs/**`, nhật ký của proxy và worker, mọi phản hồi của `/admin/claude` và `/jobs/{id}`, biến môi trường và danh sách gắn (`-v`) của lệnh chạy container. Phải là 0 lần;
  - danh sách gắn không chứa `/data/claude` hay `studio.db`.
- [X] T018 [US1] Sửa `deploy/web.Dockerfile` (cài `claude-agent-sdk` qua `deps online`, tạo `/data/claude` quyền 700 khi khởi động nếu chưa có) và `deploy/compose.yaml` (`ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}` và `HOME: /tmp/home` ở `web` và `proxy`, giữ web một tiến trình, sửa chú thích sơ đồ). Theo kết quả T001, nếu Claude Code cần ghi chỗ khác ngoài `/tmp` và `CLAUDE_CONFIG_DIR` thì thêm tmpfs cho chỗ đó.

**Checkpoint**: MVP. Một tài khoản gói chạy được phim. Commit.

---

## Phase 4: User Story 2 - Nhiều tài khoản, chia theo mức dùng, bỏ qua tài khoản hỏng (P2)

**Goal**: tối đa 5 tài khoản; mỗi lần gọi đi qua tài khoản dùng ít nhất; tự đổi tài khoản khi `429` hoặc `401`.

**Independent Test**: spec US2.

- [X] T019 [US2] Thêm vào `claude_plan.py` và `api_online.py`:
  - `POST /admin/claude/accounts` tạo slot trống nhỏ nhất ≥ 2; đã đủ 5 thì `409 max_accounts`;
  - `DELETE /admin/claude/accounts/{slot}` đăng xuất, xoá thư mục và hàng; slot 1 thì `409 first_account`.
- [X] T020 [US2] Viết đủ vòng thử của `route()` trong `tools/runner/proxy.py`, theo mã giả ở contracts/runner.md:
  - thử lần lượt các tài khoản của `usable()`;
  - `429` của gói (nhận biết theo T001): `mark_limited` rồi thử tài khoản kế tiếp;
  - `401`: làm mới một lần; vẫn `401` thì `mark_needs_signin` rồi thử tài khoản kế tiếp;
  - thành công thì `mark_ok`;
  - hết tài khoản: có khoá API thì gửi qua khoá. Không có khoá mà tài khoản sớm dùng lại nhất có `rest_until` trong ≤ 15 giây thì chờ rồi thử một lần. Còn lại thì `quotas.fail(job, "No Claude account is available until <giờ UTC>. Your credit was refunded.", "studio")`, thu hồi mã của việc, trả `429`;
  - chỉ gửi lại khi phản hồi chưa bắt đầu chạy dòng;
  - `529` và `5xx` trả nguyên.
- [X] T021 [US2] Thêm vào trang "Claude accounts" (`web/app.js`): nút "Add Claude account" (ẩn khi đủ 5), nút Remove (không có ở slot 1, có hỏi xác nhận). Trạng thái `Limit reached` kèm giờ dùng lại theo giờ máy người xem, và `Needs sign-in`.
- [X] T022 [US2] Viết `tests/online/test_rotation.py` (SC-104, SC-105; phần còn lại nằm trong `test_plan_run.py`):
  - US2 #1–7;
  - SC-104: tài khoản 1 trả `429` giữa việc, việc vẫn xong, tài khoản 1 thành `limited` kèm `rest_until`;
  - SC-105: 2 tài khoản, 10 việc giả như nhau, token lệch ≤ 20%;
  - `401` thì đúng 1 thư;
  - hết tài khoản: có khoá thì đi qua khoá (Call `via = api` có `cost_usd`); không có khoá thì việc lỗi do xưởng sau ≤ 15 giây, lượt được trả, lý do có giờ.

**Checkpoint**: commit.

---

## Phase 5: User Story 3 - Users trong Settings, giống neb (P3)

**Goal**: bỏ đăng ký công khai; chủ xưởng thêm và quản lý người dùng trong Settings → Users (đổi ngày 2026-11-08, thay cho lời mời qua email).

**Independent Test**: spec US3.

- [X] T023 [US3] Sửa `tools/studio/studio/accounts.py` và `db.py`:
  - `signup()` cho `customer` luôn báo `403 signup_closed`; bỏ khoá `signup_open` khỏi cài đặt;
  - cột `accounts.last_login_at` (thêm khi mở cơ sở dữ liệu cũ), ghi trong `login()`;
  - `add_user(email, password, role)`, `update_user(id, role, disabled, password, by)`, `signout_all(id)`, `remove_user(id, by)` theo contract, giữ luật "ít nhất một Owner đang bật" và "không tự tắt, tự hạ, tự xoá".
- [X] T024 [US3] Thêm vào `api_online.py`: `GET/POST /admin/users`, `PUT/DELETE /admin/users/{id}`, `POST /admin/users/{id}/signout`, đúng mã lỗi của contract.
- [X] T025 [US3] Sửa `web/app.js`, `style.css`:
  - trang Settings có tab như neb: General (cài đặt), Users, Usage (bảng khách và chi phí cũ, đổi ở US4); tab nhớ theo `#/settings/<tab>`;
  - tab Users: "People who can sign in", nút Add user (email, mật khẩu, vai trò), bảng User · Role · Last sign-in · Sessions · menu ⋯ (Reset password, Make owner/member, Sign out everywhere, Turn off/on, Remove);
  - bỏ trang `#/signup` và liên kết "Create an account".
- [X] T026 [US3] Đổi `signup_verified()` trong `tests/online/helpers.py` thành tạo tài khoản qua `accounts.add_user`, để các test của 007 vẫn chạy. Sửa `browser_us1.cjs` (không còn đăng ký trên trang).
- [X] T027 [US3] Viết `tests/online/test_users.py` và mở rộng `browser_admin.cjs` (thêm, đổi vai trò, tắt, xoá):
  - SC-106: `POST /auth/signup` luôn `403`;
  - thêm Member → đăng nhập được, không vào được `/admin/*`; Make owner → vào được;
  - Reset password và Sign out everywhere đăng xuất mọi phiên; Turn off chặn đăng nhập và dừng việc đang chạy;
  - luật Owner cuối cùng và tự mình;
  - tài khoản 007 cũ vẫn đăng nhập được (US3 #5);
  - trình duyệt khổ điện thoại: thêm, đổi vai trò, tắt, xoá.

**Checkpoint**: commit.

---

## Phase 6: User Story 4 - Mức dùng bằng token (P4)

**Goal**: báo cáo token theo việc, ngày, thành viên, tài khoản Claude; trần token mỗi việc.

**Independent Test**: spec US4.

- [X] T028 [US4] Sửa `tools/studio/studio/quotas.py`:
  - bỏ trần chi phí ngày và việc ghi Usage day;
  - `usage(from, to)` tính từ Call: `days`, `by_account`, `by_claude` (contract);
  - `tokens_month` cho mỗi thành viên.
  
  Bỏ lỗi `503 daily_cap` ở `POST /jobs`.
- [X] T029 [US4] Trong `tools/runner/proxy.py`, đổi kiểm trần chi phí thành `job.tokens >= job_token_cap`. Vượt trần thì việc lỗi do xưởng ("The job used more than its token limit and was stopped. Your credit was refunded.") và trả `429`.
- [X] T030 [US4] Sửa `api_online.py` và `web/app.js`:
  - `GET /jobs/{id}` thêm `tokens`; `cost_usd` chỉ admin thấy;
  - trang Usage hiện calls và tokens theo ngày, theo thành viên, theo tài khoản Claude; chỉ phần `api` có USD;
  - danh sách thành viên hiện `tokens_month`;
  - Settings: bỏ 3 khoá cũ, thêm `job_token_cap`.
- [X] T031 [US4] Sửa `tests/online/test_proxy.py`, `test_admin.py`, `test_quota.py`, `test_us4.py`, `browser_admin.cjs`:
  - bỏ các test trần chi phí ngày và trần chi phí của việc;
  - thêm test trần token;
  - SC-107: tổng token của `/admin/usage` bằng tổng bảng Call;
  - không dùng khoá API thì không chỗ nào hiện USD.

**Checkpoint**: commit.

---

## Phase 7: Polish & triển khai

- [X] T032 [P] Sửa `deploy/README.md`:
  - đăng nhập gói trên trang quản trị;
  - khoá API là tuỳ chọn;
  - thêm người dùng trong Settings → Users;
  - sao lưu `/data/claude`, và việc phải giữ kín thư mục này;
  - đoạn về điều khoản Anthropic: chỉ dùng nội bộ, chủ xưởng chịu trách nhiệm.
- [X] T033 [P] Sửa `CLAUDE.md` (mục Cấu trúc, câu về chế độ online: gói Claude, `claude_plan.py`, Settings → Users) và `bin/studio` nếu lệnh `online admin` cần đổi.
- [X] T034 Sửa `tests/online/live.py` và `live.sh`: in token theo việc và `via` thay cho `cost_usd`; không cần `ANTHROPIC_API_KEY` khi có tài khoản gói.
- [X] T035 Chạy quickstart bằng tay với tài khoản thật: các bước 1–4 (SC-101, SC-102), rồi `live.sh` (007 T048) để ghi số token thực tế. Chỉnh mặc định `job_token_cap` nếu cần, ghi vào research R7. Ghi kết quả: đạt, đạt một phần hoặc thất bại (hiến pháp IV).
  - **Kết quả (2026-11-09): đạt một phần.**
    - SC-101: đăng nhập tài khoản Pro trên trang AI accounts xong, dán mã một lần; chưa bấm giờ.
    - SC-102: **đạt**. Phim 30 giây (`j-20261109-051230-736b`) xong không cần khoá API: −14,0 LUFS, đỉnh −1,1 dB, readcheck đạt. 44 phút, trong đó 20 phút treo (lỗi 4 dưới đây).
    - Chạy bằng worker trên máy (`RUNNER=local`), **không** qua container Docker: đường Docker cho một phim thật chưa kiểm (ảnh đã dựng, xưởng Docker đã lên được).
    - 4 lỗi chỉ lộ ra khi chạy thật, đã sửa và có test: dòng trả lời bị nén (`68550b9`); Claude Code giấu mã của việc khỏi Bash nên `job step` không tới (`fe9fcfe`); ảnh trên 1 MB vượt bộ đệm của SDK (`fe9fcfe`); dòng chỉ có ping treo 20 phút và bộ chuyển tiếp không tắt được (`6d0a979`). Thêm 2 sửa nhỏ: `STUDIO_HOME_DIR` khi chạy trên máy (`4b90321`), `HOME` cho Claude Code trong Docker (`9df12b8`).
    - Số token và hạn mức: research R7.


---

## Phase 8: Giao diện giống neb-creative-tool (2026-11-08, FR-118, FR-119)

Lấy bố cục và cách dùng của neb (`app/login`, `components/accounts/ClaudePlanAccount.tsx`, `parts.tsx`, `QuotaBar.tsx`, `Summary.tsx`), giữ màu và kiểu chữ của xưởng. Không lấy proxy, Codex, tài khoản trình duyệt, sắp thứ tự bằng tay hay sao lưu.

- [X] T036 Trang đăng nhập (`web/app.js`, `style.css`): thẻ giữa màn hình, logo và tên xưởng ở trên, "Welcome back" / "Sign in to continue.", nút chính rộng hết thẻ, chữ "Signing in…" khi đang gửi, lỗi trong khung đỏ.
- [X] T037 Tạo chủ xưởng lần đầu (FR-118), giống hệt neb: `accounts.setup_needed()`, `setup()`; `GET`/`POST /auth/setup` trong `api_online.py`; giới hạn tần suất `setup_ip`; trang đăng nhập hiện form "Create the owner account" (email, mật khẩu hai lần) khi `needed`. Test trong `tests/online/test_setup.py`.
- [X] T038 Trang "AI accounts" (`#/admin/claude`, mục "AI accounts" ở thanh bên): dòng tóm tắt (số tài khoản, ready, resting, need signing in, khoá API); thẻ "Claude · plan" có huy hiệu, mô tả, mỗi tài khoản một dòng (tên, huy hiệu trạng thái và gói, nút chính, menu ⋯ có Sign out và Remove), khung đăng nhập ngay dưới dòng, cảnh báo trùng tài khoản, chân thẻ có "Add account" và "How it works". Sửa `browser_claude.cjs`.
- [X] T039 Thanh hạn mức (FR-119): cột `claude_account.usage`; `claude_plan.note_usage(slot, headers)` đọc thông tin hạn mức theo kết quả T001 (R5); hiện hai thanh 5 giờ và tuần trên trang AI accounts. Phần đọc header làm sau khi T001 kiểm xong với tài khoản thật; bộ chuyển tiếp gọi `note_usage` ở T012.


---

## Phase 9: Thứ tự tài khoản Claude, giống neb (2026-11-09, FR-120)

- [X] T040 `db.py`: cột `claude_account.position` (thêm khi mở cơ sở dữ liệu cũ, giá trị đầu = slot); cài đặt `claude_order` mặc định `auto`. `claude_plan.py`: `accounts()` theo `position`; `usable()` theo `position` khi `manual`, theo token 5 giờ khi `auto`; `set_order(mode)`, `move_to_top(slot)` (đặt lên đầu, chuyển `manual`); tài khoản mới đứng cuối.
- [X] T041 `api_online.py`: `PUT /admin/claude/order`, `POST /admin/claude/accounts/{slot}/top`, trường `order` trong `GET /admin/claude`. `web/app.js`: công tắc "Auto: least used first / Manual: top to bottom" ở chân thẻ Claude · plan, mục ⋯ **Move to top** (không có ở tài khoản đầu khi đang Manual), nhãn "Used first" trên tài khoản đầu khi Manual.
- [X] T042 Test (`test_claude_login.py`, `test_rotation.py`, `browser_claude.cjs`): Manual dùng tài khoản trên cùng dù đã dùng nhiều hơn; trên cùng chạm hạn mức thì xuống tài khoản kế; Move to top chuyển sang Manual và đổi thứ tự; Auto không đổi hành vi cũ; mã lỗi.


---

## Phase 10: Sửa sau chạy thật, mức Trực tiếp (2026-11-09)

Các thay đổi nhỏ làm thẳng theo CLAUDE.md (≤ 2 tệp, không đổi dữ liệu hay API dùng chung), ghi lại để converge đối chiếu.

- [X] T043 Trang Films có mục **In progress**: phim đang làm, dải các bước (đã xong, đang làm, sắp tới; bước đã báo tính là xong dù khác thứ tự), thanh tiến độ, thời gian; danh sách tự làm mới (`817a342`, `test_films_progress.py`).
- [X] T044 Tiết kiệm token: hướng dẫn gọn `tools/runner/JOB.md` thay cho CLAUDE.md của repo; `job run` online chỉ in 20 dòng cuối; thống kê mỗi lượt chạy `agent_runs` cho chủ xưởng (`2cf5d43`, `test_agent_thrift.py`). Đo hiệu quả: bài A/B Opus và Sonnet trên cùng kịch bản (kết quả ghi vào research R7).
- [X] T045 Web trong Docker tắt trong tối đa 10 giây (`--timeout-graceful-shutdown`), như bộ chuyển tiếp: kết nối cập nhật trực tiếp làm một tiến trình web kẹt cả ngày khi chạy thật.

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

## Phase 11: Convergence

- [ ] T046 Chạy một phim thật qua bộ xưởng Docker (`sh bin/studio online up`, container `studio-job`, mạng `jobnet`, bộ chuyển tiếp trong compose) và ghi kết quả vào T035 per SC-102, plan: một việc một container (partial)
- [X] T047 Trang AI accounts hiện số việc đang chờ tài khoản Claude ("N jobs are waiting for a Claude account") per FR-110 (partial)
- [X] T048 Khi `status()` phát hiện đăng nhập không còn hiệu lực, dùng `mark_needs_signin` để gửi đúng 1 thư cho chủ xưởng per FR-109 (partial)
- [X] T049 Đổi nhãn "At its limit" trên trang AI accounts thành "Limit reached" per FR-102, FR-108 (contradicts)
- [ ] T050 Bấm giờ một lần đăng nhập tài khoản Claude thật từ lúc bấm Sign in, ghi vào T035 per SC-101 (partial)
- [X] T051 Bỏ mẫu thư `invite` và câu lỗi `daily_cap` không còn dùng per US3, FR-116 (unrequested)
