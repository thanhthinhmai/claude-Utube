# Feature Specification: Gói đăng YouTube cho mỗi phim

**Feature Branch**: `011-publish-pack`

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "011 publish pack: after a film passes Self-check, the studio makes films/<name>/publish/ with 3 code-drawn thumbnails (1280x720, a frame of the film plus big title text, <2 MB, readable when small), titles.md (3 titles from different angles: curiosity, number/benefit, question; visible part ≤60 chars), description.md (2-line hook, summary, chapters from paragraph timing following YouTube chapter rules: first at 0:00, ≥3 chapters, each ≥10 s; sources from SOURCES.md; hashtags), subtitles.srt from words.json matching the passed script, and PUBLISH.md combining all. A machine check validates title length, chapter rules, thumbnail size and text, and subtitle/script match; results go into checks.json/CHECKS.md. Online: job page gets a Publish section (view thumbnails, copy titles/description, download srt). Out of scope: uploading to YouTube, AI images or faces. Cost target: under 5% of a film's tokens. Open: language of titles/description (film language vs also English); always made vs customer option."

## Clarifications

### Session 2026-11-11

- Q: Gói đăng luôn được làm, hay chỉ khi người giao phim bật tuỳ chọn? → A: Luôn làm cho mọi phim (FR-001).
- Q: Tiêu đề, mô tả và chữ thumbnail viết bằng ngôn ngữ nào? → A: Chỉ ngôn ngữ của phim (FR-008).
- Q: Phim đã xong trước tính năng này có làm được gói đăng riêng không? → A: Có, chỉ ở chế độ local, bằng một lệnh cho một phim đã xong trong `films/` (FR-001a).
- Q: Bước Publish hỏng giữa chừng (chạm trần token, render thumbnail lỗi) thì việc online kết thúc thế nào? → A: Phim vẫn được giao (việc "done"), không có gói hoặc chỉ có phần đã làm được; trang việc ghi lý do (FR-010).
- Q: Dòng chữ lớn trên thumbnail lấy từ đâu? → A: Mỗi thumbnail đi cặp với một tiêu đề (3 cặp, mỗi hướng một cặp); chữ trên ảnh là câu ngắn bổ sung cho tiêu đề, không lặp chữ của tiêu đề (FR-002, FR-007, FR-009).

## Bối cảnh

Hiện xưởng giao một file video. Để đăng lên YouTube, người dùng vẫn phải tự làm thumbnail, nghĩ tiêu đề, viết mô tả, chia chương và làm phụ đề. Phần lớn dữ liệu cho các việc này xưởng đã có sẵn: phong cách và khung hình của phim, kịch bản đã đạt (010), danh sách nguồn, và mốc thời gian từng từ của lời đọc.

Ý tưởng lấy từ quy trình làm video YouTube bằng đội agent mà người dùng gửi (2026-11-10). Spec 010 đã để phần "gói đăng" ra ngoài phạm vi; spec này làm phần đó.

Áp dụng cho cả hai chế độ: local (làm phim trong khung chat) và online (việc chạy trong container, 007–010).

Mức quy trình: **Đầy đủ**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Nhận gói đăng cùng với phim (Priority: P1)

Người dùng giao một phim có lời đọc. Khi phim xong và qua bước tự kiểm, xưởng làm thêm một gói đăng trong thư mục phim: 3 thumbnail, 3 tiêu đề, một mô tả có chương và nguồn, một file phụ đề, và một file gộp tất cả để copy. Người dùng mở file gộp, chọn một tiêu đề và một thumbnail, rồi dán vào YouTube Studio mà không phải viết thêm.

**Why this priority**: Đây là phần người dùng phải làm tay sau mỗi phim. Có gói đăng thì phim đi thẳng từ xưởng lên kênh.

**Independent Test**: Làm một phim mẫu 45 giây có lời đọc → thư mục `publish/` có đủ 6 file → máy kiểm gói đăng báo đạt mọi mục → mở file gộp thấy 3 tiêu đề, mô tả có ít nhất 3 chương bắt đầu từ 0:00, và nguồn trùng với danh sách nguồn của phim.

**Acceptance Scenarios**:

1. **Given** một phim có lời đọc đã qua bước tự kiểm, **When** xưởng làm gói đăng, **Then** thư mục `films/<tên>/publish/` có `thumbnail-1.png`, `thumbnail-2.png`, `thumbnail-3.png`, `titles.md`, `description.md`, `subtitles.srt` và `PUBLISH.md`.
2. **Given** gói đăng vừa làm, **When** mở `titles.md`, **Then** thấy đúng 3 tiêu đề theo 3 hướng: gợi tò mò, nêu con số hoặc lợi ích, đặt câu hỏi. Mỗi tiêu đề có hướng của nó ghi bên cạnh.
3. **Given** gói đăng vừa làm, **When** mở `description.md`, **Then** thấy theo thứ tự: 2 dòng mở đầu, đoạn tóm tắt, danh sách chương, danh sách nguồn, hashtag.
4. **Given** mỗi thumbnail, **When** xem, **Then** thấy một khung hình của chính phim, theo đúng phong cách của phim, kèm một dòng chữ lớn. 3 thumbnail dùng 3 khung hình khác nhau. Mỗi thumbnail đi cặp với một tiêu đề, và chữ trên ảnh bổ sung cho tiêu đề đó, không lặp lại nó.
5. **Given** file phụ đề, **When** phát cùng video, **Then** chữ của phụ đề khớp đúng lời trong kịch bản đã đạt, và mỗi câu hiện đúng lúc giọng đọc câu đó.
6. **Given** một phim không có lời đọc, **When** xưởng làm gói đăng, **Then** gói có thumbnail, tiêu đề và mô tả, nhưng không có phụ đề và không có chương. File gộp ghi rõ lý do: "no narration".

---

### User Story 2 - Máy kiểm gói đăng trước khi giao (Priority: P2)

Trước khi giao, một máy kiểm gói đăng đo mọi thứ đo được: độ dài tiêu đề, luật chương của YouTube, kích thước và chữ trên thumbnail, và độ khớp giữa phụ đề với kịch bản. Gói trượt thì xưởng sửa một vòng rồi kiểm lại. Kết quả nằm cùng file kết quả chấm của phim (010).

**Why this priority**: Gói đăng sai luật sẽ bị YouTube bỏ qua. Ví dụ, chương sai luật thì không hiện, và thumbnail quá nặng thì không tải lên được. Những lỗi này máy đo được mà không tốn token.

**Independent Test**: Cho máy kiểm một gói đăng mẫu đạt và các gói mẫu cố ý lỗi (mỗi gói một lỗi) → gói đạt qua hết, và mỗi gói lỗi trượt đúng một mục.

**Acceptance Scenarios**:

1. **Given** một gói đăng, **When** máy kiểm chạy, **Then** nó báo từng mục kèm số đo: độ dài từng tiêu đề, luật chương, kích thước và cỡ ảnh, cỡ chữ và độ tương phản của chữ trên thumbnail, độ dài mô tả, số hashtag, và độ khớp của phụ đề.
2. **Given** gói đăng trượt một mục, **When** việc đang chạy, **Then** xưởng nhận danh sách lỗi, sửa một vòng và kiểm lại. Nếu vẫn trượt, phim vẫn được giao, và các lỗi còn lại được ghi rõ trong kết quả chấm và báo cho người dùng một dòng.
3. **Given** máy kiểm chạy xong, **When** mở `CHECKS.md` của phim, **Then** thấy mục "Publish" với từng số đo và kết quả đạt hoặc trượt.

---

### User Story 3 - Lấy gói đăng trên trang việc (Priority: P3)

Ở chế độ online, người giao phim mở trang việc đã xong và thấy mục "Publish". Ở đó họ xem 3 thumbnail, copy từng tiêu đề và cả mô tả bằng một nút, tải file phụ đề, và tải cả gói một lần.

**Why this priority**: Người dùng online không mở được thư mục phim trên máy chủ. Nhưng phần này chỉ là cách hiển thị gói đăng đã có, nên xếp sau.

**Independent Test**: Sau một việc giả đã xong → trang việc có mục "Publish" với 3 ảnh, 3 nút copy tiêu đề, 1 nút copy mô tả, 1 nút tải phụ đề và 1 nút tải cả gói. Người không phải chủ việc và không phải admin thì không xem được.

**Acceptance Scenarios**:

1. **Given** một việc online đã xong có gói đăng, **When** chủ việc mở trang việc, **Then** thấy mục "Publish" với các nội dung trên.
2. **Given** chủ việc bấm copy một tiêu đề, **When** dán ra nơi khác, **Then** được đúng chữ của tiêu đề đó, không kèm nhãn hướng.
3. **Given** một người khác (không phải chủ việc, không phải admin), **When** mở đường dẫn tới gói đăng của việc, **Then** bị từ chối như với file phim (007).
4. **Given** chủ việc yêu cầu sửa phim (007 "Request changes"), **When** bản sửa xong, **Then** gói đăng được làm lại theo bản mới.

### Edge Cases

- Phim quá ngắn để có 3 chương dài ít nhất 10 giây: bỏ phần chương. Mô tả ghi không có chương, và máy kiểm báo mục chương là "không áp dụng" thay cho trượt.
- Một đoạn kịch bản dài dưới 10 giây: gộp với đoạn kế tiếp thành một chương.
- Kịch bản có đoạn cực dài (trên 7 giây không ngắt): phụ đề tách thành nhiều dòng tại chỗ ngắt câu hoặc dấu phẩy gần nhất.
- Phim truyện hư cấu với SOURCES.md là `no factual claims`: mô tả không có mục nguồn. Phim có dòng `fiction`: những dòng đó không vào mục nguồn.
- Ngôn ngữ không tách từ bằng khoảng trắng (tiếng Trung, Nhật, Hàn): độ dài tiêu đề và dòng phụ đề tính theo ký tự, mỗi ký tự tính gấp đôi khi so với giới hạn hiển thị.
- Phim dọc (9:16): thumbnail 720×1280, cùng hướng với phim (FR-002).
- Bước Publish hỏng giữa chừng: phim vẫn được giao với phần gói đã làm được, kèm lý do (FR-010).
- Chữ trên thumbnail có ký tự mà phông chữ không có: tính là trượt mục chữ của thumbnail, giống luật ký tự thiếu phông của 010.
- Phim bị bỏ bước kịch bản (`script skip`): phụ đề lấy từ lời của giọng đọc thay cho kịch bản. Nếu cũng không có lời đọc thì không có phụ đề.

## Requirements *(mandatory)*

### Functional Requirements

**Làm gói đăng**
- **FR-001**: Sau bước tự kiểm của phim (010 FR-013), xưởng MUST làm gói đăng trong `films/<tên>/publish/`. Nếu cổng QC cuối của xưởng trả phim về sửa, gói MUST được làm lại theo bản phim đã sửa. Việc này là một bước mới tên `Publish`, đứng sau `Self-check` trong danh sách bước của việc. Gói đăng luôn được làm cho mọi phim; không có tuỳ chọn bật hay tắt.
- **FR-001a**: Ở chế độ local, người dùng MUST làm được gói đăng cho một phim đã xong trong `films/` (kể cả phim làm trước tính năng này) mà không dựng lại phim. Phim cũ thiếu kịch bản đã đạt hoặc mốc thời gian từng từ thì gói làm với phần có được, và file gộp ghi rõ phần nào thiếu và vì sao. Chế độ online không có lệnh này; việc online cũ không có gói đăng.
- **FR-002**: Gói đăng MUST có 3 thumbnail cùng hướng với phim (1280×720 cho phim ngang, 720×1280 cho phim dọc), mỗi ảnh nhỏ hơn 2 MB; ảnh PNG quá 2 MB thì lưu bằng JPEG (`thumbnail-n.jpg`). Mỗi thumbnail MUST là một khung hình của chính phim, vẽ bằng cùng bộ máy dựng hình và cùng phong cách, cộng thêm một dòng chữ lớn (tối đa 6 từ, hoặc 12 ký tự với ngôn ngữ không tách từ). Thumbnail thứ n đi cặp với tiêu đề thứ n (FR-003); dòng chữ trên ảnh là một câu ngắn bổ sung cho tiêu đề đó và MUST NOT lặp chữ của nó: không trùng nguyên câu và không chung một chuỗi từ 3 từ liền nhau trở lên (6 ký tự liền nhau với ngôn ngữ không tách từ). 3 ảnh MUST lấy từ 3 thời điểm khác nhau của phim. Phông chữ MUST là phông phim đã dùng, hoặc phông có giấy phép đã ghi trong `CREDITS`.
- **FR-003**: Gói đăng MUST có `titles.md` với đúng 3 tiêu đề theo 3 hướng: gợi tò mò, nêu con số hoặc lợi ích, đặt câu hỏi. Mỗi tiêu đề dài tối đa 100 ký tự (giới hạn của YouTube), và 60 ký tự đầu MUST tự đứng được, tức là không bị cắt giữa từ và còn đủ ý chính. Con số trong tiêu đề MUST có trong kịch bản đã đạt hoặc trong danh sách nguồn của nó (kịch bản viết số bằng chữ cho giọng đọc, còn nguồn thường viết bằng chữ số). Tiêu đề và mô tả MUST NOT có dấu `<` hoặc `>` (YouTube không nhận).
- **FR-004**: Gói đăng MUST có `description.md` theo thứ tự:
  1. 2 dòng mở đầu, tổng cộng không quá 150 ký tự (phần YouTube hiện trước nút "xem thêm");
  2. đoạn tóm tắt;
  3. danh sách chương;
  4. danh sách nguồn lấy từ `SOURCES.md` (tên nguồn, năm, đường dẫn), bỏ các dòng `fiction` và `provided:`;
  5. 3 đến 5 hashtag.

  Toàn bộ mô tả tối đa 5000 ký tự. Mọi con số trong mô tả MUST có trong kịch bản đã đạt hoặc danh sách nguồn của nó.
- **FR-005**: Chương MUST tính từ mốc thời gian thật của lời đọc, mỗi chương ứng với một hoặc nhiều đoạn `[Pnn]` liền nhau. Chương MUST theo luật của YouTube: chương đầu ở 0:00, có ít nhất 3 chương, mỗi chương dài ít nhất 10 giây, các mốc tăng dần. Mỗi chương có một tên ngắn, tối đa 40 ký tự. Không thoả được luật thì bỏ phần chương (xem Edge Cases).
- **FR-006**: Với phim có lời đọc, gói đăng MUST có `subtitles.srt`. Chữ của phụ đề MUST khớp lời của kịch bản đã đạt (bỏ qua dấu câu và chữ hoa, chữ thường), và mốc thời gian lấy từ mốc thời gian từng từ của lời đọc. Mỗi khối phụ đề MUST có tối đa 2 dòng, mỗi dòng tối đa 42 ký tự, và hiện từ 1 đến 7 giây.
- **FR-007**: Gói đăng MUST có `PUBLISH.md` gộp 3 cặp tiêu đề và thumbnail (mỗi cặp: hướng, tiêu đề, tên file ảnh, chữ trên ảnh), mô tả đầy đủ và tên file phụ đề, theo đúng thứ tự người dùng điền vào YouTube Studio.
- **FR-008**: Tiêu đề, mô tả và chữ trên thumbnail MUST viết bằng ngôn ngữ của phim (dòng `Language` của kịch bản; phim không có kịch bản thì theo ngôn ngữ trong yêu cầu của phim). Không làm bản dịch.

**Máy kiểm gói đăng** (chạy bằng máy, không gọi Claude)
- **FR-009**: Máy kiểm MUST đo và báo đạt hoặc trượt cho từng mục:
  - đủ file theo FR-001 đến FR-007 (phim không lời thì không đòi phụ đề và chương);
  - cỡ ảnh, dung lượng thumbnail, số từ của dòng chữ trên thumbnail, và chữ trên ảnh không lặp chữ của tiêu đề đi cặp (FR-002);
  - chữ trên thumbnail không che chữ có sẵn của phim ở khung hình đó (đồng hồ, chú thích, phụ đề vẽ trong hình): không phần chữ nào của phim bị che quá 10% diện tích hộp chữ. Phim không khai báo được chữ trên màn hình thì mục này ghi "không kiểm được" thay cho trượt (bổ sung 2026-11-11);
  - chữ trên thumbnail đọc được khi thu nhỏ còn 320×180: chiều cao chữ ít nhất 8% chiều cao ảnh, độ tương phản với nền ít nhất 4,5:1, và không có ký tự thiếu phông;
  - độ dài tiêu đề và 60 ký tự đầu của mỗi tiêu đề (FR-003);
  - độ dài 2 dòng mở đầu, độ dài toàn bộ mô tả và số hashtag (FR-004);
  - luật chương (FR-005);
  - độ khớp và độ dài dòng của phụ đề (FR-006);
  - mọi con số trong tiêu đề và mô tả có trong kịch bản đã đạt hoặc danh sách nguồn, và không có dấu `<`, `>`.
- **FR-010**: Gói trượt thì xưởng MUST sửa một vòng rồi kiểm lại. Vẫn trượt thì phim MUST vẫn được giao (gói đăng không chặn việc giao phim và không làm việc online bị lỗi). Các lỗi còn lại MUST được ghi trong kết quả chấm và báo cho người dùng một dòng. Bước Publish hỏng giữa chừng (chạm trần token của việc, render thumbnail lỗi, hết giờ) cũng theo luật này: việc vẫn "done", không có gói hoặc chỉ có phần đã làm được, không trả lượt, và trang việc ghi lý do. Worker MUST NOT tự chạy lại bước Publish.
- **FR-011**: Kết quả của máy kiểm MUST nằm trong file kết quả chấm của phim (010 FR-015), ở mục riêng "Publish", và không làm mất kết quả kịch bản và QC đã có.
- **FR-012**: Máy kiểm MUST chạy được trên gói mẫu không cần mạng, và mỗi mục MUST có một gói mẫu cố ý lỗi để test.

**Hiển thị online**
- **FR-013**: Ở chế độ online, trang việc đã xong MUST có mục "Publish": xem 3 thumbnail, mỗi tiêu đề có một nút copy, mô tả có một nút copy, một nút tải phụ đề, một nút tải cả gói thành một file, và kết quả của máy kiểm.
- **FR-014**: Chỉ chủ việc và admin MUST xem và tải được gói đăng, giống như file phim (007).
- **FR-015**: Khi phim được sửa (007 "Request changes"), gói đăng MUST được làm lại theo bản mới. Gói cũ không còn hiện trên trang việc.
- **FR-016**: Token của bước Publish MUST được tính vào việc như mọi lần gọi khác (008 FR-114).

**Giới hạn**
- **FR-017**: Xưởng MUST NOT tự đăng phim lên YouTube hay nối với tài khoản kênh nào. Thumbnail MUST NOT dùng ảnh do AI vẽ, ảnh mặt người thật hay hình ngoài phim (hiến pháp VII, mục bản quyền). Không sửa file nào trong `lib/` (hiến pháp VI). Tiêu đề, mô tả và hashtag MUST NOT nêu tên kênh tham chiếu.

### Key Entities

- **Gói đăng (Publish pack)**: thư mục `publish/` của một phim; thuộc về đúng một phim và một phiên bản của phim.
- **Thumbnail**: tiêu đề đi cặp, thời điểm lấy khung hình, dòng chữ, cỡ ảnh, dung lượng, số đo đọc được khi thu nhỏ.
- **Tiêu đề (Title)**: hướng (tò mò, con số hoặc lợi ích, câu hỏi), chữ, độ dài.
- **Mô tả (Description)**: 2 dòng mở đầu, tóm tắt, chương, nguồn, hashtag.
- **Chương (Chapter)**: mốc bắt đầu, tên, các đoạn `[Pnn]` mà chương gồm.
- **Khối phụ đề (Subtitle cue)**: mốc bắt đầu, mốc kết thúc, tối đa 2 dòng chữ.
- **Kết quả kiểm gói (Publish check)**: từng mục, số đo, ngưỡng, đạt hoặc trượt; là một mục mới trong kết quả chấm của 010 và trong trường `qa` của việc.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% phim xong sau tính năng này có gói đăng đủ file. Nếu gói chưa đạt máy kiểm, kết quả chấm ghi rõ vì sao (kiểm tự động trên việc giả).
- **SC-002**: Với bộ gói mẫu cố ý lỗi, máy kiểm bắt đúng 100% lỗi cố ý; trên gói mẫu đạt thì báo 0 lỗi.
- **SC-003**: Máy kiểm chạy xong dưới 10 giây cho một phim 60 giây, và gọi Claude 0 lần.
- **SC-004**: Trên một phim thật 45–60 giây có lời đọc, bước Publish dùng không quá 5% tổng token của việc, và thêm không quá 3 phút vào thời gian làm phim.
- **SC-005**: Trên phim thật đó, gói đăng đạt máy kiểm ngay vòng đầu hoặc sau 1 vòng sửa. Người dùng đăng được lên YouTube chỉ bằng cách copy và dán từ `PUBLISH.md`, không phải sửa chữ nào (kiểm bằng tay một lần).
- **SC-006**: 100% câu trong phụ đề khớp kịch bản đã đạt, và mỗi khối phụ đề bắt đầu lệch không quá 0,3 giây so với từ đầu tiên của nó trong lời đọc.

## Assumptions

- Thumbnail được vẽ bằng chính trang dựng hình của phim tại một thời điểm, với một lớp chữ thêm vào; không cần công cụ vẽ mới (hiến pháp VII).
- Mốc thời gian từng từ và kịch bản đã đạt có sẵn từ 010. Phim bỏ bước kịch bản thì dùng lời của giọng đọc.
- Luật của YouTube được lấy theo tài liệu công khai tại thời điểm viết spec: tiêu đề tối đa 100 ký tự, mô tả tối đa 5000 ký tự, thumbnail 1280×720 và dưới 2 MB, chương bắt đầu ở 0:00, có ít nhất 3 chương, mỗi chương ít nhất 10 giây.
- Người dùng tự chọn tiêu đề và thumbnail. Xưởng không chấm hay xếp hạng 3 phương án.
- Ở chế độ local, bước Publish chạy theo hướng dẫn làm phim (giống bước Script của 010). Chế độ online có worker kiểm bằng máy.
- Ngoài phạm vi: tự đăng lên YouTube, lên lịch đăng, thử A/B thumbnail, đo kết quả sau khi đăng, hồ sơ kênh, chọn đề bằng số liệu YouTube, dịch phụ đề sang ngôn ngữ khác, ảnh bìa bằng AI hoặc ảnh mặt người.
