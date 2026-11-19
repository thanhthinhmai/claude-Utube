# Implementation Plan: Bộ dựng SVG cho phong cách Sketch Explainer

**Branch**: `028-sketch-kit` | **Date**: 2026-11-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/028-sketch-kit/spec.md`

## Summary

Phong cách `sketch-explainer` có bộ dựng `my-styles/sketch-explainer/kit/`: module ES thuần (SVG DOM, không bước build), tách từ bộ vẽ của `films/anthropic-ipo-15/` và phần lõi đã dọn trong `styleframe/`, rồi chỉnh cho khớp số đo của phong cách:
- nét viền theo bề ngang khung;
- chân không bàn chân, người phụ mặt trắng;
- bảng màu xám dịu;
- máy đi thẳng có dịch nhẹ và giữ cuối cảnh;
- lịch hành động mỗi 2–3 giây;
- 24+ bối cảnh dựng từ phần.

Trang phim chỉ còn bảng cảnh: `film({scenes})` trong `kit/film.js` dựng ra hợp đồng trang của thư viện (`render(t)`, `READY`, `DUR`, `SHOTS`, `CARDS`, `TEXTS`, `CLEAN`). Bộ dựng được chép vào phim bằng `kit use` hiện có của specs/022 (R1).

Người thật vào một **thư viện người thật** ở gốc dự án (`people/<slug>/`, trong git): hình vẽ, trạng thái duyệt gắn với dấu băm của hình. Lệnh mới `sh bin/studio people …` tạo người mới, làm bảng mẫu, ghi duyệt và chép người vào phim (`films/<tên>/people/`), vì trang phim chỉ với tới thư mục phim (R2).

Tầng 1 (`qc plan`) đọc thêm từ trang ba thứ:
- lỗi tên của bộ dựng;
- người thật trong phim, để đối chiếu dấu duyệt;
- bong bóng của người thật, để đối chiếu với trích dẫn trong `SOURCES.md` (R3, R4).

Test quét mã chặn các lệnh vẽ hỏng trên GPU (R8). Sửa `soundcraft.py` cho chỉ đo trong đoạn đã đo (R9). Cuối cùng làm phim mẫu 30–60 giây.

## Technical Context

**Language/Version**:
- JavaScript (ES modules, chạy trong Chromium của bộ dựng hình) cho bộ dựng, không bước build, có `// @ts-check`.
- Python 3.12, chỉ thư viện chuẩn, cho `tools/filmcheck/` (`people.py` mới, `plancheck.py`, `kit.py`); numpy sẵn có trong `tools/.venv` cho `tools/style-learn/sl/soundcraft.py`.
- POSIX sh cho `bin/studio people` và `demo/build.sh`.

**Primary Dependencies**: không thêm gói mới. Phông Kalam (OFL) đi kèm bộ dựng; ghi vào `CREDITS` gốc.

**Storage**: tệp.
- `my-styles/sketch-explainer/kit/` (trong git): module JS, `catalog.json`, `catalog.html`, phông.
- `people/<slug>/` (trong git): `person.json`, `figure.js`; bảng mẫu `.sheet/` không vào git (có ảnh tham chiếu bên thứ ba).
- `films/<tên>/kit/`, `films/<tên>/people/` (chép, không vào git).

**Testing**:
- `node --test` cho phần thuần của bộ dựng (lịch hành động, máy, kiểm tên, cỡ cảnh): `tests/sketchkit/*.test.mjs`, gọi từ `tests/filmcheck/run.sh`.
- `unittest` cho `people.py`, phần mới của `plancheck.py`, quét GPU, `soundcraft.py`.
- Test trang (Chromium của thư viện) cho trang danh mục và phim thử, bỏ qua khi thiếu `node`/thư viện như các test trang hiện có.

**Target Platform**: Linux và WSL2, Chromium của thư viện; GPU qua `tools/render/chrome-gpu.sh` khi có.

**Project Type**: gói mã cho trang phim + công cụ dòng lệnh của xưởng.

**Performance Goals**: một khung 1080p dựng dưới 40 ms phần mềm; phim 15 phút render GPU khoảng 20 phút như phim Anthropic.

**Constraints**:
- Không sửa `lib/` (hiến pháp VI); một bộ máy dựng hình là trang `render(t)` của thư viện (VII).
- Đường tô chỉ dùng đoạn thẳng và Bézier; không `A`, không `rx`; viền dày của hình tô vẽ bằng đoạn rời (FR-019).
- Bộ dựng và phim mẫu qua `check-names` (FR-023).

**Scale/Scope**: khoảng 1.500–2.000 dòng JS (đã có ~1.300 dòng ở hai phim cũ), ~400 dòng Python, 24+ bối cảnh, 8+ vai chung, 7 người thật chuyển vào thư viện.

## Constitution Check

| Nguyên tắc | Trạng thái |
|---|---|
| I. Spec là nguồn sự thật | ✓ spec có 1 lần làm rõ, ghi trong spec |
| II. Không đoán | ✓ chỗ mơ hồ duy nhất (thư viện người thật) đã hỏi; phần còn lại ghi ở Assumptions |
| III. MVP trước | ✓ US1+US2 (bộ dựng khớp số đo) là MVP; người thật, test GPU, phim mẫu, sửa đo âm thanh đi sau |
| IV. Đo được | ✓ SC-002/003/004 đo bằng công cụ có sẵn (`qc shots`, `learn compare --clip`, đếm bảng cảnh) |
| V. Đơn giản | ✓ dùng lại `kit use`, hợp đồng trang, tầng 1; thư viện người thật là tệp JSON + JS, không dịch vụ |
| VI. Thư viện gốc giữ nguyên | ✓ không đụng `lib/` |
| VII. Một bộ máy dựng hình | ✓ trang `render(t)` của thư viện, ghi bằng `bin/studio render` |
| VIII. Học bằng đo | ✓ mọi số mặc định của bộ dựng lấy từ `EVIDENCE.md`/`shots.json`, kèm dẫn |
| IX. Spec-kit cho phần mềm | ✓ phim mẫu đi luồng làm phim, không có spec riêng |
| Bản quyền | ✓ ảnh tham chiếu người thật không vào git, chỉ ghi nguồn và giấy phép; bộ dựng không có tên người thật |

Không vi phạm. Đánh giá lại sau thiết kế: vẫn đạt (data-model không thêm dịch vụ; contract chỉ thêm lệnh `people` theo mẫu lệnh `lesson`).

## Project Structure

### Documentation (this feature)

```text
specs/028-sketch-kit/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── kit-api.md        # film({scenes}) và tên trong danh mục
│   └── people-cli.md     # sh bin/studio people …
├── checklists/requirements.md
└── tasks.md              # /speckit-tasks
```

### Source Code (repository root)

```text
my-styles/sketch-explainer/
├── STYLE.md              # mục 10 trỏ tới kit/ và demo/
├── kit/
│   ├── film.js           # film({scenes, cues, hero, custom}) → hợp đồng trang; KIT_ERRORS, BUBBLES, PEOPLE
│   ├── core.js           # el, circ, rrect, bumpy, ease, segOutline (an toàn GPU)
│   ├── rig.js            # makeChar/setChar: nét theo khung, không bàn chân, mặt trắng, tư thế, biểu cảm
│   ├── roles.js          # vai chung + biến thể; người dẫn từ channel.json
│   ├── acting.js         # lịch hành động (thuần, có test)
│   ├── camera.js         # máy thẳng, dịch, giữ cuối; đẩy/kéo xen kẽ (thuần, có test)
│   ├── sets/index.js     # 24+ bối cảnh và phần để ghép custom:
│   ├── boards.js         # bảng trắng, bảng đen, TV, giấy tờ, biển, bong bóng, thẻ chương, số lớn
│   ├── catalog.json      # tên dùng được trong bảng cảnh, số mặc định kèm dẫn
│   ├── catalog.html      # trang danh mục (mỗi mục một ô)
│   └── Kalam-Bold.ttf
├── DEMO.md, demo/, demo-checks.json      # US5
people/<slug>/person.json, figure.js       # thư viện người thật (US3)
tools/filmcheck/people.py                  # mới: new/sheet/approve/use/list, dấu băm
tools/filmcheck/plancheck.py, plan.mjs     # thêm KIT_ERRORS, PEOPLE, BUBBLES vào tầng 1
tools/filmcheck/cli.py, bin/studio         # lệnh people
tools/style-learn/sl/soundcraft.py         # chỉ đo trong segments (US6)
tests/sketchkit/*.test.mjs                 # phần thuần của bộ dựng
tests/filmcheck/test_people.py, test_sketch_gpu.py, test_plan_people.py
tests/learn/test_soundcraft.py             # thêm ca segments
```

**Structure Decision**: giữ cấu trúc của specs/022 (bộ dựng nằm trong phong cách, chép vào phim). Thư viện người thật ở gốc dự án vì nó dùng chung cho mọi phong cách 2D sau này và không được nằm trong phong cách (FR-023).

## Complexity Tracking

Không có vi phạm cần biện minh.
