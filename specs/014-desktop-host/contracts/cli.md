# Contract: lệnh `app` của `bin/studio`

| Lệnh | Việc | Mã thoát |
|---|---|---|
| `app start [--data D] [--web-port N] [--proxy-port N] [--foreground]` | kiểm công cụ, chạy giao diện, proxy và worker, rồi in `URL: http://127.0.0.1:<cổng>` khi đã sẵn sàng | 0 · 0 khi đang chạy rồi (in địa chỉ) · 2 khi thiếu công cụ, thư mục dữ liệu không dùng được, hay hết cổng trống · 1 khi không sẵn sàng sau 30 giây (in 20 dòng cuối của log) |
| `app status [--data D] [--json]` | in phần nào đang chạy, địa chỉ, thư mục dữ liệu, thư mục log, số việc đang chạy và trong hàng đợi | 0 khi đang chạy · 1 khi không chạy |
| `app stop [--data D] [--force]` | dừng sạch (R2) | 0 · 1 khi còn việc đang chạy và không có `--force` (in tên việc) |
| `app import [--from P] [--data D]` | chép `films/`, `my-styles/` và `channels/` của dự án vào kho của chủ xưởng | 0 · 2 khi chưa có chủ xưởng |

Luồng chat (`job …`, `review …`): khi `~/.config/claude-utube/host.json` trỏ tới một máy chủ đang chạy cho đúng thư mục dự án này, việc được ghi vào sổ việc của máy chủ đó, và dòng `URL:` của `job start` là địa chỉ trang việc trên app.
