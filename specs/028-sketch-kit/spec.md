# Feature Specification: Bộ dựng SVG cho phong cách Sketch Explainer

**Feature Branch**: `028-sketch-kit`

**Created**: 2026-11-19

**Status**: Draft

**Input**: User description: "Đóng gói bộ vẽ hoạt hình 2D SVG thành bộ dựng (kit/) của phong cách đã học my-styles/sketch-explainer, để phim mới theo phong cách này chỉ cần `sh bin/studio kit use <phim>` rồi viết bảng cảnh. Mã nguồn hiện chỉ nằm trong films/anthropic-ipo-15/ và films/jensen-out. Gồm: bố cục và danh mục bộ dựng như specs/022; khớp số đo của phong cách (nét viền 0,45–0,6% bề ngang, không bàn chân, màu xám dịu với đỏ và xanh lá mang nghĩa, người phụ mặt trắng, máy đẩy hoặc kéo thẳng có dịch nhẹ và giữ cuối cảnh, khoảng 24 bối cảnh trong 3 phút dựng từ phần, khoảng nửa số cảnh là trung cảnh, mỗi ~2,4 giây có một hành động); thư viện vai (vai chung trong bộ dựng, người thật để riêng từng phim kèm bước duyệt bảng mẫu, người thật không nói lời bịa); luật an toàn GPU có test; phim mẫu ngắn trong my-styles/sketch-explainer qua tầng 1–4; sửa soundcraft.py chỉ đo tiếng động trong đoạn đã đo. Ngoài phạm vi: bộ dựng 3D (spec 027), điểm duyệt trang việc (spec 026)."

## Clarifications

### Session 2026-11-19

- Q: Người thật đã vẽ và duyệt (như Jensen, Dario) để trong thư viện chung của xưởng để phim sau dùng lại, hay vẽ và duyệt riêng ở từng phim? → A: Thư viện chung của xưởng (vào git), ngoài phong cách; phim chọn người theo tên; người đã duyệt thì không duyệt lại; sửa hình thì phải duyệt lại.

## Bối cảnh

- Phong cách `sketch-explainer` đã được học bằng đo (12 video, khung chứng minh đạt mọi chỉ số), lưu ở `my-styles/sketch-explainer/` với `STYLE.md`, `EVIDENCE.md`, `shots.json` và một khung chứng minh.
- Hai phim `jensen-out` và `anthropic-ipo-15` đã làm bằng một bộ vẽ SVG tự viết trong thư mục phim: khung nhân vật (tư thế, biểu cảm, quay 3/4, sau lưng), thư viện vai người thật biếm hoạ, cảnh `act` (bối cảnh, bảng, biển cầm tay, bong bóng, cử chỉ tự đổi, cận mặt). `films/` không vào git, nên bộ vẽ chưa dùng lại được và dễ mất.
- Bộ vẽ hiện lệch số đo của phong cách ở vài chỗ: nét viền mỏng hơn (~0,36% bề ngang), nhân vật có giày, màu rực hơn (bão hoà cao hơn ~0,12 của phong cách), máy đẩy có tăng tốc và không giữ cuối cảnh, ít bối cảnh (phòng bảng dùng lại nhiều), 68% toàn cảnh thay vì ~47% trung cảnh.
- Specs/022 đã có cơ chế bộ dựng cho phong cách 3D (`kit/`, `catalog.json`, `kit use`). Spec này dùng lại cơ chế đó cho phong cách 2D SVG.
- Lúc học phong cách phát hiện công cụ đo âm thanh đếm lời nói ngoài đoạn đo thành tiếng động (19–62/phút thay vì ~16/phút).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bộ dựng dùng lại của phong cách (Priority: P1)

Người làm phim (agent của xưởng) chọn phong cách Sketch Explainer cho một phim mới. Họ chạy `kit use`, đọc danh mục, rồi chỉ viết bảng cảnh: mỗi cảnh ghi bối cảnh, người trong cảnh, tư thế, biểu cảm, bảng hoặc biển số liệu, bong bóng, theo tên trong danh mục. Họ không viết lại nhân vật, bối cảnh, máy quay hay đồ hoạ.

**Why this priority**: Đây là giá trị chính: phim sau làm nhanh, đúng phong cách, không phải chép tay mã từ phim cũ.

**Independent Test**: Tạo một phim thử, chạy `kit use`, viết bảng cảnh 6 cảnh chỉ dùng tên trong danh mục, chạy trang phim: trang dựng được mọi cảnh, xuất đúng `SHOTS`, `CARDS`, `TEXTS`, tôn trọng `CLEAN`.

**Acceptance Scenarios**:

1. **Given** phim mới gắn phong cách `sketch-explainer`, **When** chạy `sh bin/studio kit use <phim>`, **Then** `films/<phim>/kit/` có bộ dựng và danh mục, và trang phim không với tới `my-styles/`.
2. **Given** bảng cảnh chỉ dùng tên trong danh mục, **When** mở trang phim ở thời điểm bất kỳ, **Then** khung hình dựng xong không lỗi và `window.READY` bật.
3. **Given** bảng cảnh ghi một tên không có trong danh mục, **When** dựng, **Then** xưởng báo rõ cảnh nào, tên nào sai, và gợi ý tên gần nhất.
4. **Given** bối cảnh cần không có sẵn, **When** bảng cảnh ghi `custom:<tên>` ghép từ các phần của bộ dựng, **Then** cảnh dựng được và được ghi rõ trong bảng cảnh.

---

### User Story 2 - Hình khớp số đo của phong cách (Priority: P1)

Phim dựng bằng bộ dựng nhìn và chuyển động như kênh mẫu theo số đo: nét viền, màu, dáng người, máy quay, nhịp hành động, cỡ cảnh, số bối cảnh.

**Why this priority**: Phong cách được học bằng đo (hiến pháp VIII); bộ dựng lệch số đo thì phim lệch phong cách, như phim Anthropic đã bị nhận xét.

**Independent Test**: Dựng phim thử 60 giây từ bộ dựng theo một bảng cảnh mẫu, chạy `qc shots` và đo phim: các chỉ số nằm trong khoảng của `shots.json` và `EVIDENCE.md`.

**Acceptance Scenarios**:

1. **Given** một nhân vật ở trung cảnh, **When** đo nét viền, **Then** nét bằng 0,45–0,6% bề ngang khung và nét chi tiết bối cảnh khoảng một nửa.
2. **Given** bất kỳ nhân vật nào, **When** xem chân, **Then** chân kết thúc bằng một nét, không có bàn chân hay giày; dưới chân có bóng elip mờ.
3. **Given** phim thử, **When** đo màu, **Then** độ bão hoà trung vị trong khoảng của phong cách, và đỏ, xanh lá chỉ xuất hiện ở chỗ mang nghĩa (lỗ, nguy hiểm, tiền, tăng trưởng).
4. **Given** người phụ không tên, **When** dựng, **Then** mặt trắng; người chính và người thật có màu da và màu tóc.
5. **Given** một cảnh có máy chạy, **When** đo, **Then** máy đi thẳng (không tăng tốc), có dịch nhẹ, giữ yên ở cuối cảnh theo tỉ lệ đặt sẵn; tỉ lệ khung đứng yên và độ dịch mỗi khung nằm trong khoảng kênh mẫu.
6. **Given** một cảnh dài 6 giây trở lên, **When** xem, **Then** có 2–3 hành động (cử chỉ, đổi biểu cảm, đồ hoạ dựng lên, bước vào), mỗi khoảng 2–3 giây một hành động; không nhân vật nào đứng đơ cả cảnh.
7. **Given** bảng cảnh mẫu của bộ dựng (phim 3 phút), **When** đếm, **Then** khoảng 47% trung cảnh, không quá 4 cảnh liền cùng cỡ, và khoảng 20–28 bối cảnh khác nhau.

---

### User Story 3 - Vai và luật người thật (Priority: P2)

Bộ dựng có sẵn các vai chung (người dẫn, banker, kiểm toán, trader, nhà phê bình, quan chức, nhân viên, người phụ mặt trắng). Người thật được vẽ biếm hoạ một lần vào thư viện người thật chung của xưởng, qua bước duyệt bảng mẫu trước khi dựng cảnh; phim sau chọn người theo tên và dùng lại. Người thật không bao giờ nói lời bịa.

**Why this priority**: Phim kiểu này luôn có người thật; vẽ sai hoặc gán lời bịa là lỗi nặng về độ tin cậy. Nhưng bộ dựng vẫn chạy được với vai chung trước khi có phần này.

**Independent Test**: Thêm một người thật mới vào thư viện cho phim thử: xưởng tạo bảng mẫu cạnh ảnh tham chiếu, chặn dựng cảnh tới khi bảng mẫu được duyệt; phim thứ hai chọn cùng người thì dựng ngay, không duyệt lại; bảng cảnh gán lời không có nguồn cho người thật thì bị báo lỗi.

**Acceptance Scenarios**:

1. **Given** phim cần một người thật chưa có trong thư viện, **When** tạo vai, **Then** vai nằm trong thư viện người thật của xưởng (không trong bộ dựng của phong cách, không trong thư mục phim) và có bảng mẫu đặt cạnh ảnh tham chiếu.
2. **Given** người thật đã duyệt trong thư viện, **When** một phim khác chọn người đó theo tên, **Then** phim dựng được ngay, không cần duyệt lại.
3. **Given** hình của một người thật đã duyệt bị sửa, **When** kiểm kế hoạch, **Then** người đó trở về trạng thái chưa duyệt cho tới khi bảng mẫu mới được duyệt.
4. **Given** bảng mẫu chưa được duyệt, **When** chạy kiểm kế hoạch hoặc dựng, **Then** xưởng báo người thật nào chưa duyệt và không cho dựng.
5. **Given** bong bóng của người thật chứa chữ, **When** kiểm kế hoạch, **Then** xưởng báo lỗi, trừ khi chữ đó là trích dẫn có trong `SOURCES.md`; ký hiệu (!, ?, $) luôn được phép.
6. **Given** vai chung hoặc người hư cấu, **When** có bong bóng chữ, **Then** được phép.

---

### User Story 4 - An toàn khi dựng bằng GPU (Priority: P2)

Mọi hình của bộ dựng hiện đúng khi ghi bằng GPU của máy: không mất phần tô, không vệt chéo.

**Why this priority**: Hai phim trước đã phải render lại vì lỗi chỉ xuất hiện trên GPU (cung tròn không được tô, khung bo góc vỡ, vệt chữ X trên viền dày).

**Independent Test**: Một test quét mã và danh mục bộ dựng, và một lượt chụp danh mục bằng GPU so với bản chụp phần mềm.

**Acceptance Scenarios**:

1. **Given** mã của bộ dựng, **When** chạy test, **Then** không có lệnh cung tròn trong đường tô, không có góc bo kiểu `rx`, không có đường viền dày một nét gấp khúc cho hình tô.
2. **Given** trang danh mục, **When** chụp bằng GPU và bằng phần mềm, **Then** hai ảnh khớp nhau trong ngưỡng đặt sẵn.

---

### User Story 5 - Phim mẫu của phong cách (Priority: P3)

Phong cách có phim mẫu ngắn làm bằng bộ dựng, câu chuyện riêng, đi đủ luồng làm phim, để người dùng xem phong cách và agent đọc làm mẫu.

**Why this priority**: Chứng minh bộ dựng chạy trọn luồng; làm sau khi bộ dựng xong.

**Independent Test**: Phim mẫu qua tầng 1–4 của specs/020 và kiểm cách quay của specs/021 không cảnh báo ngoài khoảng.

**Acceptance Scenarios**:

1. **Given** bộ dựng xong, **When** làm phim mẫu, **Then** `my-styles/sketch-explainer/` có `DEMO.md`, `demo/` (mã nguồn, `CREDITS`, `build.sh` có `LIB=` ở đầu), `demo-checks.json`; `test.jpg` và `test.mp4` không vào git.
2. **Given** phim mẫu, **When** chạy các tầng kiểm, **Then** đạt tầng 1–4, `qc shots` không có cảnh báo cách quay ngoài khoảng.

---

### User Story 6 - Đo tiếng động đúng (Priority: P3)

Khi học phong cách, số tiếng động mỗi phút chỉ đếm trong các đoạn đã đo, nên không lẫn lời nói ngoài đoạn.

**Why this priority**: Sai số này làm luật âm thanh của mọi phong cách học sau bị lệch; sửa nhỏ, độc lập.

**Independent Test**: Chạy công cụ đo âm thanh trên một video thử có lời nói ngoài đoạn đo: số tiếng động không tính các tiếng ngoài đoạn.

**Acceptance Scenarios**:

1. **Given** video có lời nói ngoài các đoạn đo, **When** đo âm thanh, **Then** tiếng động mỗi phút chỉ tính trong các đoạn đo, chia cho tổng thời lượng các đoạn.
2. **Given** bộ `sketch-ref` đã đo, **When** tính lại từ số liệu đã lưu, **Then** trung vị gần 16/phút như đã đếm tay ở bước kiểm chéo.

### Edge Cases

- Bảng cảnh ghi bối cảnh không có và không ghi `custom:`: báo lỗi kèm tên gần nhất, không dựng cảnh trống.
- Chữ trên bảng hoặc biển dài quá khung: chữ tự thu nhỏ để vừa, không tràn.
- Phim cũ (`jensen-out`, `anthropic-ipo-15`) dựng bằng bộ vẽ cũ trong thư mục phim: vẫn chạy như trước, không bị bộ dựng mới làm hỏng.
- Bộ dựng được cập nhật sau khi phim đã `kit use`: phim giữ bản đã chép; `kit use --update` mới lấy bản mới, như specs/022.
- Người thật không có ảnh tự do: bảng mẫu ghi "không có ảnh tham chiếu", vẫn phải được duyệt.
- Phim đã dựng xong rồi người thật trong thư viện bị sửa hình: phim cũ giữ bản đã dùng (ghi dấu phiên bản của người đó lúc dựng), không tự đổi.
- Phim không gắn kênh: nhân vật dẫn chuyện dùng mặc định của bộ dựng.

## Requirements *(mandatory)*

### Functional Requirements

**Bộ dựng và danh mục (US1)**

- **FR-001**: Phong cách MUST có bộ dựng dùng lại trong `my-styles/sketch-explainer/kit/`, chép vào phim bằng `kit use` hiện có, nạp được theo hợp đồng trang của thư viện (`window.render(t)`, `window.READY`, `window.DUR`, `window.SHOTS`, `window.CARDS`, `window.TEXTS`, `window.CLEAN`), không sửa `lib/`.
- **FR-002**: Bộ dựng MUST có danh mục máy đọc được, liệt kê tên các bối cảnh, phần bối cảnh, vai chung, tư thế, biểu cảm, loại bảng, loại biển, đạo cụ, loại chuyển cảnh, và một trang danh mục (mỗi mục một ô) để xem và kiểm bằng `qc shots`.
- **FR-003**: Trang phim MUST chỉ cần một bảng cảnh: mỗi cảnh ghi bối cảnh, người (vai, vị trí, cỡ, tư thế, biểu cảm, lời ra mặt), bảng hoặc biển số liệu, bong bóng, đạo cụ, cách đặt máy, chú thích; bộ dựng lo nhân vật, bối cảnh, máy, cử động, đồ hoạ.
- **FR-004**: Tên sai trong bảng cảnh MUST bị báo khi kiểm kế hoạch (tầng 1), kèm mã cảnh và tên gần nhất.
- **FR-005**: Bảng cảnh MUST ghép được bối cảnh mới từ phần của bộ dựng bằng `custom:<tên>`.
- **FR-006**: Bộ dựng MUST có ít nhất 24 bối cảnh dựng sẵn hoặc ghép từ phần (văn phòng, phòng họp, phòng bảng trắng, phòng bảng đen, phòng TV, trường quay tin, sân khấu, sàn giao dịch, phố ban ngày, phố đêm, toà nhà chính phủ, trụ sở công ty, nhà máy, trung tâm dữ liệu, ngân hàng hoặc két, phòng xử án hoặc điều trần, nhà ở, sạp hàng, bản đồ, nền tối có đèn rọi, và các bối cảnh khác), để phim 3 phút có thể đổi bối cảnh mỗi ~4 giây.

**Khớp số đo của phong cách (US2)**

- **FR-007**: Nét viền MUST là `#1a191a`, đầu và góc tròn, dày 0,45–0,6% bề ngang khung cho người ở trung cảnh, đổi theo cỡ người; nét chi tiết bối cảnh khoảng một nửa.
- **FR-008**: Nhân vật MUST có đầu gần tròn không cổ ≈ 1/3 chiều cao, thân hình hạt đậu, tay chân một nét không bàn tay bàn chân, bóng elip mờ dưới chân, bóng lưỡi liềm một bên đầu; mặt có hai mắt bầu đen, lông mày một nét mang cảm xúc, miệng nhỏ, thường không mũi.
- **FR-009**: Màu MUST theo luật mục 3 của `STYLE.md`: nền xám dịu, bối cảnh xám và ít tương phản hơn người, đỏ và xanh lá chỉ cho nghĩa lỗ hoặc nguy hiểm và tiền hoặc tăng trưởng; người phụ mặt trắng, người chính và người thật có màu da.
- **FR-010**: Máy MUST đi thẳng không tăng tốc, có tuỳ chọn dịch nhẹ và giữ yên ở cuối cảnh; mặc định theo tỉ lệ đo được (đẩy vào ~33%, kéo ra ~23%, đứng ~22%, lia ~10–20% số cảnh; đẩy ~3,3%/giây) và cảnh liền nhau đổi giữa đẩy và kéo.
- **FR-011**: Bộ dựng MUST lên lịch hành động trong cảnh: hành động đầu ngay sau lần cắt, sau đó mỗi 2–3 giây một hành động (cử chỉ, đổi biểu cảm, chớp mắt, đồ hoạ dựng lên, chữ hiện dần, ký hiệu bật lên, bước vào), giữ tư thế giữa các hành động; không nhân vật nào đứng đơ cả cảnh.
- **FR-012**: Bộ dựng MUST có các cách đặt máy của `shots.json`: trung, toàn, rất rộng, cận, đặc tả, qua vai có bóng tối tiền cảnh, cảnh chèn đồ hoạ; và một trợ giúp gợi ý cỡ cảnh để bảng cảnh giữ khoảng 47% trung cảnh, đổi cỡ ở ~2/3 lần cắt, không quá 4 cảnh liền cùng cỡ.
- **FR-013**: Đồ hoạ MUST là vật trong cảnh: bảng trắng, bảng đen, TV, giấy tờ có con dấu, báo, biển cầm tay, bong bóng, bong bóng suy nghĩ, thẻ chương nền gần đen chữ trắng viết tay, số lớn xanh lá đếm lên; chữ khai báo trong `window.CARDS` và `TEXTS`, tự thu nhỏ để vừa khung.
- **FR-014**: Chuyển cảnh MUST mặc định là cắt thẳng; hoà cảnh 0,4–0,6 giây chỉ khi bảng cảnh ghi nhảy thời gian hoặc nơi chốn.

**Vai và người thật (US3)**

- **FR-015**: Bộ dựng MUST có các vai chung: người dẫn chuyện (trang phục lấy từ hồ sơ kênh nếu có, như specs/022 FR-015), banker, kiểm toán, trader, nhà phê bình, quan chức chung chung, nhân viên, người phụ mặt trắng, và cách tạo biến thể (tóc, kính, mũ, màu áo).
- **FR-016**: Người thật MUST nằm trong một thư viện người thật chung của xưởng (vào git, ngoài phong cách và ngoài thư mục phim); mỗi người có hình vẽ, bảng mẫu (hình vẽ cạnh ảnh tham chiếu nếu có), nguồn và giấy phép của ảnh tham chiếu, trạng thái duyệt và dấu phiên bản. Phim chọn người theo tên; người đã duyệt không phải duyệt lại; sửa hình MUST đưa người đó về chưa duyệt. Hai phim cũ chuyển các người thật đã duyệt (vd. Jensen và bộ vai đã duyệt của phim Anthropic) vào thư viện.
- **FR-017**: Kiểm kế hoạch MUST chặn khi phim dùng người thật chưa được duyệt bảng mẫu.
- **FR-018**: Bong bóng chữ của người thật MUST bị chặn ở kiểm kế hoạch, trừ khi chữ khớp một trích dẫn trong `SOURCES.md`; ký hiệu luôn được phép.

**An toàn GPU (US4)**

- **FR-019**: Mã bộ dựng MUST không dùng lệnh cung tròn trong đường tô, không dùng góc bo `rx`, không vẽ viền dày một nét gấp khúc cho hình tô (vẽ thành đoạn rời); một test MUST quét để chặn.
- **FR-020**: Trang danh mục chụp bằng GPU và bằng phần mềm MUST khớp trong ngưỡng đặt sẵn; lệch thì test báo ô nào.

**Phim mẫu (US5)**

- **FR-021**: Phong cách MUST có phim mẫu làm bằng bộ dựng: câu chuyện riêng, đi đủ luồng làm phim của `CLAUDE.md` (kịch bản được chấm, các tầng kiểm), không làm gói đăng; `DEMO.md`, `demo/`, `demo-checks.json` theo mẫu của thư viện; mục 10 của `STYLE.md` trỏ tới `demo/` và bộ dựng.

**Đo tiếng động (US6)**

- **FR-022**: Công cụ đo âm thanh của skill học phong cách MUST chỉ đếm tiếng động và cửa sổ nhạc trong các đoạn đã đo, và chia cho tổng thời lượng các đoạn đó.

**Bản quyền và luật chung**

- **FR-023**: Bộ dựng, phim mẫu và danh mục MUST NOT chứa tên kênh tham chiếu, tên người thật (người thật chỉ nằm trong thư viện người thật), tiêu đề video hay câu thoại của kênh tham chiếu; `check-names` MUST đạt trên mọi tệp chữ của bộ dựng và phim mẫu.
- **FR-024**: Phim cũ dựng bằng bộ vẽ trong thư mục phim MUST vẫn chạy như trước.

### Key Entities

- **Bộ dựng (kit)**: mã dựng nhân vật, bối cảnh, máy, đồ hoạ, cử động của phong cách; có phiên bản (dấu băm) như specs/022.
- **Danh mục (catalog)**: tên mọi mục dùng được trong bảng cảnh, kèm tham số và mô tả ngắn.
- **Bảng cảnh (scene table)**: danh sách cảnh của một phim, mỗi cảnh ghi bối cảnh, người, đồ hoạ, máy, chú thích theo tên trong danh mục.
- **Vai (role)**: hình nhân vật dùng lại; vai chung thuộc bộ dựng, người thật thuộc thư viện người thật của xưởng.
- **Người thật (person)**: một mục trong thư viện người thật: tên, hình vẽ, bảng mẫu, ảnh tham chiếu (chỉ để so, không vào phim), nguồn và giấy phép ảnh, trạng thái duyệt, dấu phiên bản.
- **Bảng mẫu (model sheet)**: ảnh hình vẽ người thật cạnh ảnh tham chiếu, kèm trạng thái duyệt.
- **Hành động (event)**: một thay đổi trong cảnh (cử chỉ, biểu cảm, đồ hoạ, bước vào) có thời điểm và độ dài.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Một phim mới theo phong cách này dựng được chỉ bằng bảng cảnh: phần mã viết riêng cho phim (ngoài bảng cảnh và vai người thật) bằng 0 dòng.
- **SC-002**: Phim thử 60 giây dựng từ bộ dựng có nét viền, độ bão hoà, tỉ lệ khung đứng yên, độ dịch mỗi khung và phần thời gian có cử động đều nằm trong khoảng kênh mẫu ghi ở `EVIDENCE.md`.
- **SC-003**: Bảng cảnh mẫu 3 phút của bộ dựng có 40–55% trung cảnh, không quá 4 cảnh liền cùng cỡ, và 20–28 bối cảnh khác nhau.
- **SC-004**: Trong phim thử, mọi cảnh dài từ 4 giây có ít nhất một hành động sau giây đầu tiên, và cảnh dài từ 6 giây có ít nhất hai.
- **SC-005**: Test an toàn GPU chặn được 100% các mẫu lỗi đã gặp (cung tròn, góc bo, viền gấp khúc dày) và trang danh mục chụp GPU khớp bản phần mềm.
- **SC-006**: Người thật chưa duyệt bảng mẫu, hoặc người thật có bong bóng chữ không nguồn, bị chặn ở tầng 1 trong 100% trường hợp thử.
- **SC-007**: Phim mẫu đạt tầng 1–4 và không có cảnh báo cách quay ngoài khoảng.
- **SC-008**: Đo lại bộ `sketch-ref` cho trung vị tiếng động trong khoảng 12–20 lần/phút (trước khi sửa: 19–62).
- **SC-009**: Năm bộ test của xưởng (`tests/run.sh`, `tests/render/run.sh`, `tests/learn/run.sh`, `tests/ui/run.sh`, `tests/filmcheck/run.sh`) đạt.
- **SC-010**: Phim thứ hai dùng một người thật đã duyệt dựng được mà không cần bước duyệt nào.

## Assumptions

- Dùng lại cơ chế bộ dựng và lệnh `kit use` của specs/022; không đổi định dạng `kit/` của phong cách 3D.
- Mã nguồn khởi đầu lấy từ `films/anthropic-ipo-15/` (`kit.js`, `cast.js`, `scenes3.js`, `film.js`) và phần lõi đã dọn trong `my-styles/sketch-explainer/styleframe/`; vai người thật của hai phim cũ không chép vào bộ dựng mà chuyển vào thư viện người thật.
- Phim mẫu dài 30–60 giây (phong cách chưa có `STRUCTURE.md`, không cần phim dài); giọng đọc mặc định của xưởng.
- Ảnh tham chiếu người thật lấy từ nguồn có giấy phép tự do (như Wikimedia) hoặc do người dùng gửi; chỉ để so khi vẽ, không đưa vào phim.
- Âm lượng giao phim vẫn là −14 LUFS của xưởng; kênh mẫu ở −18 LUFS chỉ ghi làm tham khảo.
- Ngưỡng khớp ảnh GPU và phần mềm đặt ở bước plan.
- Giọng thứ hai cho lời nhân vật nằm ngoài phạm vi (người dùng chưa chọn).
