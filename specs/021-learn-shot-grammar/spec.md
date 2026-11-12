# Feature Specification: Học cách quay của kênh tham chiếu (cỡ cảnh, góc máy, độ nét, bối cảnh)

**Feature Branch**: `021-learn-shot-grammar`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User description: "Style-learn đo thêm cỡ cảnh (đặc tả, cận, trung, toàn, toàn rất rộng; tỉ lệ từng loại; hai cảnh liền nhau có đổi cỡ không), góc máy (ngang tầm mắt, thấp, từ trên xuống, qua vai), độ nét (phần khung nét, chủ thể nét hay mờ, tiền cảnh mờ) và bối cảnh (số bối cảnh, bao lâu đổi) trên video tham chiếu, ghi số đo và khung bằng chứng vào phong cách; học lại dusk-hypothetical. Sau đó tầng 2 (qc shots, specs/020) so phim với các số đo này và báo theo mã cảnh. (…) Cái tôi cần là học chính xác video tham chiếu đã làm với kênh."

## Bối cảnh

Học phong cách (specs/002) hiện đo màu, độ sáng, độ tương phản, chuyển động, nhịp cắt, âm lượng và tốc độ đọc. Cách quay chỉ được ghi bằng lời trong báo cáo của agent, ví dụ "cỡ cảnh xen kẽ đặc tả với toàn rất rộng", "độ sâu trường ảnh nông, một đầu mờ ở tiền cảnh". Lời không có con số, nên phim làm theo phong cách không có gì để so, và không bước kiểm nào bắt được khi phim quay khác kênh.

Phim `films/pet-swap` (192 cảnh, theo phong cách Dusk Hypothetical), đo ngày 2026-11-12:

| Số đo | `pet-swap` | Phong cách nói (bằng lời) |
|---|---|---|
| Khung không có vùng nào nét (giữa khung, bỏ dải đen và vùng phụ đề, chia 12 ô) | 128/192 khung | chủ thể nét, một đầu hoặc vai mờ ở mép khung |
| Khung mẫu đã duyệt của phong cách | 12/12 ô nét | |
| Cận và đặc tả | 46% | xen kẽ đặc tả với toàn rất rộng |
| Toàn rất rộng | 1% (2 cảnh) | |
| Hai cảnh liền nhau cùng cỡ | 42 lần | đổi cỡ mạnh giữa hai cảnh liền nhau |
| Ngang tầm mắt | 85% | góc thấp, từ trên xuống, qua vai là ngữ pháp chính |
| Bối cảnh nhiều nhất | 38% số cảnh (bếp) | (không có số) |

Người dùng xem phim và thấy ngay phim "ít góc máy, bị mờ, không đa dạng như kênh mình học theo". Mục tiêu của tính năng: học **đúng** cách kênh tham chiếu quay, bằng số đo và khung bằng chứng, rồi dùng đúng các số đó để kiểm phim.

Mức quy trình: **Đầy đủ** (đổi định dạng dữ liệu của phong cách; cách đo cỡ cảnh và góc máy còn phải làm rõ).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Học cách quay từ video tham chiếu, có số đo (Priority: P1)

Khi học phong cách từ một kênh, xưởng tách video thành từng cảnh, rồi với mỗi cảnh ghi lại: cỡ cảnh, góc máy, độ nét (phần khung nét, chủ thể nét hay mờ, có tiền cảnh mờ không) và bối cảnh. Từ đó xưởng tính phân bố cho cả bộ video: tỉ lệ từng cỡ cảnh, tỉ lệ từng góc máy, tỉ lệ hai cảnh liền nhau đổi cỡ, phần khung nét, số bối cảnh và thời gian giữa hai lần đổi bối cảnh. Mỗi con số đi kèm khung hình làm bằng chứng.

**Why this priority**: Không có số đo thì không có gì để làm theo và không có gì để kiểm. Đây là phần người dùng nhấn mạnh: "học chính xác video tham chiếu".

**Independent Test**: Chạy bước học trên một bộ video thử mà cỡ cảnh, góc máy và độ nét của từng cảnh đã biết trước. Kết quả phải có phân bố cho từng mục, từng cảnh khớp với nhãn đã biết theo SC-001, và có bảng ảnh ghi nhãn của mỗi cảnh.

**Acceptance Scenarios**:

1. **Given** một bộ video tham chiếu đã đo nhịp cắt, **When** chạy bước học cách quay, **Then** mỗi cảnh có cỡ cảnh (đặc tả, cận, trung, toàn, toàn rất rộng, hoặc "chèn" cho thẻ chữ và hình phẳng), góc máy (ngang tầm mắt, thấp, từ trên xuống, qua vai), phần khung nét và bối cảnh.
2. **Given** các cảnh đã có nhãn, **When** tổng hợp, **Then** hồ sơ đo có tỉ lệ từng cỡ cảnh, từng góc máy, tỉ lệ hai cảnh liền nhau đổi cỡ, độ dài chuỗi cùng cỡ dài nhất, trung vị phần khung nét, tỉ lệ cảnh có chủ thể nét, tỉ lệ cảnh có tiền cảnh mờ, số bối cảnh, và thời gian trung vị giữa hai lần đổi bối cảnh. Mỗi số có khoảng giữa các video, như các số đo hiện có.
3. **Given** hồ sơ đã tổng hợp, **When** mở bảng ảnh của một video, **Then** mỗi ô ghi mã cảnh và nhãn của nó, để người dùng soát bằng mắt.
4. **Given** một video có dải đen trên dưới và phụ đề cháy vào hình, **When** đo độ nét, **Then** dải đen và vùng phụ đề không tính vào khung.

---

### User Story 2 - Học lại phong cách Dusk Hypothetical (Priority: P2)

Học lại `my-styles/dusk-hypothetical` từ kênh tham chiếu đã ghi trong `channels/dusk-hypothetical/references.json`, với các số đo cách quay mới. Mục ngữ pháp máy quay và chiều sâu của phong cách ghi bằng con số (kèm khung bằng chứng) thay cho lời mô tả. Các luật và nhật ký sửa đã có được giữ lại; luật nào sai so với số đo mới thì sửa và ghi vào nhật ký.

**Why this priority**: Phong cách mà người dùng đang làm phim cần có số trước khi làm phim mới. Story 1 vẫn có giá trị riêng với mọi phong cách học sau này.

**Independent Test**: Sau khi học lại, phong cách có bảng số đo cách quay; mục máy quay có con số kèm khung bằng chứng; mọi dòng của nhật ký sửa cũ còn nguyên; video tham chiếu đã được xoá.

**Acceptance Scenarios**:

1. **Given** phong cách cũ chỉ mô tả cách quay bằng lời, **When** học lại, **Then** bảng "Key numbers" có thêm các số đo cách quay, và mục camera ghi tỉ lệ từng cỡ cảnh, từng góc máy, tỉ lệ đổi cỡ giữa hai cảnh liền nhau, phần khung nét.
2. **Given** một luật cũ (ví dụ "xen kẽ đặc tả với toàn rất rộng") mà số đo mới không xác nhận, **When** học lại, **Then** luật được sửa theo số đo và nhật ký sửa có thêm một dòng ghi trước, sau, bằng chứng.
3. **Given** học xong (đạt, dừng hoặc lỗi), **When** kiểm thư mục tham chiếu, **Then** video đã bị xoá, chỉ còn số đo và vài khung bằng chứng.

---

### User Story 3 - Tầng 2 so cách quay của phim với phong cách (Priority: P3)

Khi chạy kiểm hình theo cảnh (`qc shots`, specs/020), xưởng gán cho mỗi cảnh của phim cùng loại nhãn như video tham chiếu (cỡ cảnh, góc máy, độ nét), bằng đúng cách đo đã dùng cho video tham chiếu, rồi so phân bố của phim với phân bố của phong cách. Lỗi và cảnh báo báo theo mã cảnh.

**Why this priority**: Đây là chỗ bắt được lỗi của `pet-swap` trước khi render. Nó cần số đo của story 1 và 2.

**Independent Test**: Trên một phim thử có nhãn cảnh biết trước (cố ý quá nhiều cận, toàn ngang tầm mắt, nhiều cảnh liền nhau cùng cỡ, một số khung mờ hết), kiểm hình phải báo đủ các lệch đó, kèm mã cảnh.

**Acceptance Scenarios**:

1. **Given** một cảnh mà không vùng nào của khung nét, **When** kiểm hình, **Then** cảnh đó bị báo "khung mờ" kèm phần khung nét đo được.
2. **Given** phim có tỉ lệ toàn rất rộng 1% trong khi phong cách có khoảng cao hơn, **When** kiểm hình, **Then** báo lệch kèm số đo, khoảng của phong cách, và gợi ý các cảnh có thể đổi thành toàn rất rộng.
3. **Given** phim có chuỗi cảnh liền nhau cùng cỡ dài hơn mức của phong cách, **When** kiểm hình, **Then** báo chuỗi đó kèm mã các cảnh trong chuỗi.
4. **Given** phong cách chưa có số đo cách quay (phong cách thư viện, hoặc học trước tính năng này), **When** kiểm hình, **Then** bỏ qua phần so cách quay và nói rõ đã bỏ qua.
5. **Given** bảng ảnh của tầng 2, **When** mở, **Then** mỗi ô ghi thêm nhãn cỡ cảnh và góc máy của cảnh.

### Edge Cases

- **Cảnh không có nhân vật** (phong cảnh, đồ vật, bản đồ): cỡ cảnh tính theo chủ thể chính của khung (vật được lấy nét); không xác định được thì ghi "không rõ", và không tính vào tỉ lệ.
- **Thẻ chữ, đồ hoạ phẳng, hình chèn dữ liệu**: nhãn "chèn"; không tính vào tỉ lệ cỡ cảnh và góc máy, nhưng đếm riêng.
- **Cảnh rất ngắn** (dưới 0,5 s, chớp sáng): không gán nhãn; đếm riêng.
- **Video dọc và video ngang lẫn lộn**: số đo tách theo định dạng, như số đo hiện có.
- **Cảnh có chuyển máy đổi cỡ trong cảnh** (đẩy máy mạnh): nhãn theo khung giữa cảnh; ghi thêm cỡ ở đầu và cuối cảnh nếu chúng khác nhau.
- **Phim cố ý mờ hết một cảnh** (giấc mơ, mất ý thức): người làm phim đánh dấu ngoại lệ cho cảnh đó (specs/020 FR-015).
- **Video tham chiếu bị chặn tải**: theo cách hiện có của style-learn (người dùng đặt file vào thư mục tham chiếu).

## Requirements *(mandatory)*

### Functional Requirements

**Học (story 1)**

- **FR-001**: Bước học phong cách PHẢI gán cho mỗi cảnh của video tham chiếu: cỡ cảnh (đặc tả, cận, trung, toàn, toàn rất rộng, chèn, không rõ), góc máy (ngang tầm mắt, thấp, từ trên xuống, qua vai, không rõ), phần khung nét (0–1), chủ thể nét hay mờ, có tiền cảnh mờ hay không, và mã bối cảnh.
- **FR-002**: Cỡ cảnh và góc máy PHẢI được xác định bằng [NEEDS CLARIFICATION: cách gán nhãn cỡ cảnh và góc máy — (A) một công cụ đo tự động trên khung hình; (B) Claude xem bảng ảnh và gán nhãn từng cảnh, mỗi nhãn kèm ô bảng ảnh làm bằng chứng, công cụ đo kiểm chéo những gì đo được (kích thước chủ thể, độ nét); (C) kết hợp: công cụ gán trước, Claude soát và sửa trên bảng ảnh?].
- **FR-003**: Độ nét PHẢI được đo bằng công cụ trên từng khung giữa cảnh, không tính dải đen và vùng phụ đề cháy vào hình. Cách đo độ nét PHẢI giống hệt khi đo video tham chiếu và khi đo phim (US3).
- **FR-004**: Bối cảnh PHẢI được nhận ra bằng cách gom các cảnh giống nhau về màu và bố cục; kết quả có số bối cảnh, tỉ lệ cảnh của bối cảnh nhiều nhất, và thời gian trung vị giữa hai lần đổi bối cảnh.
- **FR-005**: Hồ sơ đo PHẢI có, cho mỗi định dạng: tỉ lệ từng cỡ cảnh, tỉ lệ từng góc máy, tỉ lệ hai cảnh liền nhau đổi cỡ, chuỗi cùng cỡ dài nhất, trung vị phần khung nét, tỉ lệ cảnh có chủ thể nét, tỉ lệ cảnh có tiền cảnh mờ, số bối cảnh, thời gian trung vị giữa hai lần đổi bối cảnh. Mỗi số có trung vị và khoảng giữa các video.
- **FR-006**: Bảng ảnh của bước học PHẢI ghi mã cảnh và nhãn trên mỗi ô.
- **FR-007**: Các số đo cách quay PHẢI được ghi vào phong cách: bảng "Key numbers" của bằng chứng, mục camera và chiều sâu của bản phong cách (kèm khung bằng chứng), và một chỗ máy đọc được để tầng kiểm dùng.

**Học lại Dusk Hypothetical (story 2)**

- **FR-008**: Phong cách `dusk-hypothetical` PHẢI được học lại từ kênh tham chiếu đã ghi của kênh, giữ mọi dòng nhật ký sửa cũ. Luật nào sai so với số đo mới thì sửa và ghi thêm vào nhật ký.
- **FR-009**: Video tham chiếu PHẢI bị xoá khi học xong, như hiện nay (hiến pháp, mục Bản quyền).

**Kiểm phim (story 3)**

- **FR-010**: Kiểm hình theo cảnh (`qc shots`) PHẢI gán cho mỗi cảnh của phim cùng loại nhãn như FR-001, bằng cùng cách đo.
- **FR-011**: Mỗi cảnh không có vùng nào nét (phần khung nét dưới ngưỡng) PHẢI bị báo "khung mờ", kèm mã cảnh và số đo. Mức của lỗi này: [NEEDS CLARIFICATION: "khung mờ" chặn render như lỗi khung (khung phẳng, quá tối), hay chỉ cảnh báo như lệch phong cách?].
- **FR-012**: Khi phong cách có số đo cách quay, kiểm hình PHẢI so tỉ lệ từng cỡ cảnh, từng góc máy, tỉ lệ đổi cỡ giữa hai cảnh liền nhau, chuỗi cùng cỡ dài nhất, trung vị phần khung nét và bối cảnh nhiều nhất với khoảng của phong cách. Lệch là cảnh báo (như specs/020 FR-013), kèm số đo, khoảng, và mã các cảnh liên quan.
- **FR-013**: Phong cách không có số đo cách quay thì kiểm hình PHẢI báo "bỏ qua so cách quay".
- **FR-014**: Bảng ảnh của tầng 2 PHẢI ghi thêm nhãn cỡ cảnh và góc máy trên mỗi ô.
- **FR-015**: Xưởng KHÔNG ĐƯỢC sửa file nào trong thư viện gốc.

### Key Entities

- **Nhãn cảnh**: mã cảnh, thời điểm, cỡ cảnh, góc máy, phần khung nét, chủ thể nét hay mờ, tiền cảnh mờ, mã bối cảnh, bằng chứng (ô bảng ảnh).
- **Hồ sơ cách quay**: theo định dạng: các tỉ lệ và trung vị của FR-005, mỗi số có trung vị và khoảng giữa các video.
- **Số đo cách quay của phong cách**: các khoảng mà tầng kiểm so với (phần máy đọc được của FR-007).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Trên một bộ 40 cảnh mà người dùng đã gán nhãn bằng tay (lấy từ video tham chiếu), nhãn cỡ cảnh của xưởng trùng nhãn của người dùng ở ít nhất 80% số cảnh, và lệch không quá một bậc ở ít nhất 95%. Góc máy trùng ở ít nhất 80%.
- **SC-002**: Phép đo độ nét phân biệt được: trên `pet-swap`, ít nhất 120/192 khung bị xếp "không vùng nào nét"; trên khung mẫu đã duyệt của phong cách, phần khung nét ít nhất 0,5.
- **SC-003**: Học lại `dusk-hypothetical` (10 video, như lần học trước) xong trong không quá 1,5 lần thời gian của lần học trước.
- **SC-004**: Sau khi học lại, phong cách có đủ các số của FR-005 kèm khung bằng chứng, và mọi dòng nhật ký sửa cũ còn nguyên.
- **SC-005**: Trên phim thử có nhãn biết trước (US3), kiểm hình báo đủ mọi cảnh "khung mờ" và mọi lệch phân bố đã cài, không báo nhầm quá 1 cảnh trên 30.
- **SC-006**: Trên `pet-swap`, kiểm hình báo được: số khung mờ, tỉ lệ toàn rất rộng, tỉ lệ ngang tầm mắt và số lần hai cảnh liền nhau cùng cỡ, mỗi mục kèm mã cảnh, và các mục nằm ngoài khoảng của phong cách học lại thì là cảnh báo.
- **SC-007**: Không file nào trong thư viện gốc bị đổi. Video tham chiếu bị xoá sau khi học.

## Assumptions

- Học lại dùng cùng kênh tham chiếu, cùng số video và cùng cách lấy mẫu (5 cửa sổ mỗi video, 1800 giây) như lần học trước, để số đo so được với số cũ.
- Cảnh lấy từ phép dò cắt cảnh hiện có của style-learn. Lần học trước có một lần sửa vì phép dò đó bỏ sót cắt cảnh giữa các cảnh tối giống nhau (nhật ký sửa #1); tính năng này cần phép dò cắt cảnh đủ đúng để tách cảnh, và sửa nó nếu SC-001 cho thấy cần.
- Ngưỡng "nét" và "không vùng nào nét" được chốt ở bước plan, dựa trên số đo của chính video tham chiếu, rồi dùng chung cho video tham chiếu và phim.
- Tầng kiểm của specs/020 là nơi so phim; các lệch phân bố là cảnh báo cần lý do (như specs/020), không chặn render.
- Bảng ảnh, nhãn và vài khung bằng chứng được giữ lại cùng phong cách; video thì không.
