# Feature Specification: Template từ cách làm của kênh mẫu

**Feature Branch**: `023-style-craft-template`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User description: "Học CÁCH LÀM của kênh tham chiếu (không chép tập phim) và viết thành template của xưởng, rồi làm lại bộ dựng 022 theo template. (…) Giữ phụ đề in trên hình. Không chép câu chuyện, câu thoại, nhân vật, giọng, nhạc, thumbnail hay từng cảnh quay của kênh mẫu."

## Bối cảnh

Ngày 2026-11-14, phim thử 1 phút `films/hundred-words` được dựng hoàn toàn bằng bộ dựng của specs/022. Phim qua đủ các tầng kiểm, nhưng người dùng thấy **đứng yên, chất lượng thấp và không đúng** kênh mẫu.

Đo lại thì thấy:
- trong mỗi cảnh, hình gần như không đổi (độ khác giữa hai khung 0,00–0,07, chỉ vọt ở chỗ cắt);
- đặt khung phim cạnh khung của kênh mẫu cùng loại cảnh (bảng so ngày 2026-11-14), phim chỉ khớp các **số trung bình** (độ sáng, bão hoà, tỉ lệ cỡ cảnh) và sai **tay nghề**.

| Mảng | Kênh mẫu | Phim thử |
|---|---|---|
| Khuôn mặt | mắt tròn có đốm sáng, mí cong mảnh, má hồng, miệng nhỏ | lông mày khối đen thô, mắt elip phẳng |
| Thân, áo | hoodie thon, mũ trùm và tay áo rõ | thân như bao, vạch trắng dọc |
| Cận rất sát | lệch tâm, cắt một mắt, hoặc cận đồ vật | chính diện, giữa khung |
| Bố cục | lệch tâm, có tiền cảnh, nhiều khoảng trống | chủ thể giữa khung, chật |
| Độ sâu | đám đông sau mờ thành đốm, tiền cảnh mờ | cả đám đông nét căng |
| Ánh sáng | nắng xiên ấm, mảng sáng tối rõ | tím đều, sàn sáng phẳng |
| Bối cảnh | đạo cụ kể chuyện (băng rôn, bóng bay, xe đồ ăn) | đồ vật lặp đều |
| Thẻ số liệu | hình ẩn dụ (tim và nhịp, bản đồ và máy bay) | chỉ có chữ |
| Thẻ câu hỏi cuối | chữ đậm, biểu tượng cho lựa chọn, dàn nhân vật 3D | chữ mảnh, chấm tròn phẳng |
| Chuyển động | nhân vật diễn, máy trôi, chuyển cảnh vệt sáng | đứng yên |

Nguyên nhân:
1. Công cụ học chỉ biến thành số những gì đo được trên từng khung; cách nhân vật diễn, cách máy đi, chuyển cảnh, âm thanh chỉ có lời văn.
2. Khung chứng minh là một ảnh tĩnh.
3. Spec 022 không có yêu cầu về chuyển động.
4. Không tầng kiểm nào so chuyển động với phong cách.
5. `STYLE.md` trộn luật học từ kênh với luật tự thêm (luật phụ đề trong `STYLE.md` không có bằng chứng nào trong ba báo cáo học).

Người dùng muốn: học **cách làm** của kênh mẫu và viết thành **template của mình** (quy trình, công thức, bộ dựng, tầng kiểm), không chép phim của họ. Giữ phụ đề in trên hình.

## Clarifications

### Session 2026-11-14

- Q: Phần học theo thời gian có tải lại đủ 10 video mẫu không? → A: Có, cả 10 video, đủ dài (≈ 1 giờ 50 phút), giống lần học ngày 2026-11-13.
- Q: Duyệt bảng so của bộ dựng theo cách nào? → A: 4 đợt: (1) nhân vật (mặt, biểu cảm, áo, đám đông); (2) khung hình (bố cục, độ sâu, ánh sáng, bối cảnh, cảnh không khí); (3) đồ hoạ (thẻ số liệu, thẻ tiêu đề, thẻ cuối); (4) chuyển động và âm thanh (diễn xuất, máy, chuyển cảnh, tiếng động, nhạc).
- Q: Nhạc nền lấy từ đâu? → A: Tự soạn bằng bộ nhạc cụ mẫu có sẵn của thư viện, theo công thức nhạc đo được cho từng nhịp; không dùng bản nhạc của bên ngoài.
- Q: Giọng đọc có nằm trong phạm vi không? → A: Có, giữ giọng của kênh (`am_michael` ×1,1) nhưng học và áp nhịp đọc của kênh mẫu (tốc độ theo nhịp, chỗ ngắt, chỗ nhấn, khoảng lặng trước số liệu), và có cách sửa chữ bị đọc sai.
- Q: Nâng cấp skill học phong cách (công cụ đo chuyển động, chứng minh bằng đoạn video) làm trong 023 hay để sau? → A: Làm luôn trong 023: công cụ đo nằm trong bước học, skill có bước đo chuyển động, chứng minh bằng đoạn video và bước viết `TEMPLATE.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Template tay nghề có bằng chứng (Priority: P1)

Người làm phim (Claude, ở luồng làm phim) mở `TEMPLATE.md` của phong cách và biết chính xác cách làm từng thành phần như kênh mẫu: mặt, thân áo, bố cục theo cỡ cảnh, độ sâu, ánh sáng, đạo cụ theo bối cảnh, thẻ số liệu, thẻ câu hỏi cuối, cảnh đêm, chuyển cảnh. Mỗi thành phần có số đo và trỏ tới các khung mẫu làm bằng chứng. `STYLE.md` được rà lại: luật nào cũng có bằng chứng từ kênh mẫu, hoặc ghi rõ là luật của xưởng.

**Why this priority**: Không có template thì bộ dựng và tầng kiểm không có gì đúng để theo. Phần hình học được ngay từ bảng ảnh cảnh còn giữ, không cần tải lại video.

**Independent Test**: Đọc `TEMPLATE.md` và `STYLE.md`; mở từng khung mẫu được dẫn; đối chiếu từng mô tả với khung.

**Acceptance Scenarios**:

1. **Given** `STYLE.md` sau tính năng này, **When** đọc từng luật, **Then** luật nào cũng có bằng chứng (khung mẫu, số đo hoặc hàng báo cáo) hoặc nhãn "luật của xưởng"; luật phụ đề mang nhãn "luật của xưởng".
2. **Given** `TEMPLATE.md`, **When** đọc một thành phần, **Then** có mô tả bằng lời của xưởng, ít nhất một số đo, ít nhất 3 khung mẫu từ ít nhất 2 video, và những điều nên làm và không nên làm.

---

### User Story 2 - Học nốt phần theo thời gian: diễn xuất, máy, chuyển cảnh, âm thanh (Priority: P2)

Xưởng học thêm những gì chỉ lộ ra theo thời gian: nhân vật cử động gì và bao lâu trong một cảnh, máy đứng hay trôi, đẩy, bám và nhanh bao nhiêu, chuyển cảnh loại nào và bao lâu, tiếng động và nhạc đặt ở đâu theo nhịp. Kết quả là số đo, vào `TEMPLATE.md`, cùng công thức cho từng nhịp của `STRUCTURE.md`.

**Why this priority**: Đây là chỗ phim thử sai rõ nhất (đứng yên), và số đo cũ không có. Phụ thuộc việc tải lại video mẫu.

**Independent Test**: Chạy các phép đo mới trên một video thử có chuyển động biết trước (nhân vật cử động, máy trôi, chuyển cảnh); rồi chạy trên bộ tham chiếu và đọc số trong `TEMPLATE.md`.

**Acceptance Scenarios**:

1. **Given** video thử có cử động nhân vật, máy trôi và chuyển cảnh biết trước, **When** chạy phép đo, **Then** đo ra đúng loại và thời điểm trong sai số cho phép.
2. **Given** bộ tham chiếu đã tải lại, **When** học xong, **Then** `TEMPLATE.md` có số cho cử động trong cảnh, máy, chuyển cảnh, âm thanh và công thức cho từng nhịp; video và âm thanh tham chiếu bị xoá.

---

### User Story 3 - Bộ dựng làm theo template, chứng minh cạnh khung mẫu (Priority: P3)

Bộ dựng của phong cách được làm lại theo template: mặt, thân áo, bố cục, độ sâu, ánh sáng, đạo cụ, thẻ, diễn xuất, máy, chuyển cảnh, âm thanh. Mỗi thành phần được chứng minh bằng một bảng so: khung của bộ dựng đặt cạnh khung mẫu cùng loại (thêm đoạn video ngắn với thành phần có chuyển động). Người dùng duyệt từng bảng bằng mắt.

**Why this priority**: Đây là thứ làm phim đẹp lên thật. Phụ thuộc US1 (hình) và US2 (chuyển động).

**Independent Test**: Mở bảng so của từng thành phần; người dùng duyệt hoặc ghi chỗ sai.

**Acceptance Scenarios**:

1. **Given** một thành phần đã làm lại, **When** tạo bảng so, **Then** có ít nhất 3 cặp (khung bộ dựng | khung mẫu cùng loại); thành phần có chuyển động có thêm đoạn video ngắn của bộ dựng và số đo đặt cạnh số của kênh mẫu.
2. **Given** người dùng xem bảng so, **When** người dùng duyệt, **Then** quyết định được ghi lại; chưa duyệt thì sửa và tạo lại bảng.

---

### User Story 4 - Tầng kiểm so phim với template, gồm chuyển động (Priority: P4)

Khi làm phim theo phong cách có template, các tầng kiểm báo cả lỗi tay nghề đo được: cảnh có người mà không có gì cử động, tỉ lệ máy đứng yên và chuyển động máy ngoài khoảng của kênh, độ sâu sai so với cỡ cảnh, kèm mã cảnh, thời điểm và cách sửa.

**Why this priority**: Để lỗi như phim thử không lọt qua lần nữa. Phụ thuộc số đo của US2.

**Independent Test**: Chạy các tầng kiểm trên phim thử cũ (đứng yên) và trên phim làm lại.

**Acceptance Scenarios**:

1. **Given** phim thử cũ, **When** chạy kiểm, **Then** các cảnh có người mà đứng yên bị báo kèm mã cảnh, và tỉ lệ máy đứng yên bị báo ngoài khoảng.
2. **Given** phim làm lại theo template, **When** chạy kiểm, **Then** không còn cảnh có người đứng yên, và các số chuyển động nằm trong khoảng của kênh mẫu.

---

### User Story 5 - Phim thử làm lại và bảng so trước/sau (Priority: P5)

Phim thử 1 phút được dựng lại bằng bộ dựng mới (cùng kịch bản, cùng giọng), kèm một bảng so ba cột: khung cũ | khung mới | khung mẫu cùng loại, và bảng số đo trước/sau.

**Why this priority**: Đây là cách người dùng thấy và quyết định có làm phim dài tiếp không.

**Independent Test**: Xem phim mới, bảng so và bảng số.

**Acceptance Scenarios**:

1. **Given** bộ dựng đã làm lại, **When** dựng lại `hundred-words`, **Then** phim qua đủ các tầng kiểm cùng các luật mới của US4, và có bảng so ba cột cho từng loại cảnh.

---

### Edge Cases

- Một thành phần không có đủ 3 khung mẫu cùng loại trong 10 video (vd. cảnh đêm hiếm): dùng tất cả khung có, ghi rõ số khung trong template, đánh dấu "ít bằng chứng".
- Hai phim mẫu làm một thành phần khác nhau (vd. 2 phim phẳng 2D): template theo 8 phim 3D (quyết định 2026-11-13), ghi khác biệt.
- Phép đo cử động nhân vật bị lẫn với máy trôi: tách chuyển động của cả khung (máy) ra trước khi đo cử động bên trong.
- Một luật của `STYLE.md` không tìm được bằng chứng và không phải luật của xưởng: bỏ luật đó, ghi vào nhật ký sửa.
- Người dùng không duyệt một đợt sau 2 lần sửa: dừng đợt đó, hỏi người dùng đi tiếp hay chấp nhận như hiện có.
- Tải lại video mẫu thất bại (bị gỡ, đổi quyền): học từ những video còn tải được, ghi rõ số video.

## Requirements *(mandatory)*

### Functional Requirements

**Rà phong cách (US1)**

- **FR-001**: Mỗi luật của `my-styles/dusk-hypothetical/STYLE.md` MUST mang bằng chứng từ kênh mẫu (khung mẫu dạng `bảng#ô`, số đo, hoặc hàng của báo cáo học) hoặc nhãn "luật của xưởng". Luật không có bằng chứng và không phải luật của xưởng MUST bị bỏ, ghi vào nhật ký sửa của `EVIDENCE.md`. Luật phụ đề in trên hình được giữ, mang nhãn "luật của xưởng".

**Template (US1, US2)**

- **FR-002**: Phong cách MUST có `TEMPLATE.md` gồm các thành phần: khuôn mặt và biểu cảm, thân và trang phục, bố cục theo từng cỡ cảnh, độ sâu theo từng cỡ cảnh, ánh sáng, bối cảnh và đạo cụ kể chuyện, đám đông, thẻ số liệu, thẻ câu hỏi cuối và thẻ tiêu đề, cảnh không khí (đêm, báo động), diễn xuất nhân vật, chuyển động máy, chuyển cảnh, âm thanh (tiếng động và nhạc), nhịp đọc lời (tốc độ theo nhịp, chỗ ngắt, chỗ nhấn, khoảng lặng trước số liệu). Mỗi thành phần MUST có: mô tả bằng lời của xưởng, ít nhất một số đo kèm khoảng, ít nhất 3 khung mẫu từ ít nhất 2 video (trừ trường hợp ít bằng chứng ở Edge Cases), điều nên làm và không nên làm, và tên gọi trong bộ dựng.
- **FR-003**: `TEMPLATE.md` MUST có công thức cho từng nhịp của `STRUCTURE.md` (hook, giải thích, được lợi, quy mô lớn, cái giá, khủng hoảng, kết, sting, thẻ cuối): chuỗi cỡ cảnh hay gặp, độ dài cảnh, máy đứng hay động, nhân vật diễn gì, đồ hoạ nào, tiếng động và chuyển cảnh nào, đo trên các phim mẫu.
- **FR-004**: Khung mẫu dùng làm bằng chứng MUST nằm trong `references/` (ngoài git); trong git chỉ có tham chiếu `bảng#ô`, số đo và hình do xưởng tự vẽ.

**Học phần theo thời gian (US2)**

- **FR-005**: Xưởng MUST đo, cho từng cảnh của video mẫu:
  - cử động bên trong cảnh sau khi đã trừ chuyển động của máy (có hay không, lớn bao nhiêu, kéo dài bao lâu);
  - loại và tốc độ chuyển động máy (đứng, trôi ngang, trôi dọc, đẩy vào, kéo ra, bám);
  - loại và độ dài chuyển cảnh (cắt, vệt sáng, nháy đen, mờ dần, vật che trượt);
  - với âm thanh: mật độ tiếng động theo thời gian và nhạc có hay không, mức nhạc so với giọng theo từng nhịp;
  - với lời đọc: tốc độ (từ mỗi phút) theo từng nhịp, độ dài chỗ ngắt giữa câu và giữa đoạn, khoảng lặng trước một con số.
- **FR-006**: Cả 10 video mẫu của bộ tham chiếu, đủ dài, MUST được tải lại chỉ để học nội bộ và MUST bị xoá khi học xong (đạt, dừng hoặc lỗi), theo mục Bản quyền của hiến pháp.
- **FR-007**: Trong chính tính năng này, các phép đo của FR-005 MUST trở thành công cụ dùng lại được của bước học phong cách (cho các phong cách sau); skill học phong cách MUST có bước đo chuyển động, bước viết `TEMPLATE.md` theo thành phần, và khung chứng minh MUST có thêm một đoạn video ngắn được so cả số đo chuyển động với kênh mẫu.

**Bộ dựng theo template (US3)**

- **FR-008**: Bộ dựng của phong cách MUST làm theo `TEMPLATE.md` cho mọi thành phần của FR-002, gồm tối thiểu:
  - nhân vật: chớp mắt và thở; dòng thời gian động tác (lên trong khoảng đo được rồi giữ); miệng mấp máy khi nhân vật có bong bóng thoại; đi bộ thì di chuyển thật;
  - máy: trôi, đẩy, bám theo tỉ lệ và tốc độ đo được;
  - chuyển cảnh theo loại và độ dài đo được;
  - âm thanh: tiếng động theo sự kiện; nhạc tự soạn bằng bộ nhạc cụ mẫu của thư viện theo công thức nhạc của từng nhịp (tempo, độ dày, lúc lên và lúc lặng, mức so với giọng đo từ kênh mẫu), không dùng bản nhạc của bên ngoài.
- **FR-017**: Lời đọc MUST giữ giọng của kênh (`am_michael` ×1,1) và MUST được xếp theo nhịp đọc của template (tốc độ theo nhịp, chỗ ngắt, khoảng lặng trước số liệu). Chữ bị bộ tạo giọng đọc sai (người nghe hoặc máy nhận dạng nghe thành chữ khác) MUST sửa được ở tầng giọng mà không đổi chữ của kịch bản đã duyệt, và tầng kiểm giọng MUST báo chữ đọc sai kèm mã dòng.
- **FR-009**: Mỗi thành phần đã làm lại MUST có bảng so ít nhất 3 cặp (khung bộ dựng | khung mẫu cùng loại); thành phần có chuyển động MUST có thêm đoạn video ngắn của bộ dựng và số đo đặt cạnh số của kênh mẫu. Bảng so chỉ dùng trong máy (có khung của kênh mẫu), không đưa vào git hay gửi đi.
- **FR-010**: Người dùng MUST duyệt bảng so theo 4 đợt: (1) nhân vật: mặt, biểu cảm, áo, đám đông; (2) khung hình: bố cục, độ sâu, ánh sáng, bối cảnh, cảnh không khí; (3) đồ hoạ: thẻ số liệu, thẻ tiêu đề, thẻ cuối; (4) chuyển động và âm thanh: diễn xuất, máy, chuyển cảnh, tiếng động, nhạc. Quyết định (duyệt, hoặc chỗ sai cần sửa) MUST được ghi lại cùng từng thành phần; đợt sau chỉ bắt đầu khi đợt trước được duyệt.

**Tầng kiểm (US4)**

- **FR-011**: Tầng kiểm cuối MUST so tỉ lệ máy đứng yên và độ chuyển động máy của phim với khoảng của phong cách; ngoài khoảng là cảnh báo phong cách.
- **FR-012**: Các tầng kiểm MUST có luật mới "cảnh có người đứng yên": cảnh có nhân vật mà không có cử động bên trong (theo ngưỡng chốt từ số đo của kênh mẫu) bị báo kèm mã cảnh, thời điểm và cách sửa. Luật này MUST được kiểm trước khi dựng hình (trên trang phim), không chỉ sau khi dựng.
- **FR-013**: Số đo nào của template đo được tự động (vd. độ sâu theo cỡ cảnh) MUST được so trong tầng kiểm khung hình như cảnh báo phong cách; số không đo tự động được MUST nằm trong bảng so để người dùng duyệt.

**Phim thử và bảng so trước/sau (US5)**

- **FR-014**: Phim `hundred-words` MUST được dựng lại bằng bộ dựng mới, cùng kịch bản và giọng đọc, qua đủ các tầng kiểm cùng luật mới, ở 60 fps trên GPU, kèm bảng so ba cột (cũ | mới | mẫu) cho từng loại cảnh và bảng số đo trước/sau.

**Phụ đề và bản quyền**

- **FR-015**: Phim theo template MUST giữ phụ đề in trên hình (luật của xưởng, người dùng chọn).
- **FR-016**: Template, bộ dựng và phim MUST NOT chép câu chuyện, câu thoại, nhân vật, giọng, nhạc, thumbnail hay bố cục từng khung cụ thể của kênh mẫu; template mô tả cách làm bằng lời của xưởng; mọi hình do code vẽ. `check-names` MUST đạt trên mọi tệp chữ mới.

### Key Entities

- **Template (`TEMPLATE.md`)**: cách làm của xưởng theo từng thành phần và từng nhịp, mỗi phần có số đo, khung mẫu làm bằng chứng và tên trong bộ dựng.
- **Thành phần**: một mảng tay nghề (mặt, bố cục, độ sâu, diễn xuất…) với mô tả, số đo, bằng chứng, điều nên và không nên làm.
- **Công thức nhịp**: cách kênh mẫu dựng một nhịp của `STRUCTURE.md` (chuỗi cảnh, máy, diễn, đồ hoạ, âm thanh).
- **Bảng so**: các cặp khung bộ dựng và khung mẫu cùng loại (thêm đoạn video và số đo với thành phần có chuyển động), cùng quyết định duyệt của người dùng.
- **Số đo chuyển động**: cho từng cảnh: cử động bên trong, loại và tốc độ máy, loại chuyển cảnh.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% luật của `STYLE.md` có bằng chứng hoặc nhãn "luật của xưởng"; 0 luật không nhãn.
- **SC-002**: Mỗi thành phần của `TEMPLATE.md` có ≥ 1 số đo kèm khoảng và ≥ 3 khung mẫu từ ≥ 2 video (hoặc ghi "ít bằng chứng" kèm số khung có); mỗi nhịp của `STRUCTURE.md` có một công thức.
- **SC-003**: Trên video thử có chuyển động biết trước, phép đo mới nhận đúng ≥ 90% cảnh có cử động nhân vật, ≥ 90% loại chuyển động máy và ≥ 90% chuyển cảnh không phải cắt thường, với thời điểm lệch ≤ 0,2 s.
- **SC-004**: Cả 4 đợt bảng so được người dùng duyệt, mỗi đợt sau tối đa 2 lần sửa.
- **SC-005**: Trên phim thử cũ, luật "cảnh có người đứng yên" báo ≥ 15/21 cảnh và tỉ lệ máy đứng yên bị báo ngoài khoảng; trên phim làm lại, 0 cảnh có người đứng yên, và tỉ lệ máy đứng yên cùng độ chuyển động máy nằm trong khoảng của kênh mẫu (hiện 0,72–0,93 và p50 0,008–0,176).
- **SC-006**: Trên bảng so ba cột của phim làm lại, người dùng thấy bản mới gần kênh mẫu hơn bản cũ ở mọi loại cảnh được so; người dùng chấp nhận phim làm lại làm điểm xuất phát cho phim dài.
- **SC-007**: Sau khi học, 0 tệp video hay âm thanh mẫu còn trong `references/`; `check-names` đạt trên `TEMPLATE.md`, `STYLE.md` và mọi tệp chữ mới của bộ dựng.

## Assumptions

- Phong cách áp dụng là `dusk-hypothetical`; công cụ đo mới dùng được cho phong cách khác sau này.
- Bộ tham chiếu là 10 video đã học ngày 2026-11-13 (`references/dusk-hypothetical-3`), tải lại đủ 10, đủ dài (Clarifications); luật hình theo 8 phim 3D, nhịp và âm thanh theo cả 10.
- Phần hình của US1 học được từ bảng ảnh cảnh và nhãn còn giữ, không cần tải lại video; US2 cần tải lại.
- Phim dài 10,5 phút và phim mẫu của specs/022 (US2, US4 của 022) để sau tính năng này, làm theo template.
- Dựng bằng GPU; dựng bằng phần mềm thì dừng và hỏi người dùng.
- Mọi lượt gọi Claude (gán nhãn, biên tập) dùng Opus; lượt nào tốn tiền thì hỏi người dùng trước.
- Gói đăng (specs/011) không thuộc phạm vi phim thử.
