# Implementation Plan: Chọn đề bằng số liệu YouTube

**Branch**: `013-topic-picker` | **Date**: 2026-11-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/013-topic-picker/spec.md`

## Summary

Thêm `tools/filmcheck/topics.py`, chỉ dùng thư viện chuẩn của Python, gồm 3 phần:
1. **Lấy số liệu** (R1): mỗi đề tốn tối đa 400 đơn vị hạn mức YouTube, gồm 2 lượt tìm kiếm (365 ngày theo lượt xem, 90 ngày theo ngày đăng) cùng các lượt đọc thông tin video, kênh và video gần đây của kênh.
2. **Chấm điểm** (R2): một hàm thuần, không mạng; cùng số liệu thô thì cho cùng điểm.
3. **Hàng đợi** của kênh (R4).

Mục "hợp kênh" và phần gợi ý đề dùng một lượt `claude -p` cho cả lô (R3), cách gọi giống biên tập của 010.

Có hai cách lấy số liệu (R5):
- **Local**: gọi thẳng YouTube với khoá nằm ngoài repo, ở `~/.config/claude-utube/youtube.key`, quyền 600.
- **Online**: container của việc không có internet, nên gọi `POST /internal/youtube` của proxy. Proxy giữ khoá của chủ xưởng, đếm hạn mức trong ngày (mặc định tối đa 9000 đơn vị) và giữ số liệu đã tra 24 giờ. Khoá không bao giờ vào container.

Online, chấm đề là một loại việc mới tên `topics` (R6):
- việc này không tốn lượt phim; mỗi người có giới hạn số đề mỗi ngày (mặc định 40);
- `agent.py` thấy loại việc `topics` thì chạy máy chấm thay cho Claude Code;
- worker chép kết quả vào kênh của người dùng.

Kết quả nằm ở `channels/<mã>/topics.json` và `TOPICS.md`. Kênh mẫu nằm ở `references.json`. Cả ba tệp đều bị git bỏ qua, vì chứa tên kênh khác (R7).

Giao diện: mục "Topics" trên trang kênh, gồm ô dán đề, nút chấm, bảng điểm, hàng đợi và nút "Make a film". Settings có ô đặt khoá YouTube (chỉ ghi, không đọc lại) cùng các giới hạn.

Chi tiết: [research.md](research.md) · [data-model.md](data-model.md) · [contracts/](contracts/) · [quickstart.md](quickstart.md).

## Technical Context

**Language/Version**: Python 3.12, chỉ dùng thư viện chuẩn (`urllib`, `json`, `statistics`) cho `topics.py`. Proxy dùng `httpx` có sẵn. JavaScript thuần có `@ts-check` cho giao diện.

**Primary Dependencies**: YouTube Data API v3 (`search.list` 100 đơn vị; `videos.list`, `channels.list`, `playlistItems.list` 1 đơn vị mỗi lần). Claude Code (`claude -p`) cho mục "hợp kênh" và phần gợi ý đề. Không thêm thư viện mới.

**Storage**:
- Tệp JSON trong thư mục kênh (012), bị git bỏ qua.
- Online:
  - khoá ở `$STUDIO_DATA/secrets/youtube.key` (quyền 600);
  - hạn mức trong ngày ở `$STUDIO_DATA/youtube/usage.json`;
  - số liệu tạm ở `$STUDIO_DATA/youtube/cache/`;
  - cài đặt `youtube_daily_units` và `topics_per_day` trong cài đặt có sẵn.
- Không thêm bảng.

**Testing**: `unittest`.
- Số liệu YouTube mẫu có kết quả tính tay (SC-001), chạy không cần mạng.
- YouTube giả nằm trong `fake_upstream` của test online.
- `fake_claude` có thêm chế độ chấm "hợp kênh".
- Có test tìm khoá mẫu trong mọi đầu ra (SC-004).

**Target Platform**: như 007–012.

**Project Type**: công cụ dòng lệnh, cộng với sửa dịch vụ online có sẵn.

**Performance Goals**: 10 đề < 2 phút và ≤ 4000 đơn vị (SC-002). Chấm lại trong 24 giờ tốn 0 đơn vị.

**Constraints**:
- Khoá không lộ ra (FR-011). Không tải video (FR-017). Không sửa `lib/`.
- Kênh mẫu và bằng chứng không vào git.

**Scale/Scope**: tối đa 20 đề mỗi lần chấm, 40 đề mỗi người mỗi ngày, 9000 đơn vị mỗi ngày cho cả xưởng.

## Constitution Check

| Nguyên tắc | Kết quả |
|---|---|
| I. Spec là nguồn sự thật | ✓ Đã làm rõ 3 câu. Bảng ngưỡng điểm ở research R2, đúng như phần Assumptions của spec để lại cho plan |
| II. Không đoán | ✓ có điều kiện. Một điều chưa thử: hạn mức và giá đơn vị thật của YouTube khi gọi bằng khoá thật. Kiểm ở bài chạy thật (quickstart mục 3). Test dùng số liệu mẫu |
| III. MVP theo story | ✓ US1 (chấm đề ở local, có số liệu mẫu) tự chạy và tự test được. US2 (hàng đợi), US3 (online) thêm sau |
| IV. Đo được | ✓ Mọi mục có bảng ngưỡng số. SC-001, SC-003, SC-004, SC-006 có test. SC-002 đo bằng đếm đơn vị trong test và ở bài chạy thật |
| V. Đơn giản | ✓ Một tệp công cụ. Proxy dùng lại cách của `web fetch` (010). Không thêm bảng. Một mục ở Complexity Tracking |
| VI. Thư viện gốc | ✓ Không đụng `lib/` |
| VII–IX | ✓ Không đổi |
| Bản quyền, nội dung | ✓ Chỉ đọc số liệu công khai, không tải video (FR-017). Tên kênh mẫu và kênh đối thủ chỉ nằm trong tệp bị git bỏ qua, không vào phim hay gói đăng. Chủ kênh tự kiểm điều khoản YouTube (spec, Assumptions) |

Kiểm lại sau thiết kế: đạt.

## Project Structure

### Documentation (this feature)

```text
specs/013-topic-picker/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/
│   ├── cli.md       # lệnh topics và config youtube-key, mã thoát
│   ├── files.md     # topics.json, TOPICS.md, references.json, số liệu thô
│   └── api.md       # API Topics, /internal/youtube của proxy, Settings
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
tools/filmcheck/
├── topics.py                    # mới: lấy số liệu, chấm điểm, kiểu đề, hàng đợi, TOPICS.md (R1–R4)
├── topics_fit.py                # mới: lời nhắc và lược đồ JSON của lượt "hợp kênh" và gợi ý đề (R3)
├── cli.py                       # sửa: topics score|queue|take|type|refs|recheck, config youtube-key
└── channels.py                  # sửa: đường dẫn topics.json, references.json
tools/runner/
├── proxy.py                     # sửa: POST /internal/youtube (khoá, hạn mức, số liệu tạm 24 giờ)
├── agent.py                     # sửa: việc loại topics chạy topics.run_job thay cho Claude Code
└── worker.py                    # sửa: việc topics không đòi job done, chép kết quả vào kênh
tools/studio/studio/
├── api_online.py                # sửa: /channels/{slug}/topics…, /channels/{slug}/references, Settings khoá YouTube
├── quotas.py                    # sửa: cài đặt youtube_daily_units, topics_per_day
└── web/app.js · style.css       # sửa: mục Topics trên trang kênh; "Make a film" từ đề; Settings
.gitignore                       # sửa: channels/*/topics.json, channels/*/TOPICS.md, channels/*/references.json
CLAUDE.md                        # sửa: luồng chọn đề ở local
tests/filmcheck/test_topics.py · tests/filmcheck/youtube_samples.py
tests/online/test_topics_api.py · helpers.py (YouTube giả) · fake_claude (chế độ topics)
```

**Structure Decision**: Máy chấm nằm trong `tools/filmcheck/`, vì nó dùng chung hồ sơ kênh của `channels.py` và cách gọi `claude -p` của `editor.py`, và giống 010–012, chỉ cần Python 3.

## Complexity Tracking

| Vi phạm | Vì sao cần | Cách đơn giản hơn bị loại vì |
|---|---|---|
| Thêm một loại việc `topics` chạy trong container, thay cho gọi thẳng từ máy chủ web | Mục "hợp kênh" cần Claude. Ở bản online, Claude chỉ được gọi qua mã của một việc và proxy (008); container giữ được luật "không có internet, khoá ở proxy" | Gọi YouTube và Claude từ tiến trình web thì phải đưa mã đăng nhập Claude ra ngoài proxy, và bỏ qua cách tính token theo việc của 008 |
