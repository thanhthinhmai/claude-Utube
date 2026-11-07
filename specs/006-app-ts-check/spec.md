# Feature Specification: Kiểm lỗi kiểu cho code giao diện

**Feature Branch**: `006-app-ts-check`

**Created**: 2026-11-07

**Status**: Draft

**Input**: User description: "Add `// @ts-check` and JSDoc to the Film Studio UI script (tools/studio/studio/web/app.js) so type mistakes are caught early: in VS Code while editing, and by an automated test. Keep plain JavaScript with no build step (decision from the web session: no move to TypeScript). Light level."

## Bối cảnh

Giao diện Film Studio là một tệp JavaScript thuần (`app.js`, khoảng 440 dòng), không có bước biên dịch. Đây là quyết định đã chốt: không chuyển dự án sang TypeScript. Lỗi gõ sai tên thuộc tính hay dùng sai loại phần tử hiện chỉ lộ ra khi chạy giao diện. Bật kiểm lỗi kiểu ngay trong tệp JavaScript giúp thấy lỗi sớm mà vẫn giữ nguyên cách chạy. Lần chạy thử (2026-11-07) đếm được 27 lỗi kiểu, hầu hết do code chưa ghi rõ loại phần tử trên trang (ô nhập, nút, ảnh).

Mức quy trình: **Nhẹ** (1–3 tệp, không đổi hành vi, dữ liệu hay API).

Người dùng đã chốt (2026-11-07): kiểm **cả hai** chỗ: VS Code gạch đỏ khi mở tệp, và một test tự động. Test cần tải công cụ kiểm kiểu lần đầu (cần mạng). Không có mạng thì bỏ qua test, không báo lỗi.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Lỗi kiểu lộ ra trước khi chạy giao diện (Priority: P1)

Người sửa giao diện (Claude hoặc người dùng) mở `app.js` trong VS Code. Chỗ dùng sai kiểu được gạch đỏ ngay. Khi chạy bộ test giao diện, test kiểm kiểu báo lỗi nếu có. Nhờ vậy lỗi bị bắt trước khi người dùng thấy giao diện hỏng.

**Why this priority**: Đây là toàn bộ giá trị của tính năng.

**Independent Test**: Chạy bộ test giao diện: test kiểm kiểu đạt với 0 lỗi. Thêm tạm một dòng sai kiểu (ví dụ gán số cho thuộc tính chữ) thì test báo lỗi, chỉ ra đúng dòng.

**Acceptance Scenarios**:

1. **Given** `app.js` hiện tại, **When** chạy bộ test giao diện có mạng, **Then** test kiểm kiểu đạt với 0 lỗi.
2. **Given** một dòng sai kiểu được thêm vào `app.js`, **When** chạy test, **Then** test thất bại và thông báo chứa số dòng sai.
3. **Given** không có mạng và chưa có công cụ kiểm kiểu trong bộ nhớ đệm, **When** chạy bộ test giao diện, **Then** test kiểm kiểu được bỏ qua kèm lý do, các test khác vẫn chạy và kết quả chung vẫn đạt.
4. **Given** mở `app.js` trong VS Code, **When** có chỗ sai kiểu, **Then** VS Code gạch đỏ chỗ đó mà không cần cài thêm gì.
5. **Given** giao diện sau khi sửa, **When** chạy các test giao diện hiện có (kể cả test trình duyệt), **Then** tất cả vẫn đạt: hành vi không đổi.

### Edge Cases

- Công cụ kiểm kiểu dùng một phiên bản cố định, để kết quả không đổi theo ngày chạy.
- Tệp `app.js` vẫn chạy thẳng trong trình duyệt, không qua bước biên dịch nào.
- Test không ghi tệp nào vào thư mục dự án (không có `node_modules/` hay `package.json` mới trong repo).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `app.js` MUST bật kiểm lỗi kiểu ngay trong tệp và có 0 lỗi kiểu ở mức kiểm thường (không bật chế độ nghiêm ngặt).
- **FR-002**: Các chỗ cần ghi rõ kiểu MUST dùng chú thích trong JavaScript, không đổi logic hay chữ hiển thị.
- **FR-003**: Bộ test giao diện MUST có một test kiểm kiểu `app.js` bằng công cụ phiên bản cố định. Test thất bại khi có lỗi và in các dòng lỗi.
- **FR-004**: Khi không lấy được công cụ kiểm kiểu (không có mạng, không có node), test MUST bỏ qua kèm lý do thay vì thất bại.
- **FR-005**: Không thêm bước biên dịch, không thêm tệp cấu hình gói vào repo, không chuyển sang TypeScript.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Kiểm kiểu `app.js` cho 0 lỗi (từ 27 lỗi hiện tại).
- **SC-002**: Thêm một lỗi kiểu mẫu thì test thất bại trong lần chạy kế tiếp.
- **SC-003**: Cả 3 bộ test hiện có vẫn đạt; tổng số test giao diện tăng thêm 1.
- **SC-004**: Không có tệp mới ngoài test kiểm kiểu và tài liệu của tính năng.

## Assumptions

- Máy có `node` và `npx` (đã cần cho test trình duyệt); thiếu thì test bỏ qua.
- Bản tải về của công cụ kiểm kiểu nằm trong bộ nhớ đệm của npm ở thư mục người dùng, không nằm trong dự án.
- Chỉ kiểm `app.js`. Code Python đã có test riêng, không thuộc phạm vi này.
