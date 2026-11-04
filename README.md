# Spec Project

Khung dự án viết code theo **Spec-Driven Development** (GitHub Spec Kit), tích hợp sẵn Claude Code.
Dùng cho web app, tool hoặc game.

## Bắt đầu
Mở Claude Code trong thư mục này và chạy lần lượt (duyệt kết quả sau mỗi bước):

```text
/speckit-specify Ứng dụng quản lý chi tiêu cá nhân: nhập khoản chi, xem tổng theo tháng.
/speckit-clarify
/speckit-plan Dùng Vite + React + TypeScript, lưu dữ liệu bằng IndexedDB.
/speckit-tasks
/speckit-analyze
/speckit-implement
/speckit-converge
```

Không phải lúc nào cũng cần đủ 7 bước. Claude tự chọn một trong 3 mức tuỳ độ lớn của yêu cầu:
- **Trực tiếp:** sửa nhỏ, không cần spec.
- **Nhẹ:** specify → plan → tasks → implement.
- **Đầy đủ:** cả 7 bước.

Bạn có thể nói rõ mức muốn dùng, ví dụ: "làm mức nhẹ".

Hiến pháp chung đã viết sẵn ở `.specify/memory/constitution.md`. Sửa bằng `/speckit-constitution` nếu cần.
Xem `CLAUDE.md` để biết quy trình đầy đủ.

## Nguồn
Template và script lấy từ [github/spec-kit](https://github.com/github/spec-kit) (MIT).
