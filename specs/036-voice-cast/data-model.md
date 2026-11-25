# Data Model: Giọng theo nhân vật và giọng ElevenLabs

Định dạng tệp đầy đủ ở [contracts/files.md](contracts/files.md).

## VoiceSetting (thiết lập giọng)

| Trường | Kiểu | Luật |
|---|---|---|
| `mode` | `own` \| `narrator` | `narrator` = người kể đóng vai: `voice` lấy từ người kể của kênh lúc giải, không lưu |
| `voice` | mã giọng `kokoro:<tên>` \| `el:<id>` | bắt buộc khi `mode=own`; mã không tiền tố = Kokoro |
| `pitch` | số −6…+6 (bán cung, 0,5 bước) | mặc định 0 |
| `formant` | `shifted` \| `preserved` | mặc định `shifted` khi pitch > 0, ngược lại `preserved` |
| `speed` | 0,7…1,2 (EL) / 0,5…2 (Kokoro) | mặc định 1 |
| `emotion` | `neutral` \| `whisper` \| `shout` \| `laugh` \| `cry` \| `sarcastic` | mặc định của người nói; câu ghi đè được |
| `el` | `{stability, similarity_boost, style}` 0…1 | chỉ khi giọng là `el:` |
| `cloned_ok` | `{at, by}` \| null | bắt buộc khi giọng nhân bản (FR edge: xác nhận quyền) |

**Khoá trùng** (luật không trùng): `(provider, voice đã giải, round(pitch,1), round(speed,2))`.

## Line (mở rộng `lines.json`)

| Trường mới | Kiểu | Luật |
|---|---|---|
| `speaker` | id nhân vật \| `narrator` \| vắng | vắng = người kể |
| `role` | `boy` \| `girl` \| `woman` \| `man` \| `old_man` \| `old_woman` | bắt buộc khi `speaker` không có trong cast và không phải người kể |
| `emotion` | như trên | ghi đè cảm xúc mặc định |
| `fx` | `none` \| `phone` \| `wall` \| `radio` \| `hall` | mặc định `none` |
| `voice`, `speed` | (cũ) | còn dùng được; ghi tay thì thắng phần giải |

`para` (sẵn có) là đơn vị **cảnh** cho luật không trùng.

## ChannelVoice (`<owner>/channels/<kênh>/voice.json`)

- `narrator`: VoiceSetting (`mode=own`), `approved {at, by}`.
- `roles`: `{boy|girl|woman|man|old_man|old_woman: [VoiceSetting…]}`; mặc định mỗi vai một `mode=narrator` với mức chỉnh ở research R6.
- Đổi `narrator` → mọi nhân vật `mode=narrator` của kênh trong kho thành "chờ duyệt lại giọng".

## Character (mở rộng 034)

- Trong phim `cast/cast.json → characters[]`: thêm `voice` (VoiceSetting | null), `voice_options[]` (`{setting, why, sample_line, sample}`), `speaks` (số câu thoại, tính từ `lines.json`).
- Dấu nhân vật thêm `voice`. Luật: `speaks > 0` và `voice` null → không duyệt được.
- Trong kho `character.json`: thêm `voice`. Bản kho bất biến (034 FR-017): đổi giọng = bản `v<n+1>`.

## Film voices (phim không có `cast/cast.json`: phim page, hoặc trước khi 034 xong)

- `film.json → voices: {<speaker>: VoiceSetting}`; chọn ở bước Voice (FR-012). Khi phim có `cast/cast.json`, `characters[].voice` thắng.

## FilmSpeakers (`films/<phim>/voices/speakers.json`, sinh ra)

- `{<speaker>: {source: narrator|cast|library|role|manual, role?, setting (đã giải, có voice thật), lines:[ids]}}` — bảng người nói ↔ giọng để kiểm SC-004 và để vai phụ giữ giọng suốt phim.

## VoiceProviderKey (app)

- `$STUDIO_DATA/secrets/elevenlabs.json` (Fernet): `{key, model, saved_at, saved_by}`; phần công khai: `{set, last4, model, tier, left, limit, reset_at, checked_at, error?}`.
- Trạng thái: `none` → `ok` (Test thành công) → `invalid` (401) | `quota` (hết ký tự). Lưu chỉ khi Test thành công.

## Usage (`films/<phim>/voices/usage.json`)

- `{provider: "elevenlabs", total, runs:[{at, chars_estimated, chars, lines:[ids], job?}]}`.

## .made.json (mở rộng)

- Khoá câu: `{text, provider, voice, speed, pitch, formant, emotion, fx, model}`; khác → câu thuộc `--changed`.
