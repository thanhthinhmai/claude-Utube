# Feature Specification: Một model Claude cho cả xưởng

**Feature Branch**: `024-one-claude-model`

**Created**: 2026-11-18

**Status**: Draft

**Input**: User description: "Một cài đặt model Claude duy nhất, khoá cứng. Mọi lượt gọi Claude của xưởng (agent làm phim, biên tập kịch bản, chấm độ hợp kênh và gợi ý đề, gán cỡ cảnh/góc máy, duyệt ý tưởng, và các lượt phụ của chính Claude Code như tìm web) dùng đúng một model lấy từ một cài đặt; không có đường lùi về model mặc định hay model khác. Danh sách được phép hiện chỉ có Opus 5.5 (mặc định), để sẵn chỗ thêm model sau. Chủ xưởng chọn trong Settings của giao diện và ở chế độ chat bằng một lệnh. Giá trị ngoài danh sách bị từ chối. Kết quả của mỗi lượt ghi đúng model chính đã dùng. Cài đặt cũ của model biên tập bị bỏ qua."

## Bối cảnh

Ngày 2026-11-18, kết quả biên tập kịch bản của phim `pause-ten-seconds` ghi "Haiku" cho cả 3 vòng, trong khi chủ xưởng đã chốt mọi việc của xưởng chạy bằng Opus 5.5 (2026-11-12). Kiểm lại thì thấy:

- lượt biên tập chính chạy đúng Opus, nhưng công cụ tìm web bên trong nó tự gọi một model nhỏ (Haiku, khoảng 12 600 token đầu vào cho một lần tìm), và kết quả ghi tên model đứng đầu danh sách, tức là model nhỏ;
- có hai ô cài đặt (model của việc, model của biên tập) với lựa chọn khác nhau (Opus, Sonnet, Haiku, "giống việc"), và ô model của việc là ô chữ tự do;
- một số chỗ gọi Claude tự chọn model riêng (gán cảnh luôn Opus, duyệt ý tưởng theo cài đặt), nên muốn đổi model phải sửa nhiều nơi.

Chủ xưởng chọn: **một** model cho mọi lượt gọi, chọn trong **một** chỗ, danh sách hiện chỉ có Opus 5.5.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mọi lượt gọi Claude dùng đúng model đã chọn (Priority: P1)

Chủ xưởng làm một phim. Mọi lượt gọi Claude trong lúc làm phim (biên tập kịch bản có tìm web, chấm đề, gán cảnh, agent làm phim, duyệt ý tưởng) chỉ dùng model đã chọn trong cài đặt, kể cả các lượt phụ mà công cụ tự gọi bên trong. Kết quả lưu lại của mỗi lượt ghi đúng tên model đó.

**Why this priority**: đây là luật chủ xưởng đã chốt; sai luật này là tốn chất lượng (model nhỏ đọc trang web cho biên tập) và báo cáo sai.

**Independent Test**: chạy một vòng biên tập có tìm web với cài đặt mặc định, rồi đọc thống kê model của lượt đó và kết quả đã lưu.

**Acceptance Scenarios**:

1. **Given** cài đặt mặc định, **When** biên tập chạy một vòng có tìm web, **Then** thống kê của lượt đó chỉ có Opus 5.5, và kết quả lưu ghi Opus 5.5.
2. **Given** cài đặt mặc định, **When** chấm đề, gán cảnh hoặc duyệt ý tưởng chạy, **Then** mỗi lượt được yêu cầu bằng Opus 5.5 và các lượt phụ bên trong cũng dùng Opus 5.5.
3. **Given** một việc làm phim ở chế độ online hoặc app, **When** agent làm phim và các công cụ nó gọi chạy, **Then** tất cả dùng model trong cài đặt của xưởng.
4. **Given** thống kê của một lượt liệt kê thêm model khác ngoài model đã yêu cầu, **When** kết quả được lưu, **Then** tên được ghi là model đã yêu cầu, không phải model đứng đầu danh sách.

---

### User Story 2 - Chủ xưởng chọn model ở một chỗ (Priority: P2)

Chủ xưởng mở Settings và thấy một ô chọn "Claude model" chỉ gồm các model được phép (hiện là Opus 5.5). Không còn ô "Script editor model". Ở chế độ chat, chủ xưởng xem và đặt model bằng một lệnh. Nhập model ngoài danh sách thì bị từ chối kèm danh sách hợp lệ.

**Why this priority**: cho chủ xưởng quyền chọn và để sẵn chỗ thêm model sau; khi danh sách chỉ có một model thì P1 đã đủ đảm bảo luật.

**Independent Test**: mở Settings, xem ô chọn; gửi một giá trị ngoài danh sách qua giao diện và qua lệnh; đọc lại cài đặt.

**Acceptance Scenarios**:

1. **Given** Settings, **When** chủ xưởng mở trang, **Then** chỉ có một ô chọn model, lựa chọn đang chọn là Opus 5.5, và không có ô model biên tập.
2. **Given** một giá trị ngoài danh sách (ví dụ Haiku), **When** gửi qua giao diện, **Then** bị từ chối với thông báo nêu các giá trị hợp lệ, cài đặt giữ nguyên.
3. **Given** chế độ chat, **When** chạy lệnh đặt model với giá trị hợp lệ, **Then** lệnh thành công và các lượt gọi sau dùng model đó; **When** giá trị không hợp lệ, **Then** lệnh báo lỗi dùng sai, nêu danh sách hợp lệ, không ghi gì.
4. **Given** chế độ chat, **When** chạy lệnh xem model, **Then** in model đang dùng.

---

### Edge Cases

- Cài đặt cũ có model biên tập (`haiku`, `sonnet`, `inherit`) hoặc biến môi trường cũ cho model biên tập: bị bỏ qua, không gây lỗi, biên tập dùng model chung.
- Cài đặt model của việc đã lưu từ trước là một giá trị ngoài danh sách (ô chữ tự do cũ): xưởng dùng model mặc định (Opus 5.5) và ghi một cảnh báo trong nhật ký; Settings hiện Opus 5.5.
- Không có tệp cài đặt (chế độ chat, máy mới): dùng Opus 5.5.
- Bảng giá token: model trong danh sách luôn có giá; thêm model mới vào danh sách mà thiếu giá thì test báo lỗi.
- Biến môi trường dành cho test (ví dụ model giả của bài test gán cảnh) chỉ có tác dụng khi chạy test, không mở đường lùi ở bản chạy thật.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Xưởng PHẢI có một danh sách model được phép, hiện chỉ có Opus 5.5, và một model mặc định là Opus 5.5.
- **FR-002**: Xưởng PHẢI có đúng một cài đặt model, dùng cho mọi lượt gọi Claude: agent làm phim, biên tập kịch bản, chấm độ hợp kênh và gợi ý đề, gán cỡ cảnh và góc máy, duyệt ý tưởng.
- **FR-003**: Mọi lượt gọi PHẢI truyền model một cách tường minh; không lượt nào được để công cụ tự chọn model mặc định.
- **FR-004**: Các lượt phụ do công cụ Claude tự gọi bên trong (tìm web, tóm tắt) PHẢI dùng cùng model với lượt chính.
- **FR-005**: Kết quả lưu của mỗi lượt PHẢI ghi model chính đã dùng: model đã yêu cầu nếu nó có trong thống kê, nếu không thì model viết nhiều nhất.
- **FR-006**: Settings PHẢI hiện cài đặt model bằng một ô chọn chỉ gồm các model được phép, và PHẢI bỏ ô model biên tập.
- **FR-007**: Giao diện quản trị PHẢI từ chối giá trị ngoài danh sách (lỗi dữ liệu không hợp lệ) và giữ nguyên cài đặt.
- **FR-008**: Chế độ chat PHẢI có lệnh xem và đặt model; giá trị ngoài danh sách bị từ chối với mã lỗi dùng sai và danh sách hợp lệ.
- **FR-009**: Cài đặt model biên tập cũ (trong tệp cài đặt, cơ sở dữ liệu và biến môi trường) PHẢI bị bỏ qua mà không gây lỗi.
- **FR-010**: Một giá trị model đã lưu nằm ngoài danh sách PHẢI được thay bằng model mặc định khi dùng, kèm một dòng cảnh báo.
- **FR-011**: PHẢI có một test tự động quét mã của xưởng và báo lỗi nếu có chỗ gọi Claude không lấy model từ cài đặt chung.

### Key Entities

- **Danh sách model được phép**: tên hiển thị và mã của từng model; model mặc định; mỗi model có giá token.
- **Cài đặt model của xưởng**: một giá trị trong danh sách; ở chế độ online/app nằm trong cài đặt của xưởng, ở chế độ chat nằm trong tệp cài đặt của dự án.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Một vòng biên tập thật có tìm web, với cài đặt mặc định, có thống kê model gồm đúng 1 model là Opus 5.5 (0 token cho model khác), và kết quả lưu ghi Opus 5.5.
- **SC-002**: Test quét mã tìm được 0 chỗ gọi Claude không lấy model từ cài đặt chung (và báo lỗi khi cố ý thêm một chỗ như vậy).
- **SC-003**: 100 % giá trị ngoài danh sách bị từ chối ở cả hai đường (giao diện và lệnh), cài đặt không đổi sau khi bị từ chối.
- **SC-004**: Settings có đúng 1 ô chọn model và 0 ô model biên tập.
- **SC-005**: Các bộ test hiện có của xưởng vẫn đạt.

## Assumptions

- "Khoá cứng" nghĩa là: chỉ dùng model đã chọn, không có đường lùi; danh sách hiện có một model nên thực tế mọi lượt là Opus 5.5.
- Thêm model mới về sau là đổi danh sách trong mã (kèm giá), không phải cài đặt của người dùng.
- Phiên chat làm phim của chính Claude Code (người dùng tự mở) do người dùng chọn model; xưởng chỉ quản các lượt gọi do xưởng tự khởi chạy.
- Model nhận lời (Whisper) và giọng đọc (Kokoro) không phải model Claude, nằm ngoài phạm vi.
- Bản sửa nhanh ngày 2026-11-18 (lượt phụ dùng cùng model, ghi đúng model chính) được giữ và trở thành một phần của tính năng này.
