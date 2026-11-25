# Implementation Plan: Giọng theo nhân vật và giọng ElevenLabs

**Branch**: `036-voice-cast` | **Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/036-voice-cast/spec.md`

## Summary

Thêm nhà cung cấp giọng **ElevenLabs** bên cạnh Kokoro và cho mỗi câu một **người nói**. `lines.json` thêm `speaker`, `role`, `emotion`, `fx`; giọng của câu không ghi tay nữa mà được **giải** từ người nói: người kể → giọng người kể của kênh; nhân vật → thiết lập giọng trong `cast/cast.json` (034) hoặc kho nhân vật; vai phụ → bộ giọng theo vai của kênh. Một thiết lập giọng là `giọng riêng` hoặc `người kể đóng vai` (giọng người kể + cao độ, tốc độ, cảm xúc). `voice make` chia câu theo nhà cung cấp: Kokoro vẫn qua `tts.py` của thư viện (đã hỗ trợ mỗi câu một giọng), ElevenLabs qua mô-đun mới gọi API có thời điểm từng ký tự; sau đó xưởng áp cao độ và hiệu ứng âm bằng ffmpeg. Khoá ElevenLabs: trong app nằm ở kho bí mật của chủ xưởng và **chỉ proxy** dùng (việc gọi `/internal/tts/…` bằng token việc, giống `web fetch`); chạy bằng lệnh thì đọc `.env`. Trang Settings có ô khoá, nút Test; ô chọn giọng gộp hai nhà cung cấp; trang Voice nhóm câu theo người nói; bước Cast thêm phần Giọng.

## Technical Context

**Language/Version**: Python 3.11+ (filmcheck, studio, runner), JavaScript trình duyệt (web/app.js, không framework)

**Primary Dependencies**: httpx (sẵn có trong proxy), urllib (phía lệnh, như `web fetch`), cryptography/Fernet (sẵn có, 50.0.2) để mã hoá khoá, ffmpeg có `rubberband` (sẵn có; thiếu thì lùi về `asetrate+atempo`), API ElevenLabs (`/v1/user/subscription`, `/v2/voices`, `/v1/text-to-speech/{id}/with-timestamps`)

**Storage**: khoá: `$STUDIO_DATA/secrets/elevenlabs.json` (Fernet, 0600) + `$STUDIO_DATA/secrets/.key` (0600); lệnh không app: `.env` ở gốc dự án. Giọng của kênh: `<owner>/channels/<kênh>/voice.json` (cạnh kho nhân vật của 034). Giọng nhân vật: trường `voice` trong `cast/cast.json` và `character.json` của kho. Âm thanh: `films/<phim>/voices/` như cũ, thêm `align.json`, `.made.json` mở rộng, `usage.json`

**Testing**: unittest (`sh tests/filmcheck/run.sh`, `sh tests/ui/run.sh`, `sh tests/online/run.sh`, `sh tests/run.sh`, `sh tests/render/run.sh`); ElevenLabs giả (`STUDIO_TTS_FAKE`, máy chủ giả trong test proxy); một lượt thật tốn tiền trong `tests/online/live.sh` (chỉ chạy khi người dùng đồng ý)

**Target Platform**: WSL2/Linux và macOS (phần lõi), app desktop qua `bin/studio app`

**Project Type**: công cụ CLI + app web cục bộ + worker/proxy (mở rộng xưởng hiện có)

**Performance Goals**: làm giọng phim 30 câu bằng ElevenLabs ≤ 2 phút (gọi song song tối đa 4 câu); ô chọn giọng mở ≤ 1 s (danh sách giọng nhớ 10 phút)

**Constraints**: không sửa `lib/`; khoá không vào job, nhật ký, tệp phim, repo, máy Client; mọi lần gọi Claude dùng Opus; một nhân vật không bao giờ có hai nhà cung cấp trong một phim

**Scale/Scope**: ≤ 200 câu mỗi phim, ≤ 10 người nói có tên, ≤ 6 vai phụ, một chủ xưởng, một khoá

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá |
|---|---|
| I. Spec là nguồn sự thật | Đạt. Spec đã làm rõ 3 câu (phiên 2026-11-25). |
| II. Không đoán | Đạt. Không còn `NEEDS CLARIFICATION`; chỗ chưa chắc về API (thẻ cảm xúc của eleven_v3, header số ký tự) có phương án đo và lùi ở research.md. |
| III. MVP theo story | Đạt. P1 = US1 (khoá + giọng ElevenLabs cho cả phim) chạy được không cần 034; US2–US4 làm sau, US2 cần 034. |
| IV. Đo được | Đạt. Giải giọng, luật không trùng, ước tính ký tự, khoá không lộ (quét chuỗi) có test tự động; cao độ đóng vai đo bằng cao độ trung vị; một lượt ElevenLabs thật trong quickstart. |
| V. Đơn giản | Đạt. Không thêm lớp nhà cung cấp tổng quát: hai nhánh `kokoro` / `el`, tiền tố trong mã giọng. Dùng lại đường proxy `/internal/*` và Fernet sẵn có. |
| VI. Thư viện giữ nguyên | Đạt. `tts.py` và `asr_check.py` được gọi như cũ; ElevenLabs và hậu kỳ nằm trong `tools/filmcheck/`. |
| VII. Hai bộ máy dựng | Đạt. Giọng chung cho cả hai bộ máy; phim page chọn giọng nhân vật ở Voice, phim AE ở Cast. |
| IX. Spec-kit cho phần mềm | Đạt. Không có spec cho từng phim; skill `film-make` được cập nhật cách ghi `speaker`. |
| Bản quyền | Đạt. Giọng nhân bản phải xác nhận quyền khi dùng lần đầu; audio video tham chiếu chỉ đo trên máy, không gửi đi. Không commit khoá (`.env` đã trong `.gitignore`). |

**Re-check sau Phase 1**: vẫn đạt. Thiết kế thêm 4 mô-đun nhỏ trong `filmcheck`, 1 mô-đun trong `studio`, sửa proxy theo mẫu sẵn có; không có ngoại lệ cần ghi ở Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/036-voice-cast/
├── spec.md
├── plan.md              # tệp này
├── research.md          # R1–R10
├── data-model.md        # thiết lập giọng, câu, giọng kênh, khoá
├── quickstart.md        # kiểm thử đầu-cuối, có một lượt ElevenLabs thật
├── contracts/
│   ├── files.md         # lines.json mở rộng, voice.json của kênh, voice trong cast, voices/*
│   ├── cli.md           # lệnh voice …, eleven …
│   └── http.md          # API app (Settings, danh sách giọng) và proxy /internal/tts/*
└── checklists/requirements.md
```

### Source Code (repository root)

```text
tools/filmcheck/
├── eleven.py            # MỚI: client ElevenLabs (trực tiếp từ .env, hoặc qua proxy bằng token việc); subscription, voices, speak
├── voicecat.py          # MỚI: danh mục giọng hai nhà cung cấp (thay filmsteps.voices), mã "kokoro:af_bella" / "el:<id>"
├── speakers.py          # MỚI: giải người nói → thiết lập giọng; luật không trùng; ước tính ký tự
├── voicefx.py           # MỚI: cao độ (rubberband/asetrate) và hiệu ứng (phone, wall, radio, hall) bằng ffmpeg
├── cli.py               # (sửa) voice make chia nhà cung cấp, áp hậu kỳ, hỏi xác nhận ký tự; voice cast/check/usage; eleven test/voices
├── cast.py, castlib.py  # (sửa, của 034) trường voice; cổng "nhân vật có thoại phải có giọng"
├── edit.py              # (sửa) thao tác Voice: đổi giọng người nói, emotion, fx
└── script.py            # (sửa) kiểm lines.json: speaker/role/emotion/fx hợp lệ
tools/studio/studio/
├── voicekeys.py         # MỚI: lưu/đọc/xoá khoá (Fernet), Test (gọi subscription), 4 ký tự cuối
├── server.py, api_online.py   # (sửa) route Settings → Voice provider; /api/voices; giọng kênh
├── filmsteps.py         # (sửa) voices() gộp hai nhà cung cấp; khối speakers trong view
└── web/app.js, style.css      # (sửa) Settings ô khoá; ô chọn giọng gộp; Voice nhóm theo người nói; phần Giọng ở Cast
tools/runner/
├── proxy.py             # (sửa) /internal/tts/elevenlabs/{subscription,voices,speak}: thêm xi-api-key, ghi số ký tự theo việc
└── agent.py             # (sửa) lời dặn Claude: ghi speaker/role/emotion/fx khi viết kịch bản; đề xuất giọng ở Cast
.claude/skills/film-make/SKILL.md   # (sửa) bước giọng: speaker, giọng kênh, ElevenLabs, chi phí
tests/filmcheck/test_speakers.py, test_voicefx.py, test_eleven.py, test_voice_make_providers.py
tests/ui/test_voicekeys_api.py, browser_voice_cast.cjs
tests/online/test_proxy_tts.py
```

**Structure Decision**: mở rộng các thư mục sẵn có; mỗi phần mới một mô-đun nhỏ cạnh mô-đun cùng loại. Không chạm `lib/`.

## Complexity Tracking

Không có vi phạm hiến pháp cần biện minh.
