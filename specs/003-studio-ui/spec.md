# Feature Specification: Giao diện và API của xưởng (giai đoạn 1: theo dõi và duyệt)

**Feature Branch**: `003-studio-ui`
**Created**: 2026-11-06
**Status**: Draft
**Input**: User description: "Giao diện web và API của xưởng phim (giai đoạn 1: chạy trên máy người dùng, chỉ một người dùng là chủ máy; API thiết kế để giai đoạn 2 phục vụ khách hàng qua internet). MVP là "theo dõi và duyệt": (1) xem danh sách việc đang chạy và đã xong — học phong cách và làm phim — với trạng thái, bước hiện tại, tiến độ, nhật ký ngắn, việc nào đang chờ duyệt; (2) duyệt lần 1 (bản phong cách: tóm tắt, 10 luật kèm số đo, các kết luận đã sửa) và duyệt lần 2 (ảnh ghép khung gốc và khung tự vẽ, bảng 4 chỉ số) bằng nút Đồng ý hoặc Yêu cầu sửa kèm góp ý, và việc đang chạy tiếp tục mà người dùng không phải gõ trong khung chat; duyệt trong khung chat vẫn dùng được; (3) xem kết quả: phát phim kèm poster và phụ đề, xem hồ sơ đo (bảng số liệu, bảng màu, ảnh ghép mỗi 2 giây), xem phong cách riêng đã lưu và khung chứng minh. Ngoài phạm vi MVP: khởi chạy việc mới từ giao diện, thư viện 66 phong cách, tài khoản, thanh toán, máy chủ cloud. Mở bằng trình duyệt Windows khi xưởng chạy trong WSL. Giao diện bằng tiếng Việt. Không làm lộ video tham chiếu ra ngoài máy."

## Bối cảnh

Khi test thật (tính năng 002), những chỗ khó nhất là: duyệt phong cách bằng cách đọc chữ trong khung chat; mở ảnh so sánh và phim bằng lệnh; không biết việc đang chạy tới đâu. Giai đoạn 1 giải quyết đúng những chỗ đó cho **một người dùng trên chính máy của họ**. Giai đoạn 2 (tính năng sau) mới đưa xưởng tới khách hàng qua internet; vì vậy giao diện lập trình (API) của giai đoạn 1 phải đủ rõ và ổn định để giai đoạn 2 dùng lại.

## Clarifications

### Session 2026-11-06

- Q: Giao diện nên chạy khi nào? → A: Tự bật chạy nền khi một việc học phong cách hoặc làm phim bắt đầu (nếu chưa chạy), và Claude in đường link để mở; lệnh mở bằng tay vẫn có để xem kết quả cũ.
- Q: Khi có việc chờ duyệt, xưởng báo bằng cách nào? → A: Làm nổi bật việc và đánh dấu tiêu đề tab, cộng thêm thông báo của trình duyệt (hiện ở góc màn hình hệ điều hành); không có âm thanh.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Theo dõi việc đang chạy (Priority: P1)

Người dùng bắt đầu một việc học phong cách hoặc làm phim trong khung chat như hiện nay. Họ mở giao diện trong trình duyệt và thấy ngay danh sách việc: loại việc, tên, trạng thái, bước hiện tại, tiến độ, thời điểm cập nhật cuối, vài dòng nhật ký gần nhất, và việc nào **đang chờ họ duyệt**. Danh sách tự cập nhật, không cần tải lại trang.

**Why this priority**: Đây là nền cho mọi thứ khác: không thấy việc thì không duyệt được, không xem được kết quả. Tự nó đã có giá trị (biết việc tới đâu mà không phải đọc khung chat).

**Independent Test**: Bắt đầu một việc học phong cách trên bộ video thử; mở giao diện; thấy việc xuất hiện, bước hiện tại đổi theo khi việc chạy, và trạng thái cuối là "xong".

**Acceptance Scenarios**:

1. **Given** không có việc nào, **When** mở giao diện, **Then** thấy trang trống kèm hướng dẫn ngắn cách bắt đầu một việc trong khung chat.
2. **Given** một việc học phong cách vừa bắt đầu, **When** mở giao diện, **Then** việc đó xuất hiện với trạng thái "đang chạy" và bước hiện tại (ví dụ "Đo video 3/5").
3. **Given** một việc đang chạy, **When** việc chuyển bước, **Then** giao diện hiện bước mới mà không cần tải lại trang.
4. **Given** một việc dừng vì lỗi, **When** xem việc đó, **Then** thấy trạng thái "lỗi", thông báo lỗi và gợi ý việc cần làm.
5. **Given** một việc đang chờ duyệt, **When** nhìn danh sách, **Then** việc đó được làm nổi bật và tiêu đề tab trình duyệt báo có việc chờ duyệt.

---

### User Story 2 - Duyệt trên giao diện (Priority: P2)

Khi việc học phong cách tới lần duyệt 1 hoặc lần duyệt 2, người dùng mở trang duyệt trên giao diện:
- **Lần 1**: bản tóm tắt phong cách, 10 luật quan trọng kèm con số, các kết luận đã sửa, cảnh báo của hồ sơ đo, kỹ thuật nền được chọn.
- **Lần 2**: ảnh khung gốc và khung tự vẽ đặt cạnh nhau (phóng to được), bảng 4 chỉ số kèm ngưỡng và đạt hay chưa, số vòng sửa đã dùng, ghi chú của Claude về những gì số đo không bắt được.

Họ bấm **Đồng ý** hoặc **Yêu cầu sửa** (kèm ô góp ý). Ở lần 2, khi đã hết vòng sửa mà chưa đạt, có thêm **Chấp nhận dù chưa đạt** và **Dừng**. Việc đang chạy tự tiếp tục theo quyết định đó, người dùng không phải gõ gì trong khung chat.

**Why this priority**: Giải quyết chỗ khó nhất khi test thật, nhưng cần US1 để biết việc nào chờ duyệt.

**Independent Test**: Chạy một việc học phong cách tới lần duyệt 1; bấm "Yêu cầu sửa" với một góp ý; thấy việc chạy lại bước viết phong cách theo góp ý và quay lại chờ duyệt; bấm "Đồng ý"; việc đi tiếp sang bước khung chứng minh.

**Acceptance Scenarios**:

1. **Given** việc chờ duyệt lần 1, **When** mở trang duyệt, **Then** thấy đủ: bản chất, 10 luật kèm số, các kết luận đã sửa, cảnh báo, kỹ thuật nền; không cần mở file nào.
2. **Given** việc chờ duyệt lần 2, **When** mở trang duyệt, **Then** thấy ảnh gốc và ảnh tự vẽ cạnh nhau, bảng 4 chỉ số có ngưỡng và dấu đạt hoặc chưa đạt.
3. **Given** trang duyệt đang mở, **When** bấm "Đồng ý", **Then** việc tiếp tục bước sau và trạng thái không còn "chờ duyệt".
4. **Given** trang duyệt đang mở, **When** bấm "Yêu cầu sửa" kèm góp ý, **Then** Claude nhận đúng góp ý đó, sửa, và việc quay lại chờ duyệt cùng lần đó.
5. **Given** việc chờ duyệt, **When** người dùng trả lời trong khung chat thay vì giao diện, **Then** việc vẫn đi tiếp, và giao diện ghi nhận đã duyệt qua khung chat.
6. **Given** đã có một quyết định cho lần duyệt này (từ giao diện hoặc khung chat), **When** có quyết định thứ hai, **Then** quyết định thứ hai bị từ chối kèm thông báo "đã được duyệt".
7. **Given** "Yêu cầu sửa" với ô góp ý trống, **When** bấm gửi, **Then** giao diện yêu cầu nhập góp ý trước khi gửi.

---

### User Story 3 - Xem kết quả (Priority: P3)

Người dùng xem kết quả ngay trên giao diện:
- **Phim**: phát phim có tiếng, poster, phụ đề bật tắt được, danh sách tài sản bên thứ ba và giấy phép.
- **Hồ sơ đo** của một bộ tham chiếu: bảng số liệu tổng hợp, bảng màu, cảnh báo, và các ảnh ghép mỗi 2 giây (khi còn trên máy).
- **Phong cách riêng** đã lưu: tên, kỹ thuật nền, nguồn học (số video, thời lượng đã đo), khung chứng minh, nội dung phong cách.

**Why this priority**: Thay cho việc mở thư mục bằng lệnh; có giá trị nhưng không chặn việc học hay làm phim.

**Independent Test**: Với một phim đã làm và một phong cách đã lưu, mở giao diện, phát được phim có tiếng, xem được hồ sơ đo và khung chứng minh, không dùng lệnh nào.

**Acceptance Scenarios**:

1. **Given** một phim đã xong, **When** mở trang phim, **Then** phát được phim có tiếng, thấy poster, bật tắt được phụ đề.
2. **Given** một bộ tham chiếu đã đo, **When** mở trang hồ sơ đo, **Then** thấy bảng số liệu, bảng màu và các ảnh ghép xem lần lượt được.
3. **Given** video tham chiếu của bộ đã bị xoá, **When** mở hồ sơ đo, **Then** vẫn thấy số liệu; phần ảnh ghép báo "đã xoá cùng video tham chiếu".
4. **Given** một phong cách riêng đã lưu, **When** mở trang phong cách, **Then** thấy khung chứng minh, kỹ thuật nền, nguồn học, và nội dung phong cách hiển thị dễ đọc.

---

### Edge Cases

- Khung chat (phiên Claude) bị đóng trong lúc việc đang chờ duyệt: giao diện vẫn nhận quyết định và lưu lại; việc hiện "chờ tiếp tục" cùng hướng dẫn mở lại phiên để chạy tiếp; quyết định đã lưu được dùng ngay khi tiếp tục.
- Giao diện bị tắt hoặc không bật được (ví dụ cổng bị chiếm) khi việc tới bước duyệt: quyết định vẫn có thể đưa qua khung chat như hiện nay; mở giao diện sau vẫn thấy đúng trạng thái.
- Hai cửa sổ giao diện cùng mở một trang duyệt: chỉ quyết định đầu tiên được nhận.
- Việc bị dừng giữa chừng (tắt máy, đóng terminal): việc hiện "không còn hoạt động" khi không có cập nhật quá một khoảng thời gian, không treo mãi ở "đang chạy".
- Phim chưa render xong: trang phim hiện tiến độ thay vì trình phát.
- File kết quả bị xoá bằng tay: giao diện báo thiếu file, không lỗi trắng trang.
- Cổng mặc định đang bị chiếm: báo rõ và gợi ý cổng khác.
- Có người khác trong cùng mạng Wi-Fi thử truy cập: bị từ chối.

## Requirements *(mandatory)*

### Functional Requirements

**Theo dõi**
- **FR-001**: Mọi việc học phong cách và làm phim (bắt đầu từ khung chat) MUST tự đăng ký một bản ghi việc gồm: mã việc, loại, tên, trạng thái, bước hiện tại, tiến độ (số trên tổng khi có), thời điểm bắt đầu, thời điểm cập nhật cuối, nhật ký ngắn (tối đa 50 dòng gần nhất), và đường dẫn tới kết quả.
- **FR-002**: Trạng thái việc MUST thuộc một trong: đang chạy · chờ duyệt · chờ tiếp tục · xong · lỗi · đã dừng · không còn hoạt động.
- **FR-003**: Giao diện MUST hiện danh sách việc, mới nhất trước, kèm bộ lọc theo trạng thái và loại việc.
- **FR-004**: Giao diện MUST tự cập nhật trạng thái và bước của việc mà không cần tải lại trang.
- **FR-005**: Việc ở trạng thái "đang chạy" mà không có cập nhật trong 10 phút MUST chuyển sang "không còn hoạt động".

**Duyệt**
- **FR-006**: Khi việc học phong cách tới lần duyệt 1 hoặc 2, xưởng MUST tạo một yêu cầu duyệt chứa đủ nội dung của US2 (lần 1: tóm tắt, 10 luật kèm số, kết luận đã sửa, cảnh báo, kỹ thuật nền; lần 2: ảnh gốc, ảnh tự vẽ, bảng 4 chỉ số kèm ngưỡng, số vòng sửa, ghi chú).
- **FR-006a**: Khi có yêu cầu duyệt mới, giao diện MUST: làm nổi bật việc đó trong danh sách; ghi số việc chờ duyệt vào tiêu đề tab (ví dụ "(1) chờ duyệt"); và gửi một thông báo của trình duyệt dẫn thẳng tới trang duyệt, nếu người dùng đã cho phép thông báo. Lần đầu, giao diện MUST hỏi quyền thông báo kèm giải thích ngắn; người dùng từ chối thì vẫn có hai cách báo kia. Không phát âm thanh.
- **FR-007**: Người dùng MUST đưa được một quyết định cho mỗi yêu cầu duyệt: Đồng ý · Yêu cầu sửa (bắt buộc kèm góp ý) · và riêng lần 2 khi đã hết vòng sửa: Chấp nhận dù chưa đạt · Dừng.
- **FR-008**: Quyết định đưa trên giao diện MUST làm việc đang chạy đi tiếp mà người dùng không phải gõ trong khung chat, khi phiên Claude của việc đó còn mở.
- **FR-009**: Quyết định trong khung chat MUST vẫn dùng được và MUST được ghi lại trên giao diện kèm nguồn ("khung chat").
- **FR-010**: Mỗi yêu cầu duyệt MUST nhận đúng một quyết định; quyết định thứ hai bị từ chối kèm lý do.
- **FR-011**: Quyết định đưa khi phiên Claude đã đóng MUST được lưu và được dùng khi việc tiếp tục.

**Xem kết quả**
- **FR-012**: Giao diện MUST phát được phim của xưởng có tiếng, kèm poster, phụ đề bật tắt được, và nội dung CREDITS.
- **FR-013**: Giao diện MUST hiện hồ sơ đo của một bộ tham chiếu: bảng số liệu tổng hợp, bảng màu, cảnh báo, và ảnh ghép mỗi 2 giây khi còn trên máy.
- **FR-014**: Giao diện MUST hiện danh sách phong cách riêng và trang chi tiết mỗi phong cách: tên, kỹ thuật nền, nguồn học (số video, thời lượng đo, định dạng), khung chứng minh, nội dung `STYLE.md` hiển thị dễ đọc.

**API (để giai đoạn 2 dùng lại)**
- **FR-015**: Mọi thứ giao diện hiện và mọi quyết định duyệt MUST đi qua một giao diện lập trình có phiên bản, có tài liệu mô tả máy đọc được, và có mã lỗi nhất quán.
- **FR-016**: Giao diện lập trình MUST không phụ thuộc vào việc chỉ có một người dùng theo cách khiến giai đoạn 2 phải đổi hình dạng dữ liệu (ví dụ: mọi bản ghi có chỗ cho chủ sở hữu, mặc định là chủ máy).

**An toàn và riêng tư**
- **FR-017**: Ở giai đoạn 1, giao diện và giao diện lập trình MUST chỉ truy cập được từ chính máy đó (kể cả từ trình duyệt Windows khi xưởng chạy trong WSL), và MUST từ chối truy cập từ máy khác trong mạng.
- **FR-018**: Video, âm thanh, ảnh ghép và khung gốc của bộ tham chiếu MUST NOT được gửi ra ngoài máy, và MUST NOT bị đưa vào bất kỳ tệp nào được commit.
- **FR-019**: Giao diện MUST chỉ phục vụ tệp nằm trong các thư mục của xưởng (phim, bộ tham chiếu, phong cách riêng); yêu cầu ngoài các thư mục đó MUST bị từ chối.

**Vận hành**
- **FR-020**: Người dùng MUST mở được giao diện bằng một lệnh của xưởng; lệnh in ra địa chỉ để mở trong trình duyệt. Nếu giao diện đã chạy, lệnh không mở bản thứ hai mà chỉ in địa chỉ.
- **FR-020a**: Khi một việc học phong cách hoặc làm phim bắt đầu, xưởng MUST tự bật giao diện chạy nền nếu chưa chạy, và Claude MUST in đường link giao diện (kèm đường link tới đúng việc đó) vào khung chat. Giao diện chạy nền MUST không làm chậm hay chặn việc đang chạy, và MUST tắt được bằng một lệnh.
- **FR-021**: Giao diện MUST dùng tiếng Việt cho mọi chữ hiển thị.

### Key Entities

- **Việc**: một lần học phong cách hoặc làm phim; có loại, tên, trạng thái, bước, tiến độ, nhật ký, kết quả, chủ sở hữu.
- **Yêu cầu duyệt**: thuộc một việc; loại (lần 1, lần 2); nội dung để duyệt; trạng thái (chờ, đã quyết định); quyết định (giá trị, góp ý, nguồn: giao diện hoặc khung chat, thời điểm).
- **Phim**: thư mục phim với tệp phim, poster, phụ đề, CREDITS, TREATMENT.
- **Bộ tham chiếu**: hồ sơ đo (số liệu, bảng màu, cảnh báo, ảnh ghép nếu còn).
- **Phong cách riêng**: gói phong cách đã lưu cùng khung chứng minh.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Mở được giao diện từ trình duyệt Windows bằng **1 lệnh**, trong **dưới 5 giây**.
- **SC-002**: Một việc vừa bắt đầu xuất hiện trên giao diện trong **dưới 5 giây**; mỗi lần đổi bước hiện lên trong **dưới 5 giây**.
- **SC-003**: Từ lúc bấm "Đồng ý" hay "Yêu cầu sửa" tới lúc việc tiếp tục chạy: **dưới 10 giây**, khi phiên Claude còn mở.
- **SC-003a**: Thông báo chờ duyệt hiện trong **dưới 10 giây** kể từ khi việc tới bước duyệt, khi giao diện đang mở trong một tab (kể cả tab không được chọn).
- **SC-004**: Duyệt lần 1 và lần 2 cần **0 lệnh** và **0 lần mở file** ngoài giao diện.
- **SC-005**: Xem phim, hồ sơ đo và phong cách riêng cần **0 lệnh** ngoài giao diện.
- **SC-006**: **0** yêu cầu từ máy khác trong mạng được phục vụ; **0** yêu cầu tới tệp ngoài thư mục của xưởng được phục vụ.
- **SC-007**: **100%** điểm truy cập của giao diện lập trình có trong tài liệu mô tả, có phiên bản, và có ít nhất một kiểm thử tự động.
- **SC-008**: Trang danh sách với 50 việc tải xong trong **dưới 2 giây**.
- **SC-009**: Một lần học phong cách thật đi trọn từ đầu tới lưu, với cả 2 lần duyệt làm trên giao diện, không gõ gì trong khung chat sau câu yêu cầu đầu tiên.

## Assumptions

- Giai đoạn 1 chỉ có một người dùng là chủ máy; không cần đăng nhập. Chủ sở hữu của mọi bản ghi mặc định là chủ máy.
- Việc vẫn được bắt đầu trong khung chat (Claude Code), như hiện nay; khởi chạy việc từ giao diện nằm ngoài phạm vi.
- Phim làm theo quy trình của thư viện chỉ có một bước duyệt tuỳ chọn (storyboard); trong MVP, bước đó vẫn duyệt trong khung chat; giao diện chỉ theo dõi và xem kết quả phim.
- Việc tiếp tục sau khi duyệt cần phiên Claude của việc đó còn mở; giai đoạn 1 không tự mở lại phiên đã đóng.
- Người dùng chạy xưởng trong WSL hoặc macOS/Linux; trình duyệt là trình duyệt hiện đại (Edge, Chrome, Firefox, Safari bản gần đây).
- Các việc đã chạy trước tính năng này (như bộ `thu-kenh`, phim `banh-mi-dem`) được hiện ở mức xem kết quả, không có lịch sử bước.
- Giai đoạn 2 (khách hàng qua internet, máy chủ, gọi Claude bằng API, tài khoản, thanh toán, bản quyền) là các tính năng sau; giai đoạn 1 chỉ giữ cho giao diện lập trình không chặn hướng đó.
