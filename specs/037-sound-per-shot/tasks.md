---
description: "Task list for 037-sound-per-shot"
---

# Tasks: Âm thanh theo shot cho phim After Effects

**Input**: `specs/037-sound-per-shot/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md)

**Tests**: bắt buộc theo hiến pháp IV (logic quan trọng có test tự động; âm thanh có kiểm bằng số liệu).

**Thứ tự story**: US2 (kho) làm trước US1 vì US1 cần tìm tiếng; cả hai là P1. US4 (học) độc lập. Các task có nhãn **⟂035** chỉ làm được sau khi 035 merge vào main và 037 đã rebase (research R1); trước đó dừng ở checkpoint "trước 035".

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Thêm `sound/cache/`, `sound/stems/`, `references/*/stems/` vào `.gitignore`; thêm `tools/requirements-sound.txt` (`--index-url https://download.pytorch.org/whl/cpu` cho `torch`, rồi `demucs`, `transformers`, `soundfile`) theo research R9
- [X] T002 Thêm lệnh `deps sound` (cài `requirements-sound.txt` vào `tools/.venv` theo mẫu `deps_learn`) và nhóm lệnh `sound …` (chuyển cho `tools/filmcheck/cli.py`) trong `bin/studio`, cập nhật `--help`
- [X] T003 [P] Tạo bộ tiếng thử nhỏ tự tổng hợp lúc chạy test bằng `tests/filmcheck/soundfix.py` (không giữ tệp âm thanh nào trong git): ~12 tệp WAV ≤ 1 s (vỡ, bụp, vút, bước chân, bọt nước…) tên kiểu UCS (`GLASBrk_Window Shatter_TEST.wav`), vài tệp có chunk `bext`/`LIST INFO`/`iXML`, một tệp hỏng; tổng ≤ 300 KB

---

## Phase 2: Foundational

- [X] T004 Tổng quát `tools/studio/studio/voicekeys.py` theo tên khoá (`elevenlabs`, `freesound`): `secret(name)`, `save(name, key, …)`, `status(name)`; giữ tương thích mọi chỗ gọi ElevenLabs hiện có (`tools/runner/proxy.py`, `tools/studio/studio/server.py`); test trong `tests/online/test_voicekeys.py` (sửa hoặc thêm) cho khoá thứ hai, quyền tệp 0600, chỉ trả 4 ký tự cuối
- [X] T005 [P] Tạo `tools/filmcheck/ucs.py`: bảng `CatID → (category, subcategory)` của UCS (danh mục chính ~80 mục, đủ cho GLASS, IMPACT, WHOOSH, FOLEY, CROWDS, WATER, AMBIENCE, UI, CARTOON, BALL, PAPER, DOOR, FOOTSTEPS…) và `parse_name(stem) → {cat_id, category, subcategory, descriptor}`
- [X] T006 Thêm `sound_root()` (thư mục `$STUDIO_DATA/sound`, mặc định `~/.local/share/claude-utube/sound`) và hàm từ chối thư mục nằm dưới `<repo>/references/` hoặc dữ liệu học trong `tools/filmcheck/soundlib.py` (khung mô-đun, research R2, R11)

**Checkpoint**: nền xong.

---

## Phase 3: User Story 2 - Kho tiếng trên máy + Freesound CC0 (Priority: P1)

**Goal**: lập mục lục gói Sonniss chỉ từ tên/metadata, tìm theo chữ, lấp chỗ thiếu bằng Freesound CC0, phạm vi chủ xưởng/khách.

**Independent Test**: kho thử 12 tệp → 11 mục + 1 hỏng; lập lại "0 new"; tìm "window shatter" ra tệp GLAS đầu tiên; Freesound giả chỉ tải CC0; khách chỉ thấy CC0.

### Tests (viết trước, phải đỏ)

- [X] T007 [P] [US2] `tests/filmcheck/test_soundlib.py`: lập mục lục kho thử (đủ mục, tệp hỏng `ok=false`, metadata `bext`/`INFO`/`iXML`/UCS vào đúng cột), lập lại chỉ đọc tệp mới/đổi (đếm số lần mở tệp), tệp mất bị xoá mục, từ chối thư mục dưới `references/`, `search()` xếp hạng bm25 + loại + độ dài, `scope="cc0"` chỉ trả mục `license = "cc0-1.0"`; kiểm **không** mô-đun nào đọc mẫu âm thanh Sonniss ngoài header (giả lập `soundfile`/`wave.readframes` ném lỗi khi bị gọi)
- [X] T008 [P] [US2] `tests/filmcheck/test_freesound.py` với máy chủ giả (`STUDIO_FREESOUND_URL`): truy vấn gửi `filter=license:"Creative Commons 0"`, kết quả có license khác CC0 bị bỏ dù máy chủ trả về, tải `preview-hq-ogg` vào `freesound/<id>.ogg`, mục mới có `source=freesound`, `credit "Freesound #<id> by <user>"`, `url`, `license cc0-1.0`, `fetched_at`; khoá không xuất hiện trong log/ngoại lệ; không có khoá → lỗi `no_key` rõ ràng
- [X] T009 [P] [US2] `tests/online/test_sound_scope.py`: proxy `/internal/sound/search` và `/internal/sound/fetch` với việc của `admin` (thấy Sonniss) và của `customer` (chỉ CC0; fetch mục Sonniss → 403 `scope`); `fetch` chép đúng tệp vào `films/<phim>/sound/cache/`; app `GET /api/sound/preview/{entry}` 403 với khách cho mục Sonniss

### Implementation

- [X] T010 [US2] `tools/filmcheck/soundlib.py`: `roots.json` (`{version: 1, roots: [{path, kind: "sonniss", added_at}]}`), quét đệ quy `.wav/.flac/.ogg/.mp3/.aif`, đọc header + chunk RIFF `bext`, `LIST/INFO` (INAM, ICMT, IKEY, ISBJ), `iXML` (UCS CatID, USER/CATEGORY) bằng thư viện chuẩn (không đọc mẫu âm thanh), nguồn `Sonniss GDC <năm>` từ tên thư mục gói; `library.db` bảng `entry` đúng các trường của data-model (id `s:` + sha1(path)[:12] hoặc `fs:<id>`; `license` ∈ `sonniss-gdc-2.0|cc0-1.0`, "lúc lấy về; không đổi sau đó") + FTS5 `entry_fts`; khoá lập lại `(path, size, mtime_ns)`
- [X] T011 [US2] `soundlib.search(query, cat=None, dur=None, scope="all", n=8)`: bm25 trọng số name 3 / description 2 / keywords 2 / category 1, cộng điểm khi loại khớp, trừ khi độ dài lệch; trả id, tên, loại, độ dài, nguồn, credit (chỉ chữ, R3)
- [X] T012 [US2] `tools/filmcheck/freesound.py`: `search_cc0(query, dur)` và `fetch(id)` (preview-hq-ogg), kiểm license từng kết quả, ghi mục vào `library.db`; hai đường: trực tiếp (`FREESOUND_API_KEY` từ môi trường hoặc `.env`) và qua proxy khi có `STUDIO_JOB_TOKEN` + `STUDIO_PROXY` (như `eleven.py`); `redact()` khoá trong mọi thông báo
- [X] T013 [US2] Hàm `find(query, cat, dur, scope)` trong `soundlib.py`: tìm trên máy, nếu điểm đầu dưới ngưỡng (hoặc 0 kết quả) và có khoá → Freesound CC0 tự động (FR-013), trả kết quả gộp
- [X] T014 [US2] Lệnh `sound lib add|index|status|search` và `sound key freesound` trong `tools/filmcheck/cli.py` theo `contracts/cli.md` (in `indexed N new · M changed · K gone · B broken · <giây> s`; `status` không in khoá)
- [X] T015 [US2] Proxy `tools/runner/proxy.py`: `POST /internal/sound/search {query, cat?, dur?}` và `POST /internal/sound/fetch {entry, film}`; phạm vi theo `jobs.owner` → `accounts.role` (`admin` → all, `customer` → cc0); khoá Freesound từ `voicekeys.secret("freesound")`; log chỉ số kết quả
- [X] T016 [US2] App `tools/studio/studio/server.py`: `GET/POST/DELETE /api/settings/sound` (thư mục kho, lập mục lục chạy nền, khoá Freesound lưu sau một lần gọi thử), `GET /api/sound/preview/{entry}` (≤ 30 s, kiểm phạm vi); mục "Sound library" trong Settings của `tools/studio/studio/web/app.js`
- [X] T017 [US2] Ghi `CREDITS` chung: Sonniss GDC (giấy phép 2.0, dùng thương mại, không phát tán, không AI; chỉ phim của chủ xưởng) và Freesound (chỉ CC0, tải qua API bằng khoá của người dùng)

**Checkpoint**: chạy `tests/filmcheck`, `tests/online`; kho thử dùng được bằng lệnh. Commit.

---

## Phase 4: User Story 1 - Tiếng tự đặt theo chuyển động (Priority: P1) 🎯 MVP

**Goal**: `sound/plan.json` + resolve theo `timing.json`/`keys.json` + trộn `out/mix.wav` có luật cắt, lặng, CREDITS.

**Independent Test**: phim thử tổng hợp (3 shot, `timing.json`, `animatic/keys.json`, giọng ngắn) → mọi cue lệch ≤ 1 khung; đổi thời lượng → mốc tính lại; ngoài đoạn sửa giống hệt từng mẫu; không mẫu tham chiếu nào lọt.

### Tests

- [X] T018 [P] [US1] Fixture phim thử `tests/filmcheck/soundfilm.py`: dựng thư mục phim AE tạm với `film.json` (`engine: "ae"`), `timing.json` và `animatic/keys.json` đúng định dạng data-model của 035, `narration.json`, `voices/*.wav` + `words.json` tổng hợp, `out/music.wav`
- [X] T019 [P] [US1] `tests/filmcheck/test_soundplan.py`: `cue add` với mỗi loại neo (`motion`+`edge`+`offset_f`, `line`+`word`, `shot_at`, `span`) cho `at` đúng ≤ 1 khung; đổi `timing.json → frames` của shot trước → mọi `at` sau dời đúng; neo `motion` biến mất hoặc mốc ≥ độ dài shot mới → `state: dropped` kèm `why`; không tìm được → `state: missing`, `entry: null`, `why` có từ khoá, không tiếng tổng hợp thay (FR-007); cue `by: user` giữ qua lập lại; mật độ: hai cue cách nhau < 0,2 s hoặc vượt `per_min` của phong cách (mặc định 12/phút) → cue ít quan trọng hơn (`auto` trước `claude`, không bao giờ `user`; tiếng nhỏ hơn trước) thành `dropped` với `why: "too dense"`; `base` lệch → mã 4; phim không có `timing.json`/`keys.json` → rơi về `out/render-shots.json`/`shots.json` và neo câu
- [X] T020 [P] [US1] `tests/filmcheck/test_soundmix.py`: trộn phim thử ra `out/mix.wav` 48 kHz stereo; tiếng `cut: hard` về ≤ −60 dB trong 10 ms sau điểm cắt, `fade` theo `fade_s`, `over` kéo qua; khoảnh khắc lặng hạ nhạc và tiếng về `db` trong khoảng; sửa một cue → mẫu ngoài [mốc − 60 ms, cuối + 60 ms] giống hệt (so mảng); mục có `source` ngoài {sonniss, freesound, user} hoặc đường dẫn dưới `references/` → lỗi (R11); khối CREDITS có đúng một dòng mỗi mục đã dùng và được thay khi trộn lại

### Implementation

- [X] T021 [US1] `tools/filmcheck/soundplan.py`: đọc/ghi nguyên tử `sound/plan.json` với `base` (băm), `version: 1`, `timing_sha`, `profile: style|default`, `cues[]` đúng các trường data-model (`id` "`c01`…, bền qua các lần chạy lại", `by` ∈ `auto|user|claude`, `state` ∈ `placed|dropped|missing` + `why`, `cut` ∈ `hard|fade|over` + `fade_s`), `silences[]`
- [X] T022 [US1] `soundplan.resolve(film_dir)`: `t0(shot)` từ `timing.json` (fallback R1), mốc neo từ `animatic/keys.json` (`{shot: [{layer, prop, t0, t1}]}`, tên hiện `layer · prop`), `voices/words.json` + `narration.json`; làm tròn khung; đặt `dropped`/`missing` + `why`; giới hạn mật độ (khoảng cách tối thiểu 0,2 s, `per_min` của phong cách hoặc mặc định 12/phút; bỏ theo thứ tự `auto` → `claude`, không bỏ cue `user`, kèm `why: "too dense"`)
- [X] T023 [US1] `soundplan.add_cue/set_cue/rm_cue/add_silence`: gọi `soundlib.find` (theo phạm vi; trong việc của app qua proxy) để chọn `entry` + `alts` (≤ 7), giới hạn `gain_db` trong `sfx_db` của phong cách (`edit.mix_ranges`), luật mặc định khi phong cách chưa có `sound.sfx` (`profile: default`)
- [X] T024 [US1] `tools/filmcheck/soundmix.py` (chạy bằng python venv thư viện, không import `lib/`): giọng theo `narration.json`, `out/music.wav` nếu có, cue từ `sound/cache/` (chép bằng `soundlib`/proxy fetch nếu thiếu), đổi 48 kHz stereo, fade vào 5 ms, luật cắt, ducking nhạc cửa sổ 50 ms, lặng dốc 30 ms, soft-clip tanh không trạng thái; ghi `out/mix.wav`, `sound/stems/fx.wav`, `sound/stems/voice.wav`; thay khối `# sound effects (studio, 037)` … `# end sound effects` trong `CREDITS` của phim
- [X] T025 [US1] Lệnh `sound cue add|set|rm`, `sound silence add`, `sound plan`, `sound mix` trong `tools/filmcheck/cli.py` theo `contracts/cli.md`; `sound mix` ghép lại tiếng vào bản đẹp nếu đã có (không dựng hình, như `edit.mix_edit`)
- [X] T026 [US1] Viết `tools/ae/SOUND.md`: cách Claude lập danh sách tiếng (đọc `SCRIPT.md`, `animatic/keys.json`, `sound.sfx` của phong cách; mỗi chuyển động có tên đáng nghe → một cue neo `motion`; tiếng nền `span`; khoảnh khắc lặng; từ khoá tiếng Anh kiểu UCS); `mix.py` của phim AE chỉ còn làm nhạc → `out/music.wav`
- [X] T053 [US1] Bật/tắt tiếng theo shot (FR-005a): `plan.json → off`, cue của shot tắt có `state: "off"` (giữ, không trộn, không tính mật độ), `add_cue` từ chối mã `off`, `soundplan.set_shots`, lệnh `sound shot on|off`; test trong `tests/filmcheck/test_soundplan.py` và `test_soundmix.py`. Trang Sound (T045/T046) thêm op `shot_set` và công tắc trên mỗi shot
- [X] T054 [US4] Hướng A và chỉnh sau bài chấm CC0 (research R8): `sound.sfx → actions` chỉ `sure`, `hints` cho `likely`; bỏ luật "AST thắng"; AST chỉ nghe lớp của sự kiện; lặng ≥ 0,6 s + nhánh "cả bản trộn im" + dung sai đuôi từ 0,2 s; khoảng lặng neo vào từ bắt đầu khi từ đó **kết thúc** (`soundplan`); `soundlib.find` hỏi Freesound khi kho có < 3 tiếng khớp mạnh; `tools/ae/SOUND.md`; test trong `tests/learn/test_sfxlearn.py`, `tests/filmcheck/test_soundplan.py`, `tests/filmcheck/test_freesound.py`
- [ ] T027 [US1] (làm cùng T051, cần kho Sonniss thật) Chuyển `films/ae-sleepless-test/mix.py` (ngoài git, chỉ trên máy) sang chỉ làm nhạc `out/music.wav`, lập `sound/plan.json` cho 9 shot bằng `sound cue add`; ghi lại cách làm trong `tools/ae/SOUND.md`

**Checkpoint "trước 035"**: chạy đủ `tests/filmcheck`; trộn được phim thử bằng lệnh với kho thử. Commit. Dừng các task ⟂035 tới khi 035 merge.

- [ ] T028 [US1] ⟂035 Rebase `037-sound-per-shot` lên `origin/main` có 035; sửa xung đột; chạy lại toàn bộ test
- [ ] T029 [US1] ⟂035 `tools/filmcheck/points.py`: với phim AE, `stale("mix")` thêm `sound/plan.json`, `timing.json`, `narration.json`; `fingerprint("mix")` thêm `sound/plan.json` + ghi chú mở trong `sound/notes.json`; `tools/ae/cli.py`: `ae render` gọi `points.gate(d, "mix")` sau cổng animatic; `tools/filmcheck/steps.py`: với phim AE, `impact("mix")` ra đúng Final render (và Self-check, Publish), không ra Script/Cast/Voice/Animatic (FR-029); test trong `tests/filmcheck/test_points.py`, `tests/filmcheck/test_steps.py` và `tests/ae/test_ae.py` (render bị từ chối khi điểm mix bật mà chưa duyệt, FR-028, SC-008)
- [ ] T030 [US1] ⟂035 Bước Sound trong việc làm phim AE: `tools/runner/JOB.md`, `tools/runner/agent.py` (sau Animatic duyệt: đọc `tools/ae/SOUND.md`, `sound cue add …`, `sound mix`, gửi duyệt `mix`; agent không tự duyệt), `.claude/skills/film-make/SKILL.md` (mục Phim After Effects)
- [ ] T031 [US1] ⟂035 Chạy thật trên `ae-sleepless-test` theo quickstart bước 4: đo SC-001, SC-002, SC-009 và ghi kết quả (đạt / đạt một phần / thất bại) vào `specs/037-sound-per-shot/quickstart.md` mục "Kết quả"

---

## Phase 5: User Story 4 - Học tiếng từ video mẫu (Priority: P2)

**Goal**: `learn sfx` cho ra `sfx.json` (sự kiện tin được khi AST và CLAP đồng ý) và khối `sound.sfx` của phong cách.

**Independent Test**: âm thanh tổng hợp + bộ phân loại giả → luật đồng ý, lớp giọng ngoài lời, lặng, cắt đúng; mẫu voice-check thật 5/5 (quickstart bước 6).

### Tests

- [X] T032 [P] [US4] `tests/learn/test_sfxlearn.py` (không cần torch; bộ tách lớp và hai bộ phân loại được tiêm giả): sự kiện tìm ở lớp tiếng động và ở lớp giọng ngoài từ (từ người kể ±80 ms bị tắt); `agree` khi CLAP top-1 ∈ AST top-5 hoặc cùng tổ tiên mức 2, ngược lại `unsure` và không vào luật; AST < 0,10 không dùng; ghép từ gần nhất ≤ 1,0 s; lặng ≥ 0,4 s ở ≤ −50 dBFS sau từ; cắt `hard` khi rơi ≥ 20 dB trong 50 ms quanh điểm cắt, `fade`, `over`; tổng hợp `sound.sfx` chỉ chứa số, nhãn, mốc (không mảng mẫu âm thanh); một bộ phân loại thiếu → không sự kiện nào `agree`
- [X] T033 [P] [US4] `tests/learn/data/voicecheck_expect.json`: 5 sự kiện kỳ vọng của mẫu đã kiểm (nhãn nhóm + mốc/từ: kính vỡ "window", lặng "goes silent" ≤ −50 dB, đám đông "people cheer" tắt ở cắt, bóng, bọt nước), chỉ số liệu

### Implementation

- [X] T034 [P] [US4] `tools/style-learn/sl/audioset.py`: ontology AudioSet rút gọn (527 nhãn → tổ tiên mức 2; danh sách nhãn tiếng động/tiếng người không phải lời, bỏ Speech/Music và con của chúng) dạng dữ liệu, nguồn CC BY 4.0 ghi đầu tệp
- [X] T035 [US4] `tools/style-learn/sl/sfxlearn.py`: tách lớp htdemucs (CPU), lớp `fx` = drums + other, lớp `vocal_off_words`; tìm sự kiện (RMS 20 ms, spectral flux ngưỡng MAD như `soundcraft.sfx_onsets`, 0,1–8 s, gộp < 150 ms); AST top-5 + CLAP zero-shot "the sound of {label}"; luật đồng ý; ghép từ/shot; lặng; cắt; `db_vs_voice`; ghi `profile/<v>/sfx.json` với `models` có phiên bản và `ontology` các nhãn đã gặp; lớp tách ra vào `references/<set>/stems/`
- [X] T036 [US4] `sfx_summary` trong `sfxlearn.py`: tổng hợp các video → `kit/template.json → sound.sfx` (`per_min`, `gain_db` [p25, p50, p75], `actions[{action, label, n, evidence}]`, `silences`, `cut`, `unsure_n`) và một đoạn bằng chứng trong mục âm thanh của `STYLE.md` của phong cách
- [X] T037 [US4] Lệnh `learn sfx <set> [--only]` và `learn sfx --file <wav> --words <json> [--shots <json>]` trong `tools/style-learn/learn.py` (mã 3 khi thiếu `deps sound`/`words.json`); xoá `stems/` cùng video khi dọn hoặc ở dịch vụ online (theo luật xoá hiện có của style-learn)
- [X] T038 [US4] `.claude/skills/style-learn/SKILL.md`: bước `learn sfx` tự chạy sau `learn sound` cho phong cách mới; cách chạy riêng cho phong cách đã có
- [X] T039 [US4] Cài `sh bin/studio deps sound`, kiểm thẻ giấy phép của htdemucs, AST, CLAP và ghi vào `CREDITS` (PyTorch BSD-3, Demucs MIT, Transformers Apache-2.0, AST, CLAP, AudioSet CC BY 4.0)
- [X] T040 [US4] Chạy thật quickstart bước 6 trên `references/voice-check/a.wav`; đo SC-003 so với `voicecheck_expect.json`; chỉnh ngưỡng nếu cần (ghi lý do vào research R8); ghi kết quả vào quickstart "Kết quả"

**Checkpoint**: `tests/learn` xanh; commit.

---

## Phase 6: User Story 3 - Duyệt Sound: nghe và sửa từng shot (Priority: P2) ⟂035

**Goal**: trang Sound theo shot với phát clip + bản trộn, đổi/dời/xoá/thêm tiếng, ghi chú cho Claude.

**Independent Test**: đổi tiếng sang gợi ý 2, dời 5 khung, xoá một tiếng → bản trộn ≤ 30 s, ngoài đoạn sửa giống hệt; sửa giữ qua đổi thời lượng; nút duyệt hoạt động.

### Tests

- [ ] T041 [P] [US3] ⟂035 `tests/ui/test_sound_api.py`: khối `sound` của `GET /jobs/{id}/steps` đúng `contracts/api.md`; `POST /jobs/{id}/actions` op `cue_set|cue_rm|cue_add|shot_set|note_add|note_delete` với `base` (409 `changed` khi lệch), sửa đánh `by: user`; `mix.wav` phát được với `Range`; `POST /films/{film}/sound/fix` tạo việc `fix` `target: "sound"`
- [ ] T042 [P] [US3] ⟂035 `tests/ui/browser_sound.cjs`: mở bước Sound, bấm một shot phát clip (video câm + bản trộn từ `t0`), đổi tiếng (≥ 3 gợi ý, nghe thử), dời, xoá; đo thời gian trộn lại ≤ 30 s; ghi chú + "Send notes to Claude"

### Implementation

- [ ] T043 [US3] ⟂035 `tools/filmcheck/edit.py`: op `cue-set`, `cue-rm`, `cue-add`, `sound-note-add`, `sound-note-delete` cho điểm `mix` của phim AE (gọi `soundplan`, rồi `soundmix`; ghi `log_edit`)
- [ ] T044 [US3] ⟂035 `tools/filmcheck/soundplan.py` + `tools/filmcheck/pins.py` (của 035): `sound/notes.json` (`{version, base_sha, shots: {S2: [{id, text, state, reply, lot}]}}`), lệnh `sound notes add|delete|show|reply`
- [ ] T045 [US3] ⟂035 `tools/studio/studio/filmsteps.py`, `actions.py`, `reviews.py`, `server.py`: khối `sound`, các op, `files/sound/mix.wav` (Range), quyết định `revise` của duyệt `mix` cho phim AE, `POST /films/{film}/sound/fix`
- [ ] T046 [US3] ⟂035 `tools/studio/studio/web/app.js`, `style.css`: khung Sound (dải thời gian shot/câu/khối tiếng có nhãn, lưới shot, danh sách tiếng của shot, công tắc tiếng bật/tắt trên mỗi shot (T053), đổi tiếng với nghe thử, dời theo khung, độ lớn, xoá, thêm, ghi chú, "Send notes to Claude", cột "If you change this" → Final render), dùng lại thành phần dải thời gian của Animatic
- [ ] T047 [US3] ⟂035 Việc `fix` `target: "sound"` trong `tools/runner/agent.py`/`JOB.md`: Claude chỉ sửa cue của shot có ghi chú, `sound mix`, trả lời từng ghi chú, không duyệt; bước Sound về chưa duyệt
- [ ] T048 [US3] ⟂035 Chạy thật quickstart bước 5 trong app trên `ae-sleepless-test`; đo SC-006 và ghi kết quả

---

## Phase 7: Polish & Cross-Cutting

- [ ] T049 [P] Test repo `tests/test_no_media.py` (hoặc thêm vào bộ có sẵn trong `tests/run.sh`): 0 tệp âm thanh mới trong git (kho thử tự tổng hợp lúc chạy test); `desktop/core-build` không gói `sound/` hay `requirements-sound.txt` (SC-005)
- [ ] T050 [P] Cập nhật `CLAUDE.md` (mục ngắn "Âm thanh theo shot (specs/037)"), `tools/CLAUDE.md` (mô-đun mới), `desktop/core-build/credits-check.py` nếu cần cho dòng CREDITS mới
- [ ] T051 Kho thật: khi người dùng đã tải Sonniss 2026 + 2024 vào `/mnt/e/SoundLibrary/Sonniss`, giải nén (nếu còn zip), `sound lib add`, đo SC-007, ghi kết quả vào quickstart
- [ ] T052 Chạy đủ bộ test (`sh tests/run.sh`, `sh tests/filmcheck/run.sh`, `sh tests/learn/run.sh`, `sh tests/ui/run.sh`, `sh tests/online/run.sh`, `sh tests/ae/run.sh`, `sh tests/render/run.sh`, `sh tests/license/run.sh`) rồi mở PR (không merge)

---

## Dependencies & Execution Order

- Setup (T001–T003) → Foundational (T004–T006) → US2 (T007–T017) → US1 trước 035 (T018–T027).
- US4 (T032–T040) chỉ cần Setup; làm song song với US2/US1.
- ⟂035: T028 (rebase) chặn T029–T031 và cả Phase 6 (T041–T048).
- Polish sau cùng; T051 chờ người dùng tải Sonniss.

## Parallel Examples

- US2: T007, T008, T009 cùng lúc (tệp test khác nhau); T005 song song T004.
- US1: T018, T019, T020 cùng lúc.
- US4: T032, T033, T034 cùng lúc; cả phase song song với US2.

## Implementation Strategy

1. MVP trước 035: US2 + US1 bằng lệnh trên phim thử tổng hợp và kho thử → commit.
2. US4 (học tiếng) → commit; chạy thật trên mẫu voice-check.
3. Sau khi 035 merge: rebase, cổng + bước Sound + trang (T028–T031, Phase 6).
4. Kho Sonniss thật khi người dùng đã tải; chạy đủ test; mở PR.
