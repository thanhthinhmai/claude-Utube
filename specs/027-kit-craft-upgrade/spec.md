# Feature Specification: Nâng tay nghề bộ dựng 3D (diễn xuất, bối cảnh, ánh sáng, góc máy)

**Feature Branch**: `027-kit-craft-upgrade`

**Created**: 2026-11-19

**Status**: Draft

**Input**: User description: "Nâng cấp bộ dựng 3D của phong cách dusk-hypothetical cho gần tay nghề kênh mẫu hơn, gồm 5 phần: diễn xuất (đồ cầm tay, động tác cả người, động tác hai người), bối cảnh ngoài trời hoàng hôn ba lớp, ánh sáng và hậu kỳ (bản thử v2), góc máy (qua vai, cận tay, góc thấp), kiểm và chứng minh (qc plan đếm, bảng ảnh cạnh kênh mẫu, làm lại phút đầu của pause-ten-seconds). Không đổi sang SVG; không chép nhân vật chính, lời, tên, giọng của kênh mẫu."

## Bối cảnh

Ngày 2026-11-19 người dùng hỏi có nên chuyển kênh sang vẽ SVG. Đã chốt: **giữ 3D**, vì cái làm nên kênh mẫu là ánh sáng mềm, độ sâu, sương và máy đi trong không gian. Khoảng cách còn lại là **tay nghề**, không phải công nghệ.

Đo bảng cảnh của `films/pause-ten-seconds` (175 cảnh, phim 10 phút làm bằng bộ dựng 023) và đặt bảng ảnh cạnh bảng ảnh kênh mẫu:

| Mảng | Kênh mẫu | pause-ten-seconds |
|---|---|---|
| Tư thế | nhân vật làm việc: chơi bài, ôm, chạy, giơ tay, bê đồ | 79% ngồi hoặc đứng (sit 73, stand 65 trên 175) |
| Động tác trong cảnh | hành động có đồ vật hoặc có người kia | gần như chỉ cử chỉ: nhìn, gật, nghiêng đầu, chồm tới |
| Đồ trong tay | thường có (bài, tiền, bóng, hộp) | 30/175 cảnh có tư thế cầm đồ, chỉ 6 loại đồ |
| Góc qua vai | tới 24% số cảnh (`shots.json`) | 1/175 |
| Độ sáng bảng ảnh | trung bình 59–71 ở 6/7 video | 53–55 |
| Bối cảnh | phố hoàng hôn có cửa sổ sáng, trời chuyển màu, đồ dày ba lớp | tường tím tối, nền xa tối đặc |
| Hậu kỳ | bóng mềm ở chỗ khuất, sương sáng ấm | mờ hậu cảnh và loé sáng có; bóng mềm tắt; sương tối |

Bản thử hậu kỳ v2 (`films/kit-post`, bật bằng `?post=v2`) làm 6 cảnh sáng hơn từ 70 lên 89, mặt bớt ám tím, hành lang có sương ấm. Nhưng khi đặt cạnh kênh mẫu, phần lớn khoảng cách vẫn nằm ở **cái diễn ra trong khung**: ai đang làm gì, với đồ gì, ở đâu.

Bài học cũ vẫn giữ (specs/023): mỗi phần mới phải chứng minh bằng bảng ảnh đặt cạnh ô kênh mẫu cùng loại cảnh và bằng clip ngắn, không bằng một ảnh tĩnh.

## Clarifications

### Session 2026-11-19

- Q: Các mức tối thiểu cho tỉ lệ cảnh có hành động, ngoài trời, đồ trong tay, qua vai lấy từ đâu? → A: Gán nhãn lại toàn bộ 2.192 cảnh của bộ mẫu (thêm nhãn có hành động, ngoài trời, đồ trong tay) và lấy khoảng từ số đo; mức 50% cảnh có hành động chỉ dùng tạm cho tới khi đo xong.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Nhân vật làm việc trong cảnh (Priority: P1)

Người làm phim (Claude theo luồng làm phim) viết bảng cảnh với nhân vật **làm một việc cụ thể**: cầm và dùng đồ vật (bóng, bài, tiền, hộp, chìa khoá, điện thoại, cốc…), động tác cả người (chạy, nhảy, ném, bê, ngã, đẩy, gõ phím), động tác giữa hai người (đưa đồ cho nhau, đập tay). Cảnh hai người nói chuyện mặc định quay qua vai; có cảnh cận tay cầm đồ; khoảnh khắc thắng dùng góc thấp.

**Why this priority**: Đây là khoảng cách lớn nhất còn lại so với kênh mẫu, và hậu kỳ hay bối cảnh không bù được.

**Independent Test**: Dựng một trang thử chỉ dùng bối cảnh sẵn có, gồm mỗi động tác mới một cảnh. Xuất bảng ảnh và clip, đặt cạnh ô kênh mẫu cùng loại (cầm đồ, hai người, qua vai), rồi người dùng duyệt.

**Acceptance Scenarios**:

1. **Given** bảng cảnh có `act` là một động tác mới với một đồ vật, **When** dựng cảnh, **Then** đồ nằm trong tay suốt động tác (không trôi, không xuyên thân), và động tác đọc được trong ≤ 1,5 s.
2. **Given** một cảnh hai người có `talk`, không ghi máy, **When** lập kế hoạch, **Then** máy mặc định là qua vai và các cảnh liền nhau đổi phía đúng luật 180°.
3. **Given** một động tác hai người (đưa đồ), **When** dựng, **Then** đồ rời tay người này và tới tay người kia ở cùng một khung, không có khung nào đồ ở hai nơi.
4. **Given** một bảng cảnh mà dưới tỉ lệ cảnh có hành động tối thiểu, **When** chạy `qc plan`, **Then** tầng 1 báo lỗi, kèm số đo, giới hạn và danh sách cảnh có thể thêm hành động.

---

### User Story 2 - Bối cảnh ngoài trời hoàng hôn, dày đồ ba lớp (Priority: P2)

Bộ dựng có thêm các bối cảnh ngoài trời lúc hoàng hôn: phố có nhà cửa sổ sáng đèn, sân bóng rổ, sân thượng, bãi xe. Mỗi bối cảnh có tiền cảnh, trung cảnh, hậu cảnh, với cây, cột đèn, xe, hàng rào và trời chuyển màu. Các bối cảnh trong nhà sẵn có được thêm đồ cho đủ mật độ.

**Why this priority**: Thay "tường tím tối" bằng nơi có không khí. Nó cần các động tác của P1 mới có ích, nên xếp sau.

**Independent Test**: Trang danh mục bối cảnh xuất mỗi bối cảnh một khung toàn và một khung trung có người. Đặt cạnh ô kênh mẫu có `place` cùng loại, rồi người dùng duyệt.

**Acceptance Scenarios**:

1. **Given** một bối cảnh ngoài trời mới, **When** quay toàn cảnh, **Then** khung có trời, có ít nhất 3 lớp độ sâu nhìn thấy, và có nguồn sáng tự phát (cửa sổ, đèn đường).
2. **Given** một bối cảnh bất kỳ trong danh mục, **When** đếm đồ vật trong khung toàn, **Then** đạt mật độ tối thiểu đã ghi trong danh mục.
3. **Given** bảng cảnh cả phim, **When** chạy `qc plan`, **Then** tầng 1 báo tỉ lệ cảnh ngoài trời và cảnh báo khi ra ngoài khoảng đo từ kênh mẫu.

---

### User Story 3 - Ánh sáng và hậu kỳ mới trong bộ dựng (Priority: P3)

Bản thử v2 trở thành mặc định của bộ dựng: trời chuyển màu, sương sáng ấm thay sương tối, bóng mềm ở chỗ khuất, mặt bớt ám tím, phơi sáng cao hơn, loé sáng nhẹ. Thêm cửa sổ tự phát sáng và vệt nắng qua cửa sổ cho bối cảnh trong nhà. Các con số mới được đo lại với kênh mẫu.

**Why this priority**: Đã có bản thử chạy được. Lợi thấy rõ nhưng nhỏ hơn P1 và P2.

**Independent Test**: Chụp cùng 6 cảnh với số cũ và số mới, đặt cạnh ô kênh mẫu. Chạy `learn compare` trên khung chứng minh và trên các cảnh thử.

**Acceptance Scenarios**:

1. **Given** số màu mới, **When** chạy `learn compare`, **Then** độ sáng trung vị và độ bão hoà trung vị nằm trong khoảng đo của phong cách.
2. **Given** một phim cũ đã có bản kit riêng, **When** dựng lại phim đó, **Then** hình không đổi (phim cũ giữ kit đã chép).
3. **Given** máy dựng bằng GPU, **When** dựng một phút phim, **Then** thời gian dựng tăng không quá 50% so với số cũ.

---

### User Story 4 - Chạy thử: làm lại phút đầu của pause-ten-seconds (Priority: P4)

Làm lại phút đầu (0:00–1:00) của `films/pause-ten-seconds` bằng bộ dựng mới, với cùng lời, cùng giọng và cùng nhịp cắt, rồi so trước và sau. Chỉ khi người dùng duyệt mới dùng bộ dựng mới cho phim dài.

**Why this priority**: Là bằng chứng cuối, cần cả P1–P3.

**Independent Test**: Một bảng so 3 hàng (kênh mẫu, trước, sau) cho cùng các loại cảnh, hai clip 60 s trước và sau, và bảng số đo của các tầng kiểm.

**Acceptance Scenarios**:

1. **Given** phút đầu làm lại, **When** chạy đủ tầng 0–4, **Then** không có lỗi nặng, và mọi cảnh báo phong cách đều được ghi.
2. **Given** bảng so và hai clip, **When** người dùng xem, **Then** người dùng chọn dùng hoặc không dùng bộ dựng mới cho phim dài.

### Edge Cases

- Động tác cần đồ vật mà bảng cảnh không ghi đồ: kế hoạch dùng đồ mặc định của động tác đó và ghi cảnh báo, không bỏ trống tay.
- Hai người qua vai nhưng một người ở ngoài khung của bối cảnh: kế hoạch đổi sang cảnh trung có cả hai và ghi lý do.
- Bối cảnh `custom:` do phim tự dựng: mật độ đồ chỉ cảnh báo, không chặn.
- Cảnh cố ý trống (`void`, thẻ chữ, thẻ cuối): không tính vào tỉ lệ cảnh có hành động hay cảnh ngoài trời.
- Phim không phải phong cách dusk-hypothetical: các luật đếm mới chỉ chạy khi phong cách có số đo tương ứng trong `template.json`.
- Hậu kỳ mới làm WebGL phần mềm quá chậm: thay đổi không được phá cách xưởng xử lý khi không có GPU (dừng và hỏi người dùng).

## Requirements *(mandatory)*

### Functional Requirements

**Diễn xuất và đồ vật (US1)**
- **FR-001**: Bộ dựng PHẢI có ít nhất 8 đồ cầm tay (bóng, bài, tiền, hộp, chìa khoá, cùng các đồ đã có: điện thoại, sách, cốc, giấy, túi). Đồ gắn vào tay và theo tay suốt động tác.
- **FR-002**: Bộ dựng PHẢI có ít nhất 7 động tác cả người: chạy, nhảy, ném, bê, ngã, đẩy, gõ phím. Mỗi động tác có tư thế đầu và cuối, có thể lặp nếu là động tác kéo dài.
- **FR-003**: Bộ dựng PHẢI có ít nhất 2 động tác hai người: đưa đồ, đập tay. Đồ chuyển tay đúng một lần, ở một mốc thời gian.
- **FR-004**: Mỗi động tác và đồ vật mới PHẢI có tên trong danh mục của bộ dựng (`catalog.json`) và trong hợp đồng bảng cảnh. Bảng cảnh cũ vẫn chạy không cần sửa.

**Góc máy (US1)**
- **FR-005**: Cảnh có hai người nói chuyện mà không ghi máy PHẢI mặc định quay qua vai, đổi phía giữa hai cảnh liền nhau và giữ luật 180°.
- **FR-006**: Bộ dựng PHẢI có cảnh cận tay cầm đồ (tay và đồ chiếm phần chính của khung) và góc thấp cho khoảnh khắc thắng, đều là tên máy trong danh mục.

**Bối cảnh (US2)**
- **FR-007**: Bộ dựng PHẢI có thêm 4 bối cảnh ngoài trời lúc hoàng hôn: phố có cửa sổ sáng đèn, sân bóng rổ, sân thượng, bãi xe. Mỗi bối cảnh có trời, ba lớp độ sâu, nguồn sáng tự phát và chỗ đứng cho người (anchors).
- **FR-008**: Mỗi bối cảnh trong danh mục (cũ và mới) PHẢI ghi mật độ đồ vật tối thiểu cho khung toàn và đạt mức đó.
- **FR-009**: Các phần dựng dùng chung (cây, cột đèn, xe, hàng rào, nhà có cửa sổ) PHẢI dùng được trong bối cảnh `custom:` của từng phim.

**Ánh sáng và hậu kỳ (US3)**
- **FR-010**: Số mặc định của bộ dựng PHẢI gồm trời chuyển màu, sương sáng ấm, bóng mềm ở chỗ khuất, phơi sáng và độ bão hoà mới. Mỗi số ghi trong `GRADE.md` kèm số đo mà nó được kiểm.
- **FR-011**: Bối cảnh trong nhà PHẢI có thể có cửa sổ tự phát sáng và vệt nắng qua cửa sổ.
- **FR-012**: Số màu mới PHẢI qua `learn compare` (độ sáng và độ bão hoà trung vị trong khoảng của phong cách). Nếu số đo của phong cách mâu thuẫn với bảng ảnh kênh mẫu, PHẢI đo lại khoảng của phong cách và ghi bằng chứng vào `EVIDENCE.md` (hiến pháp VIII), không nới tay.
- **FR-013**: Phim cũ đã chép kit (`kit use`) PHẢI không đổi hình. Phim mới nhận kit mới; phim cũ chỉ đổi khi chạy `kit use --update`.

**Kiểm (US1, US2)**
- **FR-014**: Tỉ lệ tối thiểu hoặc khoảng của (a) cảnh có người có hành động thật, (b) cảnh ngoài trời, (c) cảnh có đồ trong tay, (d) cảnh qua vai PHẢI được đo trên **toàn bộ 2.192 cảnh** của bộ video mẫu (một lượt gán nhãn độc lập, cùng cách với specs/021, thêm ba nhãn: có hành động thật, ngoài trời, có đồ trong tay; qua vai lấy từ nhãn góc đã có) và ghi vào `template.json` kèm nguồn. Mức "≥ 50% cảnh có người có hành động" của người dùng là luật xưởng tạm, dùng cho tới khi có số đo, và được ghi nhãn "luật xưởng".
- **FR-015**: `qc plan` (tầng 1) PHẢI đếm (a)–(d) từ bảng cảnh. Thấp hơn mức tối thiểu của (a) là lỗi; (b)–(d) ra ngoài khoảng là cảnh báo phong cách. Mỗi lỗi kèm số đo, giới hạn và cảnh nên sửa.
- **FR-016**: Cử chỉ (nhìn, gật, nghiêng đầu, chồm tới, đổi mặt) PHẢI không được tính là hành động thật.

**Chứng minh (US1–US4)**
- **FR-017**: Mỗi nhóm thành phần mới (đồ và động tác, góc máy, bối cảnh, hậu kỳ) PHẢI có một bảng ảnh đặt cạnh ô kênh mẫu cùng loại cảnh và một clip ≤ 10 s, và được người dùng duyệt trước khi sang nhóm sau.
- **FR-018**: Phút đầu của `films/pause-ten-seconds` PHẢI được làm lại trong một thư mục phim mới (phim gốc giữ nguyên), với cùng lời, giọng và mốc cắt, và qua tầng 0–4.

**Ranh giới**
- **FR-019**: Đồ vật, bối cảnh và động tác PHẢI được tự dựng bằng code. Không chép nhân vật chính, lời, tên, giọng hay từng cảnh quay của kênh mẫu; không dùng hình hay mô hình bên thứ ba không có giấy phép ghi trong `CREDITS`.
- **FR-020**: Không sửa file trong `lib/`. Mọi thay đổi nằm trong `my-styles/dusk-hypothetical/kit/`, `tools/` và tài liệu của phong cách.

### Key Entities

- **Đồ cầm tay**: tên, tay cầm (trái, phải, hai tay), điểm bám, kích thước theo người.
- **Động tác**: tên, loại (cử chỉ, cả người, hai người), thời lượng, đồ mặc định, có tính là hành động thật không.
- **Bối cảnh**: tên, trong nhà hay ngoài trời, các lớp độ sâu, chỗ đứng, nguồn sáng, mật độ đồ tối thiểu.
- **Số đo tay nghề của phong cách**: tỉ lệ (a)–(d), khoảng, nguồn (bộ video, số cảnh, ngày đo).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Ở phút đầu làm lại, tỉ lệ cảnh có người có hành động thật ≥ mức tối thiểu của FR-014. Tham chiếu bản gốc của cùng phút để so, ghi cả hai số.
- **SC-002**: Ở phút đầu làm lại, tỉ lệ cảnh có đồ trong tay, cảnh qua vai và cảnh ngoài trời nằm trong khoảng đo của kênh mẫu (hoặc được người dùng chấp nhận có lý do).
- **SC-003**: Chuyển động trong cảnh (độ khác trung bình giữa các khung, không tính chỗ cắt) của phút làm lại cao hơn bản gốc, và không có cảnh nào bị `still_person`.
- **SC-004**: Độ sáng và độ bão hoà trung vị của phút làm lại nằm trong khoảng của phong cách. `learn compare` của khung chứng minh đạt.
- **SC-005**: Lượt gán nhãn độc lập của tầng 2 đồng ý với cỡ cảnh và góc máy của bảng cảnh ở ≥ 80% số cảnh.
- **SC-006**: Thời gian dựng bằng GPU của một phút phim tăng ≤ 50% so với bộ dựng cũ trên cùng máy.
- **SC-007**: 4/4 bảng so (đồ và động tác, góc máy, bối cảnh, hậu kỳ) và bảng so phút đầu được người dùng duyệt.
- **SC-008**: Dựng lại `films/pause-ten-seconds` và `films/hundred-words` bằng kit đã chép của chúng cho hình giống hệt trước (khác biệt khung = 0 ở 5 thời điểm).

## Assumptions

- Áp dụng cho phong cách `dusk-hypothetical` và bộ dựng của nó. Phong cách khác không đổi.
- Bộ máy dựng hình giữ nguyên (three.js theo thư viện, hiến pháp VII). Không thêm SVG vào phim 3D. Thumbnail vẽ 2D là việc riêng, ngoài spec này.
- Các tỉ lệ (a)–(d) đo bằng một lượt gán nhãn mới trên toàn bộ 2.192 cảnh của bộ `references/dusk-hypothetical-3` (khoảng 20 lượt gọi) (đã có ảnh từng cảnh), dùng mô hình Claude của xưởng (Opus 5.5) qua gói của chủ xưởng. Mẫu sơ bộ 40 cảnh cho thấy khoảng 25% cảnh ngoài trời, và pause-ten-seconds đã có khoảng 20%, nên khoảng cách ở bối cảnh nằm ở trời, ánh sáng và mật độ đồ nhiều hơn là ở tỉ lệ ngoài trời.
- Dựng bằng GPU. Nếu xưởng rơi về dựng phần mềm thì dừng và hỏi người dùng.
- Phút đầu làm lại dùng lại `lines.json`, giọng và `cues.json` của pause-ten-seconds; chỉ bảng cảnh và bộ dựng đổi.
- Bản thử `films/kit-post` chỉ là điểm bắt đầu cho số của US3; số cuối được chỉnh theo `learn compare`.
