# Implementation Plan: Rig ball@3 có khối và hai phòng Blender (bếp, phòng khách)

**Branch**: `040-whatif-rig` | **Date**: 2026-11-28 | **Spec**: [spec.md](spec.md)

## Summary

Thêm rig AE phiên bản mới `tools/ae/kit/rigs/ball/v3/` (ExtendScript, cùng giao diện `make/pose/key/place/carry/expression/view` như `ball@2`), vẽ theo số đo mẫu (`references/whatif-long/analysis/rig-measure.json`): đầu R=200 trong khung 1000×1400 (chân 500,1360), cao 3,15 đầu, tay chân ống thẳng đầu tròn có viền và dải tối bên phải, khuỷu và gối là hai đoạn chồng nhau, giày vòm, hoodie có vòng cổ, dây, túi, cổ tay. Khoá `ball@3` vào `tools/ae/rigs.lock` bằng `sh bin/studio ae rigs --lock ball@3`. Thêm hai bối cảnh Blender `tools/blender/kit/sets/kitchen.py` và `livingroom.py` theo mẫu `office.py`. Kiểm bằng bảng mẫu AE thật, ảnh tĩnh Blender ¼ cỡ, và một shot chứng minh 6 s so bằng `learn compare`.

## Technical Context

**Language/Version**: ExtendScript (ES3) cho AE 2027; Python 3 trong Blender 5.2.5 (`bpy`); Python 3.12 cho test và đo.
**Primary Dependencies**: bộ dựng AE `tools/ae/kit/` (`lib.jsx` CU.*), `tools/ae/rigs.py`, `bundle.py`, `sheet.py`; bộ dựng Blender `tools/blender/kit/` (`mesh`, `toon`, `light`).
**Storage**: tệp; `tools/ae/rigs.lock` thêm một dòng.
**Testing**: `sh tests/ae/run.sh`, `sh tests/blender/run.sh` + đủ các bộ test của xưởng; chạy thật: `ae sheet`, `blender build --still --quarter`, `ae build` một shot, `learn compare`.
**Target Platform**: WSL2 + AE và Blender trên Windows (đã cấu hình, `ae status`, `blender status` sẵn sàng).
**Project Type**: bộ dựng dùng chung của xưởng (CLI).
**Performance Goals**: không đổi; rig mới không được chậm hơn `ball@2` quá 1,5× khi dựng bảng mẫu.
**Constraints**: `ball@1`, `ball@2` không đổi byte nào (khoá); không sửa `lib/`; dựng GPU; không đưa khung mẫu ra ngoài `references/`.
**Scale/Scope**: 2 tệp rig (jsx + catalog), 2 tệp bối cảnh, 1 dòng khoá, sửa nhỏ `castsheet.jsx` (cận mặt theo tuổi), test, tài liệu.

## Constitution Check

| Nguyên tắc | Đánh giá |
|---|---|
| I. Spec là nguồn sự thật | Spec 040 đã viết, số đo sửa vào spec trước plan. ✓ |
| II. Không đoán | Tỉ lệ lấy từ đo 20 nhân vật/15 khung/7 video, không lấy báo cáo cũ. ✓ |
| III. MVP theo story | US1 (rig) tự test được bằng bảng mẫu; US2 (phòng) độc lập; US3 kiểm cả hai. ✓ |
| IV. Đo được | SC-002 đo tỉ lệ trên bảng mẫu bằng script; SC-004 đo độ sáng/tương phản/bão hoà; xem thật. ✓ |
| V. Đơn giản | Phiên bản rig mới theo cơ chế sẵn có của 034; không thêm lớp trừu tượng. ✓ |
| VI. Thư viện gốc | Không chạm `lib/`. ✓ |
| VII. Ba bộ máy | Nhân vật vẫn là một bản code AE; phòng là Blender; mọi hình do code. ✓ |
| VIII. Học bằng đo | Hình dáng đo trên ≥ 10 khung; sửa nhận định sai (người lớn 4,5 đầu) vào nhật ký sửa của phong cách. ✓ |
| Bản quyền | Không tên kênh, nhân vật, thoại; khung mẫu chỉ trong `references/`. ✓ |

Không vi phạm.

## Project Structure

### Documentation (this feature)

```text
specs/040-whatif-rig/
├── spec.md
├── plan.md
├── research.md
├── quickstart.md
├── contracts/rig-ball3.md
└── tasks.md
```

### Source Code (repository root)

```text
tools/ae/kit/rigs/ball/v3/ball.jsx      # rig mới (khoá sau khi duyệt)
tools/ae/kit/rigs/ball/v3/catalog.json  # views, expressions, poses, walk, spec (+age), hats, ages
tools/ae/rigs.lock                      # + "ball@3"
tools/ae/kit/castsheet.jsx              # cận mặt dùng rig.sizeOf(spec) nếu có
tools/blender/kit/sets/kitchen.py       # bối cảnh mới
tools/blender/kit/sets/livingroom.py    # bối cảnh mới
tests/ae/test_rigs.py                   # ball@3 có khoá, catalog, cú pháp jsx
tests/blender/test_sets.py              # hai bối cảnh: build() chạy với bpy giả, đủ đồ, objects
tools/CLAUDE.md, specs/038-blender-engine/contracts/blender-kit.md  # tài liệu danh mục
```

**Structure Decision**: dùng nguyên cấu trúc bộ dựng; không có tệp mới ngoài các tệp trên.

## Complexity Tracking

Không có.
