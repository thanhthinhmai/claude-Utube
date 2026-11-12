# Implementation Plan: Học cách quay của kênh tham chiếu

**Branch**: `021-learn-shot-grammar` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/021-learn-shot-grammar/spec.md`

## Summary

Style-learn có thêm bước tách cảnh (`learn shots`) và bước gán nhãn (`learn label`). Mỗi cảnh của video tham chiếu có:
- cỡ cảnh và góc máy, do một lượt `claude -p` (Opus) độc lập gán khi xem bảng ảnh;
- độ nét, đo bằng một module dùng chung `focus.py`;
- bối cảnh, gom theo chữ ký màu.

Từ đó có hồ sơ cách quay (tỉ lệ, trung vị, khoảng giữa các video), ghi vào `EVIDENCE.md`, `STYLE.md` và `shots.json` của phong cách.

`qc shots` dùng **cùng** `focus.py` (luật `blurred`, chặn render) và **cùng** lượt gán nhãn (cảnh báo lệch phân bố, kèm mã cảnh).

Học lại `dusk-hypothetical` bằng `save --update` (giữ nhật ký sửa), rồi làm phim mẫu 15–30 s cho nó, như phong cách của thư viện.

## Technical Context

**Language/Version**: Python 3.12.
- `tools/filmcheck/`: chỉ thư viện chuẩn, như 010–020.
- `tools/style-learn/`: numpy và Pillow trong `tools/.venv`, như hiện nay.
- POSIX sh cho `bin/studio`.

**Primary Dependencies**: không thêm gói mới. Dùng ffmpeg (`scdet`, thu ảnh, xuất điểm ảnh xám) và Claude Code CLI (`claude -p`, như người biên tập của specs/010).

**Storage**: file JSON và JPEG.
- `references/<set>/profile/<vid>/shots.json` và `shot-sheets/` (ngoài git).
- `my-styles/<slug>/shots.json`, `DEMO.md`, `demo/`, `test.jpg` (trong git); `test.mp4` (ngoài git).
- `films/<tên>/.check/labels.json`.

**Testing**:
- `sh tests/filmcheck/run.sh` và `sh tests/learn/run.sh`, với một `claude` giả cho lượt gán nhãn (biến môi trường `STUDIO_LABELER_FAKE`, như các test của người biên tập).
- Đủ các bộ test của xưởng.
- Chạy thật theo [quickstart.md](quickstart.md).

**Target Platform**: Linux/WSL2 (máy phát triển), worker online, phần lõi của app.

**Project Type**: CLI và công cụ của xưởng.

**Performance Goals**:
- `focus.py` ≤ 0,15 s mỗi khung;
- `learn shots` ≤ 2 phút mỗi video 3 phút;
- học lại ≤ 1,5 lần lần trước (SC-003);
- `qc shots` khi dùng lại nhãn không chậm hơn bản 020 quá 30 s với 200 cảnh.

**Constraints**:
- Không sửa `lib/` (hiến pháp VI).
- Không chép khung của video tham chiếu vào phong cách hay vào git (mục Bản quyền).
- Mọi lượt gọi Claude dùng Opus.
- Lượt gán nhãn không thấy kịch bản hay ý định của phim.

**Scale/Scope**: khoảng 660 cảnh mỗi bộ tham chiếu (10 video); phim tới khoảng 300 cảnh.

## Constitution Check

| Nguyên tắc | Đánh giá |
|---|---|
| I. Spec là nguồn sự thật | Đạt. Spec đã làm rõ 5 câu (2026-11-13) |
| II. Không đoán | Đạt. Người dùng đã xác nhận (2026-11-13): "khung bằng chứng giữ cùng phong cách" được hiểu là giữ cùng **bộ tham chiếu** ngoài git, còn phong cách chỉ ghi tham chiếu `bảng#ô` (research R5). Hai ngưỡng `FOCUS_T` và `SET_D` được chốt bằng số đo của video tham chiếu, không đoán |
| III. MVP theo story | Đạt. US1 (học và đo) tự chạy và tự kiểm được trên video thử; US2–US4 lần lượt dựa vào nó |
| IV. Đo được | Đạt. SC-001 (độ nhất quán giữa hai lượt), SC-002 (độ nét), SC-005 (phim thử có nhãn biết trước) đều có số; có xem bằng mắt bảng ảnh và phim mẫu |
| V. Đơn giản | Một module độ nét và một lượt gán nhãn dùng chung cho hai phía. Có một điểm phức tạp, ghi ở Complexity Tracking |
| VI. Thư viện gốc | Đạt. Phim mẫu chép mã từ thư viện vào `demo/`, kèm giấy phép MIT trong `CREDITS` |
| VII. Một bộ máy dựng hình | Đạt. Phim mẫu dựng bằng `bin/studio render` |
| VIII. Học bằng đo | Đạt, và là mục đích chính: cách quay có số đo; mỗi nhãn có bằng chứng `bảng#ô` |
| IX. Không spec cho từng phim | Đạt. Phim mẫu là một phần của phong cách (như thư viện), không có spec riêng |
| Bản quyền | Đạt. Video tham chiếu bị xoá sau khi học; khung tham chiếu không vào git; câu chuyện của phim mẫu là của xưởng |

**Sau Phase 1**: vẫn đạt.

## Project Structure

### Documentation (this feature)

```text
specs/021-learn-shot-grammar/
├── plan.md · research.md (R1–R9) · data-model.md · quickstart.md
├── contracts/cli.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
tools/filmcheck/
├── focus.py            # mới: độ nét theo 12 ô, dùng chung (R1)
├── labeler.py          # mới: lượt claude -p độc lập gán cỡ cảnh và góc máy (R3)
├── shotcheck.py        # sửa: blurred, nhãn, so phân bố (R8)
├── shots.mjs           # sửa: bảng ảnh ghi nhãn; bảng ảnh không viền đỏ cho lượt gán nhãn
├── stylerefs.py        # sửa: đọc my-styles/<slug>/shots.json
└── tiers.py            # sửa: thêm blurred vào danh sách luật cho phép ngoại lệ
tools/style-learn/
├── learn.py            # sửa: lệnh shots, label; save --update
└── sl/
    ├── shots.py        # mới: tách cảnh (scdet), khung giữa cảnh, độ nét, chữ ký màu, gom bối cảnh, bảng ảnh (R2, R4)
    ├── summary.py      # sửa: shot_grammar
    └── save.py         # sửa: --update giữ nhật ký sửa; ghi shots.json; mang theo demo
.claude/skills/style-learn/SKILL.md   # sửa: các bước Shots, Label, Agreement, Phim mẫu
CLAUDE.md                             # sửa: phong cách riêng đọc DEMO.md và demo/ trước phong cách gốc
.gitignore                            # sửa: my-styles/*/test.mp4
my-styles/dusk-hypothetical/          # học lại; thêm shots.json, DEMO.md, demo/, test.jpg
tests/filmcheck/                      # test_focus, test_labeler, thêm ca vào test_shots
tests/learn/                          # test_shots (video thử có cắt biết trước), save --update
```

**Structure Decision**: độ nét và lượt gán nhãn nằm ở `tools/filmcheck` (chỉ thư viện chuẩn), để worker và phần kiểm phim dùng được mà không cần numpy; style-learn import hai module đó. Tách cảnh và gom bối cảnh nằm ở style-learn (numpy).

## Thứ tự làm (gợi ý cho /speckit-tasks)

1. **Nền**: `focus.py`, `labeler.py` (với claude giả), thêm `blurred` vào danh sách luật cho phép ngoại lệ.
2. **US1**: `sl/shots.py`, `learn shots`, `learn label` (cả `--pass 2`, sửa tay), `summary` có `shot_grammar`; test trên video thử.
3. **US2**: `save --update` và `shots.json`; học lại `dusk-hypothetical` thật (fetch, measure, shots, label, agreement, chốt `FOCUS_T` và `SET_D`, viết STYLE và EVIDENCE, save, clean); SC-001 – SC-004.
4. **US3**: `shotcheck` dùng độ nét, nhãn, so phân bố; bảng ảnh có nhãn; SC-005, SC-006.
5. **US4**: phim mẫu cho `dusk-hypothetical` theo luồng làm phim; lưu vào phong cách; SC-008.
6. **Hoàn thiện**: SKILL.md, CLAUDE.md, `.gitignore`, đủ các bộ test, kết quả vào quickstart.

## Complexity Tracking

| Điểm phức tạp | Vì sao cần | Cách đơn giản hơn bị loại vì |
|---|---|---|
| Lượt gán nhãn là một lượt `claude -p` (tốn tiền, có thể hỏng) nằm trong một lệnh kiểm | Người dùng chọn: Claude gán nhãn có bằng chứng, độc lập với người làm phim. Không có công cụ đo tự động nào nhận đúng cỡ cảnh với nhân vật đầu tròn không mũi tai | Chỉ đo tự động: không đạt được độ đúng mà SC-001 và SC-005 đòi. Có cách giới hạn chi phí: nhãn được lưu theo dấu vân tay; hỏng thì có cảnh báo `shot_grammar_unchecked`, không lặng lẽ cho qua |
