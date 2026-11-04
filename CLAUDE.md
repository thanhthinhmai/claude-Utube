# CLAUDE.md

Dự án này làm theo **Spec-Driven Development** của [GitHub Spec Kit](https://github.com/github/spec-kit).

## Luật bắt buộc
- Đọc `.specify/memory/constitution.md` trước khi lập kế hoạch hoặc viết code. Hiến pháp có hiệu lực cao nhất.
- Không viết code cho một tính năng khi chưa có `specs/<feature>/spec.md`, `plan.md` và `tasks.md` đã được người dùng duyệt.
- Chạy từng lệnh một. Sau mỗi lệnh, dừng lại tóm tắt kết quả và chờ người dùng duyệt.
- Chỗ nào chưa rõ thì hỏi, không đoán.

## Quy trình cho mỗi tính năng
| Bước | Lệnh | Kết quả |
|---|---|---|
| 1 | `/speckit-specify <mô tả>` | `specs/NNN-x/spec.md` + nhánh mới |
| 2 | `/speckit-clarify` | Câu hỏi làm rõ, câu trả lời được ghi vào spec |
| 3 | `/speckit-plan <công nghệ>` | `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` |
| 4 | `/speckit-tasks` | `tasks.md` |
| 5 | `/speckit-analyze` | Báo cáo mâu thuẫn (chỉ đọc) |
| 6 | `/speckit-implement` | Code |
| 7 | `/speckit-converge` | Thêm task cho phần còn thiếu. Lặp lại 6–7 đến khi `Converged` |

Lệnh phụ: `/speckit-checklist <lĩnh vực>` tạo checklist kiểm tra chất lượng spec (UX, bảo mật…). `/speckit-constitution` dùng để sửa hiến pháp.

## Cấu trúc
- `.specify/memory/constitution.md`: hiến pháp
- `.specify/templates/`: mẫu cho spec, plan, tasks, checklist
- `.specify/scripts/bash/`: script tạo nhánh và thư mục tính năng
- `.claude/skills/speckit-*/`: các lệnh `/speckit-*`
- `specs/NNN-ten-tinh-nang/`: tài liệu của từng tính năng
