# Tasks: 040-whatif-rig

## Phase 1: Setup

- [X] T001 Tạo phim thử ngoài git `films/rig040-proof/` (`film.json` engine ae, `ae/shots.jsx`, `cast/cast.json` với hero kid áo vàng, mum adult, baby toddler, rig `ball@3`)

## Phase 2: User Story 1 — rig ball@3 (P1)

- [X] T002 [US1] Viết `tools/ae/kit/rigs/ball/v3/catalog.json` theo contracts/rig-ball3.md
- [X] T003 [US1] Viết `tools/ae/kit/rigs/ball/v3/ball.jsx`: đầu (R2), thân + hoodie theo tuổi, tay chân 3 nét gấp khúc, bàn tay, giày vòm, bóng tiếp đất, tư thế theo vai/hông của tuổi, `size`, `sizeOf`
- [X] T004 [US1] `tools/ae/kit/castsheet.jsx`: cận mặt dùng `rig.sizeOf(spec)` khi rig có
- [X] T005 [US1] Test `tests/ae/test_rigs.py`: catalog ball@3 có đủ views/expressions/poses của ball@2, `ages`, cú pháp jsx (`node --check` trên bản bọc), bundle mang ball@3 khi cast dùng nó
- [X] T006 [US1] Viết `specs/040-whatif-rig/measure_sheet.py` (đo chiều cao theo đầu, mắt, tay, chân, bàn tay, viền trên ảnh toàn thân nền phẳng)
- [X] T007 [US1] Chạy `ae sheet rig040-proof` thật, đo, sửa rig tới khi SC-002 đạt; ảnh ghép cạnh khung mẫu trong `references/whatif-long/proof/out/`
- [X] T008 [US1] Dựng một shot AE có `CU.who`, đi bộ, `CU.carry`, đổi biểu cảm với ball@3 (acceptance US1 #4); xem khung dày ở chuyển động

## Phase 3: User Story 2 — bếp và phòng khách (P2)

- [X] T009 [P] [US2] `tools/blender/kit/sets/kitchen.py` (≥ 8 món: tủ trên, tủ dưới, mặt bếp, bếp nấu, tủ lạnh, bồn rửa, bàn ăn, ghế, lò nướng bánh mì, hũ, cửa sổ)
- [X] T010 [P] [US2] `tools/blender/kit/sets/livingroom.py` (≥ 8 món: sofa, bàn nước, TV + kệ, đèn bàn, thảm, cây, khung tranh, cửa sổ, giấy dán tường)
- [X] T011 [US2] Test `tests/blender/test_sets.py`: mỗi tệp bối cảnh có `build(k, light, seed)`, chỉ import `kit.*`/bpy/mathutils/math/random, `k.objects` có `look`, `cam_dir`, `floor`, `walk` (đọc mã nguồn, không cần bpy)
- [X] T012 [US2] Ảnh tĩnh ¼ cỡ 3 góc mỗi phòng trên Blender thật (GPU), đo luma/contrast/saturation (FR-010), chỉnh tới khi đạt; xem bằng mắt

## Phase 4: User Story 3 — khung chứng minh (P3)

- [X] T013 [US3] Shot 6 s: phòng khách Blender + hero và mum ball@3 + máy đẩy có ease; dựng GPU; `learn compare` ảnh và clip (≤ 2 vòng sửa)

## Phase 5: Polish

- [X] T014 Khoá `sh bin/studio ae rigs --lock ball@3` sau khi bảng mẫu được duyệt; test khoá qua
- [X] T015 [P] Tài liệu: `tools/CLAUDE.md`, `specs/038-blender-engine/contracts/blender-kit.md` (thêm kitchen, livingroom), mục rig trong `CLAUDE.md` gốc nếu có danh sách rig
- [X] T016 Chạy đủ 8 bộ test, ghi kết quả vào quickstart.md
