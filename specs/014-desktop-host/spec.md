# Feature Specification: Chế độ máy chủ trên một máy (nền cho app desktop)

**Feature Branch**: `014-desktop-host`

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "Hướng app desktop giống neb-creative-tool, cách A: mỗi người cài app, tự chạy chế độ Máy chủ trên máy họ bằng tài khoản Claude và khoá YouTube của chính họ. 014 là bước đầu: một bộ code, chạy toàn bộ xưởng (giao diện, proxy, worker) trên một máy không cần Docker, dữ liệu trong một thư mục chọn được, cùng một bộ code với bản VPS."

## Clarifications

### Session 2026-11-11

- Q: Việc làm bằng chat trong VS Code có hiện trong app không? → A: Có, khi máy chủ đang chạy trên máy thì luồng chat ghi vào cùng sổ việc (FR-017).
- Q: Cửa sổ trên chính máy chủ có cần đăng nhập không? → A: Có, đăng nhập như bản online và neb (FR-008).

## Bối cảnh

Người dùng quyết định (2026-11-11) đưa xưởng thành một app desktop giống dự án neb-creative-tool của họ. Người ngoài công ty sẽ cài app và chạy chế độ Máy chủ trên máy của chính họ, đăng nhập bằng tài khoản Claude và khoá YouTube của họ. Gói Claude của chủ xưởng không được dùng để phục vụ người khác.

Lộ trình:
- **014**: chế độ máy chủ trên một máy;
- **015**: vỏ desktop và màn hình thiết lập;
- **016**: bộ cài, công cụ đi kèm, cập nhật;
- **017**: license key.

Hiện có hai cách chạy:
- **Local** (003): Claude làm phim trong khung chat, giao diện chỉ để theo dõi.
- **Online** (007–013): web, proxy và worker chạy bằng Docker, nhiều tài khoản, mọi tính năng 010–013 hiện trên giao diện.

014 đưa bản online về chạy được trọn trên **một máy, không cần Docker**, với dữ liệu nằm trong một thư mục do người dùng chọn. Đây là thứ mà vỏ desktop (015) sẽ khởi động. Bản VPS (Docker) vẫn chạy từ cùng một bộ code.

Mức quy trình: **Đầy đủ**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chạy cả xưởng trên máy mình bằng một lệnh (Priority: P1)

Người dùng chạy một lệnh. Xưởng khởi động giao diện, proxy và worker trên máy họ, không cần Docker, rồi in ra địa chỉ để mở trong trình duyệt. Lần đầu mở, họ tạo tài khoản chủ xưởng, đăng nhập tài khoản Claude của chính họ trong Settings, rồi giao một phim bằng form New film. Phim được làm tự động và hiện trên trang việc kèm các khối Quality, Publish; menu Channels và Topics hoạt động như bản online.

**Why this priority**: Đây là lõi mà app desktop cần. Không có nó thì vỏ desktop không có gì để chạy.

**Independent Test**: Trên một máy không có Docker, với thư mục dữ liệu trống, chạy lệnh khởi động. Kết quả cần thấy:
- địa chỉ trả lời trong 20 giây;
- tạo được chủ xưởng;
- giao một phim (agent giả trong test) thì việc chạy xong và có khối Quality;
- dừng xưởng thì không còn tiến trình nào của xưởng chạy.

**Acceptance Scenarios**:

1. **Given** một máy có đủ công cụ (theo kiểm tra trạng thái của xưởng) và không có Docker, **When** người dùng chạy lệnh khởi động với một thư mục dữ liệu, **Then** giao diện, proxy và worker cùng chạy, và lệnh in địa chỉ giao diện.
2. **Given** thư mục dữ liệu trống, **When** mở địa chỉ lần đầu, **Then** hiện màn hình tạo chủ xưởng; tạo xong thì vào thẳng xưởng.
3. **Given** chủ xưởng đã đăng nhập một tài khoản Claude trong Settings (008), **When** giao phim bằng form, **Then** worker chạy việc ngay trên máy (không container) và việc đi đủ các bước như bản online, gồm cổng QC, Script và Publish.
4. **Given** xưởng đang chạy, **When** người dùng chạy lệnh xem trạng thái, **Then** thấy từng phần (giao diện, proxy, worker) đang chạy hay không, địa chỉ, thư mục dữ liệu và nơi ghi log.
5. **Given** xưởng đang chạy, **When** người dùng chạy lệnh dừng, **Then** cả ba phần tắt sạch, kể cả các tiến trình con của việc đang chạy.

---

### User Story 2 - Chạy an toàn và bền (Priority: P2)

Xưởng không cho chạy hai bản cùng lúc trên một thư mục dữ liệu. Khi đang có việc tốn tiền chạy, lệnh dừng hỏi lại (hoặc từ chối nếu không có cờ bắt buộc). Khởi động lại sau khi tắt máy hay sập thì các việc dở được đưa lại hàng đợi. Mọi log nằm trong thư mục dữ liệu.

**Why this priority**: App desktop sẽ bị tắt, mở, sập bất cứ lúc nào. Không có phần này thì người dùng mất việc và mất tiền token. Nhưng nó cần lõi của US1.

**Independent Test**:
- chạy lệnh khởi động lần hai trên cùng thư mục → báo "đang chạy" kèm địa chỉ, không mở bản thứ hai;
- dừng khi có việc đang chạy → bị từ chối kèm tên việc, có cờ bắt buộc thì dừng và việc được đánh dấu là bị dừng;
- giết tiến trình rồi khởi động lại → việc dở trở lại hàng đợi và chạy tiếp.

**Acceptance Scenarios**:

1. **Given** xưởng đang chạy trên một thư mục dữ liệu, **When** khởi động thêm một lần trên cùng thư mục, **Then** lệnh báo đang chạy kèm địa chỉ và không mở bản thứ hai.
2. **Given** có việc đang chạy, **When** người dùng chạy lệnh dừng không có cờ bắt buộc, **Then** lệnh từ chối và nêu tên việc. Có cờ bắt buộc thì việc được đánh dấu "đã dừng" rồi xưởng tắt.
3. **Given** xưởng bị tắt đột ngột khi đang có việc, **When** khởi động lại, **Then** việc dở trở lại hàng đợi và chạy tiếp, theo cách hồi phục có sẵn của worker (007).
4. **Given** xưởng chạy nhiều ngày, **When** xem thư mục log, **Then** mỗi phần có tệp log riêng, và log cũ được xoay vòng (không phình mãi).
5. **Given** cổng mặc định đang bận, **When** khởi động, **Then** xưởng chọn cổng trống kế tiếp trong một khoảng cho trước và in đúng địa chỉ.

---

### User Story 3 - Mang dữ liệu cũ vào và làm phim bằng chat (Priority: P3)

Người dùng đã có phim, phong cách riêng và kênh trong thư mục dự án (cách làm bằng chat). Họ chạy một lệnh để đưa những thứ đó vào kho của chủ xưởng trong thư mục dữ liệu. Sau đó app hiện đủ phim, phong cách và kênh cũ.

**Why this priority**: Giúp chủ xưởng (người phát triển) chuyển sang dùng app mà không mất gì. Người dùng mới cài app không cần phần này.

**Independent Test**: Thư mục dự án mẫu có 2 phim, 1 phong cách và 1 kênh có bài học và đề. Chạy lệnh nhập. Kết quả cần thấy: app hiện đủ cả 4; chạy lại lệnh không tạo bản trùng; thư mục dự án không bị đổi.

**Acceptance Scenarios**:

1. **Given** thư mục dự án có `films/`, `my-styles/` và `channels/`, **When** chạy lệnh nhập vào một thư mục dữ liệu, **Then** chúng được chép vào kho của chủ xưởng và hiện trong app. Thư mục dự án giữ nguyên.
2. **Given** đã nhập một lần, **When** chạy lại lệnh nhập, **Then** không có bản trùng; mục đã có thì giữ, mục mới thì thêm.
3. **Given** xưởng đang chạy trên máy và người dùng làm phim bằng chat trong VS Code, **When** Claude ghi việc lên giao diện, **Then** việc đó hiện trong app: các lệnh ghi việc của luồng chat ghi vào cùng sổ việc của máy chủ đang chạy, dưới tên chủ xưởng, và các bước duyệt (review) bấm được trên app như bản local cũ (FR-017).

### Edge Cases

- Thiếu công cụ (ffmpeg, node, Claude Code, thư viện, gói Python của giao diện): lệnh khởi động không chạy, in đúng thứ còn thiếu và lệnh cài của xưởng (`sh bin/studio deps …`). Xưởng không tự cài phần mềm hệ thống (CLAUDE.md).
- Thư mục dữ liệu không ghi được hoặc nằm trong thư mục dự án: báo lỗi rõ, không khởi động.
- Thư mục dữ liệu của một phiên bản cũ hơn: chạy các bước nâng cấp dữ liệu có sẵn khi mở, sau khi sao lưu cơ sở dữ liệu.
- Máy không có tài khoản Claude nào đăng nhập: việc đứng chờ "Waiting for a Claude account" như bản online (008), và trang hiện chỗ đăng nhập.
- Tắt máy khi đang ghi cơ sở dữ liệu: dữ liệu không hỏng, nhờ cơ sở dữ liệu ghi theo giao dịch.
- Hai thư mục dữ liệu khác nhau trên cùng máy: chạy được cùng lúc, mỗi bản một cổng.

## Requirements *(mandatory)*

### Functional Requirements

**Khởi động và dừng**
- **FR-001**: Xưởng MUST có lệnh khởi động, xem trạng thái và dừng chế độ máy chủ trên một máy. Lệnh khởi động nhận thư mục dữ liệu (mặc định theo hệ điều hành; xem FR-005), in địa chỉ giao diện khi đã sẵn sàng, rồi chạy nền.
- **FR-002**: Chế độ máy chủ MUST chạy đủ ba phần (giao diện, proxy, worker) của bản online mà không cần Docker. Worker chạy mỗi việc thành một tiến trình trong thư mục riêng của việc trên chính máy đó.
- **FR-003**: Giao diện và proxy MUST chỉ nghe ở địa chỉ nội bộ của máy (`127.0.0.1`) trong 014. Mở cho máy khác (máy trạm) để sau.
- **FR-004**: Chế độ máy chủ và bản VPS MUST dùng cùng một bộ code. Chỗ khác nhau chỉ nằm ở cấu hình khởi động (biến môi trường), không có nhánh logic riêng trong code nghiệp vụ. Bản VPS (Docker) MUST chạy y như trước, và bộ test online hiện có MUST đạt mà không phải sửa.

**Dữ liệu**
- **FR-005**: Mọi dữ liệu của chế độ máy chủ MUST nằm trong thư mục dữ liệu: cơ sở dữ liệu, tài khoản, phim, phong cách, kênh, khoá bí mật (khoá YouTube, đăng nhập Claude), log, bộ nhớ tạm. Thư mục mặc định: `~/.local/share/claude-utube` trên Linux và WSL, `~/Library/Application Support/ClaudeUtube` trên macOS. Chế độ máy chủ MUST NOT ghi gì vào thư mục dự án.
- **FR-006**: Mở một thư mục dữ liệu cũ hơn MUST nâng cấp nó tự động, sau khi sao lưu cơ sở dữ liệu vào `<thư mục dữ liệu>/backup/`.
- **FR-007**: Lệnh nhập MUST chép `films/`, `my-styles/` và `channels/` (kể cả tệp đề và kênh mẫu bị git bỏ qua) của một thư mục dự án vào kho của chủ xưởng. Lệnh MUST bỏ qua mục đã có, và MUST NOT sửa hay xoá thư mục nguồn.

**Tài khoản**
- **FR-008**: Lần đầu mở MUST hiện màn hình tạo chủ xưởng (đã có ở 008). Cửa sổ trên chính máy chủ MUST đăng nhập như bản online và neb (email và mật khẩu, phiên có hạn như 007); không có lối vào tự động.
- **FR-009**: Ở chế độ máy chủ, chủ xưởng MUST không bị giới hạn số phim mỗi tháng, vì họ tự trả bằng tài khoản Claude của mình. Trần token của mỗi việc (008) vẫn giữ.

**An toàn khi chạy**
- **FR-010**: Mỗi thư mục dữ liệu MUST chỉ có một bản xưởng chạy. Lần khởi động thứ hai trên cùng thư mục MUST báo đang chạy kèm địa chỉ.
- **FR-011**: Lệnh dừng MUST từ chối khi có việc đang chạy, trừ khi có cờ bắt buộc. Có cờ thì các việc đang chạy được đánh dấu "đã dừng" và mọi tiến trình con bị tắt.
- **FR-012**: Khởi động lại MUST đưa các việc dở về hàng đợi, như cách hồi phục có sẵn của worker.
- **FR-013**: Mỗi phần MUST ghi log riêng vào `<thư mục dữ liệu>/logs/`, xoay vòng khi một tệp vượt 10 MB, giữ tối đa 5 tệp mỗi phần.
- **FR-014**: Cổng MUST tự chọn trong một khoảng cho trước khi cổng mặc định bận. Địa chỉ in ra và tệp trạng thái MUST là cổng thật.
- **FR-015**: Lệnh khởi động MUST kiểm tra công cụ cần có trước khi chạy, và báo thiếu gì kèm lệnh cài của xưởng. Xưởng MUST NOT tự cài phần mềm hệ thống.

**Agent không có container**
- **FR-017**: Khi chế độ máy chủ đang chạy trên máy, các lệnh ghi việc của luồng chat (`job start|step|run|done|fail`, `review request|wait`; specs/003) MUST ghi vào sổ việc của máy chủ đó, dưới tên chủ xưởng, thay cho sổ việc local cũ. Phim của luồng chat vẫn nằm trong thư mục dự án như hiện nay; app hiện việc và đường dẫn tới phim. Khi máy chủ không chạy, luồng chat dùng sổ việc local cũ như trước.
- **FR-016**: Không có container thì agent của mỗi việc MUST chỉ được giao thư mục việc của nó làm thư mục làm việc. Claude Code của việc MUST được chạy với các quyền giới hạn có sẵn của nó (chỉ thư mục việc, thư viện và công cụ của xưởng). Giới hạn này không chắc chắn bằng container; xem Assumptions.

### Key Entities

- **Thư mục dữ liệu (Data folder)**: nơi chứa mọi dữ liệu của một máy chủ: `db`, `accounts/`, `secrets/`, `logs/`, `backup/`, `cache/`, `jobs/`.
- **Phiên máy chủ (Host session)**: các tiến trình đang chạy (giao diện, proxy, worker), cổng, thời điểm bắt đầu, tệp khoá chống chạy trùng.
- **Lần nhập (Import)**: nguồn, các mục đã chép, các mục đã bỏ qua vì đã có.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Trên một máy không có Docker, từ lệnh khởi động tới khi giao diện trả lời mất dưới 20 giây (không tính lần chạy đầu cài gói).
- **SC-002**: Một phim giao bằng form chạy hết các bước ở chế độ máy chủ, với agent giả trong test, và có đủ khối Quality cùng Publish như bản online.
- **SC-003**: Sau lệnh dừng, không còn tiến trình nào của xưởng chạy (kiểm tự động).
- **SC-004**: Sau khi giết các tiến trình của xưởng giữa một việc rồi khởi động lại, việc đó chạy xong mà không cần người can thiệp.
- **SC-005**: Chạy cả bộ test online hiện có: 100% đạt, không phải sửa test (cùng một bộ code).
- **SC-006**: Trong suốt một lần chạy chế độ máy chủ, thư mục dự án không có tệp nào bị tạo hay đổi (kiểm tự động).

## Assumptions

- 014 chạy trên Linux và WSL (máy hiện tại). Bản desktop cho Windows (qua WSL) và macOS được chốt ở 015 và 016.
- Công cụ đã có sẵn trên máy như hiện nay (giao diện, gói online, giọng, nhạc, thư viện). Đóng gói chúng vào app là việc của 016.
- Không có container thì agent không bị cách ly chắc chắn khỏi máy. Chấp nhận được vì người dùng tự chạy app trên máy của chính họ bằng tài khoản Claude của họ (giống neb). Bản VPS nhiều người vẫn dùng container.
- Chế độ máy trạm, vỏ desktop, bộ cài, cập nhật và license key nằm ngoài 014.
