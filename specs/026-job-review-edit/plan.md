# Implementation Plan: Điểm duyệt và chỉnh sửa trên trang việc làm phim

**Branch**: `026-job-review-edit` | **Date**: 2026-11-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/026-job-review-edit/spec.md`

**Mức**: Đầy đủ. Quyết định ở [research.md](research.md), dữ liệu ở [data-model.md](data-model.md), hợp đồng ở [contracts/](contracts/), kiểm chứng ở [quickstart.md](quickstart.md).

## Summary

Ba lớp, mỗi lớp dùng lại cái đã có:

1. **Lõi trong `tools/filmcheck/`** (chỉ Python chuẩn, chạy được không cần giao diện):
   - `points.py`: năm điểm duyệt, phần tệp của mỗi điểm, dấu nội dung, lần duyệt lưu trong `checks.json` → `reviews`, và cổng.
   - `steps.py`: đồ thị mười bước và trạng thái từng bước tính từ tệp của phim ("Must run again").
   - `edit.py`: mọi thao tác sửa (đoạn kịch bản, `say`, làm lại một dòng, giọng và tốc độ, một cảnh, ngoại lệ, chấp nhận phong cách, nhạc và mức tiếng, gói đăng). Mỗi thao tác kiểm `--base`, khoá bận, kiểm hợp lệ, ghi, chạy lệnh của chính bước đó, trả JSON.
   - Lệnh mới: `sh bin/studio point …` và `sh bin/studio edit …`. `voice make` và `render-gate` gọi cổng của `points.py`.
2. **Xưởng (`tools/studio/`)**:
   - Năm loại duyệt mới trong `reviews.py`; duyệt thì gọi `points.approve` trên nội dung hiện tại.
   - API `GET /jobs/{id}/steps`, `POST /jobs/{id}/actions`, `GET /jobs/{id}/actions/{aid}`, `PUT /jobs/{id}/points`.
   - Thao tác chạy ở **người chạy thao tác**: local và app là luồng nền của máy chủ web, gọi `sh bin/studio edit …`. Online thì worker chạy cùng lệnh trong container của việc, không có proxy Claude.
3. **Trang việc (`web/app.js`)**: thanh tiến trình mười bước, khung theo bước (Script, Voice, Shots, Mix, Publish) theo trang mẫu, cột "If you change this", cập nhật tại chỗ bằng sự kiện `job.updated`. Khu "Done so far" của 025 trở thành phần chỉ đọc của các khung này.

Bộ dựng `dusk-hypothetical` thêm hai thứ: bảng cảnh đọc từ `scenes.json`, và `mix.py` đọc `mix.json`. Hai thay đổi này nằm ở `my-styles/`, không đụng `lib/`.

Hướng dẫn cho agent ở `CLAUDE.md` (luồng chat) và `tools/runner/agent.py` (online) thêm các điểm dừng.

## Technical Context

**Language/Version**: Python 3.12 (FastAPI hiện có, filmcheck chỉ thư viện chuẩn), Node 20 (kiểm bảng cảnh bằng `plan.js` của bộ dựng), JavaScript thuần có `@ts-check` (`web/app.js`), CSS

**Primary Dependencies**: không thêm gói. TTS `core/tts/tts.py` và ASR `asr_check.py` của thư viện gọi như hiện nay. Trộn tiếng bằng `kit/sound/mix.py` (numpy, scipy của venv thư viện).

**Storage**:
- tệp trong thư mục phim: `checks.json` → `reviews`, `scenes.json`, `mix.json`, `.check/busy.json`, `.check/edits.jsonl`;
- hồ sơ kênh thêm trường `reviews`;
- sổ việc thêm tài liệu `action` (`store.doc_*` như review).

**Testing**:
- `unittest` trong `tests/filmcheck` (points, steps, edit với TTS và Chrome giả qua biến môi trường như `STUDIO_TTS_DRY`);
- `tests/ui` (API, quyền, trang bằng Playwright);
- `tests/online` (worker chạy thao tác, việc chờ không giữ container);
- `node --test` cho `scenes.json` của bộ dựng.

**Target Platform**: local (`127.0.0.1`), online (web + worker + container việc), app desktop (host; client đi qua host)

**Project Type**: web app nội bộ và CLI

**Performance Goals**:
- lưu một đoạn và nhận điểm < 30 s (SC-001), vì máy chấm theo luật chạy dưới 1 s;
- đổi một cảnh và thấy ảnh mới < 2 phút (`qc plan` vài giây + `qc shots --only <cảnh>`);
- `GET /steps` < 300 ms với phim 175 cảnh (dấu nội dung theo phần, có bộ nhớ đệm theo mtime).

**Constraints**:
- trang không ghi tệp (FR-005): chỉ API → thao tác → `sh bin/studio edit`;
- không sửa `lib/`;
- online: thao tác không dùng proxy Claude, và việc chờ không giữ container (FR-023).

**Scale/Scope**: phim tới khoảng 10 phút (339 dòng, 175 cảnh); vài người cùng xem một việc

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Kiểm | Kết quả |
|---|---|---|
| I. Spec là nguồn sự thật | Spec đã duyệt; plan không thêm hành vi ngoài spec | Đạt |
| II. Không đoán | Câu hỏi duy nhất (FR-002) đã được người dùng trả lời; ba mặc định ghi ở Clarifications | Đạt |
| III. MVP theo story | US1 (Script) tự chạy được: điểm duyệt, sửa đoạn, cổng `voice make`, làm tiếp | Đạt |
| IV. Đo được | SC có số; test tự động cho cổng, kiểm hợp lệ, xung đột; thử thật một phim | Đạt |
| V. Đơn giản | Một lệnh `edit` cho mọi thao tác; dùng lại review, tiers, kit check, store. Người chạy thao tác online là phần phức tạp duy nhất, xem Complexity Tracking | Đạt, có giải thích |
| VI. Thư viện giữ nguyên | Gọi `tts.py` và `asr_check.py` với tệp tạm; không sửa `lib/` | Đạt |
| VII. Một bộ máy dựng hình | Ảnh cảnh vẫn do `qc shots` (Chrome + trang phim) vẽ | Đạt |
| IX. Spec-kit cho phần mềm | Không tạo spec cho phim | Đạt |
| Bản quyền | Không thêm tài sản bên thứ ba; nhạc vẫn soạn bằng nhạc cụ thư viện | Đạt |
| Phần mềm hệ thống | Không cài gì | Đạt |

Kiểm lại sau Phase 1: đạt, không đổi.

## Project Structure

### Documentation (this feature)

```text
specs/026-job-review-edit/
├── spec.md
├── plan.md              # tệp này
├── research.md          # R1–R13
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md           # point, edit, channel set reviews, review request --kind <điểm>
│   ├── api.md           # /steps, /actions, /points, decision
│   └── film-files.md    # checks.json reviews, scenes.json, mix.json, busy.json, edits.jsonl
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
bin/studio                          # point | edit → cmd_filmcheck
tools/filmcheck/
├── points.py        # MỚI: điểm duyệt, dấu theo phần, lần duyệt, cổng
├── steps.py         # MỚI: đồ thị bước, trạng thái, "if you change this"
├── edit.py          # MỚI: thao tác sửa, base, khoá bận, nhật ký sửa
├── scenecheck.mjs   # MỚI: chạy plan.js check() của bộ dựng trong phim với scenes.json
├── cli.py           # point/edit; voice make và render-gate gọi points.gate
├── channels.py      # trường reviews (mặc định script, shots); attach chép vào checks.json
├── tiers.py         # SKIP_NAMES thêm mix.json (đổi trộn không đổi dấu hình)
├── shotcheck.py     # --only <cảnh,…> vẽ lại ảnh vài cảnh (xem trước), không ghi kết quả tầng
├── voicecheck.py    # so lời với kịch bản ở tầng 0 (FR-007)
└── publish.py       # pack.json "chosen"
tools/render/lib.mjs                # cùng danh sách bỏ qua (mix.json)
tools/studio/studio/
├── reviews.py       # KINDS script|voice|shots|mix|publish; decide approve → points.approve
├── actions.py       # MỚI: tài liệu action, hàng đợi, người chạy local
├── server.py        # /steps, /actions, /points
├── jobs.py          # tạo việc phim kèm points (job start --points)
└── web/app.js, style.css           # thanh tiến trình, khung sửa, If you change this
tools/studio/studio_cli.py          # review request --kind <điểm> --film; job start --points
tools/runner/worker.py              # chạy action của việc online trong container (không proxy)
tools/runner/agent.py               # hướng dẫn điểm dừng cho agent online
my-styles/dusk-hypothetical/kit/
├── film.js          # scenes mặc định './scenes.json' ({custom:[…], scenes:[…]})
└── sound/mix.py     # đọc mix.json (nhạc theo seed hoặc none, mức trong dải template)
CLAUDE.md                           # luồng làm phim: điểm duyệt, point approve trong chat
tests/filmcheck/test_points.py, test_steps.py, test_edit.py
tests/ui/test_review_points.py (+ Playwright)
tests/online/test_actions.py
```

**Structure Decision**: giữ cấu trúc hiện có. Logic phim nằm trong `filmcheck` để dùng được từ chat, từ app và online như nhau. Xưởng chỉ xếp hàng thao tác, kiểm quyền và hiển thị.

## Complexity Tracking

| Phần phức tạp | Vì sao cần | Cách đơn giản hơn bị loại vì |
|---|---|---|
| Người chạy thao tác online qua worker (tài liệu `action`, chạy trong container của việc) | Online, máy chủ web không có venv thư viện, TTS hay Chrome; thư mục phim của khách nằm ở vùng dữ liệu của worker | Chạy thẳng trong web: thiếu công cụ và phá cách ly. Nhờ agent sửa: tốn lượt Claude và phải giữ container trong lúc chờ (trái FR-023) |
| Dấu nội dung theo phần (script, voice, picture, mix, publish) thay vì một dấu cả phim | Đổi bản trộn không được làm mất duyệt Shots; đổi gói đăng không được làm mất duyệt hình (FR-015) | Một dấu cả phim: mọi sửa nhỏ đều mở lại mọi điểm |
