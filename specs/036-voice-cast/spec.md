# Feature Specification: Giọng theo nhân vật và giọng ElevenLabs

**Feature Branch**: `036-voice-cast`

**Created**: 2026-11-25

**Status**: Draft

**Input**: User description: "036-voice-cast: Giọng theo nhân vật và nhà cung cấp giọng ElevenLabs. (1) Chủ xưởng gắn khoá API ElevenLabs ở Settings của app (lưu mã hoá, không hiện lại đầy đủ, nút Test báo số ký tự còn lại); xưởng lấy danh sách giọng của tài khoản (kể cả giọng nhân bản) có câu nghe thử, hiện chung với giọng Kokoro, ghi rõ nhà cung cấp; đọc bằng API có thời điểm từng ký tự; báo trước số ký tự sẽ tốn khi đọc cả phim; Kokoro là giọng miễn phí và dự phòng khi hết lượt hoặc mất mạng; không sửa lib/. (2) Giọng theo nhân vật: mỗi câu trong lines.json có trường speaker (vắng = người kể chuyện); người kể chuyện là giọng cố định của kênh; nhân vật lặp lại có giọng riêng lưu trong kho nhân vật của kênh (Cast library, specs/034), được chọn ở bước Cast: Claude đề xuất 2–3 giọng theo tuổi/giới/tính cách, mỗi giọng đọc thử một câu thật của nhân vật, người dùng duyệt giọng cùng lúc với hình; vai phụ một câu lấy từ bộ giọng theo vai của kênh (bé trai, bé gái, phụ nữ, đàn ông, người già); hai người nói trong cùng cảnh không trùng giọng và không trùng người kể. Mỗi câu có thể có cảm xúc (thì thầm, hét) và hiệu ứng (điện thoại, sau tường, loa đài). Bước Voice chỉ còn sửa từng câu, đổi giọng cho cả phim theo nhân vật. Bằng chứng từ video mẫu (IFNation, 569 s, 186 câu) … Phụ thuộc specs/034 (Cast library)."

## Bối cảnh

- Hiện xưởng chỉ có giọng Kokoro (miễn phí, chạy trên máy). Bộ đọc của thư viện đã cho mỗi câu một giọng, nhưng xưởng gán **một giọng cho cả phim**: kịch bản không ghi câu nào ai nói, kho nhân vật (specs/034) chỉ lưu hình. Phim thử `ae-sleepless-test`: mọi câu đều `am_michael`.
- Trang Voice của bản mẫu 034 còn lệch: dòng tóm tắt ghi một giọng, ô chọn hiện giọng khác.
- Đo video mẫu cùng thể loại "What If" (2026-11-25, chép lời và đo cao độ, dấu vân giọng từng câu):
  - Người kể chuyện (nam trưởng thành, ~120–150 Hz) đọc khoảng 90% lời, kể nhân vật chính ở ngôi "you".
  - Khoảng 20 câu thoại ngắn (≤ 2 s) do giọng khác đọc: tổng thống (giọng nam riêng, 3 câu gom sát nhau), mẹ, bạn nữ, cô hiệu trưởng (giọng nữ ~200–275 Hz), nhân vật chính và bạn thân khi nói thành lời (giọng trẻ con).
  - Câu mẹ nói điện thoại "qua tường" lệch xa nhất so với người kể: có thể có lọc âm (chưa xác nhận bằng tai).
  - Kết luận: thoại ít nhưng mang cảm xúc chính; người kể chiếm phần lớn thời lượng và chi phí đọc.
- Đo kỹ bằng hai mô hình nhận diện người nói (chạy trên máy): mô hình đo **danh tính** thấy cả bài là 1 người (câu tổng thống giống người kể 0,96); mô hình nhạy **chất giọng** tách 16/16 câu thoại khỏi người kể, thành 4 cụm: người kể, giọng trẻ con của nhân vật chính, giọng nữ (mẹ và bạn nữ chung cụm), tổng thống. Cách hiểu hợp lý: khoảng 4 giọng nghe khác nhau nhưng chỉ 1–2 người đọc thật; người kể **đóng nhiều vai** bằng cách đổi cao độ, tốc độ, cảm xúc.

## Clarifications

### Session 2026-11-25

- Q: Các mặc định (một khoá cho mỗi chủ xưởng, không tự đổi nhà cung cấp cho một phần phim, bộ giọng theo vai mặc định Kokoro, xác nhận quyền khi dùng giọng nhân bản, phim page chọn giọng ở Voice) có giữ không? → A: Giữ cả 5.
- Q: Nhân vật nhất thiết phải có giọng khác hẳn người kể? → A: Không. Mỗi nhân vật chọn **giọng riêng** hoặc **người kể đóng vai** (giọng người kể kèm chỉnh cao độ, tốc độ, cảm xúc). Vai phụ một câu mặc định là người kể đóng vai.
- Q: Khoá ElevenLabs khi chạy bằng lệnh (không có app) nằm đâu? → A: Trong tệp `.env` ở gốc dự án (git bỏ qua) hoặc biến môi trường; người dùng đã thêm `ELEVENLABS_API_KEY` vào `.env`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gắn khoá ElevenLabs và chọn giọng ElevenLabs (Priority: P1)

Chủ xưởng mở Settings của app, dán khoá API ElevenLabs, bấm **Test**. App báo khoá hợp lệ, tên gói và số ký tự còn lại trong kỳ. Khoá được lưu kín: lần sau chỉ hiện 4 ký tự cuối, có nút thay và xoá. Từ đó mọi ô chọn giọng của xưởng hiện cả giọng Kokoro và giọng của tài khoản ElevenLabs (kể cả giọng nhân bản, giọng thêm từ thư viện của tài khoản), mỗi giọng ghi nhà cung cấp, mô tả ngắn và nút nghe thử. Chọn một giọng ElevenLabs cho phim rồi làm giọng: xưởng báo trước số ký tự sẽ tốn và số còn lại, người dùng xác nhận, xưởng đọc, mỗi câu có thời điểm từng chữ để khớp lời.

**Why this priority**: Người dùng yêu cầu trực tiếp; một mình story này đã nâng chất lượng giọng cho mọi phim, kể cả phim chỉ có người kể.

**Independent Test**: Gắn một khoá thật, bấm Test (thấy số ký tự còn lại); chọn một giọng ElevenLabs cho `ae-sleepless-test`, làm giọng: hộp xác nhận báo đúng số ký tự (sai lệch ≤ 1% so với số ký tự của kịch bản), các câu đọc ra bằng giọng đã chọn, có thời điểm từng chữ, qua kiểm lời. Gắn khoá sai: Test báo lỗi rõ, khoá không được lưu.

**Acceptance Scenarios**:

1. **Given** chưa có khoá, **When** chủ xưởng dán khoá đúng và bấm Test, **Then** app báo hợp lệ, gói, số ký tự còn lại, và lưu khoá.
2. **Given** khoá sai hoặc hết hạn, **When** bấm Test hoặc làm giọng, **Then** app báo "khoá không hợp lệ" kèm cách sửa, không lưu khoá sai, không đọc câu nào.
3. **Given** khoá đã lưu, **When** mở lại Settings, **Then** chỉ thấy 4 ký tự cuối; khoá không xuất hiện trong nhật ký, trang việc, tệp phim hay repo.
4. **Given** đã có khoá, **When** mở ô chọn giọng, **Then** thấy giọng Kokoro và giọng ElevenLabs của tài khoản, ghi nhà cung cấp, nghe thử được từng giọng.
5. **Given** phim dùng giọng ElevenLabs, **When** làm giọng cả phim, **Then** xưởng báo số ký tự sẽ tốn và còn lại, chỉ đọc khi người dùng xác nhận; làm lại một câu thì không hỏi lại nhưng vẫn cộng vào số đã dùng.
6. **Given** số ký tự còn lại ít hơn số cần, **When** làm giọng, **Then** xưởng không đọc dở dang mà báo thiếu bao nhiêu và đề xuất dùng Kokoro cho phim này.

---

### User Story 2 - Mỗi câu có người nói, mỗi nhân vật có giọng (Priority: P2)

Khi viết kịch bản, Claude ghi người nói cho từng câu: câu kể để trống (người kể chuyện), câu thoại ghi tên nhân vật. Mỗi kênh có **giọng người kể** cố định. Ở bước Cast (specs/034), mỗi nhân vật có lời thoại có thêm phần **Giọng**: Claude đề xuất 2–3 giọng hợp tuổi, giới và tính cách, mỗi giọng đọc thử một câu thật của nhân vật trong kịch bản. Người dùng nghe, chọn một giọng (có thể chọn giọng khác ngoài đề xuất), rồi duyệt nhân vật như thường. Giọng đã duyệt lưu vào kho nhân vật cùng hình; phim sau dùng lại nhân vật thì dùng luôn giọng đó, không phải chọn lại. Khi làm giọng, mỗi câu được đọc bằng giọng của người nói.

Mỗi nhân vật có hai cách mang giọng: **giọng riêng** (một giọng khác người kể) hoặc **người kể đóng vai** (giọng người kể của kênh kèm chỉnh cao độ, tốc độ và cảm xúc, ví dụ "trẻ con: cao +4, nhanh 1,1×, tinh nghịch"). Claude đề xuất cách nào hợp; đề xuất 2–3 lựa chọn có thể trộn cả hai cách.

**Why this priority**: Đây là câu hỏi cốt lõi của người dùng ("nhiều nhân vật thì chọn giọng thế nào") và là cách video mẫu kể chuyện; cần US1 hoặc Kokoro để có giọng, cần 034 để có kho nhân vật.

**Independent Test**: Phim AE thử có người kể và 3 nhân vật có thoại (nhân vật chính trẻ con, mẹ, bạn thân). Ở Cast, mỗi nhân vật có 2–3 giọng đề xuất, mỗi giọng có câu đọc thử là câu thật của nhân vật. Duyệt cast → làm giọng: câu kể bằng giọng người kể của kênh, câu thoại bằng đúng giọng của nhân vật. Làm phim thứ hai dùng lại mẹ: không phải chọn giọng mẹ lần nữa.

**Acceptance Scenarios**:

1. **Given** kịch bản đã duyệt có câu thoại, **When** mở Cast, **Then** mỗi nhân vật có lời thoại có phần Giọng với 2–3 đề xuất, mỗi đề xuất kèm lý do ngắn (ví dụ "bé trai ~10 tuổi, nhanh, tinh nghịch") và câu đọc thử lấy từ kịch bản.
2. **Given** nhân vật có thoại chưa chọn giọng, **When** duyệt nhân vật đó hoặc "Approve cast", **Then** bị từ chối kèm tên nhân vật thiếu giọng.
3. **Given** nhân vật đã duyệt có giọng trong kho, **When** phim mới dùng nhân vật đó, **Then** giọng được dùng lại, không hỏi lại.
4. **Given** kênh chưa có giọng người kể, **When** làm giọng phim đầu tiên của kênh, **Then** xưởng yêu cầu chọn giọng người kể (có đề xuất), và lưu làm giọng người kể của kênh.
5. **Given** câu không ghi người nói, **When** làm giọng, **Then** câu đó đọc bằng giọng người kể.
6. **Given** nhân vật được chọn "người kể đóng vai" với cao độ +4, **When** làm giọng, **Then** câu của nhân vật đọc bằng giọng người kể đã chỉnh, nghe cao hơn rõ rệt (cao độ trung vị cao hơn câu kể ≥ 20%) và vẫn qua kiểm lời.
7. **Given** nhân vật chính được kể ở ngôi "you", **When** nhân vật chính nói thành lời trong ngoặc kép, **Then** câu đó đọc bằng giọng của nhân vật chính, không bằng giọng người kể.

---

### User Story 3 - Vai phụ một câu và luật không trùng giọng (Priority: P3)

Nhân vật chỉ nói 1–2 câu trong phim và không có trong kho (người bán hàng, tổng thống, người lạ) không cần duyệt giọng riêng. **Mặc định vai phụ là người kể đóng vai**, chỉnh theo vai (ví dụ đàn ông: trầm −2, chậm 0,95×). Kênh có thể chuyển sang **bộ giọng theo vai**: bé trai, bé gái, phụ nữ, đàn ông, người già nam, người già nữ, mỗi vai vài giọng. Claude gán vai cho vai phụ khi viết kịch bản, xưởng tự lấy giọng từ bộ đó. Luật: trong một cảnh, mọi người nói có giọng khác nhau và khác giọng người kể; một vai phụ giữ một giọng suốt phim. Người dùng xem và đổi được giọng vai phụ ở bước Voice.

**Why this priority**: Video mẫu có nhiều vai phụ một câu; không có story này thì hoặc phải duyệt rất nhiều giọng, hoặc vai phụ trùng giọng người kể.

**Independent Test**: Kịch bản có 3 vai phụ một câu cùng một cảnh và một vai phụ nói 2 câu ở hai cảnh. Làm giọng: 3 vai phụ cùng cảnh có 3 giọng khác nhau, không giọng nào là giọng người kể; vai phụ nói 2 câu dùng cùng một giọng. Kiểm tự động báo lỗi nếu ép hai vai cùng cảnh trùng giọng.

**Acceptance Scenarios**:

1. **Given** kênh chưa có bộ giọng theo vai, **When** làm giọng phim có vai phụ, **Then** xưởng dùng bộ mặc định (giọng Kokoro, hoặc ElevenLabs nếu đã gắn khoá) và cho chủ xưởng sửa bộ đó trong hồ sơ kênh.
2. **Given** hai người nói cùng cảnh bị gán cùng một giọng, **When** chạy kiểm giọng, **Then** kiểm báo lỗi kèm tên hai người nói và cảnh.
3. **Given** vai phụ đã được gán giọng, **When** người dùng đổi giọng vai đó ở bước Voice, **Then** mọi câu của vai đó được đọc lại bằng giọng mới, các câu khác giữ nguyên.

---

### User Story 4 - Cảm xúc và hiệu ứng theo câu (Priority: P4)

Mỗi câu có thể có **cảm xúc** (bình thường, thì thầm, hét, cười, khóc, mỉa mai) và **hiệu ứng âm** (điện thoại, sau tường, loa đài, vang phòng lớn). Claude đề xuất khi viết kịch bản; người dùng đổi ở bước Voice. Cảm xúc được chuyển cho nhà cung cấp giọng khi nhà cung cấp hỗ trợ; hiệu ứng âm được xưởng áp sau khi đọc, với mọi nhà cung cấp.

**Why this priority**: Làm câu thoại có hồn như video mẫu (câu mẹ qua tường), nhưng phim vẫn dùng được khi thiếu.

**Independent Test**: Một câu gắn "sau tường", một câu gắn "thì thầm". Nghe: câu "sau tường" bị lọc trầm và nhỏ đi rõ rệt; câu "thì thầm" (ElevenLabs) nhỏ, hơi thở rõ. Với Kokoro, cảm xúc không hỗ trợ thì trang Voice ghi "không áp dụng với giọng này", hiệu ứng vẫn áp.

**Acceptance Scenarios**:

1. **Given** câu có hiệu ứng "điện thoại", **When** làm giọng, **Then** âm câu đó bị giới hạn dải tần như điện thoại; kiểm lời vẫn đọc ra đúng chữ.
2. **Given** câu có cảm xúc mà giọng đang dùng không hỗ trợ, **When** xem câu ở bước Voice, **Then** trang ghi rõ cảm xúc không được áp, không âm thầm bỏ qua.

---

### Edge Cases

- **Mất mạng hoặc ElevenLabs lỗi giữa chừng**: các câu đã đọc được giữ; câu lỗi được đánh dấu, làm lại được; xưởng không tự đổi sang Kokoro cho riêng vài câu (một nhân vật không bao giờ có hai giọng trong một phim). Người dùng có thể chọn "dùng Kokoro cho cả phim".
- **Giọng ElevenLabs bị xoá khỏi tài khoản** sau khi nhân vật đã duyệt: kho nhân vật báo "giọng không còn", phim dùng nhân vật đó bị chặn ở bước làm giọng cho tới khi chọn giọng mới (giọng mới phải duyệt lại); âm thanh đã đọc của phim cũ giữ nguyên.
- **Đổi hoặc xoá khoá API**: giọng ElevenLabs vẫn ghi trong kho nhưng không đọc được; báo rõ cần khoá. Xoá khoá không xoá giọng đã duyệt.
- **Giọng nhân bản**: hiện với nhãn "Cloned". Xưởng không tự nhân bản giọng; khi chọn giọng nhân bản cho nhân vật lần đầu, xưởng nhắc người dùng xác nhận mình có quyền dùng giọng đó (hiến pháp: giọng đọc phải là của mình).
- **Kênh khác dùng giọng người kể trùng**: được phép (mỗi kênh độc lập), không cảnh báo.
- **Nhân vật đổi giọng sau khi Voice đã duyệt**: chỉ các câu của nhân vật đó phải đọc lại; Animatic/Shots, Sound, Final render chuyển "Must run again".
- **Câu thoại rất ngắn (1 chữ, ví dụ "No.")**: vẫn đọc bằng giọng nhân vật; kiểm lời không báo sai chỉ vì câu quá ngắn.
- **Chế độ Client (specs/018)**: Client dùng khoá của Host; khoá không bao giờ được gửi sang máy Client.
- **Phim page (không phải AE)**: không có bước Cast; giọng nhân vật được chọn ngay ở bước Voice, cùng luật và cùng kho.

## Requirements *(mandatory)*

### Functional Requirements

**Nhà cung cấp giọng ElevenLabs**

- **FR-001**: Chủ xưởng MUST gắn, thử, thay và xoá được một khoá API ElevenLabs trong Settings của app. Thử khoá MUST báo hợp lệ hay không, tên gói và số ký tự còn lại.
- **FR-002**: Khoá MUST được lưu mã hoá trong kho dữ liệu của chủ xưởng, chỉ hiện 4 ký tự cuối, và MUST NOT xuất hiện trong nhật ký, trang việc, tệp phim, thông báo lỗi, repo hay máy Client.
- **FR-003**: Khi có khoá hợp lệ, mọi ô chọn giọng MUST liệt kê giọng của tài khoản ElevenLabs cùng giọng Kokoro; mỗi giọng có nhà cung cấp, tên, mô tả (giới, tuổi, chất giọng nếu có), nhãn "Cloned" nếu là giọng nhân bản, và nghe thử được.
- **FR-004**: Đọc bằng ElevenLabs MUST trả thời điểm từng chữ của mỗi câu để khớp lời với hình và để kiểm lời.
- **FR-005**: Trước khi đọc nhiều hơn một câu bằng ElevenLabs, xưởng MUST báo số ký tự sẽ tốn và số còn lại, và chỉ đọc khi người dùng xác nhận. Nếu không đủ, MUST NOT đọc dở dang.
- **FR-006**: Kokoro MUST vẫn là lựa chọn miễn phí, dùng được khi không có khoá. Xưởng MUST NOT tự đổi nhà cung cấp cho một phần phim; đổi sang Kokoro chỉ áp cho cả phim và do người dùng chọn.
- **FR-007**: Tính năng MUST NOT sửa tệp nào trong `lib/` (hiến pháp VI).
- **FR-008**: App MUST ghi số ký tự ElevenLabs đã dùng theo từng phim, xem được trên trang phim.

**Người nói và giọng nhân vật**

- **FR-010**: Mỗi câu trong kịch bản MUST có thể ghi người nói; câu không ghi là của người kể chuyện. Claude MUST ghi người nói cho mọi câu thoại khi viết kịch bản.
- **FR-011**: Mỗi kênh MUST có một giọng người kể cố định; phim đầu tiên của kênh chưa có giọng người kể thì xưởng MUST yêu cầu chọn trước khi làm giọng.
- **FR-012**: Ở bước Cast (phim AE) hoặc bước Voice (phim page), mỗi nhân vật có thoại và chưa có giọng trong kho MUST có 2–3 giọng đề xuất, mỗi giọng có lý do ngắn và câu đọc thử là một câu thật của nhân vật trong kịch bản.
- **FR-013**: Nhân vật có thoại MUST NOT được duyệt khi chưa chọn giọng. Giọng đã duyệt MUST lưu trong kho nhân vật của kênh cùng hình, gồm nhà cung cấp, mã giọng, tốc độ và thông số giọng.
- **FR-014**: Phim dùng lại nhân vật đã duyệt MUST dùng giọng đã lưu mà không hỏi lại.
- **FR-015**: Khi làm giọng, mỗi câu MUST được đọc bằng giọng của người nói của câu đó.
- **FR-016**: Giọng của nhân vật MUST là một trong hai cách: giọng riêng, hoặc người kể đóng vai (giọng người kể của kênh + chỉnh cao độ, tốc độ, cảm xúc). Người kể đóng vai MUST đi theo giọng người kể: kênh đổi giọng người kể thì các nhân vật đóng vai đổi theo và chờ duyệt lại.

**Vai phụ và luật không trùng**

- **FR-020**: Mỗi kênh MUST có một bộ giọng theo vai (ít nhất: bé trai, bé gái, phụ nữ, đàn ông, người già nam, người già nữ); mỗi vai là người kể đóng vai (mặc định, có sẵn mức chỉnh theo vai) hoặc một danh sách giọng riêng; sửa được trong hồ sơ kênh.
- **FR-021**: Vai phụ không có trong kho MUST được gán vai và lấy giọng từ bộ giọng theo vai; một vai phụ MUST giữ một giọng suốt phim.
- **FR-022**: Kiểm giọng MUST báo lỗi khi hai người nói trong cùng một cảnh có cùng **thiết lập giọng** (cùng giọng và cùng mức chỉnh), hoặc một nhân vật hay vai phụ có thiết lập giọng trùng người kể không chỉnh gì. Người kể đóng vai với mức chỉnh khác nhau được coi là khác giọng.

**Cảm xúc và hiệu ứng**

- **FR-030**: Mỗi câu MUST có thể có một cảm xúc (bình thường, thì thầm, hét, cười, khóc, mỉa mai) và một hiệu ứng âm (không, điện thoại, sau tường, loa đài, phòng lớn).
- **FR-031**: Cảm xúc MUST được chuyển cho nhà cung cấp khi nhà cung cấp hỗ trợ; khi không hỗ trợ, bước Voice MUST ghi rõ là không áp.
- **FR-032**: Hiệu ứng âm MUST áp được với mọi nhà cung cấp, và câu có hiệu ứng vẫn MUST qua kiểm lời.

**Bước Voice**

- **FR-040**: Trang Voice MUST nhóm câu theo người nói, hiện giọng của từng người nói, và cho: nghe từng câu, "Say as", làm lại một câu, đổi cảm xúc hoặc hiệu ứng của một câu, đổi giọng vai phụ. Đổi giọng nhân vật đã duyệt MUST đưa nhân vật về trạng thái chờ duyệt ở kho.
- **FR-041**: Tóm tắt trang phim và ô chọn giọng MUST hiện cùng một giọng người kể (sửa chỗ lệch của bản mẫu 034).
- **FR-042**: Đổi giọng của một người nói MUST chỉ đọc lại các câu của người đó, và đánh dấu "Must run again" cho các bước sau giọng.

### Key Entities

- **Khoá nhà cung cấp giọng**: thuộc chủ xưởng; nhà cung cấp, khoá đã mã hoá, 4 ký tự cuối, lần thử gần nhất, gói, số ký tự còn lại.
- **Giọng**: nhà cung cấp, mã giọng, tên, mô tả (giới, tuổi, chất giọng), nhân bản hay không, câu nghe thử, các cảm xúc hỗ trợ.
- **Thiết lập giọng**: cách (giọng riêng / người kể đóng vai) + một giọng (với đóng vai: giọng người kể của kênh) + cao độ + tốc độ + cảm xúc mặc định + thông số của nhà cung cấp; gắn vào người kể của kênh, nhân vật trong kho, hoặc một vai trong bộ giọng theo vai.
- **Câu** (mở rộng): thêm người nói, vai (cho vai phụ), cảm xúc, hiệu ứng, thời điểm từng chữ, số ký tự đã tốn.
- **Nhân vật trong kho** (mở rộng 034): thêm thiết lập giọng đã duyệt.
- **Bộ giọng theo vai**: thuộc kênh; mỗi vai một danh sách thiết lập giọng.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Gắn khoá và thử khoá xong trong dưới 1 phút; 100% lần thử khoá sai báo lỗi và không lưu khoá.
- **SC-002**: Quét toàn bộ nhật ký, tệp phim, trang việc và repo sau một lượt làm phim bằng ElevenLabs: 0 lần xuất hiện khoá (có test tự động).
- **SC-003**: Số ký tự báo trước lệch ≤ 1% so với số ElevenLabs thực tính cho lượt đọc đó.
- **SC-004**: Ở phim thử có người kể và ≥ 3 nhân vật có thoại, 100% câu được đọc bằng đúng giọng của người nói (kiểm tự động theo bảng người nói ↔ giọng).
- **SC-005**: Phim thứ hai dùng lại nhân vật đã duyệt: 0 lần phải chọn lại giọng cho nhân vật đó.
- **SC-006**: 100% trường hợp hai người nói cùng cảnh trùng giọng, hoặc nhân vật trùng giọng người kể, bị kiểm giọng bắt (có test tự động).
- **SC-007**: Người dùng nghe phim thử và phân biệt được người kể với từng nhân vật có thoại mà không cần nhìn hình (người dùng xác nhận khi duyệt).
- **SC-008**: Phim không có khoá ElevenLabs vẫn làm trọn với Kokoro như trước; các bộ test hiện có vẫn qua.

## Assumptions

- Phụ thuộc specs/034: bước Cast và kho nhân vật của kênh (chỉ trong kho dữ liệu của app). 036 làm sau 034; nếu 034 chưa xong thì phần giọng ở Cast chưa chạy được, US1 vẫn làm trước được.
- Một khoá ElevenLabs cho mỗi chủ xưởng (không theo kênh). Client (specs/018) dùng khoá của Host.
- Chế độ chạy bằng lệnh không có app: đọc khoá từ `.env` ở gốc dự án (git bỏ qua) hoặc biến môi trường; khoá không bao giờ được ghi ra tệp nào khác.
- Bộ giọng theo vai mặc định là người kể đóng vai (không tốn thêm giọng); giọng riêng cho vai là Kokoro khi không có khoá, ElevenLabs khi có khoá (Claude đề xuất, chủ xưởng duyệt một lần cho kênh).
- Chỉnh cao độ của "người kể đóng vai" được xưởng áp sau khi đọc nên dùng được với mọi nhà cung cấp; tốc độ và cảm xúc chuyển cho nhà cung cấp khi được hỗ trợ.
- Đề xuất giọng của Claude dựa trên mô tả nhân vật (tuổi, giới, tính cách) và mô tả giọng của nhà cung cấp; dùng Opus như mọi lần gọi Claude của xưởng.
- Giấy phép dùng thương mại giọng ElevenLabs phụ thuộc gói của chủ xưởng; xưởng nhắc điều này trong Settings, không kiểm gói hộ.
- Kiểm lời (Whisper) vẫn chạy với mọi nhà cung cấp; với ElevenLabs, thời điểm từng chữ của nhà cung cấp được dùng để khớp hình.
- Ngoài phạm vi: tự nhân bản giọng, nhà cung cấp giọng khác (có thể thêm sau theo cùng mẫu), lồng tiếng nhiều ngôn ngữ, nhạc và hiệu ứng âm thanh nền.
