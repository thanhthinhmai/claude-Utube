# Feature Specification: Tiết kiệm token cho agent của việc

**Feature Branch**: `030-agent-token-savings`

**Created**: 2026-11-23

**Status**: Draft

**Input**: User description: "Agent token savings for the studio's job agents (desktop app local mode and online VPS mode share tools/runner/worker.py, proxy.py, agent.py). (1) Proxy keeps one Claude account (plan slot) per job so prompt cache stays warm: a job keeps using the slot it got first; switch only when that slot hits 429/limit or needs sign-in; new jobs still pick the least-used slot. (2) Agent compacts earlier and keeps the right things: worker passes CLAUDE_CODE_AUTO_COMPACT_WINDOW (default 300000) and BASH_MAX_OUTPUT_LENGTH (default 20000) into the job's agent environment; agent.py appends compact instructions to its system prompt (keep: film name, current step, pending review, next step, files written, check results; drop: file contents, long logs). (3) PreCompact hook in agent.py (SDK HookMatcher) saves a small state file in the job folder (current step, git-free: list of recent files changed, last check results) before compaction, no Claude call. Must not change which model is used (specs/024) nor the token cap per job."

## Bối cảnh

- Một việc làm phim gọi Claude hàng trăm lượt. Mỗi lượt gửi lại cả hội thoại; phần đã có trong bộ nhớ đệm (cache) của tài khoản Claude chỉ tốn khoảng 0,1 lần giá đọc thường, phần không có thì tốn đủ giá và tính vào hạn mức 5 giờ của gói.
- Bộ chuyển tiếp hiện chọn lại tài khoản "dùng ít nhất trong 5 giờ" ở **mỗi lượt gọi**. Bộ nhớ đệm gắn với từng tài khoản, nên khi xưởng có từ 2 tài khoản trở lên, các lượt liên tiếp của cùng một việc dễ đổi tài khoản và mất bộ nhớ đệm.
- Agent của việc dùng ngưỡng tự gọn hội thoại mặc định (gần đầy cửa sổ ngữ cảnh), không có hướng dẫn giữ gì khi gọn, và đầu ra lệnh dài được đưa thẳng vào hội thoại.
- App desktop (chế độ trên máy, specs/014) và bản online trên VPS (specs/007–008) dùng chung bộ chạy việc, bộ chuyển tiếp và agent, nên thay đổi áp dụng cho cả hai.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Một việc giữ một tài khoản Claude (Priority: P1)

Chủ xưởng có nhiều tài khoản Claude. Khi một việc chạy, mọi lượt gọi của việc đó đi qua cùng một tài khoản cho tới khi tài khoản ấy hết hạn mức hoặc cần đăng nhập lại; việc mới vẫn được giao cho tài khoản dùng ít nhất.

**Why this priority**: Đây là chỗ phí lớn nhất: mỗi lần đổi tài khoản giữa việc là một lần nạp lại toàn bộ ngữ cảnh với giá đầy đủ, ăn vào hạn mức của gói.

**Independent Test**: Chạy bộ chuyển tiếp với 2 tài khoản giả, gửi nhiều lượt cho cùng một việc trong khi số dùng của hai tài khoản đảo thứ tự; mọi lượt phải tới cùng một tài khoản.

**Acceptance Scenarios**:

1. **Given** 2 tài khoản dùng được và việc A đã gọi lần đầu qua tài khoản 1, **When** tài khoản 2 trở thành tài khoản dùng ít hơn, **Then** các lượt tiếp theo của việc A vẫn đi qua tài khoản 1.
2. **Given** việc A đang giữ tài khoản 1, **When** tài khoản 1 trả lỗi hết hạn mức (429), **Then** lượt đó được gửi lại qua tài khoản kế tiếp dùng được, và các lượt sau của việc A ở lại tài khoản mới.
3. **Given** việc A đang giữ tài khoản 1, **When** tài khoản 1 cần đăng nhập lại hoặc bị gỡ khỏi danh sách dùng được, **Then** việc A chuyển sang tài khoản dùng được khác mà không lỗi.
4. **Given** việc A giữ tài khoản 1, **When** việc B mới bắt đầu, **Then** việc B được giao cho tài khoản dùng ít nhất lúc đó (có thể khác tài khoản 1).
5. **Given** việc A đã xong hoặc bị huỷ, **When** xem trạng thái bộ chuyển tiếp, **Then** việc A không còn giữ tài khoản nào.

---

### User Story 2 - Agent gọn hội thoại sớm hơn và giữ đúng thứ (Priority: P2)

Agent của việc tự gọn hội thoại khi đạt ngưỡng do xưởng đặt (mặc định 300.000 token), đầu ra lệnh quá dài được ghi ra tệp thay vì đưa thẳng vào hội thoại, và bản tóm tắt khi gọn giữ những thứ việc làm phim cần.

**Why this priority**: Hội thoại nhỏ hơn thì mỗi lượt rẻ hơn; tóm tắt giữ đúng thứ thì agent không phải đọc lại tệp hay làm lại bước sau khi gọn.

**Independent Test**: Khởi động agent của một việc với bộ chạy giả; kiểm môi trường và lời dặn hệ thống mà agent nhận được.

**Acceptance Scenarios**:

1. **Given** xưởng không đặt gì riêng, **When** một việc làm phim bắt đầu, **Then** agent nhận ngưỡng gọn 300.000 token và giới hạn đầu ra lệnh 20.000 ký tự.
2. **Given** chủ xưởng đặt ngưỡng khác qua biến môi trường của bộ chạy việc, **When** việc bắt đầu, **Then** agent nhận đúng giá trị đó.
3. **Given** agent khởi động, **When** đọc lời dặn hệ thống, **Then** có mục hướng dẫn gọn: giữ tên phim, bước đang làm, yêu cầu duyệt đang chờ, bước kế tiếp, tệp đã ghi, kết quả kiểm; bỏ nội dung tệp đã đọc và log dài.

---

### User Story 3 - Lưu trạng thái trước khi gọn (Priority: P3)

Ngay trước khi agent gọn hội thoại, xưởng ghi một tệp trạng thái nhỏ trong thư mục việc (bước đang làm, các tệp vừa đổi, kết quả kiểm gần nhất), không gọi Claude, để người xem và agent tìm lại được chi tiết mà tóm tắt có thể bỏ sót.

**Why this priority**: Lưới an toàn cho P2; hữu ích nhưng việc vẫn chạy được khi thiếu.

**Independent Test**: Gọi bộ xử lý "trước khi gọn" với thư mục việc mẫu; kiểm tệp trạng thái được ghi đúng nội dung và kích thước.

**Acceptance Scenarios**:

1. **Given** thư mục việc có phim với vài tệp vừa đổi và `checks.json`, **When** agent sắp gọn, **Then** tệp trạng thái được ghi trong thư mục việc, có bước đang làm, tối đa 20 tệp đổi gần nhất kèm giờ đổi, và tóm tắt kết quả kiểm gần nhất.
2. **Given** việc gọn nhiều lần, **When** xem tệp trạng thái, **Then** nó phản ánh lần gọn gần nhất (ghi đè), không phình ra.
3. **Given** ghi tệp trạng thái lỗi (vd. thiếu quyền), **When** agent gọn, **Then** việc vẫn chạy tiếp; lỗi chỉ được ghi vào log.

### Edge Cases

- Chỉ có 1 tài khoản: hành vi giống hiện nay.
- Tài khoản đang giữ bị chủ xưởng gỡ hoặc tạm tắt giữa việc: việc chuyển sang tài khoản khác ở lượt kế tiếp.
- Mọi tài khoản đều hết hạn mức: giữ cách chờ và dùng khoá API dự phòng hiện có; sau khi có tài khoản dùng lại được, việc giữ tài khoản mới đó.
- Bộ chuyển tiếp khởi động lại giữa việc: việc chọn lại tài khoản dùng ít nhất ở lượt đầu tiên sau khởi động và giữ từ đó (mất bộ nhớ đệm một lần là chấp nhận được).
- Việc tiếp tục sau điểm duyệt (resume) trong vòng 1 giờ: vẫn dùng tài khoản đã giữ nếu nó còn dùng được.
- Biến môi trường đặt giá trị không hợp lệ (không phải số, dưới 100.000 cho ngưỡng gọn): dùng giá trị mặc định và ghi cảnh báo vào log.
- Việc chọn đề (`topics`) không dùng agent: không bị ảnh hưởng.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Bộ chuyển tiếp PHẢI nhớ tài khoản Claude mà mỗi việc đã dùng thành công và gửi các lượt sau của việc đó qua tài khoản ấy khi nó còn trong danh sách dùng được.
- **FR-002**: Bộ chuyển tiếp PHẢI chuyển việc sang tài khoản dùng được kế tiếp (theo thứ tự dùng ít nhất) khi tài khoản đang giữ trả lỗi hết hạn mức, cần đăng nhập lại, hoặc không còn trong danh sách dùng được; tài khoản mới trở thành tài khoản giữ của việc.
- **FR-003**: Việc chưa giữ tài khoản nào PHẢI được giao tài khoản như hiện nay (dùng ít nhất trong 5 giờ, hoặc thứ tự tay khi chủ xưởng chọn chế độ tay).
- **FR-004**: Bộ chuyển tiếp PHẢI bỏ tài khoản giữ của việc khi việc kết thúc (xong, lỗi, huỷ, bị thu hồi mã).
- **FR-005**: Bộ chạy việc PHẢI truyền cho agent ngưỡng gọn hội thoại (mặc định 300.000 token) và giới hạn đầu ra lệnh (mặc định 20.000 ký tự); chủ xưởng đổi được hai giá trị qua biến môi trường của bộ chạy việc.
- **FR-006**: Agent PHẢI có mục hướng dẫn gọn trong lời dặn hệ thống, nêu rõ thứ cần giữ và thứ cần bỏ như User Story 2.
- **FR-007**: Agent PHẢI ghi tệp trạng thái trong thư mục việc ngay trước mỗi lần gọn, không gọi Claude, với nội dung như User Story 3, kích thước không quá 8 KB.
- **FR-008**: Lỗi khi ghi tệp trạng thái KHÔNG ĐƯỢC làm dừng việc.
- **FR-009**: Thay đổi KHÔNG ĐƯỢC đổi model mà việc dùng (specs/024), giới hạn token của mỗi việc, cách tính token, hay đường dự phòng bằng khoá API.

### Key Entities

- **Tài khoản giữ của việc**: việc nào đang dùng tài khoản Claude nào; sinh ra ở lượt gọi thành công đầu tiên, đổi khi tài khoản lỗi, mất khi việc kết thúc.
- **Tệp trạng thái trước khi gọn**: bản ghi nhỏ trong thư mục việc: thời điểm, lý do gọn (tự động hay tay), bước đang làm, tệp đổi gần nhất, tóm tắt kết quả kiểm.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Trong test với 2 tài khoản, 100% lượt gọi của một việc đi qua cùng một tài khoản khi không có lỗi hạn mức hay đăng nhập, kể cả khi thứ tự "dùng ít nhất" đảo chiều giữa chừng.
- **SC-002**: Trong test lỗi hạn mức, việc chuyển tài khoản ngay ở lượt bị lỗi (0 lượt thất bại thấy được từ agent) và 100% lượt sau đó đi qua tài khoản mới.
- **SC-003**: Hai việc bắt đầu liên tiếp khi tài khoản 1 đang dùng nhiều hơn: việc thứ hai được giao tài khoản 2 (phân tải giữ nguyên).
- **SC-004**: Agent của mọi việc làm phim nhận ngưỡng gọn và giới hạn đầu ra lệnh đúng giá trị (mặc định hoặc đặt riêng) trong 100% lần khởi động ở test.
- **SC-005**: Tệp trạng thái được ghi trong dưới 1 giây, không quá 8 KB, và việc vẫn chạy tiếp khi ghi lỗi.
- **SC-006**: 5 bộ test của xưởng (`tests/run.sh`, `tests/learn/run.sh`, `tests/ui/run.sh`, `tests/filmcheck/run.sh`, `tests/online/run.sh`) đều đạt.

## Assumptions

- Bộ nhớ đệm của Claude gắn với tài khoản; giữ cùng tài khoản là điều kiện cần để trúng bộ nhớ đệm giữa các lượt.
- Agent SDK chuyển các biến môi trường `CLAUDE_CODE_AUTO_COMPACT_WINDOW` và `BASH_MAX_OUTPUT_LENGTH` tới Claude Code bên trong (tài liệu chính thức nêu cả hai).
- Tài khoản giữ chỉ cần nằm trong bộ nhớ của bộ chuyển tiếp; không cần lưu vào cơ sở dữ liệu.
- Hiệu quả tiết kiệm thật (tỉ lệ trúng bộ nhớ đệm trên việc chạy thật) được xem trên nhật ký gọi Claude sau khi triển khai; không chạy bài thật tốn tiền trong spec này.
- Ngoài phạm vi: đổi cách tính token vào giới hạn của việc, chạy agent con bằng model khác, sửa thư viện `lib/`.
