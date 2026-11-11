# Feature Specification: Chọn đề bằng số liệu YouTube

**Feature Branch**: `013-topic-picker`

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "013 topic picker from YouTube data: for one of the user's channels (012), score candidate topics with numbers from the YouTube Data API (owner's API key): demand (in the last year, videos on the topic with many views, any video above 3x its channel's median), heat (still rising in the last 30–90 days), competition (how many channels made it in 90 days, big channels weigh more), team overlap (too close to the channel's own films), and channel fit; each /10, total /50; GO (≥32 and no item ≤3), HOLD (25–31 or a weak item), DROP (<25), PRIORITY (GO, very hot, cooling within about 2 weeks). Each topic keeps its evidence (strongest competing video, views, age). A per-channel topic queue: priority first, then score; no repeat of the type of the last 2 films; never copy a topic a reference channel just released. Local and online. API key is a secret, never in git or chat. Respect the API daily quota. Out of scope: downloading videos, analysing other channels' video content, uploading, long videos."

## Clarifications

### Session 2026-11-11

- Q: Đề lấy từ đâu? → A: Người dùng đưa đề vào; khi họ yêu cầu, xưởng gợi ý thêm tối đa 10 đề từ hồ sơ kênh rồi chấm chung (FR-001a).
- Q: Ai chấm mục "hợp kênh"? → A: Claude, một lượt ngắn cho cả lô đề, người dùng sửa được (FR-002).
- Q: Khoá YouTube ở bản online? → A: Một khoá chung của chủ xưởng, giới hạn lượt chấm mỗi người mỗi ngày (FR-011, FR-016).

## Bối cảnh

Hiện người dùng tự nghĩ ý tưởng cho từng phim. Quy trình làm video YouTube bằng đội agent mà người dùng gửi (2026-11-10, "Bước 1 – Chọn đề") chọn đề bằng số liệu, không theo cảm giác. Một máy chấm đề quét YouTube và cho điểm 5 mục, mỗi mục /10:
- nhu cầu;
- độ nóng;
- cạnh tranh;
- trùng với phim đã làm;
- hợp kênh.

Đề được xếp vào hàng đợi của kênh, mỗi đề kèm bằng chứng.

Spec này đưa máy chấm đề và hàng đợi đề vào xưởng, gắn với hồ sơ kênh của 012. Xưởng chỉ đọc số liệu công khai của video (tiêu đề, lượt xem, ngày đăng, số người đăng ký của kênh). Xưởng không tải video và không phân tích nội dung video của kênh khác.

Áp dụng cho cả hai chế độ: local và online (007–012).

Mức quy trình: **Đầy đủ**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chấm một danh sách đề cho một kênh (Priority: P1)

Người dùng có một kênh (012). Họ đưa vào vài đề muốn làm. Xưởng tra số liệu công khai trên YouTube cho từng đề và cho điểm 5 mục, mỗi mục /10, tổng /50. Mỗi đề nhận một kết luận: GO, HOLD, DROP hoặc PRIORITY, kèm bằng chứng gồm video mạnh nhất cùng đề, số lượt xem và số ngày tuổi của video đó.

**Why this priority**: Đây là giá trị chính: biết đề nào đáng làm trước khi tốn token làm phim.

**Independent Test**: Với số liệu YouTube mẫu (không gọi dịch vụ thật), chấm 4 đề đã biết trước kết quả. Kết quả cần thấy: điểm từng mục và kết luận đúng như tính tay; mỗi đề có video bằng chứng kèm lượt xem và số ngày tuổi.

**Acceptance Scenarios**:

1. **Given** một kênh và một danh sách đề, **When** người dùng chạy chấm đề, **Then** mỗi đề có 5 điểm /10, tổng /50, kết luận và bằng chứng.
2. **Given** một đề có tổng ≥ 32 và không mục nào ≤ 3, **When** chấm xong, **Then** kết luận là GO. Nếu đề đó còn rất nóng và sắp nguội trong khoảng 2 tuần, kết luận là PRIORITY.
3. **Given** một đề có tổng 25–31, hoặc có một mục ≤ 3, **When** chấm xong, **Then** kết luận là HOLD. Tổng dưới 25 thì kết luận là DROP.
4. **Given** một đề quá giống một phim kênh đã làm, **When** chấm, **Then** mục "trùng" có điểm thấp, và bằng chứng nêu tên phim đó.
5. **Given** chưa có khoá dịch vụ YouTube, **When** người dùng chạy chấm đề, **Then** xưởng báo rõ cách đặt khoá và không chấm gì.

---

### User Story 2 - Hàng đợi đề của kênh (Priority: P2)

Các đề đã chấm vào hàng đợi của kênh. Thứ tự: PRIORITY trước, rồi GO theo điểm, rồi HOLD; DROP không vào hàng đợi. Khi người dùng muốn làm phim tiếp theo cho kênh, họ lấy đề đầu hàng đợi. Xưởng bỏ qua các đề cùng kiểu với 2 phim gần nhất của kênh, và các đề mà một kênh mẫu vừa đăng.

**Why this priority**: Biến điểm số thành việc cần làm tiếp theo. Nhưng nó cần các đề đã chấm (US1).

**Independent Test**: Hàng đợi mẫu có 1 đề PRIORITY, 2 đề GO, 1 đề HOLD, 1 đề DROP; 2 phim gần nhất của kênh cùng kiểu "so sánh". Kết quả cần thấy: thứ tự PRIORITY → GO (điểm cao trước) → HOLD; không có đề DROP; đề GO kiểu "so sánh" bị đẩy xuống kèm lý do.

**Acceptance Scenarios**:

1. **Given** các đề đã chấm, **When** xem hàng đợi, **Then** thứ tự là PRIORITY, rồi GO theo điểm giảm dần, rồi HOLD; không có DROP.
2. **Given** 2 phim gần nhất của kênh cùng một kiểu đề, **When** lấy đề tiếp theo, **Then** đề cùng kiểu bị bỏ qua lần này, kèm lý do.
3. **Given** một kênh mẫu của kênh vừa đăng video cùng đề trong 30 ngày, **When** chấm hoặc lấy đề, **Then** đề đó bị đánh dấu "kênh mẫu vừa làm" và không được lấy.
4. **Given** người dùng lấy một đề để làm phim, **When** giao phim, **Then** đề chuyển sang "đang làm", gắn với phim, và ý tưởng phim được điền sẵn từ đề.
5. **Given** một đề đã chấm quá 14 ngày, **When** xem hàng đợi, **Then** đề được đánh dấu "cũ, nên chấm lại", vì số liệu YouTube thay đổi nhanh.

---

### User Story 3 - Chấm đề và xem hàng đợi trên giao diện online (Priority: P3)

Ở chế độ online, người dùng mở trang kênh, dán danh sách đề, bấm chấm, rồi xem bảng điểm và hàng đợi. Từ một đề trong hàng đợi, họ bấm "Make a film" để giao phim với ý tưởng điền sẵn. Chủ xưởng đặt khoá dịch vụ YouTube và giới hạn lượt chấm trong Settings.

**Why this priority**: Người dùng online không chạy lệnh được. Nhưng phần này chỉ hiển thị và gọi các bước của US1 và US2.

**Independent Test**: Trên giao diện, dán 3 đề cho một kênh, bấm chấm (số liệu mẫu). Kết quả cần thấy: bảng điểm và hàng đợi hiện ra; bấm "Make a film" mở form giao phim với ý tưởng điền sẵn. Người khác không thấy hàng đợi này.

**Acceptance Scenarios**:

1. **Given** trang một kênh, **When** người dùng dán đề và bấm chấm, **Then** thấy bảng điểm 5 mục, kết luận, bằng chứng (có đường dẫn tới video) và hàng đợi.
2. **Given** chủ xưởng ở Settings, **When** họ đặt khoá dịch vụ YouTube, **Then** khoá được lưu kín: không hiện lại đầy đủ, chỉ hiện 4 ký tự cuối.
3. **Given** một người đã dùng hết lượt chấm đề trong ngày, **When** họ chấm thêm, **Then** bị từ chối kèm giờ được chấm lại.
4. **Given** một người khác, **When** họ tìm hàng đợi đề của kênh này, **Then** bị từ chối như với kênh (012).

### Edge Cases

- Dịch vụ YouTube hết hạn mức trong ngày giữa chừng: các đề đã chấm được giữ; đề chưa chấm được ghi "chưa chấm: hết hạn mức", kèm giờ có hạn mức mới.
- Khoá sai hoặc bị khoá: báo rõ "khoá không dùng được", không chấm gì, không lộ khoá trong thông báo hay log.
- Đề quá mới, gần như không có video cùng đề: nhu cầu thấp, cạnh tranh cao điểm (ít đối thủ); kết luận theo luật tổng điểm như mọi đề.
- Đề viết bằng ngôn ngữ khác ngôn ngữ của kênh: tra theo ngôn ngữ và vùng của kênh; báo khi ngôn ngữ của đề khác ngôn ngữ kênh.
- Một đề trùng (gần giống) một đề đã có trong hàng đợi: không thêm bản thứ hai; chấm lại đề cũ.
- Kênh chưa có phim nào: mục "trùng" được 10 điểm.
- Kênh chưa khai báo kênh mẫu: bỏ qua luật "kênh mẫu vừa làm" và ghi rõ là không kiểm.

## Requirements *(mandatory)*

### Functional Requirements

**Đề và điểm**
- **FR-001**: Người dùng MUST đưa được một danh sách đề (mỗi đề một dòng ngắn, 3–120 ký tự, tối đa 20 đề mỗi lần) cho một kênh của họ (012).
- **FR-001a**: Khi người dùng yêu cầu, xưởng MUST gợi ý thêm tối đa 10 đề từ hồ sơ kênh (ngách, khán giả, quyết định) bằng một lượt Claude ngắn, rồi chấm chung với các đề của người dùng. Đề gợi ý được đánh dấu "suggested". Không yêu cầu thì không gọi Claude.
- **FR-002**: Với mỗi đề, xưởng MUST tra số liệu công khai của video trên YouTube, theo ngôn ngữ và vùng của kênh, và cho 5 điểm, mỗi điểm là số nguyên 0–10:
  - **Nhu cầu**: trong 365 ngày qua, có những video cùng đề nhiều lượt xem không, và có video nào vượt 3 lần trung vị lượt xem của chính kênh đăng nó không;
  - **Độ nóng**: số video cùng đề và lượt xem của chúng trong 30 ngày gần nhất, so với 31–90 ngày trước đó;
  - **Cạnh tranh**: số kênh đã làm đề này trong 90 ngày; kênh lớn trừ điểm nặng hơn kênh nhỏ; càng ít đối thủ thì điểm càng cao;
  - **Trùng**: độ giống giữa đề và các phim kênh đã làm (tên phim, ý tưởng, tiêu đề làm việc); càng giống thì điểm càng thấp;
  - **Hợp kênh**: đề có đúng ngách, khán giả và giọng điệu trong hồ sơ kênh không. Claude MUST chấm mục này theo hồ sơ kênh, một lượt ngắn cho cả lô đề (không phải mỗi đề một lượt), kèm một câu lý do cho mỗi đề. Người dùng sửa được điểm này; kết luận được tính lại ngay.
- **FR-003**: Kết luận MUST theo đúng luật:
  - **GO**: tổng ≥ 32 và không mục nào ≤ 3;
  - **HOLD**: tổng 25–31, hoặc tổng ≥ 32 nhưng có một mục ≤ 3;
  - **DROP**: tổng < 25;
  - **PRIORITY**: đề GO có độ nóng ≥ 8 và đang "sắp nguội", tức các video cùng đề trong 30 ngày gần nhất tập trung ở 15 ngày đầu của khoảng đó (nhịp đăng đang giảm).
- **FR-004**: Mỗi đề MUST lưu bằng chứng: video mạnh nhất cùng đề (tiêu đề, kênh, lượt xem, số ngày tuổi, đường dẫn), số video và số kênh đã đếm cho từng mục, phim trùng nhất của kênh (nếu có), thời điểm chấm, và số liệu thô đã dùng để tính điểm, để chấm lại hay kiểm lại được.
- **FR-005**: Máy chấm MUST cho đúng cùng điểm khi chạy lại trên cùng số liệu thô (lặp lại được), và MUST chạy được với số liệu mẫu, không cần mạng (để test).

**Hàng đợi**
- **FR-006**: Mỗi kênh MUST có một hàng đợi đề. Thứ tự: PRIORITY, rồi GO (tổng giảm dần), rồi HOLD (tổng giảm dần). DROP không vào hàng đợi nhưng vẫn được lưu để xem lại.
- **FR-007**: Mỗi đề MUST có một "kiểu đề" (ví dụ: giải thích, so sánh, danh sách, chuyện có thật, hỏi–đáp), do xưởng gợi ý và người dùng sửa được. Khi lấy đề tiếp theo, đề cùng kiểu với cả 2 phim gần nhất của kênh MUST bị bỏ qua lần đó, kèm lý do.
- **FR-008**: Người dùng MUST khai báo được danh sách kênh mẫu cho mỗi kênh của mình. Đề mà một kênh mẫu đã đăng video cùng đề trong 30 ngày qua MUST bị đánh dấu "kênh mẫu vừa làm" và không được lấy. Danh sách kênh mẫu là dữ liệu riêng: MUST NOT vào git, và MUST NOT hiện trong phim hay gói đăng (hiến pháp: không nêu tên kênh tham chiếu).
- **FR-009**: Lấy một đề để làm phim MUST chuyển đề sang "đang làm", gắn với phim, và điền sẵn ý tưởng phim từ đề. Phim xong thì đề chuyển sang "đã làm" và được tính vào mục "trùng" của các lần chấm sau.
- **FR-010**: Đề chấm quá 14 ngày MUST được đánh dấu "cũ" trong hàng đợi. Người dùng chấm lại được một đề hoặc cả hàng đợi.

**Khoá và hạn mức**
- **FR-011**: Khoá dịch vụ YouTube là bí mật: MUST NOT vào git, chat, log, thông báo lỗi hay giao diện (chỉ hiện 4 ký tự cuối). Ở local, khoá đặt bằng một lệnh nhập kín (không qua dòng lệnh hay chat). Ở online, chỉ chủ xưởng đặt khoá trong Settings. Ở online, cả xưởng dùng chung một khoá của chủ xưởng; người dùng không nhập khoá, và lượt chấm của mỗi người bị giới hạn theo FR-016.
- **FR-012**: Xưởng MUST đếm phần hạn mức dịch vụ YouTube đã dùng trong ngày và không vượt hạn mức chủ xưởng đặt (mặc định 9000 trên 10000 đơn vị/ngày, để chừa chỗ). Chấm một đề MUST tốn tối đa 400 đơn vị. Hết hạn mức thì dừng như ở Edge Cases.
- **FR-013**: Số liệu tra được MUST được giữ lại 24 giờ: chấm lại cùng một đề trong 24 giờ thì không tốn thêm hạn mức.

**Hiển thị**
- **FR-014**: Ở local, có lệnh chấm đề, xem hàng đợi, lấy đề, sửa kiểu đề, đặt kênh mẫu và đặt khoá. Kết quả được ghi vào tệp đọc được bằng mắt trong thư mục kênh (012).
- **FR-015**: Ở online, trang kênh MUST có mục "Topics": ô dán đề, nút chấm, bảng điểm có bằng chứng (đường dẫn video), hàng đợi, và nút "Make a film" mở form giao phim đã điền ý tưởng và kênh.
- **FR-016**: Ở online, mỗi người MUST chỉ thấy đề và hàng đợi của kênh mình. Lượt chấm đề MUST có giới hạn mỗi người mỗi ngày, do chủ xưởng đặt (mặc định 40 đề).

**Giới hạn**
- **FR-017**: Xưởng MUST NOT tải video, xem hay phân tích nội dung (hình, tiếng, phụ đề) video của kênh khác, hay đăng gì lên YouTube. Chỉ đọc số liệu công khai: tiêu đề, kênh, ngày đăng, lượt xem, số người đăng ký. Không sửa `lib/` (hiến pháp VI).

### Key Entities

- **Đề (Topic)**: kênh, chữ của đề, kiểu đề, trạng thái (`scored`, `queued`, `in_progress`, `made`, `dropped`, `blocked_reference`), 5 điểm, tổng, kết luận, bằng chứng, thời điểm chấm, phim gắn (nếu có).
- **Bằng chứng (Evidence)**: video mạnh nhất (tiêu đề, kênh, lượt xem, ngày tuổi, đường dẫn), số đếm cho từng mục, phim trùng nhất, số liệu thô.
- **Kênh mẫu (Reference channel)**: thuộc một kênh của người dùng; chỉ nằm trong dữ liệu riêng, không vào git.
- **Hạn mức (Quota usage)**: ngày, đơn vị đã dùng, giới hạn; online thêm số đề mỗi người đã chấm trong ngày.
- **Khoá (API key)**: bí mật; local nằm ngoài repo, online nằm trong dữ liệu của xưởng; chỉ lộ 4 ký tự cuối.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Với bộ số liệu mẫu có kết quả tính tay, 100% đề có điểm từng mục và kết luận đúng như tính tay, và chạy lại cho đúng cùng điểm.
- **SC-002**: Chấm 10 đề xong trong dưới 2 phút và tốn không quá 4000 đơn vị hạn mức YouTube (≤ 400 đơn vị mỗi đề); chấm lại trong 24 giờ tốn 0 đơn vị.
- **SC-003**: Hàng đợi mẫu xếp đúng thứ tự trong 100% trường hợp test, và luật "không lặp kiểu của 2 phim gần nhất" cùng luật "kênh mẫu vừa làm" chặn đúng 100% đề cần chặn.
- **SC-004**: Khoá dịch vụ YouTube không xuất hiện ở bất kỳ tệp nào trong repo, log, thông báo lỗi hay phản hồi giao diện nào (kiểm tự động bằng cách tìm khoá mẫu trong toàn bộ đầu ra của bộ test).
- **SC-005**: Từ một đề trong hàng đợi, người dùng giao được phim trong 1 bước (một lệnh, hoặc một nút rồi gửi form).
- **SC-006**: Ở online, một người không xem hay sửa được đề và hàng đợi của người khác (kiểm tự động).

## Assumptions

- Dịch vụ là YouTube Data API công khai, có hạn mức mặc định 10000 đơn vị mỗi ngày cho mỗi khoá. Tìm kiếm tốn nhiều đơn vị hơn đọc thông tin video, nên số lần tìm cho mỗi đề bị giới hạn.
- Lượt xem và số người đăng ký là số công khai tại thời điểm tra, không phải lịch sử. "Độ nóng" vì thế được ước lượng từ ngày đăng và lượt xem của các video mới, không phải từ biểu đồ theo thời gian.
- Trung vị lượt xem của một kênh được ước lượng từ các video gần đây của chính kênh đó mà lần tra lấy được (tối đa 50 video).
- Ngưỡng điểm cụ thể của từng mục (bao nhiêu lượt xem thì được bao nhiêu điểm) được chốt ở plan, có bảng và test.
- Chủ kênh tự kiểm tra rằng việc dùng dịch vụ YouTube hợp với điều khoản của YouTube.
- Ngoài phạm vi: tải video, phân tích nội dung video kênh khác, đăng video, lịch đăng, video dài 8–15 phút.
