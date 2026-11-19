# Feature Specification: Bộ code mẫu cho phong cách học được (film kit)

**Feature Branch**: `022-style-film-kit`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User description: "Bộ code mẫu (film kit) cho phong cách học được, để làm phim dài khoảng 10 phút sát kênh tham chiếu. (…) (1) bộ dựng dùng lại trong my-styles/dusk-hypothetical/kit/ (three.js): nhân vật có khớp, tư thế, biểu cảm, tóc/mũ/mũ trùm/dây rút, đồ cầm tay; đám đông tới hàng nghìn; các bộ bối cảnh hay gặp; ánh sáng và hậu kỳ theo số đo đã đạt ở khung chứng minh; bộ đồ hoạ; (2) phim dựng từ kit theo bảng cảnh và STRUCTURE.md, đạt các tầng kiểm specs/020 và cách quay specs/021, dựng 60 fps; (3) skill học phong cách: bỏ luật mục 11 'khác kênh gốc' khi kênh đã chọn theo cấu trúc tham chiếu, cho phép STRUCTURE.md; (4) sửa lỗi learn save chép cả file làm việc; (5) làm lại phim mẫu bằng kit. Không chép nhân vật, câu chữ, tên, giọng hay thumbnail của kênh tham chiếu."

## Clarifications

### Session 2026-11-13

- Q: Phim mẫu mới dài bao nhiêu? → A: Đủ ≈ 10,5 phút theo `STRUCTURE.md`, và chính là phim thử của US2 (FR-011).
- Q: Nhân vật chính của kênh giữ cố định cho mọi phim hay mỗi phim tự chọn? → A: Cố định theo kênh: hồ sơ kênh lưu trang phục nhân vật chính (mặc định đầu trọc, hoodie vàng mù tạt `#d9b23a`, dây rút trắng), mọi phim của kênh dùng chung (FR-015).

## Bối cảnh

Ngày 2026-11-13, phong cách `dusk-hypothetical` được học lại từ 10 video nhiều view nhất của kênh tham chiếu, học trọn từng phim (6.654 s, 2.192 cảnh). Phong cách có thêm `STRUCTURE.md`: khung kịch bản theo màn cho phim khoảng 10,5 phút. Người dùng muốn phim của kênh mình làm theo đúng cách kênh tham chiếu đang làm.

Khung chứng minh (toa tàu lúc hoàng hôn) chỉ đạt sau 9 vòng sửa. Mỗi vòng sửa một thứ mà mọi phim của phong cách đều cần:

| Vòng | Sửa gì | Vì sao phải có sẵn trong bộ dựng |
|---|---|---|
| 1 | Người ngồi mất thân (ghế cao hơn hông) | tư thế ngồi phải đúng sẵn |
| 3–4 | Độ phơi sáng, bão hoà, vignette, bóng đổ | số hậu kỳ đã đo khớp kênh |
| 5 | Người phụ cứng, nhìn thẳng máy | tư thế, đồ cầm tay, quay và nghiêng đầu |
| 6 | Tay chân là ống thẳng | khớp gối, khớp khuỷu |
| 7 | Bố cục cảnh toàn thay vì cảnh trung | chủ thể ở lớp trước, đám đông ở lớp sau, vật che tiền cảnh |
| 8 | Ánh điện thoại làm cháy mặt; đầu trắng; áo trơn | viền nắng ấm, đầu lavender, mũ trùm và dây rút |
| 9 | Thiếu chiều sâu | máy chéo, nhiều lớp người xa dần, trần và cuối phòng có đèn |

Phim mẫu cũ của phong cách (23,6 s, 8 cảnh) làm trước lần học lại: không có đám đông, không có khớp, không theo `STRUCTURE.md`. Một phim 10,5 phút cần khoảng 220 cảnh và 30 bối cảnh. Nếu mỗi phim viết lại nhân vật, bối cảnh và đồ hoạ từ đầu, mỗi phim sẽ lặp lại cả 9 vòng sửa trên.

Hai lỗi phụ gặp khi học lại:
- `learn save` chép cả file làm việc (`label.log`, `pipeline.log`, `review-1.md`, `review-2.md`) từ `references/<set>/style/` vào phong cách; phải xoá tay.
- Skill học phong cách bắt mục 11 phải gợi ý cấu trúc "khác kênh gốc", trái với quyết định của kênh ngày 2026-11-13.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bộ dựng dùng lại của phong cách (Priority: P1)

Người làm phim (Claude, ở luồng làm phim) mở bộ dựng của phong cách và dựng được một cảnh bất kỳ (một bối cảnh có sẵn, nhân vật chính và người phụ ở tư thế cần, đồ hoạ cần) bằng vài dòng mô tả cảnh, không phải viết lại nhân vật, ánh sáng, hậu kỳ hay đồ hoạ. Cảnh dựng ra đã đúng số đo của phong cách.

**Why this priority**: Đây là phần thiếu chính. Không có bộ dựng thì mọi phim 10 phút đều phải lặp lại 9 vòng sửa của khung chứng minh, và chất lượng phụ thuộc vào lần viết tay.

**Independent Test**: Dựng một trang thử chỉ gồm các cảnh mẫu của bộ dựng (mỗi bối cảnh một cảnh, mỗi tư thế, mỗi loại đồ hoạ), chụp ảnh từng cảnh, chạy kiểm hình của phong cách (`qc shots`) và so màu với số đo của phong cách.

**Acceptance Scenarios**:

1. **Given** bộ dựng của `dusk-hypothetical`, **When** dựng mỗi bối cảnh có sẵn ở một cảnh toàn có người phụ, **Then** mỗi ảnh nằm trong khoảng màu, độ sáng, bão hoà của phong cách và không bị `qc shots` báo phẳng, tối, cháy hay mờ.
2. **Given** một nhân vật của bộ dựng, **When** đặt ở từng tư thế (đứng, ngồi, cầm đồ, quay đầu, nghiêng đầu) và từng biểu cảm, **Then** thân, tay, chân liền nhau, có khớp gối và khuỷu, đầu ≈ 1/3 chiều cao, tay cầm đúng đồ vật.
3. **Given** một đám đông 1.000 người trong sân vận động, **When** dựng và ghi một đoạn 10 giây, **Then** đoạn ghi xong trên GPU của xưởng, người phụ phân biệt được bằng màu áo, tóc, mũ.
4. **Given** mỗi loại đồ hoạ của bộ dựng, **When** hiện trên một cảnh, **Then** chữ in hoa có chân màu vàng kem, nằm trong vùng hình (không vào dải đen), và được trang phim khai báo cho các bước kiểm (thẻ chữ, phụ đề).

---

### User Story 2 - Phim dài theo khung kịch bản, dựng từ bộ dựng (Priority: P2)

Người dùng nhờ làm một phim của kênh `dusk-hypothetical`. Claude viết kịch bản theo `STRUCTURE.md`, lập bảng cảnh theo `shots.json`, dựng mọi cảnh bằng bộ dựng, và phim qua đủ các tầng kiểm (specs/020) cùng kiểm cách quay (specs/021), ghi ở 60 fps.

**Why this priority**: Đây là mục đích của bộ dựng: phim đủ dài, sát kênh tham chiếu. Phụ thuộc US1.

**Independent Test**: Làm một phim theo luồng làm phim của `CLAUDE.md` và đối chiếu: các mốc màn của kịch bản so với `STRUCTURE.md`, cỡ cảnh và góc máy so với `shots.json`, kết quả các tầng kiểm, fps của tệp phim.

**Acceptance Scenarios**:

1. **Given** một đề cho kênh, **When** Claude lập bảng cảnh, **Then** mỗi cảnh ghi bối cảnh, tư thế, đồ hoạ từ danh mục của bộ dựng, và mốc các màn nằm trong ±5 điểm % so với `STRUCTURE.md`.
2. **Given** phim đã dựng, **When** chạy `qc plan`, `qc shots`, `render` và `qc`, **Then** không còn lỗi nặng, cách quay không ra ngoài khoảng của phong cách, và tệp phim ở 60 fps.

---

### User Story 3 - Skill học phong cách cho phép theo cấu trúc tham chiếu (Priority: P3)

Khi kênh đã chọn theo cấu trúc của kênh tham chiếu, skill học phong cách ghi khung kịch bản vào `STRUCTURE.md` của phong cách (chỉ cấu trúc, không câu chữ) và mục 11 trỏ tới đó, thay vì bắt gợi ý cấu trúc khác kênh gốc. `learn save` chỉ chép các tệp của phong cách, không chép tệp làm việc.

**Why this priority**: Sửa nhỏ, làm cho lần học sau không phải sửa tay. Không phụ thuộc US1.

**Independent Test**: Chạy `learn save` trên một bộ thử có tệp làm việc trong `style/`; đọc lại skill và chạy thử luồng học trên một kênh đã chọn theo cấu trúc tham chiếu.

**Acceptance Scenarios**:

1. **Given** `references/<set>/style/` có `label.log`, `pipeline.log`, `review-1.md`, `review-2.md`, `.job`, **When** chạy `learn save`, **Then** phong cách đã lưu không có các tệp đó, còn `STRUCTURE.md` (nếu có) được lưu.
2. **Given** kênh có quyết định theo cấu trúc tham chiếu, **When** skill viết mục 11, **Then** mục 11 trỏ tới `STRUCTURE.md` và không đòi cấu trúc khác kênh gốc; kênh không có quyết định đó thì luật cũ vẫn áp dụng.

---

### User Story 4 - Phim mẫu mới của phong cách (Priority: P4)

Phong cách `dusk-hypothetical` có phim mẫu mới dựng hoàn toàn bằng bộ dựng, theo `STRUCTURE.md`, thay cho phim mẫu 23,6 s làm trước khi học lại. `DEMO.md` mô tả phim mẫu theo mẫu của thư viện.

**Why this priority**: Phim mẫu là cách thư viện dạy kỹ thuật cho phim sau. Phụ thuộc US1 và US2.

**Independent Test**: Chạy lệnh dựng phim mẫu (`demo/build.sh`) trên máy sạch và đối chiếu với `DEMO.md`, `demo-checks.json`.

**Acceptance Scenarios**:

1. **Given** phong cách sau tính năng này, **When** chạy lệnh dựng phim mẫu, **Then** ra đúng phim mô tả trong `DEMO.md`, dùng bộ dựng, qua các tầng kiểm, 60 fps.

---

### Edge Cases

- Cảnh cần một bối cảnh không có trong danh mục: dựng từ các phần chung của bộ dựng (sàn, tường, lưới đồ vật, đèn, đám đông); không có bối cảnh hợp thì ghi rõ trong bảng cảnh là bối cảnh tự dựng.
- Đám đông quá lớn làm GPU chậm: bộ dựng giảm chi tiết ở người xa (người xa thành chấm màu) để giữ thời gian dựng.
- Một số liệu hậu kỳ phù hợp cảnh này nhưng làm cảnh khác lệch màu: chỉnh theo cảnh trong khoảng của phong cách, không đổi số mặc định.
- Hồ sơ kênh chưa có trang phục nhân vật chính (kênh cũ): dùng mặc định của bộ dựng và báo một dòng gợi ý đặt bằng `channel set`.
- Phim ngắn (4–7 phút): dùng tỉ lệ "Compressed" của `STRUCTURE.md`.
- Máy không dựng được bằng GPU: bộ dựng vẫn ra hình đúng khi dựng bằng phần mềm, nhưng theo luật xưởng phải dừng và hỏi người dùng trước khi dựng phim bằng phần mềm.

## Requirements *(mandatory)*

### Functional Requirements

**Bộ dựng (US1)**

- **FR-001**: Phong cách MUST có bộ dựng dùng lại trong `my-styles/dusk-hypothetical/kit/`, nạp được từ trang phim theo hợp đồng trang của thư viện (`window.render(t)`, `window.READY`, `window.DUR`, `window.SHOTS`, `window.CARDS`, `window.CLEAN`), không sửa `lib/`.
- **FR-002**: Nhân vật MUST theo luật hình của phong cách: đầu cầu ≈ 1/3 chiều cao, mắt chấm, không mũi tai, áo hoodie có mũ trùm và dây rút, tay chân hai đoạn có khớp gối và khuỷu, bàn tay tròn; MUST có các tư thế đứng, ngồi, đi, cầm đồ (điện thoại, sách, túi, cốc, giấy) và quay, nghiêng đầu; MUST có các biểu cảm của phong cách (chấm, nửa mí, ngạc nhiên, vui, trống, giận, buồn, đổ mồ hôi); MUST có tóc, mũ, kính làm biến thể.
- **FR-003**: Đám đông MUST dựng được từ vài người tới ít nhất 1.000 người trong một cảnh, phân biệt bằng màu áo rồi tóc hoặc mũ; người xa MUST được giảm chi tiết để giữ thời gian dựng.
- **FR-004**: Bộ dựng MUST có ít nhất 8 bối cảnh: phòng học, hành lang tủ khoá, nhà thi đấu, phố hoàng hôn, phòng ngủ, căng tin, sân vận động, nền tím trống (cho thẻ chèn). Mỗi bối cảnh MUST có chi tiết lặp theo hàng (bàn, tủ, ghế, cửa sổ, đèn dây) và ít nhất một nguồn đèn thật, theo mục 2–3 của `STYLE.md`.
- **FR-005**: Ánh sáng và hậu kỳ mặc định MUST là bộ số đã đạt ở khung chứng minh (độ phơi sáng, bão hoà, vignette, bóng đổ, viền nắng ấm, trần và cuối phòng không đen), ghi trong bộ dựng kèm số đo đối chiếu.
- **FR-006**: Bộ dựng MUST có các đồ hoạ của phong cách: viên số đếm (đếm lên được), menu góc kiểu game có ổ khoá, sơ đồ giải thích trên nền cảnh làm mờ (hình người phẳng, đồng hồ đo, biểu đồ hai cột), bong bóng thoại, thẻ số liệu trên nền tím, thẻ tên phim hoặc câu hỏi hai dòng, thẻ chương, thẻ câu hỏi cuối có hai ô lựa chọn và hàng nhân vật nhỏ. Chữ MUST in hoa có chân màu vàng kem, nằm trong vùng hình, và được khai báo trong `window.CARDS`.
- **FR-007**: Bộ dựng MUST có các cách đặt máy hay gặp theo `shots.json` (trung tầm mắt, toàn hơi cao, cận, rất rộng, qua vai có đầu mờ tiền cảnh, thẻ chèn) và cách dựng chủ thể ở lớp trước, đám đông ở lớp sau, vật che tiền cảnh.
- **FR-008**: Bộ dựng MUST có một trang danh mục (mỗi bối cảnh, tư thế, biểu cảm, đồ hoạ một ô) để xem và để kiểm bằng `qc shots`.

**Phim từ bộ dựng (US2, US4)**

- **FR-009**: Luồng làm phim MUST hướng dẫn dùng bộ dựng khi phong cách có bộ dựng: bảng cảnh ghi bối cảnh, tư thế, đồ hoạ theo tên trong danh mục; kịch bản theo `STRUCTURE.md`.
- **FR-010**: Phim dựng từ bộ dựng MUST qua đủ các tầng kiểm của specs/020 và kiểm cách quay của specs/021, và ghi ở 60 fps bằng `sh bin/studio render <tên> --fps 60`.
- **FR-011**: Phim mẫu của phong cách MUST được làm lại bằng bộ dựng, theo `STRUCTURE.md`, với `DEMO.md` theo mẫu của thư viện, mã nguồn trong `demo/`, `build.sh` có `LIB=` ở đầu, và `demo-checks.json`. Phim mẫu MUST dài đủ ≈ 10,5 phút theo `STRUCTURE.md` và chính là phim thử của US2 (một lần chạy cho cả US2 và US4).

**Skill và công cụ học phong cách (US3)**

- **FR-012**: Skill học phong cách MUST cho phép phong cách có `STRUCTURE.md` (chỉ cấu trúc, không câu chữ, qua `check-names`) khi kênh đã chọn theo cấu trúc tham chiếu; mục 11 khi đó trỏ tới `STRUCTURE.md`. Kênh không chọn như vậy thì luật mục 11 cũ giữ nguyên.
- **FR-013**: `learn save` MUST chỉ chép vào phong cách các tệp của phong cách (`STYLE.md`, `EVIDENCE.md`, `style.json`, `STRUCTURE.md`, khung chứng minh và các tệp mã nguồn của nó) và bỏ qua tệp làm việc (`*.log`, `review-*.md`, `.job*`).

- **FR-015**: Hồ sơ kênh MUST lưu trang phục nhân vật chính (màu áo, tóc hoặc mũ, phụ kiện); bộ dựng MUST dựng nhân vật chính từ hồ sơ kênh của phim (`channel.json` của phim), mọi phim của kênh dùng chung. Kênh `dusk-hypothetical` mặc định đầu trọc, hoodie vàng mù tạt `#d9b23a`, dây rút trắng. Phim không thuộc kênh nào thì dùng mặc định của bộ dựng. Trang phục MUST khác nhân vật chính của kênh tham chiếu (FR-014). Đặt hoặc đổi bằng lệnh kênh hiện có (`channel set`).

**Bản quyền**

- **FR-014**: Bộ dựng, phim và phim mẫu MUST NOT chép nhân vật chính (áo xanh nhạt), câu chữ, tên, giọng, nhạc hay thumbnail của kênh tham chiếu; nhân vật chính của kênh mình giữ trang phục riêng. Dáng người và đầu trọc là luật hình chung của phong cách nên được phép; điểm khác bắt buộc là màu áo, kiểm bằng khoảng cách màu so với áo nhân vật của kênh tham chiếu. `check-names` MUST đạt trên mọi tệp chữ của bộ dựng và phim mẫu.

### Key Entities

- **Bộ dựng (kit)**: các phần dựng dùng lại của một phong cách (nhân vật, đám đông, bối cảnh, ánh sáng và hậu kỳ, đồ hoạ, cách đặt máy) cùng trang danh mục.
- **Danh mục**: tên các bối cảnh, tư thế, biểu cảm, đồ hoạ mà bảng cảnh dùng để gọi.
- **Khung kịch bản (`STRUCTURE.md`)**: các màn, tỉ lệ thời lượng, mốc chuyển, nhịp leo thang của phim theo phong cách.
- **Nhân vật chính của kênh**: trang phục cố định (màu áo, tóc hoặc mũ, phụ kiện) lưu trong hồ sơ kênh, dùng cho mọi phim của kênh.
- **Phim mẫu**: phim dựng bằng bộ dựng, kèm `DEMO.md`, mã nguồn và kết quả kiểm.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Mỗi bối cảnh của bộ dựng, chụp ở một cảnh toàn có người phụ, nằm trong khoảng độ sáng (0,22–0,29) và bão hoà (0,32–0,41) của phong cách, và 0 lỗi phẳng, tối, cháy, mờ ở `qc shots`.
- **SC-002**: Một cảnh dựng từ bộ dựng theo đúng bố cục của khung gốc đã dùng ở khung chứng minh đạt ngưỡng so sánh (độ sáng Δ ≤ 0,05, bão hoà Δ ≤ 0,08, vùng rất tối Δ ≤ 5 điểm %, ≥ 4 màu khớp) ngay lần chụp đầu, không phải sửa.
- **SC-003**: Một cảnh 1.000 người, 10 giây, ghi ở 60 fps trên GPU của xưởng trong ≤ 3 phút.
- **SC-004**: Một phim từ bộ dựng có mốc các màn trong ±5 điểm % so với `STRUCTURE.md`, tỉ lệ cỡ cảnh và góc máy trong khoảng của `shots.json`, ≥ 18 bối cảnh, 0 lỗi nặng ở các tầng kiểm, tệp phim 60 fps.
- **SC-005**: Phần mô tả cảnh (bảng cảnh và lời gọi bộ dựng) trung bình ≤ 15 dòng mỗi cảnh; trang phim không viết lại nhân vật, ánh sáng, hậu kỳ hay đồ hoạ.
- **SC-006**: `learn save` trên bộ thử có tệp làm việc cho ra phong cách không còn tệp làm việc nào; `STRUCTURE.md` được lưu.
- **SC-007**: `check-names` đạt trên toàn bộ tệp chữ của bộ dựng, phim mẫu và `STRUCTURE.md`.

## Assumptions

- Bộ dựng thuộc riêng phong cách `dusk-hypothetical` (nằm trong `my-styles/dusk-hypothetical/kit/`); phong cách khác có bộ dựng riêng sau này. Không làm bộ dựng chung cho mọi phong cách.
- Dùng bộ máy dựng hình duy nhất của xưởng (hiến pháp VII), không thêm bộ máy hay mô hình 3D bên ngoài; mọi hình dựng bằng code, không ảnh AI.
- Khung chứng minh của lần học lại (`my-styles/dusk-hypothetical/styleframe/index.html`) là điểm xuất phát của bộ dựng.
- Giọng đọc là giọng của kênh (Kokoro `am_michael` ×1,1); lời nhân vật phụ hiện bằng bong bóng (người kể đọc), không lồng giọng khác.
- Dựng phim bằng GPU; nếu máy chỉ dựng được bằng phần mềm thì dừng và hỏi người dùng (luật của người dùng).
- Gói đăng (specs/011) không thuộc phạm vi phim mẫu.
