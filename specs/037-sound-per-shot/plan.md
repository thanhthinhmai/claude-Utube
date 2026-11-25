# Implementation Plan: Âm thanh theo shot cho phim After Effects

**Branch**: `037-sound-per-shot` | **Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/037-sound-per-shot/spec.md`

## Summary

Tiếng động của phim AE thôi viết tay trong `mix.py` của từng phim. Bước Sound lập `films/<phim>/sound/plan.json`: mỗi tiếng (cue) thuộc một shot, **neo** vào một chuyển động có tên (`animatic/keys.json` của 035), một từ của lời đọc, một tỉ lệ trong shot hoặc cả shot; mốc tuyệt đối luôn tính lại từ `timing.json` (035), nên đổi thời lượng ở Animatic không phải sửa mốc nào. Claude (Opus 5.5) viết các cue bằng lệnh `sound cue add` (hành động + từ khoá tìm); xưởng tìm tiếng trong **kho trên máy**: mục lục SQLite FTS5 dựng chỉ từ tên tệp và metadata của các gói Sonniss GDC (không AI lên âm thanh Sonniss, theo giấy phép), lấp chỗ thiếu bằng Freesound **chỉ CC0** qua proxy (khoá giữ ở proxy như ElevenLabs). Proxy cũng giữ phạm vi: việc của khách online chỉ thấy tiếng CC0. `soundmix.py` trộn giọng + nhạc của phim + các tiếng, có luật tắt ở điểm cắt và khoảnh khắc lặng, giới hạn bằng soft-clip không trạng thái để một sửa chỉ đổi đúng đoạn của nó. Trang Sound (điểm `mix`) cho nghe từng shot, đổi/dời/xoá/thêm tiếng, ghi chú cho Claude. Học tiếng (`learn sfx`) tách lớp bằng Demucs htdemucs, tìm sự kiện ở lớp tiếng động và lớp giọng ngoài lời, chỉ tin khi AST và CLAP đồng ý, rồi ghi luật tiếng (hành động → loại tiếng, mật độ, độ lớn, lặng, luật cắt) vào phong cách.

## Technical Context

**Language/Version**: Python 3.11+ (filmcheck, studio, runner, style-learn); JavaScript trình duyệt (web/app.js, không framework). ExtendScript: không sửa, chỉ đọc `keys.json` do 035 ghi.

**Primary Dependencies**: thư viện chuẩn (`sqlite3` FTS5, `wave`/chunk RIFF, `urllib`) cho kho và Freesound; numpy + soundfile (venv của thư viện, như `mix.py`) cho trộn; tầng mới `deps sound` trong `tools/.venv`: torch CPU, demucs, transformers (chỉ học tiếng); ffmpeg (đổi định dạng, ghép tiếng, sẵn có); FastAPI (app, sẵn có)

**Storage**: kho `$STUDIO_DATA/sound/` (`roots.json`, `library.db`, `freesound/`); phim `films/<phim>/sound/` (`plan.json`, `notes.json`, `cache/`, `stems/`), `out/mix.wav`, khối trong `CREDITS`; học `references/<set>/profile/<v>/sfx.json`, `references/<set>/stems/`; phong cách `kit/template.json → sound.sfx`

**Testing**: unittest (`sh tests/run.sh`, `tests/filmcheck`, `tests/learn`, `tests/ui`, `tests/online`, `tests/ae`), test trình duyệt `tests/ui/browser_sound.cjs`; Freesound bằng máy chủ giả; học tiếng bằng âm thanh tổng hợp + bộ phân loại giả; một lượt thật trên `ae-sleepless-test` và `references/voice-check` theo `quickstart.md`

**Target Platform**: WSL2/Linux và macOS (phần lõi); AE trên máy người dùng (chỉ qua 035)

**Project Type**: công cụ CLI + app web cục bộ + worker/proxy (mở rộng xưởng hiện có)

**Performance Goals**: mục lục 10.000 tệp ≤ 15 phút lần đầu, ≤ 1 phút lập lại (SC-007); tìm một tiếng ≤ 200 ms; trộn lại phim 30 s ≤ 30 s (SC-006); học tiếng video 3 phút ≤ 10 phút trên CPU

**Constraints**: không sửa `lib/` (soundmix không import code thư viện); không AI lên âm thanh Sonniss; tiếng Sonniss chỉ cho chủ xưởng; âm thanh tham chiếu không rời máy, không vào phim; mọi lệnh gọi Claude dùng Opus 5.5 (mô hình duy nhất của xưởng, specs/024); dựng hình vẫn GPU (037 không dựng hình); không tự cài phần mềm hệ thống (`deps sound` chỉ cài gói Python)

**Scale/Scope**: kho ≤ 10⁵ tệp; ≤ 60 shot, ≤ 200 cue mỗi phim; một chủ xưởng

**Phụ thuộc nhánh**: tách từ `origin/main@f9cf3f7`. Phần không cần 035 (kho, Freesound, phạm vi, học tiếng, lõi plan/resolve/mix trên tệp định dạng 035) làm trước. Phần cắm vào bước/điểm duyệt/trang Sound làm sau khi 035 merge (rebase). Thứ tự merge: 035 → 037. (R1)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá |
|---|---|
| I. Spec là nguồn sự thật | Đạt. Spec đã duyệt qua clarify (5 câu); spec không nêu công nghệ (Sonniss/Freesound là nguồn nội dung và giấy phép). |
| II. Không đoán | Đạt. Không còn `NEEDS CLARIFICATION`; ngưỡng (đồng ý nhãn, lặng −50 dB, cắt ±0,1 s) ghi ở research R8, rút từ mẫu đã kiểm. |
| III. MVP theo story | Đạt. P1 = US2 (kho) + US1 (đặt tiếng, trộn); US1 dùng được bằng lệnh trước khi có trang (US3). US4 (học) độc lập. |
| IV. Đo được | Đạt. Mục lục, tìm, Freesound (máy chủ giả), phạm vi, resolve, trộn (so từng mẫu ngoài đoạn sửa), luật đồng ý/lặng/cắt có test tự động; độ lớn đo bằng bước kiểm phim; lượt thật trong quickstart (SC-003 trên mẫu voice-check). |
| V. Đơn giản | Hai độ phức tạp ghi ở Complexity Tracking: tầng phụ thuộc ML nặng (chỉ cho học) và proxy giữ phạm vi kho. |
| VI. Thư viện gốc | Đạt. Không chạm `lib/`; `soundmix.py` chỉ dùng venv của thư viện để có numpy/soundfile. |
| VII. Hai bộ máy | Đạt. Chỉ phim `engine: "ae"`; phim web giữ cách trộn cũ. 037 không dựng hình. |
| VIII. Học bằng đo | Đạt. Mỗi luật tiếng kèm mốc bằng chứng; chỉ tin khi hai bộ phân loại đồng ý; lưu theo khung phong cách (template.json + mục âm thanh STYLE.md). |
| IX. Spec-kit cho phần mềm | Đạt. Công cụ xưởng; từng phim vẫn theo skill `film-make`. |
| Bản quyền | Đạt. Danh sách "(CC0, CC BY, OFL, MIT)" của hiến pháp là ví dụ về giấy phép rõ ràng, không phải danh sách đóng: xưởng đã dùng Apache-2.0 (Kokoro), GPL (FFmpeg) và dịch vụ thương mại có điều khoản riêng (ElevenLabs), đều ghi CREDITS. Giấy phép Sonniss GDC 2.0 là giấy phép thương mại rõ ràng, người dùng đã đọc và đồng ý (2026-11-25, analyze C1). Sonniss GDC 2.0 (người dùng đồng ý 2026-11-25; không AI, không phát tán, chỉ chủ xưởng), Freesound CC0, mô hình (MIT/BSD/Apache) và ontology AudioSet (CC BY 4.0) ghi CREDITS; âm thanh tham chiếu chỉ trên máy, bị từ chối ở kho (R11). |
| Phần mềm hệ thống | Đạt. `deps sound` chỉ cài gói Python vào `tools/.venv`. |

**Re-check sau Phase 1**: vẫn đạt. Không thêm dịch vụ; Freesound và kho đi qua proxy và `bin/studio` sẵn có.

## Project Structure

### Documentation (this feature)

```text
specs/037-sound-per-shot/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md       # sound lib|cue|silence|plan|mix|notes|key, learn sfx, deps sound
│   └── api.md       # khối sound của /jobs/{id}/steps, actions, preview, settings; proxy /internal/sound/*
└── tasks.md         # /speckit-tasks
```

### Source Code (repository root)

```text
tools/
├── filmcheck/
│   ├── soundlib.py      # MỚI: roots, quét + metadata (bext/INFO/iXML/UCS), library.db FTS5, search(scope), từ chối references/
│   ├── ucs.py           # MỚI: bảng CatID → loại/loại con (dữ liệu)
│   ├── freesound.py     # MỚI: search CC0, tải preview-hq-ogg, kiểm license; trực tiếp (CLI) hoặc qua proxy (việc)
│   ├── soundplan.py     # MỚI: plan.json (đọc/ghi nguyên tử theo base), cue add/set/rm, silence, resolve (timing.json + keys.json + words.json), dropped/missing
│   ├── soundmix.py      # MỚI: trộn (chạy bằng python venv thư viện), luật cắt, lặng, ducking, soft-clip, stems, khối CREDITS
│   ├── points.py        # (sửa) mix của phim AE: stale/fingerprint thêm sound/*; gate dùng cho ae render
│   ├── edit.py          # (sửa) op cue_set/cue_rm/cue_add/note_* cho điểm mix của phim AE
│   └── cli.py           # `sound …`
├── ae/cli.py            # (sửa) ae render gọi gate mix
├── style-learn/
│   ├── sl/sfxlearn.py   # MỚI: Demucs, sự kiện 2 lớp, AST + CLAP, đồng ý theo ontology, ghép từ, lặng, cắt, tổng hợp phong cách
│   ├── sl/audioset.py   # MỚI: ontology AudioSet rút gọn (nhãn → tổ tiên mức 2, nhóm tiếng động)
│   └── learn.py         # `learn sfx`
├── studio/studio/
│   ├── voicekeys.py     # (sửa) tổng quát theo tên khoá: elevenlabs, freesound
│   ├── filmsteps.py, actions.py, reviews.py, server.py   # khối sound, actions, preview (phạm vi), settings, fix target sound
│   └── web/app.js, style.css                             # trang Sound
├── runner/proxy.py      # /internal/sound/search, /internal/sound/fetch (phạm vi theo accounts.role)
├── runner/agent.py, JOB.md   # bước Sound của việc AE; việc fix target sound
└── requirements-sound.txt    # MỚI

bin/studio                      # `sound …`, `deps sound`
.claude/skills/film-make/SKILL.md, .claude/skills/style-learn/SKILL.md, tools/ae/SOUND.md (MỚI)
CREDITS, .gitignore
tests/filmcheck/test_soundlib.py, test_soundplan.py, test_soundmix.py, test_freesound.py, data/soundlib/ (tiếng tổng hợp nhỏ)
tests/learn/test_sfxlearn.py, data/voicecheck_expect.json · tests/online/test_sound_scope.py · tests/ui/test_sound_api.py, browser_sound.cjs
```

**Structure Decision**: thêm 5 mô-đun nhỏ trong `filmcheck` và 2 trong `style-learn`, mở rộng proxy/app sẵn có. Không thêm dịch vụ hay tiến trình.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Tầng phụ thuộc ML mới (~1 GB: torch CPU, demucs, transformers) | Học tiếng cần tách lớp và hai bộ phân loại (FR-017, FR-018); đã chứng minh trên mẫu voice-check | Chỉ đo năng lượng như `soundcraft` (không biết tiếng gì); một bộ phân loại (tự tin sai). Tầng tách riêng nên bộ cài và người không học phong cách không phải tải |
| Kho và Freesound đi qua proxy thay vì để agent đọc thẳng | Phạm vi Sonniss chỉ cho chủ xưởng (FR-013a) và khoá Freesound không vào việc (FR-014); sandbox cho agent đọc khắp nơi | Cho agent đọc thư mục kho: không chặn được việc của khách; đưa khoá vào môi trường việc: lộ khoá |
