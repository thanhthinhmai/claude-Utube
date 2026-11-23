# Feature Specification: Sửa ghi chú phim After Effects tự động trên app

**Feature Branch**: `031-ae-notes-fix`

**Created**: 2026-11-23

**Status**: Draft

**Input**: User description: "Sửa ghi chú phim After Effects tự động ngay trên app: (1) đưa bộ dựng AE đang nằm trong phim tập luyện films/ae-crayon-test/ae thành công cụ dùng chung của xưởng, mỗi phim AE chỉ giữ phần shot riêng; lệnh dựng, render, sửa từng shot; cấu hình đường dẫn AE và thư mục làm việc thay cho đường dẫn viết cứng; (2) cầu nối AE trong app desktop: app desktop chạy trên Windows (hoặc macOS) nhận yêu cầu dựng từ phần lõi rồi gọi After Effects và aerender trên máy, báo tiến độ và kết quả; mỗi lúc chỉ một lượt dùng AE; báo rõ khi máy không có AE; (3) nút "Fix with Claude" trên trang phim tạo một việc sửa ghi chú: Claude của app đọc ghi chú mở, sửa code của đúng các shot đó, dựng lại chỉ các shot đó qua cầu nối, thay video (giữ một bản trước), trả lời và tick từng ghi chú; khoá sổ ghi chú trong lúc sửa, giới hạn số ghi chú mỗi lượt, ghi lại token đã dùng; (4) build bộ cài app desktop qua GitHub Actions có phần cầu nối AE. Phụ thuộc spec 029."

## Clarifications

### Session 2026-11-23

- Q: Bản đầu có tạo phim AE mới từ đầu trên app không, hay chỉ sửa phim AE đã có? → A: Có cả tạo phim AE mới từ đầu trên app (từ ý tưởng tới video), ngoài phần sửa phim đã có.
- Q: Video mới thay luôn hay chờ duyệt? → A: Thay luôn sau khi dựng xong; bản cũ giữ lại để so ("Watch the previous version").
- Q: Bản đầu có chạy với After Effects thật trên macOS không? → A: Có: cả Windows và macOS đều phải thử với AE thật trước khi xong.
- Q: Có giới hạn chi phí Claude cho mỗi việc không? → A: Không giới hạn riêng; chỉ ghi lại số token và dùng hạn mức chung hiện có của app (specs/007–008).

## Bối cảnh

- Người dùng đổi hướng làm phim sang After Effects vì hình dựng bằng trang web của xưởng chưa đạt. Hiến pháp 3.0.0 (nguyên tắc VII) đã nhận AE làm bộ máy dựng hình thứ hai; AE là phần mềm có bản quyền của người dùng.
- Phim tập luyện `ae-crayon-test` (40 shot) dựng bằng bộ code AE tự viết nằm trong chính thư mục phim: thư viện hình, nhân vật có khớp, luật dàn cảnh, bộ chiều sâu, các tệp shot, lệnh chạy AE và lệnh dựng lại từng shot rồi ghép vào video. Bộ này chỉ chạy được trên máy hiện tại (đường dẫn viết cứng tới ổ E, tên người dùng Windows) và chưa dùng lại được cho phim AE khác.
- Spec 029 đã có ghi chú từng shot trên trang phim và lệnh cho Claude đọc, trả lời ghi chú, thay video. Hiện người dùng phải chép câu "Sửa theo ghi chú phim <tên>" dán vào chat; Claude trong chat chạy AE qua dòng lệnh.
- Phần lõi của app chạy trong một bản Linux riêng (Windows) hoặc trực tiếp (macOS); After Effects chạy trên hệ điều hành của máy. App desktop (specs/015–018) là phần chạy thẳng trên máy, cạnh AE.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bộ dựng AE dùng chung và lệnh cho từng phim AE (Priority: P1)

Người làm phim (Claude hoặc người dùng) có một bộ dựng AE dùng chung của xưởng. Mỗi phim AE chỉ chứa phần riêng của nó (các shot, danh sách shot, cấu hình phim) và khai báo mình dùng bộ máy After Effects. Có lệnh dựng cả phim, render, và dựng lại chỉ một vài shot rồi ghép vào video hiện có. Đường dẫn tới After Effects và thư mục làm việc nằm trong cấu hình của máy, không viết cứng.

**Why this priority**: Không có bộ dựng dùng chung và cấu hình máy thì không phần nào khác (cầu nối, sửa tự động, máy khác) chạy được. Riêng phần này đã giúp làm phim AE thứ hai không phải chép lại cả bộ code.

**Independent Test**: Chuyển `ae-crayon-test` sang dạng mới (chỉ giữ phần shot), chạy lệnh dựng lại shot 13 rồi ghép: video ra trùng từng khung với bản dựng bằng bộ code cũ (0 khung lệch quá ngưỡng), dài đúng 137,6 s, 4128 khung.

**Acceptance Scenarios**:

1. **Given** phim AE ở dạng mới, **When** chạy lệnh dựng lại một số shot, **Then** chỉ các shot đó được dựng và render, rồi được ghép đúng khoảng thời gian của chúng vào video hiện có; tiếng và các shot khác giữ nguyên; độ dài lệch ≤ 1 khung.
2. **Given** máy chưa cấu hình After Effects, **When** chạy bất kỳ lệnh AE nào, **Then** lệnh dừng ngay với thông báo nói rõ thiếu gì và cách cấu hình, không ghi gì vào phim.
3. **Given** cấu hình máy có đường dẫn AE và thư mục làm việc, **When** chạy lệnh trên một máy khác cùng cấu hình, **Then** lệnh chạy được mà không phải sửa tệp nào của phim hay của bộ dựng.
4. **Given** một thay đổi trong phần dùng chung (ví dụ hàm vẽ tóc), **When** hỏi xưởng shot nào dùng phần đó, **Then** xưởng liệt kê được các shot bị ảnh hưởng để chỉ dựng lại chúng.
5. **Given** phim dùng bộ máy trang web, **When** chạy lệnh AE cho phim đó, **Then** xưởng từ chối và nói phim dùng bộ máy nào (mỗi phim một bộ máy).

---

### User Story 2 - Cầu nối After Effects trong app desktop (Priority: P1)

App desktop đang chạy trên máy của người dùng nhận yêu cầu dựng từ phần lõi (dựng lại các shot nào của phim nào), gọi After Effects trên máy, báo tiến độ (đang dựng shot nào, bao lâu) và trả kết quả (tệp video của shot, hoặc lỗi kèm nhật ký). Mỗi lúc chỉ một lượt dựng AE; yêu cầu sau chờ tới lượt. Máy không có AE, AE không mở được, hoặc bản quyền AE không còn dùng được thì cầu nối báo rõ lý do.

**Why this priority**: Phần lõi chạy trong môi trường không gọi thẳng được AE. Cầu nối là đường duy nhất để app tự dựng phim AE, kể cả trên máy cài bằng bộ cài.

**Independent Test**: Với app desktop đang chạy và AE trên máy, gửi từ phần lõi yêu cầu dựng shot 13 của `ae-crayon-test`: nhận tiến độ và tệp video của shot trong ≤ 2 phút; gửi hai yêu cầu cùng lúc: yêu cầu thứ hai chờ, chạy sau khi yêu cầu đầu xong.

**Acceptance Scenarios**:

1. **Given** app desktop đang chạy trên máy có AE, **When** phần lõi gửi yêu cầu dựng một danh sách shot, **Then** cầu nối dựng và render từng shot, báo tiến độ ít nhất sau mỗi shot, và trả tệp video của từng shot.
2. **Given** một yêu cầu đang dùng AE, **When** yêu cầu thứ hai tới, **Then** yêu cầu thứ hai được xếp hàng và báo "đang chờ AE", không chạy song song.
3. **Given** máy không có AE (hoặc đường dẫn sai), **When** có yêu cầu dựng, **Then** cầu nối trả lỗi "không tìm thấy After Effects" kèm đường dẫn đã thử, trong ≤ 10 giây.
4. **Given** AE treo hoặc render quá thời hạn, **When** hết thời hạn đặt cho mỗi shot, **Then** cầu nối dừng tiến trình AE của lượt dựng AE đó, báo lỗi kèm nhật ký, và nhận yêu cầu tiếp theo.
5. **Given** app desktop không chạy, **When** phần lõi cần dựng AE, **Then** phần lõi báo "mở app desktop để dựng phim After Effects" thay vì chờ mãi.
6. **Given** yêu cầu đến từ nơi không phải phần lõi của chính máy này, **When** cầu nối nhận được, **Then** cầu nối từ chối (chỉ phần lõi của máy được gọi AE).

---

### User Story 3 - Nút "Fix with Claude" sửa ghi chú tự động (Priority: P2)

Trên trang phim AE, người dùng bấm "Fix with Claude". App tạo một việc sửa ghi chú. Claude của app đọc các ghi chú mở (kể cả ảnh đính kèm), liệt kê lại trong nhật ký việc, sửa code của đúng các shot đó, dựng lại chỉ các shot đó qua cầu nối, thay video của phim (giữ một bản trước), rồi trả lời và tick từng ghi chú (ghi chú chưa sửa được để mở kèm lý do). Trang phim tự cập nhật khi xong. Trong lúc sửa, sổ ghi chú bị khoá với việc đó: ghi chú mới thêm vào chờ lượt sau.

**Why this priority**: Đây là mục tiêu của người dùng (không phải chép lệnh sang chat), nhưng cần User Story 1 và 2 trước.

**Independent Test**: Phim `ae-crayon-test` có 2 ghi chú mở ở 2 shot. Bấm "Fix with Claude": trang việc hiện từng bước; khi xong, video trên trang phim là bản mới, 2 ghi chú có trả lời (tick nếu sửa được), "Watch the previous version" phát bản cũ, chi phí token của việc hiện trên trang việc.

**Acceptance Scenarios**:

1. **Given** phim AE có ghi chú mở, **When** bấm "Fix with Claude", **Then** một việc sửa ghi chú được tạo, trang phim hiện đường dẫn tới việc và trạng thái "Fixing…".
2. **Given** việc sửa đang chạy, **When** người dùng thêm hoặc sửa ghi chú, **Then** thay đổi được lưu nhưng không vào lượt đang chạy; trang báo ghi chú đó sẽ vào lượt sau. Bấm "Fix with Claude" lần nữa khi việc chưa xong thì không tạo việc thứ hai.
3. **Given** việc sửa xong, **When** mở trang phim, **Then** video đã thay, mỗi ghi chú của lượt có trả lời; ghi chú sửa được thì tick, ghi chú không sửa được thì còn mở kèm lý do; không ghi chú nào bị bỏ qua không lời.
4. **Given** số ghi chú mở vượt giới hạn mỗi lượt, **When** bấm "Fix with Claude", **Then** chỉ ghi chú trong giới hạn (theo thứ tự thời gian trong phim) vào lượt này; trang nói rõ số còn lại.
5. **Given** việc sửa gặp lỗi không tự sửa được (AE lỗi, dựng hỏng), **When** việc dừng, **Then** video cũ giữ nguyên, ghi chú còn mở, việc báo lỗi kèm bước hỏng và nhật ký.
6. **Given** phim không phải phim AE hoặc không có ghi chú mở, **When** xem trang phim, **Then** nút không bấm được và có dòng giải thích.

---

### User Story 4 - Bộ cài app desktop có cầu nối AE (Priority: P3)

Bộ cài app desktop build qua GitHub Actions có sẵn cầu nối AE. Cài vào máy Windows có AE, mở app, vào phần cài đặt chỉ đường dẫn AE (hoặc app tự tìm ở chỗ cài mặc định), là dùng được "Fix with Claude" cho phim AE.

**Why this priority**: Cần cho máy khác và bản phát hành, nhưng máy hiện tại dùng được ngay từ mã nguồn.

**Independent Test**: Chạy luồng build của GitHub Actions cho nhánh: luồng thử (smoke) trên Windows qua, trong đó có bài thử cầu nối AE với AE giả; bộ cài tạo ra có phần cài đặt đường dẫn AE.

**Acceptance Scenarios**:

1. **Given** đẩy nhánh có thay đổi app desktop, **When** luồng build thử chạy, **Then** bài thử cầu nối (với AE giả) qua trên Windows và macOS.
2. **Given** bộ cài mới, **When** cài trên máy có AE ở chỗ cài mặc định, **Then** app tự tìm thấy AE; không có thì app hỏi đường dẫn, kiểm và lưu lại.
3. **Given** bộ cài mới trên máy không có AE, **When** mở app, **Then** mọi phần khác chạy như cũ; chỉ phim AE báo cần After Effects.

---

### User Story 5 - Tạo phim After Effects mới từ đầu trên app (Priority: P3)

Người dùng tạo phim mới trên app, chọn bộ máy After Effects, nhập ý tưởng (và độ dài, kênh, phong cách nếu có). Việc làm phim của app chạy từ đầu tới cuối: kịch bản được chấm như các phim khác của xưởng, giọng đọc, bảng shot, viết code từng shot bằng bộ dựng AE dùng chung, dựng và render qua cầu nối, trộn tiếng, kiểm theo tầng, rồi giao phim kèm mốc shot để người dùng ghi chú và bấm "Fix with Claude" như User Story 3. Các điểm duyệt của xưởng (kịch bản, bảng shot…) vẫn áp dụng.

**Why this priority**: Người dùng muốn làm phim AE mới mà không cần chat; cần User Story 1–3 chạy trước vì cùng dùng bộ dựng, cầu nối và vòng sửa.

**Independent Test**: Tạo phim AE mới "thu-ae-1" dài khoảng 30 giây từ một ý tưởng trên app: việc chạy qua các bước, dừng ở các điểm duyệt đang bật; khi xong, trang phim có video, mốc shot khớp video (lệch ≤ 1 khung), và phim chỉ chứa phần shot riêng (không chép bộ dựng chung).

**Acceptance Scenarios**:

1. **Given** app có cầu nối AE, **When** tạo phim mới chọn bộ máy After Effects và nhập ý tưởng, **Then** một việc làm phim AE được tạo; phim mới khai báo bộ máy After Effects.
2. **Given** việc làm phim AE đang chạy, **When** tới bước kịch bản và giọng, **Then** dùng đúng các bước chấm kịch bản, giọng đọc và kiểm tầng 0 của xưởng (không có đường tắt riêng cho AE).
3. **Given** kịch bản và giọng đã đạt, **When** tới bước hình, **Then** Claude viết code từng shot theo bảng shot bằng bộ dựng chung, dựng qua cầu nối, và mỗi shot qua luật dàn cảnh trước khi ghép bản tổng.
4. **Given** điểm duyệt Shots đang bật, **When** bảng shot xong, **Then** việc dừng chờ người dùng duyệt trên trang việc như phim web.
5. **Given** phim AE mới xong, **When** mở trang phim, **Then** có video, mốc shot và phần Shots của spec 029; ghi chú và "Fix with Claude" dùng được ngay.
6. **Given** máy không có AE hoặc cầu nối không chạy, **When** chọn bộ máy After Effects lúc tạo phim, **Then** app báo trước và không tạo việc.

---

### Edge Cases

- Code shot bị sửa hỏng làm AE báo lỗi khi dựng: việc thử lại tối đa 1 lần sau khi Claude sửa lỗi; vẫn hỏng thì dừng, giữ video cũ, để ghi chú mở kèm lỗi.
- Ghi chú chỉ ra lỗi ở phần dùng chung (ví dụ hàm vẽ tóc) ảnh hưởng nhiều shot: việc dựng lại mọi shot dùng phần đó (không chỉ shot có ghi chú) và nói rõ đã dựng những shot nào.
- Hai việc của hai phim AE khác nhau cùng lúc: cả hai được tạo, nhưng dựng AE xếp hàng qua cầu nối.
- Người dùng đóng app desktop giữa lúc dựng: việc báo lỗi "cầu nối mất kết nối", video cũ giữ nguyên; mở lại app thì bấm sửa lại được.
- AE mở một hộp thoại chờ người bấm (sau khi bị tắt đột ngột, hoặc bản quyền hết hạn): cầu nối nhận ra việc không tiến triển trong thời hạn, dừng và báo "AE đang chờ thao tác trên máy".
- Đường dẫn chứa ký tự tiếng Việt hoặc khoảng trắng: dựng vẫn chạy.
- Thư mục làm việc của AE đầy ổ đĩa: báo lỗi đĩa rõ ràng trước khi dựng nếu còn dưới mức tối thiểu.
- Chế độ Client (specs/018): máy Client không có cầu nối; chỉ Host dựng được AE; nút trên Client gửi việc cho Host như các việc khác.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Xưởng PHẢI có bộ dựng AE dùng chung (thư viện hình, nhân vật, luật dàn cảnh, chiều sâu, máy quay, ghép bản tổng) nằm ngoài thư mục phim; mỗi phim AE chỉ chứa phần shot, danh sách shot và cấu hình phim.
- **FR-002**: Mỗi phim PHẢI khai báo bộ máy dựng của nó (trang web hoặc After Effects); lệnh của bộ máy này PHẢI từ chối phim của bộ máy kia (hiến pháp VII).
- **FR-003**: Xưởng PHẢI có lệnh dựng cả phim AE, render bản tổng, và dựng lại một danh sách shot rồi ghép vào video hiện có chính xác theo khung (độ dài lệch ≤ 1 khung, tiếng giữ nguyên), cùng định dạng mốc shot của spec 029.
- **FR-004**: Đường dẫn tới After Effects, tới trình render và thư mục làm việc của máy PHẢI nằm trong cấu hình của máy, đặt bằng lệnh hoặc trong app desktop; không tệp nào của phim hay bộ dựng chứa đường dẫn riêng của một máy.
- **FR-005**: Xưởng PHẢI liệt kê được các shot dùng một phần của bộ dựng dùng chung, để chỉ dựng lại các shot bị ảnh hưởng.
- **FR-006**: App desktop PHẢI có cầu nối AE nhận yêu cầu dựng (phim, danh sách shot) chỉ từ phần lõi của chính máy đó, chạy After Effects và trình render của máy, báo tiến độ ít nhất sau mỗi shot, trả tệp video từng shot hoặc lỗi kèm nhật ký.
- **FR-007**: Cầu nối PHẢI chạy tối đa một lượt dựng AE mỗi lúc, xếp hàng các yêu cầu khác, và có thời hạn cho mỗi shot (dừng tiến trình AE khi quá hạn, báo lỗi).
- **FR-008**: Cầu nối PHẢI báo rõ khi không tìm thấy AE, AE không khởi động được, hoặc AE không tiến triển (ví dụ chờ hộp thoại), trong thời gian quy định.
- **FR-009**: Phần lõi PHẢI báo "mở app desktop để dựng phim After Effects" khi cầu nối không chạy, thay vì chờ không giới hạn.
- **FR-010**: Trang phim AE PHẢI có nút "Fix with Claude" tạo một việc sửa ghi chú (không tạo trùng khi một việc của phim đó đang chạy); nút tắt kèm lời giải thích khi phim không phải AE hoặc không có ghi chú mở.
- **FR-011**: Việc sửa ghi chú PHẢI: lấy các ghi chú mở trong giới hạn mỗi lượt; ghi vào nhật ký việc danh sách ghi chú (shot, mốc giây, nội dung); sửa code shot; dựng lại các shot bị ảnh hưởng qua cầu nối; thay video giữ một bản trước (spec 029); trả lời mọi ghi chú của lượt (tick khi sửa được, kèm lý do khi không).
- **FR-012**: Trong lúc việc sửa chạy, sổ ghi chú PHẢI ghi nhận ghi chú nào thuộc lượt đang chạy; ghi chú thêm hoặc sửa trong lúc đó PHẢI được lưu và để cho lượt sau; trang phim PHẢI hiện việc đang chạy.
- **FR-013**: Việc sửa ghi chú và việc làm phim AE PHẢI ghi lại số token Claude đã dùng và thời gian dựng, hiện trên trang việc; không có trần riêng cho mỗi việc, chỉ áp hạn mức chung hiện có của app.
- **FR-014**: Việc lỗi PHẢI giữ nguyên video cũ và ghi chú mở, báo bước hỏng kèm nhật ký.
- **FR-015**: Phim `ae-crayon-test` PHẢI được chuyển sang dạng mới và cho ra video trùng với bộ code cũ.
- **FR-016**: Luồng build GitHub Actions của app desktop PHẢI có bài thử cầu nối AE với một AE giả, chạy trên Windows và macOS; bộ cài PHẢI có phần cài đặt đường dẫn AE (tự tìm ở chỗ cài mặc định, kiểm và lưu đường dẫn người dùng chọn).
- **FR-017**: Xưởng KHÔNG ĐƯỢC cài, tải hay đóng gói After Effects (hiến pháp VII); thiếu AE thì chỉ báo.
- **FR-018**: Form tạo phim của app PHẢI cho chọn bộ máy (trang web hoặc After Effects); chọn After Effects khi cầu nối không sẵn sàng thì báo trước và không tạo việc.
- **FR-019**: Việc làm phim AE PHẢI đi qua các bước chung của xưởng: kịch bản được chấm (specs/010), giọng và kiểm tầng 0 (specs/020), điểm duyệt đang bật (specs/026), gói đăng (specs/011); phần hình gồm bảng shot, code từng shot bằng bộ dựng chung, luật dàn cảnh cho mỗi shot, dựng và render qua cầu nối, trộn tiếng, mốc shot (spec 029).
- **FR-020**: Phim AE mới PHẢI chỉ chứa phần riêng của phim (shot, danh sách shot, cấu hình, tiếng, video); bộ dựng chung không được chép vào phim.

### Key Entities

- **Phim AE**: thư mục phim khai báo bộ máy After Effects, có các tệp shot riêng, danh sách shot (số shot, thứ tự) và cấu hình phim (khung hình, tốc độ khung); video và mốc shot như spec 029.
- **Bộ dựng AE dùng chung**: phần code của xưởng mọi phim AE dùng; có danh mục phần nào được shot nào dùng.
- **Cấu hình AE của máy**: đường dẫn After Effects, trình render, thư mục làm việc; thuộc về máy, không thuộc phim.
- **Yêu cầu dựng AE**: phim, danh sách shot, trạng thái (chờ, đang dựng shot n, xong, lỗi), tiến độ, kết quả từng shot, nhật ký.
- **Việc sửa ghi chú**: phim, danh sách ghi chú của lượt, các bước, token đã dùng, kết quả (ghi chú đã sửa, chưa sửa và lý do).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Dựng lại 1 shot (≤ 7 s) của `ae-crayon-test` và ghép vào video mất ≤ 60 giây trên máy hiện tại; video ghép trùng bản dựng đầy đủ (0 khung dưới 30 dB) và dài đúng 4128 khung.
- **SC-002**: Một phim AE mới dùng bộ dựng chung không chứa bản sao nào của phần dùng chung (0 tệp trùng), và chạy được trên máy thứ hai chỉ bằng cấu hình máy.
- **SC-003**: Hai yêu cầu dựng gửi cùng lúc: 0 lần chạy song song qua 10 lần thử tự động với AE giả; yêu cầu thứ hai bắt đầu trong ≤ 2 giây sau khi yêu cầu đầu xong.
- **SC-004**: Thiếu AE, AE treo hay cầu nối không chạy đều cho thông báo rõ ràng trong ≤ 10 giây (thiếu AE, cầu nối không chạy) hoặc ngay khi hết thời hạn mỗi shot (AE treo), ở 100% lần thử tự động.
- **SC-005**: Với 3 ghi chú mở ở 3 shot của `ae-crayon-test`, bấm "Fix with Claude" một lần: việc tự chạy tới cuối không cần thao tác thêm; mọi ghi chú có trả lời; chỉ các shot bị ảnh hưởng được dựng lại (đếm trong nhật ký); video mới hiện trên trang phim mà không tải lại.
- **SC-006**: 100% yêu cầu tới cầu nối không đến từ phần lõi của máy bị từ chối trong test tự động.
- **SC-007**: Luồng build thử trên GitHub Actions qua trên Windows và macOS, gồm bài thử cầu nối với AE giả.
- **SC-008**: Phim AE mới khoảng 30 giây tạo từ một ý tưởng trên app chạy tới khi giao phim mà người dùng chỉ thao tác ở các điểm duyệt đang bật; mốc shot khớp video (lệch ≤ 1 khung); 0 tệp của bộ dựng chung bị chép vào phim.
- **SC-009**: Trên một máy Windows và một máy macOS có After Effects thật, cài bộ cài mới rồi chạy "Fix with Claude" cho một ghi chú: cả hai máy dựng lại đúng shot, thay video và trả lời ghi chú (kiểm bằng tay theo quickstart).

## Assumptions

- Tạo phim AE mới trên app nằm trong phạm vi (User Story 5). Tiếng của phim mới là giọng đọc và nhạc của xưởng (hiến pháp: câu chuyện, giọng, nhạc là của mình), không dùng tiếng của video tham chiếu như phim tập luyện.
- Video mới thay luôn sau khi dựng xong (đã chốt ở Clarifications), giữ một bản trước như spec 029; không có bước duyệt trước khi thay.
- Kiểm chứng với AE thật trên cả Windows và macOS (đã chốt ở Clarifications). Máy chạy GitHub Actions không có AE, nên luồng build chỉ thử với AE giả; bước thử AE thật trên macOS cần người dùng cho dùng một máy Mac có cài AE (ghi trong quickstart).
- Thuật ngữ: "lượt sửa" là một lần sửa ghi chú (một việc `fix`); "lượt dựng AE" là một lần cầu nối dùng After Effects. Một lượt sửa có thể gồm nhiều lượt dựng AE.
- Giới hạn mặc định 10 ghi chú mỗi lượt sửa và 5 phút mỗi shot; đổi được trong cấu hình. Không có trần token riêng cho mỗi việc (đã chốt ở Clarifications).
- Bản quyền After Effects do người dùng tự lo (trial hiện hết hạn 2026-11-29). Hết bản quyền thì AE không chạy và cầu nối báo lỗi theo FR-008.
- Chạy luồng phát hành (gắn tag, tạo bộ cài thật) tốn phút chạy GitHub: chỉ làm khi người dùng bảo; spec này chỉ bắt buộc luồng build thử.
