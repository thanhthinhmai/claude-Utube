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

## Kết quả chạy với khoá thật (2026-11-11)

Kênh thử `kenh-thu` (tiếng Anh, khoa học đời thường), 5 đề, tổng 1881 đơn vị YouTube trong ngày (1 đơn vị thử khoá).

- **Lần 1** (cách lấy số liệu cũ, 3 đề, 642 đơn vị): phát hiện lỗi thiết kế. Lượt tìm theo ngày đăng chỉ thấy 30 ngày gần nhất (`n60 = 0`, `r` khoảng 90); trung vị lượt xem 13–51 nên độ nóng bị trần 5; cạnh tranh đếm cả kênh không ai xem. Đã sửa (research.md, "Sửa sau bài chạy thật").
- **Lần 2** (cách mới, chấm lại 3 đề, 613 đơn vị, khoảng 204 mỗi đề nhờ một phần số liệu tạm):
  - why honey never spoils: HOLD 33 (demand 5, heat 8, competition 1, fit 9)
  - why do cats purr: HOLD 34 (5, 10, 1, 8)
  - how noise cancelling headphones work: HOLD 38 (8, 10, 1, 9)

  Cả ba là đề rất phổ biến: 72–77 kênh có video đáng kể trong 90 ngày, nên cạnh tranh ≤ 3 → HOLD.
- **Đề ngách** (2 đề, 625 đơn vị, khoảng 313 mỗi đề):
  - why does honey crystallize: **GO 34** (5, 6, 4, fit 9), 27 kênh cạnh tranh
  - how do bees make wax: HOLD 34 (7, 8, 2, 7)
- **Giới hạn thấy được:**
  - Bộ lọc "cùng đề" theo từ khoá vẫn để lọt video lạc đề có cùng từ (đề "how do bees make wax" có video bằng chứng là "bees wax squishies", 10,7 triệu lượt xem, làm điểm nhu cầu cao hơn thật).
  - Với kênh tiếng Anh, `regionCode=US` vẫn trả một số video tiếng khác (video bằng chứng của đề "cats purr" là video tiếng Tamil).
  - Mục "hợp kênh" do Claude chấm 7–9, hợp lý với ngách của kênh.
- Khoá không có trong đầu ra, `topics.json` hay `TOPICS.md` (đã tìm bằng `grep`).
