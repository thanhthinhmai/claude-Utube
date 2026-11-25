# Research: Giọng theo nhân vật và giọng ElevenLabs

## R1. Gọi ElevenLabs thế nào

- **Decision**: ba lời gọi.
  - `GET /v1/user/subscription` → `tier`, `character_count`, `character_limit`, `next_character_count_reset_unix` (nút Test, số còn lại).
  - `GET /v2/voices?page_size=100` (lặp theo `next_page_token`) → `voice_id`, `name`, `category` (`premade`/`cloned`/`professional`/`generated`), `labels` (gender, age, accent, description, use_case), `preview_url`.
  - `POST /v1/text-to-speech/{voice_id}/with-timestamps?output_format=pcm_24000` với `{text, model_id, voice_settings:{stability, similarity_boost, style, speed, use_speaker_boost}}` → `audio_base64` + `alignment{characters, character_start_times_seconds, character_end_times_seconds}`.
- **Rationale**: `with-timestamps` cho thời điểm từng ký tự (FR-004); `pcm_24000` ra đúng 24 kHz mono như Kokoro nên các bước sau (dur.json, asr, mix) không đổi.
- **Alternatives**: WebSocket stream (phức tạp, không cần cho câu ngắn); mp3 (phải giải mã thêm).

## R2. Mô hình và cảm xúc

- **Decision**: mô hình theo `ELEVENLABS_MODEL` (lệnh) hoặc cài đặt app, mặc định `eleven_multilingual_v2`. Cảm xúc chỉ áp khi mô hình là `eleven_v3`: chèn thẻ âm thanh đầu câu (`[whispers]`, `[shouts]`, `[laughs]`, `[crying]`, `[sarcastic]`); thẻ được tính ký tự và không có trong chữ kịch bản. Với mô hình khác và với Kokoro: cảm xúc "không áp" và trang Voice ghi rõ (FR-031). "Thì thầm" và "hét" có thêm lùi nhẹ bằng hậu kỳ (giảm/tăng âm lượng) để luôn có khác biệt nghe được.
- **Rationale**: thẻ âm thanh là cách điều khiển cảm xúc chính thức của v3; v2 không có.
- **Cần đo khi làm**: `eleven_v3` có trả `alignment` qua `with-timestamps` hay không. Nếu không: dùng thời điểm của Whisper (`voice asr`) như hiện nay cho câu đó, ghi `align: "asr"`.

## R3. Khoá nằm đâu và ai dùng

- **Decision**:
  - App: `voicekeys.py` lưu `$STUDIO_DATA/secrets/elevenlabs.json = Fernet(key).encrypt({"key":…, "model":…})`, khoá Fernet ở `$STUDIO_DATA/secrets/.key`; cả thư mục 0700, tệp 0600. API trả về chỉ `last4`, `tier`, `left`, `checked_at`.
  - Việc (job) **không bao giờ** nhận khoá: `eleven.py` thấy `STUDIO_JOB_TOKEN` + `STUDIO_PROXY` thì gọi `POST {proxy}/internal/tts/elevenlabs/…`; proxy giải mã khoá, thêm `xi-api-key`, ghi số ký tự vào việc. Cùng mẫu với `/internal/web/fetch`.
  - Lệnh không app (chat làm phim): `eleven.py` đọc `ELEVENLABS_API_KEY`, `ELEVENLABS_MODEL` từ môi trường, nếu thiếu thì từ `.env` ở gốc dự án (trình đọc dòng `KEY=VALUE` nhỏ, không thêm thư viện). `TTS_PROVIDER` và `ELEVENLABS_CHUNK_CHARS` trong `.env` của người dùng: `TTS_PROVIDER=elevenlabs` làm Claude ưu tiên đề xuất giọng ElevenLabs; `CHUNK_CHARS` bỏ qua (mỗi câu một lời gọi, câu đã ngắn).
  - Client (018) gọi qua Host, khoá không rời Host.
- **Rationale**: mã hoá với khoá để cạnh chỉ chống lộ khi chép riêng tệp (sao lưu, `app import`, gửi nhầm); mức bảo vệ thật là quyền tệp và việc job không bao giờ thấy khoá, giống tài khoản Claude hiện nay.
- **Alternatives**: Electron `safeStorage` (DPAPI/Keychain): mạnh hơn nhưng proxy chạy trong WSL không đọc được; có thể làm sau. Biến môi trường của app: lộ vào mọi tiến trình con, kể cả job.

## R4. Mã giọng và danh mục

- **Decision**: mã giọng có tiền tố nhà cung cấp: `kokoro:am_michael`, `el:21m00Tcm4TlvDq8ikWAM`. Mã không tiền tố (phim cũ) = Kokoro. `voicecat.py` trả danh sách gộp `{id, provider, name, gender, age, accent, desc, cloned, preview}`; danh sách ElevenLabs nhớ 10 phút trong bộ nhớ, nút "Refresh". Câu nghe thử của Kokoro: tạo một lần từ câu mẫu cố định, lưu ở cache của app.
- **Rationale**: phim cũ chạy y như trước (SC-008); một chuỗi đủ để biết gọi nhánh nào.

## R5. Giải người nói → giọng

- **Decision**: thứ tự giải cho mỗi câu (`speakers.py`):
  1. `speaker` vắng hoặc `narrator` → giọng người kể của kênh (`voice.json → narrator`); phim không có kênh → `film.json → narrator` hoặc giọng mặc định cũ.
  2. `speaker` có trong `film.json → voices` (phim page / chưa có 034) → thiết lập đó; là nhân vật trong `cast/cast.json` → `characters[].voice` (đã duyệt) hoặc từ kho (`from_library`).
  3. `speaker` không có trong cast, có `role` → bộ giọng theo vai của kênh; vai phụ trong phim được gán cố định lần đầu và ghi vào `voices/speakers.json` (một vai phụ một giọng suốt phim, FR-021). Trong một vai có nhiều lựa chọn thì chọn lựa chọn đầu tiên chưa bị người nói khác dùng trong cùng `para`; hết lựa chọn thì người kể đóng vai với cao độ lệch thêm ±1 bán cung.
  4. Còn lại → lỗi kiểm, kèm tên người nói.
  - `voice` ghi tay trong câu (cách cũ) vẫn được tôn trọng và thắng mọi bước trên (để sửa nhanh một câu).
- **"Cảnh"** cho luật không trùng = `para` của câu (P01…), vì `para` là đơn vị cảnh của kịch bản và có sẵn trong mọi phim.
- **Trùng** = cùng `(provider, voice, round(pitch,1), round(speed,2))`; người kể không chỉnh (`pitch=0, speed=1`) trùng với người kể.

## R6. Người kể đóng vai: cao độ

- **Decision**: cao độ tính bằng bán cung (−6…+6). Áp sau khi đọc: `ffmpeg -af rubberband=pitch=2^(st/12):formant=shifted` khi ffmpeg có rubberband (có trên máy này), không thì `asetrate=sr*r,aresample=sr,atempo=1/r`. `formant=shifted` để giọng trẻ con nghe nhỏ người thật hơn; `formant: "preserved"` chọn được cho người lớn. Tốc độ đi vào nhà cung cấp (ElevenLabs `speed` 0,7–1,2; Kokoro `speed`).
- **Kiểm**: cao độ trung vị (tự tương quan như phép đo video mẫu) của câu đóng vai +4 cao hơn câu kể ≥ 20% (spec US2-6); Whisper vẫn đọc đúng chữ.
- **Mức sẵn theo vai** (bộ mặc định): bé trai +4/1,08×, bé gái +5/1,08×, phụ nữ +3/1,0×, đàn ông −2/0,95×, ông già −3/0,9×, bà già +2/0,9×.

## R7. Hiệu ứng âm

- **Decision** (ffmpeg, sau cao độ):
  - `phone`: `highpass=f=300,lowpass=f=3400,acompressor=ratio=4,volume=1.2`
  - `wall`: `lowpass=f=700,volume=0.45,aecho=0.6:0.4:25:0.25`
  - `radio`: `highpass=f=500,lowpass=f=4000,acrusher=bits=10:mix=0.25`
  - `hall`: `aecho=0.8:0.7:60|120:0.35|0.2`
  - Thời lượng giữ nguyên (aecho cắt đuôi về độ dài gốc + 0,15 s) để `dur.json` và khớp hình không lệch.
- **Rationale**: chạy được với mọi nhà cung cấp (FR-032), không thêm phụ thuộc.

## R8. Ước tính và đếm ký tự

- **Decision**: ước tính = tổng `len(chữ gửi đi)` (chữ `say` hoặc `text`, cộng thẻ cảm xúc) của các câu ElevenLabs sẽ đọc. Số thực tính: đọc `character_count` trước và sau lượt (lệnh), hoặc header số ký tự của phản hồi nếu có; proxy cộng vào `usage` của việc. `voices/usage.json` ghi theo phim `{total, runs:[{at, chars, lines}]}`. Hỏi xác nhận khi > 1 câu: lệnh in ước tính và cần `--yes`; trong app, bước Voice hiện hộp xác nhận trước khi tạo việc.
- **Kiểm SC-003**: test live so ước tính với chênh lệch `character_count`.

## R9. Đề xuất giọng của Claude

- **Decision**: Claude của việc làm phim (Opus) đọc mô tả nhân vật (034: `name`, `role`, tuổi/giới/tính cách trong BRIEF) và danh mục `voicecat` (đã lọc theo giới và tuổi), ghi 2–3 lựa chọn vào `cast/cast.json → characters[].voice_options[]` gồm `{setting, why, sample_line}`. Xưởng đọc thử mỗi lựa chọn bằng `voice cast sample` (một câu, ghi vào `cast/voices/<id>/<n>.wav`). Câu đọc thử là câu thoại dài nhất của nhân vật (≤ 120 ký tự). Với ElevenLabs, đọc thử tính ký tự và được báo tổng trước.

## R10. Cổng và đánh dấu chạy lại

- **Decision**: cổng Cast của 034 thêm điều kiện: nhân vật có ít nhất một câu thoại (`speaker` = id) phải có `voice` đã chọn. Dấu (fingerprint) của nhân vật gồm `voice`; đổi giọng nhân vật đã duyệt → `changed`. Điểm Voice: `.made.json` thêm `provider`, `pitch`, `fx`, `emotion`, `model` vào khoá câu; `--changed` vì thế chỉ đọc lại các câu bị ảnh hưởng (FR-042). Đổi giọng người kể của kênh → mọi nhân vật "người kể đóng vai" của kênh về `changed` ở kho (FR-016).
