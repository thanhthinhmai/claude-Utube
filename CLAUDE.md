# CLAUDE.md

**claude-Utube** là một xưởng phim cho Claude. Xưởng xây bằng **Spec-Driven Development** của [GitHub Spec Kit](https://github.com/github/spec-kit).

## Các luồng làm việc
Mỗi yêu cầu đi đúng **một** luồng:

| Người dùng muốn | Luồng |
|---|---|
| Làm một bộ phim, video, clip (theo phong cách thư viện hoặc phong cách riêng) | **Làm phim** (bên dưới). Không tạo spec cho từng phim |
| Học phong cách của một kênh YouTube hoặc một video mẫu | **Học phong cách**: **chưa có** (tính năng 002). Báo người dùng là chưa xây, không làm tạm |
| Xây hoặc sửa skill, công cụ, cấu trúc của xưởng | **Spec-kit** (các mục bên dưới) |

### Luồng làm phim
1. Chạy `sh bin/studio status`. Nếu chưa sẵn sàng thì chạy `sh bin/studio setup` và báo người dùng công cụ còn thiếu (xưởng không tự cài phần mềm hệ thống).
2. Đọc `lib/lemo-opuscar/AGENTS.md` và làm theo, **ở chế độ skill** của thư viện, với các điểm thay thế sau:
   - `LIB` = đường dẫn tuyệt đối tới `lib/lemo-opuscar`. Chạy công cụ thư viện từ `$LIB`; `build.sh` ghi `LIB=<đường dẫn>` ở đầu, không dùng `../..`.
   - Thư mục phim = `films/<tên>/` của dự án (chữ thường, số, gạch nối). Nội dung `films/` không vào git.
   - Phong cách riêng: đọc danh mục `my-styles/README.md` và lưu vào `my-styles/<slug>/`, **thay cho** `~/lemo-my-styles/`.
   - Cài gói của thư viện bằng `sh bin/studio deps [voice] [music]`, **không** chạy thẳng `setup.sh` của thư viện (nó sẽ tải một bản thư viện khác vào `~/lemo-opuscar`).
3. Không sửa file nào trong `lib/` (hiến pháp VI). Muốn dùng phiên bản thư viện mới thì đổi `library.lock` theo quy trình spec-kit.

## Luật bắt buộc
- Đọc `.specify/memory/constitution.md` trước khi lập kế hoạch hoặc viết code. Hiến pháp có hiệu lực cao nhất.
- Trước khi làm, **chọn mức quy trình** theo bảng dưới và báo cho người dùng một dòng, ví dụ: "Mức: Nhẹ, vì chỉ sửa 2 file". Người dùng có thể yêu cầu đổi mức.
- Ở mức Nhẹ và Đầy đủ: không viết code khi spec và plan chưa được người dùng duyệt.
- Chạy từng lệnh một. Sau mỗi lệnh, dừng lại tóm tắt kết quả và chờ người dùng duyệt.
- Chỗ nào chưa rõ thì hỏi, không đoán.

## Chọn mức quy trình (để tiết kiệm token)

| Mức | Khi nào | Các bước |
|---|---|---|
| **Trực tiếp** | Sửa bug nhỏ đã rõ nguyên nhân, đổi chữ hoặc CSS, đổi cấu hình; ≤ 1–2 file và không đổi hành vi chính | Sửa luôn, chạy test hoặc chạy thử, báo kết quả. Không tạo spec |
| **Nhẹ** | Tính năng nhỏ, ~1–5 file, yêu cầu đã rõ, không đổi dữ liệu hay API dùng chung | `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement` |
| **Đầy đủ** | Tính năng hoặc ứng dụng mới, game hoặc module mới, đổi dữ liệu hoặc API, yêu cầu còn mơ hồ, hoặc người dùng yêu cầu | Cả 7 bước ở bảng dưới |

Quy tắc nâng mức:
- Đang ở mức Trực tiếp mà thấy cần sửa hơn 2 file hoặc đổi hành vi chính → dừng lại, đề xuất chuyển sang mức Nhẹ.
- Đang ở mức Nhẹ mà spec còn từ 2 chỗ `[NEEDS CLARIFICATION]` trở lên, hoặc tasks vượt khoảng 15 việc → đề xuất chuyển sang mức Đầy đủ.
- Đang không chắc giữa hai mức → chọn mức cao hơn.

Ở mức Nhẹ:
- Spec chỉ cần user story P1, yêu cầu chính và tiêu chí thành công đo được.
- Bỏ qua `research.md` và `contracts/` nếu không cần.
- Sau khi implement, tự đối chiếu nhanh với tiêu chí thành công thay cho `/speckit-converge`.

Mẹo chung để tiết kiệm token:
- Chỉ dùng `/speckit-checklist` khi người dùng yêu cầu.
- Mỗi tính năng nên làm trong một phiên mới.
- Đọc tài liệu theo từng phần cần thiết, không đọc lại cả file khi không cần.

## Quy trình đầy đủ
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
- `bin/studio`: `setup` · `status [--json]` · `deps [voice] [music]`; test: `sh tests/run.sh`
- `library.lock`: phiên bản thư viện đã ghim; `lib/lemo-opuscar/`: thư viện (không vào git, không sửa)
- `my-styles/`: phong cách riêng (vào git) · `films/`: phim (không vào git) · `references/`: video tham chiếu (không vào git) · `tools/`: công cụ tự viết
- `.specify/memory/constitution.md`: hiến pháp
- `.specify/templates/`: mẫu cho spec, plan, tasks, checklist
- `.specify/scripts/bash/`: script tạo nhánh và thư mục tính năng
- `.claude/skills/speckit-*/`: các lệnh `/speckit-*`
- `specs/NNN-ten-tinh-nang/`: tài liệu của từng tính năng
