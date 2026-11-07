# Feature Specification: Xưởng online nội bộ chạy bằng gói Claude

**Feature Branch**: `008-claude-plan-login`

**Created**: 2026-11-07

**Status**: Draft

**Input**: User description: "Chế độ online dùng nội bộ, chạy bằng gói Claude (Pro/Max) thay cho khoá API. Xây trên 007-online-studio. Đăng ký công khai bị tắt; chỉ chủ xưởng và người được chủ xưởng mời (nhóm nội bộ) dùng được. Chủ xưởng đăng nhập một hoặc nhiều tài khoản Claude (tối đa 5) ngay trên trang quản trị, giống neb-creative-tool: bấm Sign in, mở trang đăng nhập Claude, dán mã nếu cần; xem trạng thái (email, gói) từng tài khoản; đăng xuất; thêm/xoá tài khoản. Việc chạy xoay vòng qua các tài khoản đã đăng nhập; tài khoản hết hạn mức hoặc cần đăng nhập lại thì bỏ qua và báo chủ xưởng. Xưởng không cần khoá API nữa. Khoá thật (token đăng nhập) không bao giờ vào container của việc. Chi phí tính bằng tiền không còn ý nghĩa: thay bằng đếm token/lượt dùng để theo dõi."

## Clarifications

### Session 2026-11-07

- Q: Khi không còn tài khoản Claude nào dùng được thì sao? → A: Như neb-creative-tool: chờ tối đa 15 giây, quá thì lỗi do xưởng (trả lượt) kèm giờ sớm nhất có tài khoản dùng lại (FR-110).
- Q: Có giữ khoá API làm dự phòng không? → A: Có, tuỳ chọn, chỉ dùng khi không còn tài khoản Claude nào dùng được (FR-117), như neb-creative-tool.
- Q: Chọn tài khoản Claude một lần cho cả việc, hay ở mỗi lần gọi? → A: Mỗi lần gọi lấy tài khoản dùng ít nhất còn dùng được, như neb-creative-tool (FR-107).
- Q: Khi xưởng chưa sẵn sàng (không tài khoản, không khoá), việc mới được nhận hay bị từ chối? → A: Bị từ chối "Studio is not ready", không trừ lượt (FR-110).

## Bối cảnh

Spec 007 đưa xưởng lên internet cho khách tự đăng ký, chạy Claude bằng khoá API của chủ xưởng. Người dùng đã chốt (2026-11-07) đổi hướng: **xưởng online chỉ dùng nội bộ** và chạy bằng **gói Claude (Pro/Max) của chủ xưởng**, không cần khoá API. Cách đăng nhập theo dự án trước của chủ xưởng (neb-creative-tool): nhiều tài khoản Claude, đăng nhập ngay trên trang, việc xoay vòng qua các tài khoản.

Lý do chỉ dùng nội bộ: điều khoản của Anthropic không cho dùng gói Claude cá nhân để phục vụ khách của một sản phẩm. Vì vậy spec này bỏ đăng ký công khai.

Spec này **sửa** 007, không thay thế nó. Mọi yêu cầu của 007 vẫn giữ, trừ các mục ghi ở phần "Thay đổi so với 007".

Mức quy trình: **Đầy đủ**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chủ xưởng đăng nhập gói Claude và chạy được một phim (Priority: P1)

Chủ xưởng mở trang quản trị, vào mục "Claude accounts" và bấm Sign in. Trang đăng nhập Claude mở ra. Chủ xưởng đăng nhập bằng tài khoản Pro hoặc Max, chép mã Claude đưa và dán vào trang quản trị. Tài khoản hiện là đã đăng nhập, kèm email và loại gói. Chủ xưởng giao một việc làm phim, và việc chạy xong bằng tài khoản đó, dù xưởng không có khoá API.

**Why this priority**: Không có bước này thì xưởng không chạy được Claude, nên mọi tính năng khác đều đứng.

**Independent Test**: Trên một xưởng chưa có khoá API và chưa có tài khoản Claude: đăng nhập một tài khoản trên trang quản trị → trạng thái hiện email và gói → giao một phim 20 giây → phim xong và đạt kiểm tra chất lượng của 007 (FR-011).

**Acceptance Scenarios**:

1. **Given** xưởng chưa có tài khoản Claude nào đăng nhập, **When** chủ xưởng mở trang quản trị, **Then** thấy cảnh báo "No Claude account signed in. Jobs cannot run.". Khi xưởng cũng không có khoá API, việc mới bị từ chối với "Studio is not ready" và không trừ lượt.
2. **Given** chủ xưởng bấm Sign in, **When** đăng nhập trên trang Claude và dán mã nhận được, **Then** trong vòng 10 giây tài khoản hiện là đã đăng nhập, kèm email và loại gói.
3. **Given** chủ xưởng dán sai mã hoặc mã đã hết hạn, **When** gửi, **Then** thấy thông báo lỗi và bấm Sign in lại được.
4. **Given** một tài khoản đã đăng nhập, **When** chủ xưởng bấm Sign out, **Then** tài khoản hiện là chưa đăng nhập và không việc nào dùng nó nữa.
5. **Given** việc đang chạy, **When** bất kỳ ai xem được bên trong môi trường của việc (tệp, biến, nhật ký), **Then** không thấy thông tin đăng nhập Claude thật.
6. **Given** người không phải chủ xưởng, **When** mở mục "Claude accounts" hoặc gọi API của nó, **Then** bị từ chối.

---

### User Story 2 - Nhiều tài khoản Claude, việc xoay vòng và tự bỏ qua tài khoản hỏng (Priority: P2)

Chủ xưởng thêm tối đa 5 tài khoản Claude. Mỗi lần gọi Claude đi qua tài khoản đã đăng nhập đang dùng ít nhất. Khi một tài khoản chạm hạn mức của gói hoặc cần đăng nhập lại, xưởng bỏ qua tài khoản đó, chuyển việc sang tài khoản khác, và báo cho chủ xưởng.

**Why this priority**: Một gói có hạn mức theo giờ và theo tuần. Nhiều tài khoản giúp nhóm làm nhiều phim hơn mà không phải chờ.

**Independent Test**: Đăng nhập 2 tài khoản → giao 4 việc → token chia cho 2 tài khoản lệch nhau không quá 20%. Giả lập tài khoản 1 chạm hạn mức giữa việc → việc đó chạy tiếp bằng tài khoản 2 và vẫn xong → trang quản trị hiện tài khoản 1 là "Limit reached" kèm giờ dùng lại được.

**Acceptance Scenarios**:

1. **Given** đã có 5 tài khoản, **When** chủ xưởng bấm "Add Claude account", **Then** bị từ chối kèm lý do (tối đa 5).
2. **Given** hai tài khoản đăng nhập cùng một tài khoản Claude, **When** xem danh sách, **Then** tài khoản sau được đánh dấu trùng và không được tính thêm vào vòng xoay.
3. **Given** nhiều tài khoản đã đăng nhập, **When** có việc mới, **Then** mỗi lần gọi Claude đi qua tài khoản còn dùng được có mức dùng thấp nhất.
4. **Given** một tài khoản chạm hạn mức của gói giữa việc, **When** việc gọi Claude lần sau, **Then** lệnh gọi đi qua một tài khoản khác còn dùng được, việc không lỗi, và tài khoản kia hiện "Limit reached" kèm giờ dùng lại (nếu dịch vụ cho biết).
5. **Given** một tài khoản bị Claude từ chối đăng nhập (hết hạn, bị thu hồi), **When** việc gọi tới, **Then** tài khoản hiện "Needs sign-in", ra khỏi vòng xoay, và chủ xưởng nhận email báo.
6. **Given** mọi tài khoản đều không dùng được, **When** việc đang chạy gọi Claude, **Then** nếu xưởng có khoá API dự phòng thì lệnh gọi đi qua khoá đó; nếu không, việc chờ tối đa 15 giây cho tài khoản sớm dùng lại nhất, quá thời gian thì lỗi do xưởng (trả lượt), kèm giờ sớm nhất có tài khoản dùng lại.
7. **Given** chủ xưởng xoá một tài khoản (không phải tài khoản đầu tiên), **When** xác nhận, **Then** tài khoản bị đăng xuất, thông tin đăng nhập bị xoá khỏi máy chủ, và nó biến khỏi danh sách.

---

### User Story 3 - Chỉ người được mời mới dùng được xưởng (Priority: P3)

Đăng ký công khai không còn. Chủ xưởng mời thành viên bằng email. Thành viên mở liên kết mời, đặt mật khẩu và dùng xưởng như khách ở 007. Chủ xưởng thu hồi được lời mời chưa dùng và khoá được thành viên.

**Why this priority**: Đây là điều kiện để dùng gói Claude đúng phạm vi nội bộ. Nó xếp sau US1 và US2 vì lúc chưa mời ai, chỉ chủ xưởng dùng xưởng.

**Independent Test**: Mở trang đăng ký khi chưa có lời mời → bị từ chối. Chủ xưởng mời một email → mở liên kết → đặt mật khẩu → giao được việc. Thu hồi một lời mời khác → liên kết đó không dùng được nữa.

**Acceptance Scenarios**:

1. **Given** bất kỳ ai không có lời mời, **When** mở trang đăng ký hoặc gọi API đăng ký, **Then** bị từ chối. Không có cài đặt nào bật lại được đăng ký công khai.
2. **Given** chủ xưởng mời một email, **When** người đó mở liên kết trong 7 ngày và đặt mật khẩu, **Then** tài khoản đã xác minh email, có hạn mức mặc định, và giao được việc.
3. **Given** liên kết mời đã dùng, đã quá 7 ngày hoặc đã bị thu hồi, **When** mở, **Then** bị từ chối.
4. **Given** xưởng 007 đã có tài khoản khách từ trước, **When** chuyển sang bản này, **Then** các tài khoản đó vẫn đăng nhập được, và chủ xưởng thấy danh sách để khoá những ai không thuộc nhóm.

---

### User Story 4 - Theo dõi mức dùng bằng token thay cho tiền (Priority: P4)

Chủ xưởng xem số token và số lần gọi Claude theo việc, theo ngày, theo thành viên và theo tài khoản Claude. Không còn trần chi phí ngày bằng tiền; chỉ phần đi qua khoá API dự phòng có số tiền ước tính.

**Why this priority**: Gói Claude trả cố định theo tháng, nên số tiền ước tính không còn đúng. Nhóm vẫn cần biết ai dùng bao nhiêu, nhưng việc này không chặn luồng chính.

**Independent Test**: Chạy 2 việc của 2 thành viên → trang mức dùng hiện token và số lần gọi đúng theo việc, theo thành viên và theo tài khoản Claude (lệch 0 so với tổng các lần gọi đã ghi) → khi không dùng khoá API, không chỗ nào hiện số tiền.

**Acceptance Scenarios**:

1. **Given** việc đã chạy xong, **When** mở trang việc hoặc trang mức dùng, **Then** thấy token vào, token ra và số lần gọi; chỉ phần đi qua khoá API dự phòng có số tiền ước tính.
2. **Given** một việc dùng vượt trần token của mỗi việc, **When** gọi Claude lần sau, **Then** bị từ chối, và việc lỗi do xưởng như "vượt trần chi phí của việc" ở 007.

### Edge Cases

- Chủ xưởng bấm Sign in hai lần liền: chỉ lần đăng nhập mới nhất còn hiệu lực, lần cũ bị huỷ.
- Chủ xưởng bỏ dở đăng nhập: sau 10 phút lần đăng nhập đó tự huỷ, bấm Sign in lại được.
- Máy chủ khởi động lại: các tài khoản đã đăng nhập vẫn còn đăng nhập.
- Thông tin đăng nhập hết hạn ngắn hạn: xưởng tự làm mới, không cần chủ xưởng đăng nhập lại, trừ khi Claude đòi đăng nhập lại.
- Tài khoản có gói miễn phí (không phải Pro hoặc Max): đăng nhập được nhưng bị đánh dấu cảnh báo.
- Việc đang chờ duyệt hoặc xếp hàng không giữ chỗ của tài khoản Claude nào.

## Requirements *(mandatory)*

### Functional Requirements

**Tài khoản Claude**
- **FR-101**: Chủ xưởng MUST đăng nhập được tài khoản Claude ngay trên trang quản trị: bấm Sign in, mở trang đăng nhập Claude, dán mã nhận được. Mỗi lần chỉ có một lần đăng nhập đang chờ, và nó tự huỷ sau 10 phút.
- **FR-102**: Xưởng MUST giữ tối đa 5 tài khoản Claude. Với mỗi tài khoản, trang quản trị MUST hiện: thứ tự, email, loại gói, trạng thái (Signed in · Signed out · Limit reached · Needs sign-in), giờ dùng lại (nếu có), có trùng tài khoản khác không.
- **FR-103**: Chủ xưởng MUST đăng xuất, thêm và xoá được tài khoản. Tài khoản đầu tiên chỉ đăng xuất được, không xoá được. Xoá MUST xoá thông tin đăng nhập khỏi máy chủ.
- **FR-104**: Thông tin đăng nhập Claude MUST chỉ nằm ở phần máy chủ không chạy việc. Nó MUST NOT vào môi trường của việc, nhật ký, trang web hay API, kể cả với chủ xưởng.
- **FR-105**: Thông tin đăng nhập MUST còn sau khi máy chủ khởi động lại, và MUST tự làm mới khi hết hạn ngắn hạn.
- **FR-106**: Chỉ vai trò quản trị MUST xem và thao tác được tài khoản Claude.

**Xoay vòng**
- **FR-107**: Mỗi lần gọi Claude MUST đi qua tài khoản còn dùng được có mức dùng thấp nhất (tính theo token trong cửa sổ hạn mức hiện tại của gói). Một việc có thể dùng nhiều tài khoản. Tài khoản trùng không được tính.
- **FR-108**: Khi một tài khoản bị từ chối vì hạn mức của gói, xưởng MUST đánh dấu "Limit reached" (kèm giờ dùng lại nếu dịch vụ cho biết), đưa nó ra khỏi vòng xoay tới giờ đó, và đưa lệnh gọi sang tài khoản khác. Việc MUST NOT lỗi chỉ vì đổi tài khoản.
- **FR-109**: Khi một tài khoản bị từ chối vì đăng nhập không còn hiệu lực, xưởng MUST đánh dấu "Needs sign-in", đưa nó ra khỏi vòng xoay cho tới khi đăng nhập lại, và gửi email cho chủ xưởng (tối đa một email cho mỗi tài khoản mỗi lần hỏng).
- **FR-110**: Khi không còn tài khoản nào dùng được, lệnh gọi MUST đi qua khoá API dự phòng nếu có (FR-117). Không có khoá thì lệnh gọi MUST chờ tối đa 15 giây cho tài khoản sớm dùng lại nhất; quá thời gian thì việc lỗi do xưởng (trả lượt, FR-006a của 007), kèm lý do và giờ sớm nhất có tài khoản dùng lại. Khi không có tài khoản nào dùng được và không có khoá API, việc mới MUST bị từ chối với "Studio is not ready", không trừ lượt (vì không kiểm được nội dung ý tưởng, 007 FR-013). Việc đã nằm trong hàng từ trước thì chờ, không bắt đầu chạy; trang quản trị và trang việc MUST hiện lý do "Waiting for a Claude account".

**Thành viên**
- **FR-111**: Đăng ký công khai MUST bị bỏ. Chỉ người có lời mời còn hiệu lực mới tạo được tài khoản.
- **FR-112**: Chủ xưởng MUST mời được thành viên bằng email, xem các lời mời đang chờ và thu hồi được. Lời mời dùng được một lần và hết hạn sau 7 ngày. Mở lời mời và đặt mật khẩu thì email được coi là đã xác minh.
- **FR-113**: Tài khoản có từ 007 MUST được giữ nguyên.

**Mức dùng**
- **FR-114**: Xưởng MUST ghi token vào, token ra và số lần gọi của mỗi việc, kèm tài khoản Claude đã dùng cho từng lần gọi.
- **FR-115**: Chủ xưởng MUST xem được mức dùng (token, số lần gọi, số việc) theo ngày, theo thành viên và theo tài khoản Claude.
- **FR-116**: Mỗi việc MUST có trần token (cài đặt). Vượt trần thì việc lỗi do xưởng (thay cho "vượt trần chi phí của việc" ở 007 FR-006a).
- **FR-117**: Xưởng MUST chạy được khi không có khoá API. Khoá API là tuỳ chọn, chỉ dùng làm dự phòng khi không còn tài khoản Claude nào dùng được; luôn ưu tiên gói Claude. Lần gọi qua khoá API MUST được ghi riêng và có chi phí ước tính như 007; trang mức dùng MUST tách "gói Claude" và "khoá API".

### Thay đổi so với 007

| Mục 007 | Thay bằng |
|---|---|
| FR-001 (người lạ tự đăng ký) | FR-111, FR-112 (chỉ người được mời) |
| FR-007: "bật hoặc tắt đăng ký" | Bỏ. FR-007: "trần chi phí tổng mỗi ngày" đổi thành FR-116 (trần token mỗi việc) |
| FR-008 (ước tính chi phí, trần chi phí ngày) | FR-114, FR-116 |
| FR-009: "chi phí theo ngày và theo khách" | FR-115 (token và số lần gọi) |
| FR-006a: "vượt trần chi phí của việc" | "vượt trần token của việc" (FR-116) |
| US3: kịch bản trần chi phí ngày, SC-005 | Bỏ |
| Assumption: "Chủ xưởng có một khoá API Claude" | Chủ xưởng có ít nhất một gói Claude Pro hoặc Max; khoá API là tuỳ chọn (FR-117) |

### Key Entities

- **Tài khoản Claude (Claude account)**: thứ tự (1–5), email, loại gói, trạng thái, giờ dùng lại, tài khoản trùng (nếu có). Thông tin đăng nhập giữ riêng, không bao giờ hiện ra.
- **Lời mời (Invite)**: email, người mời, lúc tạo, lúc hết hạn, đã dùng hay bị thu hồi.
- **Mức dùng (Usage)**: token vào, token ra, số lần gọi; theo việc, ngày, thành viên, tài khoản Claude hoặc khoá API. Chỉ lần gọi qua khoá API có chi phí ước tính.
- **Cài đặt (Settings)**: bỏ "bật/tắt đăng ký" và "trần chi phí ngày"; thêm "trần token mỗi việc".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-101**: Chủ xưởng đăng nhập xong một tài khoản Claude trong dưới 2 phút, tính từ lúc bấm Sign in.
- **SC-102**: Một phim 20 giây chạy xong và đạt kiểm tra chất lượng của 007 trên một xưởng không có khoá API.
- **SC-103**: 0 lần thông tin đăng nhập Claude xuất hiện trong môi trường của việc, nhật ký, trang web hoặc API (kiểm tự động bằng cách tìm chuỗi đăng nhập thật).
- **SC-104**: Khi một trong hai tài khoản chạm hạn mức giữa việc, 100% việc đang chạy vẫn xong mà không lỗi (kiểm tự động bằng dịch vụ Claude giả).
- **SC-105**: Với 2 tài khoản và 10 việc như nhau, tổng token mỗi tài khoản lệch nhau không quá 20%.
- **SC-106**: 100% yêu cầu đăng ký không có lời mời hợp lệ bị từ chối (kiểm tự động).
- **SC-107**: Tổng token trên trang mức dùng bằng đúng tổng token của các lần gọi đã ghi (lệch 0).

## Assumptions

- Chủ xưởng có ít nhất một gói Claude Pro hoặc Max và tự chịu trách nhiệm dùng gói theo điều khoản của Anthropic. Chủ xưởng chấp nhận rủi ro tài khoản bị hạn chế nếu nhóm dùng chung gói.
- Máy chủ ở xa, nên đăng nhập dùng cách dán mã. Không cần trang Claude quay về máy chủ.
- Hạn mức theo tháng của 007 (số phim, số lần học) vẫn giữ cho từng thành viên.
- Nhóm nhỏ, dưới 20 thành viên.
- Tài khoản quản trị đầu tiên vẫn tạo bằng lệnh trên máy chủ như 007.
- Ngoài phạm vi: đăng ký công khai, thanh toán, thành viên tự đăng nhập tài khoản Claude của họ, đi qua proxy riêng cho từng tài khoản (neb-creative-tool có, xưởng này chưa cần).
