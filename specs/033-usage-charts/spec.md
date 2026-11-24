# Feature Specification: Ô tổng và biểu đồ ở Settings → Usage

**Feature Branch**: `033-usage-charts`

**Created**: 2026-11-24

**Status**: Draft

**Input**: User description: "Settings → Usage: thêm ô tổng và biểu đồ. Đầu trang có các ô tổng: số request Claude và số token của hôm nay, 7 ngày, 30 ngày. Biểu đồ cột theo ngày cho request và token, chia màu theo tài khoản Claude (slot 1–5 và API key). Có chọn khoảng ngày (7 / 30 / 90 ngày hoặc từ ngày–đến ngày) áp dụng cho biểu đồ và các bảng hiện có. Học theo tab Usage của neb-creative-tool (components/settings/Usage.tsx: Tile, biểu đồ có chú thích và bảng xem dạng số). Mức Nhẹ: chỉ user story P1."

## Bối cảnh

- Settings → Usage (specs/008) hiện chỉ có một dòng tổng 30 ngày và ba bảng số: theo tài khoản Claude, theo thành viên, theo ngày. Muốn biết hôm nay đã dùng bao nhiêu, hay ngày nào tăng vọt, chủ xưởng phải đọc từng dòng bảng.
- Tab Usage của neb-creative-tool (dự án khác của chủ xưởng) có các ô tổng ở đầu trang và biểu đồ cột theo ngày, chia theo tài khoản, kèm chú thích và cách xem dạng bảng. Chủ xưởng muốn có cách xem tương tự.
- Dữ liệu đã có sẵn: xưởng ghi mỗi lượt gọi Claude (tài khoản nào, bao nhiêu token, thuộc việc nào, lúc nào). Không cần ghi thêm gì.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Nhìn nhanh lượng request và token (Priority: P1)

Chủ xưởng mở Settings → Usage và thấy ngay số request Claude và số token của hôm nay, 7 ngày và 30 ngày. Bên dưới là một biểu đồ cột theo ngày, mỗi cột chia màu theo tài khoản Claude; một nút chọn loại cho xem request hoặc token trên cùng biểu đồ. Chủ xưởng đổi khoảng ngày (7 / 30 / 90 ngày, hoặc tự chọn từ ngày đến ngày) thì biểu đồ và các bảng hiện có cùng đổi theo.

**Why this priority**: Đây là toàn bộ yêu cầu. Nó giúp chủ xưởng biết hạn mức đang bị dùng nhanh hay chậm, tài khoản nào gánh nhiều, và ngày nào bất thường, mà không phải đọc bảng.

**Independent Test**: Tạo dữ liệu lượt gọi giả trên nhiều ngày và nhiều tài khoản (slot 1, slot 2, API key), mở trang Usage bằng tài khoản chủ xưởng, rồi đối chiếu số trên ô tổng, chiều cao và màu cột, chú thích và bảng với dữ liệu đã tạo.

**Acceptance Scenarios**:

1. **Given** hôm nay có 12 lượt gọi (300.000 token) và 6 ngày trước đó có thêm 40 lượt, **When** chủ xưởng mở Usage, **Then** ô "Hôm nay" ghi 12 request · 300.000 token, và ô "7 ngày" ghi 52 request cùng tổng token của 7 ngày.
2. **Given** khoảng mặc định là 30 ngày, **When** trang mở, **Then** biểu đồ (mặc định: request) có đúng 30 cột (ngày không có lượt gọi là cột 0), cột xếp chồng theo tài khoản, và chú thích ghi tên từng tài khoản kèm tổng của nó trong khoảng.
3. **Given** chủ xưởng chọn "7 ngày", **When** trang cập nhật, **Then** biểu đồ còn 7 cột, ba bảng hiện có (theo tài khoản Claude, theo thành viên, theo ngày) và dòng tổng chỉ tính trong 7 ngày đó. Các ô tổng đầu trang không đổi.
4. **Given** chủ xưởng chọn từ 2026-11-01 đến 2026-11-10, **When** trang cập nhật, **Then** biểu đồ có 10 cột theo đúng các ngày đó, và địa chỉ trang giữ khoảng đã chọn (tải lại vẫn còn).
5. **Given** chủ xưởng di chuột hoặc chạm vào một cột, **When** chú giải hiện ra, **Then** nó ghi ngày, số của từng tài khoản và tổng.
6. **Given** chủ xưởng bấm "Xem dạng bảng", **When** bảng hiện ra, **Then** có một dòng mỗi ngày, một cột mỗi tài khoản và cột tổng, với cùng số liệu như biểu đồ.
7. **Given** biểu đồ đang ở loại Request, **When** chủ xưởng chọn "Token", **Then** cùng biểu đồ vẽ lại theo token (cột, trục, chú thích, chú giải, bảng), địa chỉ trang ghi loại Token, tải lại vẫn giữ.
8. **Given** một thành viên (không phải chủ xưởng), **When** mở Usage, **Then** bị chặn như hiện nay.

### Edge Cases

- Không có lượt gọi nào trong khoảng: biểu đồ thay bằng dòng "Chưa có lượt gọi nào trong khoảng này". Ô tổng ghi 0.
- Tài khoản Claude đã gỡ nhưng còn lượt gọi cũ: vẫn hiện, ghi "Slot N (đã gỡ)".
- Khoảng tự chọn sai (từ sau đến, ngày không hợp lệ, dài hơn 366 ngày): báo lỗi ngay cạnh ô chọn, giữ khoảng cũ.
- Số rất lớn (hàng trăm triệu token): trục và ô tổng viết gọn (ví dụ 1,2 tr), chú giải và bảng ghi số đầy đủ.
- Màn hình điện thoại (390 px): ô tổng xuống hàng, biểu đồ co theo bề ngang, không cuộn ngang cả trang.
- Chế độ tối: màu cột, trục và chữ vẫn đọc rõ.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Đầu trang Usage MUST có ba ô tổng "Hôm nay", "7 ngày", "30 ngày". Mỗi ô ghi số request Claude và số token. Các ô luôn tính tới hôm nay, không theo khoảng đang chọn.
- **FR-002**: Trang MUST có bộ chọn khoảng ngày: 7 ngày, 30 ngày (mặc định), 90 ngày, và tự chọn từ ngày đến ngày (tối đa 366 ngày). Khoảng đã chọn MUST nằm trong địa chỉ trang.
- **FR-003**: Khoảng đã chọn MUST áp dụng cho hai biểu đồ, dòng tổng và ba bảng hiện có.
- **FR-004**: Trang MUST có một biểu đồ cột theo ngày với nút chọn loại "Request" (mặc định) hoặc "Token"; đổi loại thì cùng biểu đồ vẽ lại theo loại đó, không tải lại trang, và loại đã chọn nằm trong địa chỉ trang. Mỗi ngày trong khoảng là một cột, kể cả ngày bằng 0. Cột xếp chồng theo nguồn gọi: Slot 1–5 và API key.
- **FR-005**: Mỗi nguồn gọi MUST có một màu cố định, giống nhau ở cả hai loại. Chú thích ghi tên nguồn (kèm email nếu có) và tổng của nó trong khoảng.
- **FR-006**: Di chuột, chạm hoặc dùng bàn phím vào một cột MUST hiện ngày, số theo từng nguồn và tổng.
- **FR-007**: Biểu đồ MUST có nút xem dạng bảng của loại đang chọn, cho cùng số liệu (dòng = ngày, cột = nguồn + tổng).
- **FR-008**: Ngày được tính theo giờ Việt Nam, giống các bảng hiện có.
- **FR-009**: Chỉ chủ xưởng xem được, như trang Usage hiện nay.
- **FR-010**: Trang MUST đọc được ở bề ngang 390 px và ở chế độ tối.

### Key Entities

- **Lượt gọi Claude** (đã có): thời điểm, nguồn gọi (slot hoặc API key), thành viên, việc, số token. Đây là nguồn duy nhất của mọi số trên trang.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Mở Usage, chủ xưởng đọc được số request và token hôm nay trong dưới 5 giây, không phải cuộn.
- **SC-002**: Với dữ liệu thử, mọi số trên ô tổng, chú thích, chú giải và bảng xem dạng số khớp 100% với dữ liệu đã tạo.
- **SC-003**: Đổi khoảng ngày hoặc loại thì biểu đồ và bảng cập nhật trong dưới 1 giây với 90 ngày dữ liệu (khoảng 50.000 lượt gọi).
- **SC-004**: Ở bề ngang 390 px không có cuộn ngang cả trang. Ở chế độ tối mọi chữ và cột đủ tương phản để đọc.

## Assumptions

- "Request" là một lượt gọi Claude mà xưởng đã ghi. Request REST/MCP qua API token không tính ở đây (chủ xưởng chưa chọn mục đó).
- Không thêm phần tách loại token (vào/ra/cache) hay mức hạn mức của slot. Đó là các mục chủ xưởng chưa chọn.
- Không lưu thêm dữ liệu mới. Chỉ đọc dữ liệu lượt gọi đã có.
- Biểu đồ vẽ bằng chính trang (không thêm thư viện ngoài), theo cách của tab Usage trong neb-creative-tool.
