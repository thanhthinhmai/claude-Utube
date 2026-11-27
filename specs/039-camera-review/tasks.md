# Tasks: Học máy quay và điểm duyệt Camera (039)

**Input**: `specs/039-camera-review/` (spec, plan, research R1–R13, data-model, contracts/, quickstart)
**Tests**: bắt buộc theo hiến pháp IV (logic quan trọng có test tự động + kiểm bằng số liệu và xem thử thật).

## Phase 1: Setup

- [X] T001 Liên kết bộ thử vào worktree (ngoài git): `references/charisma-ref` → `~/claude-Utube-037/references/charisma-ref`, `films/charisma-30` → `~/claude-Utube-038/films/charisma-30`; kiểm `.gitignore` đã bỏ qua cả hai; ghi lệnh vào quickstart.md nếu khác
- [X] T002 [P] Bộ tạo video tổng hợp cho test máy quay trong `tests/learn/camsynth.py`: nền có hoạ tiết, zoom % / ease ¼½¾ / trôi px cho trước, tuỳ chọn hai lớp chạy khác tốc độ (thị sai) và một vật cử động; ghi mp4 bằng ffmpeg

## Phase 2: Foundational (chặn mọi story)

- [X] T003 Đo đường đi máy trong `tools/style-learn/sl/camtrack.py` (R1): cộng dồn `craft.pairs()` → S(t) và vị trí; tinh chỉnh khung đầu↔cuối ở 640×360 (bỏ 0,15 s mỗi đầu, `block_shifts(search=2)` + `fit_camera`, ≤ 3 vòng); trả `{zoom_pct, rate_pct_s, move, ease:[q¼,q½,q¾] | null, drift_px:[x,y] ở 1080p, parallax_px, parallax, reliable, why_unreliable}`; `move` ∈ static/push/pull/pan/other; `reliable=false` khi dur < 1 s, chớp sáng, hoặc < 6 khối trong mô hình; hàm `measure(path, t0, t1)` dùng chung cho video mẫu và phim (FR-005)
- [X] T004 Test `tests/learn/test_camtrack.py`: video tổng hợp zoom 3/6/9 %, ease 0,13/0,48/0,85, trôi 0/8/12 px → lệch ≤ 0,3 điểm phần trăm, ≤ 2 px, ease ≤ 0,05; zoom ra cho dấu âm; đứng yên → `static`, ease null; hai lớp → `parallax: true`; một vật cử động không làm sai zoom > 0,3
- [X] T005 Hiệu chỉnh `PARALLAX_PX` (R1): đo 15 shot charisma-ref (nhóm 0) và các shot orbit/dolly của `/mnt/e/claude-utube-ae/blendertest` (nhóm 1; không còn thì dùng video hai lớp tổng hợp), đặt ngưỡng giữa hai nhóm, ghi số đo vào docstring của `camtrack.py`
- [X] T006 [P] Trường mới của shot_plan trong `tools/ae/film.py`: `card`, `action`, `outdoor`, `prop` (bool) và khối `camera` (`size, start{scale,cx,cy}, move, zoom_pct, rate_pct_s, ease, ease_ae, drift_px, transition, ref, option`); kiểm "`0.5 ≤ start.scale ≤ 4`; `|zoom_pct| ≤ 40`; ease mỗi phần tử trong [0,1] và tăng dần", `move ∈ {static, push, pull, pan}` cho khối camera trừ khi có `by_user_request: true` (chuyển động người dùng yêu cầu ngoài video mẫu); test trong `tests/ae/test_film_plan.py`

**Checkpoint**: cách đo chung đã chạy đúng trên video tổng hợp.

## Phase 3: User Story 1 - Học máy quay của từng shot mẫu (P1) 🎯 MVP

**Goal**: thư viện shot mẫu và bảng tổng máy quay theo cỡ cảnh, có khung bằng chứng.
**Independent Test**: `learn camera charisma-ref` → 15 mục; zoom lệch số đo tay ≤ 1 điểm phần trăm ở ≥ 13/15; cắt 14/14; 15/15 có hai khung (SC-001).

- [X] T007 [US1] craft-label bản 2 trong `tools/filmcheck/craftlabel.py` (R2): thêm `subject: [x0,y0,x1,y1]` % (null khi không có người hoặc là thẻ) vào SYSTEM, SCHEMA, parse; tăng `version()`; test `tests/filmcheck/test_craftlabel.py` (thêm ca subject hợp lệ, null, ngoài 0–100 bị loại)
- [X] T008 [US1] `tools/style-learn/sl/camlib.py`: `camera_set(name, videos, force)` đọc `profile/<vid>/shots.json`, gọi `camtrack.measure` cho từng shot, `craft.transition` cho chuyển cảnh, ghép nhãn (`scale`→size, `cam_height`, `lens`, craft-label `card/people/action/outdoor/prop/subject` → `subject_x/y/h`, `headroom`), ghi `profile/<vid>/camera.json` `{version:1, video, measured_at, measure:"camtrack/1", shots, skipped:[{id,reason}]}`; bỏ qua video đã đo khi `shots.json` không đổi và không `--force`
- [X] T009 [US1] Bảng tổng trong `tools/style-learn/sl/camlib.py`: `summary(rows)` → `by_size{n, dur, zoom_pct, drift_px, ease_q, subject_h, headroom: [p25,p50,p75], push_share, pull_share, static_share, thin: n<5}`, `transition_main`, `transition_share`, `parallax_share`; chỉ dùng shot `reliable`
- [X] T010 [US1] Lệnh `learn camera <set> [--videos] [--force]` trong `tools/style-learn/learn.py`: video thiếu → mã 2 + `run: learn refetch <set>`; nhãn thiếu → để null và in lệnh cần chạy; in mỗi video một dòng `v01: 15 shots, 0 skipped, parallax 0/15, cut 14/14`
- [X] T011 [US1] `learn save` ghi `my-styles/<style>/camera.json` (bảng tổng + `shots` không ảnh) và `camera/<vid>-<id>-{a,b}.jpg` rộng 360 px cho ≤ 150 shot chọn phân tầng (cỡ cảnh × move, ưu tiên reliable) trong `tools/style-learn/sl/save.py`; các phần khác của phong cách giữ nguyên
- [X] T012 [P] [US1] Test `tests/learn/test_camlib.py`: profile giả 2 video → camera.json đúng định dạng, skipped có lý do, bảng tổng p25/p50/p75 đúng, `thin` khi n<5, chọn ảnh ≤ 150 và phân tầng, `learn save` không đổi `shots.json`/`STYLE.md`
- [X] T013 [US1] Chạy thật trên charisma-ref: `learn shots`, `learn label`, `learn craft-label`, `learn camera`; so với `deep_ref.json` (pan ×2) theo CUTS của `deep.py`; ghi bảng so 15 shot vào `specs/039-camera-review/checks/sc001.md`; chưa đạt SC-001 thì sửa T003 rồi chạy lại

**Checkpoint**: US1 dùng được độc lập (Claude đọc thư viện khi tự lập bảng shot).

## Phase 4: User Story 2 - Gợi ý 2–3 phương án mỗi shot (P1)

**Goal**: `camera suggest` + `camera stills` + máy quay đã chọn đi vào bản dựng AE/Blender.
**Independent Test**: charisma-30 → 15/15 shot có 2–3 phương án có bằng chứng và ảnh thử; ★ trong p25–p75 ở ≥ 90 %; 0 máy đi/thị sai; ≤ 10 phút (SC-002, SC-003).

- [X] T014 [US2] Độ giống trong `tools/filmcheck/camsuggest.py` (R4): bảng trọng số card 3 (khác → loại), size 3 (kề 0,5), people nhóm 0/1/2/3+ 2, action 2, outdoor 1, prop 1, dur 1 (`max(0, 1 − |ln(d_phim/d_mẫu)|/ln 3)`); chia cho tổng trọng số các trường phim có; trả `score` và `why`
- [X] T015 [US2] Sinh phương án trong `tools/filmcheck/camsuggest.py` (R5): phương án 1 từ shot mẫu giống nhất (giữ rate, nhân thời lượng, kẹp p25–p75, ease của mẫu hoặc trung vị cỡ cảnh khi kém tin cậy, transition = `transition_main`); phương án 2 khác cỡ hoặc chiều; phương án 3 từ cỡ kề hoặc `static` khi ≥ 15 % đứng; bỏ trùng ("cùng size, cùng move, |Δzoom| < 1, |Δcx|,|Δcy| < 10"); `note` khi ngoài p25–p75 hoặc transition khác chính; `parallax_share < 0.05` ⇒ `move ∈ {static, push, pull, pan}`; không có mẫu giống → `ref: null` + "không có shot mẫu giống" kèm điểm cao nhất; ưu tiên shot có ảnh khi chênh < 0,1; phương án cũ từ `shot_plan.camera` giữ thành phương án `ref:"film"`; shot mẫu không `reliable` không làm `ref` của phương án ★; engine theo `shot_plan.engine`, chưa có thì wide/huge → blender
- [X] T016 [US2] Khung bắt đầu và ease AE trong `tools/filmcheck/camsuggest.py`: `start.scale/cx/cy` theo `subject_h/x/y` của mẫu so với chiều cao người ở thang 1 (marks của bản dựng hoặc mặc định của rig theo cỡ), kẹp không lộ mép; chưa có bản dựng thì chiều cao người ở thang 1 = trung vị `subject_h` của video mẫu ở cỡ đó (ghi docstring); bảng tra influence AE → tiến độ ¼½¾ của Bézier tốc độ 0, chọn `ease_ae:[in,out]` gần ease nhất
- [X] T017 [US2] Thời lượng (R6) và ghi tệp trong `tools/filmcheck/camsuggest.py`: `timing.json` nếu có, không thì `shots.json` của phim; ghi `films/<f>/camera/options.json` qua tệp tạm + đổi tên dưới khoá phim; `--shots` + `--keep-others` giữ từng byte các shot khác; giữ `choice` nếu cùng `n` còn, không thì `auto`; `retime(film)` tính lại zoom/drift theo `rate_pct_s`, trả danh sách đổi
- [X] T018 [US2] Lệnh `camera suggest|choose|retime|show` trong `tools/filmcheck/cli.py` (contracts/cli.md): nguồn `--set` > `--style` > phong cách của phim; phim trang web hoặc thiếu `camera.json` → mã 2 kèm lệnh cần chạy; `choose` ghi `choice` và chép phương án vào `shot_plan.<S>.camera` + `move`; `--by claude` chỉ khi điểm Camera tắt hoặc sửa theo ghi chú; in dòng `S3  1* med push 5.6% ease .13/.48/.85 drift 0,8  ← v03:S041 (0.86)`
- [X] T019 [P] [US2] Test `tests/filmcheck/test_camsuggest.py`: thư viện nhỏ cố định → thứ tự shot mẫu, 2–3 phương án khác nhau, ★ trong p25–p75, note khi ngoài khoảng, không máy đi khi parallax_share 0, `ref:null` khi không giống, `--keep-others` giữ byte, retime giữ rate và đổi zoom, choose ghi shot_plan, phim page → mã 2
- [X] T020 [US2] AE kit: `bundle.py` ghi `ae/data/camera.json` từ `shot_plan.*.camera`; `CU.planCam(comp, shot, dur)` trong `tools/ae/kit/lib.jsx` đặt khoá scale/position đầu–cuối cho CAM null với ease tốc độ 0 theo `ease_ae`, trôi theo `drift_px`, khung bắt đầu theo `start`; `camFromMotion` vẫn ưu tiên khi có; phim không có khối camera không đổi (FR-020)
- [X] T021 [US2] Blender: `tools/blender/kit/camera.py` đổi khối camera thành `move="zoom"` (máy đứng, tiêu cự × (1+zoom), `shift` theo drift, `ease` theo `ease_ae`); khối camera không bao giờ tạo dolly/orbit
- [X] T022 [P] [US2] Test `tests/ae/test_camera_kit.py`: bundle ghi `data/camera.json` đúng; lib.jsx có `planCam` và được gọi khi có khối camera; tham số Blender từ khối camera là zoom máy đứng; phim cũ ra bundle giống hệt trước
- [X] T023 [US2] Ảnh thử `tools/filmcheck/camstills.py` + `ae draft --still` trong `tools/ae/draft.py` (R8): AE dựng khung 1 ở ¼ cho mỗi phương án (một comp mỗi phương án, một hàng đợi), không kiểm giọng; shot chưa có jsx (ae/) thì mã 2 kèm lời nhắc viết shot trước; Blender một `blender build S# --still 1 --quarter` mỗi shot rồi cắt khung bắt đầu, phóng 480×270; vẽ khung cuối vàng 2 px bằng Pillow → `films/<f>/camera/stills/S#-o<n>.jpg`; thiếu AE/Blender hoặc không GPU → mã 3; lệnh `camera stills` trong `tools/filmcheck/cli.py`
- [X] T024 [P] [US2] Test `tests/filmcheck/test_camstills.py`: khung cuối vẽ đúng toạ độ cho zoom/drift cho trước; cắt khung Blender đúng `start`; thiếu bộ máy → mã 3 (giả cầu nối)
- [X] T025 [US2] Chạy thật trên charisma-30 với `--set charisma-ref`: `time camera suggest`, `time camera stills`; kiểm SC-002/SC-003; mở ≥ 5 ảnh thử xem khung zoom và bố cục; ghi `specs/039-camera-review/checks/sc002.md`

**Checkpoint**: phim làm được với US1+US2 (agent chọn ★ khi bỏ qua điểm duyệt).

## Phase 5: User Story 3 - Điểm duyệt Camera (P2)

**Goal**: điểm Camera giữa Cast và Voice, trang Camera trong app.
**Independent Test**: đổi phương án, ghim + gửi ghi chú, duyệt; lựa chọn ghi theo shot; ghi chú chỉ làm lại shot đó; duyệt mở `voice make` (SC-004).

- [X] T026 [US3] Điểm `camera` trong `tools/filmcheck/points.py` (R9): POINTS sau cast, AE_ON, AE_ONLY, STEP; fingerprint (danh sách shot, trường plan dùng cho độ giống, `choice.n`, rate/ease/size/start — không gồm zoom_pct/drift theo thời lượng); reached (options phủ mọi shot + có ảnh thử); checks_pass (mọi shot đã chọn, không ghi chú mở, liệt kê shot thiếu); skip khi phong cách không có `camera.json`; `tools/filmcheck/steps.py` thêm bước Camera giữa Cast và Voice
- [X] T027 [US3] Gate trong `voice make` (`tools/filmcheck/cli.py`) sau gate cast; `animatic accept` và `voice make` gọi `camsuggest.retime` khi có `camera/options.json`
- [X] T028 [P] [US3] Test `tests/filmcheck/test_camera_point.py`: thứ tự điểm, bật mặc định cho AE, skip khi không thư viện, approve từ chối khi thiếu lựa chọn, đổi choice → must run again, retime không đổi fingerprint, voice make bị chặn rồi mở
- [X] T029 [US3] `tools/filmcheck/camnotes.py` trên `pins.py` (R10): sổ `films/<f>/camera/notes.json` nhóm `shots`, ghim `{shot, option, x, y, text}`; `summary()` cho việc sửa; lệnh `camera note add|remove|list`; op `camera-choose`, `camera-note-add`, `camera-note-remove` (gạch nối như các op khác) trong `tools/filmcheck/edit.py`
- [X] T030 [P] [US3] Test `tests/filmcheck/test_camnotes.py`: thêm/xoá ghim, summary theo shot, op từ chối base cũ, sửa theo ghi chú chỉ đổi shot có ghi chú
- [ ] T031 [US3] Server: `actions.OPS["camera"]`, `reviews.py` KINDS/POINT_KINDS + `decide` lấy `camnotes.summary`, việc sửa chạy `camera suggest --shots … --keep-others` + `camera stills --shots …`, `filmsteps.camera_block()` (contracts/ui.md), route ảnh cho `camera/` và `my-styles/<style>/camera/` trong `tools/studio/studio/`; `review request --kind camera` từ chat ghi vào sổ việc của app khi app chạy (FR-017)
- [ ] T032 [US3] Trang Camera trong `tools/studio/studio/web/app.js` + `style.css`: lưới shot (★, chấm cam ghi chú), cột phương án (ảnh thử, khung a/b mẫu, số, lý do, note), "Use this", ▶ xem trước zoom (CSS transform, cubic-bezier theo `ease_ae`, trong `dur` giây), ghim ghi chú, "Send notes to Claude", Approve từ chối khi thiếu; thêm "Camera" vào POINTS, STEP_TAB, ô chọn điểm duyệt kênh/việc
- [ ] T033 [P] [US3] Test `tests/ui/test_camera_api.py` (camera_block, ops qua actions, decide revise, approve từ chối, review request kind camera vào sổ việc) và `tests/ui/browser_camera.cjs` (chọn phương án, ghim, xem trước, duyệt)
- [ ] T034 [US3] Chạy thật trong app (`app start`) với charisma-30: các bước SC-004, đo thời gian chọn 15 shot + duyệt, băm 14 shot còn lại sau sửa ghi chú; ghi `specs/039-camera-review/checks/sc004.md`

## Phase 6: User Story 4 - Kiểm máy quay sau khi dựng (P3)

**Goal**: `qc camera` so bản dựng với phương án đã chọn.
**Independent Test**: 3 shot cố ý (đúng, zoom tuyến tính, thị sai) → báo đúng 2 (SC-005).

- [ ] T035 [US4] `tools/filmcheck/camcheck.py` (R12): đo `animatic/shots/S#.mp4` hoặc clip shot của bản đẹp bằng `camtrack.measure`; luật `cam_zoom` (> 1 điểm phần trăm), `cam_dir`, `cam_ease` (q½ lệch > 0,10), `cam_parallax`, `cam_transition`; tier `camera` trong `tiers.py`; miễn theo shot qua `tiers.add_exception` (từ chối trong việc của app); lệnh `qc camera [--except S3 "<lý do>"]` trong `tools/filmcheck/cli.py`; shot có `by_user_request` thì không báo
- [ ] T036 [P] [US4] Test `tests/filmcheck/test_camcheck.py`: clip tổng hợp đúng/tuyến tính/thị sai → báo đúng 2; miễn trong job bị từ chối; miễn ngoài job được ghi theo shot
- [ ] T037 [US4] Chạy thật: `ae draft charisma-30` theo phương án đã chọn, `qc camera` → 0 lệch; dựng 3 shot cố ý sai → 2/2; so zoom trung bình mỗi shot với video mẫu (SC-006); xem thử clip thật và các điểm cắt (feedback continuity); ghi `specs/039-camera-review/checks/sc005.md`

## Phase 7: Polish

- [ ] T038 [P] Skill film-make `.claude/skills/film-make/SKILL.md`: sau Cast viết jsx của các shot (bối cảnh, chỗ đứng, thời lượng ước tính) trước Camera; bước Camera (suggest → stills → duyệt hoặc ★ ở giai đoạn thử → retime sau Voice → qc camera), luật "máy quay theo phương án có bằng chứng, không theo cảm nhận"; `tools/CLAUDE.md` thêm lệnh `camera …`, `learn camera`, `qc camera`; mục 039 ngắn trong `CLAUDE.md`
- [ ] T039 Chạy đủ bộ test: `sh tests/run.sh`, `sh tests/learn/run.sh`, `sh tests/filmcheck/run.sh`, `sh tests/ae/run.sh`, `sh tests/ui/run.sh`, `sh tests/online/run.sh`, `sh tests/render/run.sh`; ghi kết quả
- [ ] T040 Đối chiếu quickstart.md từ đầu đến cuối, cập nhật chỗ lệch

## Dependencies

- Setup (T001–T002) → Foundational (T003–T006) → US1 → US2 → US3 → US4 → Polish.
- US2 cần thư viện của US1 (T008–T011). US3 cần `options.json` và ảnh thử của US2. US4 cần khối camera trong bản dựng (T020–T021) và camtrack (T003); có thể làm song song với US3 sau khi US2 xong.
- Trong mỗi story: module → lệnh → test → chạy thật.

## Parallel

- T002 ∥ T006 (khác tệp). T012 ∥ T011. T019 ∥ T020/T021. T022 ∥ T023. T028 ∥ T029. T030 ∥ T031. T033 sau T032. T036 ∥ T035 (viết test trước). T038 ∥ T039 chuẩn bị.

## Implementation Strategy

1. MVP = Phase 1–3 (US1): thư viện máy quay đo đúng (SC-001). Dừng kiểm số so với đo tay.
2. US2: gợi ý + ảnh thử + bản dựng dùng máy đã chọn; đây là lúc phim mới hưởng lợi.
3. US3 trang Camera, US4 kiểm sau dựng.
4. Commit sau mỗi phase (tin nhắn ngắn tiếng Anh, không tên mô hình).
