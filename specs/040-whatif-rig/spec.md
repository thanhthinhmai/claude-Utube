# Feature Specification: Rig ball@3 có khối và hai phòng Blender (bếp, phòng khách) cho phim what-if

**Feature Branch**: `040-whatif-rig`

**Created**: 2026-11-28

**Status**: Draft

**Input**: User description: "Rig AE ball@3 và 2 phòng Blender (bếp, phòng khách) để phim AE đạt chất của phong cách what-if học từ kênh mẫu (references/whatif-long/style). Rig ball@3 mới trong tools/ae/kit/rigs/ball/v3, không đổi ball@1/ball@2: đầu cầu bóng loáng có viền sáng và một điểm sáng, mắt trắng to ≈0,25–0,3 bề ngang đầu, không mũi không cổ; thân có khối (một gradient mềm, bóng đổ mềm) với viền tối mảnh đều ≈1,5–2 px ở 720p; chân tay dạng ống dày, bàn tay tròn to, giày to tròn; hoodie có dây mũ và túi trước; trẻ em 3–3,5 đầu, người lớn 4,5 đầu, đầu ai cũng cỡ bằng nhau; cùng các khoá spec như ball@2 cộng tuổi (kid/adult); dùng được qua CU.who/CU.mate/CU.carry và ae sheet như rig cũ. Thêm hai bối cảnh kitchen và livingroom kiểu toon có viền, đồ đạc nhiều như mẫu, sáng mềm. Thành công: bảng mẫu của ball@3 đặt cạnh khung mẫu được người dùng thấy cùng chất; khung chứng minh dựng bằng AE + Blender + máy đẩy đo được qua learn compare trong ngưỡng; test của tools/ae và tools/blender đều qua."

**Mức quy trình**: Nhẹ (người dùng chọn phương án 1 ngày 2026-11-28).

## Bối cảnh

- Phong cách what-if (bộ `whatif-long`, chưa lưu vào `my-styles/`) đã qua duyệt lần 1. Khung chứng minh vẽ bằng three.js không dùng bộ máy của xưởng, và người dùng thấy "chưa ra chất giống mẫu".
- Khi so rig `ball@2` với khung mẫu (`references/whatif-long/proof/out/rig_vs.jpg`), khác biệt lớn nhất nằm ở nhân vật: `ball@2` phẳng như vẽ vector, chân que mảnh, tay và giày nhỏ, đầu không bóng. Nhân vật mẫu có khối, viền mảnh tối, chân tay ống dày, tay tròn to, giày to.
- Phòng Blender toon có viền (spec 038) và máy đẩy 2D đo được (spec 039) đã gần mẫu. Bộ dựng Blender còn thiếu bếp và phòng khách, hai loại phòng hay làm "bối cảnh nhà" ở phim mẫu.
- Theo quyết định của spec 038, nhân vật trong shot Blender vẫn do rig AE vẽ (một bản code nhân vật), nên nâng rig là nâng cả hai bộ máy.
- Hạ tầng phiên bản rig (spec 034: `rigs.lock`, bundle mang cả bản đã duyệt lẫn bản mới) đã có sẵn. `ball@3` là một phiên bản mới cạnh `ball@1` và `ball@2`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Nhân vật ball@3 cùng chất với mẫu (Priority: P1)

Chủ xưởng làm phim theo phong cách what-if và chọn rig `ball@3` cho nhân vật. Bảng mẫu nhân vật (mặt trước, sau, ¾, biểu cảm, tư thế) cho thấy nhân vật có khối, viền mảnh, chân tay dày, tay và giày to, đầu bóng có viền sáng, giống nhân vật của kênh mẫu về chất, nhưng là nhân vật của riêng xưởng.

**Why this priority**: Rig là khoảng cách lớn nhất với mẫu. Chưa có nó thì phim dài what-if sẽ lệch chất dù phòng và máy đã đúng.

**Independent Test**: Tạo bảng mẫu của một nhân vật `ball@3` (một trẻ em áo vàng và một người lớn), đặt cạnh khung mẫu, rồi người dùng duyệt bằng mắt. Đo tỉ lệ đầu/chiều cao và cỡ mắt trên bảng mẫu.

**Acceptance Scenarios**:

1. **Given** một nhân vật khai báo rig `ball@3`, tuổi `kid`, hoodie vàng, **When** chạy lệnh tạo bảng mẫu, **Then** bảng có đủ các góc nhìn, biểu cảm, tư thế như `ball@2`, và nhân vật cao 2,95–3,35 đầu.
2. **Given** một nhân vật `ball@3` tuổi `adult`, **When** tạo bảng mẫu, **Then** nhân vật cao 2,95–3,35 đầu, thân rộng và dài hơn tuổi `kid` (≈ 0,67 so với 0,56 bề ngang đầu), giày tối màu, và đầu cùng cỡ với đầu của tuổi `kid` ở cùng `scale`. Tuổi `toddler` cao 2,0–2,3 đầu.
3. **Given** một phim cũ đã duyệt nhân vật bằng `ball@1` hoặc `ball@2`, **When** dựng lại phim, **Then** hình nhân vật không đổi (khoá phiên bản của hai rig cũ không đổi).
4. **Given** một shot AE gọi `CU.who`, `CU.mate`, `CU.carry` với nhân vật `ball@3`, **When** dựng shot, **Then** nhân vật hiện ra, đi, cầm đồ, đổi biểu cảm như với rig cũ, không lỗi script.

---

### User Story 2 - Bếp và phòng khách trong bộ dựng Blender (Priority: P2)

Chủ xưởng lập bảng shot cho phim what-if có "bối cảnh nhà" là bếp hoặc phòng khách. Shot Blender gọi bối cảnh `kitchen` hoặc `livingroom` và nhận một phòng toon có viền, nhiều đồ đạc, sáng mềm như mẫu, có chỗ đứng cho nhân vật.

**Why this priority**: Bối cảnh nhà chiếm ≈ 26% số cảnh của phim mẫu. Bộ dựng hiện chỉ có lớp học, hành lang, phòng tập, văn phòng, hội trường.

**Independent Test**: Dựng ảnh tĩnh ¼ cỡ của mỗi phòng từ 3 góc máy (toàn cảnh, trung cảnh, ngang tầm mắt), đo độ sáng, tương phản, bão hoà, rồi xem bằng mắt cạnh các khung mẫu có bếp hoặc phòng khách.

**Acceptance Scenarios**:

1. **Given** một shot Blender khai báo bối cảnh `kitchen`, **When** dựng ảnh tĩnh, **Then** phòng có viền mảnh trên mọi cạnh, mặt màu phẳng với một gradient mềm, và có ít nhất 8 món đồ đạc đặc trưng (tủ bếp, bếp, tủ lạnh, bàn, ghế…).
2. **Given** bối cảnh `livingroom`, **When** dựng ảnh tĩnh, **Then** phòng có viền và ít nhất 8 món đồ (sofa, bàn nước, TV, kệ, đèn, thảm, cây, khung tranh…).
3. **Given** một trong hai phòng, **When** đo ảnh dựng, **Then** độ sáng, tương phản, bão hoà nằm trong khoảng đo được của bộ mẫu.

---

### User Story 3 - Khung chứng minh dựng bằng bộ máy của xưởng (Priority: P3)

Chủ xưởng xem lại khung chứng minh của phong cách what-if. Lần này khung được dựng bằng AE (nhân vật `ball@3`) trên phòng Blender mới, với máy đẩy có ease đo được, rồi so với khung mẫu bằng công cụ so của xưởng.

**Why this priority**: Đây là bằng chứng để đi tiếp bước 7–8 của học phong cách, rồi làm phim dài.

**Independent Test**: Dựng một shot 6 giây (phòng khách hoặc bếp, nhân vật chính áo vàng và một người nhà), so ảnh và đoạn clip với mẫu bằng công cụ so.

**Acceptance Scenarios**:

1. **Given** rig `ball@3` và một phòng mới, **When** dựng shot chứng minh trên GPU, **Then** công cụ so ảnh báo 4 chỉ số trong ngưỡng, hoặc nêu rõ chỉ số lệch để người dùng quyết ở bước duyệt phong cách lần 2.
2. **Given** đoạn clip chứng minh, **When** so chuyển động, **Then** máy là cú đẩy chậm có ease (≈ 1,7 %/giây), không phải máy đứng.

### Edge Cases

- Nhân vật `ball@3` khai báo khoá chỉ có ở rig cũ (`stripe`, `tie`): bỏ qua có cảnh báo, không lỗi dựng.
- Thiếu khoá `age`: mặc định `kid` (nhân vật chính của phong cách là thiếu niên).
- `scale` ngoài 0,6–1,4: giữ luật cũ của `ball@2` (từ chối hoặc kẹp như hiện tại).
- Nhân vật `ball@3` ở cỡ rất nhỏ (đám đông, toàn cảnh rất rộng): viền không được dày hơn chi tiết; viền giữ ≈ 1,5–2 px ở 720p theo cỡ hiển thị.
- Phim đang dùng `ball@2` muốn chuyển nhân vật sang `ball@3`: đi qua luồng "rig có bản mới" của trang Cast (xem trước rồi cập nhật), không tự đổi.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Xưởng PHẢI có rig phiên bản mới `ball@3`, khoá vào danh sách phiên bản rig, đặt cạnh `ball@1` và `ball@2`. Hai rig cũ không được đổi một byte nào.
- **FR-002**: Đầu của `ball@3` PHẢI là hình tròn bóng loáng, không viền tối: gradient sáng ở trên, tối ở dưới; một điểm sáng trắng phía trên bên phải; viền sáng mảnh (màu theo `rimColor`) dày hơn ở phía phải màn hình; mắt trắng ≈ 0,22–0,26 bề ngang đầu; không mũi, không cổ (đầu chồng lên thân).
- **FR-003**: Thân, tay, chân, giày của `ball@3` PHẢI có viền tối mảnh ≈ 1–2,3 px khi hiển thị ở 720p (màu gần đen pha theo màu tô, không đen tuyền); thân có gradient mềm từ trên trái xuống dưới phải; mỗi đoạn tay, chân có một dải tối cứng ở phía phải màn hình rộng 25–30% bề ngang đoạn; bóng tiếp đất mềm dưới giày.
- **FR-004**: Tay và chân của `ball@3` PHẢI là ống thẳng đầu tròn, không khớp cầu (khuỷu, gối là hai ống chồng nhau ở góc): tay 0,19–0,23, chân 0,20–0,24 bề ngang đầu; bàn tay là bóng tối 0,21–0,25 bề ngang đầu chồng lên cổ tay áo; giày hình vòm dài ≈ 0,36 và cao ≈ 0,21 bề ngang đầu (tuổi `kid`, `toddler`: trắng có dải đế xám; `adult`: nâu hoặc đen, đổi được bằng `shoes`).
- **FR-005**: Hoodie của `ball@3` PHẢI có vòng cổ mũ sau cằm, hai dây mũ trắng có đầu dây, túi trước tối hơn và hơi trong, cổ tay áo tối hơn; khoá `hood` vẫn bật hoặc tắt mũ như `ball@2`.
- **FR-006**: `ball@3` PHẢI nhận khoá `age` (`kid` | `adult` | `toddler`). `kid` (thiếu niên, mặc định) và `adult` cao 2,95–3,35 đầu; `adult` có thân rộng hơn (≈ 0,67 so với 0,56 bề ngang đầu) và dài hơn (≈ 1,08 so với 0,98). `toddler` cao 2,0–2,3 đầu (thân ≈ 0,5, chân ≈ 0,65 bề ngang đầu); tay, bàn tay, mắt, giày giữ cùng tỉ lệ với đầu. Đầu cùng cỡ ở cùng `scale`.
- **FR-007**: `ball@3` PHẢI nhận các khoá spec của `ball@2` (`hoodie`, `pants`, `shoes`, `headColor`, `rimColor`, `hat`, `hood`, `brows`, `pupils`, `blush`, `scale`) và có đủ góc nhìn, biểu cảm, tư thế, đi bộ như danh mục của `ball@2`.
- **FR-008**: Shot AE PHẢI dùng được `ball@3` qua các hàm hiện có (`CU.who`, `CU.mate`, `CU.carry`, `CU.char`) và lệnh bảng mẫu nhân vật, không phải đổi lời gọi.
- **FR-009**: Bộ dựng Blender PHẢI có bối cảnh `kitchen` và `livingroom` kiểu toon có viền, mỗi phòng ≥ 8 món đồ đặc trưng, có chỗ đứng và đường đi cho nhân vật, gọi được như các bối cảnh hiện có.
- **FR-010**: Hai phòng mới PHẢI cho ảnh dựng có độ sáng, tương phản, bão hoà trong khoảng của bộ mẫu (độ sáng 0,44–0,58, tương phản 0,17–0,23, bão hoà 0,14–0,26).
- **FR-011**: Danh mục tài liệu của bộ dựng (rig và bối cảnh) PHẢI ghi `ball@3`, `kitchen`, `livingroom` để luồng làm phim tìm thấy.
- **FR-012**: Không file nào của tính năng được chứa tên kênh mẫu, tên nhân vật, câu thoại hay hình trích từ video mẫu; ảnh khung mẫu chỉ nằm trong `references/`.

### Key Entities

- **Phiên bản rig**: mã `ball@3`, thư mục code vẽ và danh mục (góc nhìn, biểu cảm, tư thế, khoá spec, tuổi), dấu khoá.
- **Nhân vật**: khai báo trong cast của phim, có `rig`, các khoá spec và `age`.
- **Bối cảnh Blender**: tên (`kitchen`, `livingroom`), danh sách đồ đạc, chỗ đứng, đèn.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Người dùng xem bảng mẫu `ball@3` đặt cạnh khung mẫu và xác nhận cùng chất về khối, viền và tỉ lệ (duyệt ở điểm Cast hoặc trong chat).
- **SC-002**: Đo trên bảng mẫu, mọi tỉ lệ nằm trong khoảng đo được của mẫu (`references/whatif-long/analysis/rig-measure.json`): `kid` và `adult` 2,95–3,35 đầu, `toddler` 2,0–2,3; mắt 0,22–0,26, tay 0,19–0,23, chân 0,20–0,24, bàn tay 0,21–0,25 bề ngang đầu; viền 1–2,3 px ở 720p.
- **SC-003**: 100% phim cũ dùng `ball@1`/`ball@2` giữ đúng dấu khoá rig, bài test phiên bản rig vẫn qua.
- **SC-004**: Ảnh dựng của mỗi phòng mới (3 góc máy) có độ sáng, tương phản, bão hoà trong khoảng của FR-010.
- **SC-005**: Khung chứng minh dựng bằng AE + Blender trên GPU; so ảnh với khung mẫu cho 4 chỉ số trong ngưỡng, hoặc tối đa 2 vòng sửa rồi người dùng quyết ở duyệt lần 2. Clip có máy đẩy có ease.
- **SC-006**: Tất cả bộ test của xưởng qua, kể cả `tests/ae` và `tests/blender`.

## Assumptions

- Nhân vật vẫn là hình 2D do AE vẽ; "khối" là gradient, bóng mềm và viền vẽ trong AE, không phải mô hình 3D (theo quyết định của spec 038).
- Mặc định `age` là `kid`. Số đo (20 nhân vật trên 15 khung từ 7 video, `references/whatif-long/analysis/rig-measure.md`) cho thấy thiếu niên và người lớn cùng một dáng; báo cáo phân tích trước đó ghi người lớn 4,5 đầu là sai và được sửa ở nhật ký sửa của phong cách.
- Các khoá `stripe`, `tie` của `ball@2` không bắt buộc ở `ball@3`; có thể thêm sau.
- Phòng mới dùng lại vật liệu toon, viền và đèn của bộ dựng Blender hiện có; không cần thay đổi bộ máy Blender.
- Khung chứng minh và phim dài nằm ngoài phạm vi code của tính năng này (chúng là việc của luồng học phong cách và làm phim). US3 chỉ dùng chúng để kiểm.
- Máy AE và Blender trên máy người dùng như các spec 032, 038 (cấu hình đã có).
