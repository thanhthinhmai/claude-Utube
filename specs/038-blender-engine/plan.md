# Implementation Plan: Blender là bộ máy thứ ba, chọn bộ máy theo từng shot, cảnh có chiều sâu

**Branch**: `038-blender-engine` | **Date**: 2026-11-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/038-blender-engine/spec.md`

## Summary

Phim AE (`engine: "ae"`) được có shot dựng bằng Blender. `film.json` thêm khối `shot_plan` (bộ máy, số đo máy, bối cảnh theo từng shot). `ae build|fix|render` tách shot theo bộ máy:
- Shot AE dựng như specs/032.
- Shot Blender dựng thành `S<n>.mp4` bằng bộ dựng chung `tools/blender/kit/` (Python `bpy`, EEVEE trên GPU, toon, viền, bối cảnh).
- `splice.assemble()` ghép theo khung.

Nhân vật trong shot Blender là lớp 2D trong suốt do chính rig AE của Cast xuất (`kit/castlayer.jsx`, chuỗi PNG có alpha), dán lên mặt phẳng quay về máy.

Chiều sâu:
- Labeler (Opus, specs/021) đo thêm độ cao máy, ống kính, độ sâu, số lớp, vật che. Điểm tụ OpenCV làm bằng chứng.
- Phong cách lưu khối `depth`.
- `qc depth` chặn từng shot gần hoặc nông hơn mẫu trước `ae render`. Chỉ người dùng được miễn.

Gợi ý bộ máy bằng luật (`ae plan --suggest`). App desktop thêm cầu nối Blender theo khuôn cầu nối AE. Hiến pháp lên 4.0.0.

## Technical Context

**Language/Version**:
- Python 3.10+ (`tools/ae`, `tools/blender`, `tools/filmcheck`, phần lõi)
- Python 3.11 của Blender 5.2 (bộ dựng `tools/blender/kit/`, chỉ `bpy`, `bmesh`, `mathutils`, `gpu`)
- ExtendScript ES3 (`tools/ae/kit/castlayer.jsx`)
- JavaScript `@ts-check` trên Node 20 / Electron (`desktop/blenderbridge.js`)
- sh

**Primary Dependencies**:
- Có sẵn: ffmpeg/ffprobe, OpenCV headless và numpy trong `tools/.venv`, Claude CLI (labeler).
- Blender 4.2+ (thử trên 5.2.5) do người dùng tự cài. AE của người dùng như specs/032.
- Không thêm gói Python hay npm.

**Storage**:
- **Phim**: `films/<tên>/film.json` (`shot_plan`), `films/<tên>/blender/S<n>.py`, `films/<tên>/ae/data/plates/`, `out/blender/S<n>.mp4`, `out/layers/`, `shots.json` (`engines`)
- **Cấu hình Blender**: `~/.config/claude-utube/blender.json`; trong app là `config.json` của app (`.blender.{exe,work}`)
- **Hàng đợi app**: `$STUDIO_DATA/blender/requests/<mã>/`
- **Phong cách**: `my-styles/<slug>/shots.json` → `depth`
- **Kết quả kiểm**: `checks.json` → `tiers.depth`, miễn ở `qc-exceptions.json`

**Testing**:
- `tests/blender/run.sh` mới (unittest, Blender giả `desktop/test/fake-blender.mjs`)
- Mở rộng `tests/ae/run.sh`, `tests/filmcheck/run.sh`, `tests/ui/run.sh` (đường gọi cầu nối Blender)
- `node --test desktop/test/blenderbridge.test.js`, smoke trong `desktop.yml`
- `tests/blender/live.sh` chạy với Blender thật trên GPU (ngoài 5 suite)
- Xem thử thật theo quickstart

**Target Platform**:
- Windows 11 + WSL2: lõi trong WSL, Blender và AE trên Windows. Đây là máy chính của người dùng.
- macOS: lõi chạy thẳng.
- Online VPS không có Blender: báo rõ (FR-027).

**Project Type**: CLI của xưởng, cùng app desktop và web service có sẵn.

**Performance Goals**:
- 1080p EEVEE trên iGPU khoảng 5,5 s/khung (đo ở bản thử), nên shot 3 s ở 24 fps mất khoảng 7 phút. In ước tính trước khi dựng (FR-009).
- `ae fix` một shot Blender ≤ thời gian dựng shot + 2 phút (SC-002).
- Lượt tính (layers) ≤ 10 s mỗi shot.
- `qc depth` ≤ 2 phút cho phim 60 shot (labeler gom 12 shot mỗi lượt như 021).

**Constraints**:
- GPU bắt buộc (FR-025).
- Mỗi lúc một lượt AE và một lượt Blender.
- Ảnh video mẫu không rời máy. Labeler chỉ gửi khung của **phim của xưởng** và khung video mẫu đang được gửi như ở specs/021 (luật cũ không đổi).
- Không sửa `lib/`.
- Mọi lượt Claude dùng `models.current()` (Opus 5.5).

**Scale/Scope**: Một máy, phim 30 s – 7 phút, 10–90 shot, trong đó khoảng 20–40% là shot Blender.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá |
|---|---|
| I. Spec là nguồn sự thật | Đạt. Spec có nêu tên After Effects và Blender, nhưng chúng là đối tượng của tính năng và của nguyên tắc VII, giống tiền lệ specs/032. Định dạng tệp, ngôn ngữ và thư viện chỉ có trong plan. |
| II. Không đoán | Đạt. Ba câu clarify (chặn theo shot, cầu nối trong 038, một bản code nhân vật) đã được người dùng trả lời ngày 2026-11-26. Không còn `NEEDS CLARIFICATION`. Đầu ra alpha của AE được thử ở task đầu, có phương án dự phòng (R6). |
| III. MVP theo story | Đạt. US1 (phim trộn) và US2 (chiều sâu) là P1 và chạy độc lập. US1 chạy được với shot Blender chưa có nhân vật (bối cảnh, máy). US3–US5 xếp sau. |
| IV. Đo được | Đạt. SC-001 đến SC-009 đều có số. Có test với Blender và AE giả. Lượt thật trên GPU và xem thử theo quickstart. |
| V. Đơn giản | Có vượt mức: bộ máy thứ ba, hàng đợi tổng quát, cầu nối thứ hai. Xem Complexity Tracking. |
| VI. Thư viện gốc | Đạt. Không đụng `lib/`. |
| VII. Bộ máy | **Phải sửa hiến pháp**: luật "mỗi phim một bộ máy" và "hai bộ máy" mâu thuẫn với yêu cầu. Người dùng đã duyệt trộn theo shot (2026-11-26), nên task đầu tiên là sửa VII lên 4.0.0 (R1) trước mọi code. Blender do người dùng tự cài, thiếu thì báo rõ, không âm thầm chuyển sang AE (FR-027). |
| VIII. Đo phong cách | Đạt. Khối `depth` có số đo và khung bằng chứng. Nhãn của labeler được đối chiếu với điểm tụ đo bằng công cụ. |
| IX. Spec-kit cho xưởng | Đạt. Đây là công cụ của xưởng. Phim thử chỉ dùng để kiểm chứng. |
| Bản quyền | Đạt. Không AI tạo ảnh. Blender là GPL, xưởng không đóng gói Blender, chỉ thêm dòng vào `CREDITS` vì phim có dùng Blender để dựng. Bối cảnh và nhân vật đều vẽ bằng code, không chép video mẫu. |

**Sau Phase 1**: Vẫn đạt với điều kiện sửa VII lên 4.0.0 (task T001). Thiết kế không thêm phụ thuộc mới. Phim AE cũ không có `shot_plan` thì đi đúng đường cũ (SC-009, test so byte của bundle).

## Project Structure

### Documentation (this feature)

```text
specs/038-blender-engine/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md             # ae plan, ae build/fix/render cho phim trộn, blender status|config|build|plate, qc depth
│   ├── film-json.md       # khối shot_plan, shots.json engines, layers.json
│   ├── blender-kit.md     # API bộ dựng cho script shot (k.set, k.cam, k.cast, …)
│   ├── bridge-api.md      # cầu nối Blender, loại bundle layers của AE
│   └── style-depth.md     # labeler schema v3, khối depth của phong cách, luật qc depth
└── tasks.md
```

### Source Code (repository root)

```text
.specify/memory/constitution.md        # VII → 4.0.0
tools/ae/
├── film.py            # + shot_plan, engine_of(id), blender_shots()
├── plan.py            # mới: ae plan (đọc/ghi shot_plan)
├── suggest.py         # mới: luật gợi ý bộ máy
├── cli.py             # + plan; build/fix/render tách theo bộ máy; render gọi depth gate
├── splice.py          # + assemble(): ghép đoạn AE và tệp shot Blender
├── bundle.py          # + kind="layers" (castlayer)
├── enginequeue.py     # mới: hàng đợi chung theo engine; aequeue.py gọi sang
├── sheet.py           # + hình Blender cạnh hình AE, ΔE và độ dày viền
└── kit/
    ├── castlayer.jsx  # mới: comp rig trong suốt theo layers.json, render PNG alpha
    └── lib.jsx        # + CU.plate(id)
tools/blender/
├── __init__.py
├── config.py          # blender.json, tìm blender.exe, wslpath
├── local.py           # chạy Blender, đọc log.txt, ffmpeg đóng mp4, dựng tiếp
├── remote.py          # qua proxy của việc
├── bundle.py          # gói kit + script shot + layers + request.json
├── layers.py          # lượt tính: đọc kết quả lượt tính, ra layers.json
├── estimate.py        # ước tính thời gian từ secPerFrame
├── uses.py            # shot nào dùng hàm/bối cảnh nào
├── probe.py           # dò GPU cho status (cache 10 phút)
├── cli.py             # blender status|config|build|plate
└── kit/               # chạy bên trong Blender
    ├── entry.py  core.py  toon.py  mesh.py  camera.py  cards.py  fx.py  plate.py
    └── sets/classroom.py  hallway.py  auditorium.py  caststage.py
tools/filmcheck/
├── labeler.py         # schema v3 + hints điểm tụ
├── vanish.py          # mới: điểm tụ, chân trời, góc nhìn
├── depthcheck.py      # mới: qc depth, gate()
├── tiers.py           # + EXCEPTABLE depth_close, depth_shallow, card_angle; qc except từ chối trong việc
└── cli.py             # + qc depth
tools/style-learn/sl/
├── guide.py           # + dải độ cao máy, ống kính, lớp cảnh
└── save.py            # + khối depth trong shots.json
tools/runner/proxy.py            # + /internal/blender/requests
tools/studio/studio/server.py    # + /api/v1/blender/bridge/...
desktop/
├── blenderbridge.js  blender.html
├── main.js            # + cấu hình Blender, blender:choose, khởi chạy cầu nối
└── test/fake-blender.mjs  blenderbridge.test.js
.github/workflows/desktop.yml    # + smoke Blender
bin/studio             # + blender …, ae plan, qc depth, status có dòng AE và Blender
tests/blender/run.sh  live.sh  test_*.py
tests/ae/  tests/filmcheck/  tests/ui/   # mở rộng
.claude/skills/film-make/SKILL.md  tools/CLAUDE.md  desktop/CLAUDE.md  CLAUDE.md  tools/runner/JOB.md  CREDITS
```

**Structure Decision**:
- Theo khuôn có sẵn: phần thuần Python ngoài bộ máy (`tools/ae/*.py`, `tools/blender/*.py`), phần chạy bên trong bộ máy (`tools/ae/kit/`, `tools/blender/kit/`).
- Phim chỉ giữ phần riêng: `film.json`, `ae/*.jsx`, `blender/S<n>.py`.
- Lệnh vào phim vẫn là `ae …`, vì phim trộn là phim AE có shot Blender. `blender …` chỉ lo máy, cấu hình, ảnh nền và lượt dựng lẻ.

## Complexity Tracking

| Vượt mức | Vì sao cần | Phương án đơn giản hơn bị loại vì |
|---|---|---|
| Bộ máy thứ ba (Blender) trong cùng phim AE | Người dùng chọn trộn theo shot (2026-11-26). AE không có không gian 3D thật cho cảnh rộng, máy đi và đám đông, nên cảnh đang gần và nông (yêu cầu 4). | Chỉ đặt máy AE xa hơn: bản thử AE vẫn phẳng, không có bóng và lớp che. Blender cho cả phim: AE vẫn tốt hơn ở cận, biểu cảm và thoại. |
| Lớp nhân vật do AE xuất rồi dán vào Blender (mỗi shot Blender có nhân vật đi qua cả hai bộ máy) | Câu 3 clarify: một bản code nhân vật, hình giống nhau ở hai bộ máy. Nhân vật nặn 3D bằng code đã thử và không đạt. | Nhân vật 3D trong Blender: không đạt sau 3 bản. Vẽ lại rig bằng Python: hai bản code, sẽ lệch nhau. |
| Hàng đợi tổng quát `enginequeue.py` và cầu nối thứ hai | Câu 2 clarify: shot Blender phải chạy được trong việc của app. | Chép `aequeue.py` thành bản thứ hai: hai bản cùng logic khoá, nhịp tim và giới hạn, sửa lỗi phải sửa hai nơi. |
