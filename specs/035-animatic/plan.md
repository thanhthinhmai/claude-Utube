# Implementation Plan: Điểm duyệt Animatic cho phim After Effects

**Branch**: `035-animatic` | **Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/035-animatic/spec.md`

## Summary

Phim AE thay điểm duyệt **shots** bằng điểm **animatic** (giữa Voice và Sound). Thời lượng shot thôi nằm cứng trong mã của từng phim (`CU.FR` trong `ae/shots.jsx`, lặp lại trong `mix.py`) mà có một nguồn duy nhất: `films/<phim>/timing.json` (số khung mỗi shot + lịch sử để Undo). Bộ dựng AE đọc tệp này qua `CU.shotFrames(id)`; mỗi lần dựng còn ghi thời điểm keyframe của từng lớp để biết chuyển động nào bị mất khi cắt. Lệnh `ae draft` dựng bản nháp ¼ độ phân giải, chất lượng nháp, qua đúng đường dựng AE và cầu nối sẵn có, rồi ghép giọng tạm. Lệnh `animatic fit` tính đề xuất cho từng shot (kết thúc = câu cuối + 0,45 s), `animatic accept|skip|undo` đổi `timing.json` và dời mốc câu trong `narration.json` theo shot chứa câu. Phần trăm lặng tính bằng chính `rhythm.measure` của bước kiểm phim. Ghi chú trên bản nháp dùng cùng mẫu ghim của Cast (`castnotes`, specs/034) trong `animatic/notes.json`; "Send notes to Claude" là quyết định `revise` của yêu cầu duyệt animatic trong việc đang chạy, hoặc một việc `fix` với `target: "animatic"` ngoài việc làm phim (như specs/032, 034). Bản đẹp đọc cùng `timing.json`, nên mốc cắt trùng bản nháp.

## Technical Context

**Language/Version**: Python 3.11+ (filmcheck, studio, runner, ae), ExtendScript ES3 (bộ dựng AE), JavaScript trình duyệt (web/app.js, không framework)

**Primary Dependencies**: FastAPI/uvicorn (app, sẵn có), ffmpeg/ffprobe (ghép giọng, cắt clip từng shot, khung đại diện; sẵn có), Adobe After Effects của người dùng (qua `tools/ae/local.py` hoặc cầu nối app)

**Storage**: tệp trong thư mục phim: `timing.json`, `narration.json` (sẵn có, mốc câu), `animatic/` (bản nháp, clip từng shot, khung, `keys.json`, `notes.json`, `fit.json`); điểm duyệt trong `checks.json → reviews` như specs/026

**Testing**: unittest (`sh tests/filmcheck/run.sh`, `sh tests/ae/run.sh`, `sh tests/ui/run.sh`, `sh tests/online/run.sh`, `sh tests/run.sh`), test trình duyệt `tests/ui/browser_animatic.cjs`, và một lượt AE thật trên `ae-sleepless-test` theo `quickstart.md`

**Target Platform**: WSL2/Linux và macOS (phần lõi), AE trên Windows/macOS của người dùng

**Project Type**: công cụ CLI + app web cục bộ + worker (mở rộng xưởng hiện có)

**Performance Goals**: bản nháp phim 30 s ≤ 3 phút và nhanh hơn bản đẹp ≥ 3 lần (SC-001); tính lại đề xuất và phần trăm lặng ≤ 200 ms (chạy trên mỗi lần nhận/bỏ); trang Animatic mở ≤ 1 s với ≤ 60 shot

**Constraints**: không sửa `lib/`; không gọi `aerender`, AE tự render qua hàng đợi của nó (hiến pháp VII, memory "After Effects from WSL"); mỗi lần dựng một lượt AE; dựng lại bản nháp chỉ các shot đổi (`ae draft --shots`) rồi ghép khung chính xác bằng `splice.py`

**Scale/Scope**: ≤ 60 shot mỗi phim (phim 10 phút ~ 250 shot vẫn chạy nhưng lưới chia trang), một chủ xưởng

**Phụ thuộc nhánh**: tách từ `034-cast-review@049bc60`. Phần đang dở của 034 (`castnotes.py`, ghim trên trang) phải được commit trước khi làm US3; 036 (giọng nhân vật) đụng `filmsteps.py`, `cli.py`, `app.js` nên rebase sau khi 036 merge. Thứ tự merge: 034 → 036 → 035.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá |
|---|---|
| I. Spec là nguồn sự thật | Đạt. Spec đạt bảng kiểm, không còn câu hỏi; spec không nêu công nghệ ngoài tên bộ máy AE (nguyên tắc VII). |
| II. Không đoán | Đạt. Không còn `NEEDS CLARIFICATION`; đệm 0,45 s, giới hạn 20%, độ phân giải nháp là mặc định ghi ở spec và research. |
| III. MVP theo story | Đạt. P1 = US1 (bản nháp + dải thời gian + cổng) và US2 (đề xuất từng shot); US3 (phát clip, ghim, sửa nền) làm sau và cần 034 commit. |
| IV. Đo được | Đạt. Đề xuất, Undo, dời mốc câu, phần trăm lặng, cổng render có test tự động; "chỉ dựng lại shot có ghi chú" và "bản đẹp cùng mốc cắt" kiểm bằng so điểm ảnh/khung; một lượt AE thật trong quickstart. |
| V. Đơn giản | Một độ phức tạp: chuyển thời lượng shot từ mã phim sang `timing.json` (cần sửa phim cũ). Ghi ở Complexity Tracking. |
| VI. Thư viện gốc | Đạt. Không chạm `lib/`; giọng tạm trộn bằng ffmpeg, không qua `mix.py` của thư viện. |
| VII. Hai bộ máy | Đạt. Chỉ phim `engine: "ae"`; phim web giữ điểm Shots. Dựng bằng hàng đợi render của AE như specs/032. |
| VIII. Học phong cách | Không áp dụng (đệm 0,45 s là mặc định; học từ phong cách để sau). |
| IX. Spec-kit cho phần mềm | Đạt. Công cụ của xưởng; từng phim vẫn đi luồng `film-make`. |
| Bản quyền | Đạt. Không dùng tài sản ngoài. |

**Re-check sau Phase 1**: vẫn đạt; không thêm bộ máy hay dịch vụ; mọi thứ đi qua `bin/studio`, API app và đường dựng AE sẵn có.

## Project Structure

### Documentation (this feature)

```text
specs/035-animatic/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md       # ae draft, animatic status|fit|accept|skip|undo|notes, point animatic
│   ├── api.md       # /api/films/{film}/animatic…
│   └── files.md     # timing.json, animatic/*.json, CU.shotFrames, keys
└── tasks.md         # /speckit-tasks
```

### Source Code (repository root)

```text
tools/
├── ae/
│   ├── kit/build_core.jsx     # CU.shotFrames(id) từ data/timing.json; ghi keys_<proj>.json; CU.DRAFT → ¼ độ phân giải, Draft
│   ├── kit/lib.jsx            # CU.shotFrames, CU.keyScan (đệ quy thuộc tính, ES3)
│   ├── bundle.py              # gói timing.json vào data/; cờ draft
│   ├── draft.py               # MỚI: ae draft → animatic/draft.mp4 + clip/khung từng shot + ghép giọng tạm
│   └── cli.py                 # lệnh `ae draft`; `ae build|render` đọc timing.json
├── filmcheck/
│   ├── timing.py              # MỚI: timing.json (đọc/ghi nguyên tử, lịch sử Undo), dời mốc câu narration.json
│   ├── animatic.py            # MỚI: dải thời gian, phần trăm lặng (rhythm.measure), đề xuất fit, chuyển động bị ảnh hưởng
│   ├── castnotes.py → pins.py # (034) tách phần ghim dùng chung; animatic/notes.json dùng lại
│   ├── points.py              # điểm "animatic"; AE: animatic thay shots; fingerprint; checks_pass; Approve anyway
│   ├── steps.py               # bước "Animatic" (AE) thay "Shots"; GRAPH Voice→Animatic→Mix,Render; Cast→Animatic
│   └── cli.py                 # `animatic …`, `point approve animatic --anyway`
├── studio/studio/
│   ├── filmsteps.py, actions.py, reviews.py, server.py   # API + duyệt + quyết định revise
│   └── web/app.js, style.css                             # khung Animatic theo bản mẫu
└── runner/agent.py, JOB.md    # bước Animatic trong việc làm phim AE; việc fix target animatic

.claude/skills/film-make/SKILL.md, tools/ae/CAST.md → tools/ae/ANIMATIC.md   # luồng làm phim AE
tests/filmcheck/test_timing.py, test_animatic.py · tests/ae/test_draft.py, test_keys.py · tests/ui/test_animatic_api.py, browser_animatic.cjs
```

**Structure Decision**: mở rộng các mô-đun sẵn có, thêm 3 mô-đun nhỏ (`timing.py`, `animatic.py`, `ae/draft.py`). Không thêm dịch vụ.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Thời lượng shot chuyển từ mã phim (`CU.FR`) sang `timing.json`, phim AE cũ phải chuyển | Đề xuất cắt, Undo, bản nháp, Sound và bản đẹp phải cùng một nguồn thời lượng (FR-017, SC-004); app không thể sửa mã JSX của từng phim an toàn | Sửa chuỗi `CU.FR = […]` trong `shots.jsx` bằng regex: vỡ với phim viết khác, không có lịch sử, Claude dễ ghi đè |
