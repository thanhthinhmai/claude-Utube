# Feature Specification: Bước và nhật ký việc bằng tiếng Anh trên Film Studio

**Feature Branch**: `005-english-job-log`

**Created**: 2026-11-07

**Status**: Draft

**Input**: User description: "English job steps and log lines on Film Studio. Film Studio's fixed UI text is English (003 FR-021), but the job steps and log lines shown on the Jobs page are Vietnamese. Make them English: (1) the lines the studio writes itself; (2) the step names Claude writes, as instructed by CLAUDE.md and the style-learn skill — give a fixed English list. Out of scope: review summaries stay in the user's language (002); terminal messages stay Vietnamese; error text written with job fail stays as written. Old jobs keep their lines (no migration). Light level."

## Bối cảnh

Chữ cố định của Film Studio là tiếng Anh (003 FR-021), nhưng trang Jobs hiện trộn hai thứ tiếng: tiêu đề "Current step", "Log" bằng tiếng Anh, còn nội dung bên dưới là "Bắt đầu việc", "Nhạc", "Xong", "Duyệt lần 1: Đồng ý (qua giao diện)". Lần chạy thử 004 (phim `rap-anh-sao`) cho thấy rõ điều này. Mức quy trình: **Nhẹ** (đổi chữ, không đổi dữ liệu hay API).

Người dùng đã chốt phạm vi (2026-11-07):
- **Đổi sang tiếng Anh**: tên bước và các dòng nhật ký do xưởng tự ghi; tên bước Claude ghi theo CLAUDE.md và skill học phong cách.
- **Giữ nguyên**: tóm tắt duyệt viết bằng ngôn ngữ của người dùng (quyết định của 002); thông báo terminal của `bin/studio`, công cụ học phong cách và lệnh `ui`/`job`/`review`; nội dung lỗi Claude ghi bằng `job fail`; dòng do lệnh con in ra (`job run`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Đọc tiến độ việc bằng một thứ tiếng (Priority: P1)

Người dùng mở trang Jobs khi Claude đang làm phim hoặc học phong cách. Bước hiện tại, nhật ký và trạng thái kết thúc đều bằng tiếng Anh, khớp với phần còn lại của giao diện, nên họ đọc liền mạch mà không phải chuyển ngôn ngữ.

**Why this priority**: Đây là toàn bộ giá trị của tính năng.

**Independent Test**: Tạo một việc mới, ghi vài bước, gửi và trả lời một yêu cầu duyệt, chạy một lệnh bằng `job run`, rồi kết thúc việc: mọi dòng do xưởng ghi và mọi tên bước trong danh sách chuẩn đều bằng tiếng Anh.

**Acceptance Scenarios**:

1. **Given** một việc vừa bắt đầu, **When** mở trang việc, **Then** bước hiện tại là "Starting" và dòng nhật ký đầu là "Job started".
2. **Given** Claude làm phim theo CLAUDE.md, **When** qua từng giai đoạn, **Then** bước hiện tại lần lượt là tên tiếng Anh trong danh sách chuẩn (ví dụ "Music", "Render").
3. **Given** Claude học phong cách theo skill, **When** qua từng giai đoạn, **Then** bước hiện tại là tên tiếng Anh trong danh sách chuẩn (ví dụ "Measure videos", "Proof frame round 2").
4. **Given** một yêu cầu duyệt lần 1 được gửi rồi được đồng ý trên giao diện, **When** xem nhật ký, **Then** thấy các dòng "Review 1 requested", "Review 1: Approve (via UI)", "Resumed after review 1: Approve" và bước "Waiting for review 1" trong lúc chờ.
5. **Given** `job run` chạy xong một lệnh, **When** xem nhật ký, **Then** dòng cuối là "(command exited with code N)"; các dòng lệnh con in ra giữ nguyên.
6. **Given** việc kết thúc, **When** xem bước hiện tại, **Then** là "Done", "Failed" hoặc "Stopped"; nếu Claude ghi lỗi bằng `job fail`, nội dung lỗi giữ nguyên như Claude viết.
7. **Given** việc cũ trong `.studio/` có dòng tiếng Việt, **When** mở, **Then** vẫn hiện đúng như cũ (không chuyển đổi).

### Edge Cases

- Tóm tắt duyệt (lần 1, lần 2) vẫn bằng ngôn ngữ người dùng; ghi chú người dùng gõ khi "Request changes" giữ nguyên.
- Quyết định gửi từ khung chat ghi "(via chat)".
- Dòng nhật ký do lệnh con in ra (ví dụ thông báo tiếng Việt của `bin/studio learn`) giữ nguyên.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Mọi dòng nhật ký và tên bước do xưởng tự ghi MUST bằng tiếng Anh theo bảng dưới.

  | Lúc | Bước hiện tại | Dòng nhật ký |
  |---|---|---|
  | Bắt đầu việc | `Starting` | `Job started` |
  | Gửi yêu cầu duyệt lần n | `Waiting for review n` | `Review n requested` |
  | Có quyết định | | `Review n: <Approve \| Request changes \| Accept anyway \| Stop> (via UI \| via chat)[: <ghi chú>]` |
  | Tiếp tục sau duyệt | (bước Claude ghi tiếp) | `Resumed after review n: <quyết định>` |
  | `job run` kết thúc | | `(command exited with code N)` |
  | Kết thúc | `Done` · `Failed` · `Stopped` | (`Failed`: nội dung lỗi giữ nguyên) |

  Tên quyết định MUST trùng nhãn nút trên giao diện (Approve, Request changes, Accept anyway, Stop).
- **FR-002**: CLAUDE.md (luồng làm phim) MUST chỉ dẫn Claude ghi bước bằng danh sách chuẩn: `Treatment`, `Look`, `Storyboard`, `Voice`, `Music`, `Picture`, `Mix`, `Render`, `Self-check`.
- **FR-003**: Skill học phong cách MUST chỉ dẫn Claude ghi bước bằng danh sách chuẩn: `Fetch videos`, `Measure videos`, `Transcribe`, `Summarize`, `Report measurements`, `Analysis (3 agents)`, `Cross-check`, `Write style`, `Proof frame round <n>`, `Save style`.
- **FR-004**: Các phần ngoài phạm vi MUST giữ nguyên: tóm tắt duyệt, thông báo terminal, nội dung lỗi của `job fail`, dòng lệnh con in ra, dữ liệu việc cũ.
- **FR-005**: Tài liệu giao tiếp giữa skill và giao diện (contract của 003) MUST ghi danh sách chuẩn và các dòng ở FR-001, để Claude và người đọc dùng chung một bảng.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Với một việc chạy đủ vòng (bắt đầu → 3 bước → duyệt → `job run` → kết thúc), 100% dòng do xưởng ghi và tên bước trong danh sách chuẩn không chứa chữ tiếng Việt (kiểm bằng test tự động).
- **SC-002**: 0 tên bước tiếng Việt còn lại trong chỉ dẫn ghi bước của CLAUDE.md và skill học phong cách.
- **SC-003**: Các bộ test hiện có vẫn đạt sau khi cập nhật các chỗ kiểm chữ cũ.
- **SC-004**: Việc cũ trong `.studio/` mở được, nội dung hiện y như trước.

## Assumptions

- Chỉ một người dùng, cục bộ, như 003.
- Tên bước là chuỗi Claude truyền vào `job step`/`job run --step`; xưởng không ép danh sách (Claude có thể ghi bước khác khi cần), danh sách chuẩn chỉ là chỉ dẫn.
- Thông báo lỗi API vẫn dạng mã (`{error: {code, message}}`); giao diện đã dịch mã sang tiếng Anh ở 003, nên không đổi ở đây.
