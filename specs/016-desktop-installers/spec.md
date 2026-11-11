# Feature Specification: Bộ cài app desktop và phần lõi đóng gói sẵn

**Feature Branch**: `016-desktop-installers`

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "làm 016" — bộ cài app desktop cho Windows (qua WSL2) và macOS, kèm phần lõi đóng gói sẵn, để người ngoài công ty cài được mà không cần một bản studio có sẵn (lộ trình app desktop, hướng A).

## Clarifications

### Session 2026-11-11

- Q: Phần nặng (mô hình) đi kèm thế nào? → A: App tải lúc thiết lập từ nơi phát hành gốc, kiểm SHA-256 (FR-007).
- Q: Người ngoài tải bộ cài ở đâu? → A: GitHub Release của repo riêng tư; chủ xưởng tự gửi tệp; bộ cài tự chứa phần lõi (FR-010).
- Q: Tự cập nhật ở 016 hay 017? → A: 017, cùng license key (FR-012).

## Bối cảnh

Lộ trình app desktop (2026-11-11):
- **014**: cả xưởng chạy trên một máy, không cần Docker.
- **015**: vỏ desktop. Hiện vỏ cần một bản studio đã cài sẵn (Windows: trong một bản Linux WSL của người dùng; macOS: `~/claude-Utube` cùng mọi công cụ).
- **016** (spec này): bộ cài. Người ngoài công ty tải một tệp cài, bấm cài, và có ngay app chạy được, không phải tự cài studio, Python, ffmpeg hay thư viện.
- **017**: license key.

Phần lõi cần nhiều thứ, khoảng 3,5 GB chưa nén:
- thư viện phim (MIT), mô hình giọng Kokoro (Apache 2.0) và mô hình nhận dạng giọng Whisper (MIT);
- Chromium để dựng hình;
- Python cùng các gói, ffmpeg, Node, và Claude Code.

Phần lõi đặt ở đâu:
- **Windows**: trong một bản Linux WSL2 riêng của app (tên `ClaudeUtube`), tách khỏi Linux người dùng đang có.
- **macOS**: trong gói của app, chạy thẳng trên máy.

Mức quy trình: **Đầy đủ**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cài trên Windows bằng một tệp (Priority: P1)

Người dùng Windows tải tệp cài, chạy nó (vượt cảnh báo của bản chưa ký số theo hướng dẫn), rồi mở app. Màn hình thiết lập (015) kiểm WSL2, bật nếu cần, rồi cài **phần lõi đóng gói sẵn** thành một bản Linux riêng của app. Từ đó app chạy như ở 015, không cần bản studio nào có sẵn.

**Why this priority**: Phần lớn người dùng là Windows. Đây là điều kiện để người ngoài tự cài được.

**Independent Test**: Trên một máy Windows sạch đã bật WSL2, chạy tệp cài rồi mở app. Kết quả cần thấy:
- màn hình thiết lập cài phần lõi (có tiến độ) thành bản Linux `ClaudeUtube`;
- bấm Start → trang tạo chủ xưởng hiện ra;
- gỡ cài đặt → app mất; bản Linux và dữ liệu chỉ bị xoá khi người dùng chọn xoá.

**Acceptance Scenarios**:

1. **Given** một máy Windows 10 (22H2) hoặc 11 bản 64-bit, **When** người dùng chạy tệp cài, **Then** app được cài cho riêng người dùng đó (không cần quyền quản trị), có lối tắt trong Start menu, và mở được.
2. **Given** WSL2 đã bật và chưa có phần lõi, **When** màn hình thiết lập chạy, **Then** nó cài phần lõi thành bản Linux riêng `ClaudeUtube` (có thanh tiến độ, báo dung lượng cần có), không đụng tới các bản Linux khác của người dùng.
3. **Given** phần lõi đã cài, **When** bấm Start, **Then** app chạy phần lõi trong bản Linux đó và mở trang tạo chủ xưởng.
4. **Given** người dùng gỡ app, **When** trình gỡ hỏi, **Then** người dùng chọn giữ hay xoá phần lõi và dữ liệu. Mặc định là giữ.
5. **Given** một bản studio có sẵn trong Linux của người dùng (cách của 015), **When** mở màn hình thiết lập, **Then** người dùng vẫn chọn được bản đó thay cho phần lõi đóng gói (dành cho người phát triển).

---

### User Story 2 - Cài trên macOS bằng một tệp (Priority: P2)

Người dùng Mac tải tệp `.dmg`, kéo app vào Applications, mở app (vượt cảnh báo của bản chưa ký số theo hướng dẫn). App đã chứa sẵn phần lõi, nên màn hình thiết lập chỉ còn chọn thư mục dữ liệu rồi bấm Start.

**Why this priority**: Người dùng có máy Mac. Nhưng Windows nhiều người dùng hơn.

**Independent Test**: Trên một máy Mac chip Apple sạch, không có Homebrew hay Python riêng: mở `.dmg`, kéo app vào Applications, mở app → thiết lập → Start → trang tạo chủ xưởng; giao một phim thật thì dựng xong (cần tài khoản Claude của người thử).

**Acceptance Scenarios**:

1. **Given** máy Mac chip Apple không có Homebrew, Python hay ffmpeg, **When** người dùng cài từ `.dmg` và mở app, **Then** màn hình thiết lập thấy đủ công cụ (đều nằm trong gói app) và chỉ hỏi thư mục dữ liệu.
2. **Given** đã thiết lập, **When** bấm Start rồi giao một phim, **Then** phim dựng được hoàn toàn bằng công cụ trong gói app (không gọi công cụ nào của hệ thống ngoài các lệnh có sẵn của macOS).
3. **Given** macOS chặn app chưa ký số lần đầu mở, **When** người dùng làm theo hướng dẫn cài (System Settings → Privacy & Security → Open Anyway), **Then** app mở được, và các lần sau không bị hỏi lại.

---

### User Story 3 - Build bộ cài tự động (Priority: P3)

Chủ xưởng gắn một tag phiên bản. GitHub Actions build phần lõi và bộ cài cho cả hai hệ điều hành, chạy thử bộ cài trên máy sạch của GitHub, rồi đưa các tệp lên nơi phát hành.

**Why this priority**: Không có build tự động thì mỗi bản phát hành phải build tay trên hai loại máy. Nhưng người dùng chỉ cần thấy kết quả.

**Independent Test**: Gắn tag `desktop-v0.1.0`. Kết quả cần thấy: workflow tạo đủ bộ cài Windows, `.dmg` macOS và tệp phần lõi cho Windows; bước kiểm trên máy sạch đạt; các tệp có ở nơi phát hành, kèm mã kiểm (SHA-256).

**Acceptance Scenarios**:

1. **Given** chủ xưởng gắn tag `desktop-vX.Y.Z`, **When** workflow chạy, **Then** nó build phần lõi cho Windows (bản Linux), phần lõi cho macOS (trong gói app), bộ cài Windows và `.dmg`, với số phiên bản lấy từ tag.
2. **Given** các tệp đã build, **When** bước kiểm chạy trên máy sạch của GitHub, **Then** bộ cài và gói app mở được, và phần lõi trả lời kiểm tra sức khoẻ. Trên Windows, phần lõi được kiểm bằng cách chạy bản Linux trong một container Linux, vì máy của GitHub không có WSL2.
3. **Given** một tệp lớn hơn giới hạn của nơi phát hành, **When** đưa lên, **Then** nó được chia nhỏ hoặc phần nặng được tải lúc cài (xem FR-007); không có bước nào trượt vì tệp quá lớn.

### Edge Cases

- Ổ cài không đủ chỗ (phần lõi cần khoảng 6 GB khi đã giải nén): thiết lập báo trước khi cài, kèm dung lượng cần có.
- Mất mạng khi đang tải phần lõi: tiếp tục từ chỗ dừng khi có mạng lại; tệp hỏng (mã SHA-256 sai) thì tải lại.
- Đã có bản Linux tên `ClaudeUtube` (cài lần trước): hỏi dùng lại hay cài lại; cài lại thì giữ thư mục dữ liệu.
- macOS chip Intel: không hỗ trợ ở 016; bộ cài báo rõ.
- Antivirus chặn nhầm bản chưa ký số: hướng dẫn cài có mục này.

## Requirements *(mandatory)*

### Functional Requirements

**Phần lõi đóng gói sẵn**
- **FR-001**: Phần lõi đóng gói MUST chứa mọi thứ phần lõi cần để làm trọn một phim:
  - code của xưởng ở đúng phiên bản của bản phát hành;
  - thư viện phim ở đúng commit của `library.lock`, kèm tệp LICENSE;
  - Python cùng mọi gói (giao diện, online, giọng, nhạc), ffmpeg, Node, Chromium, Claude Code;
  - các mô hình giọng và nhận dạng giọng (xem FR-007).
- **FR-002**: Windows: phần lõi MUST là một bản Linux WSL2 riêng của app, tên `ClaudeUtube`, dựa trên một bản Ubuntu LTS. Cài nó MUST NOT đổi các bản Linux khác hay bản mặc định của người dùng.
- **FR-003**: macOS: phần lõi MUST nằm trong gói app (chip Apple) và chạy được trên một máy Mac không có Homebrew, Python hay ffmpeg riêng.
- **FR-004**: Mọi phần mềm và mô hình đi kèm MUST có giấy phép cho phép phát lại. Mỗi thứ MUST được ghi vào `CREDITS` kèm tên giấy phép, và tệp giấy phép của chúng MUST nằm trong gói.

**Bộ cài**
- **FR-005**: Windows MUST có một bộ cài (chưa ký số) cài cho riêng người dùng, không cần quyền quản trị, có lối tắt Start menu và trình gỡ. Trình gỡ MUST hỏi giữ hay xoá phần lõi và dữ liệu; mặc định giữ.
- **FR-006**: macOS MUST có một tệp `.dmg` (chip Apple, ký ad-hoc như neb), kéo vào Applications là xong.
- **FR-007**: Các phần nặng (mô hình giọng và nhận dạng giọng, có thể cả Chromium): App MUST tải các mô hình lúc thiết lập, từ nơi phát hành công khai của chính các mô hình đó, với mã SHA-256 ghi sẵn trong app, có thanh tiến độ và tải tiếp khi mất mạng. Phần lõi đóng gói không chứa các mô hình này.
- **FR-008**: Màn hình thiết lập (015) MUST thêm bước cài phần lõi đóng gói (Windows) với tiến độ, kiểm dung lượng trống, tải tiếp khi mất mạng, và kiểm SHA-256. Lựa chọn dùng bản studio có sẵn (015) MUST vẫn còn.

**Build và phát hành**
- **FR-009**: GitHub Actions MUST build phần lõi và bộ cài khi có tag `desktop-vX.Y.Z` và khi bấm chạy tay, rồi kiểm chúng trên máy sạch như US3/AC2, trước khi đưa tệp lên.
- **FR-010**: Nơi phát hành bộ cài cho người ngoài: GitHub Release của chính repo riêng tư này. Chủ xưởng tự chia sẻ tệp cho người dùng (ví dụ qua Google Drive) cho tới khi 017 có trang tải sau license. Vì vậy bộ cài MUST tự chứa phần lõi (Windows: tệp bản Linux nằm trong bộ cài); app MUST NOT cần truy cập repo riêng tư để cài.
- **FR-011**: Mỗi tệp phát hành MUST có mã SHA-256 đi kèm. App kiểm mã này trước khi cài phần lõi.

**Phạm vi**
- **FR-012**: Tự cập nhật app và phần lõi KHÔNG nằm trong 016; nó được làm ở 017 cùng license key, như neb. Ở 016, cài bản mới đè lên bản cũ MUST giữ dữ liệu, và MUST thay phần lõi khi phiên bản phần lõi trong bộ cài mới hơn.
- **FR-013**: Sandbox cho Bash của agent (dời từ 014): bản Linux của Windows MUST có sẵn bubblewrap và socat, và phần lõi MUST bật sandbox Bash khi chạy trong đó. macOS MUST bật sandbox có sẵn của hệ điều hành. Cả hai MUST được kiểm bằng một test chạy lệnh ghi ra ngoài thư mục việc và thấy bị chặn.

### Key Entities

- **Phần lõi đóng gói (Core package)**: phiên bản, hệ điều hành, các tệp (có thể chia nhỏ), mã SHA-256, dung lượng nén và giải nén, danh sách phần mềm và giấy phép.
- **Bộ cài (Installer)**: phiên bản, hệ điều hành, tệp, mã SHA-256.
- **Bản phát hành (Release)**: tag, các bộ cài, phần lõi, ghi chú.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Trên một máy Windows sạch đã bật WSL2, từ lúc chạy tệp cài tới trang tạo chủ xưởng mất dưới 20 phút với đường mạng 50 Mbps, không gõ lệnh nào.
- **SC-002**: Trên một máy Mac chip Apple sạch, từ lúc mở `.dmg` tới trang tạo chủ xưởng mất dưới 10 phút, không gõ lệnh nào.
- **SC-003**: Một phim thật (45 giây, có giọng đọc và nhạc) dựng xong trên mỗi hệ điều hành chỉ bằng phần lõi đóng gói (kiểm bằng tay một lần mỗi hệ điều hành; cần tài khoản Claude của người thử).
- **SC-004**: Gắn một tag thì có đủ tệp phát hành và bước kiểm trên máy sạch đạt cho cả hai hệ điều hành, không bước nào phải làm tay.
- **SC-005**: Mỗi phần mềm và mô hình trong gói có mặt trong `CREDITS` (kiểm tự động: danh sách trong gói so với `CREDITS`).
- **SC-006**: Lệnh Bash ghi ra ngoài thư mục việc bị chặn trong phần lõi đóng gói của cả hai hệ điều hành (kiểm tự động).

## Assumptions

- Bản chưa ký số (giống neb). Ký số thật để sau, khi bán (neb ước tính thêm khoảng 2 tuần).
- macOS chỉ chip Apple; Windows 10 22H2 hoặc 11 bản 64-bit.
- Giới hạn của GitHub Release là 2 GB mỗi tệp. Phần lõi nén có thể lớn hơn, nên cần chia nhỏ hoặc tải phần nặng riêng (FR-007).
- Người thử SC-003 dùng tài khoản Claude của chính họ (hướng A).
