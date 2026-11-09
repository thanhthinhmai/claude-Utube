# Feature Specification: Settings → Worker và API tokens

**Feature Branch**: `009-settings-worker-tokens`

**Created**: 2026-11-09

**Status**: Draft

**Input**: User description: "Thêm 2 tab vào trang Settings của xưởng online (chỉ Owner), theo bố cục neb-creative-tool, xây trên 008. (1) Tab Worker: trạng thái của worker (đang chạy hay nghỉ, lần báo sống gần nhất, đọc lại mỗi vài giây), các ô đếm (việc đang xếp hàng, việc đang chạy, việc chờ duyệt, việc chờ tài khoản Claude), và danh sách "Latest jobs" (việc gần nhất của mọi thành viên: trạng thái, loại phim/học phong cách, tên, thành viên, thời gian, lỗi nếu có, link tới trang việc). Việc bắt đầu/dừng worker vẫn làm ở terminal. (2) Tab API tokens: Owner tạo mã API để script hoặc tác tử AI (như Claude Code) làm việc với API của xưởng thay cho một người dùng; mỗi mã có tên, người sở hữu, vai trò (Member: giao phim và học phong cách; Owner: thêm các quyền quản trị), có được dùng lượt phim hay không, giới hạn số yêu cầu mỗi phút, hạn dùng; gửi bằng header Authorization: Bearer; danh sách mã (tên, vai trò, số yêu cầu hôm nay, lần dùng gần nhất, hạn), thu hồi mã; mã chỉ hiện đúng một lần lúc tạo, máy chủ chỉ giữ bản băm. Khung "For agents" hiện Base URL, header, tài liệu API (OpenAPI) và lệnh mẫu để Claude Code dùng. Không làm Licenses (xưởng chưa có app desktop)."

## Clarifications

### Session 2026-11-09

- Q: Khung For agents có cần một máy chủ MCP như neb, hay chỉ tài liệu OpenAPI và đoạn mẫu? → A: Có máy chủ MCP như neb (FR-219, SC-207).
- Q: Owner có tạo mã thay mặt thành viên không, và thành viên có biết không? → A: Không. Mã API là để tác tử của chính người dùng gọi API, nên **mỗi người dùng (Member và Owner) tự tạo mã cho mình**; mã luôn thay mặt người tạo. Owner xem và thu hồi được mọi mã (FR-208, FR-209).
- Q: Có làm giống neb thêm những phần nào? → A: Theo đề xuất sau khi đối chiếu với code neb: nhật ký từng yêu cầu của mã, Idempotency-Key cho giao việc, công cụ MCP chung, khung For agents đầy đủ, hạn 7 ngày, báo sống 5 giây và coi là dừng sau 30 giây, Latest jobs 20 việc. Không nhận link http(s) để xưởng tự tải tệp (FR-202, FR-203, FR-205, FR-209, FR-216–FR-219, FR-221).
- Q: Máy chủ MCP có cho học phong cách không? → A: Đủ cả: làm phim, học phong cách từ kênh YouTube (tác tử xác nhận quyền dùng video như trên web) và từ video tải lên qua MCP (FR-219, FR-220).

## Bối cảnh

Xưởng online nội bộ của 008 đã có trang Settings với các tab General, Users và Usage. Chủ xưởng còn thiếu hai thứ mà neb-creative-tool có:

- **Nhìn được xưởng đang làm gì.** Hiện muốn biết worker còn chạy không, hàng đợi dài bao nhiêu hay việc nào vừa lỗi, chủ xưởng phải xem nhật ký trong terminal.
- **Cho script và tác tử AI dùng xưởng.** API của xưởng hiện chỉ nhận phiên đăng nhập của trình duyệt. Một script hay một tác tử như Claude Code không đăng nhập được.

Tab Licenses của neb không làm, vì xưởng chưa có app desktop (đã chốt ở 008).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chủ xưởng nhìn thấy worker và các việc gần nhất (Priority: P1)

Chủ xưởng mở Settings → Worker. Trang cho biết worker đang chạy hay đã ngừng, lần cuối nó báo sống là khi nào, và nó đang làm việc nào. Bốn ô đếm cho biết số việc đang xếp hàng, đang chạy, đang chờ thành viên duyệt và đang chờ tài khoản Claude. Bên dưới là danh sách các việc gần nhất của mọi thành viên. Trang tự đọc lại sau vài giây, không cần tải lại.

**Why this priority**: Đây là phần chủ xưởng cần mỗi ngày để biết xưởng có đang chạy đúng không, và nó không phụ thuộc phần mã API.

**Independent Test**: Có một việc đang chạy và một việc vừa lỗi → mở tab Worker → thấy worker "Running", ô "jobs running" là 1, việc lỗi nằm trong Latest jobs kèm lý do. Dừng worker ở terminal → trong vòng 1 phút trang đổi sang "Stopped".

**Acceptance Scenarios**:

1. **Given** worker đang chạy, **When** chủ xưởng mở tab Worker, **Then** trang hiện "Running", việc nó đang làm (hoặc "idle"), và lần báo sống gần nhất ("last beat 3 s ago").
2. **Given** worker đã dừng hoặc treo, **When** quá 30 giây không có lần báo sống nào, **Then** trang hiện "Stopped" (hoặc "Not responding") kèm thời điểm báo sống cuối.
3. **Given** có việc ở nhiều trạng thái, **When** mở tab, **Then** bốn ô đếm đúng bằng số việc đang xếp hàng, đang chạy, đang chờ duyệt, đang chờ tài khoản Claude.
4. **Given** các việc gần nhất của nhiều thành viên, **When** mở tab, **Then** Latest jobs liệt kê 20 việc mới nhất: trạng thái, loại (phim hoặc học phong cách), tên, thành viên, thời gian; việc lỗi kèm lý do; bấm vào mở trang việc.
5. **Given** một thành viên (không phải Owner), **When** mở tab Worker hoặc gọi API của nó, **Then** bị từ chối.

---

### User Story 2 - Người dùng tạo mã API cho tác tử hay script của mình (Priority: P2)

Một người dùng (Member hoặc Owner) mở trang **Your account** → API tokens, bấm "New token", đặt tên ("Claude Code trên laptop"), chọn vai trò (Owner chọn được Member hoặc Owner; Member chỉ có Member), có được dùng lượt phim không, giới hạn số yêu cầu mỗi phút và hạn dùng. Xưởng hiện mã **một lần duy nhất** để chép. Tác tử gửi mã trong header `Authorization: Bearer` và gọi API như chính người đó, trong phạm vi vai trò và quyền đã chọn.

**Why this priority**: Đây là cách để tác tử AI hay script tự giao phim, theo dõi việc và tải phim về. Nó cần US1 không phải điều kiện, nhưng ít gấp hơn việc nhìn thấy xưởng.

**Independent Test**: Một thành viên tự tạo mã có quyền dùng lượt phim → dùng mã đó gọi API giao một phim → việc được tạo dưới tên thành viên đó và trừ lượt của họ. Tạo một mã không có quyền dùng lượt → giao phim bị từ chối, nhưng xem danh sách việc thì được.

**Acceptance Scenarios**:

1. **Given** chủ xưởng tạo mã, **When** bấm Create, **Then** mã hiện đúng một lần kèm nút Copy; tải lại trang thì chỉ còn vài ký tự đầu của mã.
2. **Given** một mã Member còn hạn, **When** script gọi API với header `Authorization: Bearer <mã>`, **Then** nó làm được những gì người đó làm được trên giao diện thành viên (xem việc, phim, phong cách; trả lời duyệt; tải phim), và không gọi được API quản trị.
3. **Given** mã không có quyền dùng lượt, **When** script giao phim hoặc học phong cách, **Then** bị từ chối với lý do rõ ràng, không trừ lượt.
4. **Given** mã Owner, **When** script gọi API quản trị (xem Users, Usage, Worker, đổi cài đặt), **Then** được; nhưng **không** tạo hay thu hồi mã API, không đăng nhập hay đăng xuất tài khoản Claude, và không thêm, sửa hay xoá người dùng.
5. **Given** mã đã thu hồi, đã hết hạn, hoặc người nó thay mặt đã bị tắt hay xoá, **When** dùng, **Then** bị từ chối ngay.
6. **Given** một mã vượt giới hạn số yêu cầu mỗi phút, **When** gọi tiếp, **Then** bị từ chối tạm thời kèm thời gian chờ.
7. **Given** một Member tạo mã, **When** chọn vai trò, **Then** chỉ có Member; không ai tạo được mã thay mặt người khác.

---

### User Story 3 - Quản lý các mã và hướng dẫn tác tử dùng API (Priority: P3)

Trang Your account liệt kê các mã của chính người dùng; tab Settings → API tokens của Owner liệt kê mã của mọi người. Mỗi danh sách gồm: tên, người thay mặt, vai trò, có được dùng lượt không, số yêu cầu hôm nay, lần dùng gần nhất, hạn dùng và trạng thái (Active, Ended, Revoked). Mỗi mã có menu ⋯ để thu hồi. Khung "For agents" cho biết những gì một tác tử cần: Base URL của xưởng, header cần gửi, link tài liệu API ở dạng OpenAPI mà tác tử đọc được, và một đoạn mẫu để dán cho Claude Code.

**Why this priority**: Quản lý và hướng dẫn chỉ có ích khi đã tạo được mã (US2).

**Independent Test**: Một thành viên tạo hai mã, dùng một mã 3 lần → danh sách hiện đúng "3 requests" và lần dùng gần nhất cho mã đó, mã kia "0 requests" → thu hồi mã đã dùng → trạng thái đổi sang Revoked và mã đó bị từ chối.

**Acceptance Scenarios**:

1. **Given** có nhiều mã, **When** mở danh sách, **Then** mỗi mã hiện đủ các cột trên; mã đã hết hạn hiện "Ended", mã đã thu hồi hiện "Revoked". Thành viên chỉ thấy mã của mình; Owner thấy mã của mọi người trong tab API tokens.
2. **Given** người tạo (hoặc Owner) bấm Revoke và xác nhận, **When** mã đó được dùng lần sau, **Then** bị từ chối.
3. **Given** khung "For agents", **When** chủ xưởng mở link tài liệu API, **Then** nhận được tài liệu OpenAPI của các API mà mã dùng được, không có các API nội bộ của container hay của bộ chuyển tiếp.
4. **Given** đoạn mẫu cho Claude Code, **When** chủ xưởng chép và dùng nó cùng một mã, **Then** Claude Code giao được một phim qua API mà không cần hướng dẫn thêm.
5. **Given** lệnh `claude mcp add` ở khung For agents với một mã Member, **When** Claude Code nối vào, **Then** nó thấy các công cụ của thành viên (phong cách, giao phim, sửa phim, học phong cách, tải video lên, việc, duyệt, tải phim) và không thấy công cụ quản trị nào.
6. **Given** tác tử học phong cách từ kênh YouTube qua MCP, **When** không gửi xác nhận quyền dùng video, **Then** bị từ chối như trên web.

---

### Edge Cases

- Worker chạy nhiều tiến trình (nhiều máy hoặc chạy lại): mỗi tiến trình là một dòng trạng thái riêng; dòng không báo sống quá 10 phút thì không hiện nữa.
- Không có việc nào: Latest jobs hiện "No jobs yet"; các ô đếm là 0.
- Mã bị lộ: chủ xưởng thu hồi; mọi yêu cầu sau đó bị từ chối, kể cả yêu cầu đang trên đường.
- Mã có hạn "Never": cho phép, nhưng trang cảnh báo rằng mã không bao giờ tự hết hạn.
- Người mà mã thay mặt bị hạ từ Owner xuống Member: mã Owner của người đó chỉ còn quyền Member cho tới khi được nâng lại.
- Gửi cả cookie phiên và mã: xưởng dùng mã, bỏ qua cookie.
- Mã sai định dạng hoặc không tồn tại: từ chối như mã đã thu hồi, không cho biết mã có tồn tại hay không.

## Requirements *(mandatory)*

### Functional Requirements

**Worker (US1)**

- **FR-201**: Settings MUST có tab **Worker**, chỉ Owner thấy và dùng được.
- **FR-202**: Mỗi tiến trình worker MUST báo sống ít nhất mỗi 5 giây (và ngay khi bắt đầu hay xong một việc), kèm việc nó đang chạy nếu có. Tab Worker MUST hiện từng tiến trình: trạng thái (Running · idle / Running · busy with <việc> / Not responding), thời gian từ lần báo sống gần nhất.
- **FR-203**: Tiến trình không báo sống quá 30 giây MUST hiện "Not responding"; quá 10 phút thì không hiện nữa. Không còn tiến trình nào thì trang MUST hiện "No worker is running" kèm lệnh để bật worker.
- **FR-204**: Tab Worker MUST hiện bốn ô đếm: jobs queued, jobs running, waiting for review, waiting for a Claude account.
- **FR-205**: Tab Worker MUST hiện **Latest jobs**: 20 việc mới nhất của mọi thành viên, mỗi việc gồm trạng thái, loại, tên, email thành viên, thời gian cập nhật; việc lỗi kèm lý do (cắt ngắn, có "Details" để xem đủ); bấm vào mở trang việc.
- **FR-206**: Tab Worker MUST tự đọc lại ít nhất mỗi 5 giây khi đang mở, không cần tải lại trang.
- **FR-207**: Việc bật và dừng worker MUST vẫn làm ở terminal; trang chỉ xem, không điều khiển.

**Mã API (US2, US3)**

- **FR-208**: Trang **Your account** MUST có mục **API tokens** cho mọi người dùng: tạo, xem và thu hồi mã của chính mình, kèm khung For agents. Settings MUST có tab **API tokens**, chỉ Owner thấy: danh sách mã của **mọi** người dùng, thu hồi được bất kỳ mã nào.
- **FR-209**: Mọi người dùng đang bật MUST tự tạo được mã **cho chính mình** (mã luôn thay mặt người tạo; không ai tạo mã thay mặt người khác) với: tên (bắt buộc, ≤ 60 ký tự), vai trò (Member; Owner chỉ khi người tạo là Owner), quyền dùng lượt phim và học phong cách (mặc định: không), giới hạn số yêu cầu mỗi phút (10, 30, 60, 120 hoặc 300; mặc định 60), hạn dùng (7 ngày, 30 ngày, 90 ngày, 1 năm hoặc Never; mặc định 90 ngày).
- **FR-210**: Mã MUST hiện đúng một lần lúc tạo. Xưởng MUST chỉ giữ bản băm của mã và vài ký tự đầu để nhận ra; không trang nào, API nào hay nhật ký nào hiện lại mã đầy đủ.
- **FR-211**: Mọi API của xưởng MUST nhận mã trong header `Authorization: Bearer <mã>` như một phiên đăng nhập của người được thay mặt, giới hạn theo vai trò và quyền của mã. Yêu cầu có mã không cần thêm gì để chống giả mạo yêu cầu của trình duyệt.
- **FR-212**: Mã không có quyền dùng lượt MUST bị từ chối khi giao phim, học phong cách hay yêu cầu sửa phim, và không trừ lượt.
- **FR-213**: Mã Owner MUST dùng được các API quản trị, **trừ**: tạo hoặc thu hồi mã API (kể cả mã của chính mình), quản lý người dùng (Users), và đăng nhập, đăng xuất, thêm hay xoá tài khoản Claude. Những việc đó chỉ làm được từ trình duyệt đã đăng nhập.
- **FR-214**: Mã MUST bị từ chối ngay khi đã thu hồi, đã hết hạn, hoặc người được thay mặt đã tắt hay đã xoá. Vai trò thực của mã MUST là vai trò thấp hơn giữa vai trò của mã và vai trò hiện tại của người được thay mặt.
- **FR-215**: Mã vượt giới hạn số yêu cầu mỗi phút MUST bị từ chối tạm thời, kèm thời gian chờ.
- **FR-216**: Danh sách mã (của mình ở Your account; của mọi người ở tab API tokens của Owner) MUST hiện: tên, vài ký tự đầu, người sở hữu, vai trò, có quyền dùng lượt không, số yêu cầu và số yêu cầu bị chặn hôm nay (theo giờ Việt Nam), lần dùng gần nhất, hạn dùng, trạng thái (Active · Ended · Revoked). Mỗi mã có menu ⋯ với **Log** (200 yêu cầu gần nhất của mã: lúc, phương thức, đường dẫn, kết quả) và Revoke (có hỏi xác nhận); người sở hữu và Owner xem và thu hồi được.
- **FR-217**: Mục API tokens (ở Your account và ở tab của Owner) MUST có khung **For agents**: Base URL của xưởng, header cần gửi, link tài liệu API dạng OpenAPI (chỉ các API mà mã dùng được, không có API nội bộ), link tài liệu đọc được bằng mắt,, địa chỉ **máy chủ MCP** của xưởng, lệnh mẫu để nối Claude Code (`claude mcp add` kèm header mã), cấu hình JSON cho các trình MCP khác, và các giới hạn của mã; mỗi mục có nút Copy. Ngay sau khi tạo mã, hộp thoại MUST có ba nút: **Copy token**, **Copy MCP command** (lệnh đã điền sẵn mã) và **Copy for an agent** (một đoạn hướng dẫn ngắn để dán cho tác tử: địa chỉ, header, tài liệu, MCP, hỏi người dùng trước khi tốn lượt, gửi Idempotency-Key, việc dài thì hỏi lại trạng thái).
- **FR-219**: Xưởng MUST có một **máy chủ MCP** như neb-creative-tool, để tác tử AI (như Claude Code) nối thẳng vào xưởng bằng một mã API. Máy chủ MCP MUST đưa ra các công cụ tương ứng với việc thành viên làm trên giao diện: xem danh sách phong cách (thư viện và của mình), giao phim, yêu cầu sửa một phim đã xong, **học phong cách** (từ kênh YouTube hoặc từ video đã tải lên, FR-220), xem danh sách việc và trạng thái một việc, xem và trả lời các yêu cầu duyệt (câu hỏi, kịch bản, hai lần duyệt bản nháp phong cách), lấy link tải phim đã xong. Với mã Owner, MUST có thêm các công cụ chỉ đọc: tình trạng worker, Latest jobs, mức dùng. Như neb, máy chủ MCP MUST có thêm ba công cụ chung: liệt kê các API, mô tả một API, và gọi một API bất kỳ của xưởng (chỉ dưới `/api/v1`), kèm tài liệu OpenAPI như một tài nguyên MCP; các lệnh gọi này chịu đúng mọi chốt chặn của mã. Mỗi công cụ MUST tuân đúng vai trò, quyền dùng lượt và giới hạn số yêu cầu của mã (FR-211 đến FR-215), và MUST NOT làm được những việc ở FR-213.
- **FR-220**: Qua máy chủ MCP, tác tử MUST học được phong cách như trên web:
  - từ **kênh YouTube**: tác tử MUST gửi kèm xác nhận quyền dùng video (cùng văn bản và cùng điều kiện như trên web, 007); thiếu xác nhận thì bị từ chối;
  - từ **video tải lên**: tác tử MUST tải video lên được qua MCP với đúng giới hạn của web (dung lượng, độ dài, số video mỗi lần học), rồi dùng các video đó để giao việc học;
  - hai lần duyệt bản nháp phong cách MUST trả lời được qua công cụ trả lời duyệt; video tham chiếu vẫn bị xoá khi việc học kết thúc như 007.
- **FR-218**: Mỗi yêu cầu dùng mã (kể cả qua MCP) MUST được ghi vào nhật ký của mã: lúc, phương thức, đường dẫn, kết quả (cho qua, hoặc lý do bị chặn: sai quyền, không được dùng lượt, vượt giới hạn mỗi phút, đường cấm, gửi lại theo Idempotency-Key), địa chỉ IP. Nhật ký giữ 30 ngày. Xưởng MUST NOT lưu nội dung yêu cầu hay phản hồi.
- **FR-221**: Giao việc (giao phim, sửa phim, học phong cách) MUST nhận header `Idempotency-Key`: gửi lại cùng khoá trong 24 giờ thì xưởng trả lại đúng việc đã tạo lần đầu, không tạo việc mới, không trừ thêm lượt, không kiểm nội dung lần nữa. Cùng khoá nhưng nội dung khác MUST bị từ chối. Công cụ MCP giao việc MUST nhận và chuyển khoá này.

### Key Entities

- **Worker heartbeat**: một tiến trình worker; tên máy hoặc mã tiến trình, lần báo sống gần nhất, việc đang chạy (nếu có), lúc bắt đầu.
- **API token**: tên, vài ký tự đầu, bản băm, người sở hữu (cũng là người tạo và người được thay mặt), vai trò, quyền dùng lượt, giới hạn mỗi phút, lúc tạo, hạn dùng, lúc thu hồi, lần dùng gần nhất.
- **Token request**: một yêu cầu dùng mã: lúc, phương thức, đường dẫn, kết quả, IP; giữ 30 ngày. Số yêu cầu và số bị chặn hôm nay tính từ đây.
- **Idempotency record**: khoá do tác tử gửi, người gửi, dấu của nội dung yêu cầu, việc đã tạo; giữ 24 giờ.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-201**: Chủ xưởng biết worker còn chạy hay không trong vòng 5 giây kể từ khi mở tab Worker, không cần mở terminal.
- **SC-202**: Khi worker dừng, tab Worker đổi sang "Not responding" hoặc "No worker is running" trong vòng 40 giây.
- **SC-203**: Bốn ô đếm và Latest jobs khớp 100% với trạng thái thật của các việc (kiểm tự động).
- **SC-204**: 0 lần mã đầy đủ xuất hiện trong cơ sở dữ liệu, nhật ký, trang web hay API sau lúc tạo (kiểm tự động bằng cách tìm chuỗi mã).
- **SC-205**: 100% yêu cầu dùng mã đã thu hồi, hết hạn, sai, hoặc vượt quyền (vai trò, lượt, các việc ở FR-213) bị từ chối (kiểm tự động).
- **SC-206**: Một tác tử chỉ có Base URL, mã và đoạn mẫu ở khung For agents giao được một phim và tải được phim về mà không cần người hướng dẫn thêm.
- **SC-207**: Claude Code nối vào máy chủ MCP bằng đúng lệnh mẫu ở khung For agents (một lệnh), rồi giao được một phim, theo dõi tới khi xong và lấy được link tải, chỉ bằng các công cụ MCP.
- **SC-209**: Gửi cùng một yêu cầu giao phim với cùng Idempotency-Key 5 lần (kể cả cùng lúc) tạo đúng 1 việc và trừ đúng 1 lượt (kiểm tự động).
- **SC-208**: Chỉ bằng các công cụ MCP, một tác tử tải lên 3 video của mình, học xong một phong cách (qua cả hai lần duyệt) và dùng phong cách đó giao một phim (kiểm tự động với tác tử giả).

## Assumptions

- Xây trên 008: Settings đã có tab General, Users, Usage; vai trò Owner (`admin`) và Member (`customer`); giới hạn số yêu cầu và phiên đăng nhập có sẵn. Thêm hai tab mới theo bố cục neb-creative-tool (và mục API tokens ở trang Your account), giữ màu của xưởng.
- Chỉ dùng nội bộ như 008. Mã API là cách để công cụ của chính nhóm dùng xưởng, không phải để mở cho bên ngoài.
- Mỗi người dùng tự tạo mã cho chính mình (Clarifications 2026-11-09); Owner giám sát và thu hồi được mọi mã, nhưng không tạo mã thay mặt người khác.
- Không có tính năng "chi tiền" như neb ("Can spend", hạn mức tiền mỗi ngày): xưởng chạy bằng gói Claude. "Dùng lượt" ở đây là lượt phim và lượt học phong cách hằng tháng của người được thay mặt.
- Không làm Licenses, không làm webhook, không làm danh sách IP được phép, trần chi tiền hay báo động chi tiền ở bản này. Không nhận link http(s) để xưởng tự tải tệp về (khác neb): tác tử tải tệp lên bằng link dùng một lần (FR-220).
- Latest jobs giữ 20 việc như neb; muốn xem thêm thì dùng trang Jobs có sẵn.
