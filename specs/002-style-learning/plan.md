# Implementation Plan: Học phong cách từ video tham chiếu

**Branch**: `002-style-learning` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/002-style-learning/spec.md`

## Summary

Hai phần:

1. **Bộ công cụ đo** `tools/style-learn/` (Python), gọi qua `sh bin/studio learn <lệnh>`:
   - `fetch`: nhận link kênh, link video hoặc file sẵn có.
   - `measure`: đo **mọi khung** của phần được đo (giải mã bằng ffmpeg ở rộng 320 px), gồm chuyển động camera (phase correlation bằng numpy FFT), cắt cảnh, độ sáng, tương phản, bão hoà, vùng rất tối và rất sáng, bảng màu Lab, độ lớn âm thanh, khoảng lặng; kèm bảng ảnh mỗi 2 giây.
   - `transcribe`: chép lời có mốc thời gian từng từ, tính tốc độ đọc.
   - `summary`: tổng hợp cả bộ.
   - `check-names`: chặn tên kênh và câu thoại nguyên văn.
   - `compare`: so khung chứng minh với khung gốc theo SC-004.
   - `save`: đóng gói vào `my-styles/`.
   - `clean`: xoá media của bộ tham chiếu.
2. **Skill Claude** `.claude/skills/style-learn/SKILL.md` điều phối toàn bộ: đo → 3 agent phân tích song song → kiểm tra chéo → `STYLE.md` tiếng Anh → **duyệt 1** → khung chứng minh vẽ bằng trang `render(t)`, chụp bằng `core/render/still.mjs` của thư viện → `compare` → **duyệt 2** → `save` → hỏi xoá video.

## Technical Context

**Language/Version**: Python 3.11+ (công cụ đo); POSIX sh (`bin/studio`); JavaScript (trang khung chứng minh, theo hợp đồng `render(t)` của thư viện)
**Primary Dependencies**: Bắt buộc: `numpy`, `Pillow`, `ffmpeg`/`ffprobe` (≥ 4.4, chỉ để đọc và đo). Tuỳ chọn: `yt-dlp` (tải), `faster-whisper` (chép lời). Khung chứng minh dùng `core/render/still.mjs` của thư viện (cần `sh bin/studio deps`)
**Storage**: Files. Bộ tham chiếu và hồ sơ đo trong `references/<set>/` (không vào git). Phong cách đã lưu trong `my-styles/<slug>/` (vào git, chỉ số liệu và nguồn)
**Testing**: `tests/learn/run.sh` chạy `unittest` của Python trên video tổng hợp tạo bằng ffmpeg (`lavfi`), biết trước số cắt cảnh, tốc độ pan, độ sáng, khoảng lặng; không cần mạng, không cần mô hình chép lời
**Target Platform**: macOS, Linux, WSL (như 001)
**Project Type**: CLI cùng skill agent
**Performance Goals**: Đo khoảng 18 phút video (~32.000 khung) dưới 60 phút (SC-005); mục tiêu thiết kế ≥ 50 khung/giây trên một nhân CPU ở rộng 320 px
**Constraints**: Không sửa `lib/`; không dùng venv của thư viện; media tham chiếu không vào git; đo lại tiếp được sau khi bị ngắt (FR-011); chạy offline khi video đã có trên máy
**Scale/Scope**: Khoảng 10 module Python (~1.200 dòng), 1 skill, 3 template báo cáo, 1 bộ test

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Kiểm tra | Kết quả |
|---|---|---|
| I. Spec là nguồn sự thật | Spec đã duyệt; 6 câu trả lời đã ghi; công nghệ chỉ ở plan | ✅ |
| II. Không đoán | 0 `[NEEDS CLARIFICATION]`; những điểm cần kiểm chứng khi code (chọn tiếng gốc của yt-dlp, ngưỡng cắt cảnh) ghi trong research.md kèm test | ✅ |
| III. MVP trước | US1 (đo) chạy và test độc lập; US2 (viết phong cách), US3 (chứng minh, lưu) xây trên đó | ✅ |
| IV. Đo được | SC-001…008 có số; SC-002 kiểm bằng video tổng hợp; tải thật và chép lời thật được ghi rõ là cần máy người dùng | ✅ |
| V. Đơn giản | Không dùng OpenCV hay scikit; numpy tự viết phase correlation và k-means. Một venv riêng là cần thiết (Complexity Tracking) | ✅ (có giải trình) |
| VI. Thư viện giữ nguyên | Chỉ gọi `still.mjs` của thư viện từ ngoài; không cài vào `lib/.venv`; trang chứng minh nằm trong `references/` (được thư viện mount ở `/@film/`) | ✅ |
| VII. Một bộ máy dựng hình | Khung chứng minh dùng bộ máy `render(t)` đã chốt ở 001 | ✅ |
| VIII. Học bằng đo | Toàn bộ tính năng thực thi nguyên tắc này; mỗi luật dẫn tới bằng chứng; có nhật ký sửa | ✅ |
| IX. Spec-kit không cho phim | Không làm phim (phim demo tách riêng) | ✅ |
| Bản quyền | Media, bản chép lời, bảng ảnh và ảnh ghép có khung gốc đều nằm trong `references/` (không vào git); `check-names` chặn tên và câu thoại; mặc định xoá media | ✅ |

**Re-check sau Phase 1**: không phát sinh vi phạm mới. `my-styles/<slug>/` chỉ chứa số liệu, văn bản tự viết và khung tự vẽ.

## Project Structure

### Documentation (this feature)

```text
specs/002-style-learning/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── learn-cli.md       # sh bin/studio learn … và deps learn
│   ├── profile-schema.md  # định dạng hồ sơ đo
│   └── skill-flow.md      # các bước, điểm dừng duyệt và agent của skill
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
bin/studio                         # thêm: learn …, deps learn
tools/
├── requirements-learn.txt         # numpy, Pillow
├── requirements-learn-extra.txt   # yt-dlp, faster-whisper
└── style-learn/
    ├── learn.py                   # CLI: fetch | measure | transcribe | summary | check-names | compare | save | clean
    └── sl/
        ├── refset.py              # bộ tham chiếu: set.json, trạng thái từng video
        ├── fetch.py               # yt-dlp (tuỳ chọn) + nhận file sẵn có
        ├── probe.py               # ffprobe, chọn phần được đo (≤ 3 phút / đoạn đại diện)
        ├── frames.py              # giải mã ffmpeg → numpy theo từng khung
        ├── motion.py              # phase correlation, cắt cảnh
        ├── color.py               # luma, tương phản, bão hoà, Lab, k-means bảng màu
        ├── audio.py               # ebur128, khoảng lặng
        ├── speech.py              # faster-whisper (tuỳ chọn), tốc độ đọc từ words.json
        ├── sheets.py              # bảng ảnh mỗi 2 giây
        ├── measure.py             # điều phối đo một video, ghi kết quả, tiếp tục sau khi ngắt
        ├── summary.py             # tổng hợp theo định dạng
        ├── names.py               # check-names
        ├── compare.py             # so khung chứng minh
        └── save.py                # đóng gói my-styles/, danh mục, clean
.claude/skills/style-learn/
├── SKILL.md                       # quy trình cho Claude
└── templates/
    ├── aspect-report.md           # báo cáo một nhóm khía cạnh
    ├── corrections.md             # nhật ký sửa
    └── review-vi.md               # bản tóm tắt duyệt bằng tiếng Việt
tests/learn/
├── run.sh
├── make_fixtures.py               # tạo video tổng hợp bằng ffmpeg
└── test_*.py
.gitignore                         # thêm tools/.venv/
CLAUDE.md                          # luồng "Học phong cách" trỏ tới skill
```

**Structure Decision**: Một dự án đơn. Công cụ nằm trong `tools/style-learn/` theo vai trò thư mục `tools/` ở 001. Skill nằm trong `.claude/skills/` để Claude Code tự nạp.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Venv riêng `tools/.venv` | TECHNIQUE.md của thư viện cấm cài gói lạ vào `$LIB/.venv`; hiến pháp VI | Dùng Python hệ thống: không kiểm soát được phiên bản, `pip install` hệ thống bị chặn trên nhiều máy (PEP 668) |
| Tự viết phase correlation và k-means bằng numpy | Tránh phụ thuộc OpenCV (~90 MB) và scikit-learn | OpenCV: nặng, wheel không có cho mọi nền tảng; độ chính xác cần thiết đạt được bằng FFT thuần |
