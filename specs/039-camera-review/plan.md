# Implementation Plan: Học máy quay và điểm duyệt Camera

**Branch**: `039-camera-review` | **Date**: 2026-11-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/039-camera-review/spec.md`

## Summary

Bốn phần, đều nằm trong các công cụ đã có:

1. **Đo máy quay theo thời gian** (`camtrack`): một cách đo dùng chung cho video mẫu và phim của xưởng. Nó theo dõi điểm góc khung nối khung (LK + RANSAC đồng dạng, như bản đo tay `deep.py`), rồi nối các phép thành đường đi của máy. Kết quả cho mỗi shot: zoom %, chiều, ease ở ¼–½–¾, trôi px ở 1080p, pan, độ thị sai (sai số còn lại của các khối đứng yên), và chuyển cảnh lấy lại từ `craft.transition`. Bố cục (khung nhân vật chính) do bộ gán nhãn craft-label bản 2 trả về.
2. **Thư viện shot mẫu**: `learn camera SET` ghi `profile/<vid>/camera.json`. `learn save` gom vào `my-styles/<style>/camera.json`, gồm từng shot, bảng tổng theo cỡ cảnh và khung bằng chứng (tối đa 150 shot có ảnh).
3. **Gợi ý và điểm duyệt Camera**:
   - `camera suggest` chấm độ giống giữa từng shot của phim và từng shot mẫu bằng luật cố định, có giải thích. Từ đó nó đưa 2–3 phương án đã kẹp vào khoảng p25–p75 và vẽ ảnh thử ¼ cỡ thật kèm khung zoom cuối.
   - Điểm duyệt mới `camera` nằm giữa Cast và Voice (points.py) và chặn `voice make`. Trang Camera trong app.js theo mẫu Animatic: ghim ghi chú (pins.py), "Send notes to Claude", xem trước zoom bằng CSS.
   - Phương án đã chọn được ghi vào `shot_plan.<S>.camera`. Bộ dựng AE (`CU.planCam`) và Blender (`camera.py`, máy đứng yên, zoom ống kính) đọc từ đó.
4. **Kiểm máy quay** (`qc camera`): đo lại clip đã dựng bằng `camtrack` rồi so với phương án đã chọn. Miễn kiểm theo từng shot, chỉ người dùng được miễn.

## Technical Context

**Language/Version**: Python 3.12 (venv của xưởng), ExtendScript (AE kit), Python của Blender (kit 038), JavaScript thuần (app, không build)
**Primary Dependencies**: numpy, Pillow, ffmpeg, opencv-python-headless (đã có trong venv học, nay ghi vào requirements-learn.txt; R1); `claude -p` Opus 5.5 cho craft-label (đã có, specs/024)
**Storage**: tệp JSON trong `references/<set>/profile/`, `my-styles/<style>/camera.json` (+ `camera/*.jpg`), `films/<f>/camera/` và `film.json`
**Testing**: unittest qua `sh tests/learn/run.sh`, `sh tests/filmcheck/run.sh`, `sh tests/ae/run.sh`, `sh tests/ui/run.sh` (+ browser `.cjs`), `sh tests/run.sh`, `sh tests/online/run.sh`
**Target Platform**: WSL2 Ubuntu 24.04 (máy phát triển), After Effects và Blender trên Windows qua cầu nối đã có
**Project Type**: CLI + app web nội bộ
**Performance Goals**: `learn camera` ≤ 2× thời lượng video mẫu (CPU); `camera suggest` gồm ảnh thử cho phim 15 shot xong trong ≤ 10 phút (SC-003)
**Constraints**:
- Đo video mẫu theo luồng, chỉ đọc đoạn cần, giới hạn bộ nhớ 3 GB (bài học charisma-30).
- Dựng trên GPU.
- Không đưa hình hay âm của video mẫu vào repo; chỉ đưa khung bằng chứng 360 px.
**Scale/Scope**: thư viện tới ~2200 shot mẫu (dusk-hypothetical-3), phim 10–60 shot, 2–3 phương án mỗi shot

## Constitution Check

| Nguyên tắc | Trạng thái |
|---|---|
| I. Spec là nguồn sự thật | Đạt: spec đã duyệt hai câu làm rõ; công nghệ chỉ nằm ở đây |
| II. Không đoán | Đạt: hết `[NEEDS CLARIFICATION]`; ngưỡng thị sai và trọng số độ giống được hiệu chỉnh bằng số đo (research R1, R4), không đặt tay rồi để đó |
| III. MVP theo story | Đạt: US1 (đo + thư viện) tự chạy và test được; US2 dùng được khi chưa có US3 |
| IV. Đo được | Đạt: SC-001 so với số đo tay `deep_ref.json`; test tổng hợp có zoom, ease, trôi, thị sai đã biết; xem thử ảnh thử và clip thật |
| V. Đơn giản | Đạt: dùng lại craft.py, craft-label, pins.py, points.py, ae draft, blender still; luật độ giống cố định, không mô hình học |
| VI. Thư viện gốc | Đạt: không chạm `lib/` |
| VII. Ba bộ máy | Đạt: ảnh thử và chuyển động máy đều do kit AE/Blender của xưởng vẽ; Blender máy đứng yên theo quyết định 2026-11-27; thiếu AE/Blender thì báo, không đổi bộ máy |
| VIII. Học bằng đo | Đạt: mỗi shot mẫu có số đo và hai khung bằng chứng; bảng tổng có n theo cỡ cảnh |
| IX. Không spec cho phim | Đạt: charisma-30 chỉ là phim thử |
| Bản quyền | Đạt: video mẫu ở `references/` (ngoài git); khung bằng chứng 360 px, tối đa 150 shot mỗi phong cách |

Kiểm lại sau thiết kế: vẫn đạt. Không có mục nào cần Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/039-camera-review/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md            # learn camera, camera suggest|stills|choose|retime|show, qc camera, edit ops
│   ├── camera-files.md   # profile camera.json, my-styles camera.json, films camera/options.json, shot_plan.camera
│   └── ui.md             # điểm duyệt Camera, panel, API, ops
└── tasks.md              # /speckit-tasks
```

### Source Code (repository root)

```text
tools/style-learn/sl/camtrack.py     # MỚI: đường đi máy, tổng zoom, ease ¼½¾, trôi, thị sai (dùng chung, FR-005)
tools/style-learn/sl/camlib.py       # MỚI: learn camera → profile/<vid>/camera.json; bảng tổng; chọn shot có khung
tools/style-learn/sl/save.py         # SỬA: learn save ghi my-styles/<style>/camera.json + camera/*.jpg
tools/style-learn/learn.py           # SỬA: lệnh `learn camera`
tools/filmcheck/craftlabel.py        # SỬA: bản 2 thêm `subject` [x0,y0,x1,y1] % (bố cục)
tools/filmcheck/camsuggest.py        # MỚI: độ giống, phương án, kẹp p25–p75, retime
tools/filmcheck/camstills.py         # MỚI: ảnh thử ¼ (AE draft khung 1 / blender --still --quarter) + khung zoom
tools/filmcheck/camcheck.py          # MỚI: qc camera (tier "camera")
tools/filmcheck/camnotes.py          # MỚI: sổ ghi chú Camera trên pins.py + summary cho việc sửa
tools/filmcheck/points.py, steps.py  # SỬA: điểm "camera" giữa cast và voice; gate trong voice make
tools/filmcheck/cli.py, edit.py      # SỬA: lệnh `camera …`, `qc camera`; ops camera_choose / camera_note_*
tools/ae/film.py                     # SỬA: shot_plan thêm card/action/outdoor/prop và khối camera
tools/ae/kit/lib.jsx, bundle.py      # SỬA: CU.planCam đọc data/camera.json (zoom có ease + trôi)
tools/ae/draft.py                    # SỬA: chế độ still (khung 1, ¼) không cần giọng
tools/blender/kit/camera.py          # SỬA: đọc khối camera (zoom ống kính, shift, ease) — máy đứng yên
tools/studio/studio/{reviews.py,filmsteps.py,actions.py,server.py}, web/app.js, web/style.css  # SỬA: trang Camera
.claude/skills/film-make/SKILL.md    # SỬA: bước Camera và luật "máy quay theo bằng chứng"
tests/learn/test_camtrack.py, test_camlib.py
tests/filmcheck/test_camsuggest.py, test_camera_point.py, test_camnotes.py, test_camcheck.py
tests/ae/test_camera_kit.py
tests/ui/test_camera_api.py, browser_camera.cjs
```

**Structure Decision**: không thêm thư mục hay gói mới. Phần đo nằm cạnh `craft.py`, vì cả learn và filmcheck đều import `sl` như hiện nay. Phần gợi ý, ảnh thử, kiểm và ghi chú nằm trong `tools/filmcheck` như depthcheck và soundnotes của 037/038.

## Complexity Tracking

Không có.
