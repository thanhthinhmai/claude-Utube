# Quickstart: kiểm 036 đầu-cuối

## Chuẩn bị
- `.env` có `ELEVENLABS_API_KEY` (người dùng đã thêm). ffmpeg có `rubberband` (`ffmpeg -filters | grep rubberband`).
- Bộ test không tốn tiền: `sh tests/filmcheck/run.sh`, `sh tests/ui/run.sh`, `sh tests/online/run.sh`, `sh tests/run.sh`, `sh tests/render/run.sh` — đều phải qua (SC-008).

## 1. Khoá (US1) — không tốn ký tự
1. `sh bin/studio eleven test` → `ok · tier … · N characters left`.
2. `ELEVENLABS_API_KEY=sai sh bin/studio eleven test` → `✗ invalid key`, mã 3.
3. App: `sh bin/studio app start` → Settings → Voice provider: dán khoá, Test → thấy gói và số còn lại; mở lại chỉ thấy `••••abcd`.
4. Quét lộ khoá (SC-002): `grep -rF "$ELEVENLABS_API_KEY" ~/.local/share/claude-utube films/ tools/ specs/ --exclude-dir=secrets` → không có kết quả (test tự động `test_voicekeys_api.py` làm việc này với khoá giả).

## 2. Giọng ElevenLabs cho cả phim (US1) — **tốn ký tự, hỏi người dùng trước**
1. `sh bin/studio eleven voices` → có danh sách, giọng nhân bản có `[cloned]`.
2. Đặt người kể kênh: `sh bin/studio voice channel default narrator --voice el:<id>`.
3. `sh bin/studio voice make ae-sleepless-test` → in ước tính, dừng vì thiếu `--yes`.
4. `--yes` → đọc xong; `voices/align.json` có thời điểm từng ký tự; `voice asr` + kiểm lời qua; `voice usage` ≈ ước tính (lệch ≤ 1%, SC-003, so với `eleven test` trước/sau).

## 3. Người nói và luật không trùng (US2, US3) — Kokoro, miễn phí
1. Phim thử nhỏ `voice-cast-test`: người kể + `hero` (bé trai) + `mom` + 3 vai phụ cùng `para` + 1 vai phụ 2 câu ở 2 `para`.
2. `sh bin/studio voice check voice-cast-test` → bảng người nói; 3 vai phụ cùng cảnh có 3 khoá giọng khác nhau, không trùng người kể; vai phụ 2 câu một giọng.
3. Ép trùng (`"voice"` giống nhau cho 2 người cùng `para`) → `voice check` mã 1, nêu tên và cảnh (SC-006).
4. `voice make --provider kokoro` → mỗi câu đúng giọng theo `speakers.json` (SC-004); câu `hero` (người kể đóng vai +4) có cao độ trung vị cao hơn câu kể ≥ 20%.

## 4. Giọng ở bước Cast (US2, cần 034)
1. Phim AE có nhân vật có thoại → trang Cast có phần Giọng, 2–3 lựa chọn có lý do và nút nghe câu thật.
2. Duyệt khi chưa chọn giọng → bị từ chối, nêu tên nhân vật.
3. Chọn, duyệt → kho có `voice`; phim thứ hai dùng lại `mom` → không hỏi giọng (SC-005).

## 5. Cảm xúc và hiệu ứng (US4)
1. Câu `fx: wall` và `fx: phone`: nghe thấy lọc rõ; kiểm lời vẫn qua; đổi `fx` rồi `voice make --changed` không gọi nhà cung cấp (dùng `.raw.wav`).
2. Câu `emotion: whisper` với Kokoro → trang Voice ghi "not applied with this voice".
3. (Tuỳ chọn, tốn ký tự) với `ELEVENLABS_MODEL=eleven_v3`: câu thì thầm nghe nhỏ và có hơi thở.

## 6. Giao diện
- `node tests/ui/browser_voice_cast.cjs`: Settings ô khoá, ô chọn giọng gộp có nhãn nhà cung cấp, Voice nhóm theo người nói, tóm tắt và ô chọn cùng một giọng người kể (FR-041).
