# Implementation Plan: Duyệt nhân vật cho phim After Effects

**Branch**: `034-cast-review` | **Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/034-cast-review/spec.md`

## Summary

Thêm điểm duyệt **cast** (giữa script và voice) cho phim AE. Mỗi nhân vật của phim được mô tả trong `films/<phim>/cast/cast.json` (thông số rig, phiên bản rig, các biểu cảm và tư thế kịch bản cần). Lệnh `ae sheet` dựng bảng mẫu qua đường dựng AE sẵn có: một comp xếp mỗi hình một khung cộng clip đi bộ, rồi tách thành ảnh. Người dùng duyệt và ghim ghi chú trên trang việc; ghi chú nằm trong `cast-notes.json` (cùng mẫu với `shot-notes.json` của specs/029, thêm toạ độ ghim). "Send notes to Claude" là quyết định `revise` của yêu cầu duyệt cast: Claude của việc đang chạy vẽ lại đúng các nhân vật có ghi chú. Ngoài việc làm phim (trang Cast library), app tạo một việc `fix` với `target: "cast"`. Nhân vật đã duyệt được lưu vào kho của kênh trong kho dữ liệu của app. Rig nhân vật vào bộ dựng chung theo thư mục phiên bản bất biến (`tools/ae/kit/rigs/ball/v1/`), có tệp khoá băm để test chặn sửa bản cũ.

## Technical Context

**Language/Version**: Python 3.11+ (filmcheck, studio, runner, ae), ExtendScript ES3 (bộ dựng AE), JavaScript trình duyệt (web/app.js, không framework)

**Primary Dependencies**: FastAPI/uvicorn (app, sẵn có), ffmpeg (tách khung bảng mẫu, sẵn có), Adobe After Effects của người dùng (dựng qua `tools/ae/local.py` hoặc cầu nối app)

**Storage**: tệp JSON và ảnh trong thư mục phim (`cast/`, `cast-notes.json`); kho nhân vật trong kho của chủ xưởng `$STUDIO_DATA/accounts/<owner>/channels/<kênh>/cast/`; điểm duyệt trong `checks.json → reviews` như specs/026

**Testing**: unittest (`sh tests/filmcheck/run.sh`, `sh tests/ae/run.sh`, `sh tests/ui/run.sh`, `sh tests/online/run.sh`, `sh tests/run.sh`), test trình duyệt `tests/ui/browser_*.cjs`, và một lượt dựng AE thật theo `quickstart.md`

**Target Platform**: WSL2/Linux và macOS (phần lõi), AE trên Windows/macOS của người dùng

**Project Type**: công cụ CLI + app web cục bộ + worker (mở rộng xưởng hiện có)

**Performance Goals**: bảng mẫu 3 nhân vật ≤ 5 phút (SC-001); trang Cast mở ≤ 1 s với ≤ 10 nhân vật × ≤ 16 hình

**Constraints**: không sửa `lib/`; không gọi `aerender`, AE tự render qua hàng đợi của nó (hiến pháp VII, memory); mỗi lần dựng một lượt AE; ảnh bảng mẫu ≤ 300 KB mỗi hình (JPEG 720 px) để kho nhẹ

**Scale/Scope**: ≤ 10 nhân vật mỗi phim, ≤ 50 nhân vật mỗi kênh, một chủ xưởng

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá |
|---|---|
| I. Spec là nguồn sự thật | Đạt. Spec đã duyệt và làm rõ 4 câu; spec không nêu công nghệ ngoài tên bộ máy AE (đúng nguyên tắc VII). |
| II. Không đoán | Đạt. Không còn `NEEDS CLARIFICATION`; các mặc định ghi ở Assumptions của spec và ở research.md. |
| III. MVP theo story | Đạt. P1 = US1 + US2 (duyệt và ghi chú trong phim), tự chạy được không cần kho hay phiên bản rig; US3, US4 làm sau. |
| IV. Đo được | Đạt. Cổng voice, ghim, lô ghi chú, kho, bất biến rig có test tự động; bảng mẫu và "chỉ dựng lại nhân vật có ghi chú" kiểm bằng so điểm ảnh; một lượt AE thật trong quickstart. |
| V. Đơn giản | Có một độ phức tạp: rig theo phiên bản cùng tồn tại trong một lần dựng. Ghi ở Complexity Tracking. |
| VI. Thư viện gốc | Đạt. Không chạm `lib/`. |
| VII. Hai bộ máy | Đạt. Chỉ phim `engine: "ae"`; phim web không đổi. Dựng bằng hàng đợi render của AE như specs/032. |
| VIII. Học phong cách | Không áp dụng. |
| IX. Spec-kit cho phần mềm | Đạt. Đây là công cụ của xưởng; nhân vật của từng phim đi theo luồng làm phim. |
| Bản quyền | Đạt. Nhân vật do xưởng tự vẽ; không chép nhân vật của kênh mẫu. |

**Re-check sau Phase 1**: vẫn đạt; không thêm bộ máy hay dịch vụ mới; mọi thứ đi qua lệnh `bin/studio`, API app và đường dựng AE sẵn có.

## Project Structure

### Documentation (this feature)

```text
specs/034-cast-review/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── files.md        # cast.json, sheet.json, cast-notes.json, kho nhân vật, rigs.lock
│   ├── cli.md          # lệnh cast …, rig …
│   ├── api.md          # API app: trang việc, phim, kho nhân vật
│   └── rig.md          # giao diện rig ExtendScript theo phiên bản, comp bảng mẫu
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
tools/ae/
├── kit/rigs/ball/v1/ball.jsx     # rig chuyển từ films/ae-sleepless-test/ae/ballchar.jsx, đăng ký CU.RIGS["ball@1"]
├── kit/castsheet.jsx             # comp bảng mẫu: mỗi hình một khung + clip đi bộ
├── rigs.lock                     # băm sha256 của từng thư mục rig/vN (bất biến)
├── rigs.py                       # đọc rigs.lock, liệt kê phiên bản, kiểm bất biến
├── sheet.py                      # ae sheet: gói bundle, dựng, tách khung → cast/sheets/<id>/
├── bundle.py                     # (sửa) thêm các rig/vN mà phim cần
└── cli.py                        # (sửa) thêm `ae sheet`
tools/filmcheck/
├── cast.py                       # cast.json: kiểm, trạng thái từng nhân vật, dấu, duyệt, cổng
├── castnotes.py                  # cast-notes.json: ghi chú có ghim, lô, trả lời
├── castlib.py                    # kho nhân vật của kênh trong kho app
├── points.py                     # (sửa) POINTS thêm "cast", fingerprint, reached, gate
├── steps.py                      # (sửa) bước Cast, đồ thị Script→Cast→Picture
├── edit.py                       # (sửa) thao tác point "cast"
├── channels.py                   # (sửa) REVIEW_POINTS
└── cli.py                        # (sửa) lệnh cast …, cổng cast trong voice make
tools/studio/studio/
├── reviews.py, server.py, api_online.py, mcp_server.py, donesofar.py, filmsteps.py   # (sửa) kind/point "cast", khối cast trong view
├── castapi.py                    # route trang việc + kho nhân vật
├── jobs.py                       # (sửa) fix target "cast"
└── web/app.js, web/style.css     # (sửa) khung Cast, trang Cast library
tools/runner/
├── agent.py                      # (sửa) AE_PICTURE thêm bước Cast; fix_prompt nhánh cast
└── worker.py                     # (sửa) finish_fix chép cast/ về, nhập kho khi duyệt
.claude/skills/film-make/SKILL.md # (sửa) bước Cast của phim AE
tests/filmcheck/test_cast.py, test_castnotes.py, test_castlib.py
tests/ae/test_rigs.py, test_sheet.py
tests/ui/test_cast_api.py, browser_cast.cjs
tests/online/test_cast_fix_job.py
```

**Structure Decision**: mở rộng các thư mục sẵn có của xưởng; mỗi phần mới một mô-đun nhỏ cạnh mô-đun cùng loại (`castnotes.py` cạnh `shotnotes.py`, `castlib.py` theo mẫu `people.py`, `sheet.py` cạnh `splice.py`).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Nhiều phiên bản rig cùng nạp trong một lần dựng AE (`CU.RIGS["ball@N"]`) | FR-020, SC-006: nhân vật đã duyệt phải dựng bằng đúng phiên bản lúc duyệt, kể cả khi phim có nhân vật khác dùng bản mới | Một rig duy nhất: sửa rig sẽ âm thầm đổi mọi nhân vật đã duyệt. Chép rig vào từng phim: kho không biết nhân vật dùng bản nào, không báo được "New rig version". |
