# Feature Specification: Học phong cách từ video tham chiếu (Style Learning)

**Feature Branch**: `002-style-learning`
**Created**: 2026-11-05
**Status**: Draft
**Input**: User description: "Skill học phong cách (style learning). Người dùng đưa một kênh YouTube (hoặc danh sách link video, hoặc file video có sẵn trên máy) và muốn xưởng học được "phong cách" của kênh đó để làm phim mới cùng phong cách nhưng nội dung của riêng mình. Theo phương pháp của claude-animated-shorts: thu thập 10–20 video gần nhất kèm tiếng gốc; xem đủ mọi khung hình chứ không lấy mẫu vài khung; đo bằng công cụ (chuyển động camera, cắt cảnh, màu sắc/độ sáng/tương phản/bão hoà, âm thanh: độ lớn, tốc độ đọc, khoảng lặng; lời thoại để tìm công thức kịch bản); phân tích theo nhiều khía cạnh (màu, viền, ánh sáng, chất liệu, nhân vật, chiều sâu, chuyển động, âm thanh, kịch bản); kiểm tra chéo số liệu với mắt nhìn và sửa kết luận sai; viết thành phong cách theo khung 11 mục của thư viện (mỗi luật kèm con số); chứng minh bằng một khung hình vẽ bằng code đặt cạnh khung gốc; làm phim demo 15–30 giây với chủ đề khác kênh gốc; lưu vào my-styles/ để dùng như phong cách thư viện. Người dùng duyệt 2 lần: sau bản phong cách và sau khung hình so sánh. Bản quyền: video tham chiếu chỉ học nội bộ, không commit, không đăng lại, không nêu tên kênh trong phim, không sao chép kịch bản hay nhân vật."

## Clarifications

### Session 2026-11-06

- Q: Nguồn video tham chiếu? → A: Cả hai: xưởng tự tải từ link kênh hoặc link video, và vẫn nhận file người dùng đặt sẵn trong thư mục tham chiếu.
- Q: Giới hạn độ dài video? → A: Mọi độ dài. Video ≤ 3 phút đo toàn bộ; video dài hơn đo một đoạn đại diện (mặc định 3 phút gồm phần mở đầu và các đoạn rải đều), đo đủ mọi khung trong đoạn đó.
- Q: Phim demo có thuộc tính năng này không? → A: Không. Tách thành tính năng riêng; tính năng này kết thúc ở phong cách đã lưu cùng khung chứng minh.
- Q: Bước phân tích 9 khía cạnh nên do nhiều agent song song hay một agent làm lần lượt? → A: 3 agent song song, mỗi agent một nhóm: hình (màu, viền, ánh sáng, chất liệu, nhân vật), chuyển động và chiều sâu, âm thanh và kịch bản.
- Q: Bản phong cách viết bằng ngôn ngữ nào? → A: `STYLE.md` (và các file phong cách khác) bằng tiếng Anh để khớp thư viện; mọi bản tóm tắt trình người dùng duyệt bằng tiếng Việt (ngôn ngữ người dùng).
- Q: Sau khi lưu phong cách, làm gì với video và âm thanh tham chiếu đã tải? → A: Hỏi người dùng một lần ở cuối, mặc định xoá; số liệu đo dạng số luôn được giữ cùng phong cách.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Đo bộ video tham chiếu (Priority: P1)

Người dùng có một bộ video tham chiếu của một kênh. Họ yêu cầu xưởng "đo" bộ video đó. Xưởng xem **mọi khung hình** của từng video, nghe toàn bộ âm thanh, chép lời, và trả về **hồ sơ đo**: số liệu theo từng video và số liệu tổng hợp cho cả bộ, cùng các bảng ảnh khung hình để người và Claude nhìn lại.

**Why this priority**: Mọi kết luận về phong cách phải dựa trên số đo (hiến pháp VIII). Không có hồ sơ đo thì không có gì để viết phong cách. Hồ sơ đo cũng có giá trị riêng: người dùng hiểu kênh đó làm như thế nào.

**Independent Test**: Đưa 3 video mẫu có đặc điểm biết trước (ví dụ một video có đúng 2 lần cắt cảnh, một video có camera đứng yên, một video có giọng đọc với tốc độ đã biết) và kiểm tra hồ sơ đo phản ánh đúng các đặc điểm đó.

**Acceptance Scenarios**:

1. **Given** một bộ video tham chiếu đã có trên máy, **When** người dùng yêu cầu đo, **Then** xưởng tạo hồ sơ đo gồm, cho từng video: độ dài, kích thước khung, tốc độ khung; chuyển động camera theo từng khung; vị trí các lần cắt cảnh; độ sáng, tương phản, độ bão hoà và bảng màu chủ đạo; độ lớn âm thanh, tốc độ đọc, tổng thời gian lặng; bản chép lời có mốc thời gian.
2. **Given** hồ sơ đo đã có, **When** người dùng xem tổng hợp, **Then** thấy giá trị điển hình (trung vị) và khoảng (thấp nhất – cao nhất) của mỗi chỉ số trên cả bộ.
3. **Given** một video có tiếng bị lồng sang ngôn ngữ khác, **When** thu thập, **Then** xưởng lấy **tiếng gốc**; nếu không xác định được tiếng gốc thì ghi rõ trong hồ sơ.
4. **Given** một video bị lỗi hoặc không đọc được, **When** đo, **Then** video đó được ghi là bỏ qua kèm lý do, các video còn lại vẫn được đo.

---

### User Story 2 - Viết phong cách từ hồ sơ đo (Priority: P2)

Từ hồ sơ đo, xưởng phân tích bộ video theo từng khía cạnh (màu, viền, ánh sáng, chất liệu, nhân vật, chiều sâu, chuyển động, âm thanh, kịch bản), **kiểm tra chéo** số liệu với mắt nhìn trên các bảng ảnh, sửa những kết luận sai, rồi viết thành **bản phong cách** theo khung 11 mục của thư viện. Người dùng **duyệt lần 1**.

**Why this priority**: Bản phong cách là sản phẩm chính, nhưng cần hồ sơ đo của P1.

**Independent Test**: Với hồ sơ đo của một bộ video, bản phong cách có đủ 11 mục; mỗi luật có ít nhất một bằng chứng (con số từ hồ sơ hoặc khung hình cụ thể); có mục ghi các kết luận đã bị sửa sau kiểm tra chéo.

**Acceptance Scenarios**:

1. **Given** hồ sơ đo đầy đủ, **When** xưởng viết phong cách, **Then** bản phong cách có đủ 11 mục của khung thư viện và mỗi luật dẫn tới bằng chứng.
2. **Given** một kết luận ban đầu mâu thuẫn với số đo hoặc với khung hình khi nhìn lại, **When** kiểm tra chéo, **Then** kết luận được sửa và việc sửa được ghi lại (trước, sau, bằng chứng).
3. **Given** bản phong cách hoàn chỉnh, **When** trình cho người dùng, **Then** xưởng dừng lại chờ duyệt và chỉ đi tiếp khi người dùng đồng ý; góp ý được áp dụng rồi trình lại.
4. **Given** công thức kịch bản của kênh, **When** viết phong cách, **Then** chỉ ghi **cấu trúc** (ví dụ: câu mở đầu dạng nghịch lý, số nhịp leo thang, cụm từ chuyển ý) và tốc độ đọc, **không** chép câu thoại, tên nhân vật hay tên kênh.

---

### User Story 3 - Chứng minh và lưu phong cách (Priority: P3)

Xưởng vẽ **một khung hình bằng code** theo bản phong cách, đặt **cạnh một khung gốc** tương ứng, và đo khoảng cách giữa hai khung theo các chỉ số của hồ sơ. Người dùng **duyệt lần 2**. Khi đạt, phong cách được lưu vào thư mục phong cách riêng của dự án, theo đúng định dạng phong cách của thư viện, và từ đó dùng được trong luồng làm phim.

**Why this priority**: Chứng minh phong cách dựng lại được bằng code; nhưng cần bản phong cách đã duyệt của P2.

**Independent Test**: Lưu một phong cách đã duyệt, rồi yêu cầu luồng làm phim liệt kê phong cách: phong cách mới xuất hiện trong nhóm phong cách riêng.

**Acceptance Scenarios**:

1. **Given** bản phong cách đã duyệt, **When** xưởng dựng khung hình chứng minh, **Then** người dùng nhận một ảnh ghép (gốc bên trái, dựng lại bên phải) kèm bảng chênh lệch các chỉ số.
2. **Given** chênh lệch vượt ngưỡng ở SC-004, **When** sau tối đa 2 vòng sửa vẫn chưa đạt, **Then** xưởng nói rõ chỉ số nào chưa đạt và vì sao, và hỏi người dùng chấp nhận hay dừng.
3. **Given** người dùng duyệt lần 2, **When** lưu, **Then** phong cách nằm trong thư mục phong cách riêng, có trong danh mục phong cách riêng, và không chứa video hay âm thanh tham chiếu nào.

---

### Edge Cases

- Kênh có ít hơn số video mặc định: dùng hết số video có, báo rõ, và cảnh báo nếu dưới 5 video (kết luận kém tin cậy).
- Bộ video trộn nhiều định dạng (dọc và ngang, nhiều kích thước): đo được tất cả; tổng hợp tách theo định dạng và báo định dạng chiếm đa số.
- Video không có lời (chỉ nhạc): bỏ qua phần kịch bản và tốc độ đọc cho video đó, ghi rõ.
- Bộ video không đồng nhất phong cách (kênh đổi phong cách theo thời gian): báo phân tán lớn ở các chỉ số và đề nghị người dùng chọn nhóm video.
- Tiếng lồng hoặc phụ đề cháy vào hình: ghi nhận; phụ đề cháy không được tính là "chữ trong phong cách" trừ khi người dùng xác nhận.
- Hết dung lượng đĩa giữa chừng: dừng sạch, giữ phần đã đo, chạy lại thì đo tiếp phần còn thiếu.
- Tên kênh hoặc tên nhân vật lọt vào bản phong cách: kiểm tra trước khi lưu và chặn.

## Requirements *(mandatory)*

### Functional Requirements

**Thu thập**
- **FR-001**: Xưởng MUST nhận bộ video tham chiếu từ (a) link một kênh, (b) danh sách link video, hoặc (c) file người dùng đã đặt trong thư mục tham chiếu; được trộn (a)/(b) với (c).
- **FR-001a**: Trước khi tự tải, xưởng MUST nói rõ sẽ tải bao nhiêu video, từ đâu, và nhắc người dùng chịu trách nhiệm về quyền sử dụng. Nếu môi trường chặn nền tảng video, xưởng MUST báo rõ và đề nghị người dùng đặt file vào thư mục tham chiếu.
- **FR-002**: Khi nhận từ một kênh, xưởng MUST lấy mặc định 12 video gần nhất (người dùng đổi được, trong khoảng 3–30).
- **FR-003**: Xưởng MUST ưu tiên tiếng gốc của video và ghi lại tiếng đã dùng.
- **FR-004**: Video và âm thanh tham chiếu MUST chỉ nằm trong thư mục tham chiếu của dự án, MUST NOT vào version control, MUST NOT bị gửi đi hay đăng lại.
- **FR-004a**: Sau khi lưu phong cách, xưởng MUST hỏi người dùng một lần có giữ video và âm thanh tham chiếu của bộ đó không; mặc định (người dùng không chọn giữ) là **xoá**. Chỉ xoá file thuộc bộ tham chiếu vừa học. Số liệu đo dạng số không bị xoá.

**Đo**
- **FR-005**: Xưởng MUST phân tích **100%** khung hình của **phần được đo** của mỗi video. Video ≤ 3 phút: phần được đo là toàn bộ video. Video > 3 phút: phần được đo là một đoạn đại diện tổng cộng 3 phút (người dùng đổi được), gồm 60 giây đầu và các đoạn rải đều trong phần còn lại; hồ sơ MUST ghi rõ các đoạn đã đo.
- **FR-006**: Cho mỗi khung, xưởng MUST đo: độ dịch chuyển camera so với khung trước; có phải lần cắt cảnh không; độ sáng trung bình, độ tương phản, độ bão hoà; phần trăm điểm ảnh rất tối và rất sáng.
- **FR-007**: Cho mỗi video, xưởng MUST đo: bảng màu chủ đạo (6 màu lớn nhất kèm tỷ lệ; ít hơn chỉ khi phần được đo có ít hơn 6 màu phân biệt được, và ghi rõ); số lần cắt cảnh và độ dài trung bình mỗi cảnh; tỷ lệ khung camera đứng yên; độ lớn âm thanh tổng thể; tốc độ đọc (từ/giây); tổng thời gian lặng; thời điểm lời đầu tiên.
- **FR-008**: Xưởng MUST chép lời mỗi video kèm mốc thời gian từng từ, bằng ngôn ngữ gốc.
- **FR-009**: Xưởng MUST tạo bảng ảnh: mỗi 2 giây video thành một ảnh ghép đủ mọi khung trong 2 giây đó, để nhìn lại được mọi khung.
- **FR-010**: Hồ sơ đo MUST có tổng hợp cho cả bộ: trung vị, thấp nhất, cao nhất của mỗi chỉ số.
- **FR-011**: Việc đo MUST tiếp tục được sau khi bị ngắt: video đã đo xong không đo lại.

**Phân tích và viết phong cách**
- **FR-012**: Xưởng MUST phân tích theo 9 khía cạnh: màu, viền, ánh sáng, chất liệu, nhân vật, chiều sâu, chuyển động, âm thanh, kịch bản; mỗi khía cạnh một báo cáo riêng có bằng chứng. Việc phân tích MUST chia thành 3 nhóm chạy song song, mỗi nhóm một agent: **hình** (màu, viền, ánh sáng, chất liệu, nhân vật), **chuyển động và chiều sâu**, **âm thanh và kịch bản**.
- **FR-013**: Xưởng MUST kiểm tra chéo mỗi kết luận với số đo **và** với bảng ảnh; kết luận sai MUST được sửa và ghi vào nhật ký sửa (trước, sau, bằng chứng).
- **FR-014**: Bản phong cách MUST theo khung 11 mục của thư viện; mỗi luật MUST dẫn tới ít nhất một con số trong hồ sơ đo hoặc một khung hình cụ thể.
- **FR-015**: Bản phong cách MUST NOT chứa tên kênh, tên người, tên nhân vật, câu thoại nguyên văn hay tiêu đề video của kênh gốc. Xưởng MUST kiểm tra điều này trước khi trình duyệt và trước khi lưu.
- **FR-016**: Xưởng MUST dừng chờ người dùng duyệt bản phong cách (duyệt lần 1) trước khi chứng minh.
- **FR-016a**: Bản phong cách và các file của phong cách MUST viết bằng tiếng Anh (như phong cách thư viện). Mọi bản tóm tắt trình người dùng duyệt (lần 1 và lần 2) MUST viết bằng ngôn ngữ của người dùng, mặc định tiếng Việt.

**Chứng minh và lưu**
- **FR-017**: Xưởng MUST dựng một khung hình bằng code theo bản phong cách và tạo ảnh ghép gốc–dựng lại kèm bảng chênh lệch các chỉ số của FR-006 và bảng màu.
- **FR-018**: Xưởng MUST cho tối đa 2 vòng sửa khung chứng minh; sau đó báo rõ chỉ số chưa đạt và để người dùng quyết định.
- **FR-019**: Xưởng MUST dừng chờ người dùng duyệt khung chứng minh (duyệt lần 2) trước khi lưu.
- **FR-020**: Khi lưu, phong cách MUST nằm trong thư mục phong cách riêng của dự án theo định dạng phong cách của thư viện, kèm hồ sơ bằng chứng dạng số (không kèm media tham chiếu), và MUST được thêm vào danh mục phong cách riêng.
- **FR-021**: Tên và mã của phong cách MUST NOT trùng phong cách thư viện hoặc phong cách riêng đã có, và MUST NOT chứa tên kênh gốc.
- **FR-022**: Sau khi lưu, luồng làm phim MUST tìm thấy và dùng được phong cách mới như một phong cách riêng.

### Key Entities

- **Bộ tham chiếu**: tập video của một kênh, mỗi video có nguồn, tiếng đã dùng, trạng thái (đã đo / bỏ qua kèm lý do). Chỉ nằm trên máy.
- **Hồ sơ đo**: số liệu theo khung, theo video, và tổng hợp cả bộ; bản chép lời; bảng ảnh. Số liệu dạng số được giữ cùng phong cách; bảng ảnh và media thì không.
- **Báo cáo khía cạnh**: kết luận cho một trong 9 khía cạnh, mỗi kết luận có bằng chứng.
- **Nhật ký sửa**: các kết luận đã sửa sau kiểm tra chéo.
- **Bản phong cách**: 11 mục theo khung thư viện; mỗi luật có bằng chứng.
- **Khung chứng minh**: ảnh ghép gốc–dựng lại và bảng chênh lệch.
- **Phong cách riêng đã lưu**: bản phong cách, thông tin phong cách, bằng chứng dạng số, khung chứng minh đã duyệt; có trong danh mục phong cách riêng.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Hồ sơ đo phủ **100%** khung hình của phần được đo của mọi video: với video đo toàn bộ, số khung đã đo **bằng đúng** số khung của video; với video đo theo đoạn, mỗi đoạn lệch tối đa **±1 khung** do làm tròn ở điểm cắt.
- **SC-002**: Với bộ video kiểm thử có đặc điểm biết trước: phát hiện cắt cảnh đúng **≥ 95%** và báo nhầm **≤ 5%**; tốc độ đọc sai lệch **≤ 10%**; độ sáng trung bình sai lệch **≤ 0,02** (trên thang 0–1).
- **SC-003**: **100%** luật trong bản phong cách dẫn tới ít nhất một bằng chứng; **0** tên kênh, tên người, câu thoại nguyên văn trong bản phong cách.
- **SC-004**: Khung chứng minh so với khung gốc: chênh lệch độ sáng trung bình **≤ 0,05**, độ bão hoà trung vị **≤ 0,08**, tỷ lệ điểm ảnh rất tối **≤ 5 điểm phần trăm**, và **≥ 4/6** màu chủ đạo có màu gần tương ứng.
- **SC-005**: Đo một bộ khoảng 18 phút video (tương đương 20 video ngắn) hoàn tất trong **dưới 60 phút** trên máy thông thường, không tính thời gian tải.
- **SC-006**: Sau toàn bộ quy trình, version control có **0** file video hay âm thanh tham chiếu; khi người dùng không chọn giữ, thư mục tham chiếu còn **0** file của bộ vừa học.
- **SC-007**: Người dùng chỉ phải dừng duyệt **đúng 2 lần** trong quy trình (không tính câu hỏi ban đầu nếu thiếu thông tin và câu hỏi giữ hay xoá video tham chiếu ở cuối).
- **SC-008**: Phong cách đã lưu xuất hiện trong danh mục phong cách riêng và luồng làm phim chọn được nó **ngay lần đầu** gọi tên.

## Assumptions

- Người dùng chịu trách nhiệm về quyền sử dụng video tham chiếu; xưởng chỉ dùng chúng để học nội bộ và không phát tán.
- Bộ video tham chiếu thuộc một phong cách tương đối đồng nhất; nếu không, người dùng chọn nhóm video.
- Khung 11 mục và định dạng phong cách riêng lấy theo thư viện ở phiên bản đã ghim (tính năng 001).
- Mỗi agent phân tích chỉ đọc hồ sơ đo và bảng ảnh, và chỉ ghi báo cáo của nhóm mình (không sửa file của agent khác).
- Thời gian tải video và chép lời lần đầu (tải mô hình) không tính vào SC-005.
- Media chứng minh nặng không vào version control (theo `.gitignore` của 001); phong cách lưu phần nguồn và số liệu.
- Phim demo của phong cách nằm ngoài phạm vi; sẽ là một tính năng riêng, dùng luồng làm phim có sẵn.
- Tự tải chỉ chạy được ở môi trường cho phép truy cập nền tảng video (ví dụ máy người dùng); trong môi trường bị chặn, dùng file đặt sẵn.
