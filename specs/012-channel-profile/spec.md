# Feature Specification: Hồ sơ kênh và tệp bài học

**Feature Branch**: `012-channel-profile`

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "012 channel profile and lessons: each of the user's own YouTube channels gets a profile (name, niche, audience, language, target length, default style, voice from the library with speed, title and thumbnail rules written by the owner, hashtags always used, words never used, decisions made). A film can belong to a channel: treatment, script, the script editor and the publish pack read the profile, and the machine checks enforce its measurable rules (language, length, required hashtags, banned words). Lessons: per channel and one shared file; each lesson = what went wrong, why it was missed, how to stop it next time, and optionally a machine rule (a banned phrase or a limit) that the script check and publish check enforce; a recorded lesson that happens again is a serious problem. The agent reads the profile and lessons (kept short) at the start of every film. Local and online. Out of scope: picking topics from YouTube data, analysing other channels' videos, cloning voices, long videos, uploading."

## Clarifications

### Session 2026-11-11

- Q: Ai viết bài học? → A: Xưởng soạn nháp từ ghi chú sửa phim hoặc lời người dùng kể; người dùng duyệt (có thể sửa) rồi mới lưu (FR-013).
- Q: Hồ sơ kênh và bài học có vào git không? → A: Có, như `my-styles/` (FR-015).
- Q: Bài học chung ở bản online là của ai? → A: Của cả xưởng, admin quản lý, áp cho mọi người (FR-016).
- Q: Gói đăng lặp lại lỗi đã có bài học thì sao? → A: Sửa một vòng như mọi lỗi gói đăng; vẫn còn thì phim vẫn giao, nhưng trang việc và `PUBLISH.md` ghi rõ "lỗi lặp lại bài học #n" và gói bị đánh dấu không được đăng khi chưa sửa (FR-011).

## Bối cảnh

Hiện mỗi phim là một yêu cầu riêng lẻ. Người dùng phải nhắc lại ngôn ngữ, khán giả, độ dài, phong cách và giọng mỗi lần giao phim. Lỗi đã gặp ở phim trước (một câu sáo, một kiểu tiêu đề người dùng ghét, một con số đọc sai) không được nhớ, nên có thể lặp lại.

Quy trình làm video YouTube bằng đội agent mà người dùng gửi (2026-11-10) giải quyết việc này bằng ba tệp:
- hồ sơ kênh: những gì chủ kênh đã chốt;
- bài học của kênh: lỗi đã gặp, vì sao lọt, cách chặn lần sau; lỗi đã ghi mà lặp lại là lỗi nặng;
- một tệp bài học chung cho mọi kênh, đọc ở đầu mỗi phiên.

Spec này đưa ba tệp đó vào xưởng, và nối chúng với các máy chấm đã có: máy chấm kịch bản (010) và máy kiểm gói đăng (011).

"Kênh" ở đây là kênh YouTube **của chính người dùng**, không phải kênh tham chiếu dùng để học phong cách. Hiến pháp vẫn cấm nêu tên kênh tham chiếu trong phim.

Áp dụng cho cả hai chế độ: local (làm phim trong khung chat) và online (việc chạy trong container, 007–011).

Mức quy trình: **Đầy đủ**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Làm phim theo hồ sơ kênh (Priority: P1)

Người dùng tạo một hồ sơ cho kênh của mình một lần: tên kênh, ngách, khán giả, ngôn ngữ, độ dài phim, phong cách mặc định, giọng đọc và tốc độ, luật tiêu đề và thumbnail, hashtag luôn dùng, từ không bao giờ dùng, và các quyết định đã chốt. Sau đó, mỗi lần giao phim họ chỉ cần nói phim thuộc kênh nào và ý tưởng. Xưởng tự lấy các giá trị còn lại từ hồ sơ. Máy chấm kịch bản và máy kiểm gói đăng tự kiểm các luật đo được của kênh.

**Why this priority**: Đây là phần người dùng thấy ngay: giao phim nhanh hơn và mọi phim của một kênh giống nhau ở những điểm đã chốt.

**Independent Test**: Tạo hồ sơ kênh tiếng Việt, độ dài 45 giây, phong cách X, hashtag bắt buộc `#khoahoc`, cấm từ "sốc". Giao một phim cho kênh đó chỉ với ý tưởng. Kết quả cần thấy: kịch bản tiếng Việt, mục tiêu 45 giây, phong cách X; gói đăng có `#khoahoc`. Nếu kịch bản hay tiêu đề có từ "sốc" thì máy chấm báo lỗi và chỉ đúng vị trí.

**Acceptance Scenarios**:

1. **Given** chưa có hồ sơ kênh nào, **When** người dùng tạo hồ sơ với các mục trên, **Then** hồ sơ được lưu và xem lại được, kèm ngày cập nhật cuối.
2. **Given** một hồ sơ kênh, **When** người dùng giao phim cho kênh đó mà không nói ngôn ngữ, độ dài hay phong cách, **Then** phim dùng giá trị trong hồ sơ. Giá trị người dùng nói riêng cho phim đó thắng giá trị trong hồ sơ.
3. **Given** phim thuộc một kênh, **When** máy chấm kịch bản chạy, **Then** nó trượt điều kiện cứng nếu ngôn ngữ của kịch bản khác ngôn ngữ của kênh, và báo mỗi từ cấm xuất hiện kèm số đoạn.
4. **Given** phim thuộc một kênh, **When** máy kiểm gói đăng chạy, **Then** nó trượt nếu thiếu hashtag bắt buộc của kênh, nếu tiêu đề, mô tả hay chữ trên thumbnail có từ cấm, hoặc nếu tiêu đề vượt độ dài tối đa của kênh (khi kênh đặt giới hạn này).
5. **Given** phim thuộc một kênh, **When** biên tập độc lập (010) chấm kịch bản, **Then** biên tập nhận cả hồ sơ kênh, và có thể ghi lỗi khi kịch bản sai giọng điệu hay sai khán giả của kênh.
6. **Given** người dùng chốt một điều mới trong lúc làm phim (ví dụ "kênh này không dùng nhạc có lời"), **When** họ yêu cầu ghi nhớ, **Then** điều đó được thêm vào mục quyết định của hồ sơ kèm ngày.
7. **Given** một phim không thuộc kênh nào, **When** làm phim, **Then** mọi thứ chạy như trước tính năng này.

---

### User Story 2 - Ghi bài học và chặn lỗi lặp lại (Priority: P2)

Khi người dùng thấy lỗi ở một phim đã giao, một bài học được ghi lại gồm: lỗi gì, vì sao lọt, cách chặn lần sau, và (khi đo được) một luật máy, ví dụ một cụm từ cấm hay một giới hạn. Bài học thuộc một kênh, hoặc thuộc tệp bài học chung khi nó đúng cho mọi kênh. Ở các phim sau, xưởng đọc bài học trước khi làm, và máy chấm kiểm các luật máy của bài học. Lỗi đã có bài học mà lặp lại thì bị coi là lỗi nặng.

**Why this priority**: Đây là cách xưởng tốt dần lên qua từng phim. Nhưng nó cần có hồ sơ kênh (US1) để biết bài học thuộc kênh nào.

**Independent Test**: Ghi một bài học cho kênh A với luật máy "cấm cụm 'you won't believe'". Giao một phim cho kênh A mà kịch bản có cụm đó. Kết quả cần thấy: máy chấm trượt và ghi rõ đây là lỗi lặp lại của bài học số mấy. Phim của kênh B không bị luật này chặn. Một bài học chung chặn được cả hai kênh.

**Acceptance Scenarios**:

1. **Given** một phim đã giao, **When** người dùng báo lỗi và yêu cầu ghi bài học, **Then** bài học được thêm vào tệp bài học của kênh (hoặc tệp chung) với đủ: ngày, phim, lỗi gì, vì sao lọt, cách chặn, và luật máy nếu có.
2. **Given** một bài học có luật máy, **When** máy chấm kịch bản hoặc máy kiểm gói đăng chạy cho một phim cùng kênh (hoặc mọi kênh với bài học chung), **Then** chỗ vi phạm bị báo kèm số bài học, và được tính là lỗi nặng.
3. **Given** bắt đầu làm một phim thuộc kênh, **When** xưởng bắt đầu, **Then** xưởng đọc hồ sơ kênh, bài học của kênh và bài học chung trước bước Treatment.
4. **Given** một bài học không có luật máy, **When** biên tập độc lập chấm kịch bản, **Then** biên tập nhận nội dung bài học, và lỗi lặp lại bài học đó được ghi mức P1.
5. **Given** một bài học đã cũ hoặc sai, **When** người dùng muốn bỏ, **Then** bài học được đánh dấu "retired" (không xoá) và không còn được kiểm.

---

### User Story 3 - Quản lý kênh trên giao diện online (Priority: P3)

Ở chế độ online, mỗi người có các kênh của riêng mình. Họ tạo, sửa hồ sơ kênh và xem, thêm, bỏ bài học trên giao diện. Khi giao phim, họ chọn kênh từ một danh sách, và các ô ngôn ngữ, độ dài, phong cách được điền sẵn theo hồ sơ.

**Why this priority**: Người dùng online không mở được tệp trên máy chủ. Nhưng phần này chỉ là cách nhập và hiển thị cho dữ liệu đã có ở US1 và US2.

**Independent Test**: Trên giao diện, tạo kênh, thêm 2 bài học, bỏ 1 bài. Giao phim chọn kênh đó: các ô được điền sẵn. Một người khác không thấy kênh này.

**Acceptance Scenarios**:

1. **Given** một người đã đăng nhập, **When** họ mở trang Channels, **Then** thấy danh sách kênh của mình, tạo được kênh mới và sửa được kênh cũ.
2. **Given** trang một kênh, **When** người dùng thêm, sửa hay bỏ bài học, **Then** thay đổi được lưu, có ghi ngày.
3. **Given** form giao phim, **When** người dùng chọn một kênh, **Then** phong cách, độ dài và ngôn ngữ được điền theo hồ sơ, và vẫn sửa được cho riêng phim đó.
4. **Given** một người khác (không phải chủ kênh), **When** họ tìm kênh này, **Then** bị từ chối như với phim và phong cách của người khác (007).
5. **Given** chủ việc yêu cầu sửa phim (007 "Request changes"), **When** họ viết ghi chú sửa và đánh dấu "ghi thành bài học", **Then** xưởng soạn một bài học nháp cho kênh của phim từ ghi chú; nháp hiện trên trang kênh để họ sửa và duyệt, và chỉ được kiểm sau khi duyệt.

### Edge Cases

- Hồ sơ đặt một phong cách hay giọng đọc không còn tồn tại: xưởng báo rõ khi giao phim và không bắt đầu việc, thay vì đoán một giá trị khác.
- Tệp bài học dài: chỉ phần bài học còn hiệu lực được đưa cho agent. Tổng phần hồ sơ và bài học mà agent đọc ở đầu phim tối đa 6000 ký tự. Vượt mức thì xưởng báo để người dùng gộp hoặc bỏ bớt bài học, và phim vẫn làm với 6000 ký tự đầu theo thứ tự: hồ sơ, bài học có luật máy, bài học còn lại mới nhất trước.
- Từ cấm trùng một phần của từ khác (cấm "sốc" nhưng kịch bản có "sốt"): chỉ khớp trọn từ, không phân biệt hoa thường; tiếng không tách từ thì khớp chuỗi.
- Luật máy viết sai (không đọc được): bài học vẫn được lưu nhưng luật máy bị đánh dấu "invalid" và không được kiểm. Người dùng được báo ngay lúc ghi.
- Phim đổi kênh hay kênh bị xoá sau khi phim đã xong: phim cũ giữ nguyên, không bị kiểm lại.
- Hồ sơ đặt độ dài vượt giới hạn phim của xưởng online: dùng giới hạn của xưởng và báo khi giao phim.
- Hai luật mâu thuẫn (hashtag bắt buộc cũng nằm trong từ cấm): báo lỗi khi lưu hồ sơ, không lưu.

## Requirements *(mandatory)*

### Functional Requirements

**Hồ sơ kênh**
- **FR-001**: Người dùng MUST tạo, xem và sửa được hồ sơ cho mỗi kênh của mình. Hồ sơ gồm:
  - tên kênh, mã kênh (chữ thường, số, gạch nối, dùng để gọi kênh);
  - ngách, khán giả (chữ tự do);
  - ngôn ngữ (mã ngôn ngữ);
  - độ dài phim mặc định (giây);
  - phong cách mặc định (một phong cách của thư viện hoặc phong cách riêng);
  - giọng đọc (một giọng có sẵn của thư viện) và tốc độ đọc;
  - luật tiêu đề và luật thumbnail (chữ tự do do chủ kênh viết; có thể kèm độ dài tối đa của tiêu đề);
  - hashtag luôn dùng (0–5);
  - từ không bao giờ dùng (0–50 từ hoặc cụm từ);
  - các quyết định đã chốt (danh sách, mỗi mục có ngày).
- **FR-002**: Hồ sơ MUST được kiểm khi lưu: mã kênh hợp lệ và không trùng, phong cách và giọng đọc tồn tại, ngôn ngữ là mã hợp lệ, không có hashtag bắt buộc nằm trong từ cấm. Sai thì báo rõ và không lưu.
- **FR-003**: Một phim MUST có thể gắn với một kênh khi giao. Giá trị người dùng nói riêng cho phim (phong cách, độ dài, ngôn ngữ) thắng giá trị của hồ sơ. Phim không gắn kênh thì chạy như trước.
- **FR-004**: Người dùng MUST thêm được quyết định mới vào hồ sơ trong lúc làm phim (local: nói với Claude trong khung chat; online: trên trang kênh). Mỗi quyết định có ngày.

**Dùng hồ sơ khi làm phim**
- **FR-005**: Với phim thuộc kênh, xưởng MUST đọc hồ sơ kênh, bài học còn hiệu lực của kênh và bài học chung còn hiệu lực trước bước Treatment. Tổng phần đọc tối đa 6000 ký tự (xem Edge Cases).
- **FR-006**: Máy chấm kịch bản (010) MUST thêm cho phim thuộc kênh:
  - điều kiện cứng `channel_language`: ngôn ngữ của kịch bản bằng ngôn ngữ của kênh;
  - điều kiện cứng `banned_word`: không có từ cấm của kênh, báo kèm số đoạn và câu.
- **FR-006a**: Máy đo phim (`qc`, 010) MUST kiểm cho phim thuộc kênh rằng mọi dòng giọng đọc dùng đúng giọng và tốc độ của kênh, trừ khi người dùng chọn giọng khác riêng cho phim đó.
- **FR-007**: Biên tập độc lập (010) MUST nhận hồ sơ kênh và các bài học không có luật máy, như một phần của "yêu cầu của phim".
- **FR-008**: Máy kiểm gói đăng (011) MUST thêm cho phim thuộc kênh: đủ hashtag bắt buộc; không có từ cấm trong tiêu đề, mô tả và chữ trên thumbnail; tiêu đề không vượt độ dài tối đa của kênh khi kênh đặt giới hạn này.

**Bài học**
- **FR-009**: Mỗi kênh MUST có một tệp bài học, và xưởng MUST có một tệp bài học chung. Mỗi bài học gồm: số bài học (tăng dần, không dùng lại), ngày, phim gặp lỗi, lỗi gì, vì sao lọt, cách chặn lần sau, trạng thái (`draft` khi xưởng vừa soạn và chưa được duyệt, `active`, hoặc `retired`; chỉ `active` được đọc và kiểm), và một luật máy tuỳ chọn.
- **FR-010**: Luật máy của bài học MUST là một trong: cụm từ cấm (áp dụng cho kịch bản, tiêu đề, mô tả và chữ trên thumbnail), hoặc một giới hạn đo được đã có trong máy chấm (ví dụ độ dài câu tối đa, độ dài tiêu đề tối đa). Luật không đọc được MUST bị đánh dấu `invalid` ngay khi ghi, và người dùng được báo.
- **FR-011**: Máy chấm kịch bản và máy kiểm gói đăng MUST kiểm mọi luật máy còn hiệu lực của bài học kênh và bài học chung. Mỗi vi phạm MUST ghi số bài học, và MUST được tính là lỗi nặng: trượt điều kiện cứng ở máy chấm kịch bản; ở máy kiểm gói đăng thì trượt và được sửa một vòng như mọi lỗi gói đăng (011 FR-010). Còn lỗi sau vòng sửa thì phim vẫn được giao, nhưng trang việc và `PUBLISH.md` MUST ghi rõ "lỗi lặp lại bài học #n" và đánh dấu gói "không được đăng khi chưa sửa".
- **FR-012**: Biên tập độc lập MUST ghi P1 khi kịch bản lặp lại một lỗi đã có trong bài học không có luật máy.
- **FR-013**: Xưởng MUST soạn nháp bài học (lỗi gì, vì sao lọt, cách chặn, luật máy đề xuất) từ ghi chú sửa phim hoặc lời người dùng kể; bài học chỉ được lưu sau khi người dùng duyệt, có thể sửa trước khi duyệt. Người dùng cũng tự viết được bài học từ đầu. Xưởng MUST NOT tự lưu bài học khi chưa được duyệt.
- **FR-014**: Bài học MUST NOT bị xoá; người dùng chỉ đổi trạng thái sang `retired`. Bài học `retired` không còn được đọc hay kiểm.

**Lưu trữ**
- **FR-015**: Ở chế độ local, hồ sơ và bài học MUST nằm trong thư mục dự án dưới dạng tệp đọc được bằng mắt, sửa được bằng tay. Chúng MUST được đưa vào git như `my-styles/`, vì đây là kênh của chính người dùng, không phải kênh tham chiếu.
- **FR-016**: Ở chế độ online, mỗi người MUST chỉ thấy và sửa được kênh và bài học kênh của mình. Bài học chung ở bản online MUST là của cả xưởng: chỉ admin thêm, sửa hay bỏ; bài học chung áp cho phim thuộc kênh của mọi người. Người dùng không phải admin chỉ thấy nội dung bài học chung khi một bài học đó chặn phim của họ (trong kết quả chấm).

**Hiển thị online**
- **FR-017**: Giao diện online MUST có trang Channels (danh sách, tạo, sửa hồ sơ, quản lý bài học), và form giao phim MUST có ô chọn kênh, điền sẵn các giá trị của hồ sơ.
- **FR-018**: Trang việc và `CHECKS.md` MUST hiện các lỗi do luật kênh và luật bài học, kèm số bài học.

**Giới hạn**
- **FR-019**: Không clone giọng; giọng đọc chỉ là giọng có sẵn của thư viện. Không phân tích video của kênh khác. Không chọn đề bằng số liệu YouTube. Không đăng lên YouTube. Không sửa `lib/` (hiến pháp VI). Hồ sơ không được dùng để nêu tên kênh tham chiếu trong phim.

### Key Entities

- **Kênh (Channel)**: mã, tên, ngách, khán giả, ngôn ngữ, độ dài mặc định, phong cách, giọng và tốc độ, luật tiêu đề và thumbnail, độ dài tối đa của tiêu đề (tuỳ chọn), hashtag bắt buộc, từ cấm, quyết định, ngày cập nhật. Thuộc về một người (online) hoặc dự án (local).
- **Quyết định (Decision)**: ngày, nội dung.
- **Bài học (Lesson)**: số, ngày, kênh (hoặc chung), phim, lỗi gì, vì sao lọt, cách chặn, trạng thái, luật máy (loại, giá trị, hợp lệ hay không).
- **Phim (Film)**: thêm mã kênh (tuỳ chọn), lưu lại tại thời điểm giao.
- **Kết quả chấm**: thêm vi phạm luật kênh và luật bài học vào kết quả của 010 và 011.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Giao một phim cho một kênh có hồ sơ chỉ cần kênh và ý tưởng (2 thông tin), thay cho 5 thông tin (ý tưởng, phong cách, độ dài, ngôn ngữ, giọng) như hiện nay.
- **SC-002**: Với bộ phim mẫu cố ý vi phạm, máy chấm bắt đúng 100% vi phạm luật kênh và luật bài học có luật máy, và trên phim mẫu đạt thì báo 0 vi phạm.
- **SC-003**: 100% vi phạm của luật bài học được ghi số bài học và được tính là lỗi nặng (kiểm tự động).
- **SC-004**: Phần hồ sơ và bài học mà agent đọc ở đầu mỗi phim không quá 6000 ký tự; trên một phim thật, token thêm vào do phần này không quá 2% tổng token của việc.
- **SC-005**: Ở bản online, một người không xem hay sửa được kênh hay bài học của người khác (kiểm tự động trên mọi đường API của kênh).
- **SC-006**: Mọi phim không gắn kênh cho kết quả chấm giống hệt trước tính năng này (các test của 010 và 011 vẫn đạt mà không phải sửa).

## Assumptions

- Giọng đọc chọn trong danh sách giọng có sẵn của thư viện (công cụ giọng của 010 đã dùng); tốc độ đọc là tốc độ của `SCRIPT.md` (010).
- Bản online hiện viết mọi chữ trong phim bằng tiếng Anh. Với kênh có ngôn ngữ khác, ngôn ngữ của kênh thay cho luật đó ở phim thuộc kênh.
- Luật tiêu đề và thumbnail viết bằng chữ tự do chỉ được agent và biên tập đọc; máy chỉ kiểm phần đo được (hashtag, từ cấm, độ dài).
- Một người có tối đa 20 kênh và mỗi kênh tối đa 200 bài học (kể cả `retired`).
- Ngoài phạm vi: chọn đề bằng số liệu YouTube, mổ xẻ video của kênh mẫu để rút công thức, clone giọng, video dài 8–15 phút, đăng lên YouTube, lịch đăng, tồn kho video.
