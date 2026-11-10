# CLAUDE.md

**claude-Utube** là một xưởng phim cho Claude. Xưởng xây bằng **Spec-Driven Development** của [GitHub Spec Kit](https://github.com/github/spec-kit).

## Các luồng làm việc
Mỗi yêu cầu đi đúng **một** luồng:

| Người dùng muốn | Luồng |
|---|---|
| Làm một bộ phim, video, clip (theo phong cách thư viện hoặc phong cách riêng) | **Làm phim** (bên dưới). Không tạo spec cho từng phim |
| Học phong cách của một kênh YouTube, danh sách video hoặc file video mẫu | **Học phong cách**: làm theo skill `.claude/skills/style-learn/SKILL.md`. Không tạo spec |
| Xây hoặc sửa skill, công cụ, cấu trúc của xưởng | **Spec-kit** (các mục bên dưới) |

### Luồng làm phim
1. Chạy `sh bin/studio status`. Nếu chưa sẵn sàng thì chạy `sh bin/studio setup` và báo người dùng công cụ còn thiếu (xưởng không tự cài phần mềm hệ thống).
2. Đọc `lib/lemo-opuscar/AGENTS.md` và làm theo, **ở chế độ skill** của thư viện, với các điểm thay thế sau:
   - `LIB` = đường dẫn tuyệt đối tới `lib/lemo-opuscar`. Chạy công cụ thư viện từ `$LIB`; `build.sh` ghi `LIB=<đường dẫn>` ở đầu, không dùng `../..`.
   - Thư mục phim = `films/<tên>/` của dự án (chữ thường, số, gạch nối). Nội dung `films/` không vào git.
   - Phong cách riêng: đọc danh mục `my-styles/README.md` và lưu vào `my-styles/<slug>/`, **thay cho** `~/lemo-my-styles/`.
   - Cài gói của thư viện bằng `sh bin/studio deps [voice] [music]`, **không** chạy thẳng `setup.sh` của thư viện (nó sẽ tải một bản thư viện khác vào `~/lemo-opuscar`).
3. **Kịch bản được chấm** (specs/010, phim có lời đọc), xen vào quy trình của thư viện:
   - Sau bước Brief: ghi `films/<tên>/BRIEF.md` (tóm tắt yêu cầu, tối đa 2000 ký tự).
   - Sau `TREATMENT.md`, trước giọng đọc: viết `SCRIPT.md` và `SOURCES.md` theo `specs/010-script-review-qc/contracts/files.md`. Tìm số liệu bằng WebSearch (tối đa 5 lượt); mở mọi đường dẫn được dẫn bằng `sh bin/studio web fetch <url> --film <tên>`.
   - `sh bin/studio script check <tên>` tới khi đạt, rồi `sh bin/studio script review <tên>`. Mã 1: chỉ sửa các đoạn bị ghi P1 hoặc P2, rồi chạy lại. Mã 3 (hết 2 vòng sửa): dừng, báo người dùng điểm cuối và các lỗi còn lại.
   - Phim không có lời đọc: `sh bin/studio script skip <tên> --reason "no narration"`.
   - Lời của `lines.json` lấy đúng từ kịch bản đã đạt; xong giọng thì ghi `narration.json`.
4. Không sửa file nào trong `lib/` (hiến pháp VI). Muốn dùng phiên bản thư viện mới thì đổi `library.lock` theo quy trình spec-kit.
5. **Ghi việc lên giao diện** (`specs/003-studio-ui/contracts/skill-integration.md`):
   - Khi đã có tên phim: `sh bin/studio job start --kind film --name <tên> --film <tên>`; lưu dòng đầu (mã việc) vào `films/<tên>/.job`; in dòng `URL: …` cho người dùng ("Theo dõi trên giao diện: <URL>").
   - Đầu mỗi giai đoạn: `sh bin/studio job step <mã> "<giai đoạn>"`, ghi đúng một trong các tên tiếng Anh: `Treatment`, `Script`, `Look`, `Storyboard`, `Voice`, `Music`, `Picture`, `Mix`, `Render`, `Self-check`.
   - Lệnh dài (render, mux, tạo giọng): bọc bằng `sh bin/studio job run <mã> --step "<giai đoạn>" -- <lệnh…>` (cùng danh sách tên trên).
   - Xong: `sh bin/studio job done <mã> --film <tên>`; lỗi không tự sửa được: `sh bin/studio job fail <mã> "<lỗi>"`.
   - Storyboard (nếu người dùng yêu cầu) vẫn duyệt trong khung chat.
   - `job start` báo chưa cài giao diện (mã 1): bỏ qua các lệnh `job`, làm phim như cũ, gợi ý một lần `sh bin/studio deps ui`.

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
- `bin/studio`: `setup` · `status [--json]` · `deps [voice] [music]` · `deps learn [--extra]` · `learn <lệnh>` · `deps ui` · `ui [open|status|stop]` · `job …` · `review …` · `deps online` · `admin create <email>` · `online up|down|logs|admin <email>`; test: `sh tests/run.sh`, `sh tests/learn/run.sh`, `sh tests/ui/run.sh`, `sh tests/online/run.sh` (bài chạy thật, tốn tiền: `sh tests/online/live.sh`)
- `tools/studio/`: giao diện web và API v1 (chỉ `127.0.0.1`), sổ việc và yêu cầu duyệt trong `.studio/` (không vào git)
- Chế độ online (specs/007, specs/008, `STUDIO_MODE=online`): xưởng nội bộ chạy bằng gói Claude Pro/Max của chủ xưởng. Tài khoản, hạn mức, việc và từng lần gọi Claude nằm trong SQLite ở `$STUDIO_DATA`; đăng nhập các tài khoản Claude nằm ở `$STUDIO_DATA/claude/slot-<n>` (quyền 700, không vào git, không vào container). `tools/studio/studio/claude_plan.py`: đăng nhập, làm mới mã, chọn tài khoản. Không có đăng ký công khai: chủ xưởng thêm người trong Settings → Users. `tools/runner/` gồm `worker.py` (hàng đợi, chạy mỗi việc trong một container), `proxy.py` (đổi mã của việc sang tài khoản Claude dùng ít nhất, khoá API chỉ là dự phòng, ghi token) và `agent.py` (Claude Agent SDK trong container). Mã API (specs/009): `tools/studio/studio/tokens.py` (mã, nhật ký, vé dùng một lần, Idempotency-Key); mỗi người tự tạo mã ở Your account, Owner xem và thu hồi ở Settings → API tokens; Settings → Worker xem worker và việc gần nhất. Máy chủ MCP ở `/api/mcp` (`tools/studio/studio/mcp_server.py`, chỉ nhận mã): mỗi công cụ là một lệnh REST với cùng mã. `deploy/` chứa Dockerfile, `compose.yaml`, Caddyfile và hướng dẫn `deploy/README.md`
- `tools/style-learn/`: công cụ đo và lưu phong cách (venv riêng `tools/.venv`, không vào git); skill `.claude/skills/style-learn/`
- `library.lock`: phiên bản thư viện đã ghim; `lib/lemo-opuscar/`: thư viện (không vào git, không sửa)
- `my-styles/`: phong cách riêng (vào git) · `films/`: phim (không vào git) · `references/`: video tham chiếu (không vào git) · `tools/`: công cụ tự viết
- `.specify/memory/constitution.md`: hiến pháp
- `.specify/templates/`: mẫu cho spec, plan, tasks, checklist
- `.specify/scripts/bash/`: script tạo nhánh và thư mục tính năng
- `.claude/skills/speckit-*/`: các lệnh `/speckit-*`
- `specs/NNN-ten-tinh-nang/`: tài liệu của từng tính năng
