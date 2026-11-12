# Feature Specification: QC theo từng cảnh trước khi render

**Feature Branch**: `020-qc-before-render`

**Created**: 2026-11-12

**Status**: Draft

**Input**: User description: "QC phát hiện lỗi theo từng cảnh trước khi render, thay vì render xong mới QC rồi phải render lại. (…) Muốn: các tầng kiểm theo dữ liệu cần — tầng 0 ngay sau khi tạo giọng; tầng 1 kiểm kế hoạch không cần render, báo theo mã cảnh; tầng 2 mỗi cảnh một ảnh và kiểm phong cách, có bảng ảnh ghi mã cảnh; tầng 3 kiểm từng đoạn ngay trong lúc render và dừng sớm; tầng 4 sau khi ghép tiếng. Câu xác định theo kịch bản, không theo dấu chấm của Whisper; chặn mốc âm; một mô hình nhận dạng cho cả xưởng. Luồng làm phim không cho render khi tầng 1–2 chưa đạt. Gói đăng dùng phụ đề đã đạt của phim; thumbnail không có phụ đề. Không sửa thư viện gốc. Dựa trên specs/019."

## Clarifications

### Session 2026-11-12

- Q: Phim lệch số đo của phong cách thì có chặn render không? → A: Không chặn. Lỗi nhịp (tầng 1) và lỗi khung (khung phẳng, quá tối hoặc cháy, chữ thiếu phông, chữ đè phụ đề ở tầng 2) chặn render; lệch phong cách chỉ cảnh báo, và render được khi người làm phim ghi một dòng lý do (FR-009, FR-013).

## Bối cảnh

Hiện `qc` (specs/010) chỉ chạy khi phim đã render và ghép tiếng xong. Phim `films/pet-swap` (9 phút 32 giây, 192 cảnh, 2026-11-12) cho thấy cái giá của việc này:

| Lỗi | Số lần | Cần gì để phát hiện | Phát hiện lúc nào |
|---|---|---|---|
| Cắt cảnh giữa câu, hoặc sát lúc câu dứt (< 0,4 s) | ≈ 85 | danh sách cảnh, mốc từng từ | sau render → render lại |
| Cảnh chứa câu cuối của đoạn ngắn hơn 2,5 s | 11 | danh sách cảnh, mốc từng từ | sau render → render lại |
| Lặng > 20%, đuôi phim > 1,5 s, hình đứng yên > 6 s ở cuối | 3 | dòng thời gian, danh sách cảnh | sau render → render lại |
| Thẻ chữ hiện chưa đủ lâu để đọc | 3 | chữ trên màn hình theo thời gian | sau render |
| Khoảng nghỉ 0,8 s bên trong một dòng giọng | 2 | file giọng | sau render; không sửa được nếu không làm lại giọng |
| Góc máy hỏng (máy quay nằm trong đầu nhân vật hoặc tường: khung gần như một màu) | ≈ 25 | một ảnh mỗi cảnh | soát bằng mắt trên bảng ảnh, 3 vòng |
| Màu lệch phong cách: độ sáng trung vị 0,13 (phong cách 0,20–0,30), bão hoà 0,53 (0,32–0,50) | 1 | một ảnh mỗi cảnh, số đo của phong cách | **không bước nào bắt được** |
| Dải âm lượng 1,5 LU (phong cách 2,4–3,3) | 1 | bản mix | không bước nào bắt được |
| Phụ đề của gói đăng có 21 dòng hiện dưới 1 s; thumbnail dính phụ đề | 22 | phụ đề, thumbnail | sau khi làm gói đăng |

Phim phải render lại 2 lần: mỗi lần 24 phút bằng GPU, tức khoảng 12 giờ nếu vẽ bằng phần mềm. Thêm vào đó, `qc` xác định câu bằng dấu chấm trong bản nhận dạng giọng, mà công cụ nhận dạng hay viết dấu phẩy thay dấu chấm và cho từ đầu dòng bắt đầu trước giây 0. Vì thế `qc` báo lỗi cắt giả, và chỉ số lặng nhảy từ 22% lên 27% chỉ vì đổi mô hình nhận dạng.

Tính năng này chia việc kiểm thành các tầng theo dữ liệu mà mỗi phép kiểm cần, để lỗi được bắt ở bước rẻ nhất có thể.

Mức quy trình: **Đầy đủ**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Kiểm kế hoạch trước khi render (Priority: P1)

Khi giọng và dòng thời gian đã xong, người làm phim (Claude trong chat hoặc worker của app) chạy một lệnh kiểm kế hoạch. Lệnh đo mọi điều về nhịp mà không cần video, xong trong vài giây, và báo từng lỗi kèm mã cảnh, thời điểm và cách sửa. Lệnh ghi video từ chối chạy khi kế hoạch hiện tại chưa đạt.

**Why this priority**: Đây là phần tiết kiệm lớn nhất. Khoảng 90% lỗi của `pet-swap` thuộc loại này, và chúng là lý do của cả hai lần render lại.

**Independent Test**: Chạy lệnh kiểm kế hoạch trên một phim thử có cài sẵn 10 lỗi nhịp đã biết (cắt giữa câu, cắt sát lúc câu dứt, cảnh chứa câu cuối quá ngắn, cảnh quá dài, lặng nhiều, đuôi dài). Kết quả cần thấy:
- cả 10 lỗi được báo, mỗi lỗi đúng mã cảnh;
- lệnh xong trong 10 giây;
- lệnh ghi video từ chối chạy. Sửa hết lỗi rồi chạy lại thì đạt, và lệnh ghi video chạy được.

**Acceptance Scenarios**:

1. **Given** một phim có giọng, dòng thời gian và danh sách cảnh, **When** chạy lệnh kiểm kế hoạch, **Then** mỗi lỗi được báo trên một dòng: mã cảnh, thời điểm, luật bị vi phạm, số đo, ngưỡng.
2. **Given** kế hoạch có cắt cảnh giữa câu, **When** kiểm, **Then** lỗi nêu câu bị cắt (vài chữ đầu) và mốc sớm nhất hợp lệ để cắt.
3. **Given** kế hoạch chưa đạt, **When** chạy lệnh ghi video, **Then** lệnh dừng trước khi mở trình duyệt, nói chạy lệnh kiểm kế hoạch, mã thoát 1.
4. **Given** kế hoạch đã đạt nhưng sau đó nguồn phim đổi, **When** chạy lệnh ghi video, **Then** lệnh coi như chưa kiểm và đòi kiểm lại.
5. **Given** người dùng chủ ý muốn ghi dù chưa đạt (ví dụ một bản thử), **When** chạy lệnh ghi video với cờ bỏ qua, **Then** lệnh chạy, và nhật ký cùng kết quả kiểm ghi rõ là đã bỏ qua kiểm kế hoạch.
6. **Given** một phim không có giọng đọc, **When** kiểm kế hoạch, **Then** chỉ các luật không liên quan tới giọng được áp dụng (độ dài cảnh, đuôi phim, thời gian đọc chữ).

---

### User Story 2 - Mỗi cảnh một ảnh, kèm kiểm phong cách (Priority: P2)

Sau khi kế hoạch đạt, người làm phim chạy lệnh kiểm hình theo cảnh. Xưởng chụp một ảnh ở giữa mỗi cảnh, tự đo từng ảnh, so cả phim với số đo của phong cách, và tạo một bảng ảnh có ghi mã cảnh để xem bằng mắt. Lệnh ghi video cũng từ chối chạy khi lỗi khung của tầng này chưa sửa. Lệch phong cách chỉ cảnh báo: phải ghi một dòng lý do mới render được.

**Why this priority**: Bắt được các góc máy hỏng và màu lệch phong cách, những thứ ở `pet-swap` phải soát bằng mắt 3 vòng hoặc không ai bắt được. Story 1 vẫn có giá trị riêng mà không cần story này.

**Independent Test**: Trên một phim thử có 6 cảnh cài lỗi (khung gần như một màu, quá tối, cháy sáng, chữ thiếu phông, chữ đè lên phụ đề, cả phim tối hơn khoảng độ sáng của phong cách), chạy lệnh kiểm hình. Kết quả cần thấy:
- đủ 6 lỗi, đúng mã cảnh;
- không quá 1 cảnh tốt bị báo nhầm trên 30 cảnh;
- có bảng ảnh ghi mã cảnh;
- trên phim 192 cảnh, xong trong 3 phút với GPU.

**Acceptance Scenarios**:

1. **Given** một cảnh mà khung gần như một màu (máy quay nằm trong vật thể), **When** kiểm hình, **Then** cảnh đó bị báo "khung phẳng" kèm tỉ lệ màu chiếm chỗ.
2. **Given** một phim dùng phong cách có số đo (phong cách học từ kênh), **When** kiểm hình, **Then** độ sáng trung vị, độ bão hoà trung vị và số lần cắt mỗi phút của phim được so với khoảng của phong cách. Ngoài khoảng thì cảnh báo kèm số đo và khoảng. Lệnh ghi video đòi một dòng lý do trước khi chạy.
3. **Given** một phong cách không có số đo (phong cách của thư viện chưa đo), **When** kiểm hình, **Then** bỏ qua phần so phong cách và nói rõ là đã bỏ qua.
4. **Given** một cảnh thẻ chữ cố ý tối và trơn (nền thẻ trong không gian trống của phong cách), **When** kiểm hình, **Then** cảnh đó không bị báo "khung phẳng", vì chữ của thẻ được tính là nội dung.
5. **Given** kiểm xong, **When** mở thư mục kết quả, **Then** có bảng ảnh: mỗi ô ghi mã cảnh, cảnh lỗi được đánh dấu.

---

### User Story 3 - Kiểm giọng ngay sau khi tạo, câu tính theo kịch bản (Priority: P3)

Ngay sau khi tạo giọng, xưởng kiểm từng dòng: khoảng nghỉ dài bên trong dòng, từ nhận dạng sai, độ dài file so với từ cuối. Ranh giới câu được tính theo kịch bản, không theo dấu chấm của công cụ nhận dạng. Mốc thời gian âm được chặn về 0. Cả xưởng dùng một mô hình nhận dạng duy nhất, nên các chỉ số không đổi khi chạy lại.

**Why this priority**: Lỗi giọng sửa rẻ nhất khi chưa có hình. Việc tính câu theo kịch bản cũng làm cho story 1 đáng tin, không báo lỗi giả.

**Independent Test**:
- Dòng giọng thử có một khoảng nghỉ 0,9 giây bên trong: bị báo kèm mã dòng và vị trí.
- Bản nhận dạng có dấu phẩy chỗ kịch bản có dấu chấm, và từ đầu dòng có mốc âm: kiểm kế hoạch vẫn xác định đúng ranh giới câu, không báo lỗi cắt giả.
- Chạy hai lần liền, chỉ số lặng giống nhau tới 0,01.

**Acceptance Scenarios**:

1. **Given** vừa tạo xong giọng, **When** chạy lệnh kiểm giọng, **Then** các khoảng nghỉ ≥ 0,8 s bên trong một dòng được báo kèm mã dòng, thời điểm, và lời khuyên làm lại dòng đó.
2. **Given** công cụ nhận dạng viết "at 7, but it sounds wrong," cho hai câu của kịch bản, **When** kiểm kế hoạch, **Then** ranh giới câu nằm sau "seven" như trong kịch bản.
3. **Given** từ đầu tiên của một dòng có mốc bắt đầu âm, **When** đo, **Then** mốc đó được tính là 0.
4. **Given** hai lần chạy liền trên cùng giọng, **When** so chỉ số lặng và các mốc câu, **Then** chúng giống hệt nhau.

---

### User Story 4 - Kiểm từng đoạn trong lúc render, dừng sớm (Priority: P4)

Trong lúc ghi video, mỗi đoạn vừa ghi xong được kiểm ngay: khung đen, hình đứng yên quá lâu. Đoạn lỗi làm lệnh dừng sớm, báo mã cảnh. Các đoạn đã đạt được giữ lại, nên sửa xong chỉ ghi lại phần bị ảnh hưởng.

**Why this priority**: Bắt các lỗi chỉ lộ ra trên hình động (chuyển động hỏng, khung đen ngẫu nhiên) mà không phải chờ hết cả phim. Ba story trước đã bắt phần lớn lỗi.

**Independent Test**: Ghi video một phim thử có một cảnh đứng yên 8 giây ở giữa phim. Kết quả cần thấy:
- lệnh dừng trong vòng 1 đoạn sau đoạn lỗi;
- báo mã cảnh của đoạn lỗi;
- các đoạn trước đó vẫn được giữ.

Sửa cảnh đó rồi chạy lại: chỉ các đoạn từ chỗ lỗi trở đi được ghi lại.

**Acceptance Scenarios**:

1. **Given** một đoạn có khung đen ở giữa phim, **When** đoạn đó ghi xong, **Then** lệnh dừng, báo mã cảnh và thời điểm.
2. **Given** một cảnh đứng yên quá ngưỡng của phong cách (mặc định 6 s), **When** đoạn chứa nó ghi xong, **Then** lệnh dừng với lỗi "hình đứng yên".
3. **Given** người dùng muốn ghi hết rồi xem lỗi một thể, **When** chạy với cờ không dừng, **Then** lệnh ghi hết và liệt kê mọi đoạn lỗi ở cuối.

---

### User Story 5 - Kiểm cuối và gói đăng dùng lại kết quả đã đạt (Priority: P5)

Sau khi ghép tiếng, bước kiểm cuối chỉ còn âm lượng, đỉnh tiếng, dải âm lượng (so với phong cách) và độ khớp của tiếng với hình. Gói đăng dùng lại phụ đề đã đạt của phim thay vì tự cắt lại. Thumbnail được chụp không có phụ đề và thẻ chữ của phim.

**Why this priority**: Dọn các lỗi còn lại của `pet-swap` ở cuối quy trình. Chúng ít nhưng phiền.

**Independent Test**:
- Bản mix có dải âm lượng 1,5 LU trên một phong cách có khoảng 2,4–3,3: bị báo.
- Gói đăng của `pet-swap` có 0 dòng phụ đề dưới 1 s.
- Ba thumbnail không chứa chữ phụ đề nào (kiểm bằng cách so vùng phụ đề).

**Acceptance Scenarios**:

1. **Given** phim đã ghép tiếng, **When** chạy kiểm cuối, **Then** âm lượng tích hợp, đỉnh tiếng, dải âm lượng được so với ngưỡng của xưởng và khoảng của phong cách (nếu có).
2. **Given** phim đã có phụ đề đạt, **When** làm gói đăng, **Then** phụ đề của gói đăng giống phụ đề của phim từng dòng.
3. **Given** làm gói đăng, **When** chụp thumbnail, **Then** khung được vẽ không có phụ đề và thẻ chữ của phim. Chữ trên thumbnail chỉ là chữ của gói đăng.
4. **Given** một phim đã qua tầng 1–4, **When** chạy `qc` như hiện nay, **Then** không còn lỗi nhịp nào (cắt, cảnh chứa câu cuối, lặng, đuôi), nên không phải render lại vì nhịp.

### Edge Cases

- **Phim không xuất danh sách cảnh** (phim cũ, phim của thư viện): kiểm kế hoạch dò mốc cắt từ một bản xem trước độ phân giải thấp, hoặc báo "không có danh sách cảnh" và chỉ chạy các luật không cần cảnh.
- **Một cảnh cố ý phẳng hoặc tối** (thẻ chữ, khoảnh khắc tắt đèn có chủ đích): người làm phim đánh dấu cảnh đó là ngoại lệ, kèm lý do; ngoại lệ hiện trong báo cáo.
- **Dòng giọng do người dùng tự thu**: kiểm giọng vẫn chạy, nhưng chỉ báo, không đề nghị tạo lại.
- **Phim rất ngắn (dưới 30 s)**: luật lặng và luật cắt mỗi phút dùng ngưỡng theo phim ngắn của `qc` hiện nay.
- **Không có GPU**: kiểm hình theo cảnh vẫn chạy bằng phần mềm (≈ 1 s mỗi ảnh). Lệnh báo trước thời gian ước tính.
- **Chế độ online**: worker chạy đủ các tầng như máy phát triển. Báo cáo của mỗi tầng hiện trên trang việc.
- **Phụ đề của phim chưa đạt**: gói đăng báo lỗi và chỉ về kiểm kế hoạch, không tự cắt lại phụ đề.

## Requirements *(mandatory)*

### Functional Requirements

**Tầng 0: giọng**

- **FR-001**: Xưởng PHẢI có lệnh kiểm giọng chạy ngay sau khi tạo giọng. Lệnh báo khoảng nghỉ ≥ 0,8 s bên trong một dòng, từ nhận dạng lệch kịch bản, và độ lệch giữa độ dài file và từ cuối (> 0,5 s). Mỗi lỗi ghi mã dòng và thời điểm.
- **FR-002**: Cả xưởng PHẢI dùng một mô hình nhận dạng giọng duy nhất cho tiếng Anh (và một cho mỗi ngôn ngữ khác), ghi rõ ở một chỗ. Mọi lệnh cần mốc từ đều dùng nó.
- **FR-003**: Ranh giới câu PHẢI được tính từ kịch bản đã đạt (dấu câu của kịch bản), gắn lên mốc từ của bản nhận dạng. Dấu câu của công cụ nhận dạng không được dùng để xác định câu.
- **FR-004**: Mốc bắt đầu âm của một từ PHẢI được tính là 0. Mốc kết thúc vượt độ dài file PHẢI được tính bằng độ dài file.

**Tầng 1: kế hoạch**

- **FR-005**: Xưởng PHẢI có lệnh kiểm kế hoạch, chạy không cần video, trên: danh sách cảnh (mã, bắt đầu, kết thúc), mốc câu (FR-003), dòng thời gian, phụ đề, và chữ trên màn hình theo cảnh.
- **FR-006**: Kiểm kế hoạch PHẢI áp dụng đúng các luật nhịp mà `qc` hiện áp dụng, với cùng ngưỡng:
  - cắt không nằm giữa câu, và cách lúc câu dứt ≥ 0,4 s (hoặc đúng lúc câu sau bắt đầu, nếu khoảng nghỉ ngắn hơn);
  - cảnh chứa từ cuối của mỗi đoạn dài ≥ 2,5 s;
  - lặng ≤ 20%;
  - khoảng nghỉ ≥ 0,8 s chỉ nằm giữa hai đoạn;
  - đuôi phim ≤ 1,5 s.
  
  Ngoài ra PHẢI áp dụng: cảnh dài từ 1,1 s đến mức tối đa của phong cách (mặc định 6 s); mỗi phụ đề hiện ≥ max(1,8 s, thời gian nói + 0,6 s); mỗi thẻ chữ hiện đủ thời gian đọc theo luật đọc của thư viện.
- **FR-007**: Mỗi lỗi PHẢI có mã cảnh (hoặc mã dòng hay phụ đề), thời điểm, luật, số đo, ngưỡng. Lỗi cắt cảnh PHẢI kèm mốc sớm nhất hợp lệ để cắt.
- **FR-008**: Kiểm kế hoạch PHẢI xong trong 10 giây với phim 10 phút.
- **FR-009**: Lệnh ghi video PHẢI từ chối chạy khi kiểm kế hoạch, hoặc các luật khung của kiểm hình theo cảnh (FR-012), chưa đạt cho đúng nguồn phim hiện tại. Lệch phong cách (FR-013) không chặn. Có một cờ bỏ qua rõ ràng; khi dùng cờ đó, nhật ký và kết quả kiểm PHẢI ghi lại.
- **FR-010**: Luật nhịp của tầng 1 và của `qc` sau khi ghép tiếng PHẢI là cùng một bộ luật, để một kế hoạch đã đạt tầng 1 thì không bị `qc` báo lỗi nhịp sau đó (SC-005).

**Tầng 2: mỗi cảnh một ảnh**

- **FR-011**: Xưởng PHẢI có lệnh kiểm hình theo cảnh: chụp một ảnh ở giữa mỗi cảnh, và với cảnh có thẻ chữ thì chụp thêm lúc thẻ hiện rõ nhất.
- **FR-012**: Mỗi ảnh PHẢI được đo:
  - khung phẳng: một màu chiếm > 60% khung, hoặc độ lệch độ sáng quá thấp; chữ trên màn hình không tính vào vùng phẳng;
  - quá tối hoặc cháy sáng theo ngưỡng của phong cách, hoặc ngưỡng mặc định;
  - chữ thiếu phông;
  - chữ trên màn hình đè lên vùng phụ đề.
- **FR-013**: Khi phong cách có số đo (khoảng độ sáng trung vị, độ bão hoà trung vị, số lần cắt mỗi phút, dải âm lượng), xưởng PHẢI so phim với các khoảng đó. Ngoài khoảng là **cảnh báo**, không chặn. Lệnh ghi video chạy được khi người làm phim ghi một dòng lý do (ví dụ "cố ý tối hơn cho phim đêm"). Lý do được lưu vào kết quả kiểm, và báo cáo cuối liệt kê mọi cảnh báo phong cách còn mở. Không có số đo thì báo "bỏ qua so phong cách".
- **FR-014**: Kiểm hình theo cảnh PHẢI tạo một bảng ảnh: mỗi ô ghi mã cảnh, cảnh lỗi được đánh dấu.
- **FR-015**: Người làm phim PHẢI đánh dấu được một cảnh là ngoại lệ cho một luật cụ thể, kèm lý do. Ngoại lệ PHẢI hiện trong báo cáo. Không được miễn trừ cả phim bằng một lệnh.

**Tầng 3: trong lúc render**

- **FR-016**: Mỗi đoạn vừa ghi xong (specs/019) PHẢI được kiểm khung đen và hình đứng yên quá ngưỡng. Đoạn lỗi làm lệnh dừng, báo mã cảnh và thời điểm, giữ các đoạn đã đạt. Có cờ "ghi hết rồi báo".

**Tầng 4 và gói đăng**

- **FR-017**: Kiểm cuối PHẢI so dải âm lượng với khoảng của phong cách (nếu có), bên cạnh các luật âm lượng và đỉnh tiếng hiện có.
- **FR-018**: Gói đăng PHẢI dùng phụ đề đã đạt của phim (cùng dòng, cùng mốc), không tự cắt lại. Phụ đề của phim chưa đạt thì gói đăng báo lỗi.
- **FR-019**: Thumbnail PHẢI được chụp khi trang phim không hiện phụ đề và thẻ chữ của phim.

**Luồng làm phim**

- **FR-020**: Luồng làm phim trong `CLAUDE.md` và hướng dẫn cho worker của app PHẢI chạy các tầng theo thứ tự: kiểm giọng → kiểm kế hoạch → kiểm hình theo cảnh → ghi video (kèm tầng 3) → ghép tiếng → kiểm cuối → gói đăng.
- **FR-021**: Kết quả của mọi tầng PHẢI được ghi vào kết quả kiểm của phim (`checks.json` và `CHECKS.md`), mỗi tầng một mục, có mã nguồn phim mà tầng đó đã kiểm.
- **FR-022**: Xưởng KHÔNG ĐƯỢC sửa file nào trong thư viện gốc.

### Key Entities

- **Cảnh**: mã (ví dụ `P27.2`), bắt đầu, kết thúc, đoạn kịch bản, thẻ chữ (nếu có), ngoại lệ đã đánh dấu.
- **Câu**: mã đoạn, thứ tự trong đoạn, mốc bắt đầu và kết thúc (từ kịch bản gắn lên mốc từ).
- **Lỗi**: tầng, mã cảnh hoặc dòng, thời điểm, luật, số đo, ngưỡng, gợi ý sửa.
- **Kết quả tầng**: tầng, đạt hay không, dấu vân tay nguồn phim, thời điểm, danh sách lỗi, danh sách ngoại lệ.
- **Số đo phong cách**: các khoảng mà phong cách cung cấp (độ sáng, bão hoà, cắt mỗi phút, dải âm lượng, độ dài cảnh tối đa).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Trên phim thử có 10 lỗi nhịp cài sẵn, kiểm kế hoạch báo đủ 10, đúng mã cảnh, không báo nhầm lỗi nào, xong trong 10 giây.
- **SC-002**: Trên `pet-swap` với kế hoạch cuối (đã đạt `qc`), kiểm kế hoạch báo 0 lỗi nhịp. Trên `pet-swap` với quy tắc cắt của lần render đầu (mỗi lần cắt sớm 0,06 s trước câu, cảnh đầu đoạn bắt đầu ở giữa khoảng nghỉ), tái tạo trên dòng thời gian của lần đó, kiểm kế hoạch báo ít nhất 80 lỗi cắt và mọi cảnh chứa câu cuối ngắn hơn 2,5 s.
- **SC-003**: Trên phim thử có 6 cảnh cài lỗi hình, kiểm hình theo cảnh báo đủ 6, báo nhầm không quá 1 trên 30 cảnh tốt. Trên `pet-swap` (192 cảnh), lệnh xong trong 3 phút với GPU.
- **SC-004**: Với phong cách Dusk Hypothetical, kiểm phong cách trên `pet-swap` báo độ sáng trung vị (0,13) và độ bão hoà (0,53) nằm ngoài khoảng (0,20–0,30 và 0,32–0,50).
- **SC-005**: Một phim đã đạt tầng 1–3 thì khi chạy `qc` sau khi ghép tiếng có 0 lỗi nhịp, tức 0 lần render lại vì nhịp.
- **SC-006**: Hai lần kiểm liền trên cùng giọng cho chỉ số lặng và mốc câu giống hệt nhau. Không còn lỗi cắt giả do dấu câu của công cụ nhận dạng (kiểm trên 2 ca thử ở US3).
- **SC-007**: Kiểm giọng báo một khoảng nghỉ 0,9 s cài sẵn trong một dòng, xong trong 30 giây với 70 dòng.
- **SC-008**: Gói đăng của `pet-swap` có 0 dòng phụ đề dưới 1 giây. Ba thumbnail không có chữ của phụ đề.
- **SC-009**: Ghi video một phim thử có cảnh đứng yên 8 giây ở giữa: lệnh dừng trong vòng 1 đoạn sau đoạn lỗi, giữ các đoạn trước.
- **SC-010**: Không file nào trong `lib/` bị đổi.

## Assumptions

- Trang phim xuất danh sách cảnh có mã (như `window.SHOTS` của `pet-swap`). Phim mới làm theo luồng của xưởng sẽ có nó. Phim cũ không có thì theo edge case "không xuất danh sách cảnh".
- Số đo của phong cách lấy từ `EVIDENCE.md` hoặc `style.json` của phong cách học được. Phong cách thư viện chưa có số đo thì bỏ qua phần so phong cách.
- Mô hình nhận dạng chung của xưởng là mô hình cho mốc từ chính xác hơn trong hai mô hình đã thử ở `pet-swap`, sẽ chốt ở bước plan. Đổi mô hình thì phải chạy lại kiểm giọng của phim đang làm.
- Ngưỡng nhịp giữ nguyên như `qc` hiện nay (specs/010). Tính năng chỉ đổi lúc chạy và cách xác định câu, không đổi luật.
- Kiểm hình theo cảnh dùng cách dựng hình của specs/019 (GPU nếu có).
- "Khung phẳng" là phép đo dựa trên ngưỡng nên có thể báo nhầm. Ngoại lệ có lý do (FR-015) là lối thoát, không phải tắt cả luật.
