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

## Kết quả T018 (2026-11-12, WSL2 Ubuntu của máy phát triển)

Chạy với kho tạm (`--data <thư mục tạm>`), vì kho mặc định đã có chủ xưởng từ trước.

| Bước | Kết quả |
|---|---|
| `app start` | Đạt: proxy, worker, web đều chạy; in `URL: http://127.0.0.1:8790`; cảnh báo Bash của agent chưa có sandbox (máy này không có `bwrap`) |
| Tạo chủ xưởng (`/api/v1/auth/setup`) | Đạt: trước đó `needed: true`, sau đó tài khoản admin được tạo và đăng nhập |
| `app import` | Đạt: chép 6 mục (2 phim, 1 phong cách, các README) vào kho của chủ xưởng |
| Trang phim | Đạt: danh sách có 2 phim, có video, poster, phụ đề; video phát được (206) |
| Trang phong cách | Đạt: hiện phong cách đã học |
| Trang kênh và đề | Đạt: tạo kênh thử, mở hồ sơ, hàng đợi đề, kênh mẫu (đều 200) |
| Việc làm bằng chat khi app chạy | Đạt: `job start` ghi vào sổ việc của app, `job fail` chuyển sang `failed` |
| `app status` / `app stop` | Đạt |
| `git status` của dự án | Sạch, app không ghi gì vào dự án |

Chưa làm (tốn tiền, chờ người dùng): đăng nhập tài khoản Claude thật ở AI accounts và giao một phim bằng form (khối Quality và Publish).
