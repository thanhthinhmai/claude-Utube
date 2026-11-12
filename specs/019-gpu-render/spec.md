# Feature Specification: Xưởng dựng hình bằng GPU khi máy có GPU

**Feature Branch**: `019-gpu-render`

**Created**: 2026-11-12

**Status**: Draft

**Input**: User description: "Cả xưởng dùng GPU để dựng hình nếu máy có GPU. Hiện mọi bước mở trang phim trong trình duyệt (render video, ảnh tĩnh, xuất sự kiện, kiểm tra thời gian đọc chữ, qc đọc chữ trên màn hình, publish vẽ thumbnail) chạy WebGL bằng phần mềm trên Linux/WSL2, rất chậm: phim 3D 10 phút mất khoảng 6 giờ, và qc bị quá hạn 300 giây khi đọc chữ của phim dài. Trên máy WSL2 có GPU (đã đo: Intel UHD 730), mở trình duyệt đầy đủ có cửa sổ trên màn hình WSLg thì dùng được GPU và nhanh gấp khoảng 12 lần (phim 10 phút còn khoảng 24 phút); macOS đã dùng GPU sẵn. Muốn: xưởng tự nhận ra máy có dùng được GPU không, tự chọn cách mở trình duyệt có GPU cho mọi lệnh dựng hình và kiểm tra, quay về cách cũ khi không có GPU, báo rõ đang dùng GPU hay phần mềm; render dài chịu được trình duyệt bị đóng giữa chừng (làm tiếp, không làm lại từ đầu). Không sửa thư viện gốc, không tự cài phần mềm hệ thống."

## Clarifications

### Session 2026-11-12

- Q: Phần lõi chạy trong app desktop có dùng GPU ngay trong tính năng này không? → A: Có. Làm cho cả máy phát triển (chat, `sh bin/studio`) lẫn app desktop, và app dùng GPU thật (FR-016, User Story 4).
- Q: Đang ghi bằng GPU mà GPU hỏng giữa chừng thì xưởng làm gì? → A: Bỏ các phần đã vẽ bằng GPU, ghi lại cả video bằng phần mềm, báo rõ trong nhật ký và trạng thái (FR-007).

## Bối cảnh

Mọi phim của xưởng là một trang web vẽ bằng code. Các bước dựng hình và kiểm tra đều mở trang đó trong một trình duyệt chạy ngầm:
- ghi video, chụp ảnh tĩnh, xuất mốc âm thanh;
- kiểm tra thời gian đọc chữ trên màn hình;
- `qc` đọc mọi chữ hiện trên màn hình;
- gói đăng chụp khung để vẽ thumbnail.

Trên Linux và trong môi trường Linux chạy trong Windows, trình duyệt chạy ngầm không dùng được GPU nên vẽ 3D bằng CPU. Phim `films/pet-swap` (3D, 9 phút 32 giây, 30 khung/giây) cho số liệu thật trên máy của người dùng (Windows, GPU tích hợp Intel UHD 730, RAM 7 GB):

| | Vẽ bằng CPU | Vẽ bằng GPU (trình duyệt đầy đủ, có cửa sổ) |
|---|---|---|
| Tốc độ ghi video | khoảng 0,85 khung/giây | khoảng 10–12 khung/giây |
| Phim khoảng 9,5 phút | khoảng 5,5–6 giờ | khoảng 24 phút |
| `qc` đọc chữ trên màn hình | quá hạn 300 giây, `qc` dừng giữa chừng | xong cả lệnh `qc` trong 2 phút 47 giây |
| Chạy nhiều luồng | không nhanh hơn; 6 luồng làm hết RAM | 2 luồng chạy ổn |

Trong phim đó, cách làm thủ công đã chạy được: một script ghi video riêng của phim, và một lớp bọc trình duyệt để các lệnh có sẵn của thư viện và của xưởng dùng GPU (xem `films/pet-swap/render_gpu.mjs`, `films/pet-swap/chrome-gpu.sh`). Một lần trình duyệt bị đóng giữa chừng làm hỏng cả lượt ghi video; bản sau chia phim thành từng đoạn, đoạn xong thì giữ, nên chịu được việc này.

macOS đã dùng GPU sẵn. Tính năng này đưa cách làm trên thành mặc định của cả xưởng.

Mức quy trình: **Đầy đủ**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Phim được dựng bằng GPU mà không phải làm gì thêm (Priority: P1)

Người dùng làm phim như thường. Khi tới bước ghi video, xưởng tự dùng GPU nếu máy dùng được. Lệnh kiểm tra trạng thái của xưởng cho biết máy đang dựng hình bằng GPU hay bằng phần mềm, và nếu chưa dùng được GPU thì vì sao và cần làm gì. Trên máy không có GPU dùng được, mọi lệnh vẫn chạy như cũ.

**Why this priority**: Đây là phần đem lại lợi ích chính: phim dài từ vài giờ còn vài chục phút. Nó tự chạy được và tự kiểm được mà không cần các story sau.

**Independent Test**: Trên máy tham chiếu, chạy lệnh trạng thái rồi ghi video phim `pet-swap`. Kết quả cần thấy:
- lệnh trạng thái báo "GPU" kèm tên GPU;
- video có đủ số khung;
- thời gian ghi không quá 40 phút.

Đặt xưởng ở chế độ ép dùng phần mềm, chạy lại trên 30 giây đầu của phim: lệnh trạng thái báo "phần mềm", video vẫn ra đúng số khung.

**Acceptance Scenarios**:

1. **Given** một máy dùng được GPU và đã có thành phần trình duyệt cần cho GPU, **When** người dùng chạy lệnh trạng thái, **Then** dòng dựng hình ghi "GPU" kèm tên GPU mà trình duyệt nhận.
2. **Given** máy như trên, **When** xưởng ghi video một phim, **Then** video được vẽ bằng GPU. Nhật ký của lần ghi ghi rõ chế độ và tên GPU ở dòng đầu.
3. **Given** một máy không dùng được GPU (không có GPU, hoặc chạy không có màn hình), **When** chạy lệnh trạng thái rồi ghi video, **Then** lệnh trạng thái ghi "phần mềm" kèm lý do. Video vẫn ghi được như hiện nay, chỉ chậm hơn.
4. **Given** máy có GPU nhưng thiếu thành phần trình duyệt cần cho GPU, **When** chạy lệnh trạng thái, **Then** xưởng ghi "phần mềm", nói thiếu gì và in đúng một lệnh để tải nó. Xưởng không tự tải.
5. **Given** người dùng muốn tắt GPU (ví dụ cửa sổ trình duyệt làm phiền họ), **When** họ đặt chế độ ép dùng phần mềm, **Then** mọi lệnh dựng hình và kiểm tra dùng phần mềm cho tới khi họ bỏ chế độ đó.
6. **Given** đang ghi bằng GPU, **When** GPU hỏng giữa chừng (trình duyệt rơi về vẽ bằng phần mềm), **Then** xưởng bỏ các phần đã vẽ bằng GPU và ghi lại cả video bằng phần mềm. Nhật ký và trạng thái của việc ghi rõ việc chuyển này. Video cuối không trộn hai cách vẽ.

---

### User Story 2 - Mọi lệnh kiểm tra cũng dùng GPU (Priority: P2)

Các lệnh khác cũng mở trang phim: chụp ảnh tĩnh, xuất mốc âm thanh, kiểm tra thời gian đọc chữ, `qc` đọc chữ trên màn hình, gói đăng vẽ thumbnail. Chúng dùng cùng chế độ dựng hình như bước ghi video, nên `qc` của phim dài không còn bị quá hạn.

**Why this priority**: Không có story này, phim dài ghi xong nhanh nhưng vẫn kẹt ở bước kiểm tra (`qc` quá hạn 300 giây với `pet-swap`). Story 1 vẫn có giá trị riêng mà không cần nó.

**Independent Test**: Trên máy tham chiếu, chạy `qc pet-swap` và `publish pet-swap` mà không đặt biến hay cờ gì thêm. Cả hai chạy hết, không quá hạn, và `qc` xong trong 5 phút.

**Acceptance Scenarios**:

1. **Given** máy dùng được GPU, **When** chạy `qc` của một phim dài 10 phút, **Then** bước đọc chữ trên màn hình xong trong hạn, và kết quả của `qc` ghi chế độ dựng hình đã dùng.
2. **Given** máy dùng được GPU, **When** chạy lệnh chụp ảnh tĩnh, xuất mốc âm thanh, kiểm tra thời gian đọc chữ, hoặc vẽ thumbnail của gói đăng, **Then** lệnh dùng GPU mà không cần người dùng đặt biến hay cờ.
3. **Given** máy không dùng được GPU, **When** chạy các lệnh trên, **Then** chúng chạy như hiện nay.

---

### User Story 3 - Ghi video dài chịu được gián đoạn (Priority: P3)

Ghi video một phim dài mất nhiều phút. Nếu trình duyệt bị đóng (người dùng tắt cửa sổ, trình duyệt sập) hoặc lệnh bị dừng giữa chừng, xưởng mở lại trình duyệt và làm tiếp. Chạy lại lệnh ghi video thì xưởng làm tiếp phần còn thiếu, không làm lại từ đầu.

**Why this priority**: Khi ghi bằng GPU, cửa sổ trình duyệt hiện trên màn hình của người dùng và có thể bị tắt nhầm. Trong `pet-swap` việc này đã xảy ra một lần. Story 1 và 2 vẫn chạy được mà không cần story này.

**Independent Test**: Ghi video một phim. Giữa chừng, đóng trình duyệt một lần. Video cuối vẫn có đủ số khung, và phần phải làm lại không quá 10 giây phim. Sau đó dừng hẳn lệnh ghi giữa chừng rồi chạy lại: phần đã xong được giữ, video cuối giống hệt khi chạy liền một mạch.

**Acceptance Scenarios**:

1. **Given** đang ghi video, **When** một cửa sổ trình duyệt bị đóng, **Then** xưởng mở lại trình duyệt và làm tiếp, video cuối đủ khung. Xưởng thử lại tối đa 3 lần cho mỗi phần; quá số đó thì dừng và báo lỗi.
2. **Given** lệnh ghi bị dừng giữa chừng, **When** chạy lại cùng lệnh, **Then** xưởng chỉ làm phần còn thiếu, và báo đã có bao nhiêu phần, còn bao nhiêu phần.
3. **Given** nguồn của phim đã đổi kể từ lần ghi trước, **When** chạy lại lệnh ghi, **Then** xưởng bỏ các phần cũ và ghi lại từ đầu, không trộn hình cũ với hình mới.

### User Story 4 - App desktop cũng dựng bằng GPU (Priority: P4)

Người dùng cài app desktop trên Windows hoặc macOS và giao phim qua app. Phần lõi của app tự dùng GPU của máy khi được, cho cả bước ghi video lẫn các bước kiểm tra. Màn hình trạng thái của app cho biết đang dùng GPU hay phần mềm, và nếu là phần mềm thì vì sao.

**Why this priority**: Người dùng app là đối tượng chính của sản phẩm (specs/014–018), nên app cũng phải nhanh như máy phát triển. Story này dựa trên cơ chế của story 1–3, nên làm sau cùng.

**Independent Test**: Trên máy tham chiếu, cài app từ bộ cài mới (chế độ Host), giao một phim 3D ngắn (khoảng 30 giây) qua app. Kết quả cần thấy:
- màn hình trạng thái của app ghi "GPU" kèm tên GPU;
- nhật ký của việc ghi chế độ GPU;
- video có đủ khung, và thời gian ghi không quá 1/5 thời gian của cùng phim khi ép dùng phần mềm.

**Acceptance Scenarios**:

1. **Given** app (chế độ Host) trên Windows, máy có GPU và môi trường Linux có màn hình đồ hoạ, **When** worker của app ghi video một phim, **Then** video được vẽ bằng GPU, và màn hình trạng thái ghi "GPU" kèm tên GPU.
2. **Given** app trên macOS, **When** worker ghi video, **Then** video được vẽ bằng GPU, như bản macOS hiện nay vẫn làm.
3. **Given** app trên một máy Windows mà môi trường Linux không có màn hình đồ hoạ, **When** mở màn hình trạng thái, **Then** app ghi "phần mềm", nói thiếu gì và cách bật. Phim vẫn làm được, chỉ chậm hơn.
4. **Given** app ở chế độ Client (specs/018), **When** người dùng xem trạng thái, **Then** app hiện chế độ dựng hình của máy Host, vì Client không tự dựng hình.

### Edge Cases

- **Máy có GPU nhưng đang chạy không có màn hình** (ví dụ qua kết nối từ xa không có màn hình đồ hoạ): dùng phần mềm và nói lý do.
- **Chế độ online** (`STUDIO_MODE=online`, container trên VPS không có GPU): dùng phần mềm như hiện nay, không cố mở cửa sổ.
- **Hai lệnh dựng hình chạy cùng lúc trên một GPU** (ghi video và `qc`): cả hai vẫn ra đúng kết quả; chậm hơn thì chấp nhận được.
- **Kết quả nhận diện GPU cũ**, ví dụ sau khi cập nhật driver hoặc đổi máy: lệnh trạng thái luôn kiểm lại, không tin vào kết quả đã lưu.
- **Ảnh vẽ bằng GPU khác chút ít với ảnh vẽ bằng phần mềm** (khác biệt nhỏ về làm mượt cạnh và độ sâu trường ảnh): chấp nhận được trong giới hạn ở SC-005. Phim không được trộn hai cách vẽ trong cùng một video.
- **Cửa sổ trình duyệt hiện lên lúc ghi:** người dùng được báo trước trong nhật ký và lệnh trạng thái, kèm lời dặn đừng đóng cửa sổ.
- **Thiếu RAM:** số luồng mặc định không được làm hết RAM của máy 7 GB như lần chạy 6 luồng.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Xưởng PHẢI tự nhận ra máy có dựng hình bằng GPU được không, bằng cách mở thử trình duyệt và đọc tên bộ vẽ thật, không đoán theo loại máy. Lần mở thử phải xong trong 30 giây.
- **FR-002**: Lệnh trạng thái của xưởng (`sh bin/studio status`, kể cả dạng `--json`) PHẢI có một dòng "dựng hình" ghi chế độ (GPU hoặc phần mềm), tên bộ vẽ, và khi là phần mềm thì ghi lý do kèm cách khắc phục nếu có.
- **FR-003**: Khi máy dùng được GPU, mọi lệnh của xưởng có mở trang phim PHẢI tự dùng GPU, không cần người dùng đặt biến hay cờ. Các lệnh đó gồm: ghi video, ảnh tĩnh, xuất mốc âm thanh, kiểm tra thời gian đọc chữ, `qc`, gói đăng (thumbnail).
- **FR-004**: Khi máy không dùng được GPU, các lệnh trên PHẢI chạy như hiện nay, cho ra kết quả giống hiện nay.
- **FR-005**: Người dùng PHẢI ép được xưởng dùng phần mềm bằng một thiết lập bền (vẫn còn sau khi khởi động lại), và bỏ ép được bằng cùng cách.
- **FR-006**: Mỗi lần ghi video và mỗi lần chạy `qc` PHẢI ghi chế độ dựng hình và tên bộ vẽ vào nhật ký hoặc kết quả của nó.
- **FR-007**: Trong một lần ghi video, nếu một lần mở trình duyệt định dùng GPU mà lại rơi về phần mềm, xưởng PHẢI bỏ mọi phần đã vẽ bằng GPU của lần ghi đó và ghi lại cả video bằng phần mềm. Một video không được trộn hình vẽ bằng hai cách. Việc chuyển này PHẢI được ghi vào nhật ký của lần ghi (lý do, thời điểm) và hiện trên trạng thái của việc.
- **FR-008**: Ghi video PHẢI chia phim thành các phần không quá 10 giây và giữ lại phần đã xong. Trình duyệt bị đóng thì mở lại và làm tiếp, tối đa 3 lần thử cho mỗi phần. Chạy lại lệnh thì chỉ làm phần còn thiếu.
- **FR-009**: Các phần đã xong chỉ được dùng lại khi nguồn của phim (trang, mã, dữ liệu, dòng thời gian), độ phân giải và số khung/giây không đổi. Có đổi thì PHẢI ghi lại từ đầu.
- **FR-010**: Video ghép từ các phần PHẢI có đúng số khung (thời lượng × số khung/giây, làm tròn lên), các phần nối không trùng và không thiếu khung.
- **FR-011**: Số luồng ghi mặc định PHẢI vừa sức máy: mỗi luồng chỉ được thêm vào khi còn đủ RAM, không làm hết RAM của máy tham chiếu (7 GB).
- **FR-012**: Xưởng KHÔNG ĐƯỢC sửa file nào trong thư viện gốc (hiến pháp VI), và KHÔNG ĐƯỢC tự cài phần mềm hệ thống (hiến pháp, mục "Phần mềm hệ thống").
- **FR-013**: Thành phần trình duyệt cần cho GPU (nếu thiếu) chỉ được tải khi người dùng chạy lệnh cài gói của xưởng. Lệnh trạng thái in đúng lệnh đó. Thành phần này nằm trong thư mục người dùng, không phải gói của hệ điều hành.
- **FR-014**: Luồng làm phim trong `CLAUDE.md` PHẢI dùng lệnh ghi video của xưởng, để phim mới tự được hưởng FR-003 đến FR-010.
- **FR-015**: Chế độ online (container) PHẢI giữ cách dựng hình bằng phần mềm như hiện nay, không cố dùng GPU, không đổi kết quả.
- **FR-016**: Phần lõi chạy trong app desktop PHẢI dùng cùng cơ chế: tự nhận ra GPU, dùng GPU khi được, quay về phần mềm khi không. Điều này áp dụng cho cả bản Linux `ClaudeUtube` trên Windows (specs/016) và bản macOS. Việc của app (worker làm phim, `qc`, gói đăng) PHẢI được hưởng FR-003 đến FR-010 như trên máy phát triển.
- **FR-017**: Bộ cài của app PHẢI mang sẵn thành phần trình duyệt cần cho GPU, để người dùng app không phải chạy lệnh nào thêm. Thành phần đó PHẢI được ghi vào `CREDITS` kèm giấy phép.
- **FR-018**: App PHẢI hiện chế độ dựng hình (GPU kèm tên GPU, hoặc phần mềm kèm lý do) ở chỗ người dùng xem trạng thái của xưởng. Khi là phần mềm vì máy thiếu điều kiện của hệ điều hành (ví dụ không có màn hình đồ hoạ cho môi trường Linux), app chỉ nói thiếu gì và cách bật. App KHÔNG ĐƯỢC tự bật tính năng nào của hệ điều hành ngoài các trường hợp hiến pháp đã cho phép.
- **FR-019**: Cửa sổ trình duyệt mà app mở để dựng bằng GPU KHÔNG ĐƯỢC che cửa sổ làm việc của người dùng. Nó phải nằm ngoài vùng nhìn hoặc ở dạng thu nhỏ, nếu hệ điều hành cho phép mà vẫn giữ được GPU. Nếu không làm được thì app báo trước cho người dùng.

### Key Entities

- **Chế độ dựng hình**: GPU hoặc phần mềm. Kèm tên bộ vẽ, lý do (khi là phần mềm), thời điểm kiểm, và nguồn quyết định (tự nhận ra hay người dùng ép).
- **Phần video**: một đoạn liên tiếp tối đa 10 giây của một lần ghi. Có số thứ tự, khung đầu và khung cuối, trạng thái (xong hoặc chưa), và dấu vân tay của nguồn phim để biết có dùng lại được không.
- **Lần ghi video**: phim, độ phân giải, số khung/giây, số luồng, chế độ dựng hình, các phần, kết quả cuối, nhật ký.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Trên máy tham chiếu, ghi video phim `pet-swap` (9 phút 32 giây, 1080p, 30 khung/giây) bằng lệnh của xưởng xong trong **40 phút**, so với khoảng 5,5–6 giờ hiện nay. Video có đúng 17.153 khung.
- **SC-002**: Trên máy tham chiếu, `qc pet-swap` chạy hết mà không bị quá hạn, xong trong **5 phút**, không cần đặt biến hay cờ.
- **SC-003**: Trên máy không dùng được GPU, mọi lệnh dựng hình và kiểm tra cho ra kết quả giống hệt bản hiện tại: cùng số khung, cùng chữ đọc được. Thời gian chênh không quá 10%.
- **SC-004**: Đóng trình duyệt một lần giữa lúc ghi: video cuối vẫn đủ khung, phần làm lại không quá 10 giây phim. Dừng hẳn rồi chạy lại: không phần nào đã xong bị ghi lại.
- **SC-005**: Trên 10 khung mẫu của `pet-swap`, ảnh vẽ bằng GPU khác ảnh vẽ bằng phần mềm trung bình không quá **8/255** mỗi kênh màu, và chữ trên màn hình giống nhau từng ký tự.
- **SC-006**: Lệnh trạng thái báo đúng chế độ trong 3 tình huống trên máy tham chiếu: có GPU; không có màn hình; thiếu thành phần trình duyệt. Mỗi lần báo xong trong 30 giây.
- **SC-007**: Không file nào trong `lib/` bị đổi (kiểm bằng git), và không gói hệ điều hành nào được cài trong lúc chạy test.
- **SC-008**: Trên máy tham chiếu, app cài từ bộ cài mới ghi video một phim 3D 30 giây bằng GPU trong không quá 1/5 thời gian của cùng phim khi ép dùng phần mềm. Màn hình trạng thái của app báo đúng chế độ.

## Assumptions

- Máy tham chiếu: Windows, môi trường Linux có màn hình đồ hoạ tích hợp, GPU Intel UHD 730, RAM 7 GB. Các số đo trong Bối cảnh lấy từ máy này ngày 2026-11-12.
- Trên Linux, dùng được GPU khi có màn hình đồ hoạ (có cửa sổ) và driver cho phép trình duyệt đầy đủ vẽ bằng GPU. Không có màn hình thì dùng phần mềm. Xưởng không tìm cách vẽ bằng GPU khi không có màn hình.
- macOS đã dùng GPU qua thư viện. Tính năng chỉ cần báo đúng chế độ ở đó và dùng chung cơ chế chia phần (story 3).
- Một cửa sổ trình duyệt hiện trên màn hình lúc dựng bằng GPU là chấp nhận được. Người dùng tắt được GPU bằng FR-005.
- Thành phần trình duyệt đầy đủ (khoảng 190 MB) là gói tải vào thư mục của người dùng, giống các gói khác mà lệnh cài gói của xưởng tải, không phải phần mềm hệ thống.
- Lệnh ghi video của thư viện vẫn dùng được trực tiếp. Lệnh của xưởng là lối mặc định, không chặn lối kia.
- App desktop trên Windows chạy phần lõi trong bản Linux riêng của nó. Bản đó dùng chung màn hình đồ hoạ của môi trường Linux trong Windows như các bản Linux khác, nếu máy có. Điều này sẽ được kiểm lại ở bước plan.
- Bộ cài lớn thêm khoảng 190 MB vì phải mang trình duyệt đầy đủ. Chấp nhận được, vì người dùng đã chọn dùng GPU trong app.
- Phim cũ (như `pet-swap`) giữ nguyên script riêng của nó. Tính năng không phải chuyển các phim đã giao sang cách mới.
