# Feature Specification: Khung xưởng phim (Studio Skeleton)

**Feature Branch**: `001-studio-skeleton`
**Created**: 2026-11-05
**Status**: Draft
**Input**: User description: "Khung xưởng phim (studio skeleton). Người dùng mở dự án lần đầu và cần: (1) một lệnh chuẩn bị môi trường đưa thư viện phong cách bên ngoài về đúng chỗ ở một phiên bản cố định, không sửa thư viện, và báo rõ máy còn thiếu công cụ hệ thống nào (cùng phiên bản tối thiểu); (2) một lệnh kiểm tra trạng thái xưởng (thư viện có chưa, đúng phiên bản chưa, công cụ đủ chưa, có bao nhiêu phong cách thư viện và phong cách riêng); (3) cấu trúc thư mục rõ ràng cho phong cách riêng, phim và công cụ, trong đó phim và video tham chiếu không bị đưa vào git; (4) hướng dẫn cho Claude điều hướng đúng 3 luồng: xây xưởng bằng spec-kit, học phong cách (chưa có, phải báo), làm phim theo quy trình của thư viện với thư mục phim và phong cách riêng nằm trong dự án."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chuẩn bị xưởng lần đầu (Priority: P1)

Người dùng vừa tải dự án về máy. Họ chạy **một lệnh chuẩn bị**. Lệnh này đưa thư viện phong cách về đúng chỗ trong dự án, ở đúng phiên bản dự án đã chọn, và cho biết máy còn thiếu công cụ hệ thống nào, kèm phiên bản tối thiểu và cách khắc phục.

**Why this priority**: Không có thư viện thì không làm được phim nào. Đây là bước đầu tiên của mọi luồng.

**Independent Test**: Trên một bản sao mới của dự án, chạy lệnh chuẩn bị một lần. Thư viện xuất hiện đúng chỗ, đúng phiên bản; báo cáo công cụ khớp với thực tế của máy.

**Acceptance Scenarios**:

1. **Given** dự án vừa tải về và chưa có thư viện, **When** người dùng chạy lệnh chuẩn bị, **Then** thư viện được đặt vào vị trí cố định trong dự án, đúng phiên bản đã ghi, và lệnh in ra bảng công cụ (có / thiếu / quá cũ, phiên bản tìm thấy, phiên bản cần).
2. **Given** thư viện đã có và đúng phiên bản, **When** người dùng chạy lại lệnh chuẩn bị, **Then** không tải lại gì và lệnh kết thúc nhanh với thông báo "đã sẵn sàng".
3. **Given** dự án nâng phiên bản thư viện đã ghi, **When** người dùng chạy lệnh chuẩn bị, **Then** thư viện được đưa về phiên bản mới.
4. **Given** máy thiếu một công cụ hoặc công cụ quá cũ, **When** chạy lệnh chuẩn bị, **Then** lệnh nêu đúng công cụ đó, phiên bản cần, gợi ý cách cài, và **không** tự cài phần mềm hệ thống.

---

### User Story 2 - Kiểm tra trạng thái xưởng (Priority: P2)

Người dùng (hoặc Claude) muốn biết xưởng có sẵn sàng làm phim không. Họ chạy **một lệnh kiểm tra**. Lệnh trả lời: thư viện có chưa, có đúng phiên bản không, có bị sửa không, công cụ đủ chưa, có bao nhiêu phong cách thư viện, bao nhiêu phong cách riêng, bao nhiêu phim.

**Why this priority**: Giúp phát hiện vấn đề trước khi bắt đầu một bộ phim dài 30–60 phút. Không chặn được việc chuẩn bị nên xếp sau P1.

**Independent Test**: Tạo lần lượt các tình huống (chưa có thư viện, thư viện sai phiên bản, thư viện bị sửa một file, thêm một phong cách riêng) và chạy lệnh kiểm tra; mỗi lần báo cáo phải phản ánh đúng tình huống.

**Acceptance Scenarios**:

1. **Given** xưởng đã sẵn sàng, **When** chạy lệnh kiểm tra, **Then** báo "sẵn sàng" và liệt kê số phong cách thư viện, số phong cách riêng, số phim.
2. **Given** thư viện bị sửa ở một file, **When** chạy lệnh kiểm tra, **Then** báo "chưa sẵn sàng" và chỉ ra thư viện đã bị sửa.
3. **Given** Claude cần đọc kết quả, **When** chạy lệnh kiểm tra ở dạng máy đọc được, **Then** nhận được kết quả có cấu trúc với cùng thông tin.

---

### User Story 3 - Claude đi đúng luồng (Priority: P3)

Người dùng nói một yêu cầu bằng lời. Claude đọc hướng dẫn của dự án và chọn đúng một trong 3 luồng: xây xưởng (quy trình spec-kit), học phong cách từ kênh YouTube (chưa xây, phải báo rõ), hoặc làm phim (quy trình của thư viện, với thư mục phim và phong cách riêng nằm trong dự án).

**Why this priority**: Cần thiết để dùng xưởng đúng cách, nhưng chỉ có giá trị sau khi P1 hoạt động.

**Independent Test**: Đưa 3 yêu cầu mẫu, mỗi loại một yêu cầu, và kiểm tra hướng dẫn dẫn tới đúng luồng.

**Acceptance Scenarios**:

1. **Given** yêu cầu "làm một phim 40 giây theo phong cách màu nước về …", **When** Claude đọc hướng dẫn, **Then** Claude đi theo quy trình làm phim của thư viện, đặt phim trong thư mục phim của dự án, không tạo spec cho phim.
2. **Given** yêu cầu "học phong cách của kênh X", **When** luồng này chưa được xây, **Then** Claude báo rõ là chưa có và không làm tạm.
3. **Given** yêu cầu "viết thêm công cụ Y cho xưởng", **When** Claude đọc hướng dẫn, **Then** Claude dùng quy trình spec-kit.

---

### Edge Cases

- Lần chuẩn bị đầu tiên mà không có mạng: báo lỗi rõ ràng, không để lại thư viện dở dang.
- Việc tải bị ngắt giữa chừng: lần chạy sau tự phát hiện và làm lại cho đúng.
- Vị trí thư viện đã có thư mục nhưng không phải thư viện: dừng lại, không xoá, báo người dùng.
- Thư viện có thay đổi cục bộ: lệnh chuẩn bị **không** ghi đè; báo người dùng cách khôi phục.
- Công cụ có nhưng thấp hơn phiên bản tối thiểu: báo "quá cũ", không coi là đủ.
- Đường dẫn dự án có dấu cách: mọi lệnh vẫn chạy đúng.
- Chạy lệnh từ một thư mục con của dự án: vẫn tìm đúng gốc dự án.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Dự án MUST có một lệnh chuẩn bị chạy được bằng một dòng lệnh từ gốc dự án hoặc thư mục con.
- **FR-002**: Lệnh chuẩn bị MUST đặt thư viện phong cách vào một vị trí cố định bên trong dự án và vị trí này MUST không được đưa vào version control.
- **FR-003**: Phiên bản thư viện MUST được ghi trong một file của dự án (có trong version control). Lệnh chuẩn bị MUST đưa thư viện về đúng phiên bản đó.
- **FR-004**: Lệnh chuẩn bị MUST chạy lại được nhiều lần (idempotent); khi thư viện đã đúng phiên bản thì không tải lại.
- **FR-005**: Lệnh chuẩn bị và lệnh kiểm tra MUST NOT sửa bất kỳ file nào bên trong thư viện. Nếu thư viện có thay đổi cục bộ, lệnh chuẩn bị MUST dừng và báo, không ghi đè.
- **FR-006**: Lệnh chuẩn bị MUST kiểm tra từng công cụ hệ thống mà thư viện yêu cầu, và với mỗi công cụ báo một trong ba trạng thái: có (đủ phiên bản), thiếu, quá cũ; kèm phiên bản tìm thấy, phiên bản tối thiểu và gợi ý cách khắc phục.
- **FR-007**: Lệnh chuẩn bị MUST NOT tự cài phần mềm hệ thống.
- **FR-008**: Dự án MUST có một lệnh kiểm tra báo: thư viện có hay chưa; đúng phiên bản hay không; có thay đổi cục bộ hay không; trạng thái công cụ; số phong cách thư viện; số phong cách riêng; số phim.
- **FR-009**: Lệnh kiểm tra MUST kết thúc với kết quả "sẵn sàng" hoặc "chưa sẵn sàng" có thể phân biệt được bằng máy, và MUST có dạng đầu ra có cấu trúc cho Claude đọc.
- **FR-010**: Dự án MUST có các thư mục riêng cho: phong cách riêng, phim, công cụ tự viết, và video tham chiếu.
- **FR-011**: Nội dung thư mục phim và thư mục video tham chiếu, cùng mọi file video và âm thanh, MUST NOT bị đưa vào version control. Phong cách riêng và công cụ tự viết MUST được đưa vào version control.
- **FR-012**: Hướng dẫn cho Claude MUST ánh xạ mỗi loại yêu cầu tới đúng một luồng: xây xưởng → spec-kit; học phong cách → báo "chưa có" cho tới khi tính năng đó được xây; làm phim → quy trình làm phim của thư viện.
- **FR-013**: Với luồng làm phim, hướng dẫn MUST chỉ rõ: phim nằm trong thư mục phim của dự án, phong cách riêng nằm trong thư mục phong cách riêng của dự án, và Claude không tạo spec cho từng phim.
- **FR-014**: Khi thư viện đã có, lệnh kiểm tra MUST chạy được khi không có mạng.

### Key Entities

- **Thư viện phong cách**: bộ phong cách và công cụ làm phim từ bên ngoài; có phiên bản; chỉ đọc đối với dự án.
- **Phiên bản đã ghi**: định danh phiên bản thư viện mà dự án dùng; thay đổi có chủ đích.
- **Phong cách riêng**: phong cách người dùng sở hữu, cùng định dạng với phong cách thư viện; được lưu trong dự án.
- **Phim**: một thư mục dự án phim gồm nguồn và kết quả; chỉ nằm trên máy.
- **Video tham chiếu**: video tải về để học phong cách; chỉ nằm trên máy, không bao giờ chia sẻ.
- **Công cụ hệ thống**: phần mềm cần có trên máy, mỗi cái có phiên bản tối thiểu.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Trên máy đã có đủ công cụ và có mạng, người dùng đi từ bản sao mới tới trạng thái "sẵn sàng" bằng **1 lệnh**, trong **dưới 5 phút**.
- **SC-002**: Chạy lại lệnh chuẩn bị khi đã sẵn sàng hoàn tất trong **dưới 10 giây** và **không tải** dữ liệu thư viện nào.
- **SC-003**: Lệnh kiểm tra trả kết quả trong **dưới 5 giây**.
- **SC-004**: **100%** công cụ thiếu hoặc quá cũ được liệt kê, mỗi cái có phiên bản cần.
- **SC-005**: Sau khi tạo thử một phim và một video tham chiếu, version control báo **0** file mới cần đưa vào từ các thư mục đó.
- **SC-006**: Sau khi chạy lệnh chuẩn bị và lệnh kiểm tra, thư viện có **0** thay đổi cục bộ.
- **SC-007**: Với 3 yêu cầu mẫu (mỗi luồng một yêu cầu), hướng dẫn dẫn tới đúng luồng **3/3**.

## Assumptions

- Thư viện phong cách là lemo-opuscar (theo hiến pháp). Danh sách công cụ hệ thống và phiên bản tối thiểu lấy theo yêu cầu của thư viện đó tại phiên bản đã ghi.
- Lệnh chuẩn bị chỉ lo thư viện và báo công cụ. Cài các gói phụ của thư viện (giọng đọc, nhạc…) vẫn theo hướng dẫn của thư viện khi phim cần.
- Phong cách riêng được lưu trong dự án thay vì thư mục chung của người dùng, để đi cùng repo.
- Phim không được đưa vào version control (kể cả mã nguồn phim) trong tính năng này. Lưu phim lâu dài là việc của một tính năng sau nếu cần.
- Người dùng chạy trên macOS, Linux hoặc WSL; Windows thuần không được hỗ trợ (theo thư viện).
- Luồng học phong cách là tính năng 002, nằm ngoài phạm vi.
