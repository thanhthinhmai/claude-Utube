# Feature Specification: Vỏ app desktop cho Windows (qua WSL) và macOS

**Feature Branch**: `015-desktop-shell`

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "làm 015 cho cả Windows qua WSL, macOS" — vỏ app desktop giống neb-creative-tool: cửa sổ app, khởi động và tắt phần lõi (chế độ máy chủ của 014), icon khay, thoát an toàn, màn hình thiết lập lần đầu; Windows chạy phần lõi trong WSL2, macOS chạy thẳng trên máy.

## Clarifications

### Session 2026-11-11

- Q: Ở 015, phần lõi trong WSL lấy từ đâu? → A: Một bản studio đã có trong một bản Linux WSL của người dùng; bản Linux riêng đóng gói sẵn để ở 016 (FR-005).
- Q: Có thêm ngoại lệ "bật WSL khi người dùng đồng ý" vào hiến pháp không? → A: Có, sửa hiến pháp lên 2.2.0 (FR-009).
- Q: Kiểm trên Windows và macOS thật bằng cách nào? → A: GitHub Actions trên máy Windows và macOS của GitHub (FR-016). Người dùng có máy Mac.

## Bối cảnh

Lộ trình app desktop (2026-11-11):
- **014** (xong): cả xưởng chạy trên một máy bằng `sh bin/studio app start|stop`, không cần Docker.
- **015** (spec này): vỏ desktop.
- **016**: bộ cài, phần lõi đóng gói sẵn, cập nhật.
- **017**: license key.

Người dùng mở app như mọi ứng dụng desktop. App khởi động phần lõi và hiện giao diện xưởng trong cửa sổ của nó. Khi người dùng thoát, app tắt phần lõi an toàn.

Phần lõi chạy ở đâu:
- **Windows**: trong WSL2, vì thư viện phim cần công cụ Linux.
- **macOS**: chạy thẳng trên máy.

Khuôn làm theo dự án neb-creative-tool của người dùng: một phiên duy nhất, cửa sổ chờ lúc khởi động, màn hình thiết lập lần đầu, icon khay, thoát an toàn có hỏi khi còn việc tốn tiền, tắt sạch cả cây tiến trình.

Mức quy trình: **Đầy đủ**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mở app là có xưởng (Priority: P1)

Người dùng mở app. Một cửa sổ chờ hiện tiến độ khởi động. App khởi động phần lõi (Windows: trong WSL2; macOS: trên máy), đợi tới khi sẵn sàng, rồi mở cửa sổ chính với giao diện xưởng. Người dùng đăng nhập (014: có đăng nhập) và dùng xưởng như bản trình duyệt. Mở app lần nữa thì chỉ đưa cửa sổ đang có lên trước.

**Why this priority**: Đây là thứ biến xưởng thành một ứng dụng desktop thật.

**Independent Test**: Trên một máy đã có phần lõi chạy được (014), mở app. Kết quả cần thấy:
- cửa sổ chờ hiện, rồi cửa sổ chính mở giao diện xưởng trong dưới 30 giây;
- mở app lần hai thì không có bản thứ hai, cửa sổ cũ được đưa lên.

**Acceptance Scenarios**:

1. **Given** máy đã có phần lõi sẵn sàng, **When** người dùng mở app, **Then** cửa sổ chờ hiện các bước (kiểm tra, khởi động phần lõi, đợi giao diện), rồi cửa sổ chính mở trang đăng nhập hoặc trang chính của xưởng.
2. **Given** app đang chạy, **When** người dùng mở app lần nữa, **Then** không có bản thứ hai; cửa sổ đang có được hiện và đưa lên trước.
3. **Given** phần lõi không khởi động được, **When** app chờ quá thời hạn, **Then** cửa sổ chờ hiện lỗi dễ hiểu, kèm các dòng log cuối và các nút "Thử lại", "Mở thư mục log", "Thoát".
4. **Given** đang dùng app, **When** bấm một liên kết ra ngoài xưởng (ví dụ video bằng chứng trên YouTube), **Then** liên kết mở bằng trình duyệt mặc định, không mở trong cửa sổ app.
5. **Given** phần lõi đã chạy từ trước, do người dùng tự gõ `app start`, **When** mở app, **Then** app dùng luôn phần lõi đó, không mở bản thứ hai.

---

### User Story 2 - Thiết lập lần đầu (Priority: P2)

Lần đầu mở app, màn hình thiết lập kiểm máy và dẫn người dùng qua từng bước:
- **Windows**: kiểm WSL2. Chưa có thì giải thích và có nút "Bật WSL" (Windows hỏi quyền quản trị, rồi cần khởi động lại máy).
- **macOS**: kiểm các công cụ cần có (014 R8).
- **Cả hai**: chọn thư mục dữ liệu, xem dung lượng trống, rồi bấm Bắt đầu. Sau đó app khởi động phần lõi và mở trang tạo chủ xưởng của xưởng (008).

**Why this priority**: Không có bước này thì người mới không tự cài được. Nhưng nó cần vỏ của US1.

**Independent Test**: Trên máy chưa có cấu hình app:
- màn hình thiết lập hiện kết quả kiểm từng mục (đạt hay thiếu, kèm cách sửa);
- chọn thư mục dữ liệu, bấm Bắt đầu → cấu hình được lưu và app mở trang tạo chủ xưởng;
- lần mở sau không hiện màn hình thiết lập nữa.

**Acceptance Scenarios**:

1. **Given** lần đầu mở app, **When** màn hình thiết lập hiện, **Then** nó liệt kê từng điều kiện với trạng thái đạt hay thiếu, và mỗi mục thiếu có một câu hướng dẫn sửa.
2. **Given** Windows chưa bật WSL2, **When** người dùng bấm "Bật WSL" và đồng ý quyền quản trị, **Then** WSL được bật, và màn hình báo cần khởi động lại máy. Mở lại app sau khi khởi động lại thì thiết lập đi tiếp.
3. **Given** người dùng chọn một thư mục dữ liệu, **When** bấm Bắt đầu, **Then** app kiểm thư mục (ghi được, đủ chỗ trống ít nhất 5 GB, không nằm trong thư mục cài app), lưu cấu hình, khởi động phần lõi và mở trang tạo chủ xưởng.
4. **Given** đã thiết lập xong, **When** người dùng muốn đổi thư mục dữ liệu, **Then** icon khay có mục "Đổi thiết lập". Mục này tắt phần lõi, mở lại màn hình thiết lập, và không xoá dữ liệu cũ.

---

### User Story 3 - Icon khay và thoát an toàn (Priority: P3)

App có icon ở khay hệ thống (thanh menu trên macOS) với các mục: Mở xưởng, Mở trong trình duyệt, Thư mục dữ liệu, Thư mục log, Đổi thiết lập, Thoát. Đóng cửa sổ chính thì app vẫn chạy ở khay, để việc làm phim không bị ngắt. Bấm Thoát khi còn việc đang chạy thì app hỏi lại, nêu tên việc. Đồng ý thì app dừng phần lõi (014 `app stop --force`), tắt sạch mọi tiến trình rồi thoát.

**Why this priority**: Làm phim mất hàng chục phút; đóng nhầm cửa sổ không được làm mất việc và tiền token. Nhưng lõi là US1.

**Independent Test**:
- đóng cửa sổ chính → app vẫn chạy, mở lại được từ khay;
- bấm Thoát khi có việc đang chạy → hộp hỏi nêu tên việc; chọn Huỷ thì không có gì xảy ra, chọn Thoát thì phần lõi dừng và không còn tiến trình nào của app.

**Acceptance Scenarios**:

1. **Given** app đang chạy, **When** đóng cửa sổ chính, **Then** app vẫn chạy ở khay. Lần đầu đóng, app báo một lần rằng xưởng vẫn đang chạy ở khay.
2. **Given** có việc đang chạy, **When** bấm Thoát, **Then** hộp hỏi nêu tên các việc. Huỷ thì giữ nguyên; Thoát thì dừng phần lõi với `--force`, rồi app thoát.
3. **Given** không có việc nào chạy, **When** bấm Thoát, **Then** app dừng phần lõi và thoát mà không hỏi.
4. **Given** app đã thoát, **When** kiểm tiến trình trên máy (và trong WSL ở Windows), **Then** không còn tiến trình nào của app hay của phần lõi.
5. **Given** máy tắt hoặc app sập khi đang có việc, **When** mở app lại, **Then** phần lõi chạy tiếp việc dở (014 FR-012).

### Edge Cases

- Windows có WSL1 hoặc WSL bản quá cũ: màn hình thiết lập báo cần WSL2 và cách nâng cấp (`wsl --update`, `wsl --set-default-version 2`).
- Máy tắt ảo hoá trong BIOS: báo rõ, kèm cách bật; app không tự sửa được.
- macOS chặn app chưa ký số lần đầu mở: thuộc phần hướng dẫn cài của 016, không thuộc 015.
- Cổng của phần lõi bị đổi (014 tự chọn cổng trống): app đọc địa chỉ thật từ trạng thái của phần lõi, không đoán.
- Phần lõi sập khi app đang mở: cửa sổ hiện thông báo "Xưởng đã dừng" với nút "Khởi động lại".
- Người dùng gõ `app stop` ngoài app khi app đang mở: app nhận ra phần lõi đã dừng, xử lý như trên.
- Thư mục dữ liệu nằm trên ổ ngoài đã rút: màn hình thiết lập hiện lại, kèm thông báo.

## Requirements *(mandatory)*

### Functional Requirements

**Vỏ và cửa sổ**
- **FR-001**: App MUST chạy một phiên duy nhất trên mỗi máy và mỗi người dùng. Mở lần hai thì đưa cửa sổ đang có lên trước.
- **FR-002**: Khi mở, app MUST hiện cửa sổ chờ với các bước đang làm, rồi mở cửa sổ chính tới địa chỉ thật của phần lõi khi phần lõi trả lời. Thời hạn chờ là 60 giây; quá hạn thì hiện lỗi theo US1/AC3.
- **FR-003**: Cửa sổ chính MUST chỉ hiện trang của xưởng (`127.0.0.1` và cổng của phần lõi). Mọi liên kết khác MUST mở bằng trình duyệt mặc định.
- **FR-004**: App MUST dùng lại phần lõi đang chạy sẵn cho cùng thư mục dữ liệu (014: lệnh `app start` báo đang chạy), không mở bản thứ hai.

**Phần lõi theo hệ điều hành**
- **FR-005**: Trên Windows, app MUST chạy phần lõi trong WSL2 bằng lệnh `app start` và `app stop` của 014, và mở giao diện qua `127.0.0.1` của Windows (WSL2 tự chuyển cổng). Ở 015, phần lõi là một bản studio đã có trong một bản Linux WSL của người dùng. Màn hình thiết lập liệt kê các bản Linux WSL2 trên máy, người dùng chọn một bản, và app tìm đường dẫn studio trong đó (mặc định `~/claude-Utube`, sửa được). Bản Linux riêng đóng gói sẵn để ở 016.
- **FR-006**: Trên macOS, app MUST chạy phần lõi thẳng trên máy bằng cùng các lệnh của 014.
- **FR-007**: Phần khác nhau giữa hai hệ điều hành MUST chỉ nằm ở cách gọi lệnh của phần lõi. Màn hình, khay, thoát và thiết lập dùng chung.

**Thiết lập lần đầu**
- **FR-008**: Lần đầu mở, hoặc khi cấu hình không còn dùng được, app MUST hiện màn hình thiết lập gồm:
  - kiểm điều kiện của máy (Windows: WSL2 và ảo hoá; cả hai: các công cụ của phần lõi, 014 R8);
  - chọn thư mục dữ liệu (mặc định theo hệ điều hành), kèm dung lượng trống;
  - nút Bắt đầu.

  Cấu hình được lưu ở thư mục cấu hình của app (theo hệ điều hành), ngoài thư mục dữ liệu.
- **FR-009**: Trên Windows chưa bật WSL2, app MUST có nút "Bật WSL" chạy lệnh bật WSL với quyền quản trị (Windows hỏi), rồi báo cần khởi động lại máy. App MUST NOT bật WSL khi người dùng chưa bấm và chưa đồng ý. Đây là ngoại lệ được hiến pháp cho phép (bản 2.2.0): app desktop được bật tính năng của hệ điều hành khi người dùng bấm và đồng ý quyền quản trị. Xưởng khi phát triển vẫn không tự cài phần mềm hệ thống.
- **FR-010**: Sau Bắt đầu, app MUST khởi động phần lõi rồi mở giao diện. Việc tạo chủ xưởng và đăng nhập Claude dùng các trang có sẵn của xưởng (008, 014); app không làm lại chúng.

**Khay và thoát**
- **FR-011**: App MUST có icon khay (macOS: thanh menu, icon tự đổi màu theo nền sáng hay tối) với các mục: Mở xưởng, Mở trong trình duyệt, Thư mục dữ liệu, Thư mục log, Đổi thiết lập, Thoát.
- **FR-012**: Đóng cửa sổ chính MUST NOT thoát app. Lần đầu đóng, app báo một lần rằng xưởng vẫn chạy ở khay.
- **FR-013**: Thoát MUST hỏi lại khi phần lõi còn việc đang chạy, nêu tên việc (lấy từ trạng thái của phần lõi, 014 `app status`). Đồng ý thì `app stop --force`; không có việc thì `app stop`. Sau khi thoát MUST không còn tiến trình nào của app hay của phần lõi, kể cả trong WSL.
- **FR-014**: App MUST theo dõi phần lõi khi đang mở. Phần lõi dừng ngoài ý muốn thì cửa sổ báo "Xưởng đã dừng" với nút "Khởi động lại".

**Kiểm chứng**
- **FR-015**: Phần logic của vỏ (chọn lệnh theo hệ điều hành, kiểm điều kiện, đọc trạng thái phần lõi, quyết định khi thoát) MUST có test tự động chạy được trên máy phát triển, không cần Windows hay macOS thật.
- **FR-016**: Một quy trình GitHub Actions MUST build app và chạy thử tự động trên máy Windows và macOS của GitHub: app mở được, cửa sổ chính tới được giao diện của một phần lõi, mở lần hai không tạo bản thứ hai, thoát không để lại tiến trình nào. Quy trình chạy khi đẩy nhánh của app desktop và khi người dùng bấm chạy tay, không chạy ở mọi lần đẩy, để tiết kiệm phút chạy.

### Key Entities

- **Cấu hình app (App config)**: hệ điều hành, thư mục dữ liệu, cách gọi phần lõi (Windows: tên bản Linux WSL và đường dẫn studio trong đó; macOS: đường dẫn studio), lần thiết lập cuối, đã báo "chạy ở khay" chưa.
- **Trạng thái phần lõi**: đang chạy hay không, địa chỉ, số việc đang chạy và tên việc; đọc từ `app status --json` của 014.
- **Kết quả kiểm máy**: danh sách điều kiện, mỗi điều kiện đạt hay thiếu kèm cách sửa.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Trên máy đã thiết lập, từ lúc mở app tới khi cửa sổ chính hiện giao diện xưởng mất dưới 30 giây (Windows và macOS).
- **SC-002**: Mở app lần hai không bao giờ tạo bản thứ hai (kiểm tự động trên logic, và bằng tay trên mỗi hệ điều hành).
- **SC-003**: Sau khi thoát, số tiến trình của app và phần lõi còn lại là 0, kể cả trong WSL (kiểm trên mỗi hệ điều hành).
- **SC-004**: Thoát khi đang có việc luôn hỏi trước; không có trường hợp nào việc bị dừng mà không có xác nhận (kiểm tự động trên logic thoát).
- **SC-005**: Một người chưa từng dùng làm xong thiết lập lần đầu và tới trang tạo chủ xưởng trong dưới 10 phút, không tính thời gian khởi động lại máy để bật WSL.

## Assumptions

- Phần lõi (014) chạy được trên máy đó. Đóng gói phần lõi và bộ cài là việc của 016.
- Hai hệ điều hành đích: Windows 10 (22H2) hoặc 11 bản 64-bit, và macOS trên chip Apple. Máy Mac chip Intel để sau.
- Bản chưa ký số; hướng dẫn vượt cảnh báo khi cài thuộc 016.
- Máy trạm (Client), cập nhật và license key nằm ngoài 015.
