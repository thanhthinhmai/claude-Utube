# Feature Specification: Xưởng phim online, bản dùng thử đầu tiên (giai đoạn 2)

**Feature Branch**: `007-online-studio`

**Created**: 2026-11-07

**Status**: Draft

**Input**: User description: "Phase 2: serve Film Studio to customers over the internet (accounts, server, Claude). First release of several specs. Full parity with the local studio: make films (library or learned styles) and learn styles, including fetching videos from YouTube channels the customer names (constitution 2.1.0 conditions). Open sign-up for anyone, quotas set in settings, no payment yet. Full level."

## Bối cảnh

Giai đoạn 1 (001–006) chạy trên máy của chủ xưởng: một người, nói chuyện với Claude trong khung chat, theo dõi và duyệt trên giao diện cục bộ. Giai đoạn 2 đưa xưởng lên internet cho khách. Khách không có Claude Code. Họ đăng ký trên trang web, giao việc làm phim hoặc học phong cách, duyệt và nhận kết quả ngay trên web. Xưởng tự chạy Claude cho từng việc.

Người dùng đã chốt (2026-11-07), kể cả các câu trả lời làm rõ ở FR-014, FR-015, FR-030:
- **Đủ tính năng như bản trên máy**: làm phim theo phong cách thư viện hoặc phong cách khách đã học; học phong cách từ kênh YouTube khách nêu hoặc từ video khách tải lên; hai lần duyệt khi học phong cách.
- **Mở đăng ký cho mọi người**, có hạn mức chỉnh được trong cài đặt.
- **Chưa thu tiền**. Thanh toán là spec sau.
- **Chia nhiều spec**. Đây là bản đầu. Thanh toán, nhóm hay doanh nghiệp, ứng dụng di động là các spec sau.
- **Tải từ YouTube theo hiến pháp 2.1.0**: khách xác nhận quyền, video giữ kín, xoá sau khi học.

Mức quy trình: **Đầy đủ**.

## Clarifications

### Session 2026-11-07

- Q: Một lúc chạy được bao nhiêu việc? → A: Mỗi khách 1 việc chạy một lúc; cả xưởng tối đa N việc (cài đặt, mặc định 2); việc khác xếp hàng, khách thấy vị trí.
- Q: Câu hỏi lại, tóm tắt duyệt và chữ trong phim bằng ngôn ngữ nào? → A: Luôn tiếng Anh.
- Q: Khi xoá tài khoản, bản ghi xác nhận quyền YouTube có bị xoá không? → A: Xoá cùng tài khoản như dữ liệu khác.
- Q: Hạn mức tháng làm mới lúc nào? → A: Ngày 1 mỗi tháng, giờ Việt Nam (UTC+7), cho mọi khách.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Đăng ký và làm một bộ phim theo phong cách thư viện (Priority: P1)

Một người lạ vào trang, đăng ký bằng email và xác minh email. Họ chọn một phong cách trong thư viện, mô tả ý tưởng phim và độ dài, rồi giao việc. Họ theo dõi tiến độ trên trang. Khi xong, họ xem phim có tiếng và phụ đề, rồi tải phim về. Lượt dùng bị trừ vào hạn mức.

**Why this priority**: Đây là giá trị cốt lõi của dịch vụ và là luồng đơn giản nhất từ đầu đến cuối. Nó cần đủ các khối nền: tài khoản, hạn mức, chạy việc trên máy chủ, theo dõi, phát phim.

**Independent Test**: Với một email mới: đăng ký → xác minh → giao một phim 20 giây (không chọn duyệt kịch bản) theo một phong cách thư viện → nhận phim xem được và tải được; hạn mức còn lại giảm đúng 1.

**Acceptance Scenarios**:

1. **Given** một email chưa đăng ký, **When** đăng ký và mở liên kết xác minh, **Then** tài khoản dùng được và có hạn mức mặc định theo cài đặt.
2. **Given** tài khoản chưa xác minh email, **When** giao việc, **Then** bị từ chối, kèm lời nhắc xác minh.
3. **Given** tài khoản còn hạn mức, **When** giao việc làm phim (phong cách, ý tưởng, độ dài trong giới hạn), **Then** việc được nhận, hiện trong danh sách việc của khách, và tiến độ tự cập nhật.
4. **Given** việc làm phim xong, **When** mở trang việc, **Then** khách xem được phim có tiếng, poster, phụ đề bật tắt được, và tải được tệp phim.
5. **Given** tài khoản đã hết hạn mức tháng, **When** giao việc mới, **Then** bị từ chối, kèm số lượt còn lại (0) và ngày hạn mức được làm mới.
6. **Given** hai khách khác nhau, **When** mỗi người mở danh sách việc, phim hay phong cách, **Then** chỉ thấy của mình.
7. **Given** việc lỗi do xưởng (không do khách), **When** việc kết thúc ở trạng thái lỗi, **Then** lượt dùng được trả lại.

---

### User Story 2 - Học phong cách từ kênh YouTube hoặc video của khách, duyệt trên web (Priority: P2)

Khách giao việc học phong cách theo một trong hai cách: nêu một kênh YouTube và số video, hoặc tải lên video của chính họ. Nếu dùng kênh YouTube, trước khi tải, khách xác nhận có quyền dùng video hoặc chỉ dùng để nghiên cứu phong cách. Xưởng đo, viết bản phong cách, rồi mời khách duyệt lần 1 (bản phong cách) và lần 2 (khung chứng minh so với khung gốc). Khách duyệt bằng nút trên web. Khi đạt, phong cách vào mục "My styles" của khách, video gốc bị xoá, và khách dùng phong cách đó làm phim như ở US1.

**Why this priority**: Đây là điểm khác biệt của xưởng, nhưng dựa trên các khối của US1.

**Independent Test**: Giao một việc học từ 3 video tải lên → duyệt lần 1 Approve → duyệt lần 2 Approve → phong cách xuất hiện trong "My styles" → video gốc không còn trên máy chủ → làm được một phim theo phong cách đó.

**Acceptance Scenarios**:

1. **Given** khách nêu một kênh YouTube, **When** giao việc mà chưa đánh dấu xác nhận quyền, **Then** bị từ chối.
2. **Given** việc học tới lần duyệt 1 hoặc 2, **When** khách mở trang duyệt, **Then** thấy đủ nội dung như giai đoạn 1 (bản tóm tắt; với lần 2 là khung của mình đặt cạnh khung gốc kèm số so sánh) và đưa được một quyết định: Approve · Request changes (bắt buộc ghi góp ý) · ở vòng cuối thêm Accept anyway · Stop.
3. **Given** khách chọn Request changes kèm góp ý, **When** xưởng sửa xong, **Then** có yêu cầu duyệt mới. Số vòng sửa giới hạn như giai đoạn 1.
4. **Given** việc học kết thúc (đạt, dừng hoặc lỗi), **When** kiểm tra máy chủ, **Then** không còn video hay âm thanh gốc. Chỉ còn số đo và khung hình bằng chứng (hiến pháp 2.1.0).
5. **Given** bất kỳ lúc nào, **When** khách hoặc người khác tìm cách xem hay tải video gốc qua trang hoặc API, **Then** không có cách nào làm được.
6. **Given** phong cách đã lưu, **When** khách giao việc làm phim, **Then** chọn được phong cách đó cạnh các phong cách thư viện.

---

### User Story 3 - Chủ xưởng đặt hạn mức và giữ chi phí trong tầm kiểm soát (Priority: P3)

Chủ xưởng mở trang quản trị và đặt các cài đặt:
- hạn mức mặc định mỗi tháng (số phim, số lần học phong cách);
- giới hạn độ dài phim và số video mỗi lần học;
- trần chi phí tổng mỗi ngày của cả xưởng;
- hạn mức riêng cho từng khách;
- bật hoặc tắt đăng ký mới.

Chủ xưởng xem được mức dùng và chi phí ước tính theo ngày và theo khách. Họ khoá được một tài khoản lạm dụng.

**Why this priority**: Mở đăng ký cho mọi người mà chưa thu tiền thì phải có cách chặn chi phí. US1 chạy được với cài đặt mặc định, nên phần này xếp P3.

**Independent Test**: Đặt hạn mức mặc định 1 phim/tháng → khách mới làm được 1 phim, phim thứ 2 bị từ chối → nâng riêng khách đó lên 3 → khách làm tiếp được. Đặt trần chi phí ngày thấp → khi chạm trần, việc mới của mọi khách bị từ chối kèm thông báo "thử lại ngày mai".

**Acceptance Scenarios**:

1. **Given** chủ xưởng đổi hạn mức mặc định, **When** lưu, **Then** áp dụng ngay cho mọi khách không có hạn mức riêng.
2. **Given** tổng chi phí trong ngày chạm trần, **When** bất kỳ khách nào giao việc mới, **Then** bị từ chối. Việc đang chạy vẫn chạy xong.
3. **Given** chủ xưởng tắt đăng ký mới, **When** người lạ đăng ký, **Then** bị từ chối. Khách cũ vẫn đăng nhập được.
4. **Given** một tài khoản bị khoá, **When** chủ tài khoản đăng nhập hoặc gọi API, **Then** bị từ chối. Việc đang chạy của họ bị dừng.
5. **Given** trang quản trị, **When** người không phải chủ xưởng mở, **Then** không truy cập được.

---

### User Story 4 - Khách quản lý tài khoản và dữ liệu của mình (Priority: P4)

Khách đổi mật khẩu hoặc lấy lại mật khẩu qua email, xem hạn mức còn lại, xoá từng phim hay phong cách, và xoá hẳn tài khoản cùng toàn bộ dữ liệu.

**Why this priority**: Cần trước khi mở rộng, nhưng không chặn luồng chính.

**Independent Test**: Xoá tài khoản → đăng nhập lại bị từ chối → không còn phim, phong cách hay việc nào của tài khoản đó trên máy chủ.

**Acceptance Scenarios**:

1. **Given** khách quên mật khẩu, **When** yêu cầu đặt lại, **Then** nhận liên kết qua email, liên kết dùng được một lần và hết hạn sau thời gian giới hạn.
2. **Given** khách xoá tài khoản, **When** xác nhận, **Then** mọi dữ liệu của khách bị xoá trong thời hạn công bố.

### Edge Cases

- Kênh YouTube không tồn tại, video riêng tư, hoặc máy chủ bị YouTube chặn tải: việc kết thúc lỗi với lý do rõ ràng, lượt được trả lại, và gợi ý tải video lên thay thế.
- Video khách tải lên quá lớn, sai định dạng hoặc quá dài: bị từ chối ngay khi tải lên, trước khi trừ lượt.
- Khách đóng trình duyệt giữa chừng: việc vẫn chạy, và mở lại thì thấy đúng tiến độ.
- Khách không duyệt trong thời gian dài: việc chờ duyệt không tốn chi phí. Sau một thời hạn thì tự dừng và báo cho khách.
- Ý tưởng phim vi phạm nội dung (bạo lực, tình dục, thù ghét, mạo danh người thật hay thương hiệu): bị từ chối kèm lý do, không trừ lượt.
- Ý tưởng nhắc tên kênh tham chiếu: phim không được nêu tên kênh (hiến pháp).
- Hai yêu cầu cùng lúc làm vượt hạn mức: chỉ một yêu cầu được nhận.
- Máy chủ khởi động lại khi việc đang chạy: việc tiếp tục hoặc kết thúc lỗi và trả lượt, không treo mãi.
- Dịch vụ dùng Claude bị lỗi hoặc quá tải: việc chờ rồi thử lại. Quá thời hạn thì lỗi và trả lượt.

## Requirements *(mandatory)*

### Functional Requirements

**Tài khoản**
- **FR-001**: Người lạ MUST tự đăng ký được bằng email và mật khẩu khi đăng ký đang bật. Tài khoản MUST xác minh email trước khi giao việc.
- **FR-002**: Khách MUST đăng nhập, đăng xuất, đổi mật khẩu và lấy lại mật khẩu qua email được.
- **FR-003**: Mọi việc, phim, phong cách, bộ tham chiếu và yêu cầu duyệt MUST thuộc đúng một khách. Khách chỉ thấy và thao tác trên dữ liệu của mình (dùng trường `owner` đã có từ 003 FR-016).
- **FR-004**: Có đúng một vai trò quản trị (chủ xưởng). Trang và API quản trị MUST chỉ mở cho vai trò này.

**Hạn mức và chi phí**
- **FR-005**: Mỗi khách MUST có hạn mức theo tháng (làm mới ngày 1 mỗi tháng, 00:00 giờ Việt Nam) gồm số phim và số lần học phong cách. Giá trị mặc định lấy từ cài đặt; chủ xưởng đặt được hạn mức riêng cho từng khách.
- **FR-006**: Xưởng MUST kiểm hạn mức lúc nhận việc, trừ một lượt khi nhận, và trả lại lượt khi việc lỗi do xưởng hoặc bị từ chối trước khi chạy. Việc khách tự dừng không được trả lượt.
- **FR-007**: Cài đặt MUST có: giới hạn độ dài phim tối đa, số video tối đa mỗi lần học, dung lượng và độ dài tối đa của video tải lên, trần chi phí tổng mỗi ngày, bật hoặc tắt đăng ký.
- **FR-008a**: Mỗi khách MUST có tối đa 1 việc đang chạy; cả xưởng MUST chạy tối đa N việc cùng lúc (cài đặt, mặc định 2). Việc vượt mức MUST xếp hàng theo thứ tự nhận, khách thấy vị trí trong hàng; việc xếp hàng không tốn chi phí.
- **FR-008**: Xưởng MUST ước tính và ghi chi phí của từng việc. Khi tổng chi phí trong ngày chạm trần, MUST từ chối mọi việc mới cho tới ngày hôm sau.
- **FR-009**: Chủ xưởng MUST xem được mức dùng và chi phí theo ngày và theo khách, và khoá hoặc mở khoá được tài khoản.

**Làm phim**
- **FR-010**: Khách MUST giao được việc làm phim gồm: phong cách (thư viện hoặc phong cách của mình), mô tả ý tưởng, độ dài trong giới hạn.
- **FR-011**: Xưởng MUST tự chạy việc làm phim theo đúng quy trình của thư viện và kiểm tra chất lượng như giai đoạn 1 (âm lượng, đỉnh âm, kiểm tra đọc chữ), không cần chủ xưởng can thiệp.
- **FR-012**: Khách MUST xem được tiến độ (bước, nhật ký) tự cập nhật, xem được phim có tiếng, poster, phụ đề, và tải được tệp phim.
- **FR-013**: Xưởng MUST từ chối ý tưởng vi phạm chính sách nội dung trước khi trừ lượt, kèm lý do.
- **FR-014**: Khách điền mẫu một lần. Nếu ý tưởng chưa rõ, Claude MUST hỏi lại tối đa 3 câu, khách trả lời trên web, và việc chờ không tốn chi phí. Khách MUST được chọn duyệt kịch bản (treatment) trước khi dựng: Approve hoặc Request changes kèm góp ý. Không có khung chat tự do.
- **FR-015**: Khách MUST yêu cầu sửa được một phim đã xong, kèm góp ý. Mỗi lần sửa tốn 1 lượt phim, và phim sửa là một bản mới, giữ bản cũ. Sửa kịch bản trước khi dựng (FR-014) không tốn lượt.

**Học phong cách**
- **FR-016**: Khách MUST giao được việc học phong cách theo một trong hai nguồn: kênh YouTube kèm số video trong giới hạn, hoặc các video tự tải lên.
- **FR-017**: Với nguồn YouTube, khách MUST đánh dấu xác nhận quyền trước khi giao việc. Xưởng MUST lưu lần xác nhận (ai, lúc nào, kênh nào).
- **FR-018**: Video và âm thanh gốc MUST NOT được hiện, phát hay tải về qua bất kỳ đường nào, kể cả cho chính khách. Chỉ khung hình bằng chứng và ảnh ghép đo được hiện ra.
- **FR-019**: Video và âm thanh gốc MUST bị xoá khi việc học kết thúc (đạt, dừng hoặc lỗi), chậm nhất sau 1 giờ.
- **FR-020**: Hai lần duyệt (bản phong cách, khung chứng minh) MUST giữ nội dung, các quyết định và giới hạn vòng sửa như giai đoạn 1. Khách duyệt bằng nút trên web, và việc đi tiếp mà không cần ai khác.
- **FR-021**: Việc chờ duyệt MUST NOT tốn chi phí khi chờ, và MUST tự dừng sau 7 ngày không có quyết định, kèm email báo cho khách.
- **FR-022**: Phong cách học xong MUST vào "My styles" của khách theo khung 11 mục, và dùng được ngay khi làm phim.

**Thông báo**
- **FR-023**: Xưởng MUST gửi email cho khách khi việc xong, lỗi, hoặc cần duyệt. Khách tắt được email này.

**An toàn và dữ liệu**
- **FR-024**: Mọi kết nối MUST được mã hoá. Mật khẩu MUST NOT được lưu ở dạng đọc được.
- **FR-025**: Đăng ký, đăng nhập và giao việc MUST có giới hạn tần suất để chống lạm dụng.
- **FR-026**: Khách xoá được từng phim hay phong cách, và xoá được tài khoản. Xoá tài khoản MUST xoá mọi dữ liệu của khách trong vòng 30 ngày, kể cả bản ghi xác nhận quyền (FR-017).
- **FR-027**: Mỗi việc MUST chạy tách biệt với việc khác: việc của khách này không đọc hay ghi được dữ liệu của khách khác.
- **FR-028**: API v1 của giai đoạn 1 MUST được dùng lại, thêm phần xác thực. Hình dạng dữ liệu hiện có (việc, yêu cầu duyệt, quyết định) MUST giữ nguyên.

**Giao diện**
- **FR-029**: Giao diện MUST là tiếng Anh như giai đoạn 1 và dùng được trên điện thoại. Câu hỏi lại của Claude, tóm tắt duyệt, email và chữ, lời trong phim MUST bằng tiếng Anh (khách viết ý tưởng bằng ngôn ngữ khác vẫn được nhận).
- **FR-030**: Phim MUST được giữ trên máy chủ đến khi khách xoá phim hoặc xoá tài khoản. Chủ xưởng MUST xem được tổng dung lượng phim, tổng chung và theo khách.

### Key Entities

- **Khách (Account)**: email, trạng thái xác minh, vai trò (khách hoặc quản trị), trạng thái khoá, hạn mức riêng (nếu có), cài đặt email.
- **Hạn mức (Quota)**: theo khách và theo tháng: lượt phim, lượt học đã dùng và còn lại, ngày làm mới.
- **Cài đặt (Settings)**: hạn mức mặc định, số việc chạy cùng lúc của cả xưởng (N), các giới hạn ở FR-007, trần chi phí ngày, bật hoặc tắt đăng ký.
- **Việc (Job)**: như 003, thêm chủ sở hữu thật và chi phí ước tính.
- **Xác nhận quyền (Rights confirmation)**: khách, kênh, lúc xác nhận, việc liên quan.
- **Mức dùng (Usage)**: chi phí và số việc theo ngày, theo khách.
- Phim, Bộ tham chiếu, Phong cách, Yêu cầu duyệt, Quyết định: như 003, thêm chủ sở hữu.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Một khách mới đi từ mở trang tới giao việc làm phim đầu tiên trong dưới 3 phút (không tính thời gian chờ email).
- **SC-002**: 100% phim làm xong đạt kiểm tra chất lượng như giai đoạn 1 (âm lượng −14 ±1 LUFS, đỉnh ≤ −1 dB, kiểm tra đọc chữ đạt).
- **SC-003**: 0 trường hợp một khách thấy hoặc tải được dữ liệu của khách khác (kiểm bằng test tự động trên mọi đường API).
- **SC-004**: 0 đường nào phát hay tải được video gốc. 100% video gốc bị xoá trong vòng 1 giờ sau khi việc học kết thúc (kiểm tự động).
- **SC-005**: Tổng chi phí mỗi ngày không vượt trần cài đặt quá chi phí của các việc đã đang chạy lúc chạm trần.
- **SC-006**: Không tính bước chờ khách, 90% việc làm phim 30 giây xong trong 20 phút.
- **SC-007**: Tiến độ trên trang cập nhật trong vòng 5 giây sau khi bước đổi.
- **SC-008**: Hạn mức đúng 100% khi có 10 yêu cầu giao việc cùng lúc từ một khách (không vượt, không trừ thừa).
- **SC-009**: Không bao giờ có quá N việc chạy cùng lúc, hay quá 1 việc chạy của cùng một khách (kiểm tự động khi giao 20 việc cùng lúc).

## Assumptions

- Chủ xưởng có một khoá API Claude và trả chi phí. Chi phí ước tính lấy từ số token mỗi việc theo bảng giá công bố.
- Hạn mức mặc định ban đầu (chỉnh được): 2 phim và 1 lần học mỗi tháng; phim tối đa 60 giây; tối đa 5 video mỗi lần học.
- Một máy chủ là đủ cho bản dùng thử. Việc chờ nhau khi đông, không cần nhiều máy.
- Bản dùng thử không cam kết thời gian hoạt động (không có SLA); bảo trì được báo trước trên trang.
- Thư viện phong cách (lemo-opuscar) chạy trên máy chủ như trên máy chủ xưởng, không sửa (hiến pháp VI).
- Chính sách nội dung và điều khoản sử dụng cho khách do chủ xưởng viết. Spec này chỉ yêu cầu có trang và có bước khách đồng ý khi đăng ký.
- Chủ xưởng tự hỏi luật sư trước khi mở công khai (hiến pháp 2.1.0).
- Ngoài phạm vi: thanh toán; nhóm hay nhiều người chung tài khoản; đăng nhập bằng Google hay mạng xã hội; ứng dụng di động; nhiều ngôn ngữ giao diện; nhiều máy chủ.
