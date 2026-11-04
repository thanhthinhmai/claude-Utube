# Hiến pháp dự án (Spec Project)

Bộ nguyên tắc bất biến cho mọi tính năng: web app, tool hay game. Các lệnh
`/speckit-plan`, `/speckit-analyze` và `/speckit-converge` đều kiểm tra theo file này.
Vi phạm một nguyên tắc **PHẢI** được coi là lỗi nghiêm trọng nhất.

## Nguyên tắc cốt lõi

### I. Spec là nguồn sự thật
- Mọi tính năng **PHẢI** bắt đầu từ `spec.md` (cái gì và vì sao). Không viết code khi chưa có spec đã duyệt.
- Spec **KHÔNG ĐƯỢC** nhắc công nghệ. Công nghệ chỉ nằm trong `plan.md`.
- Khi yêu cầu thay đổi: sửa spec trước, rồi mới sửa plan, tasks và code.

### II. Không đoán
- Mọi chỗ mơ hồ **PHẢI** được đánh dấu `[NEEDS CLARIFICATION: câu hỏi]` và hỏi người dùng.
- Không tự thêm tính năng "có thể cần sau này" (YAGNI).

### III. MVP trước, chia theo user story
- User story được xếp ưu tiên P1, P2, P3. P1 **PHẢI** tự chạy được và tự test được, tạo thành một MVP.
- Làm xong và kiểm chứng xong một story rồi mới chuyển sang story tiếp theo.

### IV. Đo được, kiểm chứng được
- Mỗi tiêu chí thành công **PHẢI** đo được bằng số liệu, ví dụ thời gian, FPS, số bước thao tác, tỷ lệ lỗi. Không dùng các từ như "đẹp" hay "nhanh".
- Logic quan trọng **PHẢI** có test tự động. Với UI và game, **PHẢI** có thêm bước chạy thử thật, chụp màn hình hoặc quay lại để đối chiếu.
- Không được báo "xong" khi chưa chạy kiểm chứng. Kết quả kiểm chứng ghi rõ: đạt, đạt một phần, hoặc thất bại.

### V. Đơn giản
- Bắt đầu với cấu trúc tối thiểu: tối đa 3 project hoặc package, dùng framework trực tiếp, không bọc thêm lớp trừu tượng khi chưa cần.
- Mọi độ phức tạp vượt mức **PHẢI** được giải thích trong mục "Complexity Tracking" của `plan.md`.

## Ràng buộc bổ sung

- **Bảo mật:** không commit secret hay API key. Dữ liệu người dùng phải được kiểm tra hợp lệ ở biên hệ thống.
- **Hiệu năng (mặc định):** web tương tác dưới 200 ms, game giữ 60 FPS trên máy tầm trung. Từng spec có thể ghi đè con số này.
- **Tài sản:** font, hình, âm thanh và mô hình phải có giấy phép rõ ràng (ví dụ CC0, MIT) và được ghi nguồn.
- **Ngôn ngữ:** tài liệu spec viết bằng tiếng Việt hoặc tiếng Anh. Code và tên biến dùng tiếng Anh.

## Quy trình làm việc

1. `/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement` → `/speckit-converge`.
2. Người dùng duyệt kết quả sau mỗi bước rồi mới chạy bước tiếp theo.
3. Mỗi tính năng nằm trên nhánh riêng `NNN-ten-tinh-nang` và thư mục riêng `specs/NNN-ten-tinh-nang/`.
4. Commit sau mỗi giai đoạn trong `tasks.md` hoàn thành.

## Quản trị

- Hiến pháp này có hiệu lực cao hơn mọi hướng dẫn khác trong dự án.
- Muốn sửa hiến pháp thì phải ghi lý do, được người dùng duyệt và tăng số phiên bản.

**Version**: 1.0.0 | **Ratified**: 2026-11-04 | **Last Amended**: 2026-11-04
