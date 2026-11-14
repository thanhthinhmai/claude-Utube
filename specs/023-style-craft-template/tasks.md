---
description: "Tasks for 023: template from the reference channel's craft"
---

# Tasks: Template từ cách làm của kênh mẫu

**Input**: các tài liệu thiết kế ở `specs/023-style-craft-template/`:
- `plan.md`, `spec.md`, `research.md` (R1–R13), `data-model.md`, `quickstart.md`;
- `contracts/cli.md`, `contracts/template-format.md`, `contracts/kit-api-v2.md`.

**Tests**: bắt buộc (hiến pháp IV).
- Phép đo: `tests/learn` trên video thử tổng hợp.
- Luật kiểm: `tests/filmcheck`.
- Bộ dựng: `node --test` trong `K/test/`, gọi từ `tests/render/run.sh`.
- Hình và tiếng xem thật: bảng so, phim. Mọi lần dựng phải trên GPU; không có thì dừng và hỏi người dùng.

**Việc tốn tiền hoặc cần người dùng** (dừng và hỏi):
- danh sách URL khi ghép không một-một (T020);
- 4 đợt duyệt (T040, T044, T047, T052);
- lượt gán nhãn tầng 2 (T054);
- chấp nhận phim (T057).

**Ký hiệu**:
- `[P]` = chạy song song được; `[USn]` = user story của spec.
- `K` = `my-styles/dusk-hypothetical/kit`; `S` = `my-styles/dusk-hypothetical`; `R` = `references/dusk-hypothetical-3`; `SL` = `tools/style-learn/sl`.

---

## Phase 1: Setup

- [ ] T001 Thêm `TEMPLATE.md`, `template.json` vào `STYLE_FILES` của `SL/save.py`, và `kit/REVIEW.md` vào phần giữ khi `--update` (đã giữ cả `kit/`). Thêm test vào `tests/learn/test_save_clean.py`.
- [ ] T002 [P] Tạo `tests/learn/synth.py`: hàm `make(path, spec)` dựng video 1280×720, 60 fps bằng numpy và ffmpeg, kèm đáp án.
  - Nội dung có nền họa tiết và các cảnh: `still`, `drift-h` 20 px/s, `drift-v` 15 px/s, `push` 3 %/s, `pull` 3 %/s; một khối "tay" lên trong 0,4 s rồi giữ, có cảnh máy đứng và cảnh máy trôi; chuyển cảnh `cut`, `streak` 0,15 s, `dip` 0,13 s, `fade` 0,3 s, `wipe` 0,3 s.
  - Đáp án trả về: `{shots: [{t0, t1, cam, inner_spans, trans_in}]}`.

---

## Phase 2: Foundational (chặn mọi story)

- [ ] T003 Viết `SL/craft.py` theo research R2:
  - `sample(path, t0, t1, fps=12, size=(320,180))`;
  - `block_shifts(a, b, block=16, search=8)`;
  - `fit_camera(shifts)` → `(dx, dy, zoom)`, bình phương tối thiểu, loại ngoại lai 2 vòng;
  - `residual(a, b, model)` → tỉ lệ khối cử động (ngưỡng 3σ nhiễu của cảnh);
  - `classify_cam(series)` → `still` (< 4 px/s ở bề ngang 1280 và < 0,5 %/s), `drift-h`, `drift-v`, `push`, `pull`, `follow`, kèm `px_s`, `zoom_pct_s`, `ease_in_s`, `ease_out_s`;
  - `inner(series)` → `active_share`, `peak`, `spans [t0, t1, độ lớn, [x, y]]` (≥ 2 mẫu liền), `rise_s` (10→90%);
  - `measure_shot(path, shot)` → một phần tử `shots[]` của `craft.json` (data-model.md).
- [ ] T004 Thêm vào `SL/craft.py` hàm `transition(path, t_cut)` theo research R3, xét ±0,3 s ở fps gốc:
  - `streak`: ≥ 2 khung có hàng độ sáng > 0,8 chiếm ≥ 15% chiều cao, kéo dài 0,08–0,25 s;
  - `dip`: độ sáng < 0,03 trong ≥ 2 khung;
  - `fade`: độ sáng đổi đơn điệu ≥ 0,15 s;
  - `wipe`: ranh giới hiệu khung chạy qua khung;
  - `flash`/`dissolve` dùng lại `SL/motion.events`;
  - còn lại `cut`.
- [ ] T005 Viết `tests/learn/test_craft.py` trên video của T002 (SC-003):
  - ≥ 90% cảnh có cử động được nhận, ≥ 90% loại máy đúng, ≥ 90% chuyển cảnh không phải `cut` đúng loại;
  - mọi thời điểm lệch ≤ 0,2 s;
  - cảnh máy trôi mà khối đứng yên thì `active_share` < ngưỡng (không lẫn máy với cử động);
  - in tỉ lệ đúng.
- [ ] T006 Viết `SL/template.py`, phần kiểm theo contracts/template-format.md:
  - `check_template(slug)`: 15 mục đúng tên và thứ tự; mỗi mục có mô tả, bảng số đo ≥ 1 dòng với cột "Khoảng" không rỗng; `Bằng chứng:` ≥ 3 từ ≥ 2 video hoặc `Ít bằng chứng: <n> khung`; mọi tệp được dẫn có trong `R/profile/`; có `Nên làm:`, `Không nên làm:`, `Trong bộ dựng:`; 9 nhịp theo thứ tự hook, explain, benefit, scale, cost, crisis, ending, sting, end-card;
  - `check_numbers`: số trong cột `Nguồn` khớp `template.json` hoặc `craft-summary.json` (lệch ≤ 0,01);
  - `check_style_tags(slug)`: mỗi dòng bảng hoặc gạch đầu dòng mang luật ở mục 1–11 của `STYLE.md` có `[bằng chứng: …]` hoặc `[xưởng]`.

  Mỗi lỗi in mục hoặc dòng và lý do.
- [ ] T007 [P] Viết `tests/learn/test_template.py`: mẫu đúng đạt; các mẫu thiếu (mất mục, < 3 bằng chứng, 1 video, thiếu nhãn luật, số lệch nguồn) mỗi cái báo đúng một lỗi.
- [ ] T008 Thêm vào `tools/style-learn/learn.py` các lệnh `template-check <slug>` và `craft-summary <set>` (phần khung trước, gom số ở T012 và T026). Thêm vào `bin/studio` (định tuyến `learn` đã có) theo contracts/cli.md: mã 0 đạt, 1 lỗi, 2 sai cách gọi, 3 thiếu dữ liệu.

**Mốc kiểm**: `sh tests/learn/run.sh` đạt, có SC-003.

---

## Phase 3: User Story 1 - Template tay nghề phần hình, rà `STYLE.md` (P1) 🎯 MVP

**Goal**: mục 1–10 của `TEMPLATE.md` có số đo và bằng chứng từ dữ liệu còn giữ; mọi luật của `STYLE.md` mang nhãn.

**Independent Test**: `learn template-check dusk-hypothetical` đạt mục 1–10 và nhãn luật (lệnh tạm cho phép thiếu mục 11–15 bằng `--partial 1-10`); mở từng bằng chứng được dẫn và đối chiếu.

- [ ] T009 [US1] Thêm `--partial <a-b>` vào `template-check` (chỉ kiểm các mục a–b, bỏ công thức nhịp), trong `SL/template.py` và `learn.py`.
- [ ] T010 [US1] Viết `cell(sheet, n)` trong `SL/template.py`: cắt ô `#Sxxx` của `shot-sheets`, theo kích thước ô của `SL/shots.draw_sheets` (đọc lại đúng tham số, không đoán).
- [ ] T011 [P] [US1] Viết các phép đo phần hình trong `SL/template.py` (research R10):
  - **Bố cục theo cỡ cảnh**: phân bố `sharpest_at` trên lưới 3×4; tỉ lệ lệch tâm (cột 0 hoặc 3, hàng 0 hoặc 2); tỉ lệ cột 1/3.
  - **Độ sâu theo cỡ cảnh**: `focused_share` p25–p75; tỉ lệ `foreground_blur`.
  - **Ánh sáng** trên ô `shot-sheets`: tỉ lệ điểm sáng ấm (độ sáng > 0,6, sắc độ 20–60°), p90 − p10 độ sáng, hướng gradient độ sáng trội.

  Bỏ cảnh `short`, `insert`. Luật hình chỉ tính 8 phim 3D (danh sách phim phẳng lấy từ `R/style/EVIDENCE.md`).
- [ ] T012 [US1] `craft-summary` ghi phần `framing` (theo cỡ cảnh) và `light` vào `R/profile/craft-summary.json`, in bảng. Thêm test trên `shots.json` nhỏ dựng tay vào `tests/learn/test_template.py`.
- [ ] T013 [US1] Chạy `learn craft-summary dusk-hypothetical-3`; ghi số vào ghi chú làm việc `R/style/craft-notes.md`.
- [ ] T014 [US1] Rà `S/STYLE.md` mục 1–11 (FR-001):
  - gắn `[bằng chứng: …]` cho từng luật, lấy từ `R/analysis/*.md`, `EVIDENCE.md`, `summary.json`, `shots.json`;
  - luật phụ đề in trên hình gắn `[xưởng]`;
  - luật không có bằng chứng mà không phải luật của xưởng thì bỏ, ghi vào `S/EVIDENCE.md` → "Nhật ký sửa" (ngày, luật, lý do).
- [ ] T015 [US1] Xem bằng mắt `shot-sheets` theo từng thành phần (mặt, thân áo, bối cảnh và đạo cụ, đám đông, thẻ số liệu, thẻ tiêu đề và thẻ cuối, cảnh không khí). Mỗi thành phần chọn ≥ 3 ô từ ≥ 2 video; với cảnh đêm hiếm, ghi `Ít bằng chứng: n khung`.
- [ ] T016 [US1] Viết `S/TEMPLATE.md` mục 1–10 theo contracts/template-format.md, bằng lời của xưởng: mô tả, bảng số đo kèm khoảng và nguồn, bằng chứng, nên làm, không nên làm, tên trong bộ dựng (tên mới của v2 ghi theo contracts/kit-api-v2.md). Viết `S/template.json` phần `framing`, `light` kèm `source`.
- [ ] T017 [US1] Chạy kiểm:
  - `learn template-check dusk-hypothetical --partial 1-10`;
  - `learn check-names dusk-hypothetical-3 S/TEMPLATE.md S/STYLE.md S/template.json`.

  Mốc kiểm: SC-001 đạt; mục 1–10 đạt phần của SC-002.

---

## Phase 4: User Story 2 - Học phần theo thời gian (P2)

**Goal**: số đo diễn xuất, máy, chuyển cảnh, âm thanh, nhịp đọc vào mục 11–15 và 9 công thức nhịp; video bị xoá.

**Independent Test**: test của T005, T023 đạt; `template-check` đạt đủ (không `--partial`); không còn tệp media trong `R/`.

- [ ] T018 [P] [US2] Viết `refetch` trong `SL/fetch.py` (research R1):
  - tải từng URL vào thư mục tạm;
  - ghép với `vNN` theo độ dài (lệch ≤ 1 s); nếu nhiều video trùng độ dài thì so 5 khung giữa cảnh với ô `shot-sheets` (ΔE trung bình ≤ 12);
  - ghép được thì chuyển vào `R/videos/vNN.mp4` và ghi `url` vào `set.json`; không ghép được thì báo và bỏ qua (mã 1);
  - in lời nhắc bản quyền như `fetch`;
  - `fetch` từ nay cũng ghi `url`.
- [ ] T019 [P] [US2] Viết `tests/learn/test_refetch.py`: ghép theo độ dài với tệp giả (video tổng hợp ngắn, `set.json` giả), không tải mạng; độ dài trùng thì dùng khung; không ghép được thì mã 1.
- [ ] T020 [US2] Tìm 10 URL:
  - liệt kê video của kênh tham chiếu bằng yt-dlp (`--flat-playlist`, có độ dài, không tải);
  - ghép với 10 độ dài của `set.json` (637, 640, 636, 614, 649, 629, 610, 376, 639, 1224 s);
  - không ra một-một thì dừng và hỏi người dùng.

  URL kênh: lấy từ lần học 2026-11-13 (nhật ký phiên trước); không có thì hỏi người dùng. Rồi chạy `learn refetch dusk-hypothetical-3 --videos <10 URL>`. Không ghi URL hay tên kênh vào tệp trong git.
- [ ] T021 [US2] Viết `learn craft <set> [--only vNN] [--strips 80]` trong `learn.py`, gọi `SL/craft.py` cho mọi cảnh của `shots.json`:
  - ghi `R/profile/<v>/craft.json`, với `person` lấy từ nhãn 021 (không `insert`, không `short`);
  - cắt dải 8 khung (320 px) cho 80 cảnh có người, rải đều theo video và cỡ cảnh (hạt giống cố định), vào `R/profile/<v>/strips/Sxxx.jpg`;
  - thêm `learn evidence <set> <vNN> <giây> --name <tên>` (khung 640 px vào `R/profile/<v>/evidence/`).
- [ ] T022 [P] [US2] Viết `SL/soundcraft.py` theo research R5, R6:
  - `speech_stats(words)`: từ/phút theo cửa sổ 10 s; nghỉ trong câu, giữa câu, giữa đoạn (> 0,6 s); nghỉ trước từ là số (chữ số hoặc số viết bằng chữ);
  - `music_windows(audio, words)`: cửa sổ 5 s gồm có nhạc (độ phẳng phổ < 0,3 trong ≥ 70% khung ở khoảng nghỉ ≥ 0,25 s) và mức nhạc so với giọng (dB);
  - `sfx_onsets(audio, words)`: flux > 4σ ngoài lời hoặc vượt nền > 6 dB, tính số mỗi phút;
  - `tempo(onsets, gaps)`: chỉ đo ở khoảng không lời ≥ 4 s, kèm độ tin cậy.

  Lệnh `learn sound <set> [--only vNN]` ghi `R/profile/<v>/sound.json`; thiếu mốc từ thì mã 3.
- [ ] T023 [P] [US2] Viết `tests/learn/test_soundcraft.py` trên âm thanh tổng hợp (giọng giả là chuỗi xung có mốc từ, nhạc là hoà âm 90 BPM ở −14 dB so với giọng, 6 tiếng gõ): đo đúng nghỉ (lệch ≤ 0,05 s), có nhạc, mức (lệch ≤ 2 dB), tempo (lệch ≤ 5 BPM), số tiếng động (lệch ≤ 1).
- [ ] T024 [US2] Chạy lần lượt trên `dusk-hypothetical-3`: `learn transcribe` (nếu mốc từ cũ không còn), `learn craft --strips 80`, `learn sound`. Mọi lệnh bọc `job run` của bước học. Ghi thời gian chạy `learn craft` (mục tiêu ≤ 60 phút cho 10 video) vào `R/style/craft-notes.md`. Kiểm `still_ratio` tính từ `craft.json` so với `summary.json` (lệch ≤ 0,02 mỗi video); lệch hơn thì sửa phép đo trước khi đi tiếp.
- [ ] T025 [US2] Claude, trong phiên:
  - đọc bản chép lời từng video, ghi `R/profile/beats.json` theo data-model.md (9 tên nhịp, liền nhau, phủ hết video, nhịp vắng thì bỏ);
  - đọc 80 dải khung, viết bảng loại động tác (chớp mắt, nghiêng đầu, tay giơ, miệng, đi, đổi biểu cảm…) với tần suất theo cỡ cảnh và bằng chứng `vNN/strips/Sxxx.jpg#k` vào `R/style/craft-notes.md`;
  - trích `learn evidence` cho máy, chuyển cảnh, cảnh không khí khi cần.
- [ ] T026 [US2] Viết `learn beats --check` và phần gom theo thời gian của `craft-summary` trong `SL/template.py`:
  - theo cỡ cảnh: máy, cử động;
  - theo nhịp: độ dài cảnh, chuỗi cỡ cảnh, máy động, cảnh có cử động, chuyển cảnh, từ/phút, nhạc, tiếng động/phút;
  - toàn bộ: `still_ratio`, `motion720_p50`, tỉ lệ chuyển cảnh, `person_active_share` p10, `rise_s`.

  Thêm test vào `tests/learn/test_template.py`. Chạy cả hai lệnh.
- [ ] T027 [US2] Chạy `learn clean dusk-hypothetical-3` ngay khi T024–T026 xong (cả khi dừng hay lỗi, FR-006). Kiểm `find R \( -name '*.mp4' -o -name '*.wav' -o -name '*.m4a' -o -name '*.webm' \)` ra rỗng (SC-007).
- [ ] T028 [US2] Viết `S/TEMPLATE.md` mục 11–15 và `## Công thức nhịp` (9 nhịp). Viết đủ `S/template.json` (`motion`, `transitions`, `voice`, `sound`, `beats`, `source`) theo data-model.md; mọi số lấy từ `craft-summary.json`.
- [ ] T029 [US2] Chạy `learn template-check dusk-hypothetical` (đủ, không `--partial`) và `check-names` trên các tệp mới. Mốc kiểm: SC-002, SC-007.

---

## Phase 5: User Story 4 - Tầng kiểm so phim với template (P4)

Làm trước US3, vì phải đo phim cũ khi nó còn dùng kit cũ (plan, bước 4).

**Goal**: luật `still_person`, `style_depth`, `style_still_ratio`, `style_motion720`, `style_person_motion`, `style_transitions`.

**Independent Test**: test trong `tests/filmcheck`; trên `hundred-words` cũ, `still_person` báo ≥ 15/21 cảnh và tỉ lệ máy đứng yên bị báo.

- [ ] T030 [US4] Viết `tools/filmcheck/motioncheck.py`:
  - gọi `tools/.venv/bin/python -I -m` một điểm vào của `SL/craft.py` với danh sách ảnh hoặc mp4, đọc JSON trả về;
  - thiếu venv thì báo lỗi mã 3 "cần `sh bin/studio deps learn`";
  - `template_of(film_dir)` đọc `template.json` của phong cách; không có thì trả `None`, và luật ghi `skipped: no template`.

  Thêm điểm vào `python -m sl.craft frames|video` vào `SL/craft.py`.
- [ ] T031 [US4] Sửa `tools/filmcheck/shots.mjs`:
  - chụp thêm 4 khung mỗi cảnh ở 20, 40, 60, 80% độ dài, cỡ 320×180, vào `.check/shots/motion/<id>-<k>.jpg`;
  - đọc `window.CAST` nếu trang có.

  Sửa `tools/filmcheck/shotcheck.py`:
  - luật chặn `still_person`: cảnh có người (`CAST` > 0). Trang không có `CAST` (vd. kit 022) thì ước lượng: cảnh có người = mọi cảnh trừ nhãn tầng 2 `insert` và trừ cảnh không có nhân vật nhìn thấy theo lượt nhãn tầng 2; kết quả ghi `person: estimated` mà tỉ lệ khối cử động < `motion.person_active_share_min`; báo mã cảnh, thời điểm, "thêm `act`, `move` hoặc `talk`";
  - luật cảnh báo `style_depth`: `focused_share` ngoài khoảng của cỡ cảnh trong `framing.by_scale`.
- [ ] T032 [US4] Sửa `tools/filmcheck/qc.py` và `stylerefs.py` (tầng 4): đo mp4 bằng `motioncheck`, rồi thêm cảnh báo phong cách `style_still_ratio`, `style_motion720`, `style_person_motion`, `style_transitions` theo `template.json`. `qc accept-style` dùng chung cho các luật này.
- [ ] T033 [P] [US4] Viết `tests/filmcheck/test_motioncheck.py`:
  - khung thử đứng yên → `still_person`;
  - có cử động → đạt;
  - máy trôi mà người đứng yên → vẫn báo `still_person`;
  - không có `template.json` → `skipped`;
  - thiếu venv → mã 3;
  - `style_*` trên số giả ngoài và trong khoảng.
- [ ] T034 [US4] Chạy trên `hundred-words` **khi kit của phim còn là bản cũ**: `qc shots hundred-words`, `qc hundred-words`.
  - Ghi kết quả vào `films/hundred-words/compare/before.json`.
  - Chụp khung cũ cho bảng ba cột (`page still` một khung giữa mỗi cảnh, vào `films/hundred-words/compare/old/`).
  - Mốc kiểm: SC-005 nửa đầu (≥ 15/21 cảnh, tỉ lệ máy đứng yên bị báo).

---

## Phase 6: User Story 3 - Bộ dựng v2, chứng minh cạnh khung mẫu (P3)

**Goal**: bộ dựng theo template; 4 đợt bảng so được duyệt.

**Independent Test**: test `node --test` của v2; bảng so từng thành phần; `K/REVIEW.md` có "duyệt" cho mọi thành phần.

### Chung

- [ ] T035 [US3] Chuẩn bị chung:
  - `learn pairs` trong `SL/pairs.py` và `learn.py` (contracts/cli.md, research R9): ≥ 3 cặp, dưới 3 thì mã 2; ảnh lưới `khung bộ dựng | khung mẫu`, có tên thành phần và số đo hai bên; với `--clip` thì mp4 hai nửa (trái là đoạn bộ dựng, phải là dải khung mẫu phát theo nhịp đo được, dựng từ ảnh), vào `R/pairs/<đợt>/`. Test trong `tests/learn/test_pairs.py`.
  - `page clip <phim> --from --to [--size]` trong `tools/filmcheck/cli.py` và `bin/studio`, dùng bộ ghi của specs/019 trên GPU, ≤ 10 s, ra `films/<phim>/.check/clips/`.
  - Phim nội bộ `films/kit-proof/` (trang có bảng cảnh chụp từng thành phần, có `channel attach` kênh `dusk-hypothetical`).
  - Tạo `K/REVIEW.md` theo data-model.md.
- [ ] T036 [US3] Thêm vào `K/plan.js` phần kiểm trường mới (contracts/kit-api-v2.md):
  - `act` (động tác trong `catalog.acts`, thời điểm trong cảnh), `talk`, `path` (chỉ với `walk`), `blink`, `move` (`type` trong `catalog.moves`), `frame` (0–1), `trans` (`fade` ≤ 2 mỗi phim), `gfx.icon` trong `catalog.icons`;
  - xuất `CAST`, `MOVES`;
  - thêm `acts`, `moves`, `icons`, `trans` vào `K/catalog.json`;
  - test trong `K/test/plan-v2.test.mjs`, kèm bảng cảnh 022 cũ vẫn chạy.

### Đợt 1: nhân vật (mặt, biểu cảm, áo, đám đông)

- [ ] T037 [US3] Sửa `K/figure.js`, theo mục 1, 2, 11 của `TEMPLATE.md`:
  - mặt mới: mắt tròn có đốm sáng, mí cong mảnh, má hồng, miệng nhỏ; 8 biểu cảm vẽ lại;
  - thân hoodie thon có mũ trùm và tay áo;
  - chớp mắt 0,12 s theo hạt giống và `template.json`; thở;
  - `act` lên trong `motion.rise_s` (dễ dần) rồi giữ; `talk` mấp máy 6–9 lần/s; `path` đi thật;
  - tất cả là hàm của `t`.

  Test trong `K/test/figure.test.mjs`: góc khớp đúng theo `t`, gọi đảo thứ tự cho cùng kết quả.
- [ ] T038 [P] [US3] Sửa `K/crowd.js` theo mục 7: người gần và vừa cùng kiểu thân áo mới; đám đông xa để mờ thành đốm qua độ sâu (dựa vào T042).
- [ ] T039 [US3] Chụp `kit-proof` cho mặt, biểu cảm, áo, đám đông; `page clip` cho chớp mắt, tay giơ, mấp máy; `learn pairs --batch 1` cho từng thành phần. Xem bảng bằng mắt trước, sửa chỗ thấy sai.
- [ ] T040 [US3] **Đợt duyệt 1**: gửi người dùng các bảng của T039 (đường dẫn trong máy, không gửi ra ngoài). Ghi quyết định vào `K/REVIEW.md`. Sửa tối đa 2 lần; lần 3 chưa duyệt thì dừng và hỏi.

### Đợt 2: khung hình (bố cục, độ sâu, ánh sáng, bối cảnh, cảnh không khí)

- [ ] T041 [US3] Sửa `K/camera.js` theo mục 3, 4, 12:
  - `frame: 'auto'` đặt chủ thể theo phân bố ô của cỡ cảnh; ECU lệch tâm hoặc cắt một mắt; vật tiền cảnh mờ;
  - độ sâu theo `focused_share` của cỡ cảnh;
  - `move` (`drift-h`, `drift-v`, `push`, `pull`, `follow`, `tilt`) có bắt đầu và dừng mềm; `auto` theo `motion.cam_by_scale` với hạt giống là mã cảnh.

  Test trong `K/test/camera.test.mjs`: vị trí máy theo `t`, tốc độ trong khoảng.
- [ ] T042 [P] [US3] Sửa `K/stage.js` và `K/sets/*.js` theo mục 5, 6, 10:
  - đèn chính ấm xiên, mảng sáng tối;
  - mỗi bối cảnh có bộ đạo cụ kể chuyện (thêm phần vào `K/sets/parts.js`);
  - cảnh đêm và báo động cách điệu theo bằng chứng.

  Kiểm độ sáng và bão hoà của 8 bối cảnh vẫn trong khoảng (SC-001 của 022).
- [ ] T043 [US3] Chụp và `learn pairs --batch 2` cho bố cục theo từng cỡ cảnh, độ sâu, ánh sáng, từng bối cảnh, cảnh đêm và báo động; `page clip` cho máy trôi, đẩy, bám.
- [ ] T044 [US3] **Đợt duyệt 2**, như T040.

### Đợt 3: đồ hoạ (thẻ số liệu, thẻ tiêu đề, thẻ cuối)

- [ ] T045 [US3] Sửa `K/graphics.js` và `K/film.js` theo mục 8, 9:
  - `stat` có `icon`: hình ẩn dụ vẽ bằng code, ≥ 8 icon trong `catalog.icons`;
  - thẻ tiêu đề và thẻ chương theo template;
  - `end-choice` chữ đậm, biểu tượng lựa chọn, dàn nhân vật 3D thật (`figure.js`) sau thẻ;
  - hiệu ứng vào thẻ theo thời gian đo được.

  Test trong `K/test/graphics.test.mjs` (tên icon trong danh mục đều vẽ được).
- [ ] T046 [US3] Chụp, `page clip` (thẻ vào), `learn pairs --batch 3`.
- [ ] T047 [US3] **Đợt duyệt 3**, như T040.

### Đợt 4: chuyển động và âm thanh (diễn xuất, máy, chuyển cảnh, tiếng động, nhạc)

- [ ] T048 [US3] Thêm `trans` vào `K/stage.js` và `K/film.js`: `streak`, `dip`, `fade` với độ dài theo `transitions`, tất định theo `t`. Test trong `K/test/film.test.mjs`.
- [ ] T049 [P] [US3] Viết `K/sound/`:
  - `timing.py` (`schedule` theo `template.json → voice`);
  - `score.py` (`compose` bằng `core/audio/sampler.py` của thư viện theo `beats.<nhịp>`: tempo, độ dày, lên, lặng);
  - `sfx.py` (`place` theo sự kiện bằng `core/audio/sfx.py`);
  - `mix.py` (giảm nhạc khi có lời theo `music_under_voice_db`, −14 LUFS).

  Test trong `tests/render/test_sound.py` với nhạc cụ giả lập khi thiếu bộ mẫu: tempo, mức so với giọng, độ dài khớp. Thêm dòng chạy test Python này vào `tests/render/run.sh` (hiện chỉ chạy test Node).
- [ ] T050 [P] [US3] Viết `voice make <phim>` trong `tools/filmcheck/cli.py` và `bin/studio` (research R7):
  - ghi `voices/.say.json` (thay `text` bằng `say` ở dòng có `say`) rồi gọi `tts.py` của thư viện;
  - sửa `tools/filmcheck/voicecheck.py` thêm luật `mispronounced` (mã dòng, chữ đúng, chữ nghe được, "thêm `say` cho dòng <id>").

  Test trong `tests/filmcheck/test_voicemake.py`.
- [ ] T051 [US3] Dựng một cảnh mẫu 20–30 s ở `kit-proof` có đủ diễn xuất, máy, chuyển cảnh, nhạc, tiếng động.
  - `page clip` từng đoạn; trộn tiếng bằng `K/sound/`.
  - `learn pairs --batch 4` với số đo của bộ dựng (chạy `motioncheck` trên clip) đặt cạnh số của kênh mẫu.
  - Ghi số âm thanh (tiếng động/phút, mức nhạc) cạnh số của kênh.
- [ ] T052 [US3] **Đợt duyệt 4**, như T040. Mốc kiểm: SC-004.

---

## Phase 7: User Story 5 - Phim thử làm lại, bảng so trước/sau (P5)

**Goal**: `hundred-words` dựng lại bằng bộ dựng v2, qua đủ các tầng kiểm cùng luật mới, có bảng ba cột.

**Independent Test**: xem phim mới, `compare/`, `before-after.json`.

- [ ] T053 [US5] Chuẩn bị phim:
  - `kit use hundred-words --update`;
  - sửa `films/hundred-words/build_plan.py` cho bảng cảnh dùng `act`, `talk`, `move`, `frame`, `trans`, `icon`, và mốc dòng theo `K/sound/timing.py` (bỏ `GAP_IN`, `GAP_PARA` tự đặt);
  - thêm `say` cho dòng có "hurt" trong `lines.json`;
  - chạy `voice make`, `voice asr`, `qc voice`. Kịch bản đã duyệt không đổi.
- [ ] T054 [US5] Chạy `qc plan`, `qc shots` (lượt gán nhãn tầng 2 tốn tiền: hỏi người dùng trước), sửa tới khi 0 `still_person`; tầng 1 vẫn kiểm phụ đề in trên hình (FR-015), ghi lại kết quả. Rồi `render hundred-words --fps 60` (GPU; phần mềm thì dừng và hỏi) và `qc hundred-words`; nhạc và tiếng bằng `K/sound/`. Ghi thời gian dựng (mục tiêu ≤ 10 phút) vào `compare/before-after.json`.
- [ ] T055 [US5] Lập `films/hundred-words/compare/`:
  - bảng ba cột (cũ từ T034 | mới | khung mẫu cùng cỡ cảnh) cho từng loại cảnh, bằng `learn pairs` với cột thứ ba;
  - `before-after.json` gồm `still_ratio`, `motion720_p50`, số cảnh `still_person`, `style_*`, LUFS, LRA của cũ và mới.

  Mốc kiểm: SC-005 nửa sau.
- [ ] T056 [US5] Xem phim mới bằng mắt theo thời gian (khung qua nhiều thời điểm, không chỉ ảnh tĩnh), so với khung mẫu cùng loại cảnh, trước khi giao.
- [ ] T057 [US5] Giao người dùng: phim, bảng ba cột, bảng số. Ghi quyết định chấp nhận (SC-006).

---

## Phase 8: Polish & Cross-Cutting

- [ ] T064 [P] Thêm `learn compare --clip <mp4>` trong `SL/compare.py` và `learn.py` (FR-007): đo đoạn video của khung chứng minh bằng `SL/craft.py` (`still_ratio`, `motion720_p50`, tỉ lệ cảnh có cử động), so với `craft-summary.json`, in đạt hoặc ngoài khoảng cho từng số. Test trong `tests/learn/test_compare_clip.py` trên video của T002.

- [ ] T058 [P] Sửa `.claude/skills/style-learn/SKILL.md` (FR-007, dùng `learn compare --clip` của T064): thêm các bước `refetch` hoặc `fetch` có `url`, `craft`, `sound`, `beats`, `craft-summary`, viết `TEMPLATE.md` và `template.json`, `template-check`, khung chứng minh có đoạn video ngắn so cả số chuyển động (`page clip` và `pairs`); `clean` ngay sau phần đo.
- [ ] T059 [P] Sửa `CLAUDE.md`:
  - luồng làm phim đọc `TEMPLATE.md` của phong cách (nếu có) trước khi lập bảng cảnh;
  - `voice make` thay việc gọi thẳng `tts.py`;
  - các luật mới của tầng 2 và tầng 4;
  - `page clip`.

  Sửa `S/STYLE.md` §10 trỏ tới `TEMPLATE.md`.
- [ ] T060 [P] Ghi các bộ nhạc cụ được dùng vào `CREDITS` (giấy phép theo LICENSE của từng bộ trong thư viện); chạy `desktop/core-build/credits-check.py`.
- [ ] T061 Chạy `check-names` trên mọi tệp chữ mới: `TEMPLATE.md`, `template.json`, `STYLE.md`, `EVIDENCE.md`, `K/REVIEW.md`, `K/**/*.js`, `K/sound/*.py`.
- [ ] T062 Chạy đủ: `sh tests/run.sh`, `sh tests/learn/run.sh`, `sh tests/filmcheck/run.sh`, `sh tests/render/run.sh`, `sh tests/ui/run.sh`.
- [ ] T063 Ghi kết quả vào mục "Kết quả" của `quickstart.md` (đạt, đạt một phần, thất bại, kèm số). Cập nhật bộ nhớ dự án. Commit sau mỗi phase, chỉ các tệp có tên.

---

## Dependencies

- Phase 1 → Phase 2 → US1 (Phase 3).
- US2 (Phase 4) cần Phase 2. Nó độc lập với US1 về code, nhưng `template-check` đủ cần cả hai.
- US4 (Phase 5) cần `template.json` đầy đủ (T028). T034 phải chạy trước T053 (phim còn kit cũ).
- US3 (Phase 6) cần US1, US2 (template) và T030 (`motioncheck` cho T051). Đợt N+1 chỉ bắt đầu sau khi đợt N được duyệt.
- US5 (Phase 7) cần US3, US4.
- Polish sau cùng; T058 có thể làm ngay sau US2.

## Parallel

- Phase 2: T003/T004 (cùng tệp, nối tiếp) song song với T006, T007.
- US2: T018, T019, T022, T023 song song; T024 trở đi nối tiếp.
- US3: trong mỗi đợt, các tệp khác nhau ([P]) làm song song; T049, T050 song song với T048.
- Polish: T058, T059, T060 song song.

## Implementation Strategy

1. **MVP = US1**: template phần hình và `STYLE.md` có nhãn. Đây là điểm dừng đầu tiên, có giá trị riêng (sửa lỗi gốc "luật không bằng chứng").
2. US2, để template đủ 15 mục và 9 nhịp. Video được xoá ngay sau phần đo.
3. US4 trên phim cũ (đo "trước").
4. US3 theo 4 đợt duyệt.
5. US5 (đo "sau", người dùng quyết định phim dài).

Commit sau mỗi phase.
