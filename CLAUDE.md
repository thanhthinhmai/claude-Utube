# CLAUDE.md

**claude-Utube** là một xưởng phim cho Claude. Xưởng xây bằng **Spec-Driven Development** của [GitHub Spec Kit](https://github.com/github/spec-kit).

## Các luồng làm việc
Mỗi yêu cầu đi đúng **một** luồng:

| Người dùng muốn | Luồng |
|---|---|
| Làm một bộ phim, video, clip (theo phong cách thư viện hoặc phong cách riêng), kể cả kênh, chọn đề, gói đăng, sửa theo ghi chú phim | **Làm phim**: làm theo skill `.claude/skills/film-make/SKILL.md`. Không tạo spec cho từng phim |
| Học phong cách của một kênh YouTube, danh sách video hoặc file video mẫu | **Học phong cách**: làm theo skill `.claude/skills/style-learn/SKILL.md`. Không tạo spec |
| Xây hoặc sửa skill, công cụ, cấu trúc của xưởng | **Spec-kit** (các mục bên dưới) |

### Chạy app trên máy (specs/014, nền cho app desktop)
- `sh bin/studio app start` chạy cả xưởng (giao diện, proxy, worker) trên máy này, không cần Docker, rồi in `URL: http://127.0.0.1:<cổng>`. Dữ liệu nằm ở `~/.local/share/claude-utube` (đổi bằng `--data`), không ghi vào thư mục dự án. Lần đầu mở: tạo chủ xưởng, rồi đăng nhập tài khoản Claude của chính người dùng ở AI accounts.
- `app status` · `app stop` (còn việc đang chạy thì từ chối, `--force` để dừng) · `app models` (tải mô hình Whisper) · `app import` (chép `films/`, `my-styles/`, `channels/` của dự án vào app).
- Khi app đang chạy, việc của luồng làm phim bằng chat (`job …`, `review …`) ghi vào sổ việc của app: xem và duyệt trên app; phim xong được chép (hard link) vào kho của chủ xưởng.

### App desktop, bộ cài, license, Client (specs/015–018)
- 015: vỏ Electron trong `desktop/`, chỉ gọi `sh bin/studio app …` (macOS chạy thẳng, Windows qua WSL2). 016: bộ cài chứa sẵn phần lõi. 017: máy chủ license `tools/license/`, lease Ed25519, tự cập nhật. 018: chế độ Host/Client, ghép đôi bằng mã một lần.
- Chi tiết (lệnh chạy khi phát triển, test, phát hành, khoá) ở `desktop/CLAUDE.md`. Khoá riêng ký license **không bao giờ** vào repo hay vào chat.

## Luật bắt buộc
- Đọc `.specify/memory/constitution.md` trước khi lập kế hoạch hoặc viết code. Hiến pháp có hiệu lực cao nhất.
- Trước khi làm, **chọn mức quy trình** theo bảng dưới và báo cho người dùng một dòng, ví dụ: "Mức: Nhẹ, vì chỉ sửa 2 file". Người dùng có thể yêu cầu đổi mức.
- Ở mức Nhẹ và Đầy đủ: không viết code khi spec và plan chưa được người dùng duyệt.
- Chạy từng lệnh một. Sau mỗi lệnh, dừng lại tóm tắt kết quả và chờ người dùng duyệt.
- Chỗ nào chưa rõ thì hỏi, không đoán.
- Không sửa file nào trong `lib/` (hiến pháp VI). Muốn dùng phiên bản thư viện mới thì đổi `library.lock` theo quy trình spec-kit.

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
- `bin/studio`: mọi lệnh của xưởng, xem `sh bin/studio --help`; lệnh làm phim ở skill `film-make`. Test: `sh tests/run.sh`, `sh tests/render/run.sh`, `sh tests/learn/run.sh`, `sh tests/ui/run.sh`, `sh tests/filmcheck/run.sh`, `sh tests/online/run.sh`, `sh tests/license/run.sh` (bài chạy thật, tốn tiền: `sh tests/online/live.sh`)
- `tools/`: công cụ tự viết (`studio/` giao diện và API, `runner/` worker, proxy, agent của chế độ online, `filmcheck/` kiểm phim và gói đăng, `render/` dựng hình, `style-learn/` học phong cách, `license/`); chi tiết ở `tools/CLAUDE.md`
- `library.lock`: phiên bản thư viện đã ghim; `lib/lemo-opuscar/`: thư viện (không vào git, không sửa)
- `channels/`: hồ sơ kênh của chính xưởng và bài học (vào git, specs/012) · `people/`: thư viện người thật (hình vẽ và duyệt vào git, ảnh tham chiếu trong `.sheet/` không vào git; `tools/filmcheck/people.py`, specs/028) · `my-styles/`: phong cách riêng (vào git) · `films/`: phim (không vào git) · `references/`: video tham chiếu (không vào git) · `tools/`: công cụ tự viết
- `desktop/`: app desktop (Electron, specs/015) · `CREDITS`: giấy phép của phần mềm bên thứ ba
- `.specify/memory/constitution.md`: hiến pháp
- `.specify/templates/`: mẫu cho spec, plan, tasks, checklist
- `.specify/scripts/bash/`: script tạo nhánh và thư mục tính năng
- `.claude/skills/speckit-*/`: các lệnh `/speckit-*`
- `specs/NNN-ten-tinh-nang/`: tài liệu của từng tính năng
