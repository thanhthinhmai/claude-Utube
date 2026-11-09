# Research: Settings → Worker và API tokens

Nền là 007 và 008: FastAPI một tiến trình web, SQLite ở `$STUDIO_DATA/studio.db`, middleware `online_guard` trong `server.py` (CSRF bằng `X-Studio` và Origin, phiên bằng cookie), vai trò `admin` (Owner) và `customer` (Member), `ratelimit.py`, worker chạy vòng lặp `tick()` mỗi vài giây.

## R1. Mã API nhận vào ở đâu
- **Decision**: trong `online_guard`. Yêu cầu có header `Authorization: Bearer <mã>` thì xưởng tìm mã theo bản băm, gắn người sở hữu vào `request.state.account` như một phiên, và gắn thêm `request.state.token` (vai trò thực, quyền dùng lượt). Có mã thì bỏ qua cookie (spec, Edge Cases) và **không** kiểm `X-Studio`/Origin: CSRF chỉ đánh vào cookie mà trình duyệt tự gửi, còn mã thì trình duyệt không tự gửi.
- Mã có dạng `fs_` + 32 byte ngẫu nhiên (base64url). Lưu `sha256` của mã (mã đã đủ ngẫu nhiên nên không cần argon2) và 8 ký tự đầu để nhận ra (`fs_ab12cd…`).
- **Rationale**: mọi API sẵn có (phim, việc, duyệt, tải lên, quản trị) dùng được ngay với mã mà không phải sửa từng route.
- **Alternatives**: một bộ route riêng `/api/agent/…`: phải viết lại và giữ hai bản logic.

## R2. Giới hạn quyền của mã
- **Decision**: vai trò thực = vai trò thấp hơn giữa vai trò của mã và vai trò hiện tại của người sở hữu (FR-214), tính lại ở mỗi yêu cầu. Ba chốt chặn:
  - `admin(request)` dùng vai trò thực, nên mã Member gọi API quản trị bị `403`.
  - Danh sách cấm cho mọi mã (FR-213): `/api/v1/me/tokens*`, `/api/v1/admin/tokens*`, `/api/v1/admin/users*` (kể cả `GET`), `/api/v1/admin/claude*` (kể cả `GET` và đổi thứ tự), `PUT /api/v1/me` (đổi mật khẩu, cài đặt tài khoản), `DELETE /api/v1/me`. Có mã thì trả `403 token_forbidden`.
  - Không có quyền dùng lượt (FR-212): `POST /api/v1/jobs` (giao phim, sửa phim, học phong cách) trả `403 spend_not_allowed`, trước khi kiểm nội dung hay trừ lượt.
- **Rationale**: ít chỗ chạm, dễ test, không quên route nào: danh sách cấm theo tiền tố đường dẫn.

## R3. Giới hạn số yêu cầu mỗi phút và nhật ký của mã (như neb)
- **Decision**: mỗi yêu cầu có mã gọi `ratelimit.hit("token", <id>, limit=<rate>, window=60)` (thêm tham số giới hạn riêng vào `ratelimit.hit`), vượt thì `429 rate_limited` kèm `Retry-After` (FR-215).
- Mỗi yêu cầu có mã ghi một hàng `token_request(token_id, at, method, path, outcome, ip)` (FR-218); `outcome` ∈ `allowed`, `replay`, `forbidden`, `token_forbidden`, `no_spend`, `rate_limit`. Hàng cũ hơn 30 ngày bị xoá, tối đa một lần mỗi giờ. Số yêu cầu và số bị chặn hôm nay (giờ Việt Nam) tính thẳng từ bảng này. `api_token.last_used_at` ghi tối đa mỗi 5 phút. Không ghi nội dung yêu cầu hay phản hồi.
- Việc giao qua mã vẫn chịu giới hạn giao việc của người sở hữu như trên web (`job_account`).
- **Rationale**: như neb (`api_token_requests`); biết tác tử đã gọi gì và vì sao bị chặn. Nhóm nhỏ nên một lần ghi SQLite mỗi yêu cầu là đủ.
- **Alternatives**: chỉ đếm theo ngày (bản đầu của plan): không biết vì sao bị chặn.

## R4. Worker báo sống
- **Decision**: bảng `worker_beat`, mỗi tiến trình một hàng (`id` = tên máy + mã tiến trình), như bảng `workers` của neb. Worker ghi khi khởi động, ít nhất mỗi 5 giây, và ngay khi bắt đầu hay xong một việc, kèm danh sách việc đang chạy. Tab Worker tính trạng thái: báo sống ≤ 30 giây là Running (idle hoặc busy), > 30 giây là Not responding, > 10 phút thì ẩn (FR-202, FR-203). Hàng cũ hơn 24 giờ bị xoá khi một worker khởi động. Worker dừng êm thì xoá hàng của mình.
- **Rationale**: worker và web là hai tiến trình (hai container ở Docker); SQLite chung là kênh duy nhất cả hai đã dùng.
- **Alternatives**: web hỏi thẳng worker qua HTTP: thêm một cổng và một dịch vụ mạng cho worker.

## R5. Máy chủ MCP
- **Decision**: dùng thư viện `mcp` 2.3.0 **đã có sẵn** (thư viện `claude-agent-sdk` cần nó; ghim rõ trong `tools/requirements-online.txt`). `MCPServer` với `streamable_http_app(stateless_http=True, json_response=True)`, gắn vào web ở `/api/mcp`. Không giữ phiên, không dùng luồng SSE, nên đi qua Caddy như một API thường.
- **Mỗi công cụ là một lệnh gọi REST của chính xưởng**, gọi trong tiến trình (httpx `ASGITransport` tới chính app) với cùng header `Authorization` mà tác tử gửi tới `/api/mcp` (đọc qua `Context.headers`). Vì vậy kiểm quyền, giới hạn, trừ lượt, kiểm nội dung và lỗi giống hệt REST. Không có logic thứ hai.
- `/api/mcp` chỉ nhận mã API (không nhận cookie). Danh sách công cụ theo vai trò thực: mã Member không thấy công cụ quản trị (US3 #5). Khác neb (neb không ẩn), vì chặt hơn.
- Như neb, thêm ba công cụ chung `list_operations`, `describe_operation`, `api_request` (đọc OpenAPI của xưởng; `api_request` chỉ nhận đường dưới `/api/v1/`, không nhận `/api/mcp`, không nhận `..` hay `%2f`), và tài nguyên `film-studio://openapi`. Công cụ riêng chỉ giữ cho các việc hay làm.
- **Rationale**: FR-219 đòi máy chủ MCP như neb; dùng lại thư viện có sẵn và REST có sẵn là cách ít mã nhất.
- **Alternatives**: tự viết JSON-RPC của MCP: phải theo kịp giao thức. Gọi thẳng hàm Python thay vì REST: phải lặp lại kiểm quyền ở từng công cụ.

## R6. Tải video lên qua MCP (FR-220)
- **Vấn đề**: máy chủ MCP nằm ở xưởng, không đọc được tệp trên máy tác tử; một lệnh gọi MCP giới hạn 4 MB, còn video tới 500 MB.
- **Decision**: công cụ MCP `start_upload(filename, size_bytes)` kiểm giới hạn (dung lượng, định dạng) rồi trả một **link tải lên dùng một lần** (`PUT /api/v1/uploads/t/<vé>`, sống 30 phút) và lệnh `curl -T <tệp> <link>` mẫu. Tác tử (Claude Code có Bash) tải tệp lên link đó; xưởng kiểm video như `POST /uploads` hiện nay và trả `upload_id`. Sau đó `learn_style(source="upload", upload_ids=[…])`.
  - Vé lưu dạng băm trong bảng `ticket`, gắn với người sở hữu và mã; dùng một lần; tính vào lượt dùng của mã.
  - Tải phim về qua MCP dùng cùng cơ chế: `film_download_url` trả link `GET /api/v1/films/t/<vé>` dùng một lần.
  - Đường `/api/v1/uploads/t/` là đường công khai (vé chính là quyền), không cần cookie hay header.
- **Rationale**: tác tử không cần biết mã API trong shell (mã nằm trong cấu hình MCP của Claude Code), tệp lớn đi thẳng bằng HTTP.
- **Alternatives**: gửi video dạng base64 trong lệnh gọi MCP: vượt 4 MB. Bảo tác tử tự gọi `POST /uploads` với mã: tác tử phải có mã trong shell.

## R7. Tài liệu cho tác tử (FR-217)
- **Decision**: OpenAPI sẵn có của FastAPI ở `/api/v1/openapi.json`, và trang đọc `/api/v1/docs`; cả hai nhận mã hoặc cookie. Ẩn khỏi OpenAPI các đường không dùng được bằng mã (`/api/v1/me/tokens*`, `/api/v1/admin/tokens*`, `/api/v1/admin/users*`, `/api/v1/admin/claude*`). API nội bộ của container nằm ở bộ chuyển tiếp, vốn không có trong OpenAPI của web.
- Lệnh mẫu cho Claude Code: `claude mcp add --transport http film-studio <STUDIO_URL>/api/mcp --header "Authorization: Bearer <mã>"`.

## R8. Không lộ mã
- **Decision**: mã đầy đủ chỉ có trong phản hồi của `POST /me/tokens`. Không ghi vào nhật ký (web chạy ở mức `warning`, không có nhật ký truy cập). Có test tìm chuỗi mã trong cơ sở dữ liệu, nhật ký và mọi phản hồi (SC-204).
- **Kiểm khi implement**: Caddy có ghi header `Authorization` vào nhật ký truy cập không (`deploy/Caddyfile`); nếu có thì tắt hoặc che.

## R10. Idempotency-Key cho giao việc (FR-221, như neb)
- **Decision**: `POST /jobs` nhận header `Idempotency-Key` (≤ 100 ký tự). Bảng `idempotency(account_id, key_hash, request_hash, job_id, created_at)`, khoá chính `(account_id, key_hash)`, giữ 24 giờ.
  - Chưa có: xử lý như thường; khi việc được tạo thì ghi hàng **trong cùng giao dịch** trừ lượt (`quotas.reserve`), nên 5 yêu cầu cùng lúc chỉ tạo 1 việc (SC-209).
  - Đã có, cùng `request_hash` (sha256 của thân yêu cầu đã chuẩn hoá): trả `200` với việc cũ, ghi nhật ký `replay`, không kiểm nội dung, không trừ lượt.
  - Đã có, khác `request_hash`: `409 idempotency_conflict`.
- Có cho cả yêu cầu bằng cookie, không chỉ bằng mã.
- **Rationale**: tác tử hay thử lại khi mạng chập chờn; không có khoá thì có thể giao trùng phim và trừ 2 lượt.

## R11. Đối chiếu với neb-creative-tool (2026-11-09)
Đã đối chiếu với `lib/auth/tokens.ts`, `lib/auth/tokenPolicy.ts`, `app/api/mcp/route.ts`, `lib/mcp/*`, `components/settings/ApiTokens.tsx`, `Worker.tsx` của neb.
- **Giống**: dạng mã (tiền tố + 32 byte, chỉ lưu SHA-256, vài ký tự đầu, hiện một lần), Bearer bỏ qua cookie, mã thay mặt người tạo, vai trò lấy mức thấp hơn, giới hạn 10/30/60/120/300, mặc định không được tốn lượt, danh sách việc mã không làm được, MCP bằng SDK chính thức không giữ phiên trả JSON, công cụ gọi lại REST, lệnh `claude mcp add`, bảng báo sống của worker, tab Worker đọc lại mỗi 5 giây.
- **Khác, theo lựa chọn của người dùng**: mọi người dùng tự tạo mã (neb: chỉ Owner); học phong cách qua MCP.
- **Khác, chặt hơn neb**: ẩn công cụ quản trị với mã Member; mã Owner không đụng tới tài khoản Claude.
- **Khác, cách tải tệp**: neb nhận link http(s) và tự tải về (không tải được tệp trên máy tác tử); xưởng dùng link dùng một lần (R6), không làm phần tự tải link để khỏi thêm bề mặt SSRF.
- **Không lấy**: danh sách IP, trần chi tiền mỗi ngày, báo động chi tiền, webhook, Licenses.

## R9. Tạo mã không cần nhập lại mật khẩu
- **Decision**: không hỏi lại mật khẩu; người dùng đã đăng nhập (Clarifications: để plan quyết). Có giới hạn 20 mã còn hiệu lực mỗi người để tránh tạo tràn (neb: 50 cho cả xưởng).
