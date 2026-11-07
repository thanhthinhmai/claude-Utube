# Tasks: Bước và nhật ký việc bằng tiếng Anh trên Film Studio

**Input**: `specs/005-english-job-log/` (spec.md, plan.md, quickstart.md)

**Tests**: có, theo SC-001 (test tự động đủ vòng).

## Phase 1: Setup và Phase 2: Foundational

Không có việc: không thêm gói, không đổi cấu trúc.

## Phase 3: User Story 1 - Đọc tiến độ việc bằng một thứ tiếng (P1) 🎯 MVP

**Goal**: Mọi dòng và tên bước do xưởng ghi bằng tiếng Anh; chỉ dẫn ghi bước dùng danh sách chuẩn.

**Independent Test**: test đủ vòng ở T001 đạt; `grep` ở quickstart cho thấy chỉ còn tên bước chuẩn.

### Test

- [X] T001 [US1] Thêm `test_english_lines` vào `tests/ui/test_cli_events.py`. Test chạy start → `job step` "Treatment", "Music" (có `--progress 1/2`), → `review request` style-1 → quyết định approve qua API (`source` ui) → `review wait` → `review request` style-2 có `--final-round` (cần ghi sẵn `references/demo-set/proof/compare.json` trong project thử) → `review decide --value revise --note "darker" --source chat` → `review wait` → `job run --step "Render" -- sh -c 'echo hello; exit 3'` → `job done`. Kiểm đúng các dòng: `Job started`, `Review 1 requested`, `Review 1: Approve (via UI)`, `Resumed after review 1: Approve`, `Review 2: Request changes (via chat): darker`, `(command exited with code 3)`, `Done`; bước lúc chờ là `Waiting for review 1`. Thêm kiểm mọi dòng trong nhật ký đều là ASCII. Trong `test_job_commands`, đổi `"mã 7"` thành `"code 7"`. Một việc mới phải có bước `Starting`. Test phải fail trước T002–T004.

### Code

- [X] T002 [P] [US1] Trong `tools/studio/studio/jobs.py`, đổi bước đầu thành `"Starting"` và dòng đầu thành `"Job started"`. Đổi bước cuối thành `{"done": "Done", "failed": "Failed", "stopped": "Stopped"}`. Nội dung lỗi của `job fail` vẫn ghi vào nhật ký như cũ (FR-001, FR-004).
- [X] T003 [P] [US1] Trong `tools/studio/studio/reviews.py`:
  - `KINDS = {"style-1": "review 1", "style-2": "review 2"}`.
  - `LABEL` = Approve / Request changes / Accept anyway / Stop, trùng `DECISION` trong `tools/studio/studio/web/app.js`.
  - Bước `Waiting for review n`.
  - Dòng `Review n requested`, `Review n: <label> (via UI|via chat)[: note]`, `Resumed after review n: <label>` (viết hoa chữ đầu `Review`; trong dòng Resumed thì viết thường).

  Thông báo lỗi giữ nguyên (FR-001).
- [X] T004 [P] [US1] Trong `tools/studio/studio_cli.py`, đổi dòng cuối của `job_run` thành `f"(command exited with code {rc})"`. Các thông báo terminal giữ tiếng Việt (FR-001, FR-004).

### Tài liệu

- [X] T005 [P] [US1] Trong `CLAUDE.md` dòng 24–25, đổi danh sách giai đoạn thành `Treatment`, `Look`, `Storyboard`, `Voice`, `Music`, `Picture`, `Mix`, `Render`, `Self-check`. Ghi rõ "ghi đúng tên tiếng Anh này" (FR-002).
- [X] T006 [P] [US1] Trong `.claude/skills/style-learn/SKILL.md`, đổi 10 tên bước:
  - `Tải video` → `Fetch videos`
  - `Đo video` → `Measure videos`
  - `Chép lời` → `Transcribe`
  - `Tổng hợp` → `Summarize`
  - `Báo hồ sơ đo` → `Report measurements`
  - `Phân tích (3 agent)` → `Analysis (3 agents)`
  - `Kiểm tra chéo` → `Cross-check`
  - `Viết bản phong cách` → `Write style`
  - `Khung chứng minh vòng <n>` → `Proof frame round <n>`
  - `Lưu phong cách` → `Save style`

  Phần chữ còn lại giữ nguyên (FR-003).
- [X] T007 [P] [US1] Trong `specs/003-studio-ui/contracts/skill-integration.md`, đổi tên bước ví dụ. Thêm mục "Chữ trên trang Jobs" gồm bảng FR-001 và hai danh sách bước chuẩn. Ghi chú: tóm tắt duyệt, thông báo terminal và dòng lệnh con không đổi (FR-005).

**Checkpoint**: T001 đạt.

## Phase 4: Polish

- [X] T008 Chạy `sh tests/ui/run.sh`, `sh tests/run.sh`, `sh tests/learn/run.sh`; chạy `grep` ở `specs/005-english-job-log/quickstart.md`. Đối chiếu SC-001 đến SC-004, trong đó SC-004 là việc cũ có dòng tiếng Việt vẫn mở được qua `job show`.

## Dependencies

T001 trước → T002, T003, T004 song song (khác tệp) → T005, T006, T007 song song (độc lập với code) → T008 cuối.

## Implementation Strategy

Một story, một lần giao: T001 (test đỏ) → T002–T004 (test xanh) → tài liệu → T008.
