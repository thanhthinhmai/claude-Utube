# Feature Specification: Duyệt nhân vật cho phim After Effects

**Feature Branch**: `034-cast-review`

**Created**: 2026-11-25

**Status**: Draft

**Input**: User description: "034-cast-review: Điểm duyệt nhân vật (Cast) và quy trình duyệt cho phim After Effects. Mỗi phim AE có thêm điểm duyệt "Cast" nằm giữa Script và Voice: mỗi nhân vật của phim có một bảng mẫu do rig AE tự vẽ (ba góc trước, sau, 3/4; các biểu cảm; các tư thế; một clip đi bộ lặp; bảng màu và thông số). Người dùng duyệt từng nhân vật hoặc cả dàn, ghim ghi chú vào đúng điểm trên một hình (có thể dời ghim, xoá ghi chú), ghi chú chung cho cả nhân vật, yêu cầu vẽ thêm một góc còn thiếu (bỏ yêu cầu được), rồi "Send notes to Claude" gửi mọi ghi chú một lượt; Claude chỉ vẽ lại các nhân vật có ghi chú và gửi lại bảng mẫu để duyệt. Nhân vật đã duyệt được lưu vào kho nhân vật của kênh (Cast library) để phim sau dùng lại không phải duyệt; phim dùng nhân vật chưa duyệt thì bị chặn ở bước giọng. Rig nhân vật chung có phiên bản: nhân vật đã duyệt giữ phiên bản rig lúc duyệt; khi rig có bản mới (ví dụ thêm một góc), Cast library báo và người dùng chọn cập nhật nhân vật nào (dựng lại và duyệt lại). Thêm điểm duyệt "Animatic" cho phim AE: bản nháp độ phân giải thấp có giọng thật, dải thời gian shot cạnh lời, báo phần trăm lặng, nút khớp shot theo lời (mỗi shot kết thúc ngay sau câu cuối của nó). Thứ tự bước của phim AE: Script → Cast → Voice → Animatic → Sound (Mix) → Final render → Publish. Giao diện theo bản mẫu đã duyệt: https://claude.ai/artifact/GQ5frgBviPPC8Sb4xMY434. Phim thử: films/ae-sleepless-test (rig riêng của phim, sẽ chuyển vào bộ dựng chung). Video mẫu phong cách: nhân vật chính và vai phụ dùng lại nhiều lần, shot trung vị 2,2 s, nhạc nền liên tục."

## Bối cảnh

- Phim After Effects (specs/032) hiện có các điểm duyệt chung của specs/026: Script, Voice, Shots, Mix, Publish. Không có bước nào để người dùng xem và duyệt **nhân vật** trước khi phim được dựng. Nhân vật chỉ hiện ra lần đầu trong bản dựng, lúc sửa đã tốn cả lượt dựng AE.
- Phim thử `ae-sleepless-test` (2026-11-25) cho thấy hai vấn đề:
  - Nhân vật được vẽ thẳng trong phim. Lỗi con ngươi bị che và mũ che mắt chỉ lộ ra sau khi dựng cả 9 shot.
  - Shot được cắt trước khi có giọng, nên phim lặng 33% (luật xưởng cho tối đa 20%), mà phải dựng xong bản đẹp mới đo được.
- Video mẫu của phong cách này dùng lại một nhân vật chính và các vai phụ qua nhiều phim, shot trung vị 2,2 s, giọng gần như liên tục và nhạc nền chạy suốt. Vì vậy nhân vật nên được chốt **một lần** cho kênh, và nhịp shot nên được duyệt trên bản nháp có giọng trước khi dựng bản đẹp.
- Rig nhân vật (đầu cầu, thân hoodie, tay chân ống mềm) hiện nằm riêng trong thư mục phim thử. Mỗi nhân vật là một bộ thông số (màu, kiểu tóc hoặc mũ, tỉ lệ) dựng bằng rig chung; góc nhìn là một thông số khi dựng.
- Xưởng đã có mẫu duyệt tương tự cho người thật (specs/028: bảng mẫu, duyệt, chặn khi chưa duyệt) và cho ghi chú theo shot (specs/029: ghi chú, "Fix with Claude").
- Bản mẫu giao diện đã duyệt: https://claude.ai/artifact/GQ5frgBviPPC8Sb4xMY434

## Clarifications

### Session 2026-11-25

- Q: Có làm phần Animatic ngay trong tính năng này, hay tách sang tính năng riêng? → A: Tách. 034 làm Cast, kho nhân vật và phiên bản rig; Animatic là tính năng 035, làm ngay sau.
- Q: Khi bấm "Send notes to Claude", việc vẽ lại chạy ở đâu? → A: App tự tạo một việc sửa nhân vật chạy nền (như "Fix with Claude" của phim AE); xong thì bảng mẫu mới và câu trả lời hiện trên trang, người dùng không phải mở chat.
- Q: Kho nhân vật của kênh lưu ở đâu? → A: Chỉ trong kho dữ liệu của app desktop (kho của chủ xưởng), không vào git.
- Q: Biểu cảm và tư thế trên bảng mẫu là bộ cố định hay theo phim? → A: Theo phim: chỉ các biểu cảm và tư thế mà kịch bản của phim cần cho nhân vật đó.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Duyệt nhân vật của phim trước khi làm giọng (Priority: P1)

Sau khi kịch bản được duyệt, xưởng dựng một bảng mẫu cho mỗi nhân vật của phim và dừng ở bước **Cast**. Trên trang việc, người dùng thấy danh sách nhân vật (tên, vai, trạng thái) và bảng mẫu của nhân vật đang chọn: ba góc (trước, sau, 3/4), các biểu cảm và tư thế mà kịch bản cần cho nhân vật đó, một clip đi bộ lặp, bảng màu kèm mã màu, và các đoạn kịch bản có nhân vật đó. Người dùng duyệt từng nhân vật, hoặc bấm "Approve cast" để duyệt cả dàn. Khi mọi nhân vật đã duyệt, phim chuyển sang bước Voice.

**Why this priority**: Đây là bước người dùng yêu cầu trực tiếp và là cổng chặn lỗi nhân vật trước mọi bước tốn kém. Chỉ riêng story này đã có giá trị: người dùng thấy và chốt nhân vật trước khi có giọng hay hình.

**Independent Test**: Tạo một phim AE có 3 nhân vật (nhân vật chính, bạn thân, nhóm 4 bạn cùng lớp như `ae-sleepless-test`), duyệt kịch bản. Trang việc dừng ở Cast với 3 bảng mẫu (nhóm nền: 1 ảnh nhóm); bảng của nhân vật chính có đủ 3 góc, đúng các biểu cảm và tư thế kịch bản cần (ví dụ mắt mở to, ngáp, ngồi bật dậy, ôm đàn, giơ tay), và clip đi bộ. Lệnh làm giọng bị từ chối cho tới khi bấm "Approve cast"; sau đó chạy được.

**Acceptance Scenarios**:

1. **Given** phim AE vừa được duyệt kịch bản và có danh sách nhân vật, **When** bước Cast bắt đầu, **Then** mỗi nhân vật có một bảng mẫu dựng từ rig, gồm góc trước, sau, 3/4, các biểu cảm và tư thế mà kịch bản cần cho nhân vật đó, clip đi bộ lặp (nếu nhân vật đi) và bảng màu; trang việc hiện bước Cast ở trạng thái "Your review".
2. **Given** bước Cast đang chờ duyệt, **When** người dùng duyệt từng nhân vật một, **Then** nhân vật đó hiện "Approved", và bước Cast chỉ đạt khi mọi nhân vật đã duyệt.
3. **Given** bước Cast đang chờ duyệt, **When** người dùng bấm "Approve cast", **Then** mọi nhân vật được duyệt cùng lúc và phim chuyển sang bước Voice.
4. **Given** còn ít nhất một nhân vật chưa duyệt, **When** có lệnh làm giọng cho phim, **Then** lệnh bị từ chối, kèm tên các nhân vật chưa duyệt.
5. **Given** một nhóm nhân vật nền (ví dụ "Classmates ×4"), **When** dựng bảng mẫu, **Then** nhóm có một ảnh nhóm thay cho bảng đầy đủ của từng người, và được duyệt như một mục.

---

### User Story 2 - Ghi chú lên nhân vật và để Claude vẽ lại (Priority: P1)

Người dùng thấy một nhân vật chưa đúng (ví dụ tóc của bạn thân chưa xoăn như mong muốn). Họ bấm vào đúng chỗ trên một hình của bảng mẫu (mái tóc trên hình "Front"): một chấm ghim được cắm tại điểm đó và khung ghi chú mở ngay dưới hình, có hình phóng to để dời ghim. Họ gõ ghi chú và bấm "Add note". Họ cũng có thể viết ghi chú chung cho cả nhân vật, yêu cầu vẽ một góc còn thiếu ("Request this view", bỏ được bằng "Undo"), và xoá bất kỳ ghi chú nào. Xong, họ bấm "Send notes to Claude": mọi ghi chú được gửi một lượt; Claude chỉ vẽ lại các nhân vật có ghi chú, trả lời từng ghi chú, dựng lại bảng mẫu của các nhân vật đó và đưa bước Cast về chờ duyệt.

**Why this priority**: Duyệt mà không sửa được thì phải nhắn vào chat như trước, dễ nhầm chỗ. Ghim vào đúng điểm trên hình là cách người dùng đã yêu cầu khi xem bản mẫu.

**Independent Test**: Ở bước Cast của phim thử, ghim 1 ghi chú lên tóc ở hình "Front" của bạn thân, thêm 1 ghi chú chung, xoá 1 ghi chú, gửi. Chỉ bảng mẫu của bạn thân được dựng lại (bảng mẫu của 2 mục còn lại giữ nguyên, so từng điểm ảnh); ghi chú còn lại có câu trả lời của Claude; bước Cast quay về "Your review".

**Acceptance Scenarios**:

1. **Given** bảng mẫu đang mở, **When** người dùng bấm vào một điểm trên một hình, **Then** một ghim có số thứ tự được đặt tại điểm đó (theo phần trăm chiều rộng và chiều cao của hình) và khung ghi chú mở ngay dưới nhóm hình đó.
2. **Given** khung ghi chú đang mở, **When** người dùng bấm vào hình phóng to, **Then** ghim dời tới điểm mới và chữ đang gõ được giữ nguyên.
3. **Given** một ghi chú đã thêm, **When** người dùng bấm "Delete" trên ghi chú đó, **Then** ghi chú và ghim của nó biến mất, các ghi chú còn lại được đánh số lại.
4. **Given** một góc chưa có hình, **When** người dùng bấm "Request this view", **Then** một yêu cầu vẽ góc đó được thêm vào danh sách ghi chú; bấm "Undo" thì yêu cầu bị bỏ. Bấm vào ô trống (ngoài nút) không thêm gì.
5. **Given** có ghi chú trên 1 trong 3 nhân vật, **When** người dùng bấm "Send notes to Claude", **Then** chỉ nhân vật đó được vẽ lại, mỗi ghi chú có một câu trả lời (đã sửa gì, hoặc vì sao chưa sửa được), và nhân vật đó trở về chưa duyệt; các nhân vật đã duyệt giữ nguyên trạng thái.
6. **Given** người dùng thêm ghi chú lên một nhân vật đã duyệt, **When** ghi chú được thêm, **Then** nhân vật đó trở về chưa duyệt.

---

### User Story 3 - Kho nhân vật của kênh (Priority: P2)

Nhân vật đã duyệt được lưu vào kho nhân vật của kênh (Cast library) khi ô "Save approved characters to the channel's cast" được chọn. Phim sau của cùng kênh dùng lại nhân vật đó: bước Cast hiện nhân vật ở trạng thái "From the channel, approved" và không bắt duyệt lại. Trang Cast library liệt kê các nhân vật của từng kênh, kèm bảng mẫu, ngày duyệt, phiên bản rig và các phim đã dùng.

**Why this priority**: Phong cách này dùng lại nhân vật chính qua nhiều phim. Không có kho thì mỗi phim phải duyệt lại, và nhân vật có thể lệch nhau giữa các phim.

**Independent Test**: Duyệt nhân vật chính ở phim A (kênh K) với ô lưu được chọn. Tạo phim B của kênh K dùng nhân vật chính: bước Cast của phim B đạt ngay cho nhân vật đó, bảng mẫu trùng với bảng đã duyệt ở phim A.

**Acceptance Scenarios**:

1. **Given** ô lưu được chọn, **When** một nhân vật được duyệt, **Then** nhân vật được ghi vào kho của kênh, kèm bảng mẫu, ngày duyệt, phiên bản rig và tên phim.
2. **Given** một phim mới của kênh dùng nhân vật có trong kho, **When** bước Cast bắt đầu, **Then** nhân vật đó đã ở trạng thái duyệt; chỉ các nhân vật mới, và các hình mới mà phim cần của nhân vật cũ, cần duyệt. Phim mà mọi nhân vật đều có trong kho thì bước Cast đạt ngay.
3. **Given** một nhân vật trong kho, **When** phim mới muốn đổi nhân vật đó (ví dụ đổi màu áo), **Then** đó là một nhân vật mới (hoặc bản mới của nhân vật) và phải duyệt lại; bản cũ trong kho không bị đổi.
4. **Given** ô lưu không được chọn, **When** nhân vật được duyệt, **Then** nhân vật chỉ được duyệt cho phim này, không vào kho.

---

### User Story 4 - Phiên bản rig và cập nhật nhân vật (Priority: P2)

Rig nhân vật dùng chung có số phiên bản. Mỗi nhân vật đã duyệt ghi phiên bản rig lúc duyệt và luôn được dựng bằng đúng phiên bản đó, nên sửa rig (ví dụ thêm một góc nhìn) không làm đổi nhân vật đã duyệt ở phim khác. Khi rig có bản mới, Cast library báo "New rig version" cho các nhân vật đang dùng bản cũ; người dùng xem trước bảng mẫu dựng bằng bản mới cạnh bản đã duyệt, rồi chọn cập nhật nhân vật nào. Nhân vật được cập nhật phải duyệt lại.

**Why this priority**: Yêu cầu "vẽ thêm góc" ở story 2 có thể phải sửa rig chung. Không có phiên bản thì sửa cho một phim sẽ âm thầm đổi nhân vật của mọi phim.

**Independent Test**: Duyệt nhân vật chính bằng rig bản N. Tăng rig lên bản N+1 có đổi hình (ví dụ thêm góc nghiêng). Dựng lại một shot của phim cũ: nhân vật giống hệt trước (so từng điểm ảnh). Cast library báo bản mới cho nhân vật chính; bấm xem trước thấy bảng mẫu hai bản cạnh nhau; chọn cập nhật thì nhân vật về "chưa duyệt" với bản N+1.

**Acceptance Scenarios**:

1. **Given** nhân vật được duyệt bằng rig bản N, **When** rig lên bản N+1, **Then** mọi lần dựng nhân vật đó vẫn dùng bản N cho tới khi người dùng chọn cập nhật.
2. **Given** rig có bản mới, **When** mở Cast library, **Then** mỗi nhân vật đang dùng bản cũ có nhãn "New rig version" và nút xem trước.
3. **Given** người dùng xem trước, **When** chọn cập nhật một nhân vật, **Then** nhân vật dùng bản mới, về trạng thái chưa duyệt; nhân vật không được chọn giữ bản cũ.
4. **Given** một yêu cầu vẽ góc mà rig hiện tại đã vẽ được, **When** Claude xử lý yêu cầu, **Then** chỉ dựng lại bảng mẫu, không tạo phiên bản rig mới.

---

### Edge Cases

- **Phim không có nhân vật** (chỉ đồ vật, chữ): bước Cast tự đạt kèm lý do "no characters".
- **Rig không dựng được một góc hoặc một biểu cảm**: ô đó hiện "No picture yet" kèm nút "Request this view"; bảng mẫu vẫn dùng được, và bước Cast vẫn duyệt được nếu người dùng chấp nhận.
- **Lượt vẽ lại của Claude thất bại** (AE lỗi, hết thời gian): bước Cast giữ ghi chú ở trạng thái mở, hiện lỗi, và cho gửi lại.
- **Người dùng thêm ghi chú trong lúc Claude đang vẽ lại**: ghi chú mới chờ lượt sau, không chen vào lượt đang chạy (giống specs/029).
- **Sửa kịch bản sau khi Cast đã duyệt** làm thêm hoặc bớt nhân vật: chỉ nhân vật mới cần duyệt; nhân vật bị bớt không còn nằm trong phim.
- **Đổi nhân vật sau khi giọng hoặc bảng cảnh đã duyệt**: các bước Shots và Final render chuyển "Must run again"; giọng không phải làm lại.
- **Cầu nối AE chưa sẵn sàng** khi cần dựng bảng mẫu: bước Cast báo rõ AE chưa sẵn sàng và cách bật lại, không âm thầm bỏ qua.
- **Phim web (bộ máy trang)**: không có bước Cast; quy trình như cũ.
- **Phim mới cần một biểu cảm hoặc tư thế chưa có trong bảng mẫu của nhân vật trong kho**: chỉ các hình mới được dựng và cần duyệt; phần đã duyệt của nhân vật giữ nguyên, và hình mới được thêm vào bảng mẫu trong kho khi duyệt.
- **Kịch bản đổi sau khi Cast đã duyệt** làm cần thêm biểu cảm hoặc tư thế: chỉ các hình mới cần duyệt.
- **App không chạy** khi làm phim bằng chat: bước Cast duyệt trong phim như bình thường; ô lưu vào kho bị tắt kèm lý do "the app is not running".
- **Hai phim cùng kênh duyệt cùng một nhân vật mới cùng lúc** với hai bản khác nhau: bản được duyệt sau trở thành một bản mới của nhân vật, không ghi đè bản trước.

## Requirements *(mandatory)*

### Functional Requirements

**Bước và cổng**
- **FR-001**: Phim AE MUST đi theo thứ tự bước Script → Cast → Voice → Shots → Sound → Final render → Publish. Cast là điểm duyệt mới, nằm giữa Script và Voice. (Tính năng 035 sẽ thay điểm Shots của phim AE bằng Animatic; ngoài phạm vi 034.)
- **FR-002**: Điểm Cast MUST bật mặc định cho phim AE; người dùng tắt được theo phim hoặc theo kênh như các điểm duyệt khác (specs/026).
- **FR-003**: Khi điểm Cast bật, lệnh làm giọng MUST bị từ chối khi còn nhân vật chưa duyệt, và báo tên các nhân vật đó.
- **FR-005**: Sửa nhân vật sau khi đã duyệt các bước sau MUST đánh dấu "Must run again" cho Shots và Final render, không cho Voice.

**Bảng mẫu nhân vật**
- **FR-006**: Mỗi nhân vật của phim MUST có một bảng mẫu dựng từ rig nhân vật dùng chung, gồm: góc trước, sau và 3/4; các biểu cảm và tư thế mà kịch bản của phim cần cho nhân vật đó (mỗi hình ghi câu hoặc đoạn kịch bản cần nó); một clip đi bộ lặp 2–3 s nếu nhân vật đi trong phim; bảng màu kèm mã màu; danh sách đoạn kịch bản có nhân vật.
- **FR-007**: Nhóm nhân vật nền MUST dùng được một ảnh nhóm thay cho bảng đầy đủ.
- **FR-008**: Hình nào rig không dựng được MUST hiện "No picture yet" kèm nút "Request this view", không làm hỏng cả bảng.

**Ghi chú và vẽ lại**
- **FR-009**: Người dùng MUST ghim được ghi chú vào một điểm trên bất kỳ hình nào của bảng mẫu; vị trí ghim lưu theo phần trăm của hình; ghim dời được trước khi lưu.
- **FR-010**: Người dùng MUST thêm được ghi chú chung cho cả nhân vật, xoá được từng ghi chú, và thêm hoặc bỏ được yêu cầu vẽ một góc.
- **FR-011**: "Send notes to Claude" MUST gửi mọi ghi chú đang mở trong một lượt và việc vẽ lại MUST chạy nền trên app; người dùng không phải mở chat. Trong việc làm phim, Claude của chính việc đó vẽ lại; ngoài việc làm phim (Cast library), app tạo một việc sửa nhân vật. Trang việc MUST hiện việc sửa đang chạy, và khi xong MUST tự hiện bảng mẫu mới cùng các câu trả lời. Claude MUST chỉ vẽ lại các nhân vật có ghi chú và MUST trả lời từng ghi chú (đã sửa gì, hoặc vì sao chưa sửa được).
- **FR-012**: Thêm ghi chú lên nhân vật đã duyệt, hoặc nhân vật được vẽ lại, MUST đưa nhân vật đó về chưa duyệt.
- **FR-013**: Ghi chú thêm trong lúc một lượt vẽ lại đang chạy MUST chờ lượt sau.
- **FR-014**: Mỗi lượt vẽ lại MUST giữ đúng một bảng mẫu trước của nhân vật để so trước và sau.

**Kho nhân vật của kênh**
- **FR-015**: Nhân vật đã duyệt MUST vào kho nhân vật của kênh khi người dùng chọn lưu, kèm bảng mẫu, thông số, ngày duyệt, phiên bản rig và tên phim. Kho nằm trong kho dữ liệu của app desktop (kho của chủ xưởng), không nằm trong repo dự án.
- **FR-016**: Phim mới của kênh dùng nhân vật có trong kho MUST coi nhân vật đó là đã duyệt, và MUST dựng nhân vật bằng đúng thông số và phiên bản rig trong kho.
- **FR-017**: Đổi một nhân vật có trong kho MUST tạo bản mới của nhân vật, không sửa bản đã duyệt.
- **FR-018**: App MUST có trang Cast library liệt kê nhân vật theo kênh, với bảng mẫu, ngày duyệt, phiên bản rig và các phim đã dùng.

**Phiên bản rig**
- **FR-019**: Rig nhân vật dùng chung MUST có số phiên bản; mọi thay đổi làm đổi hình MUST tăng phiên bản.
- **FR-020**: Nhân vật đã duyệt MUST luôn được dựng bằng phiên bản rig lúc duyệt cho tới khi người dùng chọn cập nhật.
- **FR-021**: Khi có phiên bản rig mới, Cast library MUST báo cho từng nhân vật đang dùng bản cũ, MUST cho xem trước bảng mẫu bản mới cạnh bản đã duyệt, và MUST cho người dùng chọn cập nhật từng nhân vật; nhân vật được cập nhật về chưa duyệt.


**Giao diện**
- **FR-025**: Trang việc MUST theo bản mẫu đã duyệt: thanh bước có nhãn REVIEW cho điểm duyệt, khung duyệt của bước đang chọn, cột "How it works" và "If you change this".

### Key Entities

- **Nhân vật (Character)**: một vai trong phim hoặc trong kho của kênh. Có tên, vai (chính, phụ, nền), loại (một người hoặc nhóm), thông số hình (màu áo, chân, giày, kiểu tóc hoặc mũ, tỉ lệ), phiên bản rig, trạng thái duyệt, bản (version) của chính nhân vật.
- **Bảng mẫu (Cast sheet)**: tập hình của một nhân vật ở một phiên bản: các góc, biểu cảm, tư thế, clip đi bộ, bảng màu. Giữ đúng một bản trước để so.
- **Ghi chú nhân vật (Cast note)**: thuộc một nhân vật; có thể gắn với một hình và một điểm (phần trăm), hoặc chung; có loại "yêu cầu vẽ góc"; trạng thái mở hoặc đã trả lời; câu trả lời của Claude; lượt sửa.
- **Kho nhân vật của kênh (Cast library)**: các nhân vật đã duyệt của một kênh, kèm ngày duyệt, phim đã dùng.
- **Phiên bản rig (Rig version)**: số phiên bản của rig nhân vật dùng chung và ghi chú thay đổi.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Với phim có 3 nhân vật, mọi bảng mẫu sẵn sàng để duyệt trong ≤ 5 phút sau khi kịch bản được duyệt (AE đã mở trên máy).
- **SC-002**: 100% lệnh làm giọng bị từ chối khi còn nhân vật chưa duyệt (điểm Cast bật), có test tự động.
- **SC-003**: Một lượt "Send notes to Claude" chỉ dựng lại bảng mẫu của các nhân vật có ghi chú: bảng mẫu của nhân vật khác giống hệt trước (so từng điểm ảnh), và 100% ghi chú có câu trả lời.
- **SC-004**: Ghim ghi chú được đặt lệch ≤ 2% chiều rộng hình so với điểm bấm, ở cả màn hình máy tính và điện thoại (≈ 400 px).
- **SC-005**: Phim thứ hai của cùng kênh dùng lại nhân vật chính đã duyệt không có lượt duyệt nào cho nhân vật đó, và nhân vật dựng ra giống hệt bảng mẫu đã duyệt (so từng điểm ảnh ở cùng góc và tư thế).
- **SC-006**: Sau khi rig lên phiên bản mới, dựng lại shot của phim cũ cho hình giống hệt trước (so từng điểm ảnh) cho mọi nhân vật chưa cập nhật.

## Assumptions

- Chỉ áp dụng cho phim After Effects; phim web giữ quy trình hiện tại.
- Danh sách nhân vật của phim do Claude rút từ kịch bản khi lập kế hoạch phim; người dùng sửa danh sách qua ghi chú ở bước Cast.
- Rig nhân vật của phim thử (đầu cầu, hoodie, tay chân ống mềm) được chuyển vào bộ dựng AE dùng chung và là phiên bản rig đầu tiên.
- Bảng mẫu được dựng qua cùng đường dựng AE của xưởng (trên máy hoặc qua cầu nối của app desktop).
- Kho nhân vật nằm theo kênh trong kho dữ liệu của app desktop, không vào git. Làm phim bằng chat khi app đang chạy thì đọc và ghi vào kho này (như sổ việc, specs/014); khi app không chạy thì bước Cast vẫn duyệt được trong phim nhưng không lưu và không dùng lại được nhân vật từ kho. Phim không thuộc kênh nào dùng kho của kênh mặc định.
- Điểm Sound, Final render và Publish giữ như specs/026 và specs/032.
- Một người dùng (chủ xưởng) duyệt; không có phân quyền duyệt riêng ở bản này.
