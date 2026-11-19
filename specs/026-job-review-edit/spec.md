# Feature Specification: Điểm duyệt và chỉnh sửa trên trang việc làm phim

**Feature Branch**: `026-job-review-edit`

**Created**: 2026-11-19

**Status**: Draft

**Input**: User description: "Điểm duyệt và chỉnh sửa trên trang việc làm phim. Thanh tiến trình theo các bước của xưởng; năm bước là điểm duyệt: Script, Voice, Shots (trước render), Mix, Publish. Ở mỗi điểm duyệt người dùng xem và sửa (kịch bản từng đoạn, giọng từng dòng, cảnh theo danh mục bộ dựng, nhạc và mức tiếng, tiêu đề và thumbnail). Giao diện không ghi file trực tiếp, chỉ gọi lệnh có kiểm tra của xưởng; đồ thị phụ thuộc cho biết bước nào phải làm lại; mỗi điểm duyệt là một yêu cầu duyệt, agent chờ; cổng trong code chặn bước sau khi chưa duyệt; duyệt gắn với nội dung lúc duyệt; online lưu trạng thái chờ và làm tiếp đúng bước. Bản xem trước giao diện: https://claude.ai/artifact/MxW7LE2jx1DMrYYMzJMNoD"

## Bối cảnh

Hiện tại chủ phim chỉ thấy phim khi đã dựng hình xong (khoảng 30 phút GPU cho phim 5 phút). Specs/025 cho xem các phần đã xong trong lúc làm, nhưng chỉ để đọc: thấy lỗi kịch bản hay một cảnh xấu thì phải hỏi trong chat, và agent có thể đã đi tiếp. Phim `anthropic-ipo-15` bị loại sau khi đã làm xong toàn bộ.

Ngày 2026-11-19, chủ xưởng duyệt bố cục trên một trang mẫu (đường dẫn ở trên): thanh tiến trình có nhãn `REVIEW` ở năm điểm duyệt, khung giữa đổi theo bước, cột "If you change this" chỉ các bước phải làm lại, và nút duyệt bị khoá khi còn lỗi.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Duyệt và sửa kịch bản trước khi tạo giọng (Priority: P1)

Agent viết xong kịch bản và qua máy chấm, rồi dừng. Trang việc báo "Waiting for you: Script". Chủ phim đọc từng đoạn kèm điểm và nhận xét biên tập, sửa một đoạn, bấm chạy kiểm, thấy điểm mới. Khi kiểm đạt, chủ phim bấm "Approve script"; agent làm tiếp bước Voice.

**Why this priority**: kịch bản là chỗ rẻ nhất để sửa và là gốc của mọi bước sau. Đây cũng là lát cắt nhỏ nhất chứng minh cả cơ chế: dừng, sửa có kiểm, duyệt, làm tiếp, và cổng chặn.

**Independent Test**: làm một phim tới hết bước Script; sửa một đoạn trên trang, chạy kiểm, duyệt; xác nhận agent làm tiếp Voice, và trước khi duyệt thì lệnh tạo giọng từ chối.

**Acceptance Scenarios**:

1. **Given** kịch bản đã qua máy chấm và biên tập, **When** agent tới điểm duyệt Script, **Then** trang việc hiện "Waiting for you: Script", bước Script có nhãn `REVIEW`, và agent không làm bước nào tiếp.
2. **Given** đang chờ duyệt Script, **When** chủ phim sửa đoạn 3 rồi bấm "Run script check", **Then** đoạn đó được lưu vào kịch bản, máy chấm chạy lại, trang hiện điểm mới và lỗi (nếu có) trong vòng 30 giây.
3. **Given** chủ phim đã mở ô sửa nhưng chưa chạy kiểm, hoặc kiểm chưa đạt, **Then** nút "Approve script" bị khoá và ghi lý do.
4. **Given** kiểm đạt, **When** chủ phim bấm "Approve script", **Then** yêu cầu duyệt được ghi là đã duyệt, trang báo bước Voice đang chạy, và agent làm tiếp.
5. **Given** kịch bản chưa được duyệt (hoặc đã sửa sau lần duyệt), **When** ai đó chạy lệnh tạo giọng, **Then** lệnh từ chối và ghi lệnh cần chạy.
6. **Given** đang chờ duyệt, **When** chủ phim trả lời trong khung chat thay vì trên trang, **Then** quyết định được ghi như duyệt trên trang (cách của specs/003).

---

### User Story 2 - Duyệt và sửa cảnh trước khi dựng hình (Priority: P2)

Sau kiểm cảnh (tầng 2), agent dừng ở điểm duyệt Shots. Chủ phim xem mỗi cảnh một ảnh kèm thời điểm và lời; đổi bối cảnh, cỡ máy hoặc động tác của một cảnh bằng lựa chọn từ danh mục của bộ dựng; giữ một cảnh lệch phong cách kèm lý do. Khi không còn lỗi mở, chủ phim bấm "Approve and render".

**Why this priority**: dựng hình là bước tốn thời gian nhất; duyệt cảnh trước đó tiết kiệm nhiều nhất sau kịch bản.

**Independent Test**: với một phim dùng bộ dựng đã qua kiểm cảnh, đổi máy của một cảnh, chờ kiểm lại, chấp nhận một cảnh báo phong cách, duyệt; xác nhận chỉ khi đó dựng hình mới chạy.

**Acceptance Scenarios**:

1. **Given** kiểm cảnh đã chạy, **When** chủ phim bấm "Shots", **Then** thấy ảnh của mọi cảnh (theo trang, 24 cảnh mỗi lần), mỗi cảnh có mã, thời điểm, lời, bối cảnh, máy, động tác, và nhãn lỗi hoặc cảnh báo của nó.
2. **Given** phim dùng bộ dựng, **When** chủ phim mở lựa chọn bối cảnh, máy hoặc động tác của một cảnh, **Then** chỉ thấy các tên có trong danh mục của bộ dựng (và các bối cảnh riêng phim đã khai báo); không có ô gõ tự do.
3. **Given** chủ phim chọn một giá trị mới, **When** xưởng kiểm bảng cảnh, **Then** nếu bảng cảnh không hợp lệ thì không lưu gì và trang báo lỗi kèm mã cảnh; nếu hợp lệ thì lưu, chạy lại kiểm kế hoạch và kiểm cảnh, và cảnh đó hiện nhãn "changed" tới khi kiểm xong.
4. **Given** một cảnh có cảnh báo phong cách, **When** chủ phim bấm "Keep it this way…" và nhập lý do, **Then** cảnh báo được chấp nhận kèm lý do (như `qc except` / `qc accept-style`); không có lý do thì không chấp nhận.
5. **Given** còn lỗi khung, cảnh báo chưa xử lý, hoặc cảnh vừa sửa chưa kiểm lại, **Then** nút "Approve and render" bị khoá và ghi lý do.
6. **Given** bảng cảnh chưa được duyệt hoặc đã đổi sau lần duyệt, **When** chạy lệnh dựng hình, **Then** cổng dựng hình từ chối và ghi lệnh cần chạy.

---

### User Story 3 - Nghe và sửa giọng từng dòng (Priority: P3)

Sau kiểm giọng (tầng 0), agent dừng ở điểm duyệt Voice. Chủ phim nghe từng dòng, sửa cách đọc một từ ("say"), làm lại một dòng, hoặc đổi giọng và tốc độ cho cả phim, rồi duyệt.

**Why this priority**: lỗi đọc sai tên riêng hay số liệu hay gặp, và sửa từng dòng rẻ hơn làm lại cả phim; nhưng tầng 0 đã bắt phần lớn lỗi.

**Independent Test**: với một phim đã tạo giọng, sửa "say" của một dòng, làm lại dòng đó, nghe lại, duyệt.

**Acceptance Scenarios**:

1. **Given** đã tạo giọng, **When** chủ phim bấm "Voice", **Then** thấy giọng và tốc độ của phim, và từng dòng có nút nghe, chữ, ô "say", kết quả kiểm tầng 0 của dòng đó.
2. **Given** chủ phim sửa "say" của dòng L17 và bấm "Remake line", **Then** chỉ dòng L17 được tạo lại, chữ hiển thị của dòng không đổi, và kiểm giọng chạy lại cho dòng đó.
3. **Given** chủ phim đổi giọng hoặc tốc độ, **Then** trang báo mọi dòng sẽ được tạo lại và cần xác nhận trước khi chạy.
4. **Given** chữ hiển thị của một dòng, **Then** không sửa được trên trang Voice; muốn đổi chữ thì phải sửa kịch bản (User Story 1).

---

### User Story 4 - Chọn nhạc và mức tiếng (Priority: P4)

Sau khi trộn tiếng, chủ phim chọn bài nhạc trong các lựa chọn xưởng soạn, chỉnh mức lời, nhạc dưới lời, nhạc giữa các nhịp và hiệu ứng, nghe lại bản trộn, rồi duyệt. Sửa ở đây không vẽ lại hình.

**Why this priority**: âm thanh ít khi làm hỏng phim và sửa rẻ, vì chỉ trộn và ghép tiếng lại.

**Independent Test**: với một phim đã trộn, đổi mức nhạc, nghe bản trộn mới, xác nhận phần hình đã dựng không bị dựng lại.

**Acceptance Scenarios**:

1. **Given** đã trộn tiếng, **When** chủ phim đổi bài nhạc hoặc một mức tiếng, **Then** bản trộn chạy lại và trang cho nghe bản mới.
2. **Given** phim đã dựng hình, **When** bản trộn đổi, **Then** chỉ bước ghép tiếng, Self-check và Publish phải làm lại; phần hình không bị dựng lại.
3. **Given** mức tiếng ngoài dải xưởng cho phép, **Then** trang từ chối và ghi dải cho phép.

---

### User Story 5 - Chọn tiêu đề và thumbnail (Priority: P5)

Sau Self-check, chủ phim xem ba tiêu đề và thumbnail của gói đăng, chọn một, sửa mô tả và hashtag, rồi duyệt; gói đăng được kiểm lại.

**Why this priority**: không ảnh hưởng tới phim, chỉ tới gói đăng.

**Independent Test**: với một phim đã có gói đăng, chọn tiêu đề thứ hai, sửa một hashtag, chạy kiểm gói đăng.

**Acceptance Scenarios**:

1. **Given** gói đăng đã tạo, **When** chủ phim chọn một tiêu đề, **Then** tiêu đề đó được ghi là tiêu đề chính trong gói đăng.
2. **Given** chủ phim sửa mô tả hoặc hashtag, **Then** gói đăng được kiểm lại theo luật của kênh; lỗi hiện kèm luật bị vi phạm.

---

### Cross-cutting: thanh tiến trình và "If you change this"

Áp dụng cho mọi user story.

**Acceptance Scenarios**:

1. **Given** một phim đang làm, **Then** trang việc có thanh tiến trình theo đúng thứ tự Treatment, Script, Voice, Look, Picture, Shots, Mix, Render, Self-check, Publish; mỗi bước hiện trạng thái (Done, Running, Waiting for you, Not yet, Must run again), và năm điểm duyệt có nhãn `REVIEW`.
2. **Given** chủ phim đang xem một bước có thể sửa, **Then** cột "If you change this" liệt kê các bước sẽ phải làm lại nếu sửa bước này.
3. **Given** chủ phim vừa sửa một bước đã xong, **Then** các bước phụ thuộc đã xong chuyển sang "Must run again", và các lần duyệt của chúng không còn hiệu lực.

### Edge Cases

- Chủ phim sửa kịch bản sau khi giọng đã được duyệt: duyệt Voice, kiểm kế hoạch, kiểm cảnh và duyệt Shots mất hiệu lực; chỉ những dòng có chữ đổi được tạo lại giọng.
- Agent đang chạy một bước dài (tạo giọng, dựng hình) đúng lúc chủ phim sửa bước trước đó: trang không cho sửa bước đã bị khoá bởi lệnh đang chạy, và ghi "Busy: <bước>".
- Hai người cùng mở trang (chủ phim và chủ xưởng): lần lưu thứ hai dựa trên nội dung cũ bị từ chối, và trang yêu cầu tải lại.
- Phim theo phong cách không có bộ dựng: Shots chỉ xem, chấp nhận cảnh báo kèm lý do và duyệt; không đổi được bối cảnh, máy hay động tác trên trang.
- Phim không có lời đọc: điểm duyệt Script và Voice được bỏ qua và ghi là "Skipped (no narration)".
- Ai đó sửa file trong thư mục phim bằng tay (ngoài trang): nội dung đổi làm lần duyệt mất hiệu lực, giống như sửa trên trang.
- Chế độ online, container của việc bị dừng trong lúc chờ duyệt (hết giờ, máy khởi động lại): khi có quyết định, việc được nhận lại và agent làm tiếp từ đúng điểm duyệt, không làm lại các bước đã xong.
- Chủ phim từ chối thay vì duyệt (kèm ghi chú): agent đọc ghi chú, sửa theo đó, rồi gửi lại yêu cầu duyệt của cùng điểm.
- Giao diện chưa cài (`deps ui` chưa chạy): luồng làm phim bằng chat duyệt trong khung chat như specs/003.

## Requirements *(mandatory)*

### Functional Requirements

**Thanh tiến trình và điểm duyệt**

- **FR-001**: Trang việc của một phim MUST hiện thanh tiến trình gồm mười bước theo thứ tự Treatment, Script, Voice, Look, Picture, Shots, Mix, Render, Self-check, Publish, mỗi bước có một trạng thái: Done, Running, Waiting for you, Not yet, Must run again, hoặc Skipped.
- **FR-002**: Năm bước Script, Voice, Shots, Mix, Publish MUST là điểm duyệt. Ở mỗi điểm duyệt, agent MUST gửi một yêu cầu duyệt thuộc loại riêng của điểm đó và không làm bước nào tiếp cho tới khi có quyết định. Điểm duyệt nào được bật cho một phim: mỗi kênh có mặc định riêng (kênh mới và kênh cũ chưa đặt: Script và Shots bật, Voice, Mix, Publish tắt), đặt bằng 5 ô đánh dấu trên trang kênh hoặc bằng lệnh `channel set <kênh> reviews …`; khi bắt đầu phim, 5 ô được đánh sẵn theo kênh và đổi được cho riêng phim đó; trong lúc làm, chủ phim bật hoặc tắt được một điểm chưa tới. Điểm tắt vẫn xem và sửa được trên trang nhưng agent không dừng ở đó.
- **FR-003**: Quyết định duyệt MUST nhận được từ trang việc, từ khung chat, và từ API/MCP (như specs/003, specs/009). Quyết định gồm duyệt hoặc từ chối, kèm ghi chú tuỳ chọn.
- **FR-004**: Khi bị từ chối, agent MUST đọc ghi chú, sửa bước đó, và gửi lại yêu cầu duyệt của cùng điểm.

**Chỉnh sửa có kiểm tra**

- **FR-005**: Trang MUST NOT ghi thẳng vào tệp của phim. Mọi thay đổi MUST đi qua một lệnh của xưởng có kiểm tra, và lệnh đó từ chối thay đổi không hợp lệ mà không ghi gì.
- **FR-006**: Script: chủ phim MUST sửa được từng đoạn của kịch bản; mỗi lần lưu, máy chấm kịch bản (theo luật, không gọi Claude) chạy lại và trả điểm cùng lỗi. Lượt biên tập độc lập không chạy lại vì sửa của chủ phim. Duyệt Script MUST bị khoá khi kiểm chưa đạt hoặc còn đoạn sửa chưa kiểm.
- **FR-007**: Lời đọc MUST được tạo từ kịch bản đã duyệt theo một chiều; chữ hiển thị của một dòng giọng MUST NOT sửa được ở bước Voice. Phép so lời đọc với kịch bản MUST chạy ở kiểm giọng (tầng 0), không chỉ ở tầng 4.
- **FR-008**: Voice: chủ phim MUST nghe được từng dòng, sửa được "say" của một dòng và làm lại đúng dòng đó, và đổi được giọng hoặc tốc độ của phim (có xác nhận vì mọi dòng sẽ làm lại). Giọng chỉ lấy từ danh sách giọng của thư viện.
- **FR-009**: Shots: với phim dùng bộ dựng, bảng cảnh MUST nằm trong một tệp dữ liệu tách khỏi mã của trang phim, để sửa cảnh không phải sửa mã.
- **FR-010**: Shots: lựa chọn bối cảnh, máy, động tác MUST chỉ gồm các tên trong danh mục của bộ dựng và các bối cảnh riêng phim đã khai báo. Trước khi lưu, xưởng MUST kiểm cả bảng cảnh bằng chính phép kiểm của bộ dựng; không hợp lệ thì không lưu và báo lỗi kèm mã cảnh.
- **FR-011**: Shots: chủ phim MUST giữ được một cảnh có lỗi khung cố ý (ngoại lệ từng cảnh) hoặc chấp nhận cảnh báo phong cách, và cả hai MUST có lý do không rỗng, ghi như `qc except` / `qc accept-style`.
- **FR-012**: Shots: duyệt MUST bị khoá khi còn lỗi khung chưa miễn, cảnh báo phong cách chưa chấp nhận, hoặc cảnh đã sửa mà kiểm cảnh chưa chạy lại.
- **FR-013**: Mix: chủ phim MUST chọn được bài nhạc trong các lựa chọn xưởng đã soạn cho phim và chỉnh được mức lời, nhạc dưới lời, nhạc giữa các nhịp và hiệu ứng trong dải xưởng cho phép; mỗi thay đổi chạy lại bản trộn và cho nghe bản mới.
- **FR-014**: Publish: chủ phim MUST chọn được một trong ba tiêu đề (kèm thumbnail của nó) làm tiêu đề chính, sửa được mô tả và hashtag; mỗi lần lưu, gói đăng được kiểm lại theo luật của kênh.

**Phụ thuộc và làm lại**

- **FR-015**: Xưởng MUST giữ một đồ thị phụ thuộc giữa các bước: Script → Voice → Picture (kế hoạch) → Shots → Render → Self-check → Publish; Voice → Mix; Mix chỉ ảnh hưởng ghép tiếng, Self-check và Publish, không ảnh hưởng hình đã dựng.
- **FR-016**: Khi nội dung một bước đổi (trên trang, bằng chat hay sửa tay), mọi bước phụ thuộc đã xong MUST chuyển sang "Must run again", và trang MUST hiện danh sách đó trong cột "If you change this" trước khi chủ phim lưu.
- **FR-016a**: Trang chỉ chạy các lệnh của chính bước đang sửa (kiểm kịch bản, tạo lại một dòng giọng và kiểm nó, kiểm kế hoạch và vẽ lại ảnh cảnh đã sửa, trộn lại, kiểm gói đăng). Các bước phụ thuộc bị "Must run again" do agent làm lại sau khi điểm duyệt được duyệt, theo thứ tự của đồ thị. Sửa một bước đã duyệt trong lúc phim đang chờ ở điểm sau MUST mở lại điểm duyệt của bước đó (nếu điểm đó đang bật).
- **FR-017**: Chỉ phần bị ảnh hưởng MUST được làm lại: sửa một đoạn kịch bản chỉ tạo lại giọng các dòng có chữ đổi; sửa một cảnh chỉ vẽ lại ảnh của cảnh đó ở kiểm cảnh; đổi bản trộn chỉ ghép tiếng lại, không dựng lại hình.

**Cổng và hiệu lực của lần duyệt**

- **FR-018**: Mỗi quyết định duyệt MUST ghi kèm dấu của nội dung lúc duyệt. Khi nội dung đó đổi, lần duyệt MUST mất hiệu lực và điểm duyệt quay về "Waiting for you" khi agent tới lại.
- **FR-019**: Lệnh tạo giọng MUST từ chối khi kịch bản chưa có lần duyệt còn hiệu lực; cổng dựng hình MUST từ chối khi bảng cảnh chưa có lần duyệt còn hiệu lực, ngoài các điều kiện của specs/020. Mỗi lời từ chối MUST ghi lý do và lệnh cần chạy.
- **FR-020**: Điểm duyệt bị tắt cho một phim (theo FR-002) MUST không chặn cổng của nó, và trang ghi bước đó là "Not reviewed".
- **FR-021**: Việc bỏ qua cổng (như `--skip-checks` của specs/020) MUST cần lý do và được ghi lại.

**Chờ và làm tiếp**

- **FR-022**: Trạng thái "đang chờ duyệt <điểm>" MUST được lưu trong sổ việc, không chỉ trong tiến trình của agent.
- **FR-023**: Ở chế độ online, trong lúc chờ duyệt việc MUST NOT giữ tài nguyên chạy (container, hạn mức Claude); khi có quyết định, worker MUST nhận lại việc và agent MUST làm tiếp từ đúng điểm duyệt, không làm lại các bước đã xong.
- **FR-024**: Khi một bước đang chạy, trang MUST khoá sửa các bước mà bước đó đang dùng và ghi "Busy: <bước>".
- **FR-025**: Một lần lưu dựa trên nội dung cũ hơn nội dung hiện tại MUST bị từ chối, và trang yêu cầu tải lại.

**Quyền và chế độ**

- **FR-026**: Ở chế độ online và app (Host/Client), chỉ chủ phim và chủ xưởng MUST xem và sửa được ở các điểm duyệt (như specs/025); người khác nhận lỗi không có quyền.
- **FR-027**: Tính năng MUST chạy ở chế độ local, online và app. Khi chưa cài giao diện, luồng chat MUST duyệt trong khung chat như cũ.
- **FR-028**: Trang MUST tự cập nhật trạng thái các bước và kết quả kiểm mà không phải tải lại (như specs/025).

### Key Entities

- **Điểm duyệt (Review point)**: một trong năm bước Script, Voice, Shots, Mix, Publish của một phim; có trạng thái (bật/tắt, đang chờ, đã duyệt, bị từ chối, mất hiệu lực).
- **Mặc định duyệt của kênh (Channel review defaults)**: năm cờ bật/tắt trong hồ sơ kênh; được chép vào phim khi bắt đầu, rồi đổi riêng cho phim.
- **Quyết định duyệt (Review decision)**: duyệt hoặc từ chối, ghi chú, người quyết định, nguồn (trang, chat, API), thời điểm, và dấu nội dung lúc duyệt. Mở rộng yêu cầu duyệt của specs/003.
- **Thay đổi (Edit)**: một lần sửa của chủ phim ở một bước: bước nào, phần nào (đoạn, dòng, cảnh, mức tiếng, tiêu đề), giá trị cũ và mới, kết quả kiểm, và danh sách bước phải làm lại.
- **Đồ thị phụ thuộc (Step graph)**: các bước và quan hệ phụ thuộc giữa chúng, cùng dấu nội dung của từng bước; dùng để tính "Must run again" và hiệu lực của lần duyệt.
- **Bảng cảnh (Scene table)**: danh sách cảnh của phim dùng bộ dựng (bối cảnh, máy, động tác, lời, thời gian), lưu tách khỏi mã trang phim.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Với một phim thử, chủ phim sửa một đoạn kịch bản và thấy điểm mới trong vòng 30 giây; sửa một cảnh và thấy ảnh mới của cảnh đó trong vòng 2 phút.
- **SC-002**: Trong bộ test, 100% lệnh tạo giọng và lệnh dựng hình chạy khi điểm duyệt tương ứng chưa có lần duyệt còn hiệu lực đều bị từ chối, kèm lệnh cần chạy.
- **SC-003**: Trong bộ test, 100% thay đổi không hợp lệ (tên ngoài danh mục, kịch bản làm lời đọc lệch, mức tiếng ngoài dải, lưu dựa trên nội dung cũ) bị từ chối và không đổi tệp nào của phim.
- **SC-004**: Sửa một đoạn kịch bản chỉ tạo lại giọng các dòng có chữ đổi (đo trên phim thử: số dòng tạo lại bằng số dòng đổi chữ); đổi bản trộn không dựng lại hình.
- **SC-005**: Ở chế độ online, một việc chờ duyệt không giữ container hay hạn mức nào; sau khi duyệt, việc chạy tiếp từ đúng điểm duyệt trong vòng 1 phút (khi worker rảnh).
- **SC-006**: Với phim 5 phút, chủ phim phát hiện và sửa được lỗi kịch bản hoặc cảnh trước khi dựng hình, nên không phải dựng hình lại vì những lỗi đó (đo trên một phim làm thật có ít nhất một lần sửa ở Script và một lần ở Shots).
- **SC-007**: Năm bộ test của xưởng (`tests/run.sh`, `tests/render/run.sh`, `tests/ui/run.sh`, `tests/filmcheck/run.sh`, `tests/online/run.sh`) vẫn đạt.

## Clarifications

### Session 2026-11-19

- Q: Điểm duyệt nào được bật cho một phim? → A: Mặc định theo kênh (Script và Shots bật), đặt bằng 5 ô đánh dấu trên trang kênh hoặc `channel set … reviews`; đổi được cho từng phim khi bắt đầu và trong lúc làm (điểm chưa tới). Không dùng file Excel cho cấu hình này.
- Q: Ai chạy lại các bước phụ thuộc sau khi sửa trên trang? → A: Trang chỉ chạy lệnh của bước đang sửa (không gọi Claude); agent làm lại các bước "Must run again" sau khi duyệt (FR-016a). Mặc định do Claude đề xuất, người dùng xác nhận 2026-11-19.
- Q: Sửa kịch bản trên trang có chạy lại lượt biên tập Claude không? → A: Không; chỉ máy chấm theo luật (FR-006). Người dùng xác nhận 2026-11-19.
- Ngoài phạm vi 026: nhập danh sách nhiều phim từ một bảng tính (CSV/Excel) để làm số lượng lớn; làm thành spec riêng sau khi 026 xong.

## Assumptions

- Bố cục theo trang mẫu đã duyệt ngày 2026-11-19; chữ trên giao diện bằng tiếng Anh như phần còn lại của app.
- Dùng lại cơ chế yêu cầu duyệt của specs/003, dấu nội dung và cổng dựng hình của specs/020, danh mục và phép kiểm của bộ dựng specs/022–023, khu "Done so far" và kiểm quyền của specs/025.
- Shots chỉ sửa được bối cảnh, máy và động tác của một cảnh; thêm, xoá, đổi thứ tự hay đổi thời lượng cảnh nằm ngoài phạm vi (sửa qua chat với agent).
- Treatment, Look, Picture, Render và Self-check không phải điểm duyệt; storyboard vẫn duyệt trong chat khi người dùng yêu cầu, như hiện nay.
- Nhạc chỉ chọn trong các lựa chọn xưởng soạn bằng nhạc cụ của thư viện; không tải nhạc ngoài. Lựa chọn là các kiểu nhạc mà bộ âm thanh của phong cách có sẵn (và "No music"); một kiểu chỉ được soạn khi chủ phim chọn nó.
- Sửa trên trang không tốn lượt gọi Claude: các lệnh trang chạy (FR-016a) đều chạy trên máy; chỉ phần agent làm lại sau khi duyệt mới dùng Claude.
- Chờ duyệt không có hạn giờ; việc chờ vẫn hiện trong danh sách việc.
- Không sửa tệp trong `lib/` (hiến pháp VI).
