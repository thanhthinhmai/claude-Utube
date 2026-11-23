# Feature Specification: CLAUDE.md gọn

**Feature Branch**: `031-slim-claude-md`

**Created**: 2026-11-23

**Status**: Draft

**Input**: User description: "CLAUDE.md của dự án quá dài (~36 KB, nạp ở mọi lượt). Chuyển luồng làm phim thành skill, chi tiết app desktop (014–018) và công cụ sang CLAUDE.md của thư mục con, rút phần Cấu trúc; giữ nguyên mọi luật."

## Bối cảnh

- `CLAUDE.md` gốc có 179 dòng nhưng 35.730 byte (khoảng 11–14 nghìn token) vì mỗi dòng rất dài. Nó được nạp ở mọi lượt của mọi phiên, kể cả khi chỉ sửa app desktop hay license.
- "Luồng làm phim" chiếm hơn một nửa tệp nhưng chỉ cần khi người dùng nhờ làm phim. Phần app desktop, bộ cài, license, Client (014–018) và mô tả từng thư mục công cụ chỉ cần khi sửa các thư mục đó.
- Claude Code tự nạp skill khi yêu cầu khớp mô tả của skill, và tự nạp `CLAUDE.md` của thư mục con khi làm việc với tệp trong thư mục đó. Agent của việc online và app đọc `tools/runner/JOB.md`, không đọc `CLAUDE.md` hay tự nạp skill của dự án, nên không bị ảnh hưởng.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Phiên thường nạp ít hơn, phim vẫn làm đúng (Priority: P1)

Người dùng mở phiên để sửa xưởng (desktop, proxy, test…). Claude chỉ nạp phần chung của `CLAUDE.md`. Khi người dùng nhờ làm phim, Claude nạp skill làm phim và đi đúng các bước như trước.

**Why this priority**: Đây là toàn bộ giá trị: giảm phần nạp ở mọi lượt mà không mất luật nào.

**Independent Test**: Đo kích thước `CLAUDE.md` gốc; chạy script đối chiếu kiểm mọi dòng luật của bản cũ có mặt trong đúng một tệp mới; kiểm skill làm phim có mô tả nhận "làm phim/video/clip".

**Acceptance Scenarios**:

1. **Given** bản `CLAUDE.md` mới, **When** đo, **Then** tệp ≤ 9.000 byte.
2. **Given** bản cũ và các tệp mới, **When** chạy script đối chiếu, **Then** 100% dòng nội dung của bản cũ (trừ tiêu đề mục và dòng được thay bằng lời trỏ) có trong `CLAUDE.md` gốc, skill làm phim, hoặc một `CLAUDE.md` của thư mục con.
3. **Given** người dùng nói "làm một phim về …", **When** Claude chọn luồng, **Then** bảng luồng trong `CLAUDE.md` trỏ tới skill làm phim, và skill được liệt kê với mô tả khớp.
4. **Given** người dùng sửa tệp trong `desktop/`, **When** Claude làm việc ở đó, **Then** chi tiết 015–018 có trong `desktop/CLAUDE.md`.

### Edge Cases

- Tệp khác trỏ tới "luồng làm phim của CLAUDE.md" (vd. skill `style-learn`): phải đổi sang trỏ tới skill mới.
- Luật chung đang nằm trong luồng làm phim nhưng dùng cho mọi việc (không sửa `lib/`, ghi việc lên giao diện): luật "không sửa `lib/`" phải còn trong `CLAUDE.md` gốc.
- Agent online/app không được nạp skill làm phim thay cho `JOB.md`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Toàn bộ "Luồng làm phim" (bước 1–5, 2a, 2b, 3, 3a, 3b, 3c) PHẢI chuyển nguyên văn sang skill `.claude/skills/film-make/SKILL.md`, có mô tả để Claude nạp khi người dùng muốn làm phim, video, clip, gói đăng cho phim, hoặc sửa theo ghi chú phim.
- **FR-002**: Bảng "Các luồng làm việc" trong `CLAUDE.md` PHẢI trỏ luồng Làm phim tới skill đó.
- **FR-003**: Chi tiết 015–018 (app desktop, bộ cài, license, Client) PHẢI chuyển nguyên văn sang `desktop/CLAUDE.md`; `CLAUDE.md` gốc giữ tối đa 2 dòng tóm tắt cho mỗi spec và lời trỏ.
- **FR-004**: Mô tả chi tiết từng thư mục công cụ trong "Cấu trúc" (`tools/studio/`, chế độ online, `tools/filmcheck/`, `tools/render/`, `tools/style-learn/`) PHẢI chuyển nguyên văn sang `tools/CLAUDE.md`; `CLAUDE.md` gốc giữ bản đồ thư mục một dòng mỗi mục.
- **FR-005**: Danh sách lệnh dài của `bin/studio` trong "Cấu trúc" PHẢI chuyển sang skill làm phim (lệnh làm phim) và `tools/CLAUDE.md` (lệnh test); `CLAUDE.md` gốc trỏ tới `sh bin/studio --help`.
- **FR-006**: Các mục "Luật bắt buộc", "Chọn mức quy trình", "Quy trình đầy đủ" và phần chạy app trên máy (014) PHẢI giữ trong `CLAUDE.md` gốc; luật "không sửa `lib/`" PHẢI có trong `CLAUDE.md` gốc.
- **FR-007**: Mọi tham chiếu tới "luồng làm phim của `CLAUDE.md`" trong repo PHẢI đổi sang skill mới.
- **FR-008**: KHÔNG ĐƯỢC đổi `tools/runner/JOB.md`, `agent.py` hay cách agent online/app nạp hướng dẫn.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `CLAUDE.md` gốc ≤ 9.000 byte (giảm ≥ 70% so với 35.730 byte).
- **SC-002**: Script đối chiếu báo 0 dòng nội dung bị mất.
- **SC-003**: 0 tham chiếu còn lại tới luồng làm phim trong `CLAUDE.md` (tìm bằng grep).
- **SC-004**: 5 bộ test của xưởng đạt.

## Assumptions

- Claude Code nạp `CLAUDE.md` của thư mục con khi đọc hoặc sửa tệp trong thư mục đó, và nạp skill khi yêu cầu khớp mô tả (tài liệu chính thức).
- Không kiểm được trong spec này rằng một phiên mới thật sự chọn skill khi người dùng nói "làm phim"; người dùng thử ở phiên sau.
- Nội dung được chuyển nguyên văn, không viết lại luật.
