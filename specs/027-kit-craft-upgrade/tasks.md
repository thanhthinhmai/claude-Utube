---
description: "Task list for 027 — nâng tay nghề bộ dựng 3D"
---

# Tasks: Nâng tay nghề bộ dựng 3D

**Input**: `specs/027-kit-craft-upgrade/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md)

**Tests**: bắt buộc theo hiến pháp IV. Logic thuần có test tự động; phần hình có bảng so, clip và số đo.

**Duyệt**: mỗi dòng "⏸ Duyệt" là điểm dừng, chờ người dùng xem bảng so và clip (FR-017) trước khi làm tiếp.

## Phase 1: Setup

- [X] T001 Nối `lib/`, `references/`, `films/`, `tools/.venv` của thư mục chính vào worktree `/home/thinhmt/claude-Utube-027` bằng symlink, thêm chúng vào `.git/info/exclude` của worktree (không commit), rồi chạy `sh bin/studio status` để xác nhận dòng `dựng hình: gpu`
- [X] T002 Chạy 5 bộ test gốc (`sh tests/run.sh`, `sh tests/filmcheck/run.sh`, `sh tests/learn/run.sh`, `sh tests/ui/run.sh`, `sh tests/render/run.sh` (gồm test của kit)) và ghi kết quả gốc vào `specs/027-kit-craft-upgrade/baseline.md` (mục "Test gốc")
- [X] T003 Ghi số đo "trước" vào `specs/027-kit-craft-upgrade/baseline.md`: 5 khung tham chiếu của `films/pause-ten-seconds` và `films/hundred-words` (t = 10, 60, 120, 200, 290), thời gian dựng GPU 10 s của pause-ten-seconds, tỉ lệ action/outdoor/prop/ots của bảng cảnh phút đầu 0:00–1:00

## Phase 2: Foundational (đo tay nghề kênh mẫu, FR-014)

- [X] T004 Viết `tools/filmcheck/craftlabel.py`: prompt theo định nghĩa R2 (`card`, `people`, `action`, `outdoor`, `prop`), schema JSON, gọi `claude -p` bằng model của `tools/models.json` (dùng lại `_env`/`_call` của `labeler.py`), cache theo `version()` cộng nguồn bảng ảnh vào `references/<set>/profile/craft-labels.json`, thử lại 2 lần
- [X] T005 [P] Viết `tests/learn/test_craftlabel.py` với `claude` giả: kiểm cache, câu trả lời sai schema bị loại, id thiếu thì gọi lại, tính tỉ lệ theo video (bỏ `card`; bỏ cảnh không có người khỏi mẫu số của action và prop)
- [X] T006 Thêm lệnh `craft-label <set> [--force] [--write <style>]` vào `tools/style-learn/learn.py` theo `contracts/cli.md`. `--write` ghi `craft` vào `my-styles/<style>/template.json` theo `data-model.md` (khoảng p25–p75 theo 10 video, `ots` lấy từ nhãn góc của `labels`) và thêm mục vào `my-styles/<style>/EVIDENCE.md`
- [X] T007 Ghi tạm `craft.action.min = 0.5` kèm `"source": "studio rule"` vào `my-styles/dusk-hypothetical/template.json` (thay bằng số đo ở T008)
- [X] T008 ⏸ Hỏi người dùng trước khi chạy (tốn hạn mức gói Claude). Chạy `sh bin/studio learn craft-label dusk-hypothetical-3` (khoảng 20 lượt gọi Opus trên gói của chủ xưởng), kiểm tay 30 cảnh ngẫu nhiên trên bảng ảnh (nhãn `action` đúng ≥ 85%), rồi `--write dusk-hypothetical`. ⏸ Duyệt: báo người dùng các tỉ lệ đo được và mức `action.min` đề xuất

## Phase 3: User Story 1 — Nhân vật làm việc trong cảnh (P1) 🎯 MVP

**Goal**: đồ cầm tay, act cả người và hai người, máy qua vai mặc định, máy `hands` và `hero-low`, luật `craft_*` của tầng 1.

**Independent Test**: trang thử `films/kit-acting` (mỗi act mới một cảnh, bối cảnh sẵn có), bảng so ba hàng và clip ≤ 10 s; `qc plan` báo đúng `craft_action`.

### Tests (US1)

- [X] T009 [P] [US1] `my-styles/dusk-hypothetical/kit/test/items.test.mjs`: mỗi item có `grip` `one`/`both`; đồ bám tay luôn ở trong khoảng 0,05 đơn vị quanh bàn tay ở 20 thời điểm của mỗi act
- [X] T010 [P] [US1] `my-styles/dusk-hypothetical/kit/test/acting-v3.test.mjs`: act mới là hàm thuần (cùng `lt` cho cùng kết quả, theo thứ tự gọi bất kỳ); `handoff` có đúng một mốc đổi chủ; đường ném liên tục; `kind` của mọi act trong danh mục đúng R5; act một lần (không lặp) có `dur` ≤ 1,5 s (US1 kịch bản 1)
- [X] T011 [P] [US1] `my-styles/dusk-hypothetical/kit/test/ots.test.mjs`: cảnh ≥ 2 người có `talk` mà không có `cam` thì nhận `ots`; hai cảnh liền nhau đổi `subject` và giữ phía; cảnh thiếu `cam` không có `talk` vẫn lỗi như cũ; cặp qua vai mà một người ở ngoài `room` của bối cảnh thì nhận `mid-eye` có cả hai và ghi lý do vào cảnh báo của plan; bảng cảnh của `films/pause-ten-seconds` cho `SHOTS` giống hệt trước
- [X] T012 [P] [US1] `tests/filmcheck/test_craft.py`: `craftcheck` đếm CRAFT (bỏ `card`), `craft_action` là lỗi dưới `min`, `craft_outdoor`/`craft_prop`/`craft_ots` là cảnh báo ngoài khoảng, `qc except` từng cảnh được bỏ khỏi mẫu số, trang không có CRAFT thì luật vào `skipped`; `craft_item_default` là cảnh báo khi act cần đồ mà không ghi đồ

### Implementation (US1)

- [X] T013 [US1] `my-styles/dusk-hypothetical/kit/catalog.json`: `items` (phone, book, bag, cup, paper, ball, cards, cash, box, keys kèm `grip`, `size`, `default_for`); `acts` thành `{name: {kind, dur, item, needs}}` theo `data-model.md`; `cams` thêm `hands`, `hero-low`
- [X] T014 [US1] `my-styles/dusk-hypothetical/kit/plan.js`: `actOk` đọc được `acts` dạng bảng, nhận `<act>:<item>` và `@<who>` (who là chỉ số trong cast); kiểm `needs: partner`; hàm `kindOf(act)`; mặc định `ots` và luật 180° theo R6 (một người ở ngoài `room` thì dùng `mid-eye` có cả hai, ghi cảnh báo); xuất `CRAFT` theo `data-model.md`
- [X] T015 [US1] `my-styles/dusk-hypothetical/kit/figure.js`: dựng 5 đồ mới; `hold(item, {hand})` bám một tay (grip `one`) hoặc giữa hai tay; chân `run`, `jump`, `fall`, `carry`; tay `throw`, `push`, `type`, `give`, `high-five`
- [X] T016 [US1] `my-styles/dusk-hypothetical/kit/acting.js`: `actState` cho act `body` và `pair` (chân, thân, tay theo thời gian; `run`, `carry`, `type` lặp), `handoff(lt, t, dur)`, `throwPath(lt, t, from, to)`
- [X] T017 [US1] `my-styles/dusk-hypothetical/kit/camera.js`: `hands` (nhắm điểm bám, aper nông) và `hero-low` (máy thấp hơn ngực, nhìn lên, cỡ trung)
- [X] T018 [US1] `my-styles/dusk-hypothetical/kit/film.js`: áp act mới mỗi khung, đồ chuyển tay theo `handoff`, đồ bay theo `throwPath`, `cast[i].item`/`hand`, xuất `window.CRAFT`
- [X] T019 [US1] `tools/filmcheck/plan.mjs` đọc `window.CRAFT`; viết `tools/filmcheck/craftcheck.py`; gọi từ `tools/filmcheck/plancheck.py` khi phong cách có `template.json → craft`; nối `qc except … craft_action` qua `tools/filmcheck/tiers.py`
- [X] T020 [US1] Trang thử `films/kit-acting/index.html` (`kit use`): mỗi act và đồ mới một cảnh, một cặp qua vai hai cảnh, một cảnh `hands`, một cảnh `hero-low`; chụp ảnh bằng `sh bin/studio page still` và clip bằng `sh bin/studio page clip`
- [X] T021 [US1] Hai bảng so ba hàng (ô kênh mẫu từ `craft-labels.json`, cảnh tương ứng của pause-ten-seconds, cảnh mới): `films/kit-acting/compare-acts.jpg` (đồ và động tác, ô có `action` hoặc `prop`) và `films/kit-acting/compare-cams.jpg` (góc máy, ô qua vai, cận tay, góc thấp), mỗi bảng một clip ≤ 10 s. ⏸ Duyệt

## Phase 4: User Story 2 — Bối cảnh ngoài trời hoàng hôn (P2)

**Goal**: 4 bối cảnh ngoài trời mới, 10 phần dựng dùng chung, mật độ đồ cho mọi bối cảnh.

**Independent Test**: `catalog.html` có khung toàn và khung trung có người cho mỗi bối cảnh; `sets.test.mjs` đạt; bảng so với ô kênh mẫu có `place` cùng loại.

- [ ] T022 [P] [US2] `my-styles/dusk-hypothetical/kit/test/sets.test.mjs`: dựng từng bối cảnh trong node, đếm `props` theo lớp, so `props_min` (tổng và mỗi lớp ≥ 1); bối cảnh ngoài trời có `sky` và nguồn sáng tự phát
- [ ] T023 [US2] `my-styles/dusk-hypothetical/kit/sets/parts.js`: `tree`, `streetLamp`, `fence`, `house` (cửa sổ sáng tự phát), `hoop`, `railing`, `parkLines`, `skyDome`, `windowGlow`, `sunBeam`; mỗi hàm ghi `{kind}` vào danh sách `props` của bối cảnh
- [ ] T024 [P] [US2] `my-styles/dusk-hypothetical/kit/sets/court.js` (sân bóng rổ: rổ, hàng rào, cột đèn, nhà sau, cây)
- [ ] T025 [P] [US2] `my-styles/dusk-hypothetical/kit/sets/rooftop.js` (lan can, bồn nước, dây đèn, đường chân trời thành phố)
- [ ] T026 [P] [US2] `my-styles/dusk-hypothetical/kit/sets/parking.js` (vạch, xe, cột đèn, hàng rào, cửa hàng sáng đèn)
- [ ] T027 [P] [US2] `my-styles/dusk-hypothetical/kit/sets/street-dusk.js` (phố có nhà cửa sổ sáng, vỉa hè, cây, xe đỗ, cột đèn, ba lớp)
- [ ] T028 [US2] Đăng ký 4 bối cảnh trong `my-styles/dusk-hypothetical/kit/sets/index.js` và `catalog.json` (`outdoor`, `sky`, `props_min`); thêm `outdoor`/`props_min` cho 7 bối cảnh cũ
- [ ] T029 [US2] Thêm đồ cho 7 bối cảnh cũ (`classroom`, `lockers`, `gym`, `bedroom`, `cafeteria`, `street`, `stadium`) tới `props_min`, kèm cửa sổ sáng hoặc `windowGlow` ở bối cảnh trong nhà; `film.js` nhận `outdoor` của `custom:` (thiếu thì false và ghi cảnh báo)
- [ ] T030 [US2] Cập nhật `my-styles/dusk-hypothetical/kit/catalog.html` (khung toàn và khung trung có người cho mỗi bối cảnh); bảng so `films/kit-acting/compare-us2.jpg` với ô kênh mẫu có `place` cùng loại. ⏸ Duyệt

## Phase 5: User Story 3 — Ánh sáng và hậu kỳ (P3)

**Goal**: grade v3 thành mặc định, có bằng chứng, phim cũ không đổi.

**Independent Test**: `learn compare` đạt; 6 cảnh cũ/mới cạnh ô kênh mẫu; thời gian dựng ≤ +50%; khung phim cũ giống hệt.

- [ ] T031 [US3] Đo thời gian mỗi khung trên GPU, có và không AO, ở 1920×1080 trên 3 bối cảnh (R4), ghi vào `specs/027-kit-craft-upgrade/baseline.md`; chọn AO cho mọi cảnh hay chỉ cảnh trung và gần
- [ ] T032 [US3] `my-styles/dusk-hypothetical/kit/stage.js`: grade v3 từ `films/kit-post/kit/stage.js` (vòm trời, sương sáng, AO, phơi sáng, bão hoà, ánh mặt, bloom) thành mặc định, bỏ cờ `?post=v2`; `sunBeam` và `windowGlow` dùng được từ bối cảnh
- [ ] T033 [US3] Chạy `learn compare` trên khung chứng minh dựng lại bằng v3. Nếu độ sáng trung vị vượt khoảng thì đo lại khoảng trên ô bảng ảnh 10 video (R8), sửa `my-styles/dusk-hypothetical/style.json` và `EVIDENCE.md` kèm bằng chứng; chỉnh số tới khi đạt
- [ ] T034 [US3] Viết lại `my-styles/dusk-hypothetical/kit/GRADE.md` (mỗi số mới kèm số đo và vòng chỉnh)
- [ ] T035 [US3] Kiểm FR-013: dựng 5 khung của `films/pause-ten-seconds` và `films/hundred-words` bằng kit đã chép của chúng, so với T003 (khác biệt = 0)
- [ ] T036 [US3] Bảng so `films/kit-acting/compare-us3.jpg` (ô kênh mẫu, v2 cũ, v3) cho 6 cảnh của bản thử và 2 bối cảnh ngoài trời mới. ⏸ Duyệt

## Phase 6: User Story 4 — Làm lại phút đầu của pause-ten-seconds (P4)

**Goal**: bằng chứng cuối, cùng lời, giọng và mốc cắt.

**Independent Test**: tầng 0–4 đạt, bảng so ba hàng, hai clip 60 s.

- [ ] T037 [US4] Tạo `films/pause-ten-redo/` bằng `channel attach` và `kit use`, chép `lines.json`, `voices/`, `cues.json`, `narration.json` của 0:00–1:00 từ `films/pause-ten-seconds` (phim gốc giữ nguyên); `job start`
- [ ] T038 [US4] Viết bảng cảnh mới cho 0:00–1:00 trong `films/pause-ten-redo/index.html`, giữ mốc cắt, dùng act, đồ, máy và bối cảnh mới theo `TEMPLATE.md`
- [ ] T039 [US4] Chạy `qc voice`, `qc plan`, `qc shots` tới khi đạt (`craft_action` đạt; nhãn tầng 2 khớp ≥ 80%)
- [ ] T040 [US4] `sh bin/studio render pause-ten-redo --fps 60` (GPU, bọc `job run`), rồi `sh bin/studio qc pause-ten-redo`; ghi thời gian dựng so với T003 (SC-006) và chuyển động trong cảnh so với bản gốc (SC-003)
- [ ] T041 [US4] Bảng so ba hàng `films/pause-ten-redo/compare.jpg` và hai clip 60 s trước và sau; ghi SC-001…SC-008 vào `specs/027-kit-craft-upgrade/quickstart.md` (đạt, đạt một phần, thất bại). ⏸ Duyệt: người dùng chọn có dùng kit v3 cho phim dài không

## Phase 7: Polish

- [ ] T042 [P] Cập nhật `my-styles/dusk-hypothetical/TEMPLATE.md` (cách dùng act, đồ, máy, bối cảnh mới và luật craft) và `specs/023-style-craft-template/contracts/kit-api-v2.md` (dẫn sang `kit-api-v3.md`)
- [ ] T043 [P] Cập nhật `CLAUDE.md` (luồng làm phim: CRAFT, `learn craft-label`, luật `craft_*`) và `my-styles/dusk-hypothetical/kit/catalog.json → version` = 3
- [ ] T044 Chạy lại 5 bộ test của T002 (tất cả xanh), rồi commit đúng các tệp đã đổi (không `git add` thư mục, không commit symlink)

## Dependencies & Execution Order

- Edge case "hậu kỳ chậm với WebGL phần mềm": không cần task, xưởng đã dừng và hỏi khi rơi về dựng phần mềm.
- Phase 1 → Phase 2 (T008 cần T004–T006) → US1 → US2 → US3 → US4 → Polish.
- US1 chỉ cần `template.json → craft` (T007 tạm là đủ để code chạy; T008 cho số thật).
- US2 dùng `CRAFT.outdoor` của US1 (T014) cho luật `craft_outdoor`; phần dựng bối cảnh (T023–T029) làm song song với US1 được.
- US3 cần bối cảnh của US2 cho bảng so T036; T031–T032 làm sớm được.
- US4 cần US1–US3 đã duyệt.

## Parallel Examples

- US1: T009, T010, T011, T012 cùng lúc (khác tệp); rồi T013 → T014 → (T015, T016, T017) → T018 → T019.
- US2: T024, T025, T026, T027 cùng lúc sau T023.

## Implementation Strategy

MVP = Phase 2 + US1: đo tay nghề, rồi nhân vật làm việc có đồ trong tay và máy qua vai, chứng minh bằng `films/kit-acting`. Mỗi story dừng ở điểm ⏸ Duyệt. Không làm phim dài bằng kit v3 trước khi T041 được duyệt.
