# Tasks: Settings → Worker và API tokens

**Input**: `specs/009-settings-worker-tokens/` (spec.md, plan.md, research.md, data-model.md, contracts/api-tokens-worker.md, contracts/mcp.md, quickstart.md). Nền là 008: `specs/008-claude-plan-login/`.

**Tests**: có. Spec ghi SC-203 … SC-209 là "kiểm tự động". Test dùng `unittest` như 007/008, Playwright cho trình duyệt, client MCP của thư viện `mcp` (trong tiến trình) cho máy chủ MCP, tác tử giả cho SC-208.

**Luật chung cho mọi task**:
- Chế độ `local` giữ nguyên. Sau mỗi phase, 4 bộ test phải đạt: `tests/run.sh`, `tests/learn/run.sh`, `tests/ui/run.sh`, `tests/online/run.sh`.
- Không sửa `lib/`. Không ghi mã API đầy đủ, header `Authorization` hay nội dung yêu cầu vào nhật ký (FR-210, FR-218).
- Mọi chữ trên giao diện bằng tiếng Anh; `app.js` giữ `@ts-check`.
- Commit sau mỗi phase.

## Phase 1: Setup

- [ ] T001 Ghim `mcp==2.3.0` vào `tools/requirements-online.txt` (đã có sẵn vì `claude-agent-sdk` cần; research R5). Kiểm `deploy/Caddyfile`: Caddy có ghi header `Authorization` vào nhật ký truy cập không (research R8); ghi kết quả vào research R8. Nếu có thì sửa ở T024.
- [ ] T002 [P] `tools/studio/studio/ratelimit.py`: `hit(kind, key, limit=None, window=None)` nhận giới hạn và cửa sổ riêng (dùng cho mã API, research R3); hành vi cũ giữ nguyên khi không truyền.

---

## Phase 2: Foundational (chặn mọi user story)

- [ ] T003 `tools/studio/studio/db.py`: lược đồ phiên bản **3** (data-model): bảng `api_token` (hash duy nhất), `token_request` (chỉ mục `(token_id, at)`), `idempotency` (khoá chính `(account_id, key_hash)`), `worker_beat`, `ticket`. Cơ sở dữ liệu 008 (phiên bản 2) tự nâng cấp, không mất dữ liệu. Thêm test nâng cấp vào `tests/online/test_store_online.py`.
- [ ] T004 `tools/studio/studio/tokens.py` (mới), theo data-model và research R1–R3, R9:
  - `create(owner, name, role, can_spend, rate_per_min, expires)` → `(token, secret)`: `secret = "fs_" + token_urlsafe(32)`, lưu `sha256` và 8 ký tự đầu; tên 1–60 ký tự; `role = "admin"` chỉ khi người tạo là Owner; `rate_per_min` ∈ {10, 30, 60, 120, 300}; `expires` ∈ {7d, 30d, 90d, 1y, never}; tối đa 20 mã Active mỗi người (`409 too_many_tokens`);
  - `resolve(secret)` → `(account, token, effective_role)` hoặc None: sai, thu hồi, hết hạn, người sở hữu bị tắt hay xoá → None; vai trò thực = mức thấp hơn giữa mã và người sở hữu;
  - `revoke(id, by)`, `list(owner=None)` (kèm `requests_today`, `blocked_today`, `status`), `log(id, limit)`;
  - `record(token, method, path, outcome, ip)`: một hàng `token_request`; xoá hàng > 30 ngày tối đa mỗi giờ; `last_used_at` tối đa mỗi 5 phút.
- [ ] T005 `tools/studio/studio/server.py` (`online_guard`) và `api_online.py` (`admin()`), theo contract "Xác thực bằng mã":
  - có `Authorization: Bearer fs_…` → `tokens.resolve`; bỏ qua cookie và không kiểm `X-Studio`/Origin; `request.state.account` là người sở hữu với vai trò thực, `request.state.token` là mã;
  - mã hỏng → `401 bad_token`; đường cấm (`/me/tokens*`, `/admin/tokens*`, `/admin/users*`, `/admin/claude*`, `PUT /me`, `DELETE /me`) → `403 token_forbidden`; vượt giới hạn mỗi phút → `429 rate_limited` + `Retry-After`;
  - ghi nhật ký mỗi yêu cầu có mã với `outcome` đúng (data-model: Token request), kể cả khi route trả `403 forbidden`;
  - `admin()` dùng vai trò thực.
- [ ] T006 `tests/online/test_tokens.py` (phần nền): dạng mã và chỉ lưu băm; vai trò thực (Owner bị hạ xuống Member thì mã Owner chỉ còn quyền Member); mã thu hồi, hết hạn, người sở hữu bị tắt hay xoá → `401`; có mã thì bỏ qua cookie và không cần `X-Studio`; từng đường cấm → `403 token_forbidden`; vượt giới hạn → `429` + `Retry-After`; nhật ký ghi đúng `outcome`; hàng > 30 ngày bị xoá.

**Checkpoint**: mã API gọi được mọi API sẵn có trong giới hạn của nó; 4 bộ test đạt. Commit.

---

## Phase 3: User Story 1 - Tab Worker (P1) 🎯 MVP

**Goal**: Owner thấy worker còn chạy không, đang làm gì, hàng đợi và 20 việc mới nhất.

**Independent Test**: spec US1.

- [ ] T007 [US1] `tools/runner/worker.py`: ghi `worker_beat` (`id = <tên máy>:<pid>`) khi khởi động, mỗi 5 giây, và ngay khi bắt đầu hay xong một việc, kèm danh sách việc đang chạy; xoá hàng của mình khi dừng êm; xoá hàng > 24 giờ khi khởi động (research R4).
- [ ] T008 [US1] `tools/studio/studio/api_online.py`: `GET /admin/worker` đúng contract: `workers` (`running` khi báo sống ≤ 30 giây, `not_responding` khi lâu hơn, ẩn khi > 10 phút), `counts` (`queued`, `running`, `waiting_review`, `waiting_claude`), `latest` (20 việc mới nhất của mọi người, lỗi cắt còn 300 ký tự).
- [ ] T009 [US1] `tools/studio/studio/web/app.js`, `style.css`: Settings → tab **Worker** (thêm vào `SETTINGS_TABS`): hộp Status (huy hiệu "Running · idle/busy", "Not responding", "No worker is running" kèm lệnh bật worker; từng tiến trình: busy with / idle, "last beat N s ago"), bốn ô đếm, Latest jobs (huy hiệu trạng thái, loại, tên link tới trang việc, email, "… ago", lỗi 2 dòng + "Details"); đọc lại mỗi 5 giây khi tab đang mở, dừng khi rời tab.
- [ ] T010 [US1] `tests/online/test_worker_status.py` (đồng hồ giả): running / not_responding / ẩn theo ngưỡng; busy_with đúng việc; bốn ô đếm khớp trạng thái thật (SC-203); `latest` đúng 20 việc mới nhất; Member và mã Member bị `403`; mã Owner đọc được. `tests/online/browser_worker.cjs` (khổ điện thoại): tab hiện đúng, tự đọc lại.

**Checkpoint**: MVP. Commit.

---

## Phase 4: User Story 2 - Người dùng tự tạo mã (P2)

**Goal**: mọi người dùng tạo mã cho tác tử của mình; mã giao phim được khi có quyền dùng lượt, không trùng khi thử lại.

**Independent Test**: spec US2.

- [ ] T011 [US2] `api_online.py`: `GET /me/tokens`, `POST /me/tokens` (trả `secret` đúng một lần), `DELETE /me/tokens/{id}`, `GET /me/tokens/{id}/log`, đúng mã lỗi của contract; chỉ bằng cookie (T005 đã chặn mã).
- [ ] T012 [US2] `POST /jobs`: mã không có `can_spend` → `403 spend_not_allowed`, trước khi kiểm nội dung hay trừ lượt; ghi nhật ký `no_spend` (FR-212).
- [ ] T013 [US2] Idempotency-Key ở `POST /jobs` (research R10): khoá mới → như thường, hàng `idempotency` ghi trong cùng giao dịch với `quotas.reserve`; cùng khoá cùng thân trong 24 giờ → `200` việc cũ + `Idempotent-Replayed: true`, nhật ký `replay`, không kiểm nội dung, không trừ lượt; khác thân → `409 idempotency_conflict`; xoá hàng > 24 giờ.
- [ ] T014 [US2] `web/app.js`, `style.css`: trang **Your account** có mục **API tokens**: danh sách mã của mình (tên, 8 ký tự đầu, vai trò, quyền dùng lượt, requests/blocked hôm nay, lần dùng gần nhất, hạn, trạng thái), nút **New token** (tên; vai trò chỉ hiện khi là Owner; quyền dùng lượt; giới hạn mỗi phút; hạn 7 ngày / 30 ngày / 90 ngày / 1 năm / Never với cảnh báo khi Never), hộp thoại hiện mã một lần với **Copy token**, **Copy MCP command**, **Copy for an agent** (đoạn hướng dẫn theo FR-217); khung **For agents** (Base URL, header, OpenAPI, docs, MCP, lệnh `claude mcp add`, JSON cho trình MCP khác, các giới hạn của mã).
- [ ] T015 [US2] `tests/online/test_tokens.py` (phần US2): Member tạo mã, không xin được vai trò Owner, tối đa 20 mã; `secret` chỉ có trong phản hồi tạo; mã không dùng lượt giao phim bị `403` mà xem việc được; mã có quyền giao phim, trừ lượt của người sở hữu; mã Member gọi API quản trị `403`. `tests/online/test_idempotency.py`: SC-209 (5 yêu cầu cùng lúc cùng khoá → 1 việc, 1 lượt), khác thân → `409`, hết 24 giờ → khoá dùng lại được. `tests/online/browser_tokens.cjs` (khổ điện thoại): tạo mã, thấy mã một lần, các nút Copy.

**Checkpoint**: commit.

---

## Phase 5: User Story 3 - Quản lý mã, For agents, máy chủ MCP (P3)

**Goal**: Owner giám sát mọi mã; Claude Code nối vào xưởng bằng một lệnh và làm phim, học phong cách chỉ bằng công cụ MCP.

**Independent Test**: spec US3.

- [ ] T016 [US3] `api_online.py`: `GET /admin/tokens`, `DELETE /admin/tokens/{id}`, `GET /admin/tokens/{id}/log` (chỉ Owner, chỉ cookie).
- [ ] T017 [US3] `web/app.js`: Settings → tab **API tokens** (mã của mọi người, cột người sở hữu, ⋯ Log và Revoke); khung For agents; màn **Log** (200 yêu cầu gần nhất: lúc, phương thức, đường, kết quả) dùng chung cho Your account.
- [ ] T018 [US3] Vé dùng một lần (research R6, contract "Tải lên và tải về bằng vé") trong `tokens.py` và `api_online.py`: `POST /uploads/tickets`, `PUT /uploads/t/{vé}` (đường công khai; dùng chung phần kiểm và lưu video với `POST /uploads`, tách thành một hàm), `POST /films/{name}/tickets`, `GET /films/t/{vé}`; vé sống 30 phút, dùng một lần, lưu băm, tính vào nhật ký của mã.
- [ ] T019 [US3] `server.py`: OpenAPI (`/api/v1/openapi.json`, `/api/v1/docs`) bỏ các đường cấm mã (research R7); nhận cookie hoặc mã.
- [ ] T020 [US3] `tools/studio/studio/mcp_server.py` (mới) và gắn vào `server.py` ở `/api/mcp` (chỉ nhận mã): `MCPServer` + `streamable_http_app(stateless_http=True, json_response=True)`; các công cụ ở contracts/mcp.md (riêng, chung, và thêm cho Owner), công cụ giao việc nhận `idempotency_key`; tài nguyên `film-studio://openapi`; mỗi công cụ gọi REST trong tiến trình bằng httpx `ASGITransport` với cùng `Authorization` (đọc qua `Context.headers`); `api_request` chỉ nhận đường dưới `/api/v1/`, chặn `/api/mcp`, `..`, `%2f`; phản hồi nhị phân trả kiểu và kích thước; danh sách công cụ theo vai trò thực.
- [ ] T021 [US3] `tests/online/test_mcp.py` (client MCP trong tiến trình): không có mã hoặc dùng cookie → `401`; mã Member không thấy `worker_status`, `usage`; `make_film` → việc của người sở hữu, trừ lượt; `idempotency_key` qua MCP không giao trùng; `get_job`, `get_review`, `answer_review`; `film_download_url` → link tải được đúng một lần; `api_request` tới đường cấm hay `/api/v1/admin/*` bằng mã Member → lỗi; `api_request` với `..` hay `/api/mcp` bị chặn; mỗi lệnh gọi công cụ ghi một hàng nhật ký (SC-207).
- [ ] T022 [US3] `tests/online/test_tickets.py` và SC-208: vé tải lên (đúng giới hạn, dùng một lần, hết hạn, đuôi tệp sai), vé tải về; một kịch bản chỉ bằng công cụ MCP với tác tử giả: `start_upload` ×3 + PUT tệp, `learn_style(source="upload")`, trả lời hai lần duyệt, rồi `make_film` với phong cách vừa học; `learn_style(source="youtube")` thiếu `rights_confirmed` → lỗi như web.
- [ ] T023 [US3] `tests/online/test_token_secrets.py` (SC-204): sau khi tạo và dùng mã (cả qua MCP), chuỗi mã đầy đủ không có trong `studio.db`, nhật ký web và worker, mọi phản hồi của `/me/tokens`, `/admin/tokens`, `/admin/worker`, OpenAPI.

**Checkpoint**: commit.

---

## Phase 6: Polish & triển khai

- [ ] T024 [P] `deploy/Caddyfile` (theo kết quả T001: không ghi `Authorization`; `/api/mcp` đi tới web) và `deploy/README.md`: mục mã API, khung For agents, nối Claude Code bằng MCP, thu hồi mã khi lộ.
- [ ] T025 [P] `CLAUDE.md` (mục Cấu trúc: `tokens.py`, `mcp_server.py`, `/api/mcp`, tab Worker và API tokens).
- [ ] T026 Chạy quickstart bằng tay (bước 1–5) với Claude Code thật nối qua MCP (SC-206, SC-207); ghi kết quả vào tasks: đạt, đạt một phần hoặc thất bại (hiến pháp IV).

---

## Dependencies & Execution Order

- **Phase 1** (T001, T002 song song) → **Phase 2** (T003 → T004 → T005 → T006) chặn mọi user story.
- **US1** (Phase 3) chỉ cần T003; làm song song với US2 được (khác tệp, trừ `api_online.py` và `app.js` làm lần lượt).
- **US2** cần Phase 2. **US3** cần US2 (mã, T011) và T013 (Idempotency-Key cho công cụ giao việc).
- **Phase 6** sau cùng; T026 cần cả xưởng chạy được và một tài khoản Claude.

## Parallel Examples

- Phase 1: T001, T002.
- Sau Phase 2: một người làm US1 (worker.py, test_worker_status.py), một người làm US2 (tokens.py phần idempotency, test_idempotency.py).
- Phase 5: T018 (vé) và T019 (OpenAPI) song song; T020 sau T018.
- Phase 6: T024, T025.

## Implementation Strategy

1. Phase 1–2: mã API đi được qua mọi API sẵn có, có test bảo mật nền.
2. US1 (MVP): tab Worker, dừng lại kiểm quickstart bước 1.
3. US2: mã của mình và Idempotency-Key; kiểm quickstart bước 2.
4. US3: quản lý, vé, MCP; kiểm quickstart bước 3–5.
5. Phase 6, rồi `/speckit-analyze` và `/speckit-converge`.
