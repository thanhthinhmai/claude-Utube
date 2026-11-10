# Feature Specification: Kịch bản được chấm và QC video tự động

**Feature Branch**: `010-script-review-qc`

**Created**: 2026-11-10

**Status**: Draft

**Input**: User description: "010 – Kịch bản và QC tự động cho luồng làm phim (cả chế độ local và online). Lấy ý từ quy trình làm video YouTube bằng đội agent mà người dùng gửi, chỉ phần hợp hiến pháp. (1) Bước Script mới giữa Treatment và Voice: SCRIPT.md (đoạn [P01]…, tiêu đề làm việc, thời lượng mục tiêu) và SOURCES.md. (2) Máy chấm kịch bản bằng script, không tốn token, điểm /10, phải đạt ≥ 7/10. (3) Biên tập độc lập: subagent chấm /10 với lỗi P1/P2/P3 theo số đoạn; đạt khi ≥ 8/10 và không còn P1; chỉ sửa đúng các đoạn bị ghi; giới hạn số vòng; không bao giờ bỏ bước chấm. (4) Mở rộng máy QC video: tỉ lệ lặng, khoảng lặng dài, cảnh đứng im, mốc chuyển cảnh, cảnh chốt ý, đuôi video, ký tự ô vuông; sai thì sửa một vòng như cổng QC 007. Không sửa lib/, không clone giọng kênh thật, không thêm bộ máy vẽ ảnh AI. Ngoài phạm vi: gói đăng, hồ sơ kênh, chọn đề bằng số liệu YouTube, video dài 8–15 phút."

## Clarifications

### Session 2026-11-10

- Q: Hết 2 vòng sửa mà kịch bản vẫn chưa đạt biên tập thì làm gì? → A: Dừng việc, báo lỗi; online là lỗi do xưởng và trả lượt (FR-010).
- Q: Khi viết nguồn và khi biên tập kiểm số liệu, xưởng có được tìm trên web không? → A: Có. Người viết và biên tập dùng công cụ tìm web của Claude, đi qua proxy; container vẫn không có internet. Mọi nguồn phải có đường dẫn đã mở được (FR-002, FR-007a).
- Q: Biên tập độc lập chạy bằng model nào? → A: Chủ xưởng chọn trong Settings, mặc định cùng model với việc (FR-007b).
- Q: Ở chế độ online, khi người giao phim đã chọn duyệt treatment, họ có duyệt luôn kịch bản không? → A: Có, gộp một lần duyệt: lần duyệt treatment chuyển ra sau khi kịch bản đạt, gồm cả bản tóm tắt và kịch bản (FR-019).

## Bối cảnh

Người dùng gửi một quy trình làm video YouTube bằng một đội agent (2026-11-10). Spec này lấy hai phần hợp với xưởng và hiến pháp:
- kịch bản được viết riêng và chấm hai lớp (máy chấm, rồi một biên tập viên độc lập) trước khi thu giọng;
- máy QC video đo thêm nhịp lời và hình, ngoài độ to và chữ đọc được mà 007 đã có.

Hiện tại phim đi thẳng từ bản tóm tắt (`TREATMENT.md`) sang thu giọng. Không ai chấm lời đọc trước khi làm, và cổng QC chỉ đo độ to, đỉnh âm và thời gian đọc chữ.

Áp dụng cho cả hai chế độ: local (làm phim trong khung chat) và online (việc chạy trong container, 007–009).

Mức quy trình: **Đầy đủ**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Lời đọc được chấm trước khi thu giọng (Priority: P1)

Người dùng giao một phim có lời đọc. Sau bản tóm tắt, xưởng viết kịch bản có đánh số đoạn và danh sách nguồn cho mọi con số hay sự kiện. Máy chấm kịch bản cho điểm. Chưa đạt thì xưởng tự sửa. Sau đó một biên tập viên độc lập chấm và ghi lỗi theo số đoạn. Xưởng chỉ sửa các đoạn bị ghi, tới khi đạt. Chỉ kịch bản đã đạt mới được thu giọng.

**Why this priority**: Lời đọc là thứ người xem nghe suốt phim. Sửa lời sau khi đã thu giọng và dựng hình thì tốn gấp nhiều lần sửa trên giấy.

**Independent Test**: Giao một phim 45 giây có lời đọc về một chủ đề có số liệu → trong thư mục phim có kịch bản đánh số đoạn, danh sách nguồn, kết quả máy chấm ≥ 7/10 và kết quả biên tập ≥ 8/10 không còn lỗi P1 → mốc giờ của hai kết quả đều trước mốc giờ của file giọng đầu tiên.

**Acceptance Scenarios**:

1. **Given** một phim có lời đọc, **When** bản tóm tắt xong, **Then** xưởng viết kịch bản: đầu file có tiêu đề làm việc và thời lượng mục tiêu, mỗi đoạn có số `[P01]`, `[P02]`…; và một danh sách nguồn, mỗi con số hoặc sự kiện có một nguồn.
2. **Given** kịch bản vừa viết, **When** máy chấm chạy, **Then** nó in điểm /10, kết quả từng điều kiện cứng và vị trí từng lỗi (số đoạn và câu), không gọi Claude.
3. **Given** máy chấm cho dưới 7/10 hoặc trượt một điều kiện cứng, **When** xưởng sửa, **Then** máy chấm chạy lại; xưởng chưa được gửi cho biên tập.
4. **Given** kịch bản đã qua máy chấm, **When** biên tập viên chấm, **Then** họ chỉ thấy kịch bản, danh sách nguồn, bản tóm tắt và yêu cầu của phim (không thấy quá trình viết), và trả điểm /10 kèm danh sách lỗi P1 (bắt buộc sửa), P2 (nên sửa), P3 (góp ý), mỗi lỗi gắn một số đoạn.
5. **Given** biên tập cho dưới 8/10 hoặc còn lỗi P1, **When** xưởng sửa, **Then** chỉ các đoạn bị ghi lỗi thay đổi (các đoạn khác giữ nguyên từng chữ), máy chấm chạy lại, rồi biên tập chấm lại.
6. **Given** kịch bản đã đạt, **When** xưởng thu giọng, **Then** lời đọc khớp kịch bản đã đạt.
7. **Given** một phim không có lời đọc (chỉ nhạc và hình), **When** bản tóm tắt xong, **Then** xưởng bỏ qua bước kịch bản và ghi rõ lý do "no narration" vào kết quả.
8. **Given** việc online mà người giao phim đã chọn duyệt treatment, **When** kịch bản đạt, **Then** người giao phim nhận một lần duyệt gồm bản tóm tắt, kịch bản và điểm chấm; chưa có file giọng nào trước khi họ duyệt (FR-019).

---

### User Story 2 - Máy QC đo nhịp lời và hình trước khi giao (Priority: P2)

Trước khi giao phim, máy QC đo thêm: tỉ lệ lặng của lời đọc, khoảng lặng dài, cảnh đứng im, mốc chuyển cảnh so với lời, cảnh chốt ý, đuôi video và ký tự hiện thành ô vuông. Phim trượt thì xưởng sửa một vòng rồi đo lại, như cổng QC của 007.

**Why this priority**: Đây là những lỗi người xem thấy ngay (giọng ngắt quãng, hình đứng im, cắt giữa câu, đuôi trống, chữ lỗi), và đo được bằng máy mà không tốn token.

**Independent Test**: Cho máy QC một phim mẫu đạt và các phim mẫu cố ý lỗi (mỗi phim một lỗi) → phim đạt qua hết; mỗi phim lỗi trượt đúng một mục, kèm mốc thời gian của lỗi.

**Acceptance Scenarios**:

1. **Given** một phim có lời đọc, **When** máy QC chạy, **Then** nó báo: tỉ lệ lặng (đạt khi ≤ 20%), mọi khoảng lặng ≥ 0,8 giây không nằm ở chỗ chuyển đoạn, mọi lần chuyển cảnh đến sớm hơn 0,4 giây sau từ cuối của câu, cảnh mang câu cuối của mỗi đoạn ngắn hơn 2,5 giây, và khoảng từ từ cuối cùng tới hết phim (đạt khi ≤ 1,5 giây).
2. **Given** bất kỳ phim nào, kể cả không có lời, **When** máy QC chạy, **Then** nó báo mọi đoạn hình đứng im quá 6 giây và mọi ký tự hiện thành ô vuông, kèm mốc thời gian.
3. **Given** phim trượt một mục QC, **When** việc đang chạy, **Then** xưởng nhận danh sách lỗi kèm số đo, sửa một vòng và đo lại. Vẫn trượt thì việc online lỗi do xưởng (trả lượt) như 007; ở chế độ local, xưởng báo người dùng một dòng khi giao.
4. **Given** phim đạt, **When** xem trang việc (online) hoặc kết quả trong thư mục phim (local), **Then** thấy từng số đo QC và kết quả đạt/trượt.

---

### User Story 3 - Theo dõi kết quả chấm (Priority: P3)

Người giao phim và chủ xưởng xem được điểm máy chấm, điểm biên tập, số vòng sửa và kết quả QC của mỗi phim.

**Why this priority**: Giúp biết bước chấm có thật sự chạy và phim tốt lên ra sao, nhưng không chặn luồng chính.

**Independent Test**: Sau một việc giả có 1 vòng sửa kịch bản → trang việc hiện điểm máy chấm, điểm biên tập của từng vòng và số vòng = 1.

**Acceptance Scenarios**:

1. **Given** một việc đã xong, **When** mở trang việc, **Then** thấy điểm máy chấm và điểm biên tập của từng vòng, số lỗi P1/P2/P3, và kết quả QC.
2. **Given** chế độ local, **When** phim xong, **Then** thư mục phim có một file kết quả chấm đọc được bằng mắt.

### Edge Cases

- Phim rất ngắn (dưới 30 giây): "hook" tính trong 20% đầu của thời lượng thay cho 30 giây đầu; không đòi điểm giữ chân.
- Phim truyện hư cấu không có số liệu: danh sách nguồn được để trống với dòng "no factual claims"; máy chấm vẫn kiểm câu có con số mà không có nguồn.
- Kịch bản tiếng Trung hoặc ngôn ngữ không tách từ bằng khoảng trắng: giới hạn độ dài câu tính theo ký tự (40 ký tự) thay cho 25 từ.
- Biên tập trả kết quả sai định dạng: chấm lại một lần; vẫn sai thì tính là một vòng không đạt.
- Phim sửa sau khi xong (007 "Request changes"): chỉ chấm lại kịch bản khi lời đọc thay đổi; QC luôn chạy lại.
- Chuyển cảnh: khi phim không ghi mốc cảnh, máy QC tự tìm mốc cảnh từ hình.

## Requirements *(mandatory)*

### Functional Requirements

**Kịch bản**
- **FR-001**: Với phim có lời đọc, xưởng MUST viết `SCRIPT.md` sau bản tóm tắt và trước khi thu giọng. Đầu file MUST có tiêu đề làm việc, thời lượng mục tiêu và ngôn ngữ. Mỗi đoạn MUST có số `[Pnn]` duy nhất, tăng dần.
- **FR-002**: Xưởng MUST viết `SOURCES.md`: mỗi con số hoặc sự kiện trong kịch bản gắn với số đoạn và một nguồn (tên nguồn, năm, đường dẫn). Đường dẫn MUST là trang đã mở được bằng công cụ tìm web trong lúc viết (FR-007a); nguồn không có đường dẫn chỉ được dùng khi đó là tài liệu người giao phim tự đưa. Không có số liệu thì ghi "no factual claims".
- **FR-003**: Phim không có lời đọc MUST bỏ qua FR-001 tới FR-010 và ghi lý do vào kết quả chấm.

**Máy chấm kịch bản** (chạy bằng máy, không gọi Claude)
- **FR-004**: Máy chấm MUST kiểm các điều kiện cứng, trượt một điều kiện là không đạt dù điểm cao:
  - đúng định dạng FR-001 (số đoạn, phần đầu file);
  - mọi câu có con số MUST có nguồn cho đoạn đó trong `SOURCES.md`, trừ khi phim là truyện hư cấu và câu không nêu sự thật;
  - thời lượng đọc ước tính nằm trong ±15% thời lượng mục tiêu.
- **FR-005**: Máy chấm MUST cho điểm /10 từ các mục có trọng số:
  - câu dài (> 25 từ, hoặc > 40 ký tự với ngôn ngữ không tách từ);
  - hook: câu hỏi, con số hoặc nghịch lý trong 30 giây đầu (20% đầu với phim dưới 30 giây), và không mở bằng lời giới thiệu;
  - điểm giữ chân cách nhau không quá 90 giây (chỉ với phim từ 90 giây);
  - câu sáo rỗng theo một danh sách có sẵn cho mỗi ngôn ngữ;
  - số viết bằng chữ số ở chỗ giọng đọc dễ đọc sai (ví dụ năm, số thập phân, đơn vị viết tắt), theo luật của ngôn ngữ phim;
  - ngoặc và gạch ngang dày đặc.
- **FR-006**: Kịch bản MUST đạt ≥ 7/10 và mọi điều kiện cứng thì mới được gửi biên tập. Máy chấm MUST in vị trí (số đoạn, câu) cho mỗi lỗi.

**Biên tập độc lập**
- **FR-007**: Biên tập MUST là một lượt Claude riêng, không thấy quá trình viết, chỉ nhận: kịch bản, danh sách nguồn, bản tóm tắt, yêu cầu của phim và phiếu chấm. Biên tập MUST trả điểm /10 và danh sách lỗi; mỗi lỗi có mức P1/P2/P3, số đoạn và một câu lý do.
- **FR-007a**: Người viết và biên tập MUST được dùng công cụ tìm và mở trang web của Claude. Ở chế độ online, công cụ này đi qua proxy của xưởng như mọi lần gọi Claude; container của việc MUST vẫn không có đường ra internet (007). Biên tập MUST mở lại ít nhất các nguồn của những con số chính và ghi P1 cho số nào không khớp nguồn. Token và lượt tìm web được tính vào việc.
- **FR-007b**: Model của biên tập MUST là một cài đặt của chủ xưởng (online: Settings; local: cấu hình của xưởng), mặc định "cùng model với việc". Chỉ admin đổi được cài đặt này. Kết quả chấm MUST ghi model đã dùng.
- **FR-008**: Kịch bản đạt biên tập khi điểm ≥ 8/10 và không còn lỗi P1.
- **FR-009**: Chưa đạt thì xưởng MUST chỉ sửa các đoạn có lỗi P1 hoặc P2. Các đoạn không bị ghi MUST giữ nguyên từng chữ (kiểm bằng máy). Sau khi sửa, máy chấm chạy lại rồi biên tập chấm lại.
- **FR-010**: Bước chấm MUST NOT bị bỏ, kể cả khi việc gần chạm trần token. Số vòng sửa sau biên tập tối đa là 2. Hết 2 vòng mà vẫn chưa đạt thì xưởng MUST dừng, không thu giọng: việc online lỗi do xưởng (trả lượt, 007 FR-006a) kèm điểm cuối và các lỗi còn lại; ở chế độ local, xưởng dừng và báo người dùng điểm cuối cùng các lỗi còn lại.

**Máy QC video** (chạy bằng máy, không gọi Claude)
- **FR-011**: Với phim có lời đọc, máy QC MUST đo từ mốc thời gian từng từ của lời đọc:
  - tỉ lệ lặng trên toàn phần có lời ≤ 20%;
  - khoảng lặng ≥ 0,8 giây chỉ ở chỗ chuyển đoạn `[Pnn]`;
  - mỗi lần chuyển cảnh cách từ cuối của câu đang đọc ít nhất 0,4 giây (không cắt giữa câu);
  - cảnh mang câu cuối của mỗi đoạn hiện ít nhất 2,5 giây;
  - phim hết không quá 1,5 giây sau từ cuối cùng.
- **FR-012**: Với mọi phim, máy QC MUST báo đoạn hình đứng im quá 6 giây (trừ khi `STYLE.md` của phong cách cho phép cảnh tĩnh dài hơn) và mọi ký tự trên màn hình mà phông chữ không có, kèm mốc thời gian.
- **FR-013**: FR-011 và FR-012 MUST nằm trong cùng cổng QC với độ to, đỉnh âm và chữ đọc được của 007, và theo cùng luật: trượt thì xưởng nhận danh sách lỗi kèm số đo, sửa một vòng, đo lại; vẫn trượt thì việc online lỗi do xưởng (trả lượt). Ở chế độ local, cùng các số đo chạy ở bước Self-check và kết quả được báo cho người dùng khi giao.
- **FR-014**: Máy QC MUST chạy được trên phim mẫu không cần mạng, và mỗi mục có một phim mẫu cố ý lỗi để test.

**Kết quả và theo dõi**
- **FR-015**: Mỗi phim MUST có một file kết quả chấm trong thư mục phim: điểm máy chấm và điểm biên tập từng vòng, số lỗi theo mức, số vòng sửa, và từng số đo QC kèm đạt/trượt.
- **FR-016**: Ở chế độ online, trang việc MUST hiện các kết quả của FR-015 cho người giao việc và chủ xưởng. Token của lượt biên tập MUST được tính vào việc như mọi lần gọi khác (008 FR-114).
- **FR-017**: Bước `Script` MUST hiện trong danh sách bước của việc, giữa `Treatment` và `Voice`.

**Duyệt của người giao phim (online)**
- **FR-019**: Khi người giao phim chọn duyệt treatment (007), lần duyệt đó MUST diễn ra sau khi kịch bản đạt máy chấm và biên tập, và MUST gồm cả bản tóm tắt, kịch bản và điểm chấm. Vẫn chỉ một lần dừng chờ duyệt. Người giao phim yêu cầu sửa thì xưởng sửa, rồi kịch bản qua lại máy chấm và biên tập trước khi gửi duyệt lại; các vòng này không tính vào giới hạn 2 vòng của FR-010. Phim không có lời đọc thì lần duyệt chỉ gồm bản tóm tắt như 007.

**Giới hạn**
- **FR-018**: Không sửa file nào trong `lib/` (hiến pháp VI). Không clone giọng của kênh thật; giọng đọc vẫn theo luật hiện có (hiến pháp, bản quyền). Không thêm bộ máy vẽ ảnh AI (hiến pháp VII).

### Key Entities

- **Kịch bản (Script)**: tiêu đề làm việc, thời lượng mục tiêu, ngôn ngữ, các đoạn có số.
- **Nguồn (Source)**: số đoạn, nội dung được dẫn, tên nguồn, năm, đường dẫn.
- **Lượt chấm (Script review)**: ai chấm (máy hay biên tập), model của biên tập, vòng thứ mấy, điểm /10, kết quả điều kiện cứng, danh sách lỗi (mức, số đoạn, lý do).
- **Cài đặt (Settings)**: thêm "model của biên tập" (mặc định cùng model với việc).
- **Kết quả QC (QC result)**: từng số đo, ngưỡng, đạt/trượt, mốc thời gian của lỗi; mở rộng trường `qa` của việc ở 007.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% phim có lời đọc làm sau tính năng này có kịch bản qua máy chấm (≥ 7/10) và biên tập (≥ 8/10, 0 lỗi P1) trước file giọng đầu tiên, hoặc có kết quả ghi rõ vì sao không đạt (kiểm tự động trên việc giả).
- **SC-002**: Máy chấm kịch bản chạy xong dưới 5 giây cho kịch bản 300 giây và gọi Claude 0 lần.
- **SC-003**: Với bộ phim mẫu cố ý lỗi, máy QC bắt đúng 100% lỗi cố ý, và trên phim mẫu đạt thì báo 0 lỗi.
- **SC-004**: Sau mỗi vòng sửa kịch bản, 100% đoạn không bị ghi lỗi giữ nguyên từng chữ (kiểm tự động).
- **SC-005**: Trên một phim thật 45–60 giây có lời đọc, phần token tăng thêm của bước kịch bản và biên tập không quá 15% tổng token của việc.
- **SC-006**: Máy QC mở rộng chạy xong dưới 60 giây cho phim 60 giây.

## Assumptions

- Lời đọc tạo bằng công cụ giọng sẵn có của thư viện, và bước kiểm giọng của thư viện xuất được mốc thời gian từng từ. Xưởng đọc kết quả này, không sửa thư viện.
- Thời lượng đọc ước tính theo tốc độ đọc mặc định của ngôn ngữ (ví dụ khoảng 150 từ mỗi phút với tiếng Anh) khi chưa có giọng.
- Biên tập dùng cùng tài khoản Claude của việc (online) hoặc phiên hiện tại (local); không cần dịch vụ mới.
- Danh sách câu sáo rỗng ban đầu có cho tiếng Anh và tiếng Việt; ngôn ngữ khác chỉ kiểm các mục còn lại.
- Phim online mặc định tối đa 60 giây (chỉnh được tới 300 giây), nên điểm giữ chân chỉ áp dụng cho phim từ 90 giây.
- Ngoài phạm vi: gói đăng (thumbnail, tiêu đề, mô tả), hồ sơ kênh, bài học chung giữa các phim, chọn đề bằng số liệu YouTube, video dài 8–15 phút, AI vẽ ảnh, clone giọng.
