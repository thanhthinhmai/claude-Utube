# Contract: lệnh

Mọi lệnh qua `sh bin/studio`. Mã thoát: 0 xong, 1 bị cổng/kiểm chặn, 2 lỗi đầu vào, 3 lỗi nhà cung cấp (khoá, hết ký tự, mạng).

## `eleven test`
In `ok · tier <gói> · <còn>/<giới hạn> characters left · resets <ngày>` hoặc `✗ invalid key` / `✗ no key (set ELEVENLABS_API_KEY in .env or in the app's Settings)`. Không bao giờ in khoá.

## `eleven voices [--json] [--refresh]`
Danh sách giọng của tài khoản: `el:<id>  <tên>  <giới>/<tuổi>  <accent>  [cloned]`.

## `voice make <phim> [--only ids] [--changed] [--yes] [--provider kokoro]`
- Giải người nói → giọng (`speakers.json`), chạy `voice check`; lỗi thì dừng (mã 1).
- Câu ElevenLabs > 1: in `elevenlabs: <n> characters for <k> lines; <còn> left` và dừng nếu thiếu `--yes` (mã 1). Thiếu ký tự: `✗ not enough characters: need N, have M — use --provider kokoro for this film` (mã 3), không đọc câu nào.
- `--provider kokoro`: đọc cả phim bằng Kokoro, giọng ElevenLabs được thay bằng giọng Kokoro gần nhất (cùng giới/tuổi), ghi vào `speakers.json → fallback`.
- Đổi chỉ `fx`/`pitch`: dùng lại `<id>.raw.wav`, không gọi nhà cung cấp.
- Giữ các biến cũ: `STUDIO_TTS_FAKE`, `STUDIO_TTS_DRY`.

## `voice check <phim>`
In bảng người nói ↔ giọng và lỗi: người nói không giải được; hai người nói cùng `para` trùng giọng; nhân vật trùng người kể; giọng không còn trong tài khoản; giọng nhân bản chưa xác nhận quyền. Mã 1 nếu có lỗi.

## `voice cast <phim> sample <nhân vật> [--option n]`
Đọc câu thử cho các `voice_options` (hoặc một lựa chọn) → `cast/voices/<id>/<n>.wav`. Báo ký tự trước như `voice make`.

## `voice cast <phim> set <nhân vật> --option n | --voice <mã> [--pitch st] [--speed x] [--mode narrator|own]`
Ghi `characters[].voice`; nhân vật đã duyệt → `changed`.

## `voice channel <kênh> narrator --voice <mã> [--speed x]` · `voice channel <kênh> role <vai> …`
Ghi `voice.json` của kênh.

## `voice usage <phim>`
Tổng ký tự ElevenLabs đã dùng của phim và từng lượt.
