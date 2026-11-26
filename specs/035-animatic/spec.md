# Feature Specification: Điểm duyệt Animatic cho phim After Effects

**Feature Branch**: `035-animatic`

**Created**: 2026-11-25

**Status**: Draft

**Input**: User description: "035-animatic: Điểm duyệt Animatic cho phim After Effects, thay điểm Shots của phim AE. Thứ tự: Script → Cast → Voice → Animatic → Sound → Final render → Publish. Bản nháp độ phân giải thấp có giọng thật; dải thời gian shot cạnh các câu thoại; báo phần trăm lặng so với giới hạn 20%. Khớp shot theo lời: đề xuất theo TỪNG shot (ví dụ "S2 bớt 1,1 s", shot kết thúc 0,45 s sau câu cuối), người dùng nhận hoặc bỏ từng đề xuất, có Undo; báo khi việc cắt làm mất hoặc dồn một chuyển động ở đuôi shot. Lưới shot: bấm vào phát clip nháp có giọng của shot đó; ghim ghi chú vào điểm trên khung, ghi chú chung cho shot, nút "Send notes to Claude" tạo việc sửa chạy nền chỉ dựng lại các shot có ghi chú ở độ phân giải thấp (dùng lại cơ chế ghim ghi chú của Cast 034 và "Fix with Claude" 032). Sửa ở Animatic chỉ làm Sound (mốc hiệu ứng) và Final render phải chạy lại. Phần âm thanh theo shot (kho tiếng, học tiếng từ video mẫu) là spec 037, ngoài phạm vi. Giao diện theo bản mẫu đã duyệt https://claude.ai/artifact/GQ5frgBviPPC8Sb4xMY434. Phim thử films/ae-sleepless-test (lặng 25–33%)."

## Bối cảnh

- Phim After Effects (specs/032) dùng điểm duyệt Shots chung của specs/026: người dùng xem ảnh tĩnh các cảnh trước khi dựng. Ảnh tĩnh không cho thấy **nhịp**: shot dài bao lâu, lời rơi vào đâu, chỗ nào lặng.
- Phim thử `ae-sleepless-test` (2026-11-25): shot được cắt trước khi có giọng, nên phim lặng 25–33% (luật xưởng cho tối đa 20%). Phải dựng xong bản đẹp, tốn cả lượt dựng AE, mới đo được.
- Video mẫu của phong cách: shot trung vị 2,2 s, giọng gần như liên tục. Nhịp phải được duyệt trên bản nháp **có giọng thật** trước bản đẹp.
- 034 thêm điểm Cast giữa Script và Voice, kèm cơ chế ghim ghi chú lên hình và việc sửa chạy nền. 032 có "Fix with Claude" cho phim AE. 029 có ghi chú theo shot trên phim đã dựng. Animatic dùng lại các cơ chế này.
- Bản mẫu giao diện đã duyệt: https://claude.ai/artifact/GQ5frgBviPPC8Sb4xMY434 (khung Animatic: dải thời gian, nhãn lặng, lưới shot, cột "How Animatic works" và "If you change this").
- Người dùng đã chọn (2026-11-25): đề xuất cắt theo từng shot thay cho một nút áp cả phim; lưới shot phát được clip và ghim được ghi chú như Cast.

## Clarifications

### Session 2026-11-26

- Q: Cắt đuôi shot = câu cuối + 0,45 s không đưa được phim thử từ 32,9% lặng xuống ≤ 20% (chỉ còn 30,3%; lặng nằm ở khoảng hở giữa các câu, cần trung bình ≤ 0,29 s). Đề xuất khớp shot làm gì? → A: Đệm 0,25 s sau từ cuối, và câu đầu của mỗi shot (trừ shot đầu phim) bắt đầu ngay ở đường cắt; câu trong cùng shot giữ khoảng cách với nhau. Phim thử ước tính còn 18,7%.
- Q: Khớp shot "câu cuối + 0,25 s" làm shot chứa lời cuối của đoạn ngắn hơn 2,5 s (lỗi của `qc final`); và khi giữ 2,5 s thì silence vượt 20%? → A: Đề xuất khớp giữ shot cuối đoạn ≥ 2,5 s; phim kẹt giữa hai luật thì duyệt Animatic bằng "Approve anyway".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Xem bản nháp có giọng và duyệt nhịp (Priority: P1)

Sau khi giọng được duyệt, xưởng dựng một bản nháp độ phân giải thấp của cả phim với giọng thật. Ở bước Animatic, người dùng thấy dải thời gian: hàng shot (độ rộng theo thời lượng) và hàng câu thoại ngay dưới, nhãn phần trăm lặng so với giới hạn 20%, tổng thời lượng, và lưới shot (khung đại diện, tên, thời lượng, lời của shot). Người dùng xem bản nháp, rồi duyệt hoặc không.

**Why this priority**: Đây là lý do có bước này: thấy và đo nhịp trước lượt dựng đẹp. Không có bản nháp và dải thời gian thì các story sau không có chỗ để làm.

**Independent Test**: Với `ae-sleepless-test` đã có giọng duyệt, mở bước Animatic: có bản nháp phát được kèm giọng, dải thời gian 9 shot và 14 câu, nhãn lặng trùng với số đo của bước kiểm phim trên cùng bản trộn (sai lệch ≤ 1 điểm phần trăm), và nút duyệt hoạt động.

**Acceptance Scenarios**:

1. **Given** giọng đã duyệt, **When** bước Animatic bắt đầu, **Then** một bản nháp độ phân giải thấp có giọng thật được dựng và hiện trên trang, kèm dải thời gian shot và câu thoại đúng mốc.
2. **Given** bản nháp có phần lặng vượt 20%, **When** trang hiện bước Animatic, **Then** nhãn lặng ghi phần trăm hiện tại và giới hạn, đổi màu cảnh báo, và các khoảng lặng dài nhất được đánh dấu trên dải thời gian.
3. **Given** phần lặng ≤ 20%, **When** người dùng bấm duyệt, **Then** bước Animatic đạt và Sound được phép chạy.
4. **Given** phần lặng vẫn > 20%, **When** người dùng bấm duyệt, **Then** trang hỏi xác nhận "Approve anyway" và ghi lại lựa chọn đó cùng phần trăm lặng; Claude không tự duyệt thay.
5. **Given** điểm Animatic đang bật, **When** có lệnh dựng bản đẹp (Final render) trước khi Animatic được duyệt, **Then** lệnh bị từ chối kèm lý do.

---

### User Story 2 - Khớp shot theo lời, từng shot (Priority: P1)

Với mỗi shot có đầu hoặc đuôi lặng dài, trang đưa một đề xuất riêng, ví dụ "S2: bớt 1,1 s (lời vào ngay, kết thúc 0,25 s sau câu cuối)". Người dùng nhận hoặc bỏ từng đề xuất, hoặc nhận tất cả. Dải thời gian, nhãn lặng và tổng thời lượng cập nhật ngay. Nếu việc cắt làm mất hoặc dồn một chuyển động ở đuôi shot, đề xuất đó báo rõ chuyển động nào. "Undo" trả lại thời lượng trước lần nhận gần nhất.

**Why this priority**: Đây là cách sửa lỗi lặng quá mức của phim thử. Làm theo từng shot để giữ được các khoảng lặng có chủ ý (ví dụ shot kết).

**Independent Test**: Với `ae-sleepless-test`, nhận mọi đề xuất: phần lặng của bản nháp mới ≤ 20%, mỗi shot kết thúc đúng 0,25 s (± 1 khung) sau câu cuối của nó và câu đầu của shot (trừ shot đầu) bắt đầu ở đường cắt (± 1 khung); bỏ đề xuất của S9 thì S9 giữ nguyên thời lượng; Undo trả về đúng thời lượng trước.

**Acceptance Scenarios**:

1. **Given** một shot kết thúc lệch "câu cuối + 0,25 s" quá 1 khung, hoặc câu đầu của nó bắt đầu sau đường cắt quá 1 khung, **When** trang hiện bước Animatic, **Then** shot đó có một đề xuất ghi số giây bớt đi và mốc kết thúc mới.
2. **Given** một đề xuất, **When** người dùng nhận, **Then** chỉ shot đó đổi thời lượng, câu của shot đó dời lên đầu shot; các shot sau dời theo, câu của chúng giữ vị trí trong shot; dải thời gian, nhãn lặng và tổng thời lượng cập nhật.
3. **Given** một đề xuất, **When** người dùng bỏ, **Then** shot giữ nguyên và đề xuất không hiện lại cho tới khi lời hoặc shot thay đổi.
4. **Given** việc cắt làm một chuyển động bắt đầu sau mốc kết thúc mới bị mất, hoặc một chuyển động phải dồn nhanh hơn để vừa, **When** đề xuất hiện, **Then** đề xuất ghi tên chuyển động đó và hậu quả: chuyển động bị mất, hoặc bị cắt dở (ghi tỉ lệ phải dồn nếu muốn giữ trọn). Nhận đề xuất chỉ cắt shot; muốn dồn chuyển động cho vừa, người dùng ghim ghi chú để Claude sửa shot (story 3).
5. **Given** người dùng đã nhận một hay nhiều đề xuất, **When** bấm "Undo", **Then** thời lượng trở về trạng thái trước lần nhận gần nhất.
6. **Given** người dùng đã đổi thời lượng shot, **When** xem bản nháp, **Then** bản nháp được dựng lại theo thời lượng mới (chỉ các shot đổi được dựng lại) trước khi cho duyệt.

---

### User Story 3 - Phát từng shot và ghim ghi chú (Priority: P2)

Bấm vào một shot trong lưới thì phát clip nháp của shot đó kèm giọng. Người dùng ghim ghi chú vào một điểm trên khung (ví dụ "mũ che mắt"), thêm ghi chú chung cho shot (ví dụ "đặt nhân vật lệch trái"), xoá được từng ghi chú. "Send notes to Claude" gửi mọi ghi chú trong một lượt; việc sửa chạy nền, Claude chỉ dựng lại các shot có ghi chú ở độ phân giải thấp và trả lời từng ghi chú.

**Why this priority**: Sửa hình ở bản nháp rẻ hơn nhiều so với sửa sau bản đẹp. Nhưng duyệt nhịp (P1) đã dùng được mà chưa cần story này.

**Independent Test**: Ghim một ghi chú lên S2 và một ghi chú chung cho S6, gửi: chỉ S2 và S6 được dựng lại (các shot khác giống hệt trước, so từng điểm ảnh), mỗi ghi chú có câu trả lời, và trang tự hiện bản nháp mới khi xong.

**Acceptance Scenarios**:

1. **Given** lưới shot, **When** người dùng bấm vào một shot, **Then** clip nháp của shot đó phát kèm giọng của đúng đoạn đó.
2. **Given** clip đang dừng ở một khung, **When** người dùng bấm vào một điểm trên khung, **Then** một ghim có số được đặt tại điểm đó (theo phần trăm của khung, kèm mốc thời gian trong shot) và khung ghi chú mở.
3. **Given** ghi chú trên 2 trong 9 shot, **When** người dùng bấm "Send notes to Claude", **Then** một việc sửa chạy nền trên app, chỉ 2 shot đó được dựng lại ở độ phân giải thấp, mỗi ghi chú có câu trả lời (đã sửa gì, hoặc vì sao chưa sửa được), và bước Animatic trở về chưa duyệt.
4. **Given** một lượt sửa đang chạy, **When** người dùng thêm ghi chú mới, **Then** ghi chú mới chờ lượt sau.
5. **Given** lượt sửa thất bại (AE lỗi, hết thời gian), **When** trang cập nhật, **Then** ghi chú vẫn mở, lỗi được hiện, và cho gửi lại.

---

### Edge Cases

- **Shot không có câu thoại** (shot chuyển cảnh, shot hình): không có đề xuất cắt; shot ghi "no lines" và giữ thời lượng.
- **Câu thoại kéo qua đường cắt** (bắt đầu ở shot này, kết thúc ở shot sau): câu thuộc shot chứa phần lớn thời lượng của câu; đề xuất không bao giờ cắt shot trước khi câu cuối của nó kết thúc.
- **Shot đang ngắn hơn câu của nó** (lời tràn qua shot sau): đề xuất là kéo dài, ghi số giây thêm vào.
- **Đề xuất làm shot ngắn hơn 1 s**: vẫn hiện, kèm cảnh báo "very short shot".
- **Giọng được đọc lại sau khi Animatic đã duyệt** (ví dụ đổi giọng nhân vật, specs/036): mốc câu đổi, Animatic chuyển "Must run again", đề xuất được tính lại.
- **Sửa kịch bản hoặc nhân vật sau khi Animatic đã duyệt**: Animatic chuyển "Must run again" theo đồ thị phụ thuộc hiện có.
- **Cầu nối AE chưa sẵn sàng** khi cần dựng bản nháp: bước Animatic báo rõ AE chưa sẵn sàng và cách bật lại, không âm thầm bỏ qua.
- **Phim web (bộ máy trang)**: không có bước Animatic; giữ điểm Shots như cũ.
- **Phim AE tắt điểm Animatic**: bản nháp và trang vẫn xem và sửa được, nhưng không dừng ở đó (như các điểm duyệt khác, specs/026).

## Requirements *(mandatory)*

### Functional Requirements

**Bước và cổng**
- **FR-001**: Phim AE MUST đi theo thứ tự bước Script → Cast → Voice → Animatic → Sound → Final render → Publish. Animatic thay điểm Shots của phim AE; phim web giữ điểm Shots.
- **FR-002**: Điểm Animatic MUST bật mặc định cho phim AE; tắt được theo phim hoặc theo kênh như các điểm duyệt khác (specs/026).
- **FR-003**: Khi điểm Animatic bật, lệnh dựng bản đẹp MUST bị từ chối khi Animatic chưa được duyệt, kèm lý do.
- **FR-004**: Đổi thời lượng shot hoặc sửa shot ở Animatic sau khi các bước sau đã duyệt MUST đánh dấu "Must run again" cho Sound và Final render, không cho Script, Cast hay Voice.
- **FR-005**: Đọc lại giọng, sửa kịch bản hoặc sửa nhân vật sau khi Animatic đã duyệt MUST đánh dấu Animatic "Must run again".

**Bản nháp và dải thời gian**
- **FR-006**: Sau khi giọng được duyệt, xưởng MUST dựng bản nháp cả phim ở độ phân giải thấp, có giọng thật đặt đúng mốc, và hiện nó ở bước Animatic.
- **FR-007**: Trang MUST hiện dải thời gian gồm hàng shot (độ rộng theo thời lượng, có tên shot) và hàng câu thoại (mỗi câu một khối đúng mốc bắt đầu và kết thúc), cùng tổng thời lượng.
- **FR-008**: Trang MUST hiện phần trăm lặng của bản nháp và giới hạn 20%, tính cùng cách với bước kiểm phim của xưởng, và đánh dấu các khoảng lặng dài nhất khi vượt giới hạn.
- **FR-009**: Trang MUST hiện lưới shot: mỗi shot có khung đại diện, tên, thời lượng và lời của shot.
- **FR-010**: Duyệt Animatic khi phần lặng > 20% MUST cần người dùng xác nhận "Approve anyway"; lựa chọn và phần trăm lặng MUST được ghi lại. Agent MUST NOT tự duyệt hay tự xác nhận ngoại lệ này; lệnh xác nhận ngoại lệ MUST bị từ chối khi chạy bên trong một việc của app.

**Khớp shot theo lời**
- **FR-011**: Với mỗi shot có câu thoại mà mốc kết thúc khác "từ cuối + 0,25 s" quá 1 khung, hoặc câu đầu bắt đầu sau đường cắt quá 1 khung (trừ shot đầu phim), trang MUST đưa một đề xuất riêng cho shot đó, ghi số giây bớt hoặc thêm và mốc kết thúc mới. Nhận đề xuất đưa câu đầu của shot về đường cắt (câu trong shot giữ khoảng cách với nhau) và đặt đuôi shot ở từ cuối + 0,25 s; riêng shot chứa lời cuối của một đoạn giữ tối thiểu 2,5 s (mức của bước kiểm phim), phần dư thành khoảng lặng cuối đoạn, và đề xuất ghi rõ lý do giữ.
- **FR-012**: Người dùng MUST nhận hoặc bỏ được từng đề xuất, và nhận được tất cả trong một lần bấm. Nhận một đề xuất MUST chỉ đổi thời lượng shot đó; các shot sau dời theo.
- **FR-013**: Đề xuất bị bỏ MUST không hiện lại cho tới khi lời hoặc thời lượng của shot đó thay đổi.
- **FR-014**: Đề xuất làm mất một chuyển động (bắt đầu sau mốc kết thúc mới) hoặc cắt dở một chuyển động MUST ghi tên chuyển động và hậu quả (mất, hoặc cắt dở kèm tỉ lệ phải dồn để giữ trọn). Nhận đề xuất MUST NOT tự dồn chuyển động; việc dồn đi qua ghi chú (FR-019, FR-020).
- **FR-015**: "Undo" MUST trả thời lượng các shot về trạng thái trước lần nhận gần nhất; Undo MUST lặp được về tới thời lượng lúc bước Animatic bắt đầu.
- **FR-016**: Sau khi thời lượng đổi, bản nháp MUST được dựng lại trước khi cho duyệt; chỉ các shot đổi thời lượng hoặc bị ghi chú MUST được dựng lại.
- **FR-017**: Thời lượng đã nhận MUST được bản đẹp dùng đúng như thế (bản đẹp và bản nháp có cùng mốc cắt, ± 1 khung).

**Phát shot và ghi chú**
- **FR-018**: Bấm vào một shot MUST phát clip nháp của shot đó kèm giọng của đúng đoạn đó.
- **FR-019**: Người dùng MUST ghim được ghi chú vào một điểm trên khung của shot (vị trí theo phần trăm, kèm mốc thời gian trong shot), thêm ghi chú chung cho shot, và xoá từng ghi chú; cách ghim giống bước Cast (specs/034).
- **FR-020**: "Send notes to Claude" MUST gửi mọi ghi chú đang mở trong một lượt; việc sửa MUST chạy nền trên app, người dùng không phải mở chat (như "Fix with Claude", specs/032). Claude MUST chỉ dựng lại các shot có ghi chú, ở độ phân giải thấp, và MUST trả lời từng ghi chú.
- **FR-021**: Khi lượt sửa xong, trang MUST tự hiện bản nháp mới và các câu trả lời; bước Animatic MUST trở về chưa duyệt.
- **FR-022**: Ghi chú thêm trong lúc một lượt sửa đang chạy MUST chờ lượt sau; lượt thất bại MUST giữ ghi chú mở và cho gửi lại.

**Giao diện**
- **FR-023**: Khung Animatic MUST theo bản mẫu đã duyệt: dải thời gian và chú giải, nhãn lặng, dòng kết quả khớp shot kèm Undo, lưới shot, cột "How Animatic works" và "If you change this" (ghi Sound và Final render).

### Key Entities

- **Bản nháp (Animatic draft)**: bản dựng độ phân giải thấp của cả phim có giọng thật, ứng với một bộ thời lượng shot; có phần trăm lặng và tổng thời lượng; giữ đúng một bản trước để so.
- **Thời lượng shot (Shot timing)**: mốc bắt đầu và kết thúc của mỗi shot; có lịch sử để Undo; là nguồn thời lượng duy nhất cho bản nháp, Sound và bản đẹp.
- **Câu thoại có mốc (Timed line)**: câu của giọng đã duyệt, có mốc bắt đầu, kết thúc và shot chứa nó.
- **Đề xuất khớp shot (Fit suggestion)**: thuộc một shot; số giây bớt hoặc thêm, mốc kết thúc mới, các chuyển động bị ảnh hưởng và cách xử lý; trạng thái mới, đã nhận, đã bỏ.
- **Ghi chú shot nháp (Animatic note)**: thuộc một shot; có thể gắn với một điểm (phần trăm) và mốc thời gian, hoặc chung; trạng thái mở hoặc đã trả lời; câu trả lời của Claude; lượt sửa.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Bản nháp của một phim 30 s sẵn sàng để xem trong ≤ 3 phút sau khi giọng được duyệt (AE đã mở trên máy), nhanh hơn ít nhất 3 lần so với bản đẹp của cùng phim.
- **SC-002**: Với `ae-sleepless-test`, nhận mọi đề xuất khớp shot đưa phần lặng từ 33% xuống ≤ 20% cộng phần lặng do giữ shot cuối đoạn 2,5 s (đo được: 22%, nên duyệt cần "Approve anyway"); mỗi shot có lời kết thúc 0,25 s (± 1 khung) sau câu cuối của nó, trừ shot cuối đoạn kéo lên 2,5 s; `qc final` không còn lỗi shot cuối đoạn.
- **SC-003**: Phần trăm lặng hiện ở bước Animatic khớp với số đo của bước kiểm phim trên bản đẹp dựng từ cùng thời lượng (sai lệch ≤ 1 điểm phần trăm).
- **SC-004**: Mốc cắt của bản đẹp trùng mốc cắt đã duyệt ở Animatic cho 100% shot (± 1 khung).
- **SC-005**: Một lượt "Send notes to Claude" chỉ dựng lại các shot có ghi chú: các shot khác của bản nháp giống hệt trước (so từng điểm ảnh), và 100% ghi chú có câu trả lời.
- **SC-006**: 100% lệnh dựng bản đẹp bị từ chối khi điểm Animatic bật mà chưa duyệt, có test tự động.
- **SC-007**: Ghim ghi chú được đặt lệch ≤ 2% chiều rộng khung so với điểm bấm, ở cả màn hình máy tính và điện thoại (≈ 400 px).

## Assumptions

- Chỉ áp dụng cho phim After Effects; phim web giữ điểm Shots hiện tại.
- Xây trên 034 (bước Cast, cơ chế ghim ghi chú, việc sửa chạy nền) và 032 (bộ dựng AE, cầu nối, "Fix with Claude"). Code của 035 bắt đầu sau khi 034 được commit đủ; thứ tự merge dự kiến 034 → 036 → 035.
- Khoảng đệm sau từ cuối là 0,25 s và câu đầu của shot vào ngay ở đường cắt, cố định cho bản này (người dùng chọn 2026-11-26: giọng gần như liên tục như video mẫu; 0,45 s không đạt 20%); chỉnh theo phong cách là việc sau.
- Bản nháp dựng qua cùng đường dựng AE của xưởng (trên máy hoặc qua cầu nối của app), ở độ phân giải thấp và chất lượng nháp; hình nháp có thể thiếu hiệu ứng nặng (mờ, phát sáng) nhưng đúng bố cục, chuyển động và thời lượng.
- Giới hạn lặng 20% và cách đo lặng lấy từ bước kiểm phim hiện có của xưởng.
- Bản nháp dùng bản trộn tạm của giọng (có thể kèm nhạc nền hiện có); tiếng theo shot thuộc spec 037, ngoài phạm vi.
- Sound (specs/026 Mix) giữ như cũ, chỉ đứng sau Animatic; mốc hiệu ứng được tính lại từ thời lượng mới.
- Một người dùng (chủ xưởng) duyệt; không có phân quyền duyệt riêng ở bản này.
