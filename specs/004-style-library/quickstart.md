# Quickstart: kiểm tra thư viện trên Film Studio

## Tự động

```sh
sh tests/run.sh          # setup: máy mới có poster, máy cũ nhận poster, lỗi tải poster, status đếm poster
sh tests/ui/run.sh       # API /library…, tên lạ bị từ chối, OpenAPI khớp contract, trình duyệt (nếu có)
```

## Bằng tay (máy người dùng, WSL)

1. Máy đã `setup` trước đây:
   ```sh
   git pull && sh bin/studio setup
   ```
   Mong đợi: `↓ đang tải poster…` rồi `✓ đã có poster: 66/66`, không tải lại thư viện (FR-002).
2. `sh bin/studio status` → `poster: 66/66`. `git -C lib/lemo-opuscar status --short` không in gì (SC-007).
3. `sh bin/studio ui`, mở URL, bấm **Library**:
   - 66 thẻ, mỗi thẻ có poster (SC-001). Trang hiện xong < 2 s (SC-003, đo bằng tab Network/Performance của trình duyệt).
   - Bấm giờ: từ lúc mở trang tới lúc mở được Art Deco bằng ô tìm ≤ 10 s (SC-002).
   - Chọn nhóm "Hand-drawn & Painting" → 8 thẻ. Gõ `deco` → Art Deco. Tải lại trang → vẫn đúng bộ lọc (FR-008).
   - Bấm Art Deco → luật đầy đủ, link GitHub mở đúng thư mục ở commit `bebbbe1`.
   - Bấm **Use this style** → "Copied"; dán vào Claude Code thấy `Make a 40-second film in the Art Deco style about …` (SC-004).
4. Bấm **My styles** → chỉ có Quiet Night; "based on scifi-toon" mở trang scifi-toon trong Library; **Use this style** chép câu lệnh có "Quiet Night".
5. Thử tên lạ: mở `http://localhost:<cổng>/api/v1/library/styles/..%2f..%2fCLAUDE.md/poster` → `400` hoặc `404`, không có nội dung file (SC-006).
