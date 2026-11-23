# Implementation Plan: Ghi chú từng shot trên trang phim

**Branch**: `029-shot-notes` | **Date**: 2026-11-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/029-shot-notes/spec.md`

## Summary

Trang phim của app có thêm phần Shots: thanh thời gian và danh sách shot đọc từ tệp mốc shot `shots.json` cạnh video, ảnh nhỏ cắt từ video bằng ffmpeg (có bộ nhớ đệm), phát riêng một shot, và sổ ghi chú `shot-notes.json` (kèm ảnh dán Ctrl+V trong `shot-notes/`) ghi qua API với dấu nội dung để không mất thay đổi của người khác. Phim web có `shots.json` từ `SHOTS` của trang (sau `render` và qua lệnh `shots export` cho phim cũ); phim After Effects ghi `shots.json` khi ghép bản tổng. Claude dùng các lệnh `notes show|reply` và `film replace` (giữ một bản video trước) để khép vòng sửa. Không thêm bộ máy dựng hình, không thêm gói phụ thuộc, không sửa `lib/`.

## Technical Context

**Language/Version**: Python 3.10+ (máy chủ app `tools/studio`, công cụ `tools/filmcheck`), JavaScript thuần có `@ts-check` (giao diện `tools/studio/studio/web/app.js`), Node 20 (đọc `SHOTS` của trang qua `tools/filmcheck/plan.mjs` có sẵn), sh (`bin/studio`).

**Primary Dependencies**: FastAPI và python-multipart đã có trong app (uploads specs/009); ffmpeg/ffprobe đã là yêu cầu của xưởng; Playwright đã có (đọc trang phim). Không thêm gói mới.

**Storage**: Tệp trong thư mục phim: `shots.json`, `shot-notes.json`, `shot-notes/<ảnh>`, `shots.prev.json` + `<tên>.prev.mp4`, bộ nhớ đệm ảnh nhỏ `.shots/thumbs/<dấu video>/`. Ghi nguyên tử (tệp tạm rồi `os.replace`) như `store.py`.

**Testing**: pytest trong `tests/ui/` (API, CLI, bảo mật, ghi đồng thời), `tests/ui/test_typecheck.py` cho `app.js`, `tests/filmcheck/` cho `shots export`; chạy thử thật trên phim `ae-crayon-test` và một phim web (`pet-swap`) theo `quickstart.md`.

**Target Platform**: App chạy trên máy (specs/014, Linux/WSL2, macOS core) và chế độ online (specs/007). Giao diện chạy trong trình duyệt và trong app desktop (specs/015, cùng giao diện).

**Project Type**: Web service + giao diện web có sẵn của xưởng, cộng lệnh `bin/studio`.

**Performance Goals**: Phần Shots của phim 40 shot hiện trong ≤ 3 s khi ảnh nhỏ đã có, ≤ 15 s lần đầu (SC-002); phát riêng shot dừng trong ±0,2 s (SC-003).

**Constraints**: Chỉ đọc, ghi trong thư mục của đúng phim (SC-007); ảnh PNG/JPEG/WebP ≤ 10 MB, ≤ 4 ảnh mỗi ghi chú; ghi chú ≤ 2.000 ký tự; tối đa 300 shot.

**Scale/Scope**: Một người hoặc một nhóm nhỏ; phim 2–10 phút, 20–300 shot; vài chục ghi chú mỗi phim.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá |
|---|---|
| I. Spec là nguồn sự thật | Đạt: spec đã làm rõ 4 câu (2026-11-23); spec không nêu công nghệ ngoài tên tệp và sản phẩm người dùng dùng (After Effects). |
| II. Không đoán | Đạt: không còn `[NEEDS CLARIFICATION]`; giả định ghi trong spec. Không thêm tính năng ngoài spec (không vẽ khoanh, không gọi AE). |
| III. MVP theo story | Đạt: US1 (xem theo shot) chạy độc lập; US2 (ghi chú) dựa trên US1; US3 (vòng sửa với Claude) dựa trên US2. |
| IV. Đo được, kiểm chứng được | Đạt: test tự động cho API, ghi đồng thời (20 lần), bảo mật đường dẫn, ảnh; đo thời gian dừng khi phát shot và khớp mốc shot với video (ffprobe) trong quickstart. |
| V. Đơn giản | Đạt: tệp JSON trong thư mục phim, không bảng CSDL mới; dấu nội dung (sha256) thay cho khoá phân tán; ảnh nhỏ cắt theo yêu cầu, có đệm. |
| VI. Thư viện gốc giữ nguyên | Đạt: không sửa `lib/`; `shots.json` sinh từ trang phim và từ `record.mjs` của xưởng, không từ `mux.sh` của thư viện. |
| VII. Một bộ máy dựng hình | Đạt: ffmpeg chỉ cắt ảnh nhỏ từ video có sẵn, không dựng hình. After Effects là công cụ của người dùng trong phim tập luyện, nằm ngoài xưởng (phim không vào git). |
| VIII. Học phong cách bằng đo | Không áp dụng. |
| IX. Spec-kit cho phần mềm | Đạt: tính năng là công cụ của xưởng; phần ghi `shots.json` trong dự án AE của phim tập luyện là việc của phim, ghi trong quickstart. |

Kết quả: **qua cổng**, không có vi phạm.

## Project Structure

### Documentation (this feature)

```text
specs/029-shot-notes/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── api.md          # các đường API của trang phim (shots, notes, ảnh, bản trước)
│   ├── cli.md          # bin/studio shots export · notes show|reply · film replace
│   └── files.md        # shots.json, shot-notes.json, shot-notes/, *.prev.*
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
tools/filmcheck/
├── shotnotes.py        # MỚI: đọc/kiểm shots.json, sổ ghi chú (dấu nội dung, trạng thái tự suy, dọn ảnh),
│                       #      ảnh nhỏ (ffmpeg, đệm), film replace (giữ 1 bản trước); dùng chung cho API và CLI
└── shotsexport.py      # MỚI: shots export <phim> từ SHOTS của trang (gọi plan.mjs có sẵn)

tools/studio/studio/
├── resources.py        # thêm đường dẫn tệp an toàn cho shots/notes/ảnh/bản trước; film_summary thêm has_shots
├── server.py           # thêm các đường /films/{name}/shots…, /notes…, ảnh, video?prev=1 (cả local và online)
└── web/
    ├── app.js          # pageFilm: phần Shots (thanh thời gian, lọc, danh sách, khung shot, ghi chú, dán ảnh,
    │                   #           "Xem bản trước", ô "Fix with Claude"); trang việc: đường dẫn "Ghi chú shot"
    └── style.css       # kiểu cho phần Shots (dùng token màu có sẵn)

tools/render/record.mjs # ghi out/shots.json cạnh video sau khi ghép (từ SHOTS đã đọc sẵn)
tools/filmcheck/qc.py   # tầng 4: chép out/shots.json (hoặc chạy shots export) thành shots.json của phim
bin/studio              # lệnh shots export · notes show|reply · film replace

tests/ui/test_shot_notes.py        # MỚI: API, bảo mật, ghi đồng thời, ảnh, trạng thái tự suy, bản trước
tests/filmcheck/test_shots_export.py  # MỚI: export từ trang giả, kiểm tệp mốc shot
CLAUDE.md               # luồng làm phim: bước "Sửa theo ghi chú phim <tên>"; danh mục lệnh
```

**Structure Decision**: Logic dùng chung nằm trong `tools/filmcheck/shotnotes.py` (chỉ cần Python 3 như các công cụ filmcheck khác) để máy chủ app và lệnh `bin/studio` cùng dùng một chỗ; máy chủ chỉ thêm các đường mỏng gọi vào đó, giống cách `edit.py` (specs/026) được dùng.

## Complexity Tracking

Không có vi phạm cần giải thích.
