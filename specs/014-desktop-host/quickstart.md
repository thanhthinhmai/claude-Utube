# Quickstart: kiểm chứng chế độ máy chủ (014)

## 1. Test tự động

```bash
sh tests/online/run.sh      # test_host: khởi động và dừng, chạy trùng, dừng khi có việc, hồi phục, nhập, luồng chat, thư mục dự án không đổi
sh tests/run.sh; sh tests/learn/run.sh; sh tests/ui/run.sh; sh tests/filmcheck/run.sh
```

## 2. Trên máy thật (không cần Docker)

```bash
sh bin/studio deps ui && sh bin/studio deps online     # nếu chưa có
sh bin/studio app start                                # in URL: http://127.0.0.1:8790
# mở URL → tạo chủ xưởng → Settings › AI accounts: đăng nhập Claude của bạn → New film
sh bin/studio app import                               # mang phim, phong cách, kênh cũ vào app
sh bin/studio app status
sh bin/studio app stop
```

Kết quả cần thấy:
- Phim làm bằng form hiện khối Quality và Publish.
- Phim làm bằng chat trong VS Code (khi app đang chạy) hiện trong danh sách việc của app.
- `git status` của dự án không có thay đổi do app.
