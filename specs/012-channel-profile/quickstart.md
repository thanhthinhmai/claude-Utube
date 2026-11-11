# Quickstart: kiểm chứng hồ sơ kênh và bài học (012)

## 1. Test tự động (không tốn tiền)

```bash
sh tests/filmcheck/run.sh      # test_channels: hồ sơ, bài học, bản chụp, mọi luật kênh và bài học (SC-002, SC-003)
sh tests/online/run.sh         # test_channels_api (quyền, SC-005), việc có kênh, nháp bài học sau khi sửa phim
sh tests/run.sh; sh tests/learn/run.sh; sh tests/ui/run.sh
```

Kết quả cần thấy:
- Phim mẫu đạt: 0 vi phạm. Mỗi phim mẫu cố ý vi phạm trượt đúng một mã.
- Mọi lỗi `lesson_rule` có số bài học.
- Test của 010 và 011 không phải sửa (SC-006).

## 2. Local: một kênh, một phim, một bài học

```bash
sh bin/studio channel new khoa-hoc-vui --name "Khoa học vui" --language vi --seconds 45 --style dark-keynote --voice af_bella
sh bin/studio channel set khoa-hoc-vui hashtags "#khoahoc"
sh bin/studio channel set khoa-hoc-vui banned "sốc"
sh bin/studio lesson add khoa-hoc-vui --what "Tiêu đề câu view" --why "Chưa có luật" --stop "Không dùng 'không thể tin'" --rule "phrase:không thể tin"
cat channels/khoa-hoc-vui/CHANNEL.md channels/khoa-hoc-vui/LESSONS.md
# trong khung chat: "làm phim cho kênh khoa-hoc-vui: <ý tưởng>"
#   Claude chạy: sh bin/studio channel attach <phim> khoa-hoc-vui, rồi đọc films/<phim>/CHANNEL_BRIEF.md
```

Kết quả cần thấy:
- Kịch bản tiếng Việt, mục tiêu 45 giây.
- `script check` trượt `banned_word` nếu lời đọc có "sốc", và trượt `lesson_rule #1` nếu có "không thể tin".
- Gói đăng có `#khoahoc`.

## 3. Online: trang Channels

Mở giao diện online, vào Channels:
- Tạo kênh, thêm 2 bài học, bỏ 1 bài.
- Giao phim, chọn kênh: phong cách và độ dài được điền sẵn.
- Đăng nhập bằng một người khác: không thấy kênh.
- Yêu cầu sửa phim với "Save this as a lesson": sau khi việc xong, trang kênh có một bài học nháp. Duyệt bài học đó.

## 4. Bài chạy thật (tốn tiền, hỏi người dùng trước)

Làm một phim online cho một kênh. Đo phần token thêm của `CHANNEL_BRIEF.md` (SC-004): số ký tự ÷ 4 × số lượt của agent, so với tổng token của việc. Mức cho phép ≤ 2%.
