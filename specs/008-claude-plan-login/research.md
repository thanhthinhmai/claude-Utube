# Research: Xưởng online nội bộ chạy bằng gói Claude

Nền là kiến trúc 007 ([plan](../007-online-studio/plan.md), [runner](../007-online-studio/contracts/runner.md)). Mỗi việc chạy Claude Agent SDK trong một container. Mọi lệnh gọi Claude đi qua bộ chuyển tiếp (`proxy`). Bản tham chiếu là neb-creative-tool: `lib/claudeCode/auth.ts`, `structured.ts`, `lib/accounts/health.ts`.

Các mục có ghi **Kiểm khi implement** dựa trên hành vi của Claude Code mà tài liệu công khai chưa nói rõ. Task đầu tiên của tasks.md **PHẢI** kiểm từng mục bằng một bài thử nhỏ với tài khoản thật. Nếu kết quả khác thì dừng lại và hỏi người dùng (hiến pháp II), không tự đổi thiết kế.

## R1. Đăng nhập bằng gì
- **Decision**: chạy `claude auth login --claudeai` của chính Claude Code (bản đi kèm `claude-agent-sdk`). Mỗi tài khoản có một thư mục cấu hình riêng `CLAUDE_CONFIG_DIR=/data/claude/slot-<n>` (n = 1…5), giống neb.
  - Máy chủ ở xa, nên trang Claude không quay về máy chủ được. Xưởng đọc URL đăng nhập Claude Code in ra, mở trên trình duyệt của chủ xưởng, rồi chủ xưởng dán mã vào trang quản trị. Mã được ghi vào stdin của tiến trình đang chờ.
  - Trạng thái (email, gói) đọc bằng `claude auth status --json`. Đăng xuất bằng `claude auth logout`.
  - Mỗi lần chỉ có một lần đăng nhập đang chờ; sau 10 phút thì dừng tiến trình (FR-101).
- **Rationale**: đây là cách đăng nhập chính thức của Claude Code, nên xưởng không tự làm luồng OAuth. Hành vi giống neb mà người dùng đã quen.
- **Alternatives**:
  - `claude setup-token` (mã dài hạn cho máy không màn hình): không cho biết email và gói, trái FR-102.
  - Tự làm luồng OAuth: phải chép mã nội bộ của Claude Code, dễ hỏng khi Claude Code đổi.
- **Kiểm khi implement**: khi không có trình duyệt, `auth login` in URL và chờ mã trên stdin (neb dựa vào hành vi này); mẫu URL `https://…/oauth/authorize?…`; các trường JSON của `auth status` (`loggedIn`, `email`, `subscriptionType`).

## R2. Bộ chuyển tiếp lấy thông tin đăng nhập thế nào
- **Decision**: container vẫn không có gì thật (FR-104). Bộ chuyển tiếp đọc mã truy cập ở `slot-<n>/.credentials.json` (`claudeAiOauth.accessToken`, `expiresAt`). Với mỗi lần gọi đi qua gói, nó gửi `Authorization: Bearer <mã>` thay cho `x-api-key`.
- **Làm mới**: mã truy cập sống ngắn. Còn dưới 10 phút thì bộ chuyển tiếp chạy một lệnh Claude Code trên thư mục đó để Claude Code tự làm mới, rồi đọc lại tệp. Bộ chuyển tiếp không tự gọi máy chủ OAuth.
  - Có khoá cho mỗi tài khoản, nên hai tiến trình không làm mới cùng lúc. neb gặp lỗi khi hai tiến trình làm mới cùng lúc và phải thử lại.
  - Làm mới không được thì đánh dấu "Needs sign-in" (FR-109).
- **Rationale**: chỉ bộ chuyển tiếp có mạng ra ngoài mà container không chạm tới được. Cách này giữ nguyên mô hình an toàn của 007.
- **Alternatives**: đưa thư mục đăng nhập vào container (giống neb chạy trên máy): trái FR-104, vì tác tử có Bash và đọc được tệp.
- **Kiểm khi implement**: tên tệp và các trường; lệnh nào của Claude Code làm mới mã mà không tốn hạn mức (thử `claude auth status` trước). Không có lệnh nào như vậy thì dừng và hỏi người dùng.

## R3. Container gọi bằng chế độ nào
- **Decision**: container chạy Claude Code ở **chế độ gói**: đặt `CLAUDE_CODE_OAUTH_TOKEN=<mã riêng của việc>` và `ANTHROPIC_BASE_URL=http://proxy:8780`, không đặt `ANTHROPIC_API_KEY`. Claude Code tự gửi đúng các header của chế độ gói. Bộ chuyển tiếp chỉ thay giá trị Bearer:
  - đi qua gói: thay bằng mã thật của tài khoản;
  - đi qua khoá API dự phòng (FR-117): đổi sang `x-api-key` và bỏ phần `oauth-*` trong `anthropic-beta`.
- Đặt thêm `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`, vì container không có mạng ra ngoài.
- **Rationale**: lệnh gọi giống hệt Claude Code thật đang chạy trên gói, nên ít bị dịch vụ từ chối.
- **Alternatives**: giữ chế độ khoá API như 007 rồi để bộ chuyển tiếp thêm header gói. Cách này bị loại vì phải đoán các header của chế độ gói.
- **Kiểm khi implement**: Claude Code chế độ gói vẫn theo `ANTHROPIC_BASE_URL`; nó còn gọi đường nào khác ngoài `/v1/messages` (bộ chuyển tiếp trả 404 cho đường lạ, và việc không được hỏng vì thế).

## R4. Chọn tài khoản cho mỗi lần gọi (FR-107, Clarifications)
- **Decision**: mỗi lần gọi lấy tài khoản có token thấp nhất trong 5 giờ gần nhất, trong số tài khoản `signed_in`, hết thời gian nghỉ và không trùng. Token tính từ bảng Call do xưởng tự ghi (R7). Bằng nhau thì lấy tài khoản có số thứ tự nhỏ.
- **Rationale**: "dùng ít nhất" giống neb. 5 giờ là cửa sổ hạn mức ngắn của gói. Xưởng tự đếm nên test được không cần dịch vụ thật (SC-105).
- **Alternatives**: đọc phần trăm đã dùng từ header của dịch vụ: tốt hơn khi có, nhưng chưa chắc có. Nếu kiểm khi implement thấy có header này thì ghi lại để hiện lên trang quản trị, không dùng để chọn tài khoản.

## R5. Chạm hạn mức, hỏng đăng nhập, hết tài khoản (FR-108, FR-109, FR-110)
- **Chạm hạn mức**: dịch vụ trả `429` khi gọi qua gói. Khi đó:
  - tài khoản thành `limited`; `rest_until` lấy từ header giờ dùng lại, không có thì chờ tăng dần 2 giây → 5 phút, giống neb;
  - bộ chuyển tiếp **gửi lại cùng nội dung** qua tài khoản kế tiếp, nên việc không lỗi. Phản hồi `429` đến trước khi dòng dữ liệu bắt đầu, nên gửi lại được.
- **Hỏng đăng nhập**: gặp `401` thì thử làm mới một lần (R2). Vẫn hỏng thì tài khoản thành `needs_signin`, gửi một thư `claude_signin` cho chủ xưởng, rồi gửi lại lệnh gọi qua tài khoản kế tiếp.
- **Hết tài khoản**: thứ tự xử lý như sau.
  1. Có khoá API thì gửi qua khoá.
  2. Không có khoá thì chờ, nếu tài khoản sớm dùng lại nhất có `rest_until` trong vòng 15 giây.
  3. Còn lại thì `quotas.fail(job, …, "studio")` (trả lượt), kèm giờ sớm nhất có tài khoản dùng lại, và trả `429`. Việc đã bị đánh dấu lỗi nên SDK không thử lại mãi.
- `529` và `5xx` vẫn trả nguyên như 007 R13: lỗi của dịch vụ, không phải của tài khoản.
- **Kiểm khi implement**: tên header giờ dùng lại khi chạm hạn mức của gói, và phân biệt `429` do hạn mức gói với `429` thường.

## R6. Kiểm nội dung ý tưởng (007 R9) khi không có khoá API
- **Decision**: chạy lệnh kiểm bằng `claude -p --output-format json` trên một tài khoản chọn theo R4 (tiến trình web, cùng thư mục `/data/claude`), với lời nhắc và lược đồ trả lời như cũ. Không còn tài khoản nào thì dùng khoá API nếu có. Không có cả hai thì từ chối giao việc với "Studio is not ready", không trừ lượt.
- **Rationale**: gửi thẳng tới Messages API bằng mã của gói (không qua Claude Code) là dùng gói ngoài Claude Code: dễ bị từ chối và trái mục đích của gói. neb cũng chỉ gọi gói qua Claude Code (`structured.ts`).
- **Alternatives**: bỏ kiểm nội dung cho nhóm nội bộ: trái 007 FR-013, spec 008 không bỏ yêu cầu này.

## R7. Ghi mức dùng (FR-114–FR-116)
- **Decision**: thêm bảng Call, mỗi lần gọi một hàng: việc, tài khoản (`plan:<n>` hoặc `api`), model, token vào, ra, ghi đệm, đọc đệm, chi phí (chỉ với `api`), lúc gọi.
  - Báo cáo tính thẳng từ bảng này: theo ngày, thành viên, tài khoản (SC-107).
  - Trường `cost_usd` của Job vẫn giữ, chỉ cộng phần đi qua khoá. Thêm `tokens` vào Job.
  - Bỏ trần chi phí ngày và việc ghi vào Usage day.
- **Trần token mỗi việc (FR-116)**: `job_token_cap`, mặc định 40 triệu, tính cả token đọc đệm. Con số này ước từ 007 (trần 5 USD, giá đọc đệm của Opus). Bài chạy thật ghi số token thực tế để chỉnh lại.
- **Rationale**: đếm theo từng lần gọi thì mọi cách chia đều đúng và test được. Nhóm dưới 20 người nên bảng không lớn.
- **Alternatives**: cộng dồn theo ngày như Usage day: không chia được theo tài khoản Claude.

## R8. Lời mời (FR-111–FR-113)
- **Decision**: dùng lại bảng Account và Token của 007.
  - Lời mời là một Account `customer` chưa có mật khẩu (`password_hash` null), cộng một Token loại `invite` sống 7 ngày.
  - Mở lời mời và đặt mật khẩu thì ghi `email_verified_at`, và Token được tính là đã dùng.
  - Thu hồi lời mời thì xoá Account chưa có mật khẩu đó và Token của nó.
  - `/auth/signup` luôn trả `403`. Bỏ `signup_open`.
- **Rationale**: không cần bảng mới. Luồng giống "đặt lại mật khẩu" đã có và đã test.
- **Alternatives**: bảng Invite riêng: thêm một bảng mà không thêm khả năng nào.

## R9. Đặt Claude Code ở đâu
- **Decision**: ảnh `studio-web` (dùng cho web, proxy, worker) cài `claude-agent-sdk` để có tệp chạy `claude`. Thư mục `/data/claude/` để quyền 700 cho uid 1000. Worker chỉ gắn `/data/jobs/<id>` vào container (như 007). Có test kiểm danh sách gắn không chứa `/data/claude`.
- **Rationale**: cùng một bản Claude Code với container việc, không thêm dịch vụ.
