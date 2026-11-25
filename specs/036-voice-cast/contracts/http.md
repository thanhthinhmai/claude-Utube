# Contract: HTTP

## App (studio server, chủ xưởng đã đăng nhập; Client đi qua Host)

| Route | Vào | Ra |
|---|---|---|
| `GET /api/v1/admin/settings` | — | thêm `elevenlabs: {set, last4, model, tier, left, limit, reset_at, checked_at, status: none\|ok\|invalid\|quota}` |
| `PUT /api/v1/admin/elevenlabs-key` | `{key, model?}` | Test trước; 200 + phần công khai khi hợp lệ; 422 `elevenlabs_key_invalid` và **không lưu** khi sai |
| `POST /api/v1/admin/elevenlabs-key/test` | — | phần công khai mới |
| `PUT /api/v1/admin/elevenlabs-model` | `{model}` | phần công khai mới |
| `DELETE /api/v1/admin/elevenlabs-key` | — | 204 |
| `GET /api/voices?refresh=1` | — | `[{id, provider, name, gender, age, accent, desc, cloned, preview}]` (preview của EL được proxy lại, không lộ khoá) |
| `GET/PUT /api/channels/{kênh}/voice` | ChannelVoice | ChannelVoice |
| `POST /api/films/{phim}/voice/estimate` | `{only?}` | `{chars, lines, left}` |

- Khoá không bao giờ có trong phản hồi, nhật ký truy cập, thông báo lỗi. Chỉ vai owner được ghi.
- US1 đã làm: view của phim thêm `voice_rows` (danh mục gộp hai nguồn) và `voice_cost: {chars, lines, used}`; `voices` gồm cả mã `el:`.
- View của phim (`filmsteps`, US2+) thêm `speakers: [{id, name, source, setting, lines, issues}]` và `voices` gộp.

## Proxy (job → proxy, bằng `STUDIO_JOB_TOKEN`)

| Route | Vào | Ra |
|---|---|---|
| `POST /internal/tts/elevenlabs/subscription` | — | `{tier, left, limit, reset_at}` |
| `POST /internal/tts/elevenlabs/voices` | `{refresh?}` | như `/api/voices` (chỉ phần EL) |
| `POST /internal/tts/elevenlabs/speak` | `{voice_id, text, model_id?, voice_settings}` | `{audio_base64, alignment, chars}` |

- Proxy thêm `xi-api-key` từ kho bí mật; chưa có khoá → 409 `{error:"no_key"}`; 401 từ EL → 502 `{error:"invalid_key"}`; 401 `quota_exceeded` → 402 `{error:"quota"}`.
- Mỗi `speak` cộng `chars` vào việc (`job.tts_chars`) và ghi một dòng nhật ký chỉ có số ký tự và mã giọng, không có chữ câu.
- Giới hạn: tối đa 4 lời gọi song song mỗi việc; câu > 1000 ký tự bị từ chối (400).
