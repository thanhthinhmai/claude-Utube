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

Hiến pháp chung đã viết sẵn ở `.specify/memory/constitution.md`. Sửa bằng `/speckit-constitution` nếu cần.
Xem `CLAUDE.md` để biết quy trình đầy đủ.

## Nguồn
Template và script lấy từ [github/spec-kit](https://github.com/github/spec-kit) (MIT).
