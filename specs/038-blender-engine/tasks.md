---
description: "Tasks for 038 Blender engine, per-shot engine, depth"
---

# Tasks: Blender là bộ máy thứ ba, chọn bộ máy theo từng shot, cảnh có chiều sâu

**Input**: `specs/038-blender-engine/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md)

**Tests**: Bắt buộc theo hiến pháp IV. Test viết trước code của từng story, chạy với Blender giả và AE giả. Lượt thật trên GPU chạy theo quickstart.

**Luật chung cho mọi task**:
- Không sửa `lib/`.
- Không có đường dẫn máy trong repo.
- Mọi lượt Claude dùng `models.current()`.
- Chỉ dựng trên GPU: phần mềm thì dừng (exit 3).
- Commit chỉ các tệp có tên, không `git add` thư mục, không commit `.specify/feature.json`.

## Phase 1: Setup

- [X] T001 Sửa nguyên tắc VII trong `.specify/memory/constitution.md` thành "Ba bộ máy dựng hình" theo research R1, cụ thể:
  - trang web
  - AE render bằng render queue của chính AE, thay chữ `aerender`
  - Blender do người dùng tự cài
  - phim `engine:"ae"` được có shot Blender, phim trang web chỉ một bộ máy
  - mọi hình bằng code, không AI tạo ảnh

  Version 4.0.0, Last Amended 2026-11-26, thêm dòng lịch sử sửa đổi. Cập nhật mục VII trong `CLAUDE.md` gốc.
- [X] T002 [P] Tạo khung `tools/blender/__init__.py`, `tools/blender/kit/__init__.py`, `tools/blender/kit/sets/__init__.py`, `tests/blender/run.sh` (unittest discover `tests/blender`, theo mẫu `tests/ae/run.sh`) và `tests/blender/__init__.py`.
- [X] T003 [P] Viết Blender giả `desktop/test/fake-blender.mjs`:
  - nhận `-b --factory-startup -P <entry.py> -- <request.json>`
  - đọc `request.json`, ghi `log.txt` theo `contracts/bridge-api.md`: START, GPU, frame, shot ok, DONE
  - kind `render`: ra khung PNG bằng `ffmpeg -f lavfi testsrc` vào `<run>/S<n>/f####.png`
  - kind `plan`: ghi `layers.json` mẫu
  - kind `plate`: ghi PNG
  - `FAKE_BLENDER_MODE` = `gpu_software` | `hang` | `err` | `slow`
- [X] T004 [P] Thêm dòng Blender (GPL, người dùng tự cài, không đóng gói) vào `CREDITS`.

## Phase 2: Foundational (chặn mọi story)

- [X] T005 Viết test `tests/ae/test_film_plan.py` cho `film.py` mở rộng. Test các luật:
  - đọc `shot_plan`, `default_engine` mặc định `"ae"`
  - `engine_of(id)`, `blender_shots()`
  - trường sai, mã shot không có trong `shots`, hoặc shot Blender thiếu `blender/<id>.py` thì thoát mã 2
  - giá trị hợp lệ đúng như bảng trong data-model.md: `size` ecu/cu/med/wide/huge/insert; `cam_height` low/eye/high/top; `lens` wide/normal/long; `depth` shallow/mid/deep; `layers` ⊆ fg/mid/bg/far; `move` static/push/pull/pan/dolly/orbit/track/crane; `transition` cut/fade/dip; `set` bắt buộc với shot Blender
- [X] T006 Mở rộng `tools/ae/film.py` cho đạt T005 (`shot_plan`, `engine_of`, `blender_shots`, `validate_plan`). Phim không có `shot_plan` phải giữ đúng hành vi cũ.
- [X] T007 Viết `tools/blender/config.py`:
  - đọc và ghi `~/.config/claude-utube/blender.json` (hoặc `$STUDIO_BLENDER_CONFIG`), các khoá `blender`, `work`, `shotTimeoutSec` (mặc định 3600), `secPerFrame` (mặc định 5.5)
  - `win_path()` qua `wslpath -w`
  - `find_default()` tìm theo thứ tự: Windows `C:\Program Files\Blender Foundation\Blender */blender.exe`, rồi macOS `/Applications/Blender.app/Contents/MacOS/Blender`
  - `STUDIO_BLENDER_FAKE=1` thì dùng `node desktop/test/fake-blender.mjs`
- [X] T008 Tổng quát hoá `tools/ae/aequeue.py` thành `tools/ae/enginequeue.py` với tham số `engine` ∈ {ae, blender}, thư mục `$STUDIO_DATA/<engine>/requests/`.
  - `aequeue.py` giữ nguyên API công khai, chỉ gọi sang module mới với `engine="ae"`.
  - Tên kết quả: AE nhận thêm `L<shot>-<char>-<view>`, Blender nhận `S<n>`.
  - `tests/ui` và `tests/ae` hiện có phải vẫn đạt.
- [X] T009 [P] Viết test `tests/ae/test_enginequeue.py` cho hai engine. Kiểm: khoá một lượt, nhịp tim 60 s → `bridge_lost`, hello 30 s, giới hạn 500 MB, tên kết quả hợp lệ hoặc bị từ chối.
- [X] T010 Viết lõi bộ dựng `tools/blender/kit/core.py`, viết lại từ phần cảnh, render và GPU của bản thử, không chép đường dẫn:
  - `setup_scene(fps,size,frames)`, EEVEE
  - `gpu_guard()`: `gpu.platform.renderer_get()` khớp `llvmpipe|softpipe|swrast|SwiftShader|Microsoft Basic Render|Software` thì ghi `ERR gpu_software` và `sys.exit(3)` trước khung đầu
  - `log(line)` ghi `log.txt`
  - `render_frames(out_dir)` với `use_overwrite=False` và `use_placeholder=True` để dựng tiếp
- [X] T011 Viết `tools/blender/kit/entry.py`: đọc `request.json`, theo `kind` (render/plan/plate/probe) nạp script shot `blender/S<n>.py`, tạo đối tượng `k` của bộ dựng, gọi `shot(k)`, ghi log theo contract.
- [X] T012 Viết `tools/blender/local.py`:
  - chép kit, script shot và `layers` vào `<work>/<run>/`
  - chạy Blender, theo dõi `log.txt` theo cách của `tools/ae/local.py` (240 s chờ START, `shotTimeoutSec` mỗi shot)
  - ffmpeg đóng khung PNG thành `S<n>.mp4` (libx264, crf 18, yuv420p)
  - ghi `secPerFrame` đo được vào config
  - lỗi raise `BlenderError(code)`; mã 3 cho `gpu_software` và `no_blender`
- [X] T013 [P] Viết `tools/blender/remote.py`: trong việc (`STUDIO_JOB` + `STUDIO_PROXY`) thì POST `$STUDIO_PROXY/internal/blender/requests` và poll, giống `tools/ae/remote.py`.
- [X] T014 Viết test `tests/blender/test_local.py` với Blender giả. Kiểm:
  - dựng ra mp4 đúng số khung
  - ngắt giữa chừng thì lượt sau dựng tiếp từ khung có sẵn (FR-008)
  - `gpu_software` thoát mã 3 và không có khung nào (SC-008)
  - `hang` thì hết hạn
  - `err` thì báo mã

**Checkpoint**: Dựng được một shot Blender giả thành mp4 trên máy.

## Phase 3: User Story 1 - Một phim, mỗi shot chọn AE hoặc Blender (P1) 🎯 MVP

**Goal**: Một lệnh dựng phim trộn, mỗi shot đúng khung. Sửa một shot Blender thì chỉ shot đó được dựng lại.

**Independent test**: Quickstart mục 3–4 với shot Blender chưa có nhân vật (bối cảnh, máy).

- [ ] T015 [P] [US1] Viết test `tests/ae/test_assemble.py` cho `splice.assemble()`:
  - ghép đoạn AE từ master và tệp shot Blender theo thứ tự phim
  - đúng số khung theo `timing.json`, lệch ±1
  - chuyển cảnh `fade`/`dip` ở chỗ nối giữa hai bộ máy
  - `shots.json` có `source:"mixed"` và `engines` với `version`
- [ ] T016 [US1] Thêm `assemble(segments, timing, transitions, out)` vào `tools/ae/splice.py`: một filter ffmpeg trim/concat (thêm xfade cho fade/dip), dùng lại `pieces_from_master`.
- [ ] T017 [P] [US1] Viết test `tests/ae/test_mixed_build.py`:
  - `ae build` phim trộn với AE giả và Blender giả: thứ tự các lượt, bỏ qua shot `done` mà `version` không đổi
  - `ae fix S3` (shot Blender) chỉ dựng lại S3, các khung khác giữ md5
  - `test_old_film_identical`: phim không có `shot_plan` cho `bundle.tar` cùng sha với bản 032 (SC-009)
- [ ] T018 [US1] Viết `tools/blender/bundle.py`:
  - gói kit, script shot, layers, `timing.json` và `request.json`
  - tính `version` của mỗi shot: sha của script shot, các tệp kit mà shot dùng (qua `uses.py`), layers và sha của rig
- [ ] T019 [US1] Sửa `tools/ae/cli.py` cho `build`/`draft`/`fix`:
  - tách shot theo `film.engine_of`
  - shot AE đi đường cũ; shot Blender đi qua `tools/blender/local|remote`
  - ghép bằng `assemble`, ghi `build-shots.json` (`engines`)
  - `fix` dùng lại `plan()`/`splice()` cho shot Blender
  - in `estimate: …` trước khi dựng (FR-009, qua `tools/blender/estimate.py`)
- [ ] T020 [P] [US1] Viết `tools/blender/estimate.py`: số khung × `secPerFrame` (tính riêng `--quarter`), kèm ước tính phần AE từ `shotTimeoutSec` và lịch sử. Có test trong `tests/blender/test_estimate.py`.
- [ ] T021 [US1] Mở rộng `ae status` trong `tools/ae/cli.py`: thêm cột bộ máy, và shot có `version` khác mốc thì ghi "Must run again".
- [ ] T022 [US1] (làm trước T018) Viết `tools/blender/uses.py` (regex `k.<hàm>(` và `k.set("<tên>")` trên `blender/S*.py`, cộng đồ thị gọi trong kit), nối vào `ae uses` (FR-006). Có test `tests/blender/test_uses.py`.
- [ ] T023 [P] [US1] Viết `tools/blender/kit/toon.py`, viết lại từ bản thử: vật liệu hai tông (ColorRamp constant), viền inverted hull (Solidify flip + vật liệu đen backface), `mat(color)`, `outline(obj, w)`.
- [ ] T024 [P] [US1] Viết `tools/blender/kit/mesh.py`: hộp, trụ, bo cạnh, mặt phẳng, `join`, gán vật liệu theo mặt.
- [ ] T025 [P] [US1] Viết `tools/blender/kit/camera.py`:
  - `cam(size,height,lens,move,frm,to,look)`: lens wide/normal/long = 18/35/85 mm; độ cao low/eye/high/top
  - move theo key với ease
  - DOF tuỳ chọn
- [ ] T026 [US1] Viết các bối cảnh `tools/blender/kit/sets/classroom.py`, `hallway.py`, `auditorium.py` (viết lại từ bản thử, mỗi bối cảnh có đủ lớp fg/mid/bg/far và tham số `light`), cùng `tools/blender/kit/fx.py` (confetti). Đối tượng `k` trong `entry.py` có các hàm `k.set`, `k.cam`, `k.fg`, `k.fx` theo `contracts/blender-kit.md`.
- [ ] T027 [US1] Viết `tools/blender/cli.py` và nối vào `bin/studio`:
  - `blender build <phim> S3 [--still F] [--quarter]`
  - `blender config [--exe] [--work] [--timeout]`
- [ ] T028 [US1] Kiểm thật (quickstart mục 3–4) trên phim thử `films/film30` (AE + ít nhất 3 shot Blender chưa có nhân vật):
  - chạy trên GPU
  - đo khung bằng ffprobe
  - xem bản tổng
  - ghi kết quả vào `quickstart.md` mục Kết quả

**Checkpoint**: Phim trộn dựng và sửa được (SC-001, SC-002, SC-009).

## Phase 4: User Story 2 - Cảnh có chiều sâu và không gian như video mẫu (P1)

**Goal**: Đo chiều sâu của video mẫu, đặt máy theo số đo, chặn shot gần hoặc nông trước khi render.

**Independent test**: Quickstart mục 5.

- [ ] T029 [P] [US2] Viết test `tests/filmcheck/test_vanish.py`: ảnh hành lang vẽ bằng code, có điểm tụ đã biết, cho `horizon` đúng ±0,03. Ảnh ít đường thẳng thì ra `None`.
- [ ] T030 [P] [US2] Viết `tools/filmcheck/vanish.py`: Canny + HoughLinesP, gom giao điểm, `measure(img)` theo `contracts/style-depth.md`.
- [ ] T031 [US2] Mở rộng labeler `tools/filmcheck/labeler.py`:
  - schema v3 (`cam_height`, `lens`, `depth`, `layers`, `occluder`)
  - tăng `LABELER_VERSION`
  - hints từ `vanish.measure`
  - nhãn lệch điểm tụ thì đánh `check`

  Cập nhật test labeler hiện có trong `tests/filmcheck/` (Claude giả).
- [ ] T032 [P] [US2] Vẽ thêm vào `tools/style-learn/sl/guide.py` ba dải ví dụ bằng code (độ cao máy, ống kính, lớp cảnh và vật che), rồi tạo lại `labeler-guide.png`.
- [ ] T033 [US2] Ghi khối `depth` trong `tools/style-learn/sl/save.py` theo data-model.md: theo cỡ cảnh có `n`, tỉ lệ `cam_height`, `lens`, `depth`, `layers_p25`, `layers_p50`, `occluder_share`, `evidence`. Có test trong `tests/learn/`.
- [ ] T034 [P] [US2] Viết test `tests/filmcheck/test_depthcheck.py`:
  - luật `depth_close`, `depth_shallow`, `card_angle` theo bảng trong contract
  - `size_share` lệch hơn 10 điểm phần trăm chỉ cảnh báo
  - `n < 5` chỉ cảnh báo (FR-015)
  - được miễn thì không chặn
  - `gate()` chặn `ae render`
- [ ] T035 [US2] Viết `tools/filmcheck/depthcheck.py` và lệnh `qc depth`:
  - lấy khung giữa từ `animatic/shots/S#.mp4`, không có thì dùng khung ¼ qua `blender build --still --quarter` hoặc `ae draft`
  - chạy labeler, so với `depth` của phong cách
  - ghi `checks.json` → `tiers.depth` kèm vân tay
  - phong cách thiếu `depth` thì thoát mã 2
- [ ] T036 [US2] Sửa `tools/filmcheck/tiers.py`: thêm `depth_close`, `depth_shallow`, `card_angle` vào `EXCEPTABLE`. `qc except` từ chối (mã 2) khi biến `STUDIO_JOB` có mặt (FR-014). Có test.
- [ ] T037 [US2] Gọi `depthcheck.gate()` trong `ae render` (`tools/ae/cli.py`) cạnh `points.gate(…,"animatic")`. Còn lỗi thì thoát mã 1 và liệt kê từng shot.
- [ ] T038 [US2] Đo lại phong cách của phim thử bằng `learn` (labeler v3) để có khối `depth`, rồi lập `shot_plan` theo số đo.
  - Kiểm SC-005: 40 shot, người dùng kiểm nhãn.
  - Lượt Claude có trả phí: hỏi người dùng trước.
- [ ] T039 [US2] Kiểm thật quickstart mục 5:
  - `qc depth` trên phim thử
  - sửa shot theo số đo
  - so tỉ lệ cỡ cảnh (SC-003)
  - người dùng chấm và đánh dấu 10 shot cho SC-004
  - ghi kết quả

**Checkpoint**: Shot gần hoặc nông bị chặn và sửa được theo số đo.

## Phase 5: User Story 3 - Nhân vật trông như nhau ở AE và Blender (P2)

**Goal**: Rig AE của Cast xuất lớp trong suốt, Blender dán lên mặt phẳng quay về máy.

**Independent test**: Quickstart mục 6, và shot Blender có nhân vật đi bộ, vẫy tay.

- [ ] T040 [US3] Thử thật (spike) với AE: output module "PNG Sequence" và "RGB + Alpha" qua `setSettings`; nếu không được thì dùng template "Lossless with Alpha". Ghi kết quả vào research.md mục R6 trước các task sau.
- [ ] T041 [P] [US3] Viết test `tests/blender/test_layers.py`:
  - đổi góc nhìn ra view của rig, có trễ 15° để không nhấp nháy
  - `dir` ±1
  - `height_px` × 1,2, tối đa 1080
  - `track` chỉ ghi khi trạng thái đổi
  - đám đông dùng một bộ nhỏ lớp
- [ ] T042 [US3] Viết lượt tính:
  - `tools/blender/kit/cards.py` phần plan: `k.cast` và `k.crowd` ghi vị trí và hướng, tính yaw của máy so với nhân vật cho từng khung, tính `card_angle_max`
  - `tools/blender/layers.py` ra `layers.json` theo data-model.md
- [ ] T043 [US3] Viết `tools/ae/kit/castlayer.jsx`: `CU.layers(json)` dựng mỗi (char, view) một comp chỉ có rig (`CU.rig`), nền trong suốt, động tác theo `track`, rồi đưa vào render queue PNG alpha. Ghi log `layer S3 hero 34 ok`.
- [ ] T044 [US3] Thêm `kind="layers"` vào `tools/ae/bundle.py` (`entry.jsx` đặt `CU.MODE="layers"`), và nhận kết quả `L…` trong `tools/ae/local.py`/`remote.py`. Có test trong `tests/ae/` với AE giả (thêm chế độ layers vào `fake-ae.mjs`).
- [ ] T045 [US3] Viết phần dựng của `tools/blender/kit/cards.py`:
  - mỗi view một mặt phẳng gắn Image Sequence (alpha blend, bóng alpha clip), chỉ hiện view đang dùng theo khung
  - Locked Track Z về máy, gốc ở chân
  - đám đông lệch thời gian và lật trái/phải
- [ ] T046 [US3] Nối lượt tính và lượt lớp vào `ae build/fix` (T019): shot Blender có nhân vật chạy lượt tính, rồi lượt lớp AE, rồi lượt dựng. Rig hoặc động tác đổi thì `version` đổi. Thiếu AE thì dừng và báo (edge case).
- [ ] T047 [US3] Viết bảng mẫu Cast cho phim trộn:
  - bối cảnh `tools/blender/kit/sets/caststage.py`
  - `tools/ae/sheet.py` đặt hình Blender cạnh hình AE
  - đo ΔE2000 màu áo và màu đầu trên vùng mặt nạ, đo tỉ lệ độ dày viền bằng distance transform (SC-006)
  - có test
- [ ] T048 [P] [US3] Viết ảnh nền cho shot AE:
  - `tools/blender/kit/plate.py` và lệnh `blender plate <phim> S5 --from S4` ra `ae/data/plates/S5.png`
  - `CU.plate(id)` trong `tools/ae/kit/lib.jsx` (FR-020)
- [ ] T049 [US3] Kiểm thật: shot Blender có hero đi và vẫy tay, đám đông vỗ tay, rồi bảng mẫu Cast hai bộ máy (quickstart mục 6). Gửi người dùng xem, không gửi khung của video mẫu.

## Phase 6: User Story 4 - Xưởng gợi ý bộ máy cho từng shot (P2)

- [ ] T050 [P] [US4] Viết test `tests/ae/test_suggest.py` cho các luật trong research R11:
  - wide/huge, máy đi, ≥ 6 người, hoặc bối cảnh Blender → blender
  - ecu/cu/insert hoặc thẻ chữ → ae
  - med → ae, trừ khi máy đi
  - kèm một câu lý do
- [ ] T051 [US4] Viết `tools/ae/suggest.py` và `tools/ae/plan.py`, lệnh `ae plan <phim> [--suggest] [--set …] [--json]` theo `contracts/cli.md`. Không ghi đè `engine` mà người dùng đã đặt (FR-022).
- [ ] T052 [US4] Ghi số trùng giữa bộ máy gợi ý và lựa chọn cuối của người dùng trên phim thử (SC-007) vào quickstart mục Kết quả.

## Phase 7: User Story 5 - Cài đặt Blender và dựng bắt buộc trên GPU (P3)

- [ ] T053 [P] [US5] Viết `tools/blender/probe.py` (kind `probe`, khoảng 3 s, cache 10 phút tại `~/.cache/claude-utube/blender-probe.json`) và lệnh `blender status`. Thêm hai dòng `after effects:` và `blender:` vào `cmd_status` trong `bin/studio` (FR-024).
- [ ] T054 [US5] Thêm đường gọi `/api/v1/blender/bridge/{next,hello,<id>/bundle,<id>/progress,<id>/result/<tên>,<id>/finish}` vào `tools/studio/studio/server.py` (khoá `x-cu-bridge`, dùng `enginequeue` engine blender) và `/internal/blender/requests` vào `tools/runner/proxy.py`. Có test trong `tests/ui/`.
- [ ] T055 [US5] Viết `desktop/blenderbridge.js` theo khuôn `aebridge.js`:
  - poll 5 s, hello và nhịp tim 10 s, một lượt mỗi lúc
  - `findBlender()`, `CU_FAKE_BLENDER`
  - in `blender bridge ok` và `blender build ok`
- [ ] T056 [US5] Sửa `desktop/main.js`: cấu hình `.blender.{exe,work}`, IPC `blender:choose`, khởi chạy cầu nối Blender cạnh cầu nối AE, mục khay "Blender: …". Thêm trang `desktop/blender.html` (như `ae.html`).
- [ ] T057 [P] [US5] Viết `desktop/test/blenderbridge.test.js` (`node --test`, Blender giả: ok, hang, err, gpu_software).
- [ ] T058 [US5] Thêm vào `.github/workflows/desktop.yml` bước smoke cầu nối Blender trên Windows và macOS, chờ đủ hai dòng "blender bridge ok" và "blender build ok" (FR-028). Bộ cài có bước chọn đường dẫn Blender (chọn sau cũng được).
- [ ] T059 [US5] Sửa form tạo phim của app (`tools/studio` UI) cho phim AE có shot Blender. Khi cầu nối chưa sẵn sàng cho bộ máy cần dùng thì báo rõ (FR-029). Có test trong `tests/ui/`.
- [ ] T060 [US5] Viết `tests/blender/live.sh`: Blender thật, dựng một shot 1 s ở ¼ cỡ, kiểm dòng GPU không phải software. Chạy một lần và ghi kết quả.

## Phase 8: Polish

- [ ] T061 [P] Cập nhật tài liệu:
  - `.claude/skills/film-make/SKILL.md`: mục phim trộn, `ae plan`, script shot Blender, `qc depth`, miễn chỉ do người dùng
  - `tools/runner/JOB.md`: agent không được `qc except` chiều sâu
  - `tools/CLAUDE.md`, `desktop/CLAUDE.md`, `CLAUDE.md`
- [ ] T062 Chạy `sh tests/run.sh`, `sh tests/ae/run.sh`, `sh tests/blender/run.sh`, `sh tests/filmcheck/run.sh`, `sh tests/ui/run.sh`, `sh tests/learn/run.sh`, `sh tests/render/run.sh`, `sh tests/online/run.sh`, `sh tests/license/run.sh` và test node của desktop. Ghi kết quả.
- [ ] T063 Đối chiếu SC-001 đến SC-009 với kết quả trong quickstart. Mục nào chưa chạy được thì ghi rõ.

## Phase 9: Vá sau analyze

- [ ] T064 [US1] Tính shot Blender trong dấu vân tay Animatic (`tools/filmcheck/points.py` → `animatic_fingerprint` gồm `version` của shot Blender), và kiểm `notes`/`film replace` đọc được `shots.json` có `source:"mixed"` (FR-005). Có test trong `tests/filmcheck/` và `tests/ae/`.
- [ ] T065 [US3] Chặn dựng shot Blender có nhân vật khi nhân vật chưa duyệt ở Cast, dùng cùng cổng `points.gate(code,"cast")` với AE (FR-018). Có test trong `tests/ae/test_mixed_build.py`.
- [ ] T066 [US1] Ghi phiên bản Blender vào `engines.<id>.blender` của mốc shot. `ae status` và `qc depth` cảnh báo `blender_versions` khi các shot của một phim dựng bằng hai phiên bản khác nhau (edge case). Có test.
- [ ] T067 [US5] Thêm bước chọn đường dẫn Blender vào bộ cài và lần mở đầu của app (`desktop/` installer/first-run theo specs/016): tự tìm ở chỗ cài mặc định, kiểm bằng `blender --version`, lưu vào `.blender.exe` (FR-028).

## Dependencies

- T001 trước mọi code.
- Phase 2 chặn mọi story.
- US1 (Phase 3) là MVP. US2 độc lập với US1, trừ T035 cần `blender build --still` (T027) cho shot Blender.
- US3 cần US1 (T019) và T040.
- US4 chỉ cần T006.
- US5 cần T008 và T012.
- Polish chạy sau cùng.

## Parallel examples

- Phase 2: T009, T013 song song sau T008/T012.
- US1: T015, T017, T020, T022, T023, T024, T025 song song, rồi T016 → T019.
- US2: T029/T030, T032, T034 song song, rồi T031 → T033 → T035 → T036 → T037.
- US5: T053, T057 song song với T054.

## Implementation strategy

1. T001 → Phase 2 → US1, kiểm thật phim trộn với bối cảnh, chưa có nhân vật.
2. US2: chiều sâu và chặn theo shot. Đây là chỗ sửa lời phàn nàn "cảnh gần, nông".
3. US3: nhân vật lớp AE trong Blender.
4. US4 và US5, rồi Polish, chạy đủ test, mở PR (không merge).
5. Sau đó spec 039: máy chạy trong shot, cách nối shot, trang Camera.
