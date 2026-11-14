# Implementation Plan: Bộ code mẫu cho phong cách học được (film kit)

**Branch**: `022-style-film-kit` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/022-style-film-kit/spec.md`

## Summary

Phong cách `dusk-hypothetical` có thêm bộ dựng `my-styles/dusk-hypothetical/kit/`: các module ES dùng three.js của thư viện, tách từ khung chứng minh đã đạt sau 9 vòng sửa.
- Nhân vật có khớp, tư thế, biểu cảm, biến thể; đám đông tới hàng nghìn người (InstancedMesh, người xa giảm chi tiết).
- 8 bối cảnh, ánh sáng và hậu kỳ theo số đã đạt, đồ hoạ 2D theo mục 8 của `STYLE.md`, cách đặt máy theo `shots.json`.
- Trang phim chỉ còn bảng cảnh (`SCENES`, mỗi cảnh vài dòng); `kit/film.js` dựng ra `render(t)`, `SHOTS`, `CARDS`, `CUES`, `READY`, `DUR` theo hợp đồng trang của thư viện và specs/020.

Máy chủ trang của thư viện chỉ phục vụ gốc thư viện và thư mục phim (gắn ở `/@film/`), nên trang phim không với tới `my-styles/`. Bộ dựng được **chép** vào `films/<tên>/kit/` bằng lệnh mới `sh bin/studio kit use <tên>` (R1).

Hồ sơ kênh có thêm trường `hero` (trang phục nhân vật chính), đi vào bản chụp `channel.json` của phim để bộ dựng đọc. Sửa thêm hai lỗi của style-learn: `learn save` bỏ tệp làm việc; skill cho phép `STRUCTURE.md`. Cuối cùng làm phim mẫu ≈ 10,5 phút bằng bộ dựng, ghi 60 fps trên GPU, thay phim mẫu 23,6 s.

## Technical Context

**Language/Version**:
- JavaScript (ES modules, chạy trong Chromium của bộ dựng hình) cho bộ dựng.
- Python 3.12, chỉ thư viện chuẩn, cho `tools/filmcheck/` (kênh) và `tools/style-learn/sl/save.py`.
- POSIX sh cho `bin/studio kit` và `demo/build.sh`.

**Primary Dependencies**: không thêm gói mới.
- three.js có sẵn trong `lib/lemo-opuscar/node_modules` (MIT, đã ghi trong `CREDITS`), nạp qua importmap như khung chứng minh.
- `/core/three/post.js` (DOF, bloom), `/core/lib.js` (`mulberry`), `/core/fonts/fonts.css` (IM Fell English cho chữ serif in hoa, OFL) của thư viện: chỉ đọc, không sửa.

**Storage**: tệp.
- `my-styles/dusk-hypothetical/kit/` (trong git): module JS, `catalog.json`, `catalog.html`, `GRADE.md`.
- `films/<tên>/kit/` (bản chép, ngoài git như cả `films/`), có `kit/.from` ghi phong cách và dấu băm.
- `channels/<kênh>/channel.json`: thêm `hero`.
- `my-styles/dusk-hypothetical/demo/` (trong git), `test.jpg`; `test.mp4` ngoài git (đã có trong `.gitignore`).

**Testing**:
- `node --test` cho phần thuần của bộ dựng (bảng cảnh → `SHOTS`/`CARDS`, danh mục khớp module, tư thế), trong `tests/render/run.sh`. Gốc dự án không có `node_modules/three`, và module ES bỏ qua `NODE_PATH`, nên lệnh test chạy với `node --import ./tests/render/three-resolve.mjs` (hook resolve trỏ `three` tới bản của thư viện); module của bộ dựng import `three` bằng tên trần (trình duyệt dùng importmap).
- `sh tests/filmcheck/run.sh`: `hero` của kênh (kiểm, `set`, `attach`), `kit use`.
- `sh tests/learn/run.sh`: `save` bỏ tệp làm việc, giữ `STRUCTURE.md`.
- Trang danh mục chạy qua `qc shots` và `page still` (ảnh thật, xem bằng mắt); đủ các bộ test của xưởng; chạy thật theo [quickstart.md](quickstart.md).

**Target Platform**: Linux/WSL2 có GPU (máy phát triển, Chrome đầy đủ qua `chrome-gpu.sh`); macOS và WSL của app desktop dùng cùng trang.

**Project Type**: thư viện dựng cảnh cho trang phim, cộng sửa nhỏ ở CLI của xưởng.

**Performance Goals**:
- cảnh 1.000 người, 10 s, 60 fps ≤ 3 phút trên GPU (SC-003);
- đổi cảnh sang bối cảnh mới ≤ 1 s lần đầu (bối cảnh được giữ trong bộ nhớ đệm, R4);
- phim 630 s ở 60 fps (37.800 khung) dựng xong trong một buổi trên GPU (khoảng 1 giờ theo số đo specs/019).

**Constraints**:
- Không sửa `lib/` (hiến pháp VI); không thêm bộ máy dựng hình (VII); không ảnh AI, không mô hình 3D tải về.
- `render(t)` phải tất định: cùng `t` ra cùng khung, gọi theo thứ tự bất kỳ (bộ ghi chia đoạn, nhiều worker).
- Không chép nhân vật chính, câu chữ, tên, giọng, nhạc hay thumbnail của kênh tham chiếu; `check-names` đạt trên mọi tệp chữ.
- Dựng bằng phần mềm thì dừng và hỏi người dùng.

**Scale/Scope**: khoảng 220 cảnh, ≥ 18 bối cảnh dùng trong một phim, tới vài nghìn người mỗi cảnh; bộ dựng khoảng 2.500–3.500 dòng JS.

## Constitution Check

| Nguyên tắc | Đánh giá |
|---|---|
| I. Spec là nguồn sự thật | Đạt. Spec đã làm rõ 2 câu (2026-11-13); spec không nêu công nghệ |
| II. Không đoán | Đạt. Không còn `NEEDS CLARIFICATION`. Số hậu kỳ lấy từ khung chứng minh đã đạt, không đặt mới. Ngưỡng khác áo nhân vật chính (ΔE ≥ 25, R6) không có số đo; người dùng duyệt ngày 2026-11-14 |
| III. MVP theo story | Đạt. US1 (bộ dựng + trang danh mục) tự kiểm được bằng `qc shots` và so màu; US3 độc lập; US2 và US4 là cùng một lần chạy (FR-011) |
| IV. Đo được | Đạt. SC-001–SC-007 đều có số; có test tự động cho phần thuần; xem bằng mắt bảng ảnh danh mục và phim mẫu |
| V. Đơn giản | Một thư mục module, không bước build, không framework. Hai điểm phức tạp ghi ở Complexity Tracking |
| VI. Thư viện gốc | Đạt. Chỉ đọc `/core/…` và `node_modules` của thư viện; bộ dựng nằm trong `my-styles/` |
| VII. Một bộ máy dựng hình | Đạt. three.js trong trang, ghi bằng `bin/studio render` (phim) và bộ ghi của thư viện (phim mẫu chạy trên máy sạch), cùng một bộ máy |
| VIII. Học bằng đo | Đạt. Mỗi số mặc định của hậu kỳ ghi kèm số đo đối chiếu trong `kit/GRADE.md` |
| IX. Không spec cho từng phim | Đạt. Phim mẫu là một phần của phong cách; bộ dựng là công cụ của xưởng |
| Bản quyền | Đạt. Nhân vật chính lấy từ hồ sơ kênh và phải khác áo nhân vật của kênh tham chiếu (R6); phông OFL đã ghi |

**Sau Phase 1**: vẫn đạt.

## Project Structure

### Documentation (this feature)

```text
specs/022-style-film-kit/
├── plan.md · research.md (R1–R9) · data-model.md · quickstart.md
├── contracts/kit-api.md · contracts/cli.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
my-styles/dusk-hypothetical/kit/        # mới (R2)
├── stage.js        # renderer, bản chép sang canvas 2D, sương, hậu kỳ mặc định (R5)
├── figure.js       # nhân vật có khớp; tư thế, biểu cảm, biến thể, đồ cầm tay (R3)
├── crowd.js        # đám đông: người gần đủ chi tiết, người vừa instanced, người xa chấm (R4)
├── sets/           # classroom, lockers, gym, street, bedroom, cafeteria, stadium, void + parts.js (sàn, tường, lưới, đèn)
├── camera.js       # cách đặt máy theo nhãn của shots.json, lớp trước/sau, vật che tiền cảnh
├── graphics.js     # đồ hoạ 2D trên canvas: pill, menu, sơ đồ, bong bóng, thẻ số liệu, thẻ tên, chương, thẻ cuối
├── film.js         # bảng cảnh → render(t), SHOTS, CARDS, CUES, DUR, READY, CLEAN (contracts/kit-api.md)
├── catalog.json    # danh mục tên: bối cảnh, tư thế, biểu cảm, đồ hoạ, cách đặt máy, đồ cầm tay
├── catalog.html    # trang danh mục (mỗi mục một cảnh 1 s), là một trang phim hợp lệ
├── GRADE.md        # số hậu kỳ mặc định và số đo đối chiếu (FR-005)
└── test/           # node --test cho phần thuần
my-styles/dusk-hypothetical/            # DEMO.md, demo/ (bảng cảnh dùng kit), demo-checks.json, test.jpg làm lại; STYLE.md trỏ tới kit/
bin/studio                              # sửa: chuyển lệnh kit sang tools/filmcheck/cli.py
tools/filmcheck/kit.py                  # mới: kit use (R1), ΔE Lab cho áo nhân vật chính (R6)
tools/filmcheck/channels.py, cli.py     # sửa: trường hero, kiểm, set, attach (R6); lệnh kit
tools/style-learn/sl/save.py            # sửa: chỉ chép tệp của phong cách (R8)
.claude/skills/style-learn/SKILL.md     # sửa: STRUCTURE.md và mục 11 (R8)
CLAUDE.md                               # sửa: luồng làm phim dùng kit khi phong cách có kit/ (FR-009)
channels/dusk-hypothetical/channel.json # thêm hero mặc định
tests/filmcheck/, tests/learn/, tests/render/run.sh   # test mới
```

**Structure Decision**: bộ dựng thuộc riêng phong cách (giả định của spec), nằm cạnh `STYLE.md` để `learn save --update` mang theo như `demo/`. Phần thuần (bảng cảnh, thời gian, danh mục) tách khỏi phần three.js để `node --test` chạy được không cần trình duyệt.

## Thứ tự làm (gợi ý cho /speckit-tasks)

1. **Nền**: `kit use`, `stage.js` tách từ khung chứng minh, `film.js` (phần thuần + test), `catalog.json`.
2. **US1**: `figure.js` (khớp, tư thế, biểu cảm, biến thể), `crowd.js`, 8 bối cảnh, `camera.js`, `graphics.js`, `catalog.html`; chụp danh mục, `qc shots`, so màu; dựng lại khung chứng minh bằng kit (SC-002); cảnh 1.000 người (SC-003).
3. **US3** (song song được): `save` bỏ tệp làm việc; SKILL.md; test.
4. **FR-015**: `hero` trong kênh, `attach`, bộ dựng đọc `channel.json`.
5. **US2 + US4**: phim mẫu ≈ 10,5 phút theo luồng làm phim (kênh `dusk-hypothetical`), qua các tầng kiểm, 60 fps; lưu vào `demo/`, `DEMO.md`, `demo-checks.json`; SC-004, SC-005.
6. **Hoàn thiện**: CLAUDE.md, STYLE.md trỏ tới kit, `check-names` (SC-007), đủ các bộ test, kết quả vào quickstart.

## Complexity Tracking

| Điểm phức tạp | Vì sao cần | Cách đơn giản hơn bị loại vì |
|---|---|---|
| Bộ dựng được chép vào mỗi phim (hai bản cùng mã) | Máy chủ trang của thư viện chỉ phục vụ gốc thư viện và thư mục phim; không sửa được thư viện (VI). Bản chép còn giữ phim dựng lại đúng như lúc làm khi kit đổi sau này | Đường dẫn tới `my-styles/` từ trang: bị máy chủ chặn (403). Liên kết mềm: không theo được trên Windows và trong container của worker. `kit/.from` ghi dấu băm để biết bản chép cũ |
| Đám đông ba mức chi tiết | SC-003 đòi 1.000 người, 10 s, 60 fps ≤ 3 phút; người đủ khớp mỗi người khoảng 30 mesh, 1.000 người là 30.000 lần vẽ | Một mức instanced cho mọi người: người gần trông như khối, trái mục 4 của `STYLE.md`. Chỉ người đủ chi tiết: quá chậm |
