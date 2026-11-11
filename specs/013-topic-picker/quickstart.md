# Quickstart: kiểm chứng chọn đề (013)

## 1. Test tự động (không tốn tiền, không cần mạng)

```bash
sh tests/filmcheck/run.sh    # test_topics: bảng điểm trên số liệu mẫu (SC-001), hàng đợi và luật lấy đề (SC-003), đếm đơn vị (SC-002), giấu khoá (SC-004)
sh tests/online/run.sh       # test_topics_api: việc topics với YouTube giả, giới hạn đề mỗi ngày, quyền (SC-006), proxy /internal/youtube
sh tests/run.sh; sh tests/learn/run.sh; sh tests/ui/run.sh
```

## 2. Local với khoá thật (tốn hạn mức YouTube miễn phí, không tốn tiền Claude trừ khi có mục "hợp kênh")

Tạo khoá YouTube Data API v3 trong Google Cloud Console (người dùng tự làm). Sau đó:

```bash
sh bin/studio config youtube-key          # tự gõ hoặc dán khoá vào terminal của bạn, không dán vào chat
sh bin/studio topics score <kênh> "why honey never spoils" "honey vs sugar" "how bees make honey"
sh bin/studio topics queue <kênh>
sh bin/studio topics usage                 # ~3 × 214 đơn vị
sh bin/studio topics take <kênh>
```

Kết quả cần thấy:
- Mỗi đề có 5 điểm và kết luận, kèm một video bằng chứng mở được.
- Chạy `score` lại cùng các đề trong 24 giờ: `usage` không tăng.
- Tìm khoá trong repo bằng `grep -r` (kể cả `.studio/`): không thấy.

## 3. Online

1. Settings → General: dán khoá YouTube; thấy "Key set (…abcd)".
2. Trang một kênh → Topics: dán 3 đề, chọn "Suggest", bấm Score.
3. Việc `topics` xong: bảng điểm và hàng đợi hiện ra.
4. Bấm "Make a film" trên đề đầu hàng đợi: form giao phim có sẵn kênh và ý tưởng.
