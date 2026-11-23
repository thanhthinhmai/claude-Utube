# Tasks: CLAUDE.md gọn

**Input**: `specs/031-slim-claude-md/` (spec.md, plan.md)

## Phase 1: User Story 1 - Phiên thường nạp ít hơn, phim vẫn làm đúng (P1) 🎯 MVP

**Independent Test**: `python3 specs/031-slim-claude-md/check_split.py`

- [x] T001 [US1] Viết specs/031-slim-claude-md/check_split.py: đọc bản cũ bằng `git show main:CLAUDE.md`, bỏ tiêu đề và dòng trống, kiểm từng dòng có nguyên văn trong CLAUDE.md, .claude/skills/film-make/SKILL.md, desktop/CLAUDE.md, tools/CLAUDE.md (ngoại lệ có lý do); in số dòng thiếu, kích thước CLAUDE.md; mã 1 nếu thiếu dòng hoặc CLAUDE.md > 9000 byte
- [x] T002 [P] [US1] Tạo .claude/skills/film-make/SKILL.md: frontmatter `name: film-make`, `description` (làm phim, video, clip theo phong cách thư viện hoặc riêng; kênh, chọn đề, gói đăng, sửa theo ghi chú phim); nguyên văn bước 1–5, 2a, 2b, 3, 3a, 3b, 3c của "Luồng làm phim" và dòng lệnh `bin/studio` của "Cấu trúc"
- [x] T003 [P] [US1] Tạo desktop/CLAUDE.md: nguyên văn mục 015, 016, 017, 018
- [x] T004 [P] [US1] Tạo tools/CLAUDE.md: nguyên văn các dòng `tools/studio/`, chế độ online, `tools/filmcheck/`, `tools/render/`, `tools/style-learn/` của "Cấu trúc"
- [x] T005 [US1] Viết lại CLAUDE.md gốc theo plan.md (bảng luồng trỏ skill, 015–018 tóm tắt + trỏ, luật "không sửa `lib/`", ba mục quy trình giữ nguyên, bản đồ thư mục ngắn)
- [x] T006 [US1] Đổi tham chiếu "luồng làm phim của `CLAUDE.md`" trong .claude/skills/style-learn/SKILL.md sang skill film-make; grep toàn repo (trừ specs/, lib/, tools/.venv) để chắc 0 tham chiếu còn lại
- [x] T007 [US1] Chạy check_split.py tới khi đạt (SC-001, SC-002, SC-003)

## Phase 2: Polish

- [x] T008 Chạy 5 bộ test (`tests/run.sh`, `tests/learn/run.sh`, `tests/ui/run.sh`, `tests/filmcheck/run.sh`, `tests/online/run.sh`) (SC-004)

## Dependencies

T002–T004 song song; T005 sau T002–T004; T007 sau T001, T005, T006; T008 cuối.
