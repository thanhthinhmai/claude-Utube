# Feature Specification: Thư viện phong cách trên Film Studio

**Feature Branch**: `004-style-library`
**Created**: 2026-11-06
**Status**: Draft
**Input**: User description: "Thư viện phong cách trên Film Studio (giao diện web của xưởng). Thêm trang Library để xem 66 phong cách của thư viện lemo-opuscar đã ghim: lưới thẻ có poster, số thứ tự, tên, nhóm, tên phim mẫu, câu mô tả, mục đích dùng; lọc theo nhóm và tìm theo tên; trang chi tiết hiện STYLE.md; nút "Use this style" chép câu lệnh mẫu để dán vào Claude Code (giao diện không tự chạy việc). Phong cách riêng trong my-styles/ hiện cùng chỗ với nhãn "My style". Poster được tải thêm khi chạy setup (người dùng chọn cách 1: tải thêm poster, vài chục MB), không tải phim demo (chỉ link sang trang GitHub của thư viện). Không sửa file trong lib/ (hiến pháp VI). Chữ trên giao diện bằng tiếng Anh, theo kiểu giao diện hiện tại. API mới nằm dưới /api/v1, chỉ đọc, chỉ phục vụ tệp theo tên đã kiểm."

## Bối cảnh

Xưởng đã có sẵn 66 phong cách của thư viện trên máy, nhưng muốn biết có những phong cách nào thì người dùng phải đọc file hoặc hỏi Claude. Tính năng 003 cố ý để thư viện ngoài phạm vi. Tính năng này cho người dùng **nhìn và chọn** phong cách ngay trên Film Studio, rồi mang lựa chọn đó sang Claude Code để làm phim. Giao diện vẫn chỉ xem; việc làm phim vẫn bắt đầu trong Claude Code.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Xem và tìm phong cách trong thư viện (Priority: P1)

Người dùng mở trang Library và thấy một lưới thẻ, mỗi thẻ là một phong cách: poster, số thứ tự, tên, nhóm, tên phim mẫu, một câu mô tả phim mẫu, các mục đích dùng. Họ lọc theo nhóm (ví dụ "Hand-drawn & Painting") hoặc gõ tên để tìm. Bấm một thẻ thì mở trang chi tiết: poster lớn, thông tin trên, toàn bộ luật của phong cách (STYLE.md), và link sang trang của phong cách đó trên GitHub để xem phim mẫu.

**Why this priority**: Đây là giá trị chính: chọn phong cách bằng mắt thay vì đọc 66 file. Chỉ riêng phần này đã dùng được.

**Independent Test**: Sau `setup`, mở trang Library: đếm được đúng số phong cách của thư viện, mỗi thẻ có poster; lọc một nhóm chỉ còn phong cách của nhóm đó; gõ "deco" thấy Art Deco; mở chi tiết thấy luật và link GitHub.

**Acceptance Scenarios**:

1. **Given** thư viện đã tải kèm poster, **When** mở trang Library, **Then** thấy đủ mọi phong cách của thư viện (hiện là 66), mỗi thẻ có poster và các thông tin kể trên, xếp theo số thứ tự.
2. **Given** trang Library, **When** chọn một nhóm, **Then** chỉ còn các phong cách thuộc nhóm đó, kèm số lượng.
3. **Given** trang Library, **When** gõ một phần tên tiếng Anh, tên tiếng Trung, tên thư mục, hoặc một mục đích dùng, **Then** chỉ còn các phong cách khớp; xoá ô tìm thì hiện lại đủ.
4. **Given** một thẻ, **When** bấm vào, **Then** mở trang chi tiết có poster lớn, thông tin, luật đầy đủ của phong cách và link GitHub tới thư mục phong cách ở đúng phiên bản thư viện đang ghim.
5. **Given** tìm hoặc lọc không ra kết quả, **When** nhìn trang, **Then** thấy thông báo không có kết quả và cách xoá bộ lọc.

---

### User Story 2 - Dùng một phong cách để làm phim (Priority: P2)

Ở thẻ hoặc trang chi tiết, người dùng bấm "Use this style". Xưởng chép vào bộ nhớ tạm một câu lệnh mẫu có tên phong cách (ví dụ "Make a 40-second film in the Art Deco style about …") và báo đã chép. Người dùng dán vào Claude Code, sửa phần nội dung, và Claude làm phim như luồng hiện tại.

**Why this priority**: Nối việc chọn phong cách với việc làm phim, nhưng cần P1 trước.

**Independent Test**: Bấm "Use this style" ở Art Deco; nội dung bộ nhớ tạm là câu lệnh chứa "Art Deco"; trang hiện "Copied".

**Acceptance Scenarios**:

1. **Given** một phong cách thư viện, **When** bấm "Use this style", **Then** câu lệnh mẫu chứa tên phong cách được chép và trang báo đã chép.
2. **Given** trình duyệt không cho chép tự động, **When** bấm "Use this style", **Then** trang hiện câu lệnh trong ô có thể bôi đen để chép tay.
3. **Given** bất kỳ trang nào của Library, **When** người dùng thao tác, **Then** giao diện không tự bắt đầu việc nào (không tạo việc, không chạy lệnh).

---

### User Story 3 - Phong cách riêng hiện cùng thư viện (Priority: P3)

Phong cách riêng trong `my-styles/` (ví dụ Quiet Night) hiện trong cùng trang Library, có nhãn "My style" và có bộ lọc riêng "My styles". Thẻ dùng khung chứng minh làm ảnh, ghi phong cách nền của thư viện mà nó dựa vào. Bấm vào mở trang phong cách riêng đã có ở 003; "Use this style" cũng chạy với phong cách riêng.

**Why this priority**: Gom mọi lựa chọn vào một chỗ; phong cách riêng đã xem được ở 003 nên ít gấp hơn.

**Independent Test**: Với một phong cách riêng trong `my-styles/`, trang Library hiện nó ở đầu lưới với nhãn "My style"; bộ lọc "My styles" chỉ còn phong cách riêng.

**Acceptance Scenarios**:

1. **Given** có phong cách riêng, **When** mở Library, **Then** phong cách riêng đứng đầu lưới, có nhãn "My style", ảnh là khung chứng minh, và ghi "based on <phong cách nền>".
2. **Given** chọn bộ lọc "My styles", **When** nhìn lưới, **Then** chỉ còn phong cách riêng.
3. **Given** không có phong cách riêng nào, **When** mở Library, **Then** không có nhãn hay bộ lọc "My styles" trống gây nhầm; có một dòng gợi ý cách học phong cách mới.

---

### Edge Cases

- **Chưa có poster** (máy đã `setup` trước tính năng này, hoặc tải poster lỗi): thẻ hiện ô thay thế có tên phong cách; trang Library hiện một dòng gợi ý chạy `sh bin/studio setup` để tải poster. Mọi thứ khác vẫn dùng được.
- **Chưa có thư viện** (chưa `setup`): trang Library báo chưa có thư viện và hướng dẫn chạy `sh bin/studio setup`.
- **Một phong cách có thông tin hỏng hoặc thiếu** (file mô tả không đọc được): bỏ qua phong cách đó, trang ghi rõ số phong cách bị bỏ qua; các phong cách khác vẫn hiện.
- **Thư mục mẫu của thư viện** (`_template`) không được hiện như một phong cách.
- **Đổi phiên bản thư viện** (`library.lock`): danh sách, poster và link GitHub theo phiên bản mới sau khi chạy `setup`.
- **Tên phong cách lạ trong đường dẫn** (có `..`, `/`, ký tự lạ): bị từ chối, không đọc file ngoài thư viện.
- **Mạng chậm hoặc chặn khi tải poster**: `setup` vẫn hoàn tất phần thư viện cần để làm phim; báo poster chưa tải được và có thể chạy lại sau.

## Requirements *(mandatory)*

### Functional Requirements

**Tải thư viện**

- **FR-001**: `sh bin/studio setup` MUST tải thêm poster của mọi phong cách thư viện ở phiên bản đang ghim, cùng lúc với phần thư viện hiện có, và MUST NOT tải phim mẫu hay mã nguồn phim mẫu.
- **FR-002**: Máy đã `setup` trước tính năng này MUST nhận được poster chỉ bằng cách chạy lại `sh bin/studio setup`, không phải xoá thư viện hay tải lại từ đầu.
- **FR-003**: Lỗi khi tải poster MUST NOT làm hỏng phần thư viện cần để làm phim; `setup` MUST báo rõ poster chưa tải được.
- **FR-004**: Việc tải MUST NOT sửa file nào trong thư viện (hiến pháp VI); `sh bin/studio status` MUST báo có poster hay chưa (ví dụ "posters: 66/66").

**Trang Library**

- **FR-005**: Thanh bên MUST có mục "Library" dẫn tới trang lưới phong cách; trang MUST hiện mọi phong cách của thư viện (trừ thư mục mẫu), xếp theo số thứ tự.
- **FR-006**: Mỗi thẻ MUST có: poster (hoặc ô thay thế), số thứ tự, tên tiếng Anh, nhóm, tên phim mẫu, câu mô tả phim mẫu, các mục đích dùng.
- **FR-007**: Người dùng MUST lọc được theo nhóm (kèm số lượng mỗi nhóm) và tìm theo tên tiếng Anh, tên tiếng Trung, tên thư mục hoặc mục đích dùng; lọc và tìm kết hợp được; kết quả hiện ngay khi gõ, không tải lại trang.
- **FR-008**: Bộ lọc và chuỗi tìm MUST được giữ trong địa chỉ trang, để tải lại hoặc quay lại vẫn thấy đúng kết quả.
- **FR-009**: Trang chi tiết MUST hiện poster lớn, mọi thông tin của thẻ, luật đầy đủ của phong cách (STYLE.md) đã được làm sạch như các trang khác, và link GitHub tới thư mục phong cách ở đúng commit đang ghim.
- **FR-010**: "Use this style" MUST có trên thẻ và trang chi tiết, chép một câu lệnh mẫu tiếng Anh chứa tên phong cách và báo đã chép; nếu không chép được thì hiện câu lệnh để chép tay.
- **FR-011**: Giao diện MUST NOT bắt đầu việc, chạy lệnh hay sửa file từ trang Library.

**Phong cách riêng**

- **FR-012**: Phong cách riêng MUST hiện trong cùng lưới, đứng trước phong cách thư viện, có nhãn "My style", ảnh là khung chứng minh và dòng "based on <phong cách nền>"; MUST có bộ lọc "My styles" khi có ít nhất một phong cách riêng.
- **FR-013**: Bấm thẻ phong cách riêng MUST mở trang phong cách riêng đã có; mục "Styles" riêng ở thanh bên MUST được gộp vào "Library" để không có hai nơi liệt kê phong cách.

**Giao diện lập trình và an toàn**

- **FR-014**: Dữ liệu cho trang Library MUST đi qua các điểm truy cập mới dưới `/api/v1`, chỉ đọc, có trong tài liệu máy đọc được của API, theo cùng quy tắc an toàn của 003 (chỉ trên máy, kiểm `Host`, lỗi dạng `{error: {code, message}}`).
- **FR-015**: Điểm truy cập ảnh và luật MUST chỉ nhận tên phong cách đúng mẫu đã có (chữ thường, số, gạch nối) và có trong danh sách thư viện; MUST NOT trả file nào khác của thư viện.
- **FR-016**: Mọi chữ cố định mới trên giao diện MUST bằng tiếng Anh (FR-021 của 003) và theo kiểu giao diện hiện tại (thẻ trắng, điểm nhấn tím, nhãn dạng viên thuốc).

### Key Entities

- **Library style**: một phong cách của thư viện ở phiên bản ghim. Thuộc tính: tên thư mục (mã), số thứ tự, tên tiếng Anh, tên tiếng Trung, nhóm, tên phim mẫu, câu mô tả, mục đích dùng, có poster hay không, luật (STYLE.md), link GitHub.
- **My style**: phong cách riêng đã có ở 003 (`my-styles/<mã>/`). Thêm vào danh sách chung với nhãn riêng, phong cách nền và khung chứng minh.
- **Style prompt**: câu lệnh mẫu chép ra cho Claude Code, chứa tên phong cách và chỗ trống cho nội dung phim.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Sau `setup`, trang Library hiện đúng số phong cách có trong thư viện ghim (66/66), và 100% thẻ có poster.
- **SC-002**: Người dùng tìm ra một phong cách cho trước theo tên trong không quá 10 giây từ lúc mở trang.
- **SC-003**: Trang Library với đủ 66 thẻ hiện xong trong dưới 2 giây trên máy người dùng; lọc và tìm cập nhật trong dưới 0,2 giây.
- **SC-004**: Từ trang Library tới câu lệnh đã chép vào Claude Code: 1 lần bấm.
- **SC-005**: Phần tải thêm của `setup` gồm 0 tệp phim; dung lượng tải thêm được đo và ghi trong tài liệu (dự kiến vài chục MB).
- **SC-006**: 100% yêu cầu tới tên phong cách lạ hoặc file ngoài danh sách bị từ chối (kiểm bằng test).
- **SC-007**: Không file nào trong thư viện bị sửa sau `setup` (kiểm bằng trạng thái git của thư viện).

## Assumptions

- Thư viện ghim (`library.lock`) có sẵn poster cho mỗi phong cách trong kho của thư viện; thông tin thẻ lấy từ file mô tả có sẵn của từng phong cách. Dung lượng poster được đo ở bước plan.
- Phim mẫu không có trong máy; người dùng xem phim mẫu trên GitHub qua link (cần mạng).
- Thanh bên đổi thành: Jobs, Films, rồi nhóm Library gồm "Library" (phong cách thư viện và phong cách riêng) và "Measurements". Trang phong cách riêng ở 003 giữ nguyên, chỉ đổi đường quay lại thành "Library".
- Câu lệnh mẫu: "Make a 40-second film in the <tên> style about …". Người dùng tự sửa thời lượng và nội dung.
- Chỉ một người dùng trên máy của họ, như 003; không cần tài khoản.
- Ngoài phạm vi: phát phim mẫu trong giao diện, so sánh hai phong cách, chỉnh sửa phong cách, bắt đầu làm phim từ giao diện, thư viện 98 phong cách đầy đủ ngoài bản ghim.
