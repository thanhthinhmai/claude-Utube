# Feature Specification: Blender là bộ máy thứ ba, chọn bộ máy theo từng shot, cảnh có chiều sâu như video mẫu

**Feature Branch**: `038-blender-engine`

**Created**: 2026-11-26

**Status**: Draft

**Input**: User description: "Tính năng 038: Blender là bộ máy dựng hình thứ ba và chọn bộ máy theo từng cảnh. (1) Mọi hình vẽ bằng code do Claude Code viết (ExtendScript cho AE, Python cho Blender), không vẽ tay, không AI tạo ảnh; (2) cảnh nào hợp thì dùng AE (cận/trung cận nhân vật, biểu cảm, thoại, đồ hoạ chữ); (3) cảnh nào hợp thì dùng Blender (cảnh rộng có không gian: hội trường, lớp học, hành lang; máy đi/vòng; đám đông; ánh sáng bóng đổ); một phim được trộn hai bộ máy theo từng cảnh (sửa hiến pháp VII thành 4.0.0); nhân vật trông giống nhau ở hai bộ máy (nhân vật 2D đặt trên mặt phẳng trong bối cảnh 3D); (4) cảnh hiện bị gần, thiếu chiều sâu và không gian so với video mẫu: đo từ video mẫu cỡ cảnh, độ cao máy, góc ống kính ước lượng, độ sâu bối cảnh, số lớp tiền/trung/hậu cảnh; đặt máy theo số đo; tầng kiểm chặn cảnh gần hoặc nông hơn mẫu. Bắt buộc dựng trên GPU. Gợi ý góc máy/đổi cảnh kiểu trang Sound để sang 039."

## Bối cảnh

- Phim hoạt hình nhân vật hiện dựng bằng After Effects (specs/032, hiến pháp 3.0.0 nguyên tắc VII: mỗi phim đúng một bộ máy). Hình 2D của AE giống nhân vật của video mẫu, nhưng bối cảnh rộng (hội trường, lớp học, hành lang) và máy quay đi lại phải giả lập, nên cảnh bị **gần và phẳng**.
- Bản thử Blender (2026-11-26, `/mnt/e/claude-utube-ae/blendertest`): bối cảnh 3D dựng bằng code có chiều sâu, ánh sáng và bóng đổ thật, máy quay đi tự do; dựng 1080p trên GPU của máy khoảng 5,5 s mỗi khung. Nhân vật **nặn 3D bằng code** sau nhiều vòng vẫn chưa đạt so với nhân vật 2D của video mẫu (thân, tay, khớp vai lệch dáng).
- So với video mẫu, các shot thử bị gần và nông: máy đặt sát, ống kính dài, bối cảnh nông, ít vật ở tiền cảnh, không có lớp xa. Lỗi này nằm ở cách đặt máy, không ở bộ máy.
- specs/021 đã học cỡ cảnh, góc máy, độ nét và bối cảnh của video mẫu, nhưng chưa có độ cao máy, góc ống kính, độ sâu bối cảnh và số lớp cảnh.
- Người dùng đã chọn (2026-11-26):
  - Một phim được trộn AE và Blender theo từng shot.
  - Làm 038 trước (bộ máy và chiều sâu); 039 (học góc máy, trang gợi ý Camera giống trang Sound) làm sau.
  - Mọi hình do Claude Code viết bằng code.

## Clarifications

### Session 2026-11-26

- Q: Shot gần hoặc nông hơn video mẫu thì chặn dựng bản đẹp hay chỉ cảnh báo? → A: Chặn theo shot (đến khi sửa hoặc người dùng miễn riêng shot đó); lệch tỉ lệ cỡ cảnh của cả phim chỉ cảnh báo.
- Q: Cầu nối app desktop dựng shot Blender làm luôn trong 038 hay để spec sau? → A: Làm luôn trong 038: cầu nối dựng Blender như AE, có bài thử Windows/macOS với Blender giả trên GitHub Actions và phần cài đường dẫn Blender trong bộ cài.
- Q: Hình 2D của nhân vật trong shot Blender lấy từ đâu? → A: Một bản code nhân vật duy nhất (rig AE do Claude Code viết, đã duyệt ở Cast). Với mỗi shot Blender, AE chạy code đó xuất động tác của nhân vật trên nền trong suốt theo góc máy của shot; Blender dán chuỗi hình lên mặt phẳng trong bối cảnh 3D. Shot Blender có nhân vật vì vậy cũng cần AE.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Một phim, mỗi shot chọn AE hoặc Blender (Priority: P1)

Người làm phim (Claude theo luồng làm phim, hoặc việc của app) khai báo trong danh sách shot bộ máy của từng shot: After Effects hoặc Blender. Một lệnh dựng cả phim dựng mỗi shot bằng bộ máy của nó và ghép thành một bản tổng, đúng khung, có tiếng. Ghi chú phim và "Fix with Claude" dựng lại đúng các shot bị ghi chú, dù shot đó thuộc bộ máy nào.

**Why this priority**: Đây là nền của mọi story khác. Không trộn được thì không đặt được cảnh rộng vào Blender mà vẫn giữ cảnh nhân vật ở AE.

**Independent Test**: Phim thử 30 s gồm ít nhất 3 shot AE và 3 shot Blender. Chạy lệnh dựng cả phim: ra một bản tổng có tiếng, mỗi shot dài đúng thời lượng trong danh sách (lệch ≤ 1 khung), mốc shot đúng định dạng của specs/029. Đổi một shot Blender, chạy lệnh sửa: chỉ shot đó được dựng lại, các shot khác giữ nguyên.

**Acceptance Scenarios**:

1. **Given** danh sách shot có cả shot AE và shot Blender, **When** chạy lệnh dựng cả phim, **Then** mỗi shot được dựng bằng đúng bộ máy của nó và ghép thành một bản tổng; mốc shot ghi kèm bộ máy của từng shot.
2. **Given** một phim trộn đã dựng, **When** sửa một shot Blender theo ghi chú, **Then** chỉ shot đó được dựng lại và ghép theo khung vào video hiện có, giữ một bản trước (specs/029).
3. **Given** một shot không ghi bộ máy, **When** dựng, **Then** shot dùng bộ máy mặc định của phim, và mốc shot ghi bộ máy đã dùng.
4. **Given** phim trang web (bộ máy "page"), **When** khai báo shot Blender, **Then** lệnh từ chối: chỉ phim hoạt hình nhân vật (AE) mới trộn được với Blender.
5. **Given** Blender hoặc After Effects chưa được cài đặt trên máy, **When** dựng một shot của bộ máy đó, **Then** lệnh dừng và báo bộ máy nào thiếu và cách cài đặt đường dẫn, không âm thầm đổi sang bộ máy khác.

---

### User Story 2 - Cảnh có chiều sâu và không gian như video mẫu (Priority: P1)

Xưởng đo trên video mẫu, cho từng shot: cỡ cảnh, độ cao máy so với mắt nhân vật, góc nhìn của ống kính (rộng, thường, hẹp), độ sâu bối cảnh nhìn thấy, và số lớp cảnh (tiền cảnh, trung cảnh, hậu cảnh). Số đo được lưu vào phong cách kèm khung bằng chứng. Khi lập bảng shot, mỗi shot ghi cỡ cảnh, độ cao máy, góc ống kính và các lớp cảnh theo số đo đó. Tầng kiểm trước khi dựng đẹp chặn các shot gần hơn hoặc nông hơn video mẫu, theo mã shot.

**Why this priority**: Người dùng nhận xét các cảnh "vẫn đang bị gần, không có chiều sâu, không có không gian so với bản gốc". Bộ máy mới không tự sửa được lỗi này nếu máy vẫn đặt như cũ.

**Independent Test**: Học lại video mẫu của phim thử khớp shot (`charisma-ref`): phong cách có thêm phân bố độ cao máy, góc ống kính, độ sâu và số lớp cảnh, mỗi mục có khung bằng chứng. Chạy tầng kiểm trên 10 shot thử hiện có: các shot gần và nông bị báo theo mã shot. Dựng lại theo số đo: tầng kiểm đạt, và người dùng xem cạnh video mẫu thấy không gian tương đương.

**Acceptance Scenarios**:

1. **Given** một bộ video mẫu, **When** chạy bước học chiều sâu, **Then** phong cách ghi phân bố của cỡ cảnh, độ cao máy, góc ống kính, độ sâu bối cảnh và số lớp cảnh, mỗi mục có khung bằng chứng (hiến pháp VIII).
2. **Given** một bảng shot của phim, **When** chạy tầng kiểm chiều sâu, **Then** mỗi shot gần hơn hoặc nông hơn mức của video mẫu bị báo theo mã shot, kèm số đo của shot, mức của video mẫu và cách sửa.
3. **Given** một shot cố ý cận (ví dụ biểu cảm), **When** người dùng cho miễn shot đó, **Then** miễn được ghi theo từng shot kèm lý do, không miễn cả phim; agent không được tự miễn.
4. **Given** phân bố cỡ cảnh của cả phim lệch quá mức so với video mẫu (ví dụ thiếu cảnh toàn), **When** chạy tầng kiểm, **Then** tầng kiểm cảnh báo cả phim (không chặn), kèm tỉ lệ từng cỡ cảnh của phim và của video mẫu.
5. **Given** còn shot gần hoặc nông chưa sửa và chưa được miễn, **When** chạy lệnh dựng bản đẹp, **Then** lệnh từ chối và liệt kê các shot đó.

---

### User Story 3 - Nhân vật trông như nhau ở AE và Blender (Priority: P2)

Nhân vật của phim được vẽ một lần bằng code ở dạng 2D (như video mẫu). Shot AE dùng nhân vật đó như hiện nay. Shot Blender đặt chính nhân vật 2D đó lên các mặt phẳng trong bối cảnh 3D, quay về phía máy, đi trên sàn, có bóng đổ xuống sàn và bị vật ở tiền cảnh che đúng thứ tự. Bảng mẫu nhân vật ở điểm duyệt Cast (specs/034) cho thấy nhân vật ở cả hai bộ máy.

**Why this priority**: Phim trộn chỉ dùng được khi khán giả không thấy nhân vật đổi dáng giữa hai shot liền nhau. Cần sau US1 vì phải có phim trộn mới thấy.

**Independent Test**: Bảng mẫu của một nhân vật có hình AE và hình trong bối cảnh Blender đặt cạnh nhau, cùng tư thế: màu áo và đầu lệch trong mức đã định, độ dày viền tương đương, người dùng duyệt là "cùng một nhân vật".

**Acceptance Scenarios**:

1. **Given** một nhân vật đã duyệt ở Cast, **When** dựng một shot Blender có nhân vật đó, **Then** nhân vật dùng đúng hình 2D đã duyệt (màu, viền, mặt, phụ kiện), không phải một mô hình 3D khác.
2. **Given** shot Blender có máy đi vòng quanh nhân vật, **When** dựng, **Then** nhân vật luôn quay về phía máy, chân chạm sàn, có bóng đổ, và bị vật ở tiền cảnh che đúng thứ tự xa gần.
3. **Given** điểm duyệt Cast của phim trộn, **When** mở bảng mẫu, **Then** mỗi nhân vật có cả hình AE và hình trong bối cảnh Blender cùng tư thế.

---

### User Story 4 - Xưởng gợi ý bộ máy cho từng shot (Priority: P2)

Khi lập bảng shot, xưởng gợi ý bộ máy cho từng shot dựa trên nội dung shot (cỡ cảnh, bối cảnh, chuyển động máy, số người, đồ hoạ chữ), kèm một dòng lý do. Người làm phim giữ hoặc đổi; lựa chọn được ghi lại.

**Why this priority**: Giúp chọn nhất quán, đúng yêu cầu "cảnh nào hợp thì dùng AE, cảnh nào hợp thì dùng Blender" mà không phải tự cân nhắc từng shot. Phim vẫn làm được khi chỉ có US1 (khai báo tay).

**Independent Test**: Trên bảng shot của phim thử, mỗi shot có một bộ máy gợi ý và lý do; đối chiếu với lựa chọn của người dùng.

**Acceptance Scenarios**:

1. **Given** một shot cảnh toàn trong hội trường có máy đi, **When** lập bảng shot, **Then** xưởng gợi ý Blender với lý do (cảnh rộng, máy đi).
2. **Given** một shot cận biểu cảm hoặc một thẻ chữ, **When** lập bảng shot, **Then** xưởng gợi ý AE với lý do.
3. **Given** người làm phim đổi bộ máy gợi ý, **When** lưu bảng shot, **Then** lựa chọn và bộ máy gợi ý ban đầu đều được ghi lại.

---

### User Story 5 - Cài đặt Blender và dựng bắt buộc trên GPU (Priority: P3)

Người dùng tự cài Blender (phần mềm miễn phí) và chỉ cho xưởng đường dẫn, bằng lệnh hoặc trong app desktop. Bước kiểm trạng thái của xưởng cho biết Blender có sẵn không, phiên bản, và Blender có dựng được trên GPU không. Mỗi lượt dựng shot Blender kiểm lại GPU: dựng bằng phần mềm thì dừng và hỏi người dùng. Trong app desktop, shot Blender được dựng trên máy của người dùng qua cầu nối, như AE.

**Why this priority**: Cần cho máy của người khác và cho app (người dùng chọn làm luôn trong 038), nhưng máy phát triển hiện đã có Blender chạy được nên không chặn US1–US4.

**Independent Test**: Trỏ đường dẫn tới Blender: lệnh kiểm trạng thái báo phiên bản và GPU. Trỏ sai: báo rõ. Ép dựng phần mềm: lượt dựng dừng với thông báo GPU, không ra video.

**Acceptance Scenarios**:

1. **Given** đường dẫn Blender đúng, **When** chạy lệnh kiểm trạng thái, **Then** thấy phiên bản và tên GPU dùng để dựng.
2. **Given** Blender chỉ dựng được bằng phần mềm, **When** dựng một shot Blender, **Then** lượt dựng dừng trước khung đầu tiên và báo người dùng; không tiếp tục bằng phần mềm.
3. **Given** app desktop đang chạy và có cầu nối, **When** việc của app cần dựng shot Blender, **Then** shot được dựng trên máy của người dùng qua cầu nối, báo tiến độ ít nhất sau mỗi shot; mỗi lúc một lượt dựng của mỗi bộ máy.

---

### Edge Cases

- Shot Blender có nhân vật mà AE không chạy (thiếu bản quyền, cầu nối tắt): lệnh dừng và báo, không dựng shot Blender thiếu nhân vật.
- Shot Blender dựng dở bị ngắt (máy tắt, hết thời hạn): lượt sau dựng tiếp từ khung đã có, không dựng lại từ đầu.
- Shot AE và shot Blender liền nhau có chuyển cảnh mờ dần: chuyển cảnh được làm lúc ghép bản tổng, không phụ thuộc bộ máy.
- Hai shot liền nhau khác bộ máy nhưng cùng bối cảnh (ví dụ cảnh toàn Blender rồi cận AE trong cùng lớp học): nền của shot AE phải khớp màu và ánh sáng của bối cảnh Blender. Cách làm: shot AE dùng ảnh nền dựng từ chính bối cảnh Blender ở góc máy của shot.
- Shot Blender có nhân vật 2D mà máy nhìn gần như ngang mặt phẳng nhân vật (góc trên 75°): tầng kiểm báo shot đó, vì nhân vật 2D sẽ bị mỏng đi.
- Video mẫu có ít shot của một cỡ cảnh (dưới 5 shot): mức của cỡ cảnh đó chỉ là cảnh báo, không chặn.
- Phim cũ chỉ có AE (film.json `engine: "ae"`, không có bộ máy theo shot): vẫn dựng như cũ, không phải sửa.
- Blender đổi phiên bản: phiên bản dùng để dựng được ghi trong mốc shot; tầng kiểm cảnh báo khi các shot của cùng một phim dựng bằng hai phiên bản khác nhau.
- Thời gian dựng Blender dài (khoảng 5,5 s mỗi khung 1080p trên GPU tích hợp): lệnh in ước tính thời gian trước khi dựng cả phim.

## Requirements *(mandatory)*

### Functional Requirements

**Hiến pháp và quy tắc chung**

- **FR-001**: Hiến pháp PHẢI được sửa thành bản 4.0.0, nguyên tắc VII:
  - Xưởng có ba bộ máy: trang web, After Effects, Blender.
  - Phim hoạt hình nhân vật được trộn After Effects và Blender theo từng shot. Phim trang web vẫn chỉ dùng một bộ máy.
  - Blender do người dùng tự cài; xưởng không tải, cài hay đóng gói Blender.
- **FR-002**: Mọi hình của mọi bộ máy PHẢI do script của xưởng hoặc do Claude Code viết sinh ra; xưởng KHÔNG ĐƯỢC dùng mô hình AI tạo ảnh hay video, và không cần vẽ tay.

**Phim trộn (US1)**

- **FR-003**: Mỗi shot trong danh sách shot của phim hoạt hình nhân vật PHẢI khai báo được bộ máy (After Effects hoặc Blender). Shot không khai báo dùng bộ máy mặc định của phim.
- **FR-004**: Lệnh dựng cả phim PHẢI dựng mỗi shot bằng bộ máy của nó và ghép thành một bản tổng. Mỗi shot dài đúng thời lượng trong danh sách (lệch ≤ 1 khung), tiếng giữ nguyên. Mốc shot theo định dạng specs/029, thêm bộ máy và phiên bản bộ máy của từng shot.
- **FR-005**: Lệnh sửa shot, ghi chú phim (specs/029), "Fix with Claude" (specs/032) và Animatic (specs/035) PHẢI hoạt động với shot Blender như với shot AE: chỉ dựng lại các shot bị ảnh hưởng, ghép theo khung, giữ một bản trước.
- **FR-006**: Xưởng PHẢI liệt kê được các shot dùng một phần của bộ dựng Blender dùng chung (bối cảnh, ánh sáng, máy quay), như lệnh `uses` của AE, để chỉ dựng lại các shot bị ảnh hưởng.
- **FR-007**: Bộ dựng Blender dùng chung (bối cảnh, vật, ánh sáng, cách tô hoạt hình, viền, máy quay, đám đông, hiệu ứng như hoa giấy) PHẢI nằm ngoài thư mục phim. Phim chỉ chứa phần riêng của từng shot.
- **FR-008**: Shot Blender bị ngắt giữa chừng PHẢI dựng tiếp được từ khung đã có.
- **FR-009**: Trước khi dựng cả phim, lệnh PHẢI in ước tính thời gian dựng của từng bộ máy.
- **FR-010**: Chuyển cảnh giữa hai shot (cắt, mờ dần, đen) PHẢI được làm lúc ghép bản tổng, không phụ thuộc bộ máy của hai shot.

**Chiều sâu và không gian (US2)**

- **FR-011**: Bước học phong cách PHẢI đo thêm trên mỗi shot của video mẫu:
  - độ cao máy so với mắt nhân vật: thấp, ngang, cao, rất cao
  - góc nhìn ống kính: rộng, thường, hẹp
  - độ sâu bối cảnh nhìn thấy: nông, vừa, sâu
  - số lớp cảnh: tiền cảnh, trung cảnh, hậu cảnh, lớp xa
  - có vật che ở tiền cảnh hay không
  Mỗi số đo PHẢI có khung bằng chứng, và kết quả PHẢI lưu vào phong cách cạnh số đo cỡ cảnh của specs/021.
- **FR-012**: Bảng shot của phim hoạt hình nhân vật PHẢI ghi cho mỗi shot: cỡ cảnh, độ cao máy, góc ống kính, độ sâu, các lớp cảnh.
- **FR-013**: Tầng kiểm trước khi dựng đẹp PHẢI so bảng shot (và ảnh thử mỗi shot) với số đo của video mẫu, rồi:
  - **chặn** lệnh dựng bản đẹp khi có shot gần hơn hoặc nông hơn mức của video mẫu ở cùng cỡ cảnh, báo theo mã shot kèm số đo và cách sửa, đến khi shot được sửa hoặc được miễn riêng (FR-014)
  - **cảnh báo** (không chặn) khi tỉ lệ một cỡ cảnh của cả phim lệch quá 10 điểm phần trăm so với video mẫu
- **FR-014**: Miễn kiểm chiều sâu PHẢI theo từng shot, kèm lý do, và do người dùng quyết; agent KHÔNG ĐƯỢC tự miễn. Lệnh miễn PHẢI bị từ chối khi chạy bên trong một việc của app.
- **FR-015**: Cỡ cảnh có dưới 5 shot trong video mẫu PHẢI chỉ cảnh báo, không chặn.

**Nhân vật dùng chung (US3)**

- **FR-016**: Nhân vật của phim trộn PHẢI có một bản code duy nhất: rig AE đã duyệt ở Cast. Với mỗi shot Blender có nhân vật, AE PHẢI chạy rig đó, xuất động tác của từng nhân vật trên nền trong suốt (đúng thời lượng shot, hướng nhìn theo góc máy của shot); Blender PHẢI dán chuỗi hình lên mặt phẳng trong bối cảnh 3D: quay về phía máy, chân chạm sàn, có bóng đổ, che và bị che đúng thứ tự xa gần. Sửa nhân vật hoặc động tác PHẢI làm cả lớp nhân vật lẫn shot Blender đó "Must run again".
- **FR-017**: Nhân vật trong shot Blender PHẢI cử động được như ở AE (đi, vẫy, vỗ tay, giơ tay, quay đầu, biểu cảm), cùng tên động tác.
- **FR-018**: Bảng mẫu ở điểm duyệt Cast (specs/034) của phim trộn PHẢI cho thấy mỗi nhân vật ở cả hai bộ máy, cùng tư thế. Nhân vật chưa duyệt chặn dựng shot của cả hai bộ máy.
- **FR-019**: Tầng kiểm PHẢI báo shot Blender mà máy nhìn mặt phẳng nhân vật lệch quá 75°.
- **FR-020**: Shot AE nằm cạnh shot Blender cùng bối cảnh PHẢI dùng được ảnh nền dựng từ bối cảnh Blender ở góc máy của shot đó.

**Gợi ý bộ máy (US4)**

- **FR-021**: Khi lập bảng shot, xưởng PHẢI gợi ý bộ máy cho từng shot kèm một dòng lý do, theo luật:
  - **Blender**: cảnh toàn hoặc rất rộng, máy đi hay vòng quanh, đám đông, bối cảnh trong nhà có chiều sâu
  - **After Effects**: cận, trung cận, thẻ chữ hoặc đồ hoạ
- **FR-022**: Bộ máy gợi ý và bộ máy được chọn PHẢI được ghi cùng nhau trong danh sách shot.

**Cài đặt, GPU, app (US5)**

- **FR-023**: Đường dẫn tới Blender PHẢI nằm trong cấu hình của máy, đặt bằng lệnh hoặc trong app desktop; không tệp nào của phim hay bộ dựng chứa đường dẫn riêng của máy.
- **FR-024**: Lệnh kiểm trạng thái của xưởng PHẢI báo Blender có sẵn hay không, phiên bản, và GPU dùng để dựng.
- **FR-025**: Mỗi lượt dựng shot Blender PHẢI kiểm bộ dựng đang dùng GPU trước khung đầu tiên. Không có GPU thì dừng và báo người dùng; không dựng tiếp bằng phần mềm.
- **FR-026**: Trong app desktop, shot Blender PHẢI được dựng trên máy của người dùng qua cầu nối (như AE, specs/032):
  - mỗi lúc một lượt dựng của mỗi bộ máy
  - có thời hạn cho mỗi shot
  - báo tiến độ ít nhất sau mỗi shot
  - báo rõ khi không tìm thấy Blender
- **FR-028**: Luồng build GitHub Actions của app desktop PHẢI có bài thử cầu nối Blender với một Blender giả, chạy trên Windows và macOS. Bộ cài PHẢI có phần cài đường dẫn Blender: tự tìm ở chỗ cài mặc định, kiểm và lưu đường dẫn người dùng chọn.
- **FR-029**: Form tạo phim của app PHẢI cho phép phim hoạt hình nhân vật có shot Blender. Khi cầu nối chưa sẵn sàng cho bộ máy nào cần dùng, app PHẢI báo trước và không tạo việc.
- **FR-027**: Thiếu Blender PHẢI chỉ báo, không âm thầm đổi shot sang bộ máy khác.

### Key Entities

- **Shot (mở rộng)**: một shot trong danh sách shot của phim. Thêm:
  - bộ máy được chọn và bộ máy gợi ý (kèm lý do)
  - cỡ cảnh, độ cao máy, góc ống kính, độ sâu, các lớp cảnh
  - miễn kiểm chiều sâu (nếu có, kèm lý do và người quyết)
- **Mốc shot (mở rộng, specs/029)**: thêm bộ máy và phiên bản bộ máy đã dựng shot.
- **Số đo chiều sâu của phong cách**: phân bố độ cao máy, góc ống kính, độ sâu, số lớp cảnh và vật che tiền cảnh, theo từng cỡ cảnh, kèm khung bằng chứng của video mẫu.
- **Bộ dựng Blender dùng chung**: bối cảnh, vật, ánh sáng, cách tô, viền, máy quay, đám đông, hiệu ứng; có phiên bản để biết shot nào cần dựng lại.
- **Nhân vật 2D dùng chung**: rig AE của mỗi nhân vật (màu, viền, mặt, phụ kiện, động tác), dùng thẳng ở shot AE và qua lớp nhân vật xuất trên nền trong suốt ở shot Blender.
- **Lớp nhân vật của shot Blender**: chuỗi hình trong suốt của một nhân vật trong một shot, do AE xuất từ rig; ghi rig, phiên bản rig, động tác và góc nhìn đã dùng.
- **Cấu hình Blender của máy**: đường dẫn, phiên bản, GPU đã kiểm.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Phim thử 30 s có ít nhất 3 shot AE và 3 shot Blender được dựng thành một bản tổng bằng một lệnh. Mỗi shot lệch thời lượng ≤ 1 khung, và mốc shot ghi đúng bộ máy của 100% shot.
- **SC-002**: Sửa một shot Blender theo ghi chú chỉ dựng lại shot đó. Các khung của mọi shot khác giữ nguyên từng khung, và tổng thời gian sửa ≤ thời gian dựng shot đó + 2 phút.
- **SC-003**: Trên phim thử khớp shot, sau khi dựng lại theo số đo chiều sâu:
  - tỉ lệ mỗi cỡ cảnh của phim lệch ≤ 10 điểm phần trăm so với video mẫu
  - ≥ 80% shot có số lớp cảnh không ít hơn trung vị của video mẫu ở cùng cỡ cảnh
  - người dùng xem cạnh video mẫu và đánh giá "không gian tương đương" ở ≥ 8/10 shot
- **SC-004**: Tầng kiểm chiều sâu báo đúng ≥ 90% số shot mà người dùng đánh dấu "bị gần hoặc nông" trong 10 shot thử hiện có.
- **SC-005**: Số đo độ cao máy và góc ống kính trên video mẫu khớp với nhãn người dùng kiểm lại ở ≥ 80% của 40 shot lấy ngẫu nhiên.
- **SC-006**: Trên bảng mẫu nhân vật, hình AE và hình Blender của cùng nhân vật, cùng tư thế:
  - màu áo và màu đầu lệch ≤ 5 đơn vị khác biệt màu cảm nhận
  - độ dày viền chênh trong khoảng 0,8–1,25 lần
  - người dùng duyệt là "cùng một nhân vật"
- **SC-007**: Bộ máy gợi ý trùng với lựa chọn cuối cùng của người dùng ở ≥ 80% số shot của phim thử.
- **SC-008**: 100% lượt dựng Blender trên máy không có GPU dừng trước khung đầu tiên với thông báo rõ, không ra video dựng bằng phần mềm.
- **SC-009**: Phim AE cũ (chỉ khai báo `engine: "ae"`) dựng lại ra video trùng với trước khi có tính năng này.

## Assumptions

- Blender là phần mềm miễn phí (GPL) do người dùng tự cài. Máy phát triển dùng Blender 5.2.5 bản portable trên Windows, gọi từ WSL ở chế độ không giao diện; bộ dựng EEVEE trên GPU của máy (Intel UHD 730).
- Cách tô hoạt hình (hai tông màu và viền), rig đi bộ, hoa giấy và ba bối cảnh (lớp học, hành lang, hội trường) của bản thử là điểm khởi đầu cho bộ dựng Blender dùng chung, sẽ viết lại theo chuẩn của xưởng.
- Nhân vật nặn 3D bằng code không được dùng. Nhân vật trong Blender là hình 2D đặt trên mặt phẳng, theo bài học của bản thử (2026-11-26).
- Phần đo chiều sâu dùng cùng cách gán nhãn của specs/021 (một lượt Claude độc lập, luôn Opus 5.5, có hình hướng dẫn vẽ bằng code), cộng số đo bằng công cụ nếu đo được (ví dụ điểm tụ để ước lượng độ cao máy và góc ống kính).
- Video mẫu và tiếng của nó không rời máy; ảnh từ video mẫu không gửi đi đâu.
- Thời gian dựng Blender không có trần riêng; lệnh chỉ in ước tính (FR-009).
- Ngoài phạm vi (để sang 039): học kiểu chuyển động máy và chuyển cảnh của video mẫu để gợi ý 2–3 phương án cho mỗi shot, và trang duyệt "Camera" giống trang Sound.
- Ngoài phạm vi: trộn Blender với phim trang web; nhân vật 3D thật; dựng Blender trên máy chủ của chế độ online.
- Phụ thuộc: specs/032 (phim AE, cầu nối, ghép theo khung), 034 (Cast), 035 (Animatic, `timing.json`), 029 (mốc shot, ghi chú phim), 021 (cỡ cảnh của video mẫu), 020 (tầng kiểm).
