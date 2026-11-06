# Tasks: Khung xưởng phim (Studio Skeleton)

**Input**: Design documents from `specs/001-studio-skeleton/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/studio-cli.md, quickstart.md

**Tests**: Bắt buộc theo hiến pháp IV (logic quan trọng phải có test tự động). Mọi test nằm trong `tests/run.sh` và chạy offline.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Tạo `library.lock` ở gốc với `LIB_REPO=https://github.com/lemomo-ai/lemo-opuscar.git` và `LIB_COMMIT=bebbbe1aa92a3cb4bb6f83500e61b23a17d1aa00` (SHA "đúng 40 ký tự hex")
- [X] T002 [P] Tạo `my-styles/README.md`, `tools/README.md`, `films/README.md`, `references/README.md` mô tả vai trò từng thư mục (phong cách riêng theo khung 11 mục; phim chỉ nằm trên máy; video tham chiếu chỉ để học, không chia sẻ)
- [X] T003 [P] Cập nhật `.gitignore`: bỏ qua `lib/`, `films/*` và `references/*` trừ `README.md`, cùng mọi file `*.mp4 *.mov *.webm *.mkv *.wav *.mp3 *.m4a`

## Phase 2: Foundational (Blocking Prerequisites)

- [X] T004 Tạo khung `bin/studio` (POSIX sh, `set -eu`): tìm gốc dự án từ vị trí script (chạy được từ thư mục con, đường dẫn có dấu cách); phân lệnh `setup | status [--json] | deps … | help`; lệnh lạ → mã thoát 2
- [X] T005 Trong `bin/studio` viết hàm đọc `library.lock` (cho phép `STUDIO_LIB_REPO` và `STUDIO_LIB_COMMIT` ghi đè); thiếu hoặc `LIB_COMMIT` không phải 40 ký tự hex → mã thoát 2
- [X] T006 Trong `bin/studio` viết hàm kiểm tra công cụ theo research.md §5: git ≥ 2.25, node ≥ 20, ffmpeg ≥ 7 (bản build theo ngày → `unknown`), python3 ≥ 3.11 hoặc có `uv`; trạng thái `ok · missing · old · unknown` kèm `hint`; so sánh số bằng `[ -lt ]`, không dùng `sort -V`
- [X] T007 Trong `bin/studio` viết hàm xác định trạng thái thư viện theo data-model.md: `missing · foreign · modified (trừ package-lock.json) · outdated · ok`
- [X] T008 Tạo `tests/run.sh`: dựng repo thư viện giả (có `AGENTS.md`, `core/render/`, `styles/a/STYLE.md`, `styles/_template/STYLE.md`, `styles/a/demo/x.js`), PATH giả cho `node ffmpeg python3 uv`, dự án tạm có dấu cách trong đường dẫn, các hàm `check`/`PASS n/n`

**Checkpoint**: Nền sẵn sàng cho các user story.

## Phase 3: User Story 1 - Chuẩn bị xưởng lần đầu (Priority: P1) 🎯 MVP

**Goal**: Một lệnh `setup` đưa thư viện về đúng phiên bản và báo công cụ.

**Independent Test**: `sh tests/run.sh` phần US1 xanh.

### Tests for User Story 1

- [X] T009 [US1] Trong `tests/run.sh` thêm kịch bản: tải mới → `ok` và đúng commit; `styles/a/demo/` không có (sparse); chạy lại → không fetch, thông báo đã đúng phiên bản; đổi `STUDIO_LIB_COMMIT` sang commit mới → cập nhật; thư viện bị sửa → mã 1, file giữ nguyên; thư mục lạ → mã 1, không xoá; node thiếu, ffmpeg 6 → liệt kê `missing`, `old` kèm phiên bản cần; ffmpeg bản theo ngày → `unknown`; python 3.9 + uv → `ok`; lock sai → mã 2; `git status` của dự án không thấy file trong `films/` và `references/` sau khi tạo file thử

### Implementation for User Story 1

- [X] T010 [US1] Trong `bin/studio` viết `setup`: tải vào `lib/.lemo-opuscar.tmp` (git init, remote, sparse checkout qua `.git/info/sparse-checkout` với mẫu ở research.md §3, tải từng phần, `fetch --depth 1 origin <SHA>`, fallback fetch đầy đủ, `checkout --detach`), đặt `studio.managed=true` (KHÔNG đặt `lemo.managed`), đổi tên thành `lib/lemo-opuscar`; dọn thư mục tạm cũ
- [X] T011 [US1] Trong `bin/studio` `setup`: với `outdated` thì fetch và checkout SHA mới; với `foreign`/`modified` thì dừng, in cách khôi phục, mã 1; in bảng công cụ và kết luận; mã thoát theo contracts/studio-cli.md

**Checkpoint**: US1 chạy và test độc lập được.

## Phase 4: User Story 2 - Kiểm tra trạng thái xưởng (Priority: P2)

**Goal**: `status [--json]` báo trạng thái đầy đủ, offline, không ghi file.

**Independent Test**: `sh tests/run.sh` phần US2 xanh.

- [X] T012 [US2] Trong `tests/run.sh` thêm kịch bản: sẵn sàng → mã 0 và counts `library_styles=1` (trừ `_template`), `my_styles`, `films` đúng; thư viện bị sửa → mã 1 và `"state":"modified"`; `--json` hợp lệ (kiểm bằng `python3 -m json.tool` nếu có); chạy từ thư mục con; không có thay đổi file nào sau `status`
- [X] T013 [US2] Trong `bin/studio` viết `status`: bảng dễ đọc và `--json` theo `StudioStatus` (escape `"` và `\`), gồm `deps_core`; mã 0/1/2

**Checkpoint**: US1 và US2 đều chạy độc lập.

## Phase 5: User Story 3 - Claude đi đúng luồng (Priority: P3)

**Goal**: `CLAUDE.md` dẫn mỗi loại yêu cầu tới đúng luồng.

**Independent Test**: 3 yêu cầu mẫu trong quickstart.md → 3/3 đúng luồng.

- [X] T014 [US3] Viết lại mục "Các luồng làm việc" trong `CLAUDE.md`: làm phim → `sh bin/studio status` (chưa sẵn sàng thì `setup`), đọc `lib/lemo-opuscar/AGENTS.md` và làm theo ở chế độ skill với `LIB=<gốc>/lib/lemo-opuscar`, thư mục phim `films/<tên>/`, phong cách riêng đọc và lưu ở `my-styles/` (thay cho `~/lemo-my-styles/`), cài gói bằng `sh bin/studio deps`, không tạo spec; học phong cách → báo chưa có (tính năng 002); xây xưởng → spec-kit
- [X] T015 [US3] Thêm `my-styles/README.md` dạng danh mục (bảng trống) để Claude đọc như `~/lemo-my-styles/README.md` của thư viện

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T016 [P] Cập nhật `README.md`: cách bắt đầu (`sh bin/studio setup`, `status`, `deps`), bảng trạng thái tính năng
- [X] T017 Chạy `sh tests/run.sh` (toàn bộ) và chạy thật `sh bin/studio setup` + `status` với GitHub theo quickstart.md; ghi kết quả (đạt / đạt một phần / thất bại) vào cuối file này

## Dependencies & Execution Order

- Phase 1 → Phase 2 → US1 → US2 → US3 → Polish.
- US2 dùng các hàm của Phase 2, không phụ thuộc mã `setup` của US1 (test của US2 tự dựng thư viện bằng `setup` nên chạy sau US1).
- US3 chỉ là tài liệu, làm song song được sau Phase 2.

## Parallel Opportunities

- T002, T003 song song (khác file).
- T014, T015, T016 song song (khác file).
- Các task trong `bin/studio` và `tests/run.sh` tuần tự vì cùng file.

## Implementation Strategy

MVP = Phase 1 + 2 + US1: chạy được `setup`. Sau đó thêm `status`, rồi tài liệu điều hướng.

## Kết quả kiểm chứng (T017, 2026-11-05)

| Kiểm tra | Kết quả |
|---|---|
| `sh tests/run.sh` | **Đạt**: 46/46. Thử cài 2 lỗi cố ý (đặt `lemo.managed`, đếm cả `_template`) → test bắt được cả 2 |
| SC-001: tải thật từ GitHub | **Đạt**: 1 lệnh, khoảng 2 giây; đúng `bebbbe1`; 66 phong cách; không có `demo/` |
| SC-002: chạy lại | **Đạt**: 0,14 giây, không tải |
| SC-003: `status` | **Đạt**: 0,18 giây |
| SC-004: báo công cụ | **Đạt**: máy cloud có ffmpeg 6.1 → báo "quá cũ, cần ≥ 7" kèm gợi ý |
| SC-005: gitignore | **Đạt** (trong test) |
| SC-006: thư viện không bị sửa | **Đạt**: 0 thay đổi sau `setup` và `status` |
| SC-007: điều hướng | **Đạt**: 3 yêu cầu mẫu trong quickstart.md đối chiếu với `CLAUDE.md` → 3/3 |
| `deps` với thư viện thật | **Chưa chạy**: chỉ kiểm bằng test (biến môi trường được chuyển đúng); cài thật nặng khoảng 350 MB, để chạy trên máy người dùng |
