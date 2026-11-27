# Feature Specification: Học máy quay và điểm duyệt Camera

**Feature Branch**: `039-camera-review`
**Created**: 2026-11-27
**Status**: Draft

## Clarifications

### Session 2026-11-27

- Q: Điểm duyệt Camera nằm ở đâu? → A: Sau Cast, trước Voice; thời lượng đổi sau Voice thì zoom tự tính lại, giữ phương án.
- Q: Ảnh thử nhanh là gì? → A: Khung đầu shot ¼ cỡ, dựng bằng nền và nhân vật thật, vẽ đè khung zoom cuối.
**Input**: "Học máy quay và chuyển cảnh theo từng shot của video mẫu (cỡ cảnh, bố cục, độ cao máy, ống kính, chuyển động máy 2D: zoom % có ease, trôi, pan, thời lượng, chuyển cảnh); khi lập bảng shot của phim AE, xưởng đưa 2–3 phương án máy quay cho mỗi shot của kịch bản, mỗi phương án có bằng chứng (shot mẫu giống nhất + số đo) và một ảnh thử nhanh; điểm duyệt "Camera" trong app như trang Sound: chọn phương án, ghim ghi chú, gửi cho Claude. Theo quyết định 2026-11-27: phim làm đúng cách video mẫu làm — nền phối cảnh + rig 2D + zoom 2D chậm; Blender chỉ vẽ nền rộng với máy đứng yên."

## Bối cảnh

Phim charisma-30 cho thấy: video mẫu dựng mỗi shot bằng một nền phối cảnh, nhân vật 2D và **một lần zoom 2D chậm** (3–9 %, có ease ở hai đầu, trôi xuống 6–12 px ở 1080p, không có thị sai), cắt thẳng giữa các shot. Phim của xưởng sai ở chỗ chọn máy quay theo cảm nhận: cỡ cảnh quá chặt, zoom tuyến tính, máy Blender đi vòng gây thị sai mà video mẫu không có. Người dùng quyết định (2026-11-27): xưởng làm phim **đúng cách video mẫu làm**. specs/038 đã đo độ cao máy, ống kính, độ sâu, lớp cảnh và chặn shot gần hoặc nông. Tính năng này thêm phần còn thiếu: học **máy quay theo thời gian** của từng shot mẫu, rồi **gợi ý** máy quay cho từng shot của phim kèm bằng chứng, và cho người dùng **duyệt** ở một điểm duyệt riêng.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Học máy quay của từng shot mẫu (Priority: P1)

Khi học phong cách (hoặc học thêm cho một phong cách đã có, video mẫu còn trên máy), xưởng đo trên **mỗi shot** của video mẫu: thời lượng, cỡ cảnh, bố cục (nhân vật chính ở đâu trong khung, chiếm bao nhiêu chiều cao khung, khoảng trống trên đầu), độ cao máy và ống kính (lấy lại số đo của specs/038), chuyển động máy 2D (zoom vào hay ra bao nhiêu %, đường ease, trôi ngang và dọc bao nhiêu px, pan), có thị sai hay không, và chuyển cảnh vào shot (cắt, mờ dần, đen). Mỗi shot mẫu thành một mục trong **thư viện shot mẫu** của phong cách, kèm một khung bằng chứng đầu và cuối shot. Phong cách còn có bảng tổng: phân bố từng số đo theo cỡ cảnh.

**Why this priority**: Không có số đo từng shot mẫu thì không có gì làm bằng chứng cho gợi ý. Đây là nền của US2 và US3, và tự dùng được: Claude đọc thư viện khi tự lập bảng shot.

**Independent Test**: Chạy bước học máy quay trên bộ video mẫu của charisma-30 (15 shot đã đo tay ngày 2026-11-27). Thư viện có 15 mục; mỗi mục có zoom %, trôi, đường ease, thời lượng, chuyển cảnh, bố cục và hai khung bằng chứng. Zoom % lệch số đo tay ≤ 1 điểm phần trăm ở ≥ 13/15 shot; chuyển cảnh đúng 15/15 (đều là cắt).

**Acceptance Scenarios**:

1. **Given** một bộ video mẫu đã tách shot, **When** chạy bước học máy quay, **Then** mỗi shot mẫu có một mục với đủ các số đo trên và hai khung bằng chứng; shot không đo được (quá ngắn, chớp sáng) được ghi lý do, không bị bỏ im lặng.
2. **Given** thư viện đã có, **When** xem bảng tổng của phong cách, **Then** thấy cho từng cỡ cảnh: số shot, thời lượng (trung vị, p25–p75), zoom % và chiều (vào/ra/đứng), trôi, tỉ lệ shot có thị sai, tỉ lệ từng loại chuyển cảnh.
3. **Given** video mẫu đã bị xoá sau khi học, **When** chạy lại bước học máy quay, **Then** lệnh báo cần video và cách tải lại; thư viện cũ giữ nguyên.
4. **Given** một shot mẫu có thị sai rõ (máy đi thật), **When** học, **Then** mục đó ghi "có thị sai" và loại chuyển động đo được, không ép về zoom 2D.

---

### User Story 2 - Gợi ý 2–3 phương án máy quay cho mỗi shot của phim (Priority: P1)

Khi bảng shot của một phim AE đã có (mỗi shot có nội dung, nhân vật, hành động, thời lượng dự kiến), xưởng tìm trong thư viện shot mẫu những shot giống nhất (cùng loại cảnh, cùng số người, hành động tương tự, thời lượng gần) và đưa **2–3 phương án máy quay** cho mỗi shot. Mỗi phương án ghi: cỡ cảnh, bố cục, độ cao máy, ống kính, chuyển động 2D (zoom %, chiều, ease, trôi), chuyển cảnh vào shot, bộ máy vẽ nền (AE, hoặc Blender với máy đứng yên), và **bằng chứng**: mã shot mẫu giống nhất, khung của shot đó, các số đo, và một dòng lý do. Phương án đầu là phương án khuyên dùng. Mỗi phương án có **một ảnh thử nhanh** của chính shot đó trong phim.

**Why this priority**: Đây là thứ người dùng yêu cầu: máy quay chọn theo bằng chứng, không theo cảm nhận. Không cần trang duyệt vẫn dùng được: Claude chọn phương án khuyên dùng khi phim ở giai đoạn thử (bỏ qua điểm duyệt).

**Independent Test**: Trên bảng shot 15 shot của charisma-30: mỗi shot có 2–3 phương án, mỗi phương án có mã shot mẫu, khung, số đo, lý do và ảnh thử. Các con số của phương án khuyên dùng nằm trong p25–p75 của video mẫu ở cùng cỡ cảnh (zoom %, thời lượng, trôi) ở ≥ 90 % shot. Không phương án nào có máy Blender đi hay vòng quanh khi video mẫu không có shot nào như vậy.

**Acceptance Scenarios**:

1. **Given** bảng shot của phim AE và phong cách có thư viện shot mẫu, **When** chạy lệnh gợi ý máy quay, **Then** mỗi shot có 2–3 phương án khác nhau thật (khác cỡ cảnh, hoặc khác chiều zoom, hoặc khác bố cục), phương án đầu là khuyên dùng, mỗi phương án có bằng chứng và ảnh thử.
2. **Given** video mẫu không có shot nào có máy đi thật, **When** gợi ý, **Then** mọi phương án chỉ dùng zoom 2D, trôi và pan; shot vẽ nền bằng Blender có máy đứng yên.
3. **Given** một shot của phim không tìm được shot mẫu đủ giống (khác hẳn loại cảnh), **When** gợi ý, **Then** phương án vẫn được đưa theo bảng tổng của cỡ cảnh đó, ghi rõ "không có shot mẫu giống" và độ giống thấp nhất đã thử.
4. **Given** thời lượng shot đổi sau khi có giọng thật, **When** gợi ý chạy lại, **Then** phương án đã chọn được giữ, chỉ zoom và trôi được tính lại theo tốc độ của shot mẫu (cùng % mỗi giây), và báo các shot có số mới.
5. **Given** chuyển cảnh của phương án khác loại chuyển cảnh mà video mẫu dùng ở ≥ 90 % số cắt, **When** gợi ý, **Then** phương án đó phải ghi lý do; phương án khuyên dùng luôn dùng loại chuyển cảnh chính của video mẫu.

---

### User Story 3 - Điểm duyệt Camera trong app (Priority: P2)

Phim AE có thêm điểm duyệt **Camera**, nằm sau Cast và trước Voice (Script → Cast → Camera → Voice → Animatic; người dùng chọn 2026-11-27): máy quay được chốt trước khi tốn tiền làm giọng, ảnh thử dùng nhân vật đã duyệt; khi có giọng thật, zoom và trôi được tính lại theo thời lượng mới (FR-011) mà không phải duyệt lại. Trang Camera giống trang Sound: lưới shot; bấm một shot thì thấy các phương án cạnh nhau (ảnh thử, khung shot mẫu, số đo, lý do), xem trước chuyển động zoom của phương án; người dùng chọn phương án, hoặc ghim ghi chú lên ảnh rồi "Send notes to Claude". Khi mọi shot đã có phương án được chọn, người dùng duyệt Camera; các bước sau dùng đúng máy quay đã chọn.

**Why this priority**: Cho người dùng quyết máy quay trước khi tốn thời gian dựng. Phim vẫn làm được với US1+US2 (Claude chọn phương án khuyên dùng).

**Independent Test**: Mở trang Camera của phim thử trong app: đổi phương án của một shot, ghim một ghi chú và gửi cho Claude, duyệt. Kiểm: lựa chọn được ghi theo mã shot cùng người chọn; ghi chú tạo một việc sửa chỉ cho đúng shot đó; duyệt xong thì bước dựng dùng phương án đã chọn (zoom % của bản dựng khớp phương án trong ±0,5 điểm phần trăm).

**Acceptance Scenarios**:

1. **Given** phim có phương án máy quay cho mọi shot, **When** mở trang Camera, **Then** mỗi shot hiện 2–3 phương án với ảnh thử, khung shot mẫu, số đo và lý do; phương án khuyên dùng được đánh dấu.
2. **Given** người dùng chọn phương án thứ hai cho một shot, **When** lưu, **Then** lựa chọn ghi theo mã shot, cả phương án khuyên dùng ban đầu cũng được giữ, và bước Camera chuyển về "chưa duyệt" nếu đã duyệt trước đó.
3. **Given** người dùng ghim ghi chú lên ảnh thử và bấm "Send notes to Claude", **When** việc sửa chạy, **Then** chỉ các shot có ghi chú được làm lại phương án và ảnh thử; các shot khác giữ nguyên.
4. **Given** còn shot chưa có phương án được chọn, **When** bấm duyệt, **Then** app từ chối và liệt kê các shot đó.
5. **Given** Camera đã duyệt, **When** đổi bảng shot (thêm, bỏ shot) hoặc đổi phương án, **Then** Camera thành "Must run again" theo cách các điểm duyệt khác làm (specs/026), và các bước dựng sau chờ duyệt lại.
6. **Given** phim đang ở giai đoạn thử và điểm duyệt Camera tắt, **When** làm phim, **Then** phương án khuyên dùng được dùng và ghi lại là "tự động".

---

### User Story 4 - Kiểm máy quay sau khi dựng (Priority: P3)

Sau khi dựng bản nháp hoặc bản đẹp, xưởng đo lại máy quay trên chính phim (cùng cách đo của US1) và so với phương án đã chọn của từng shot: zoom %, chiều, đường ease, trôi, có thị sai không, chuyển cảnh. Shot nào lệch quá mức được báo theo mã shot, kèm số đo của phim, số của phương án và cách sửa.

**Why this priority**: Đóng vòng "đo, dựng, đo lại" đã học từ charisma-30, nhưng phim vẫn làm được khi chỉ có US1–US3.

**Independent Test**: Dựng 3 shot thử: một đúng phương án, một zoom tuyến tính thay vì có ease, một có thị sai. Bước kiểm báo đúng hai shot sai, theo mã shot, không báo shot đúng.

**Acceptance Scenarios**:

1. **Given** phim đã dựng và có phương án đã chọn, **When** chạy kiểm máy quay, **Then** mỗi shot có số đo của phim cạnh số của phương án; shot lệch zoom > 1 điểm phần trăm, sai chiều, ease lệch > 10 điểm phần trăm ở mốc giữa shot, hoặc có thị sai khi phương án không có, bị báo theo mã shot.
2. **Given** một shot bị báo, **When** người dùng cho miễn shot đó kèm lý do, **Then** miễn ghi theo từng shot; agent không tự miễn; lệnh miễn bị từ chối khi chạy bên trong một việc của app.

---

### Edge Cases

- Phong cách học trước tính năng này (chưa có thư viện shot mẫu): lệnh gợi ý dừng và báo cần chạy bước học máy quay, kèm việc phải tải lại video mẫu nếu đã xoá.
- Shot mẫu dài dưới 1 s hoặc có chớp, rung mạnh: đo được thì ghi kèm cờ "kém tin cậy" và không dùng làm bằng chứng chính.
- Phim trang web (bộ máy "page"): lệnh gợi ý và điểm duyệt Camera từ chối, vì chỉ phim AE dùng bảng shot của specs/038.
- Hai phương án của cùng shot trùng hết số đo: chỉ giữ một, và nói rõ chỉ có 2 phương án khác nhau (hoặc 1 khi thư viện quá ít).
- Phương án chọn zoom ra (pull) nhưng video mẫu chỉ zoom vào: phương án vẫn có thể đưa nếu có shot mẫu zoom ra; không có thì không đưa.
- Bảng shot đã có máy quay viết tay (phim cũ của 038): gợi ý vẫn chạy, phương án cũ được giữ làm một phương án "của người làm phim" cạnh các phương án mới.
- Shot vẽ nền bằng Blender: máy Blender luôn đứng yên; chuyển động máy của shot là zoom 2D trên ảnh đã dựng, như video mẫu.
- Người dùng ghi chú yêu cầu một chuyển động video mẫu không có (ví dụ máy vòng quanh): Claude làm theo người dùng, phương án ghi "theo yêu cầu, ngoài video mẫu", và kiểm máy quay không báo shot đó.

## Requirements *(mandatory)*

### Functional Requirements

**Học máy quay (US1)**

- **FR-001**: Bước học máy quay PHẢI đo trên mỗi shot của video mẫu: thời lượng; cỡ cảnh; bố cục (vị trí ngang và dọc của nhân vật chính theo phần trăm khung, chiều cao nhân vật chính so với khung, khoảng trống trên đầu); độ cao máy và ống kính (dùng lại số đo của specs/038); chuyển động 2D (zoom % đầu → cuối, chiều, đường ease ở ¼, ½, ¾ thời lượng, trôi ngang và dọc theo px ở 1080p, pan); có thị sai hay không; chuyển cảnh vào shot.
- **FR-002**: Mỗi shot mẫu PHẢI có hai khung bằng chứng (đầu và cuối shot) và mã shot ổn định để các bước sau dẫn tới (hiến pháp VIII).
- **FR-003**: Phong cách PHẢI có bảng tổng của máy quay theo cỡ cảnh (số shot, trung vị và p25–p75 của thời lượng, zoom %, trôi; tỉ lệ thị sai; tỉ lệ từng loại chuyển cảnh), lưu cạnh số đo chiều sâu của specs/038.
- **FR-004**: Bước học PHẢI chạy được cho phong cách đã có mà không làm mất các phần khác của phong cách; video mẫu chỉ dùng để học nội bộ và không vào repo (mục Bản quyền).
- **FR-005**: Cách đo máy quay của US1 PHẢI là một cách đo dùng chung cho cả video mẫu (US1) và phim của xưởng (US4), để hai bên so được với nhau.

**Gợi ý phương án (US2)**

- **FR-006**: Lệnh gợi ý PHẢI đưa 2–3 phương án khác nhau cho mỗi shot trong bảng shot của phim AE, phương án đầu là khuyên dùng; mỗi phương án ghi cỡ cảnh, bố cục, độ cao máy, ống kính, chuyển động 2D, chuyển cảnh, bộ máy vẽ nền, mã shot mẫu giống nhất, độ giống, các số đo và một dòng lý do.
- **FR-007**: Độ giống giữa một shot của phim và một shot mẫu PHẢI dựa trên những gì bảng shot có: loại cảnh, số người, hành động, cỡ cảnh dự kiến, thời lượng. Cách tính PHẢI được ghi lại để người dùng hiểu vì sao shot mẫu đó được chọn.
- **FR-008**: Phương án khuyên dùng PHẢI có zoom %, thời lượng và trôi nằm trong p25–p75 của video mẫu ở cùng cỡ cảnh, và dùng loại chuyển cảnh chính của video mẫu; phương án khác ra ngoài khoảng đó PHẢI ghi lý do.
- **FR-009**: Không phương án nào được có máy Blender đi, vòng quanh hay có thị sai khi tỉ lệ shot mẫu có thị sai dưới 5 %. Shot vẽ nền bằng Blender PHẢI có máy Blender đứng yên; chuyển động máy là zoom 2D trên hình đã dựng.
- **FR-010**: Mỗi phương án PHẢI có một ảnh thử nhanh của chính shot đó trong phim: khung đầu shot dựng ở cỡ ¼ bằng nền và nhân vật thật (bộ máy của shot), vẽ đè khung chữ nhật của khung cuối để thấy zoom đi tới đâu (người dùng chọn 2026-11-27). Bộ máy cần cho ảnh thử chưa chạy được thì lệnh báo rõ, không thay bằng ảnh khác. Mọi ảnh thử do code của xưởng vẽ (hiến pháp VII).
- **FR-011**: Khi thời lượng shot đổi, phương án đã chọn PHẢI được giữ; zoom và trôi được tính lại theo cùng tốc độ mỗi giây của phương án, và lệnh báo các shot có số mới.
- **FR-012**: Phương án đã chọn của mỗi shot PHẢI được ghi vào bảng shot của phim (specs/038) để bước dựng và Animatic dùng đúng máy quay đó; phương án khuyên dùng ban đầu và nguồn lựa chọn (tự động, người dùng, ghi chú) cũng được giữ.

**Điểm duyệt Camera (US3)**

- **FR-013**: Phim AE PHẢI có điểm duyệt Camera giữa Cast và Voice, bật mặc định cho phim AE như Cast và Animatic, theo cách các điểm duyệt khác (specs/026): bật/tắt theo kênh và theo phim, có dấu vân tay, "Must run again" khi bảng shot hoặc phương án đổi, các bước sau chờ duyệt.
- **FR-014**: Trang Camera PHẢI cho: xem lưới shot; xem các phương án của một shot cạnh nhau (ảnh thử, khung shot mẫu, số đo, lý do); xem trước chuyển động zoom của phương án; chọn phương án; ghim ghi chú lên ảnh và "Send notes to Claude"; duyệt. Trang không tự ghi tệp, chỉ gọi các lệnh đã kiểm của xưởng (như specs/026).
- **FR-015**: "Send notes to Claude" PHẢI tạo một việc sửa chỉ làm lại phương án và ảnh thử của các shot có ghi chú.
- **FR-016**: Duyệt Camera PHẢI bị từ chối khi còn shot chưa có phương án được chọn, kèm danh sách shot.
- **FR-017**: Lệnh gợi ý và điểm duyệt Camera PHẢI dùng được bằng lệnh khi app không chạy (như luồng làm phim bằng chat), và ghi vào sổ việc của app khi app đang chạy.

**Kiểm máy quay (US4)**

- **FR-018**: Bước kiểm máy quay PHẢI đo lại phim đã dựng bằng cách đo của FR-005 và báo theo mã shot khi: zoom lệch > 1 điểm phần trăm, sai chiều zoom, ease ở mốc ½ lệch > 10 điểm phần trăm, có thị sai khi phương án không có, hoặc chuyển cảnh khác phương án.
- **FR-019**: Miễn kiểm máy quay PHẢI theo từng shot, kèm lý do, do người dùng quyết; agent KHÔNG ĐƯỢC tự miễn; lệnh miễn bị từ chối bên trong một việc của app (như specs/038 FR-014).

**Chung**

- **FR-020**: Phim AE cũ (không có phương án máy quay) PHẢI dựng như cũ; điểm duyệt Camera chỉ bật cho phim có thư viện shot mẫu trong phong cách.
- **FR-021**: Tài liệu luồng làm phim (skill film-make) PHẢI có bước gợi ý và duyệt máy quay, và luật: máy quay chọn theo phương án có bằng chứng, không theo cảm nhận.

### Key Entities

- **Shot mẫu (Reference shot)**: thuộc một phong cách; mã ổn định, video và thời điểm, thời lượng, cỡ cảnh, bố cục, độ cao máy, ống kính, chuyển động 2D (zoom, ease, trôi, pan), thị sai, chuyển cảnh, độ tin cậy, hai khung bằng chứng.
- **Bảng tổng máy quay (Camera summary)**: thuộc phong cách; theo cỡ cảnh: số shot, khoảng của các số đo, tỉ lệ thị sai và chuyển cảnh.
- **Phương án máy quay (Camera option)**: thuộc một shot của phim; các thông số máy quay, bộ máy vẽ nền, shot mẫu dẫn chứng, độ giống, lý do, ảnh thử, có phải khuyên dùng không.
- **Lựa chọn máy quay (Camera choice)**: thuộc một shot; phương án được chọn, phương án khuyên dùng ban đầu, nguồn (tự động, người dùng, ghi chú), người chọn, thời điểm.
- **Ghi chú Camera (Camera note)**: ghim lên ảnh thử của một phương án; nội dung, vị trí, trạng thái đã gửi/đã sửa.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Trên 15 shot mẫu của charisma-30, zoom % đo được lệch số đo tay ≤ 1 điểm phần trăm ở ≥ 13/15 shot, chuyển cảnh đúng 15/15, và mọi shot có hai khung bằng chứng.
- **SC-002**: Trên bảng shot 15 shot của charisma-30, 100 % shot có 2–3 phương án có bằng chứng và ảnh thử; phương án khuyên dùng nằm trong p25–p75 của video mẫu (zoom %, thời lượng, trôi) ở ≥ 90 % shot; 0 phương án có máy đi hay thị sai.
- **SC-003**: Gợi ý cho một phim 15 shot (kể cả ảnh thử) xong trong ≤ 10 phút trên máy phát triển.
- **SC-004**: Trên trang Camera, người dùng chọn phương án cho cả 15 shot và duyệt trong ≤ 5 phút; 100 % lựa chọn được ghi theo mã shot; gửi ghi chú cho một shot chỉ làm lại đúng shot đó (14 shot còn lại giống hệt).
- **SC-005**: Sau khi dựng theo phương án đã chọn, kiểm máy quay báo 0 shot lệch trên phim thử; trên 3 shot cố ý sai, báo đúng 2/2 shot sai và 0 shot đúng.
- **SC-006**: Khi xem phim thử cạnh video mẫu, sai khác zoom % trung bình mỗi shot giảm xuống ≤ 1 điểm phần trăm (charisma-30 trước sửa: zoom tuyến tính và đứng yên ở nhiều shot).

## Assumptions

- Thư viện shot mẫu dựa trên phần tách shot và số đo chiều sâu đã có (specs/021, 023, 038); bước học máy quay chỉ thêm phần còn thiếu.
- Video mẫu phải còn trên máy khi học máy quay; nếu đã xoá thì tải lại theo cách đã có (`learn refetch`).
- "Chuyển động 2D" gồm zoom, trôi và pan trên cả khung; không có quay máy 3D. Đây là cách video mẫu của kênh đang dùng được đo ngày 2026-11-27; nếu một video mẫu khác có máy đi thật, thư viện sẽ ghi lại và gợi ý được dùng nó (FR-009 chỉ chặn khi video mẫu gần như không có).
- Ảnh thử nhanh ở cỡ ¼ khung, đủ để thấy bố cục và vùng zoom, không cần chất lượng bản đẹp.
- Gợi ý chỉ dành cho phim AE (có bảng shot của specs/038); phim trang web không đổi.
- Bộ dữ liệu thử là charisma-30 (video mẫu và 15 shot đã đo tay) đang nằm ở worktree của 038.
