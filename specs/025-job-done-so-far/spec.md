# Feature Specification: Phần đã xong trên trang việc làm phim

**Feature Branch**: `025-job-done-so-far`

**Created**: 2026-11-18

**Status**: Draft

**Input**: User description: "Khu 'Done so far' trên trang việc làm phim: trong lúc phim đang làm, chủ phim xem được các phần đã xong, theo bố cục mẫu đã duyệt 2026-11-18. Hàng nút theo bước; Script, Voice, Shots, Mix, Render với các số và nội dung đã liệt kê; chỉ đọc file trong thư mục phim của việc đó; online chỉ chủ phim và chủ xưởng xem; local, online và app đều chạy; trang tự cập nhật; chỉ xem, không sửa."

## Bối cảnh

Ngày 2026-11-18, khi làm phim `pause-ten-seconds` (khoảng 10 phút), kịch bản, 339 dòng giọng, 175 cảnh và bản trộn đã xong từ hơn một giờ, nhưng trang việc chỉ hiện bước hiện tại, bảng kiểm theo tầng và đường tới phim (chỉ xem được khi có video cuối). Chủ xưởng phải hỏi trong chat để biết phim tới đâu và không nghe, không xem được phần nào.

Bố cục đã được chủ xưởng duyệt trên một trang mẫu dùng dữ liệu thật của phim đó (2026-11-18). Phần tiến độ N/M của bước đang chạy đã làm ở nhánh trước (việc A).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Xem kịch bản, nghe giọng và bản trộn khi phim đang làm (Priority: P1)

Chủ phim mở trang việc của một phim đang làm. Dưới "Current step" có khu "Done so far" với một hàng nút theo bước. Bấm "Script" thấy điểm và đoạn đầu kịch bản, mở được toàn bộ kịch bản, nguồn và nhận xét biên tập. Bấm "Voice" thấy bảng từng dòng và nghe được từng dòng. Bấm "Mix" nghe được bản trộn.

**Why this priority**: kịch bản và giọng xong sớm nhất và là chỗ chủ phim hay muốn kiểm (đọc sai tên, số liệu sai); nghe được sớm là sửa được sớm, trước khi tốn thời gian dựng hình.

**Independent Test**: với một phim đã có kịch bản, giọng và bản trộn nhưng chưa dựng hình, mở trang việc và kiểm từng mục.

**Acceptance Scenarios**:

1. **Given** phim có kịch bản đã đạt, **When** chủ phim bấm "Script", **Then** thấy điểm máy chấm, điểm biên tập và số vòng sửa, số chữ, số đoạn, độ dài đích, số nguồn và 9 đoạn đầu; bấm "Open the full script" thấy toàn bộ; bấm "Sources" thấy danh sách nguồn; bấm nhận xét biên tập thấy nhận xét từng vòng.
2. **Given** phim có 339 dòng giọng, **When** bấm "Voice", **Then** thấy số dòng, giọng và tốc độ, kết quả kiểm giọng, và bảng dòng theo từng nhóm đoạn; mỗi dòng có nút nghe, mã dòng, mã đoạn, chữ và độ dài.
3. **Given** có 12 dòng đọc theo cách viết khác, **When** bật lọc "Respelled only", **Then** chỉ còn 12 dòng đó, mỗi dòng hiện thêm "Read as: …".
4. **Given** đã có bản trộn, **When** bấm "Mix", **Then** nghe được bản trộn từ đầu tới cuối và thấy độ dài của nó.
5. **Given** một bước chưa tới (ví dụ Self-check), **Then** nút của bước đó mờ và bấm không được.

---

### User Story 2 - Xem cảnh và tiến độ dựng hình (Priority: P2)

Chủ phim bấm "Shots" để xem các bảng ảnh cảnh hoặc từng cảnh kèm cỡ cảnh và bối cảnh, bấm vào ảnh để phóng to. Khi đang dựng hình, nút "Render" nhấp nháy kèm phần trăm, và mục Render hiện lưới các đoạn đã ghi, đang ghi, chưa ghi.

**Why this priority**: cảnh và dựng hình đến sau giọng; xem được bảng ảnh giúp phát hiện cảnh tối, cảnh mờ trước khi dựng xong.

**Independent Test**: với một phim đã qua kiểm cảnh và đang dựng hình, mở trang việc và kiểm "Shots" và "Render".

**Acceptance Scenarios**:

1. **Given** phim có 175 cảnh và 5 bảng ảnh, **When** bấm "Shots", **Then** thấy số cảnh, kết quả kiểm kế hoạch và kiểm cảnh (kèm số cảnh báo đã chấp nhận), số khung phụ, và bảng ảnh 1; chọn được bảng 1–5.
2. **Given** chế độ "Shot by shot", **Then** thấy 24 cảnh đầu, mỗi cảnh có ảnh, mã cảnh, cỡ cảnh và bối cảnh; bấm "Show more" thêm 24 cảnh nữa; bấm vào ảnh thì phóng to, bấm lần nữa thì đóng.
3. **Given** đang dựng hình 21/61 đoạn, **Then** nút "Render" nhấp nháy kèm "34%"; mục Render hiện 61 ô (21 đã ghi, các ô đang ghi, phần còn lại chưa ghi), số đoạn, và dựng bằng GPU hay phần mềm.
4. **Given** dựng hình đã xong, **Then** nút "Render" có chấm xanh và mục Render hiện đủ ô đã ghi.

---

### User Story 3 - Tự cập nhật và an toàn (Priority: P3)

Trang tự cập nhật khi có phần mới xong, không phải tải lại. Ở chế độ online, chỉ chủ phim và chủ xưởng xem được phần đã xong; không ai đọc được tệp ngoài thư mục phim của việc đó.

**Why this priority**: tự cập nhật là tiện; an toàn là bắt buộc nhưng đi kèm cách xưởng đã kiểm quyền với các trang khác.

**Independent Test**: mở trang việc, cho một bước mới xong, xem nút đổi màu; dùng tài khoản khác và đường dẫn có `..` để thử đọc tệp.

**Acceptance Scenarios**:

1. **Given** trang đang mở và giọng vừa xong, **When** chờ tối đa 10 giây, **Then** nút "Voice" chuyển sang chấm xanh mà không cần tải lại.
2. **Given** chế độ online, **When** một thành viên khác (không phải chủ phim, không phải chủ xưởng) mở phần đã xong của phim đó, **Then** bị từ chối như với trang việc.
3. **Given** một yêu cầu đọc tệp có `..`, đường dẫn tuyệt đối, hoặc tệp là liên kết trỏ ra ngoài thư mục phim, **Then** bị từ chối và không lộ nội dung tệp.
4. **Given** một yêu cầu đọc tệp không thuộc các loại được xem (ví dụ tệp cấu hình kênh), **Then** bị từ chối.

---

### Edge Cases

- Phim cũ (trước specs/010) không có kịch bản đã chấm: nút "Script" vẫn bấm được nếu có `SCRIPT.md`, các số không có thì hiện "—".
- Phim không có lời đọc: "Script" và "Voice" hiện "No narration" và mờ.
- Bảng ảnh chưa có (chưa chạy kiểm cảnh): "Shots" mờ.
- Bản trộn đang được ghi dở: "Mix" chỉ xanh khi tệp trộn đã xong (bước Mix đã qua hoặc tệp không đổi trong 5 giây).
- Kịch bản rất dài: đoạn đầu chỉ hiện 9 đoạn; bản đầy đủ cuộn trong khung.
- Phim ở chế độ app: phần đã xong đọc từ thư mục phim của việc trong kho dữ liệu của app.
- Việc không phải làm phim (học phong cách, chọn đề): không có khu "Done so far".

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Trang việc làm phim PHẢI có khu "Done so far" ngay dưới "Current step", gồm hàng nút Script, Voice, Shots, Mix, Render, Self-check, Publish.
- **FR-002**: Mỗi nút PHẢI có một trong ba trạng thái: đã xong (chấm xanh, bấm được), đang chạy (chấm nhấp nháy, kèm % khi có N/M), chưa tới (mờ, bấm không được). Trạng thái lấy từ các tệp đã có trong thư mục phim và bước hiện tại của việc.
- **FR-003**: Mục Script PHẢI hiện: điểm máy chấm, điểm biên tập và số vòng sửa, số chữ, số đoạn, độ dài đích, số nguồn, tiêu đề và 9 đoạn đầu kèm ghi chú đạo diễn; và cho mở toàn bộ kịch bản, danh sách nguồn, nhận xét biên tập từng vòng.
- **FR-004**: Mục Voice PHẢI hiện: số dòng, giọng và tốc độ, kết quả kiểm giọng, số dòng đọc theo cách viết khác, và bảng dòng chia theo nhóm đoạn (mỗi lần một nhóm, chuyển nhóm được) với nút nghe, mã dòng, mã đoạn, chữ, độ dài; lọc "Respelled only" hiện "Read as: …".
- **FR-005**: Mục Shots PHẢI hiện: số cảnh, kết quả kiểm kế hoạch và kiểm cảnh, số cảnh báo đã chấp nhận, số khung phụ; chế độ bảng ảnh (chọn bảng) và chế độ từng cảnh (24 cảnh mỗi lần, ảnh, mã, cỡ cảnh, bối cảnh); phóng to khi bấm ảnh.
- **FR-006**: Mục Mix PHẢI cho nghe toàn bộ bản trộn và hiện độ dài.
- **FR-007**: Mục Render PHẢI hiện lưới các đoạn (đã ghi, đang ghi, chưa ghi), số đoạn đã ghi trên tổng, và dựng bằng GPU hay phần mềm.
- **FR-008**: Khu PHẢI tự cập nhật khi việc có thay đổi, trong tối đa 10 giây, không tải lại trang và không làm mất mục đang mở.
- **FR-009**: Xưởng PHẢI chỉ trả tệp nằm trong thư mục phim của việc đó, thuộc danh sách loại được xem (kịch bản, nguồn, nhận xét biên tập, danh sách dòng, giọng, bản trộn, bảng ảnh và ảnh cảnh, nhãn cảnh, kết quả kiểm, tiến độ dựng hình); từ chối `..`, đường dẫn tuyệt đối và liên kết trỏ ra ngoài.
- **FR-010**: Ở chế độ online, chỉ chủ phim và chủ xưởng xem được phần đã xong, theo cùng luật quyền của trang việc. Ở chế độ local và app, theo luật của giao diện local hiện có.
- **FR-011**: Khu chỉ để xem: không có nút sửa, xoá hay chạy lại.
- **FR-012**: Khu PHẢI chạy ở cả ba chế độ: local (chat), online và app.

### Key Entities

- **Tóm tắt phần đã xong** của một việc: trạng thái từng bước và các số của từng mục (điểm, số dòng, số cảnh, độ dài, số đoạn dựng), tính từ thư mục phim.
- **Tệp xem được**: một tệp trong thư mục phim thuộc danh sách loại cho phép, đọc theo đường dẫn tương đối.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Với phim `pause-ten-seconds` (đã xong kịch bản, 339 dòng giọng, 175 cảnh, bản trộn), các số hiện trên trang khớp 100 % với tệp của phim (điểm 10/10 và 8,0/10, 2 vòng sửa, 339 dòng, 12 dòng đọc khác, 175 cảnh, 5 bảng ảnh, độ dài bản trộn 10:06).
- **SC-002**: Nghe được bất kỳ dòng nào trong 339 dòng và toàn bộ bản trộn; mỗi dòng bắt đầu phát trong dưới 1 giây sau khi bấm.
- **SC-003**: Khi một bước mới xong, nút của bước đó đổi trạng thái trong tối đa 10 giây mà không tải lại trang.
- **SC-004**: 100 % yêu cầu đọc tệp ngoài thư mục phim, ngoài danh sách loại cho phép, hoặc từ tài khoản không có quyền bị từ chối (test tự động có ít nhất các ca `..`, đường dẫn tuyệt đối, liên kết ra ngoài, loại không cho phép, thành viên khác).
- **SC-005**: Trang việc mở xong khu "Done so far" (mục Script) trong dưới 2 giây với phim 175 cảnh; chế độ từng cảnh chỉ tải 24 ảnh mỗi lần.
- **SC-006**: Các bộ test hiện có của xưởng vẫn đạt.

## Assumptions

- Bố cục, chữ trên nút và thứ tự mục theo trang mẫu đã duyệt 2026-11-18; tên nút và nhãn bằng tiếng Anh như phần còn lại của giao diện.
- "Self-check" và "Publish" trong bản này chỉ có trạng thái nút; nội dung của chúng đã có ở bảng kiểm theo tầng và mục Publish hiện có.
- Dữ liệu lấy từ các tệp mà quy trình làm phim đã ghi (không thêm bước ghi mới vào quy trình), trừ tiến độ dựng hình đã có trong nhật ký dựng.
- Không xem được phim đã xong của người khác qua khu này hơn những gì trang việc đã cho phép.
- Không làm bản cho điện thoại riêng; trang vẫn dùng được ở bề ngang hẹp như phần còn lại của giao diện.
