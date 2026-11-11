# Feature Specification: License key và tự cập nhật cho app desktop

**Feature Branch**: `017-desktop-license-updates`

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "017 first": license key và tự cập nhật cho app desktop (015, 016), theo cách của neb-creative-tool.

## Clarifications

### Session 2026-11-11

- Q: Mất mạng thì app dùng tiếp được bao lâu? → A: 7 ngày (FR-005).
- Q: Chủ xưởng quản lý key ở đâu? → A: một trang web nhỏ trên chính máy chủ license, đăng nhập bằng mật khẩu chủ xưởng (FR-012).
- Q: Bản 0.2.0 có cho dùng tạm không cần key? → A: không; cần key ngay từ 0.2.0 (Edge Cases).

## Bối cảnh

Lộ trình app desktop (2026-11-11), hướng A: mỗi người ngoài cài app, chạy xưởng trên máy mình bằng tài khoản Claude và khoá YouTube của chính họ.
- **016** đã phát hành `desktop-v0.1.0`: bộ cài Windows và macOS. Chủ xưởng tự gửi tệp cài cho từng người. Chưa có gì giới hạn ai được dùng, và chưa có cập nhật.
- **017** (spec này):
  - **License key**: chủ xưởng cấp và thu hồi quyền dùng app cho từng người, theo số máy.
  - **Tự cập nhật**: người dùng nhận bản mới mà không cần chủ xưởng gửi tệp.

neb-creative-tool đã làm việc này, và 017 đi theo cùng hướng:
- một máy chủ license nhỏ của chủ xưởng;
- key ngẫu nhiên, máy chủ chỉ giữ mã băm;
- mỗi máy nhận một "giấy phép ngắn hạn" (lease) có chữ ký, dùng được khi mất mạng trong vài ngày;
- bản phát hành riêng tư được máy chủ license chuyển tiếp cho người có key hợp lệ.

License chỉ chặn người dùng bình thường; người sửa được mã của app vẫn vượt qua được. neb cũng nhận giới hạn này.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chủ xưởng cấp key, người dùng nhập key để mở app (Priority: P1)

Chủ xưởng tạo một key cho một người, đặt số máy được dùng và ngày hết hạn (nếu có), rồi gửi key cho họ. Người dùng mở app lần đầu, nhập key, và dùng được xưởng. Chủ xưởng thấy máy nào đang dùng key nào.

**Why this priority**: không có phần này thì không kiểm soát được ai dùng app. Đây là lý do có 017.

**Independent Test**: chạy máy chủ license trên một máy thử. Tạo key với 1 máy. Mở app (bản có địa chỉ máy chủ license), nhập key, thấy cửa sổ chính. Mở app ở máy thứ hai với cùng key thì bị từ chối, kèm lý do "hết số máy".

**Acceptance Scenarios**:

1. **Given** một key còn hạn, còn chỗ, **When** người dùng nhập key lần đầu, **Then** app mở xưởng, và trang quản lý key hiện máy đó (tên máy, hệ điều hành, phiên bản app, lần thấy gần nhất).
2. **Given** một key sai, **When** người dùng nhập, **Then** app báo "key không đúng", không mở xưởng. Nhập sai quá 10 lần trong 10 phút từ một địa chỉ thì máy chủ tạm từ chối.
3. **Given** một key đã dùng hết số máy, **When** nhập ở máy mới, **Then** app báo hết số máy và nhắc liên hệ chủ xưởng. Chủ xưởng gỡ một máy cũ thì máy mới nhập lại được.
4. **Given** app đã kích hoạt, **When** máy mất mạng, **Then** app vẫn chạy thêm 7 ngày kể từ lần gia hạn cuối (FR-005), rồi khoá.
5. **Given** key được tạo, **When** chủ xưởng đóng trang, **Then** key không bao giờ hiện lại. Máy chủ chỉ giữ mã băm và 4 ký tự cuối.

---

### User Story 2 - Thu hồi và khoá (Priority: P1)

Chủ xưởng thu hồi một key, hoặc key hết hạn, hoặc gỡ một máy. App của người đó khoá lại trong thời gian ngắn: cửa sổ chính ẩn đi, việc đang chạy được làm xong, không nhận việc mới, dữ liệu không mất. Nhập key hợp lệ khác thì mở lại.

**Why this priority**: cấp key mà không thu hồi được thì vô nghĩa.

**Independent Test**: kích hoạt app, rồi thu hồi key trên trang quản lý. Trong 15 phút (đang có mạng), app hiện màn hình khoá. Mở trang của xưởng bằng trình duyệt thì nhận trang "đã khoá". Bật lại key, nhập lại thì app mở.

**Acceptance Scenarios**:

1. **Given** app đang chạy và có mạng, **When** key bị thu hồi, **Then** app khoá trong tối đa 15 phút. Việc đang chạy được chạy xong; xưởng không nhận việc mới.
2. **Given** app đang khoá, **When** ai đó mở trang của xưởng trực tiếp bằng trình duyệt, **Then** xưởng trả trang "đã khoá", trừ trang kiểm tình trạng.
3. **Given** máy bị chỉnh lùi đồng hồ, **When** app kiểm giấy phép, **Then** app coi như hết hạn và khoá.
4. **Given** máy chủ trả lời "từ chối" (key bị thu hồi, hết hạn, máy bị gỡ), **When** máy mất mạng sau đó, **Then** app vẫn khoá (không quay về giấy phép cũ).

---

### User Story 3 - Tự cập nhật (Priority: P2)

Chủ xưởng gắn tag phát hành bản mới. App của người dùng có key hợp lệ tự thấy bản mới trong vài giờ và tải về. Trên Windows, bản mới cài khi thoát app (hoặc khi bấm "Khởi động lại ngay"), và phần lõi được cài lại mà vẫn giữ dữ liệu. Trên macOS, app hiện tệp `.dmg` mới để người dùng kéo vào Applications.

**Why this priority**: bớt việc gửi tệp bằng tay cho chủ xưởng. Không có nó app vẫn dùng được.

**Independent Test**: phát hành bản `X.Y.Z+1` (thử). App bản `X.Y.Z` có key hợp lệ: bấm "Check for updates" trên khay, thấy bản mới tải về và kiểm xong. Windows: thoát app, mở lại thấy bản mới, phim cũ vẫn còn. Key bị thu hồi thì không tải được bản mới.

**Acceptance Scenarios**:

1. **Given** có bản mới, **When** app kiểm (lúc mở, rồi mỗi 4 giờ, hoặc bấm tay), **Then** app tải bản mới về, kiểm chữ ký, và báo "bản mới sẵn sàng".
2. **Given** tệp tải về bị hỏng hoặc bị thay, **When** app kiểm, **Then** app bỏ tệp đó và không cài.
3. **Given** Windows và bản mới đã sẵn sàng, **When** người dùng thoát app hoặc bấm "Khởi động lại ngay", **Then** bản mới được cài cho riêng người dùng (không hỏi quyền quản trị). Lần mở sau, phần lõi mới được cài, dữ liệu giữ nguyên (016 FR-012).
4. **Given** macOS, **When** bản mới sẵn sàng, **Then** app mở tệp `.dmg` mới và hướng dẫn kéo vào Applications.
5. **Given** key không hợp lệ, **When** app hỏi bản mới, **Then** máy chủ từ chối.

---

### Edge Cases

- **Máy chủ license tắt hoặc mất mạng**: app dùng giấy phép đã có tới hết hạn; chỉ khoá khi hết hạn hoặc khi máy chủ trả lời "từ chối".
- **Cài lại Windows hay cài lại bản Linux của app**: mã máy lấy từ phía Windows hoặc macOS, không lấy từ bản Linux, nên cài lại phần lõi không tốn thêm một máy.
- **Đang làm phim thì bị khoá**: phim đang dựng được làm xong (tối đa 6 giờ). Người dùng xem được phim đó sau khi mở khoá lại.
- **Tải bản mới bị ngắt**: lần sau tải tiếp hoặc tải lại; tệp chưa xong không bao giờ được cài.
- **Bản 0.1.0 đã phát (chưa có license)**: không tự cập nhật được, vì 0.1.0 chưa có phần cập nhật. Người dùng phải tự cài bản 0.2.0 một lần, và 0.2.0 cần key ngay (không có thời gian dùng tạm). Chủ xưởng gửi key cùng tệp cài 0.2.0.
- **Bản phát triển hoặc build không có địa chỉ máy chủ license**: không có license, không có cập nhật (như hiện nay).
- **Chủ xưởng mất khoá ký**: mọi app đã cài không kiểm được giấy phép mới; phải phát hành bản mới. Hướng dẫn triển khai nhắc sao lưu khoá ký.

## Requirements *(mandatory)*

### Functional Requirements

**Máy chủ license**
- **FR-001**: Máy chủ license MUST là một dịch vụ riêng, chạy trên máy chủ của chủ xưởng, có HTTPS, triển khai bằng một bộ cấu hình có sẵn trong repo (như `deploy/`). Nó lưu key, máy và nhật ký thay đổi, và sao lưu hằng ngày.
- **FR-002**: Key MUST là chuỗi ngẫu nhiên dễ đọc (không có ký tự dễ nhầm), hiện **một lần** lúc tạo. Máy chủ chỉ lưu mã băm và 4 ký tự cuối. Mỗi key có: tên người dùng (nhãn), ghi chú, số máy (1–20, mặc định 1), ngày hết hạn (có thể không có), trạng thái thu hồi.
- **FR-003**: Kích hoạt và gia hạn dùng chung một lời gọi, gửi key, mã máy, tên máy, hệ điều hành và phiên bản app. Máy chủ trả về một giấy phép ngắn hạn có chữ ký (của máy đó, hết hạn sớm hơn trong hai mốc: thời gian dùng khi mất mạng hoặc ngày hết hạn của key), hoặc một lý do từ chối rõ ràng: `unknown`, `revoked`, `expired`, `device_limit`, `device_removed`.
- **FR-004**: Nhập sai key MUST bị giới hạn: tối đa 10 lần mỗi 10 phút cho mỗi địa chỉ. Khoá ký riêng và mã quản trị chỉ nằm trên máy chủ license, không vào repo.

**App desktop**
- **FR-005**: App MUST hỏi key khi chưa có giấy phép hợp lệ. Có mạng thì gia hạn mỗi khoảng 15 phút. Mất mạng thì dùng tiếp tới khi giấy phép hết hạn: thời gian dùng khi mất mạng là **7 ngày**.
- **FR-006**: App MUST kiểm giấy phép trên máy: chữ ký đúng, đúng máy này, chưa hết hạn, đồng hồ không bị lùi (giữ mốc giờ lớn nhất từng thấy, cho phép lệch 10 phút).
- **FR-007**: Mã máy MUST lấy từ hệ điều hành chính (Windows hoặc macOS), băm lại trước khi gửi, và không đổi khi cài lại phần lõi.
- **FR-008**: Khi khoá, app MUST:
  - ẩn cửa sổ chính, khay báo "đã khoá", hiện màn hình nhập key;
  - để việc đang chạy làm xong và không nhận việc mới;
  - giữ nguyên mọi dữ liệu.

  Nhập key hợp lệ thì mở lại.
- **FR-009**: Phần lõi của xưởng MUST tự kiểm lại giấy phép mà app ghi ra cho nó, và trả lời "đã khoá" cho mọi trang và lời gọi, trừ trang kiểm tình trạng. Nhờ vậy mở xưởng bằng trình duyệt cũng không vượt được khoá.
- **FR-010**: Key MUST được cất bằng kho bí mật của hệ điều hành (Windows: mã hoá theo tài khoản người dùng; macOS: Keychain). Khay có mục "License…" để xem người được cấp, ngày hết hạn và đổi key.
- **FR-011**: Bản build không có địa chỉ máy chủ license MUST không có license và không có cập nhật. Bộ test và GitHub Actions dùng một máy chủ license giả.

**Quản lý key**
- **FR-012**: Chủ xưởng MUST quản lý được:
  - key: tạo, sửa nhãn, ghi chú, số máy và ngày hết hạn; thu hồi, bật lại, xoá;
  - máy: xem từng máy của key (tên, hệ điều hành, phiên bản, địa chỉ, lần đầu và lần cuối thấy); gỡ máy, cho phép lại.

  Nơi quản lý: một trang web nhỏ trên chính máy chủ license, đăng nhập bằng mật khẩu của chủ xưởng (lưu dạng băm; phiên đăng nhập bằng cookie an toàn; nhập sai mật khẩu bị giới hạn như FR-004). Không có mã quản trị nào tới trình duyệt.

**Cập nhật**
- **FR-013**: Máy chủ license MUST chuyển tiếp các tệp của bản phát hành mới nhất (riêng tư) cho app có giấy phép còn tốt **ngay lúc đó** (key và máy vẫn hợp lệ). Chỉ các tên tệp trong danh sách cho phép mới được chuyển tiếp. Mã truy cập GitHub chỉ nằm trên máy chủ.
- **FR-014**: Mỗi bản phát hành MUST có danh sách tệp và mã SHA-256, được ký bằng khoá ký của license. App MUST kiểm chữ ký và SHA-256 trước khi dùng một tệp.
- **FR-015**: App MUST kiểm bản mới 30 giây sau khi mở, rồi mỗi 4 giờ, và khi bấm "Check for updates" trên khay. App tải tệp vào một thư mục riêng (tệp tạm rồi đổi tên); không tải khi đang khoá.
- **FR-016**: Windows: bản mới MUST cài khi thoát app hoặc khi bấm "Khởi động lại ngay", cho riêng người dùng, không hỏi quyền quản trị. Lần mở sau, nếu phần lõi khác phiên bản thì cài lại phần lõi và giữ dữ liệu (016 FR-012).
- **FR-017**: macOS (ký ad-hoc, không tự thay app được): app MUST mở tệp `.dmg` mới và hướng dẫn kéo vào Applications.
- **FR-018**: Workflow phát hành (016) MUST thêm tệp mô tả bản phát hành mà phần cập nhật cần, và tệp chữ ký. Khoá ký dùng trong GitHub Actions là secret của repo.

### Key Entities

- **License key**: nhãn, ghi chú, mã băm, 4 ký tự cuối, số máy, ngày hết hạn, thu hồi lúc nào, tạo lúc nào. Trạng thái suy ra: đang dùng, hết hạn, thu hồi.
- **Máy (seat)**: thuộc một key; mã máy (đã băm), tên, hệ điều hành, phiên bản app, địa chỉ gần nhất, lần đầu và lần cuối thấy, gỡ lúc nào.
- **Giấy phép ngắn hạn (lease)**: key nào, máy nào, nhãn, cấp lúc nào, hết hạn lúc nào, key hết hạn lúc nào. Có chữ ký của máy chủ license.
- **Bản phát hành**: phiên bản, danh sách tệp kèm SHA-256 và kích thước, chữ ký.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Người dùng nhập key và thấy xưởng trong dưới 1 phút (có mạng).
- **SC-002**: Key bị thu hồi thì app có mạng khoá trong tối đa 15 phút, và mở xưởng bằng trình duyệt cũng nhận trang "đã khoá" (kiểm tự động bằng máy chủ license giả và đồng hồ giả).
- **SC-003**: App có key hợp lệ nhận bản mới trong tối đa 4 giờ sau khi phát hành; trên Windows cài xong khi mở lại, phim và tài khoản còn nguyên (kiểm bằng tay một lần).
- **SC-004**: Tệp cập nhật bị sửa một byte thì bị từ chối 100% (kiểm tự động).
- **SC-005**: Không có key, khoá ký hay mã quản trị nào trong repo, trong bộ cài hay trong log (kiểm tự động bằng tìm chuỗi).
- **SC-006**: Nhập sai key lần thứ 11 trong 10 phút từ một địa chỉ bị từ chối (kiểm tự động).

## Assumptions

- Máy chủ license chạy trên một VPS nhỏ của chủ xưởng (1 CPU, 1 GB), có tên miền. Chủ xưởng tự thuê VPS và tên miền; 017 có hướng dẫn và cấu hình triển khai.
- Số người dùng nhỏ (vài chục), nên một tiến trình và một cơ sở dữ liệu tệp là đủ.
- Không thu tiền trong app. Chủ xưởng tự thoả thuận với người dùng, rồi cấp key.
- Bộ cài vẫn chưa ký số (như 016). Windows tự cài bản mới được vì bộ cài cho riêng người dùng; macOS thì không.
- Phiên bản đầu có license là `0.2.0`.
