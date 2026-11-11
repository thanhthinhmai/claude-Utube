# Feature Specification: Chế độ Client của app desktop

**Feature Branch**: `018-desktop-client`

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "Chế độ Client của app desktop": một bộ cài, chọn **Host** (chạy cả xưởng) hoặc **Client** (chỉ cửa sổ app, nối vào Host), như neb-creative-tool.

## Clarifications

### Session 2026-11-11

- Q: Kết nối Client–Host mã hoá thế nào? → A: Host tự tạo chứng chỉ HTTPS riêng. Lúc ghép đôi, Client ghi nhớ dấu vân tay của Host và chỉ nối vào đúng Host đó (FR-008).
- Q: Client có cần license key riêng? → A: Không. Client dùng license của Host; Host bị khoá thì Client cũng bị khoá (FR-010).
- Q: Client lấy bản mới từ đâu? → A: Qua Host. Host chuyển tiếp bản phát hành có chữ ký cho các Client đã ghép đôi (FR-011).

## Bối cảnh

Hiện app desktop (015, 016, 017) chỉ có một chế độ: mỗi máy chạy cả xưởng của mình. Phần lõi chỉ nghe ở `127.0.0.1` (014 FR-003), nên chỉ chính máy đó dùng được.

neb-creative-tool có hai chế độ trong cùng một bộ cài:
- **Host**: máy của chủ xưởng hoặc một máy trong nhóm. Chạy cả xưởng: cơ sở dữ liệu, worker, tài khoản AI, phim.
- **Client**: máy của thành viên. Chỉ có cửa sổ app, nối vào Host qua mạng LAN hoặc Tailscale, đăng nhập bằng tài khoản member do chủ xưởng tạo.

018 làm điều tương tự cho claude-Utube:
- Cả nhóm dùng chung một kho phim, một bộ tài khoản Claude và hạn mức của Host.
- Người dùng và vai trò đã có sẵn từ 008: chủ xưởng thêm người trong Settings → Users.

**Lưu ý về điều khoản**: gói Claude Pro hoặc Max là gói cá nhân. Như hướng dẫn chế độ online (`deploy/README.md`), Host chỉ nên chia cho **nhóm nội bộ** của chủ xưởng, và chủ xưởng chịu trách nhiệm việc này. App nhắc điều này khi bật chia sẻ.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Host mở chia sẻ, thành viên nối vào bằng app Client (Priority: P1)

Chủ xưởng bật "Share with my team" trên app Host. App hiện địa chỉ để thành viên nối vào (theo mạng LAN và Tailscale nếu có) cùng một mã ghép đôi. Thành viên cài cùng bộ cài đó, chọn **Connect to a studio**, nhập địa chỉ và mã ghép đôi, rồi đăng nhập bằng tài khoản chủ xưởng đã tạo cho họ. Họ làm phim như trên Host; phim nằm trên Host.

**Why this priority**: đây là toàn bộ giá trị của chế độ Client.

**Independent Test**:
1. Hai máy trong cùng mạng LAN (hoặc hai tiến trình trên một máy, với Host giả).
2. Host bật chia sẻ. Client nhập địa chỉ và mã, đăng nhập member, giao một phim giả.
3. Phim chạy trên Host, và Client thấy tiến độ và kết quả.

**Acceptance Scenarios**:

1. **Given** Host đang chạy, **When** chủ xưởng bật chia sẻ, **Then** app hiện các địa chỉ nối vào, mã ghép đôi, và lời nhắc chỉ chia cho nhóm nội bộ. Tắt chia sẻ thì không máy nào ngoài Host nối vào được nữa.
2. **Given** Client có địa chỉ và mã đúng, **When** nối vào, **Then** app hiện trang đăng nhập của xưởng trên Host. Member đăng nhập và thấy đúng những gì vai trò member được thấy (008).
3. **Given** mã ghép đôi sai, **When** Client nối vào, **Then** app từ chối và không gửi mật khẩu nào. Sai quá 10 lần trong 10 phút từ một địa chỉ thì Host tạm chặn địa chỉ đó.
4. **Given** Client đã ghép đôi, **When** mở app lần sau, **Then** app nối thẳng vào Host đã nhớ, không hỏi lại mã.
5. **Given** Client đang làm việc, **When** Host tắt hoặc mất mạng, **Then** Client hiện "Cannot reach the studio", có nút thử lại. Phim đang chạy trên Host không bị ảnh hưởng bởi việc Client mất kết nối.

---

### User Story 2 - Kết nối an toàn (Priority: P1)

Mật khẩu và phiên đăng nhập của thành viên đi qua mạng. Kết nối giữa Client và Host phải được mã hoá, và Client chỉ tin đúng Host đã ghép đôi.

**Why this priority**: không có phần này thì ai trong cùng mạng cũng đọc được mật khẩu, hoặc giả làm Host.

**Independent Test**: bắt gói tin giữa Client và Host thì không thấy mật khẩu. Một máy giả làm Host ở cùng địa chỉ thì Client từ chối nối.

**Acceptance Scenarios**:

1. **Given** Client và Host đã ghép đôi, **When** Client gửi mật khẩu, **Then** dữ liệu đi qua HTTPS bằng chứng chỉ riêng của Host, và Client chỉ chấp nhận đúng dấu vân tay đã ghi nhớ lúc ghép đôi.
2. **Given** một máy khác trả lời ở địa chỉ của Host, **When** Client nối vào, **Then** Client từ chối và báo "This is not the studio you paired with".

---

### User Story 3 - Client nhận bản mới và license (Priority: P2)

Thành viên không phải tự tìm bản cài mới. App Client dùng được mà không bắt mỗi thành viên nhập license key riêng.

**Why this priority**: bớt việc cho chủ xưởng và thành viên. Không có nó Client vẫn dùng được, chỉ phiền hơn.

**Independent Test**: Host có bản mới hơn Client. Client được báo và cài được bản mới (Windows cài khi thoát; macOS mở `.dmg`).

**Acceptance Scenarios**:

1. **Given** Client mở app, **When** cần license, **Then** Client không hỏi key. Nếu Host đang bị khoá (017), Client thấy trang "claude-Utube is locked" của Host.
2. **Given** có bản mới, **When** Client kiểm, **Then** Client lấy bản mới qua Host (Host chuyển tiếp từ máy chủ license bằng license của chính nó), kiểm chữ ký và SHA-256 như 017, rồi cài (Windows) hoặc mở `.dmg` (macOS).

---

### Edge Cases

- **Host trên Windows**: phần lõi chạy trong WSL2, mà các máy khác trong mạng không vào thẳng được WSL2 nếu không có quyền quản trị. Cổng chia sẻ nằm trong app Host (phía Windows hoặc macOS) rồi chuyển vào phần lõi, nên không cần quyền quản trị. Lần đầu bật chia sẻ, tường lửa của hệ điều hành có thể hỏi cho phép app nhận kết nối; app báo trước điều này.
- **macOS 15 trở lên, Client**: macOS hỏi quyền "tìm thiết bị trong mạng cục bộ". Bấm Allow; lỡ từ chối thì bật lại ở System Settings → Privacy & Security → Local Network. App giải thích khi không nối được.
- **Địa chỉ của Host đổi** (DHCP): Client nối không được thì cho sửa địa chỉ. Host đã ghép đôi được nhận ra theo danh tính của nó, không theo địa chỉ, nên không phải ghép đôi lại.
- **Host bị khoá license (017)**: Client thấy trang "claude-Utube is locked" của Host.
- **Đổi chế độ**: tray → "Change setup…" cho đổi giữa Host và Client. Dữ liệu của Host không bị xoá khi máy đó chuyển sang Client.
- **Máy Client không có WSL2 hay ổ trống**: Client không cần WSL2 hay chỗ trống cho phần lõi. Màn hình thiết lập không kiểm những thứ đó ở chế độ Client.

## Requirements *(mandatory)*

### Functional Requirements

**Chọn chế độ**
- **FR-001**: Màn hình thiết lập lần đầu MUST cho chọn: **Run the studio on this computer** (Host, như 015/016) hoặc **Connect to a studio** (Client). Đổi được sau này qua "Change setup…".

**Host**
- **FR-002**: App Host MUST có nút bật và tắt "Share with my team" (mặc định tắt). Khi bật, app mở một cổng chia sẻ cho mạng và chuyển các kết nối vào phần lõi ở `127.0.0.1`. Phần lõi vẫn chỉ nghe ở `127.0.0.1`.
- **FR-003**: Khi chia sẻ, app MUST hiện:
  - các địa chỉ nối vào: địa chỉ LAN, và địa chỉ Tailscale nếu máy có;
  - mã ghép đôi;
  - lời nhắc chỉ chia cho nhóm nội bộ.

  Chủ xưởng đổi được mã ghép đôi; đổi mã thì các Client mới phải dùng mã mới, còn các Client đã ghép đôi vẫn nối được.
- **FR-004**: Cổng chia sẻ MUST chỉ chuyển kết nối của Client đã ghép đôi. Ghép đôi sai bị giới hạn 10 lần mỗi 10 phút cho mỗi địa chỉ. Chủ xưởng xem được danh sách Client đã ghép đôi (tên máy, lần thấy cuối) và gỡ được từng máy.
- **FR-005**: Phần lõi MUST hoạt động đúng khi được mở qua cổng chia sẻ: đăng nhập, cookie, kiểm nguồn gửi (CSRF) và đường dẫn trong trang theo đúng địa chỉ Client đang dùng.

**Client**
- **FR-006**: App Client MUST không cần WSL2, phần lõi hay mô hình. Nó chỉ có cửa sổ chính mở xưởng của Host, khay, và thiết lập kết nối.
- **FR-007**: Client MUST nhớ Host đã ghép đôi: địa chỉ, và danh tính của Host dùng để kiểm kết nối. Lần mở sau Client nối thẳng vào. Mất kết nối thì Client hiện trang "Cannot reach the studio" với nút thử lại và nút sửa địa chỉ.
- **FR-008**: Kết nối Client–Host MUST được mã hoá, và Client MUST chỉ nối vào đúng Host đã ghép đôi (US2).
  - Host tự tạo một chứng chỉ riêng, giữ suốt đời của Host.
  - Lúc ghép đôi, hai bên chứng minh cùng biết mã ghép đôi mà không gửi mã qua mạng, và gắn bằng chứng đó với dấu vân tay của chứng chỉ. Máy đứng giữa vì thế không giả được Host.
  - Mã ghép đôi chỉ dùng được trong 10 phút sau khi chủ xưởng bấm "Add a computer".
- **FR-009**: Thoát Client MUST không ảnh hưởng tới Host hay các phim đang chạy trên Host.

**License và cập nhật**
- **FR-010**: Client MUST không hỏi license key. Chế độ Client không kiểm license; Host kiểm license của chính nó (017), và khi Host bị khoá thì mọi trang qua cổng chia sẻ là trang khoá.
- **FR-011**: Client MUST kiểm bản mới qua Host theo lịch của 017:
  - Host chuyển tiếp danh sách và tệp của bản phát hành từ máy chủ license, bằng lease của chính Host, và chỉ cho Client đã ghép đôi;
  - Client kiểm chữ ký `release.json` bằng khoá công khai có sẵn trong app, rồi kiểm SHA-256 của tệp;
  - Windows cài khi thoát, macOS mở `.dmg`.

  Bản build không có license (không có máy chủ license) thì Client không tự cập nhật.

### Key Entities

- **Chế độ** (cấu hình app): `host` hoặc `client`.
- **Chia sẻ** (trên Host): bật hay tắt, cổng, mã ghép đôi (chỉ lưu dạng băm), danh tính của Host, danh sách Client đã ghép đôi (mã Client, tên máy, lần đầu và lần cuối thấy, đã gỡ chưa).
- **Host đã ghép đôi** (trên Client): địa chỉ, danh tính của Host, mã Client do Host cấp, lúc ghép đôi.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Một thành viên cài app, ghép đôi và đăng nhập vào Host trong cùng mạng LAN trong dưới 3 phút, không gõ lệnh nào (kiểm bằng tay một lần).
- **SC-002**: Bắt gói tin giữa Client và Host thì không thấy mật khẩu hay cookie nào (kiểm tự động trong test bằng cách đọc dòng dữ liệu đi qua cổng chia sẻ).
- **SC-003**: Một máy chưa ghép đôi, hoặc một máy giả làm Host, bị từ chối 100% (kiểm tự động).
- **SC-004**: Tắt chia sẻ thì cổng mạng đóng trong dưới 2 giây (kiểm tự động).
- **SC-005**: Một phim giao từ Client chạy xong trên Host, và Client thấy tiến độ và kết quả như trên Host (kiểm tự động với phần lõi giả, và bằng tay một lần với phần lõi thật).

## Assumptions

- Thành viên và Host ở cùng mạng LAN, hoặc cùng một mạng Tailscale do chủ xưởng tự lập. 018 không dựng đường hầm qua Internet (Cloudflare Tunnel hay tương tự); có thể làm ở một spec sau.
- Tài khoản member do chủ xưởng tạo trong Settings → Users (008). 018 không thêm cách đăng ký mới.
- Số Client nhỏ (dưới 20).
- Host có thể là app trên Windows hoặc macOS. Client có thể là Windows hoặc macOS, bất kể Host là gì.
