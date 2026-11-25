# Tasks: Giọng theo nhân vật và giọng ElevenLabs

**Input**: Design documents from `specs/036-voice-cast/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: có, vì spec đòi test tự động (SC-002, SC-004, SC-006, SC-008). Mọi test chạy không tốn tiền (ElevenLabs giả); lượt thật chỉ ở quickstart §2 và `tests/online/live.sh`, cần người dùng đồng ý.

**Phụ thuộc ngoài**: phần Cast của US2 (T030–T034) cần 034 đã có `tools/filmcheck/cast.py`, `castlib.py` (034 chưa làm: 54 task mở). Mọi phần khác chạy độc lập; nhân vật của phim chưa có 034 lấy giọng từ `film.json → voices`.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Thêm máy chủ ElevenLabs giả cho test (subscription, voices phân trang, with-timestamps trả PCM im lặng + alignment theo số ký tự, 401 khi khoá sai, quota khi vượt) trong `tests/filmcheck/fake_eleven.py`
- [X] T002 [P] Thêm trình đọc `.env` nhỏ (`KEY=VALUE`, bỏ dòng `#`, biến môi trường thắng tệp) `load_env(root)` trong `tools/filmcheck/eleven.py` (khung mô-đun, chưa có lời gọi)

---

## Phase 2: Foundational (chặn mọi story)

- [X] T003 Viết `tools/filmcheck/voicecat.py`: mã giọng `kokoro:<tên>` | `el:<id>`, mã không tiền tố = Kokoro (research R4); `parse(id) -> (provider, name)`; `kokoro_voices()` chuyển từ `tools/studio/studio/filmsteps.py::voices`; `catalog(el_voices)` trả `[{id, provider, name, gender, age, accent, desc, cloned, preview}]`
- [X] T004 Viết `tools/filmcheck/voicefx.py`: `apply(raw_wav, out_wav, pitch, formant, fx, emotion_fallback)` bằng ffmpeg; cao độ −6…+6 bán cung bằng `rubberband=pitch=2^(st/12):formant=shifted|preserved`, lùi về `asetrate+aresample+atempo` khi ffmpeg thiếu rubberband; `fx` ∈ `none|phone|wall|radio|hall` theo chuỗi lọc ở research R7; giữ thời lượng (đuôi vang ≤ +0,15 s); thì thầm −6 dB, hét +3 dB khi cảm xúc không áp được
- [X] T005 Mở rộng `.made.json` trong `tools/filmcheck/cli.py::made_key` thành `{text, provider, voice, speed, pitch, formant, emotion, fx, model}` (data-model); phim cũ thiếu trường coi như mặc định để `--changed` không đọc lại cả phim
- [X] T006 [P] Test `tests/filmcheck/test_voicefx.py`: cao độ +4 tăng cao độ trung vị ≥ 20% trên một tông thử; −2 giảm; thời lượng lệch ≤ 0,15 s; `phone` cắt năng lượng < 300 Hz và > 3400 Hz; lùi asetrate khi giả lập thiếu rubberband
- [X] T007 [P] Test `tests/filmcheck/test_voicecat.py`: mã có/không tiền tố, danh mục gộp, giọng nhân bản có `cloned: true`

**Checkpoint**: danh mục giọng và hậu kỳ dùng được; phim cũ vẫn chạy như trước.

---

## Phase 3: User Story 1 - Khoá ElevenLabs và giọng ElevenLabs (P1) 🎯 MVP

**Goal**: gắn khoá, thử khoá, chọn giọng ElevenLabs, đọc cả phim có báo trước ký tự.
**Independent Test**: quickstart §1 và §2 (bước 1–3 với máy chủ giả; bước 4 là lượt thật).

### Tests

- [X] T008 [P] [US1] Test `tests/filmcheck/test_eleven.py`: `subscription()`, `voices()` lặp `next_page_token`, `speak()` trả PCM 24 kHz + alignment; khoá sai → `ElevenError("invalid_key")` mã thoát 3; quota → `"quota"`; đi qua proxy khi có `STUDIO_JOB_TOKEN`+`STUDIO_PROXY`, khi đó không đọc `.env`
- [X] T009 [P] [US1] Test `tests/filmcheck/test_voice_make_providers.py`: phim trộn câu `kokoro:` và `el:`; thiếu `--yes` khi > 1 câu EL → mã 1 và in ước tính; đủ `--yes` → mọi `<id>.wav` + `<id>.raw.wav`, `align.json` (source `el`), `usage.json`; thiếu ký tự → mã 3, không có tệp mới; `--provider kokoro` thay giọng EL bằng Kokoro cùng giới/tuổi và ghi `speakers.json → fallback`; đổi chỉ `fx` → không gọi máy chủ giả
- [X] T010 [P] [US1] Test (đã gộp vào `tests/online/test_voicekeys.py`): PUT khoá đúng lưu và trả `last4`; khoá sai → 422 `elevenlabs_key_invalid`, không có tệp; GET không bao giờ chứa khoá; quyền tệp 0600, thư mục 0700; quét chuỗi khoá giả trong `$STUDIO_DATA` (trừ `secrets/`), nhật ký và phản hồi → 0 kết quả (SC-002); người không phải owner → 403
- [X] T011 [P] [US1] Test (đã gộp vào `tests/online/test_voicekeys.py`): `/internal/tts/elevenlabs/{subscription,voices,speak}` cần token việc; thêm `xi-api-key` từ kho bí mật; chưa có khoá → 409 `no_key`; 401 → 502 `invalid_key`; quota → 402; cộng `chars` vào `job.tts_chars`; nhật ký không có chữ câu; > 1000 ký tự → 400; tối đa 4 lời gọi song song mỗi việc

### Implementation

- [X] T012 [US1] Hoàn tất `tools/filmcheck/eleven.py`: `subscription()`, `voices(refresh)` (nhớ 10 phút), `speak(voice_id, text, model, settings) -> (pcm, alignment, chars)` theo research R1; chọn đường: proxy (`STUDIO_JOB_TOKEN`, `STUDIO_PROXY`) hoặc trực tiếp (`ELEVENLABS_API_KEY`, `ELEVENLABS_MODEL` mặc định `eleven_multilingual_v2`); không bao giờ in hoặc ghi khoá; gọi song song tối đa 4
- [X] T013 [US1] Thêm lệnh `eleven test` và `eleven voices [--json] [--refresh]` theo `contracts/cli.md` trong `tools/filmcheck/cli.py` và đăng ký trong `bin/studio`
- [X] T014 [US1] Sửa `cmd_voice_make` trong `tools/filmcheck/cli.py`: chia câu theo nhà cung cấp; Kokoro vẫn qua `tts.py` của thư viện (ghi `.raw.wav` rồi hậu kỳ); EL qua `eleven.speak`; ước tính ký tự (research R8) + `--yes`; thiếu ký tự → mã 3 không đọc dở; `--provider kokoro`; áp `voicefx` cho mọi câu; ghi `dur.json`, `align.json`, `usage.json`, `.made.json`; đổi chỉ `fx`/`pitch` dùng lại `.raw.wav`; giữ `STUDIO_TTS_FAKE`/`STUDIO_TTS_DRY`
- [X] T015 [US1] Thêm `voice usage <phim>` trong `tools/filmcheck/cli.py`
- [X] T016 [US1] Viết `tools/studio/studio/voicekeys.py`: Fernet, `$STUDIO_DATA/secrets/.key` + `elevenlabs.json` (0600, thư mục 0700); `save(key, model)` chỉ lưu khi Test thành công; `public()` trả `{set, last4, model, tier, left, limit, reset_at, checked_at, status}`; `secret()` chỉ cho proxy; loại `secrets/` khỏi `app import` và sao lưu
- [X] T017 [US1] Thêm route `GET/PUT/DELETE /api/settings/voice-provider`, `POST …/test`, `GET /api/voices`, `POST /api/films/{phim}/voice/estimate` theo `contracts/http.md` trong `tools/studio/studio/server.py` (và `api_online.py` nếu route online dùng chung); preview giọng EL được proxy lại không lộ khoá
- [X] T018 [US1] Thêm `/internal/tts/elevenlabs/{subscription,voices,speak}` trong `tools/runner/proxy.py` theo `contracts/http.md` (mẫu `/internal/web/fetch`), cộng `tts_chars` vào việc
- [X] T019 [US1] Sửa `tools/studio/studio/filmsteps.py::voices` dùng `voicecat.catalog` (gộp hai nhà cung cấp)
- [X] T020 [US1] Giao diện trong `tools/studio/studio/web/app.js` và `style.css`: Settings → "Voice provider" (ô khoá, Test, `••••last4`, gói, số còn lại, Replace/Remove, nhắc giấy phép thương mại theo gói); ô chọn giọng gộp có nhãn nhà cung cấp, `Cloned`, nút nghe thử; hộp xác nhận ký tự trước khi làm giọng EL; số ký tự đã dùng trên trang phim (FR-008)

**Checkpoint**: phim chỉ có người kể đọc được bằng ElevenLabs từ lệnh và từ app; khoá không lộ.

---

## Phase 4: User Story 2 - Người nói và giọng nhân vật (P2)

**Goal**: mỗi câu đọc bằng giọng của người nói; người kể của kênh; nhân vật giọng riêng hoặc người kể đóng vai; chọn và duyệt giọng (Voice cho phim page, Cast cho phim AE).
**Independent Test**: quickstart §3 bước 1, 2, 4 và §4.

### Tests

- [X] T021 [P] [US2] Test `tests/filmcheck/test_speakers.py`: thứ tự giải research R5 (`voice` ghi tay > `film.json → voices` / cast > kho > vai > lỗi); câu không `speaker` → người kể; `mode=narrator` lấy giọng người kể + pitch; phim cũ không có trường mới → mọi câu như trước; `speakers.json` đúng (SC-004); kênh chưa có người kể → lỗi "choose a narrator voice"

### Implementation

- [X] T022 [US2] Viết `tools/filmcheck/speakers.py`: `resolve(film_dir) -> {speaker: {source, role?, setting, lines}}` theo research R5 và data-model (VoiceSetting: `mode` `own|narrator`, `pitch` "−6…+6 (bán cung, 0,5 bước)", `speed` "0,7…1,2 (EL) / 0,5…2 (Kokoro)", `emotion` "`neutral`|`whisper`|`shout`|`laugh`|`cry`|`sarcastic`", `formant` mặc định `shifted` khi pitch > 0); ghi `voices/speakers.json`; `estimate_chars(lines)`
- [X] T023 [US2] Đọc/ghi giọng kênh `channels/<kênh>/VOICE.json` dưới gốc kênh của chế độ đang chạy (app: `store.root()`; lệnh: `STUDIO_ROOT`) với bộ mặc định research R6, trong `tools/filmcheck/speakers.py`; lệnh `voice channel <kênh> narrator|role …` trong `tools/filmcheck/cli.py`
- [X] T024 [US2] Nối `speakers.resolve` vào `cmd_voice_make` (T014): mỗi câu lấy giọng, tốc độ, cao độ, cảm xúc từ người nói; chặn khi kênh chưa có người kể (FR-011)
- [X] T025 [US2] Kiểm `lines.json` (làm ở `speakers.line_errors`, gọi từ `voice check`/`voice make`; `script check` chỉ đọc SCRIPT.md): `speaker` là `narrator` hoặc khớp `[a-z0-9-]{1,32}`; `role` ∈ `boy|girl|woman|man|old_man|old_woman`; `emotion`, `fx` thuộc tập cho phép
- [X] T026 [US2] Thao tác Voice trong `tools/filmcheck/edit.py`: đặt `film.json → voices.<speaker>` (phim page), đổi giọng người nói chỉ đánh dấu các câu của người đó (FR-042), đổi giọng người kể của kênh
- [X] T027 [US2] Khối `speakers` trong view phim (`tools/studio/studio/filmsteps.py`) và route `GET/PUT /api/v1/channels/{kênh}/voice` (`api_online.py`)
- [X] T028 [US2] Trang Voice trong `tools/studio/studio/web/app.js`: nhóm câu theo người nói, hiện thiết lập giọng mỗi người nói, đổi giọng người nói (phim page: chọn giọng nhân vật ở đây, FR-012); tóm tắt và ô chọn cùng một giọng người kể (FR-041); chọn giọng người kể khi kênh chưa có
- [X] T029 [US2] Lời dặn Claude trong `tools/runner/agent.py` và `.claude/skills/film-make/SKILL.md`: ghi `speaker` cho mọi câu thoại, `role` cho vai phụ, nhân vật chính kể ở ngôi "you" mà nói thành lời thì `speaker` là nhân vật chính; đề xuất 2–3 giọng (research R9) bằng Opus

### Cast (cần 034)

- [ ] T030 [US2] Thêm `voice`, `voice_options[]`, `speaks` vào nhân vật trong `tools/filmcheck/cast.py`; dấu nhân vật gồm `voice`; cổng: `speaks > 0` và `voice` null → không duyệt được, báo tên (FR-013)
- [ ] T031 [US2] Lưu `voice` vào `character.json` của kho trong `tools/filmcheck/castlib.py` (đổi giọng = bản `v<n+1>`); phim dùng lại nhân vật lấy giọng từ kho, không hỏi (FR-014); đổi người kể kênh → nhân vật `mode=narrator` của kênh "chờ duyệt lại giọng" (FR-016)
- [ ] T032 [US2] Lệnh `voice cast <phim> sample|set …` theo `contracts/cli.md` trong `tools/filmcheck/cli.py`; câu thử = câu thoại dài nhất ≤ 120 ký tự; báo ký tự trước
- [ ] T033 [US2] Phần Giọng ở khung Cast trong `tools/studio/studio/web/app.js`: 2–3 lựa chọn có lý do và nút nghe câu thật, chọn giọng khác ngoài đề xuất, chỉnh pitch/speed khi `mode=narrator`, xác nhận quyền khi chọn giọng nhân bản lần đầu (`cloned_ok`)
- [ ] T034 [P] [US2] Test cổng giọng ở Cast và kho trong `tests/filmcheck/test_cast_voice.py` (SC-005)

**Checkpoint**: phim có người kể và nhân vật đọc đúng giọng theo người nói.

---

## Phase 5: User Story 3 - Vai phụ và luật không trùng (P3)

**Goal**: vai phụ lấy giọng từ bộ theo vai (mặc định người kể đóng vai), giữ giọng suốt phim, không trùng trong cảnh.
**Independent Test**: quickstart §3 bước 2–3.

- [X] T035 [P] [US3] Test trong `tests/filmcheck/test_speakers.py`: 3 vai phụ cùng `para` → 3 khoá giọng khác nhau, không trùng người kể; vai phụ 2 câu ở 2 `para` một giọng; hết lựa chọn trong vai → người kể đóng vai lệch thêm ±1 bán cung; ép trùng → `voice check` mã 1 nêu tên và cảnh (SC-006)
- [X] T036 [US3] Gán vai phụ và khoá trùng `(provider, voice đã giải, round(pitch,1), round(speed,2))` trong `tools/filmcheck/speakers.py` (research R5)
- [X] T037 [US3] Lệnh `voice check <phim>` theo `contracts/cli.md` trong `tools/filmcheck/cli.py`; `voice make` gọi nó trước khi đọc
- [ ] T038 [US3] Đổi giọng vai phụ ở trang Voice (`web/app.js` + `edit.py`): chỉ đọc lại câu của vai đó; sửa bộ giọng theo vai trong hồ sơ kênh

---

## Phase 6: User Story 4 - Cảm xúc và hiệu ứng (P4)

**Goal**: cảm xúc chuyển cho ElevenLabs v3, hiệu ứng âm cho mọi nhà cung cấp.
**Independent Test**: quickstart §5.

- [ ] T039 [P] [US4] Test trong `tests/filmcheck/test_voice_make_providers.py`: `emotion: whisper` + `eleven_v3` → chữ gửi đi bắt đầu bằng `[whispers]`, chữ kịch bản không đổi, ký tự tính cả thẻ; mô hình khác / Kokoro → `emotion_applied: false` trong `speakers.json`; `fx: wall` qua kiểm lời giả
- [ ] T040 [US4] Chèn thẻ cảm xúc khi mô hình là `eleven_v3` trong `tools/filmcheck/eleven.py`; khi v3 không trả alignment thì dùng thời điểm Whisper và ghi `align.source: "asr"` (research R2)
- [ ] T041 [US4] Trang Voice: chọn cảm xúc và hiệu ứng mỗi câu, ghi "not applied with this voice" khi không hỗ trợ (FR-031) trong `tools/studio/studio/web/app.js` và `edit.py`

---

## Phase 7: Polish

- [ ] T042 [P] Test trình duyệt `tests/ui/browser_voice_cast.cjs`: Settings ô khoá, ô chọn giọng gộp, Voice nhóm theo người nói, tóm tắt khớp ô chọn (quickstart §6)
- [ ] T043 [P] Thêm lượt thật vào `tests/online/live.sh` (chỉ khi có `ELEVENLABS_API_KEY`): đọc 3 câu, so ước tính với chênh lệch `character_count` ≤ 1% (SC-003)
- [ ] T044 [P] Cập nhật tài liệu: `tools/CLAUDE.md` (eleven.py, voicecat, speakers, voicefx), mục giọng trong `.claude/skills/film-make/SKILL.md`, `CREDITS` nếu thêm gì bên thứ ba
- [ ] T045 Chạy đủ 5 bộ test (`sh tests/run.sh`, `sh tests/filmcheck/run.sh`, `sh tests/ui/run.sh`, `sh tests/online/run.sh`, `sh tests/render/run.sh`) và quickstart §1, §3, §5 (miễn phí); hỏi người dùng trước quickstart §2 (tốn ký tự)

---

## Dependencies & Execution Order

- Setup (T001–T002) → Foundational (T003–T007) → US1 (T008–T020) → US2 (T021–T029) → US3 (T035–T038) → US4 (T039–T041) → Polish.
- US2 phần Cast (T030–T034) chờ 034 merge; làm US3, US4 trước được.
- US3 dùng `speakers.py` của US2 (T022). US4 chỉ cần US1.
- Trong một story: test trước, rồi mô-đun lõi (`filmcheck`), rồi app/proxy, rồi giao diện.

## Parallel Opportunities

- T006, T007 song song sau T003/T004.
- US1: T008–T011 song song; T016 (voicekeys) và T018 (proxy) song song với T012–T015 (lệnh).
- US4 làm song song với US2/US3 sau US1.

## Implementation Strategy

- **MVP = Phase 1–3 (US1)**: ElevenLabs cho phim một người kể, đủ dùng ngay với `.env` đã có.
- Sau đó US2 (không Cast) + US3: phim nhiều giọng bằng `film.json → voices` và bộ theo vai.
- Cast (T030–T034) khi 034 xong; US4 cuối.
