# Implementation Plan: Template từ cách làm của kênh mẫu

**Branch**: `023-style-craft-template` | **Date**: 2026-11-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/023-style-craft-template/spec.md`

## Summary

Phim thử của 022 khớp các số trung bình nhưng đứng yên và sai tay nghề. Tính năng này làm sáu việc:

1. **Phần hình** (US1, không cần video): đo bố cục, độ sâu, ánh sáng theo cỡ cảnh từ dữ liệu còn giữ (`shots.json`, `shot-sheets`). Rà `STYLE.md` bằng nhãn `[bằng chứng: …]` hoặc `[xưởng]`.
2. **Phần theo thời gian** (US2): `learn refetch` tải lại đủ 10 video, ghép đúng `vNN` cũ nên nhãn và bằng chứng cũ vẫn dùng được.
   - Module mới `sl/craft.py` đo máy (dời, phóng), cử động bên trong sau khi bù máy, và loại chuyển cảnh.
   - `learn sound` đo nhịp đọc, nhạc, tiếng động.
   - Claude chia nhịp phim và đặt tên động tác từ dải khung.
   - Xong thì xoá video.
3. **Template**: viết `TEMPLATE.md` (15 thành phần, 9 công thức nhịp) và `template.json` (khoảng số cho máy đọc). `learn template-check` kiểm.
4. **Bộ dựng v2** (US3): theo template, gồm
   - mặt và thân mới;
   - diễn xuất `act`, `talk`, `path`, chớp mắt, thở;
   - máy `move`, bố cục `frame`, độ sâu theo cỡ cảnh, ánh sáng ấm xiên;
   - đạo cụ, thẻ có hình ẩn dụ, thẻ cuối có dàn nhân vật 3D;
   - chuyển cảnh `trans`;
   - âm thanh: `kit/sound/` soạn nhạc bằng sampler của thư viện, tiếng động, nhịp đọc.

   Mỗi thành phần chứng minh bằng `learn pairs`. Người dùng duyệt theo 4 đợt, ghi ở `kit/REVIEW.md`.
5. **Tầng kiểm** (US4):
   - `qc shots` có luật `still_person` (trước khi dựng, đo trên 4 khung mỗi cảnh) và `style_depth`;
   - `qc` có `style_still_ratio`, `style_motion720`, `style_person_motion`, `style_transitions`;
   - `qc voice` có `mispronounced`; `voice make` dùng trường `say` mà không sửa thư viện.
6. **Phim thử** (US5): dựng lại `hundred-words`, kèm bảng so ba cột và bảng số trước/sau.

## Technical Context

**Language/Version**:
- Python 3.12:
  - `tools/style-learn/sl/` (numpy, Pillow có sẵn trong `tools/.venv`);
  - `tools/filmcheck/` (thư viện chuẩn; riêng phép đo chuyển động gọi venv);
  - `kit/sound/` (numpy, soundfile, soxr của thư viện, chạy bằng Python của thư viện như `mix.py`).
- JavaScript ES modules (three.js của thư viện) cho bộ dựng.
- POSIX sh cho `bin/studio`.

**Primary Dependencies**: không thêm gói.
- `faster-whisper` và `yt-dlp` (đã có, `deps learn --extra`); ffmpeg.
- `core/audio/sampler.py`, `sfx.py` của thư viện, cùng các bộ nhạc cụ tải bằng `deps music`. Chỉ đọc. Bộ nào dùng thì ghi giấy phép vào `CREDITS`.

**Storage**: tệp (data-model.md).
- Ngoài git: `references/<set>/profile/<v>/{craft,sound}.json`, `strips/`, `evidence/`, `beats.json`, `craft-summary.json`, `pairs/`.
- Trong git: `my-styles/dusk-hypothetical/{TEMPLATE.md, template.json, STYLE.md, EVIDENCE.md, kit/…, kit/REVIEW.md}`.

**Testing**:
- `tests/learn`: video thử tổng hợp (numpy và ffmpeg) có máy, cử động, chuyển cảnh biết trước cho SC-003; `sound` trên âm thanh tổng hợp; `beats --check`; `template-check` trên mẫu đúng và mẫu thiếu; `pairs` đếm cặp; `refetch` ghép theo độ dài (giả lập, không tải).
- `tests/filmcheck`: `still_person` trên các khung thử (đứng yên, có cử động, máy trôi mà người đứng yên); `style_*` mới; `mispronounced`; `.say.json`.
- `tests/render` (`node --test`): `act`, `move`, `trans`, `frame` ra đúng giá trị theo `t`; tất định khi gọi đảo thứ tự; `CAST`, `MOVES`; bảng cảnh 022 cũ vẫn chạy.
- Chạy thật theo [quickstart.md](quickstart.md), xem bằng mắt bảng so và phim.

**Target Platform**: Linux/WSL2 có GPU (máy phát triển); lệnh `learn` và `qc` chạy được cả trong lõi của app desktop.

**Project Type**: công cụ học và kiểm của xưởng, cộng thư viện dựng cảnh của phong cách.

**Performance Goals**:
- `learn craft` cho 10 video (≈ 6.650 s) ≤ 60 phút trên CPU (12 khung/s, 320×180);
- `qc shots` thêm ≤ 30 s cho phim 1 phút;
- tầng 4 thêm ≤ 2 phút cho phim 1 phút;
- phim 1 phút ở 60 fps dựng ≤ 10 phút trên GPU.

**Constraints**:
- Không sửa `lib/` (VI); không thêm bộ máy dựng hình (VII); không gói mới.
- Video và âm thanh mẫu bị xoá khi học xong; bảng so và khung mẫu không vào git và không gửi đi.
- `render(t)` tất định.
- Không chép câu chuyện, câu thoại, nhân vật, giọng, nhạc, thumbnail, bố cục từng khung của kênh mẫu; `check-names` đạt.
- Mọi lượt Claude dùng Opus; lượt tốn tiền phải hỏi trước. Kế hoạch này chỉ thêm việc đọc trong phiên; lượt gán nhãn tầng 2 vẫn như cũ.

**Scale/Scope**:
- 10 video, 2.192 cảnh, khoảng 80 dải khung;
- bộ dựng thêm khoảng 1.500–2.000 dòng JS và khoảng 400 dòng Python âm thanh;
- công cụ học thêm khoảng 900 dòng; tầng kiểm thêm khoảng 300 dòng.

## Constitution Check

| Nguyên tắc | Đánh giá |
|---|---|
| I. Spec là nguồn sự thật | Đạt. Spec đã làm rõ 5 câu (2026-11-14) và không nêu công nghệ |
| II. Không đoán | Đạt. Mọi ngưỡng lấy từ số đo của kênh mẫu (`template.json → source`). Ngưỡng của chính phép đo (3σ nhiễu, ΔE ≤ 12 khi ghép video) được kiểm bằng video thử và ghi trong research. Không thêm tính năng ngoài spec |
| III. MVP theo story | Đạt. US1 tự làm và tự kiểm được không cần video. US2 có test riêng trên video thử. US3, US4, US5 nối tiếp theo phụ thuộc đã ghi trong spec |
| IV. Đo được | Đạt. SC-001–SC-007 có số; test tự động cho phép đo (SC-003), luật kiểm và bộ dựng; xem bằng mắt bảng so (4 đợt) và phim |
| V. Đơn giản | Một module đo dùng chung cho học và kiểm; không framework. Ba điểm phức tạp ghi ở Complexity Tracking |
| VI. Thư viện gốc | Đạt. `tts.py` không có `say`, nên xưởng viết tệp đầu vào riêng (R7) thay vì sửa thư viện; sampler và `sfx` chỉ được gọi |
| VII. Một bộ máy dựng hình | Đạt. three.js trong trang; `page clip` dùng bộ ghi của specs/019 |
| VIII. Học bằng đo | Đạt, và đây là mục tiêu của tính năng. Mọi luật có bằng chứng hoặc nhãn `[xưởng]`; mọi số của template có nguồn |
| IX. Không spec cho từng phim | Đạt. `hundred-words` và `kit-proof` là phim thử, đi theo luồng làm phim |
| Bản quyền | Đạt có điều kiện. Video tải lại chỉ để học và bị xoá ngay sau `learn craft`/`sound`. Giữ khoảng 80 dải × 8 khung làm bằng chứng, nhiều hơn "vài khung" (xem Complexity Tracking). Đoạn so chuyển động dựng từ khung đã giữ, không cắt video. Nhạc tự soạn |
| Phần mềm hệ thống | Đạt. Không cài gì; thiếu thì báo (`deps learn`, `deps music`) |

**Sau Phase 1**: vẫn đạt. Điều kiện bản quyền cần người dùng biết: số khung giữ lại.

## Project Structure

### Documentation (this feature)

```text
specs/023-style-craft-template/
├── spec.md · plan.md · research.md (R1–R13) · data-model.md · quickstart.md
├── contracts/cli.md · contracts/template-format.md · contracts/kit-api-v2.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
tools/style-learn/sl/craft.py        # mới: khớp khối, mô hình máy, cử động dư, chuyển cảnh, dải khung (R2, R3)
tools/style-learn/sl/soundcraft.py   # mới: nhịp đọc, nhạc, tiếng động (R5, R6)
tools/style-learn/sl/template.py     # mới: craft-summary, beats --check, template-check, nhãn STYLE.md (R8, R10)
tools/style-learn/sl/pairs.py        # mới: bảng so ảnh và mp4 hai nửa (R9)
tools/style-learn/sl/fetch.py        # sửa: refetch, ghi url (R1)
tools/style-learn/learn.py           # sửa: lệnh refetch, craft, sound, beats, craft-summary, evidence, template-check, pairs
tools/filmcheck/motioncheck.py       # mới: gọi craft.py qua tools/.venv cho still_person, style_* (R11)
tools/filmcheck/shotcheck.py, shots.mjs   # sửa: 4 khung/cảnh, still_person, style_depth
tools/filmcheck/qc.py, stylerefs.py       # sửa: style_still_ratio, style_motion720, style_person_motion, style_transitions; đọc template.json
tools/filmcheck/voicecheck.py             # sửa: mispronounced
tools/filmcheck/cli.py, bin/studio        # sửa: voice make, page clip
my-styles/dusk-hypothetical/
├── TEMPLATE.md · template.json      # mới
├── STYLE.md · EVIDENCE.md           # sửa: nhãn luật, nhật ký sửa
└── kit/
    ├── figure.js       # mặt, thân, act/talk/blink/thở, path
    ├── camera.js       # move, frame, độ sâu theo cỡ cảnh
    ├── stage.js        # ánh sáng ấm xiên; streak/dip/fade
    ├── graphics.js     # icon ẩn dụ, thẻ cuối có dàn nhân vật 3D
    ├── plan.js         # kiểm trường mới; CAST, MOVES
    ├── film.js         # nối các phần trên
    ├── sets/*.js       # đạo cụ kể chuyện
    ├── catalog.json    # acts, moves, icons, trans
    ├── sound/          # timing.py, score.py, sfx.py, mix.py
    ├── REVIEW.md       # sổ duyệt 4 đợt
    └── test/           # thêm test v2
.claude/skills/style-learn/SKILL.md  # sửa: bước refetch/craft/sound/beats, viết TEMPLATE.md, chứng minh bằng đoạn video (FR-007)
CLAUDE.md                            # sửa: luồng làm phim đọc TEMPLATE.md; voice make; luật mới
CREDITS                              # thêm bộ nhạc cụ được dùng
tests/learn/, tests/filmcheck/, tests/render/   # test mới
```

**Structure Decision**:
- Phép đo nằm ở `tools/style-learn/sl/craft.py`, vì bước học cần numpy. Tầng kiểm gọi đúng module đó qua venv, để học và kiểm dùng chung một cách đo.
- Template và bộ dựng nằm trong phong cách, để `learn save --update` mang theo. Cần thêm `TEMPLATE.md` và `template.json` vào danh sách tệp phong cách của `save.py`.

## Thứ tự làm (gợi ý cho /speckit-tasks)

1. **Nền**: `craft.py` cùng video thử tổng hợp và test SC-003; `template.py` (`template-check`, nhãn `STYLE.md`); `save.py` nhận tệp mới.
2. **US1**: `craft-summary` phần hình; rà `STYLE.md`; viết mục 1–10 của `TEMPLATE.md`, bằng chứng từ `shot-sheets`. Mốc kiểm: `template-check` đạt cho mục 1–10, SC-001.
3. **US2**:
   - `refetch` (hỏi người dùng danh sách URL nếu ghép không một-một);
   - `transcribe`, `craft`, `sound`;
   - Claude ghi `beats.json`, bảng diễn xuất, `evidence`;
   - `craft-summary`, rồi `clean`;
   - mục 11–15 và công thức nhịp; `template.json`.

   Mốc kiểm: SC-002, SC-007.
4. **US4 phần đo trên phim cũ** (trước khi đổi kit trong phim): `motioncheck.py`, `still_person`, `style_*`, chạy trên `hundred-words` cũ, chụp khung "cũ". Mốc kiểm: SC-005 nửa đầu.
5. **US3**: bộ dựng v2 theo 4 đợt; mỗi đợt `kit-proof`, `page clip`, `pairs`, duyệt, `REVIEW.md`. Đợt 4 gồm `kit/sound/`, `voice make`, `mispronounced`. Mốc kiểm: SC-004.
6. **US5**: dựng lại `hundred-words`, bảng ba cột, `before-after.json`. Mốc kiểm: SC-005 nửa sau, SC-006.
7. **Hoàn thiện**: SKILL.md (FR-007), CLAUDE.md, CREDITS, `check-names`, đủ các bộ test, kết quả vào quickstart.

Bước 4 đứng trước bước 5 vì phải đo phim cũ khi nó còn dùng kit cũ. Đổi lại, tầng kiểm có thể làm sớm vì chỉ cần `template.json`.

## Complexity Tracking

| Điểm phức tạp | Vì sao cần | Cách đơn giản hơn bị loại vì |
|---|---|---|
| Giữ khoảng 80 dải × 8 khung (320 px) của kênh mẫu làm bằng chứng, ngoài git | Diễn xuất và chuyển động chỉ thấy qua nhiều khung liên tiếp. Video bị xoá trước khi làm bộ dựng, nhưng bảng so của US3 vẫn cần khung mẫu | Giữ video tới khi xong US3: trái mục Bản quyền (xoá khi học xong). Chỉ giữ một khung mỗi cảnh: không thấy được chuyển động, lặp lại lỗi của 022 |
| Tầng kiểm gọi Python của venv (numpy) | Đo cử động sau khi bù máy cần khớp khối trên hàng nghìn khung; Python thuần quá chậm | Viết lại phép đo bằng JS trong trang: hai bản cài lệch nhau. Chỉ dùng hiệu khung: báo nhầm khi máy trôi |
| Hai phần học "trong phiên" (chia nhịp, đặt tên động tác) do Claude đọc thay vì tự động | Không có mô hình tư thế; tự động hoá cần gói nặng hoặc lượt Claude riêng tốn tiền | Lượt Claude độc lập: tốn tiền mà tầng kiểm không dùng. Bỏ hẳn: template thiếu tên động tác, bộ dựng không biết diễn gì |
