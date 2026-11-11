# Implementation Plan: Hồ sơ kênh và tệp bài học

**Branch**: `012-channel-profile` | **Date**: 2026-11-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/012-channel-profile/spec.md`

## Summary

Hồ sơ kênh và bài học là tệp JSON trong `channels/` của gốc dữ liệu (`store.root()`). Khi chạy local, gốc này là thư mục dự án và tệp được đưa vào git (Q2). Khi chạy online, gốc là thư mục của từng người dùng. Bài học chung nằm ở:
- local: `channels/lessons.json`;
- online: `$STUDIO_DATA/shared/lessons.json`, do admin quản lý (Q3).

Mỗi lần ghi, xưởng viết lại thêm một bản Markdown để người đọc bằng mắt (R1).

Khi một phim được gắn với một kênh, lệnh `studio channel attach <phim> <kênh>` chụp lại trạng thái lúc đó vào thư mục phim (R2):
- `channel.json`: các luật đo được, cùng các bài học `active` có luật máy;
- `CHANNEL_BRIEF.md`: phần agent đọc ở đầu phim, tối đa 6000 ký tự.

Từ đó, các máy chấm chỉ đọc bản chụp trong thư mục phim:
- `script check` (010): thêm `channel_language`, `banned_word` và `lesson_rule` (R3);
- `publish` (011): thêm `channel_hashtags`, `channel_banned`, `channel_title_max` và `lesson_rule` (R3);
- `qc`: thêm `channel_voice` (FR-006a);
- biên tập độc lập: nhận thêm `CHANNEL_BRIEF.md` (R4).

Lợi ích của cách này:
- container online không cần đọc thư mục tài khoản;
- phim cũ không bị kiểm lại theo luật mới;
- phim không gắn kênh chạy y như trước (SC-006).

**Bài học:**
- Xưởng (Claude trong khung chat, hoặc agent của việc sửa phim) soạn nháp bằng `studio lesson draft`.
- Người dùng duyệt bằng `lesson approve` hoặc trên trang kênh; chỉ bài học `active` mới được đọc và kiểm (Q1, R5).
- Luật máy có 3 loại: `phrase:<cụm từ>`, `max_sentence_words:<n>`, `max_title_chars:<n>` (R3).

**Online (R6):**
- API `/api/v1/channels…` và `/api/v1/lessons/shared…` (admin);
- `POST /jobs` nhận thêm `channel`; worker `prepare()` chạy `attach` vào thư mục việc;
- việc sửa phim có cờ `lesson`: agent viết `LESSON_DRAFT.json`, worker lưu thành nháp;
- trang Channels; form giao phim có ô chọn kênh, điền sẵn các giá trị.

Chi tiết: [research.md](research.md) · [data-model.md](data-model.md) · [contracts/](contracts/) · [quickstart.md](quickstart.md).

## Technical Context

**Language/Version**: Python 3.12, chỉ dùng thư viện chuẩn, cho `tools/filmcheck/channels.py` và các lệnh. FastAPI có sẵn cho API online. JavaScript thuần có `@ts-check` cho giao diện.

**Primary Dependencies**: không thêm thư viện mới. Dùng lại `report.update` (010), `script.check` (010), `publish.check` (011), `qc.measure` (010), `store.root()` và `store.write_json` (007).

**Storage**: tệp JSON và Markdown; khuôn dạng ở contracts/files.md. Không thêm bảng SQLite. Kênh online là tệp trong thư mục tài khoản, nên tự đi theo luật xoá tài khoản của 007 (FR-026).

**Testing**: `unittest`.
- `tests/filmcheck/test_channels.py`: hồ sơ, bài học, bản chụp, mỗi luật kênh và luật bài học có một phim mẫu cố ý vi phạm (SC-002, SC-003).
- `tests/online/test_channels_api.py`: API và quyền (SC-005).
- `tests/online/browser_channels.cjs`: trang Channels và form giao phim.
- Các test của 010 và 011 giữ nguyên (SC-006).

**Target Platform**: như 007–011.

**Project Type**: công cụ dòng lệnh, cộng với sửa dịch vụ online có sẵn.

**Performance Goals**: `channel attach` < 1 giây. Các máy chấm chậm thêm < 0,5 giây.

**Constraints**:
- Không sửa `lib/` (VI). Không clone giọng.
- Bản chụp đọc ở đầu phim ≤ 6000 ký tự (FR-005), token thêm ≤ 2% (SC-004).

**Scale/Scope**: tối đa 20 kênh mỗi người, 200 bài học mỗi kênh.

## Constitution Check

| Nguyên tắc | Kết quả |
|---|---|
| I. Spec là nguồn sự thật | ✓ Đã làm rõ 4 câu. Chỗ thiết kế phát hiện thiếu (kiểm giọng đọc) đã được thêm vào spec trước (FR-006a) |
| II. Không đoán | ✓ Không còn hành vi chưa thử. Danh sách giọng chỉ kiểm theo dạng tên (R7), ghi rõ giới hạn |
| III. MVP theo story | ✓ US1 (hồ sơ + bản chụp + luật kênh) tự chạy và tự test được ở local. US2 (bài học), US3 (giao diện) thêm sau |
| IV. Đo được | ✓ Mọi luật có mã lỗi và ngưỡng (contracts/cli.md). SC-001, SC-002, SC-003, SC-005, SC-006 có test. SC-004 đo ở bài chạy thật |
| V. Đơn giản | ✓ Tệp JSON thay cho bảng mới; một bản chụp dùng cho mọi máy chấm; 3 loại luật máy. Một mục ở Complexity Tracking |
| VI. Thư viện gốc | ✓ Chỉ đọc `lines.json` của phim; không sửa `lib/` |
| VII. Một bộ máy dựng hình | ✓ Không đổi |
| VIII. Học phong cách | ✓ Không đổi. Kênh chỉ trỏ tới một phong cách có sẵn |
| IX. Spec-kit cho phần mềm | ✓ Hồ sơ kênh là dữ liệu của người dùng, không phải spec cho từng phim |
| Bản quyền, nội dung | ✓ Kênh là kênh của chính người dùng. Không lưu tên kênh tham chiếu. Giọng chỉ là giọng có sẵn của thư viện. Tệp kênh vào git là chữ, không có media |

Kiểm lại sau thiết kế: đạt.

## Project Structure

### Documentation (this feature)

```text
specs/012-channel-profile/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/
│   ├── cli.md       # lệnh channel và lesson, luật mới của các máy chấm, mã thoát
│   ├── files.md     # channel.json, lessons.json, bản chụp trong thư mục phim, LESSON_DRAFT.json
│   └── api.md       # API kênh, bài học, bài học chung; form giao phim
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
tools/filmcheck/
├── channels.py                  # mới: đọc, ghi, kiểm hồ sơ và bài học; bản chụp; brief; khớp từ cấm (R1–R5)
├── cli.py                       # sửa: channel new|show|set|list|decide|attach, lesson draft|approve|retire|list
├── script.py                    # sửa: luật channel_language, banned_word, lesson_rule
├── publish.py                   # sửa: luật channel_hashtags, channel_banned, channel_title_max, lesson_rule
├── qc.py                        # sửa: channel_voice
└── editor.py                    # sửa: đưa CHANNEL_BRIEF.md cho biên tập
bin/studio                       # sửa: chuyển channel | lesson tới cli.py
channels/README.md               # mới: danh mục kênh (như my-styles/README.md)
tools/runner/
├── JOB.md · agent.py            # sửa: đọc CHANNEL_BRIEF.md trước Treatment; giọng đọc của kênh; LESSON_DRAFT.json
└── worker.py                    # sửa: prepare() chạy attach; lưu nháp bài học sau việc sửa phim
tools/studio/studio/
├── api_online.py                # sửa: /channels…, /lessons/shared…, POST /jobs nhận channel, revise nhận lesson
└── web/app.js · style.css       # sửa: trang Channels, bài học, form giao phim
CLAUDE.md                        # sửa: luồng làm phim gắn kênh; ghi bài học; danh mục channels/
tests/filmcheck/test_channels.py · tests/online/test_channels_api.py · tests/online/browser_channels.cjs
```

**Structure Decision**:
- Mọi luật nằm trong `tools/filmcheck/channels.py`. Ba máy chấm và API online cùng import tệp này: proxy đã import `filmcheck`, và `api_online` sẽ thêm `tools/` vào `sys.path` theo cách của proxy.
- Có hai lý do để chụp lại hồ sơ vào thư mục phim: container online không thấy thư mục tài khoản, và kết quả chấm phải lặp lại được khi kiểm lại sau này.

## Complexity Tracking

| Vi phạm | Vì sao cần | Cách đơn giản hơn bị loại vì |
|---|---|---|
| Hai bản cho mỗi dữ liệu (JSON để máy đọc, Markdown để người đọc) | Máy chấm cần dữ liệu có cấu trúc; người dùng muốn đọc và sửa tay (FR-015) | Chỉ Markdown thì phải viết bộ đọc Markdown dễ vỡ. Chỉ JSON thì khó đọc khi xem lại trên git. Markdown luôn được viết lại từ JSON, nên không bao giờ lệch nhau |
