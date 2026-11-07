# Tasks: Xưởng phim online, bản dùng thử đầu tiên

**Input**: `specs/007-online-studio/` (spec.md, plan.md, research.md, data-model.md, contracts/api-online.md, contracts/runner.md, quickstart.md)

**Tests**: có. Spec đòi test tự động cho SC-003, SC-004, SC-005, SC-008, SC-009. Test online dùng tác tử giả và API Claude giả, nên không cần mạng và không tốn tiền. Test cần Docker được bỏ qua kèm lý do khi máy không có Docker.

**Luật chung cho mọi task**:
- Chế độ `local` (mặc định) giữ nguyên mọi hành vi của 001–006. Sau mỗi phase, 3 bộ test cũ phải vẫn đạt.
- Không sửa `lib/`.
- Không commit khoá API hay `deploy/.env`.

## Phase 1: Setup

- [X] T001 Tạo `tools/requirements-online.txt`: `argon2-cffi`, `python-multipart`, `httpx`, `anthropic`; ghim phiên bản đã phát hành ít nhất 2 tuần. Thêm lệnh `sh bin/studio deps online` cài tệp này vào `tools/.venv`, theo cách của `deps ui` trong `bin/studio`.
- [X] T002 [P] Tạo thư mục `tests/online/`: `run.sh` (theo mẫu `tests/ui/run.sh`, discover `tests/online`) và `helpers.py`. `helpers.py` có:
  - `OnlineProject`: STUDIO_ROOT tạm, `STUDIO_MODE=online`, `STUDIO_DATA` tạm, thư ghi ra tệp;
  - `client(account)` đã đăng nhập;
  - hàm `signup_verified(email)`.
- [X] T003 [P] Thêm vào `.gitignore`: `deploy/.env`, `/data/`, `tests/online/.tmp/`.

## Phase 2: Foundational (chặn mọi user story)

- [X] T004 Tạo `tools/studio/studio/db.py`:
  - Kết nối SQLite tại `$STUDIO_DATA/studio.db`, bật WAL và `foreign_keys`.
  - Hàm `tx()` mở `BEGIN IMMEDIATE`.
  - Chuyển lược đồ theo số phiên bản (bảng `meta`).
  - Tạo đủ các bảng của `data-model.md`: Account, Session, Token, Settings (1 hàng, giá trị mặc định đúng bảng Settings), Job, Review, Decision, RightsConfirmation, UsageDay, Outbox, RateLimit.
  - Ràng buộc: `email` duy nhất, chữ thường, ≤ 254 ký tự; `role` ∈ {customer, admin}; `purpose` ∈ {verify, reset}.
- [X] T005 Sửa `tools/studio/studio/store.py` để thêm `mode()` (đọc `STUDIO_MODE`, mặc định `local`). Sửa `jobs.py` và `reviews.py` để lưu bằng `db.py` khi `mode()=="online"`, và giữ nguyên tệp JSON khi `local`.
  - Hàm công khai giữ nguyên chữ ký, chỉ thêm tham số `owner`.
  - Job thêm `owner`, `input`, `charged`, `cost_usd`, `queued_at`, `run_count`, `agent_session`, `failure_kind` và trạng thái `queued`.
  - `reviews.KINDS` thêm `question` (log `Question n`) và `treatment` (log `Treatment review`).
  - Test trong `tests/online/test_store_online.py`.
- [X] T006 Tạo `tools/studio/studio/accounts.py`:
  - `signup`, `verify`, `login` (băm argon2; sai email hay sai mật khẩu cùng trả `bad_login`), `logout`, `forgot`, `reset` (huỷ mọi phiên), `current(request)`.
  - Phiên dùng cookie `studio_session` với `HttpOnly`, `Secure` (khi HTTPS), `SameSite=Lax`, hết hạn sau 30 ngày; chỉ lưu `sha256` của mã phiên.
  - Token dùng một lần: verify hết hạn sau 24 giờ, reset sau 1 giờ.
  - Mật khẩu tối thiểu 10 ký tự.
- [X] T007 [P] Tạo `tools/studio/studio/mail.py`:
  - `queue(to, template, data)` ghi vào Outbox.
  - `flush()` gửi qua SMTP (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `MAIL_FROM`); khi `MAIL_DIR` có giá trị thì ghi ra tệp `.eml`.
  - Có 7 mẫu thư tiếng Anh: verify, reset, job_done, job_failed, review_needed, review_timeout, account_deleted.
  - Thư lỗi được thử lại tối đa 5 lần.
- [X] T008 [P] Tạo `tools/studio/studio/ratelimit.py`: đếm theo cửa sổ trượt trong bảng RateLimit, khoá theo `(kind, ip|email)`:
  - signup 5 lần/giờ theo IP;
  - login 10 lần/15 phút theo email và theo IP;
  - forgot 3 lần/giờ theo email;
  - giao việc 20 lần/giờ theo tài khoản.

  Vượt mức thì ném `StudioError("rate_limited", …, 429)` kèm `retry_after`.
- [X] T009 Sửa `tools/studio/studio/server.py` ở chế độ online:
  - bỏ kiểm loopback và Host;
  - thêm middleware đăng nhập: `401 auth_required`, `403 locked`; kiểm `Origin` cho POST/PUT/DELETE, giữ `X-Studio: 1`;
  - lọc mọi điểm truy cập cũ theo `owner`, tài nguyên của khách khác trả `404`;
  - đường dẫn tệp phim, bộ tham chiếu và phong cách đổi sang `/data/accounts/<id>/…`;
  - `/events` chỉ gửi sự kiện của khách đang đăng nhập.

  Chế độ local không đổi.
- [X] T010 Tạo `tools/studio/studio/api_online.py`, gồm router `/auth/*` và `/me` (GET, PUT, DELETE) đúng `contracts/api-online.md`. Gắn router vào `server.py` khi chế độ online.
- [X] T011 [P] Thêm lệnh `sh bin/studio admin create <email>` (hỏi mật khẩu, tạo tài khoản `admin` đã xác minh; chỉ 1 admin) trong `bin/studio` và `tools/studio/studio_cli.py`.
- [X] T012 Test `tests/online/test_accounts.py` cho:
  - đăng ký, xác minh, đăng nhập, đăng xuất;
  - token hết hạn và token dùng lại;
  - đặt lại mật khẩu huỷ phiên cũ;
  - `signup_open=false` trả `403 signup_closed`;
  - giới hạn tần suất trả 429;
  - tài khoản bị khoá trả 403.

  Thêm test hai khách, trong đó mỗi điểm truy cập cũ của 003 trả `404` với tài nguyên của khách kia (SC-003).

**Checkpoint**: tài khoản chạy được; 3 bộ test cũ vẫn đạt.

## Phase 3: User Story 1 - Đăng ký và làm phim theo phong cách thư viện (P1) 🎯 MVP

**Goal**: khách mới giao được một phim, theo dõi, xem và tải phim; hạn mức giảm đúng.

**Independent Test**: `sh tests/online/run.sh -k us1` đạt với tác tử giả. Bài chạy thật ở quickstart §2 làm ra một phim thật.

### Tests (viết trước, phải fail)

- [X] T013 [P] [US1] Tạo `tests/online/test_quota.py` cho FR-005, FR-006 và SC-008:
  - Hạn mức 2: 10 luồng cùng `POST /jobs` thì đúng 2 lần `201`, còn lại `402 quota_exceeded` kèm `resets_at` là 00:00 ngày 1 tháng sau giờ Việt Nam.
  - Việc lỗi `failure_kind=studio` được trả lượt.
  - Khách tự dừng thì không được trả lượt.
  - Bị `content_rejected` thì không trừ lượt.
- [X] T014 [P] [US1] Tạo `tests/online/test_queue.py` cho FR-008a và SC-009: N=2, 20 việc của 5 khách chạy bằng tác tử giả. Kiểm qua bảng Job được ghi mỗi 50 ms rằng không lúc nào có hơn 2 việc `running`, và không khách nào có 2 việc `running`. Kiểm thêm `queue_position` đúng thứ tự nhận.
- [X] T015 [P] [US1] Tạo `tests/online/test_proxy.py` cho R3 và SC-005:
  - Dựng API Claude giả trả `usage` cố định.
  - Kiểm chi phí cộng đúng theo `price_table`.
  - Khoá thật không có trong yêu cầu từ container.
  - Mã của việc đã kết thúc bị từ chối.
  - Vượt `job_cost_cap_usd` thì việc thành failed/studio và lượt được trả.
  - Chạm `daily_cost_cap_usd` thì `POST /jobs` trả `503 daily_cap`, còn việc đang chạy vẫn xong.
- [X] T016 [P] [US1] Tạo `tests/online/fake_agent.py` để thay `agent.py` trong test. Tác tử giả đọc `/work/.input.json` và:
  - ghi 3 bước bằng `sh bin/studio job step`;
  - chép một mp4 mẫu 2 giây (tạo bằng ffmpeg trong `helpers.py`) vào `/work/films/<tên>/`;
  - chạy `job done`.

  Tác tử nhận các cờ `--ask` (tạo `review request --kind question`, thoát mã 10), `--fail`, và `--spend <usd>` (gọi API giả qua bộ chuyển tiếp).

### Implementation

- [X] T017 [US1] Tạo `tools/studio/studio/quotas.py`:
  - `settings()` và `update_settings(dict)`, kiểm khoảng cho phép (concurrency 1–16, các trần chi phí > 0, film_max_seconds 5–300).
  - `month_start_vn(now)` theo UTC+7.
  - `used(account, kind)`.
  - `reserve(account, kind)`: cùng giao dịch với việc tạo Job; ném `quota_exceeded` hoặc `daily_cap`.
  - `refund(job)`.
  - `add_cost(job, usd)`: cập nhật Job.cost_usd và UsageDay.
- [X] T018 [P] [US1] Tạo `tools/studio/studio/moderation.py`, hàm `check(idea) -> (ok, reason)`:
  - Một lệnh gọi `anthropic` Messages API với model trong Settings, `output_config.effort="low"`, và structured outputs `{allowed: bool, reason: str}`.
  - Chính sách: không bạo lực đồ hoạ, nội dung tình dục, thù ghét, mạo danh người thật hay thương hiệu, hay nêu tên kênh tham chiếu.
  - Khi `stop_reason=="refusal"` thì coi là từ chối.
  - Khi chạy test, dùng biến `STUDIO_MODERATION=fake` để thay bằng luật từ khoá.
  - Tham số SDK phải kiểm lại theo skill claude-api, không đoán.
- [X] T019 [US1] Trong `tools/studio/studio/api_online.py`, thêm:
  - `POST /jobs` loại `film`: kiểm `style` có trong thư viện hoặc trong `my-styles` của khách, `seconds ≤ film_max_seconds`, đã xác minh email, tối đa 3 việc chưa xong; gọi moderation rồi `quotas.reserve` và tạo Job `queued`.
  - `POST /jobs/{id}/stop`.
  - `GET /films/{name}/download` (`Content-Disposition: attachment`).
  - `DELETE /films/{name}`.

  Mã lỗi đúng `contracts/api-online.md`.
- [X] T020 [US1] Tạo `tools/runner/proxy.py` (FastAPI, nghe `proxy:8780`):
  - `POST /v1/messages` chuyển tiếp tới `ANTHROPIC_UPSTREAM` (mặc định `https://api.anthropic.com`) bằng `httpx`, kể cả khi phản hồi chạy dòng (SSE), và thay `x-api-key` bằng khoá thật.
  - Đọc `usage` từ phản hồi thường, hoặc từ sự kiện `message_delta` khi chạy dòng, rồi gọi `quotas.add_cost`.
  - Trả nguyên `429`, `529` và `5xx` của Anthropic kèm `retry-after` (R13), và ghi lúc có phản hồi thành công gần nhất của việc.
  - Kiểm trần chi phí của việc như R3.
  - `/internal/jobs/{id}/{step|log|done|fail}` và `/internal/reviews/{request|status}`, chỉ cho mã của chính việc đó.
  - Mã của việc: ngẫu nhiên 32 byte, lưu bản băm, thu hồi khi việc kết thúc.
  - Nhật ký không ghi nội dung lời nhắc.
- [X] T021 [US1] Sửa `tools/studio/studio_cli.py` để khi `STUDIO_MODE=online` và có `STUDIO_JOB`, các lệnh `job step|log|run|done|fail` và `review request|status` gọi `http://proxy:8780/internal/…` (địa chỉ lấy từ `STUDIO_PROXY`) bằng `ANTHROPIC_API_KEY` của việc. `review wait` in "kết thúc lượt: thoát mã 10" rồi thoát mã 10. `job fail` nhận thêm `--by studio|customer` (mặc định `studio`; FR-006a). Chế độ local không đổi.
- [X] T022 [US1] Tạo `tools/runner/worker.py` theo `contracts/runner.md`:
  - Vòng lặp 2 giây: chọn việc `queued` cũ nhất mà chủ của nó không có việc `running`, khi tổng số việc `running` < N, trong `db.tx()`.
  - Tạo `/data/jobs/<id>/`, ghi `.input.json`, cấp mã việc, bật container qua `RUNNER` (`docker`, hoặc `local` để test chạy tiến trình con không có container).
  - Đọc `.result.json`; khi xong thì chép phim về `/data/accounts/<owner>/films/`.
  - Mã thoát 10 thì đặt `waiting_review` và lưu `agent_session`.
  - Khởi động lại: chạy lại một lần, lần thứ hai thì failed/studio và trả lượt.
  - Gửi thư job_done, job_failed hoặc review_needed (khi việc chuyển sang `waiting_review`) nếu khách bật `email_notify` (FR-023).
  - Theo dõi: lượt chạy nào không có phản hồi thành công từ Claude trong 30 phút thì dừng, tính là failed/studio (R13).
  - Kiểm chất lượng (R14): khi tác tử báo xong một phim, chạy `ffmpeg -af ebur128` (−14 ±1 LUFS, đỉnh ≤ −1 dB) và `readcheck.mjs` của thư viện trong container, rồi ghi `qa`. Không đạt thì nối lại phiên một lần, kèm số đo. Vẫn không đạt thì failed/studio và trả lượt.
- [X] T023 [US1] (chưa chạy với Claude thật) Tạo `tools/runner/agent.py` (chạy trong container):
  - Đọc `/work/.input.json` và dựng lời nhắc tiếng Anh. Lời nhắc làm phim gồm: phong cách, ý tưởng, độ dài; luôn làm theo `CLAUDE.md` của `/studio`; mọi chữ trong phim bằng tiếng Anh; không nêu tên kênh; ghi bước bằng `job step`; kết thúc bằng `job done --film <tên>`.
  - Gọi Claude Agent SDK với thư mục làm việc `/work`, nạp `CLAUDE.md` và skill từ `/studio`, công cụ Read/Write/Edit/Bash/Glob/Grep, không có công cụ web, model trong Settings.
  - Ghi `.result.json` kèm mã phiên.
  - Khi có `.resume.json` thì nối lại phiên với tin nhắn là quyết định của khách.
  - **Trước khi viết, đọc tài liệu Agent SDK cho Python (code.claude.com/docs/en/agent-sdk) để lấy đúng tên tuỳ chọn (cwd, allowed tools, setting sources, resume, max turns), không đoán.**
- [X] T024 [P] [US1] Tạo `deploy/job.Dockerfile`:
  - Ubuntu 24.04, người dùng 1000.
  - ffmpeg 7 bản static, Node và Chromium cho Playwright.
  - Chép `bin/`, `tools/`, `CLAUDE.md`, `.claude/`, `library.lock`; dựng `tools/.venv` (`deps voice music learn --extra`); lấy thư viện theo `library.lock` vào `/studio/lib/lemo-opuscar`; cài `claude-agent-sdk`.
  - Đặt `ENTRYPOINT python /studio/tools/runner/agent.py`.
- [X] T025 [US1] Viết phần `docker` của worker trong `tools/runner/worker.py`, theo `contracts/runner.md`:
  - các cờ `--user 1000 --read-only --tmpfs /tmp --cap-drop ALL --pids-limit 512 --cpus --memory`;
  - mạng `jobnet`, gắn `/data/jobs/<id>:/work`;
  - giới hạn 60 phút mỗi lượt.

  Test `tests/online/test_sandbox.py`, bỏ qua khi không có Docker, kiểm rằng từ trong container:
  - không đọc được `/data/jobs/<khác>`;
  - `env` không có khoá thật;
  - `curl https://example.com` thất bại;
  - `curl http://proxy:8780` thành công.
- [X] T026 [US1] Trong `tools/studio/studio/web/` (`index.html`, `app.js`, `style.css`), thêm các trang ở chế độ online:
  - Sign up (ô đồng ý điều khoản), Log in, Verify, Forgot/Reset password.
  - Thanh trên có tên tài khoản, số lượt còn lại và nút Log out.
  - **New film**: chọn phong cách bằng thẻ của trang Library 004, ô ý tưởng, ô độ dài, ô "Review the treatment first".
  - Trang việc hiện `queue_position`, nút Stop, nút Download khi xong.

  Viết chữ tiếng Anh, dùng được trên điện thoại (bề rộng 360 px); `app.js` giữ `// @ts-check` với 0 lỗi. Giao diện nhận biết chế độ qua `GET /health` (thêm `mode`).
- [X] T027 [US1] Tạo `tests/online/test_us1.py`, chạy với `RUNNER=local` và tác tử giả:
  - đăng ký → xác minh qua tệp `.eml` → giao phim → `queued` → `running` → `done`;
  - tải phim được (`Content-Disposition: attachment`), còn lượt `used=1`;
  - chưa xác minh thì `403 unverified`;
  - hết lượt thì `402`;
  - tác tử giả xuất phim quá to (−8 LUFS) thì việc thành failed/studio và được trả lượt (FR-011);
  - `job fail --by customer` không trả lượt, `--by studio` có trả lượt (FR-006a);
  - API giả trả `529` liên tục quá thời hạn (thu ngắn trong test) thì việc thành failed/studio (R13);
  - thư `review_needed` được ghi khi tác tử giả chạy với `--ask`.

  Mở rộng `tests/ui/browser_check.cjs` (hoặc thêm `tests/online/browser_us1.cjs`) để đi trọn luồng trên trình duyệt. Đo thời gian từ mở trang tới giao việc, không tính bước đọc thư (SC-001, dưới 3 phút với thao tác tự động; ghi số đo), và kiểm bước mới hiện trên trang trong ≤ 5 giây sau `job step` (SC-007).

**Checkpoint**: MVP: khách lạ làm được phim. Có thể triển khai bản dùng thử chỉ với US1.

## Phase 4: User Story 2 - Học phong cách, duyệt trên web (P2)

**Goal**: học từ kênh YouTube hoặc video tải lên, duyệt 2 lần trên web, video gốc bị xoá, phong cách dùng được để làm phim.

**Independent Test**: `sh tests/online/run.sh -k us2` đạt.

- [X] T028 [P] [US2] Tạo `tests/online/test_us2.py`. Tác tử giả có thêm cờ `--learn`: tạo `references/<set>/videos/a.mp4`, ảnh ghép, yêu cầu duyệt style-1 rồi style-2 (thoát mã 10 mỗi lần), và lưu `my-styles/<slug>/`. Test kiểm:
  - Nguồn YouTube mà thiếu `rights_confirmed` thì `422 rights_required`; có xác nhận thì RightsConfirmation được lưu.
  - Hai lần duyệt Approve trên web thì việc nối lại phiên và xong.
  - Phong cách có trong `GET /styles` và dùng được ở `POST /jobs` loại film.
- [X] T029 [P] [US2] Tạo `tests/online/test_media_gone.py` cho FR-018, FR-019 và SC-004:
  - Sau khi việc học xong, dừng hoặc lỗi, và sau một lượt dọn, không còn tệp `.mp4 .mkv .webm .mov .m4a .wav .mp3 .opus` nào trong `/data/jobs/<id>` hay `/data/accounts/*/references`. Cũng không còn ảnh ghép (`profile/*/sheets/`) hay lời chép (`transcripts/`), và mỗi bộ tham chiếu còn ≤ 6 ảnh trong `proof/` (FR-018, FR-019, SC-004).
  - Trong lúc việc học còn chạy, `GET /sets/{set}/sheets` trả danh sách ảnh; sau khi kết thúc thì trả `{removed: true}`.
  - Thử mọi đường `/api/v1/sets/*` và `/uploads/*` với tên tệp video đều trả 404.
  - Tác vụ dọn xoá được tệp sót được tạo giả với thời gian kết thúc cách đây hơn 1 giờ.
- [X] T030 [US2] Trong `tools/studio/studio/api_online.py`, thêm:
  - `POST /uploads`: multipart; kiểm dung lượng ≤ `upload_max_mb`, độ dài ≤ `upload_max_minutes` bằng `ffprobe`, và định dạng video; lưu vào `/data/uploads/<owner>/<id>`; chỉ chủ của tệp dùng được.
  - `POST /jobs` loại `learn` với `source` `youtube` (`channel`, `count ≤ learn_max_videos`, `rights_confirmed`) hoặc `upload` (`uploads[]`), và tạo RightsConfirmation.
  - `DELETE /styles/{slug}` (`409 in_use` khi một việc đang dùng).
- [X] T031 [US2] Trong `tools/runner/worker.py`, thêm cho việc học:
  - Chép các tệp tải lên vào `/work/references/<set>/videos/`.
  - Với nguồn YouTube, dùng thêm mạng `jobnet-yt`. Tạo mạng này trong `deploy/compose.yaml` kèm một bộ lọc ra ngoài (ví dụ squid hoặc tinyproxy) chỉ cho `*.youtube.com`, `*.googlevideo.com`, `*.ytimg.com`.
  - Khi xong, chép `my-styles/<slug>` về `/data/accounts/<owner>/`. Từ `references/<set>` chỉ chép số đo (`profile/*.json`, summary) và tối đa 6 ảnh `proof/`; **không** chép video, ảnh ghép hay lời chép (hiến pháp 2.1.0).
- [X] T032 [US2] Trong `tools/runner/agent.py`, thêm lời nhắc học phong cách: làm theo skill `style-learn` với nguồn đã cho; tải bằng `sh bin/studio learn fetch` (YouTube) hoặc dùng video có sẵn; duyệt bằng `review request` (style-1, style-2) rồi kết thúc lượt; viết mọi tóm tắt bằng tiếng Anh. Khi nối lại phiên, đưa quyết định và góp ý vào tin nhắn.
- [X] T033 [US2] Trong `tools/runner/worker.py`, thêm tác vụ dọn mỗi 15 phút (R10):
  - Với Job `learn` đã kết thúc, chạy `sh bin/studio learn clean <set>` trong thư mục việc, rồi xoá mọi tệp có phần mở rộng âm thanh hay video (kể cả tệp tải lên của việc đó), ảnh ghép `profile/*/sheets/` và lời chép `transcripts/`.
  - Ghi `media_removed_at`.
  - Dừng các việc `waiting_review` quá `review_timeout_days`, gửi thư review_timeout.
- [X] T034 [US2] Trong `tools/studio/studio/web/app.js`, thêm:
  - Trang **Learn a style**: chọn nguồn (YouTube channel và số video, kèm ô xác nhận quyền bắt buộc với đúng câu chữ của hiến pháp 2.1.0; hoặc tải lên nhiều video, có thanh tiến độ).
  - Trang duyệt style-1 và style-2 dùng lại của 003.

  Không có thẻ `<video>` nào trỏ tới bộ tham chiếu.

Ghi chú khi làm (2026-11-07):
- T031: bộ tham chiếu nằm sẵn trong thư mục của khách trong lúc học. Container chỉ được gắn đúng bộ đó (`-v …/references/<set>:/work/references/<set>`), để khách duyệt ảnh ghép trên web. Khi kết thúc thì quét xoá tại chỗ, thay cho việc chép số đo về sau. Tệp tải lên được chép vào `/work/uploads/`, rồi tác tử chạy `learn fetch --files`.
- T033: không gọi `learn clean`. Worker tự quét bằng Python (`sweep` trong worker.py): xoá âm thanh và video, ảnh ghép, lời chép, `words.json`, `compare.jpg`, và xoá tên kênh khỏi `set.json`. Giữ số đo và tối đa 6 khung bằng chứng, kể cả khung gốc để so sánh (FR-018 cho phép). Worker cũng không cần cài công cụ học.
- `deploy/compose.yaml` hiện chỉ có `proxy`, `egress` (tinyproxy chỉ cho các tên miền YouTube) và hai mạng nội bộ. Phase 8 thêm web, worker, Caddy và bộ lọc socket Docker.

**Checkpoint**: US1 và US2 chạy độc lập.

## Phase 5: User Story 3 - Quản trị, hạn mức, chi phí (P3)

**Goal**: chủ xưởng đặt cài đặt, nâng hạn mức từng khách, khoá tài khoản, xem chi phí và dung lượng.

**Independent Test**: `sh tests/online/run.sh -k us3` đạt.

- [X] T035 [P] [US3] Tạo `tests/online/test_admin.py`. Kiểm:
  - Khách gọi `/admin/*` thì `403 forbidden`.
  - Đổi hạn mức mặc định có hiệu lực ngay (US3/AC1), và hạn mức riêng ghi đè mặc định.
  - `signup_open=false` (US3/AC3).
  - Khoá tài khoản thì đăng nhập bị chặn và việc đang chạy chuyển `stopped` (US3/AC4).
  - `/admin/usage` khớp tổng cost_usd của Job.
  - Giá trị cài đặt ngoài khoảng thì `422`.
- [X] T036 [US3] Trong `tools/studio/studio/api_online.py`, thêm `/admin/settings` (GET, PUT), `/admin/accounts` (GET kèm `storage_mb` tính bằng `du` các thư mục của khách, có bộ nhớ đệm 10 phút), `/admin/accounts/{id}` (PUT; `locked` thì `jobs.finish(stopped)` cho mọi việc chưa xong và worker dừng container), và `/admin/usage`.
- [X] T037 [US3] Trong `tools/studio/studio/web/app.js`, thêm trang **Admin** (chỉ hiện với admin):
  - form Settings;
  - bảng khách (tìm theo email, sửa hạn mức, khoá);
  - bảng chi phí theo ngày và tổng dung lượng.

## Phase 6: User Story 4 - Khách quản lý tài khoản và dữ liệu (P4)

**Independent Test**: `sh tests/online/run.sh -k us4` đạt.

- [ ] T038 [P] [US4] Tạo `tests/online/test_us4.py`:
  - đổi mật khẩu (cần mật khẩu cũ);
  - tắt email thông báo;
  - xoá phim hoặc phong cách;
  - `DELETE /me` thì đăng xuất ngay và đăng nhập lại bị từ chối;
  - sau lượt dọn (giả lập thời gian 30 ngày), mọi hàng và thư mục của khách đã hết, kể cả RightsConfirmation.
- [ ] T039 [US4] Trong `accounts.py` và `api_online.py`, viết `PUT /me` và `DELETE /me` (đặt `deleted_at`, huỷ phiên, dừng việc). Trong `tools/runner/worker.py`, thêm bước xoá hẳn (hàng trong cơ sở dữ liệu và `/data/accounts/<id>`, `/data/uploads/<id>`) cho tài khoản có `deleted_at` quá 30 ngày, và gửi thư account_deleted ngay khi khách yêu cầu.
- [ ] T040 [US4] Trong `tools/studio/studio/web/app.js`, thêm trang **Account**: số lượt còn lại và ngày làm mới, đổi mật khẩu, công tắc email, nút xoá tài khoản (phải gõ lại mật khẩu).

## Phase 7: Hỏi lại, duyệt kịch bản, sửa phim (FR-014, FR-015)

Các yêu cầu này thuộc luồng làm phim, nhưng xếp sau US1 để MVP gọn.

- [ ] T041 [P] [US1] Tạo `tests/online/test_film_dialog.py` với tác tử giả:
  - `--ask` tạo `question`; khách trả lời qua `POST /reviews/{id}/decision {value: approve, note: <câu trả lời>}` thì việc nối lại phiên.
  - Tối đa 3 câu hỏi, câu thứ 4 bị `422`.
  - `review_treatment` tạo yêu cầu `treatment`; Request changes có góp ý.
  - `revise_of` tốn 1 lượt và tạo phim `<tên>-r1`, giữ phim cũ.
- [ ] T042 [US1] Trong `reviews.py`, thêm luật cho `question` (≤ 3 mỗi việc) và `treatment`. Trong `agent.py`, thêm vào lời nhắc làm phim: được hỏi lại tối đa 3 câu bằng `review request --kind question --summary <file>` khi ý tưởng chưa rõ; khi `review_treatment` thì gửi kịch bản để duyệt trước khi dựng. Với `revise_of`, chép phim cũ vào `/work` và làm bản `-r<n>` theo góp ý.
- [ ] T043 [US1] Trong `app.js`, thêm vào trang việc: khung trả lời câu hỏi (ô chữ và nút Send), duyệt kịch bản (dùng lại trang duyệt), và nút **Request changes** trên phim đã xong (ô góp ý, báo "uses 1 film credit").

## Phase 8: Polish & triển khai

- [ ] T044 [P] Tạo `deploy/web.Dockerfile` (web, proxy và worker dùng chung ảnh, khác lệnh chạy), `deploy/compose.yaml` (các dịch vụ `web`, `proxy` (chỉ trên `jobnet`), `worker`, `docker-socket-proxy` (chỉ cho phép containers create/start/inspect/stop/remove/logs; worker gọi Docker qua dịch vụ này, **không** gắn `docker.sock` thật vào worker; xem runner.md), `caddy`, `egress-yt`; volume `/data`; mạng `jobnet` (internal), `jobnet-yt`. Worker từ chối mọi ảnh khác `studio-job:*`) và `deploy/Caddyfile` (tên miền lấy từ `.env`, chuyển `/` tới web, header bảo mật HSTS, CSP như 003). Thêm `deploy/.env.example` gồm `ANTHROPIC_API_KEY`, `SMTP_*`, `MAIL_FROM`, `DOMAIN`, `STUDIO_DATA=/data`.
- [ ] T045 [P] Thêm lệnh `sh bin/studio online up|down|logs` trong `bin/studio`: chạy `docker compose -f deploy/compose.yaml`; thiếu Docker thì báo rõ, không tự cài (CLAUDE.md).
- [ ] T046 [P] Viết `deploy/README.md` bằng tiếng Việt, ngắn:
  - chọn máy chủ (Ubuntu 24.04, khoảng 8 vCPU, 16 GB RAM);
  - trỏ tên miền về máy chủ;
  - điền `.env`;
  - chạy `online up`;
  - `admin create`;
  - sao lưu `/data` (chép `studio.db` bằng `sqlite3 .backup` và thư mục phim);
  - nhắc hỏi luật sư trước khi mở đăng ký (hiến pháp 2.1.0).
- [ ] T047 [P] Tạo trang Terms và trang Content policy (chữ mẫu, chủ xưởng sửa trong `deploy/terms.md`) phục vụ ở `/terms`; đăng ký bắt buộc đồng ý (Assumptions của spec).
- [ ] T048 Viết `tests/online/live.sh` (chạy bằng tay, tốn tiền, hỏi xác nhận trước): bật stack `online up` ở localhost, làm 3 phim 30 giây và 1 lần học từ 3 video mẫu tải lên. In thời gian và cost_usd của mỗi việc (SC-006), và chạy kiểm tra âm thanh (−14 ±1 LUFS, đỉnh ≤ −1 dB) và kiểm tra đọc chữ trên từng phim (SC-002).
- [ ] T049 Cập nhật `CLAUDE.md` (mục Cấu trúc: `tools/runner/`, `deploy/`, `tests/online/run.sh`, lệnh `online`, `admin`) và `specs/003-studio-ui/contracts/cli.md` (hành vi `job`/`review` ở chế độ online).
- [ ] T050 Chạy đủ 4 bộ test: `sh tests/run.sh`, `sh tests/learn/run.sh`, `sh tests/ui/run.sh`, `sh tests/online/run.sh`; kiểm tra kiểu `app.js`; đối chiếu SC-001…SC-009. Ghi rõ kết quả cho từng SC: đạt, đạt một phần, hay chưa chạy được (ví dụ SC-006 cần bài chạy thật).

## Dependencies

- Phase 1 → Phase 2 → US1 (Phase 3). US1 là nền chạy việc (worker, proxy, agent) cho mọi story sau.
- US2 cần T020–T025 của US1. US3 cần T017 (quotas) và T019. US4 chỉ cần Phase 2.
- Phase 7 cần US1. Phase 8 cần US1; T048 cần US1 và US2.
- Trong mỗi story: viết test trước (phải fail), rồi viết code.

## Parallel examples

- Phase 2: T007, T008, T011 song song sau T004.
- US1: T013, T014, T015, T016 song song; T018, T024 song song với T017.
- US2: T028 và T029 song song. US3 (T035–T037) và US4 (T038–T040) làm song song được sau US1.
- Phase 8: T044–T047 song song.

## Implementation Strategy

1. **MVP = Phase 1, 2, 3.** Khách lạ làm được phim. Dừng lại: chạy bài chạy thật một phim, xem chi phí thật, rồi người dùng duyệt.
2. Thêm US3 (quản trị) **trước khi mở đăng ký công khai**, vì cần trần chi phí và nút khoá tài khoản.
3. Thêm US2, Phase 7, US4, rồi Phase 8.
4. Commit sau mỗi phase (hiến pháp: Quy trình làm việc).

Tổng cộng 50 task. Vượt mức "khoảng 15" của mức Nhẹ, đúng với mức Đầy đủ. Nên làm qua nhiều phiên, mỗi phiên một hai phase.
