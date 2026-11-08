# Contract: worker, container và bộ chuyển tiếp (008)

Thay đổi trên [runner của 007](../../007-online-studio/contracts/runner.md). Mục nào không nhắc ở đây thì giữ nguyên.

## Worker → container
- **Biến môi trường** (research R3). Không còn `ANTHROPIC_API_KEY`:
  - `ANTHROPIC_BASE_URL=http://proxy:8780`
  - `CLAUDE_CODE_OAUTH_TOKEN=<mã riêng của việc>`: vẫn là mã do bộ chuyển tiếp cấp như 007
  - `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`
- **Gắn vào**: như 007, chỉ `/data/jobs/<id>`. Không bao giờ gắn `/data/claude` hay `/data/studio.db`. Có test kiểm điều này.
- **Bắt đầu việc**: vòng lặp chỉ nhận việc `queued` khi xưởng `ready`, tức còn ít nhất một tài khoản Claude dùng được hoặc có khoá API (FR-110). Khi không `ready`, việc vẫn nằm trong hàng, và trang việc hiện "Waiting for a Claude account".

## Bộ chuyển tiếp: `POST /v1/messages` (và `/count_tokens`)
1. Kiểm mã của việc như 007.
2. Kiểm `job.tokens < job_token_cap`. Vượt trần thì việc lỗi do xưởng ("used more than its token limit", trả lượt) và trả `429` (FR-116).
3. Chọn đường gọi (research R4, R5):
   ```
   for slot in tài khoản dùng được, xếp theo token 5 giờ tăng dần:
       gửi với Bearer <mã của slot> (làm mới trước nếu còn < 5 phút, mốc của Claude Code, T001)
       429 của gói  → slot thành limited (rest_until), thử slot kế tiếp
       401          → làm mới 1 lần; vẫn 401 → needs_signin + thư, thử slot kế tiếp
       khác         → trả nguyên phản hồi cho container (kể cả 529, 5xx)
   hết slot:
       có ANTHROPIC_API_KEY → gửi qua khoá (x-api-key, bỏ oauth-* khỏi anthropic-beta)
       slot sớm nhất dùng lại trong ≤ 15 s → chờ rồi thử lại slot đó một lần
       còn lại → việc lỗi do xưởng "No Claude account is available until <giờ>" (trả lượt), trả 429
   ```
4. Đọc `usage`, ghi một hàng Call (`via`), cộng `job.tokens`. Chỉ cộng `cost_usd` khi `via = api`.
- Nhật ký ghi `via`, mã trạng thái và số token. **Không** ghi mã đăng nhập, header `authorization` hay nội dung lời nhắc.
- Đường lạ dưới `/v1/` hoặc `/api/` trả `404` dạng lỗi của Anthropic (R3).

## Thư mục đăng nhập
- `/data/claude/slot-<n>/`, quyền 700, chủ là uid 1000. Chỉ web (đăng nhập, kiểm nội dung) và proxy (gọi, làm mới) đọc được.
- Khoá cho mỗi slot: `/data/claude/slot-<n>.lock` (`flock`) bao quanh mọi lệnh Claude Code chạy trên slot đó. Nhờ vậy làm mới, đăng nhập và kiểm nội dung không chạy chồng nhau.
- Worker không cần thư mục này.
- `web` và `proxy` chạy chỉ đọc, nên đặt `HOME=/tmp/home` (tmpfs) để Claude Code ghi được các tệp ngoài `CLAUDE_CONFIG_DIR`. Web chạy **một** tiến trình uvicorn, vì lần đăng nhập đang chờ nằm trong bộ nhớ.

## Compose
- `web`, `proxy`: `ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}` (không còn bắt buộc).
- Ảnh `studio-web` có thêm `claude-agent-sdk` (tệp chạy `claude`, research R9).
