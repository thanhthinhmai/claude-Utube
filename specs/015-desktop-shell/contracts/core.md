# Contract: app gọi phần lõi, và cầu nối của các trang

## Lệnh của phần lõi (014, R2 bổ sung)

| Lệnh | Dùng khi | Đầu ra app đọc |
|---|---|---|
| `app check --json` | thiết lập | `{"ok", "missing": [str], "data_default"}` |
| `app start --data D` | mở app, Khởi động lại | dòng `URL: http://127.0.0.1:<cổng>`; mã 0 là sẵn sàng |
| `app status --data D --json` | 10 giây một lần, trước khi thoát | Core status (data-model.md) |
| `app stop --data D [--force]` | thoát | mã 0 là đã dừng; mã 1 là còn việc (app luôn hỏi người dùng trước, rồi gọi `--force`) |

Windows: mọi lệnh chạy qua `wsl.exe -d <distro> --cd <studio> -- sh bin/studio …`. macOS: `/bin/sh <studio>/bin/studio …`.

## Cầu nối `preload.js` (chỉ cho `setup.html` và `stopped.html`)

| Hàm | Trả về |
|---|---|
| `setup.check()` | `{platform, checks: [Machine check], distros: [str], defaults: {studio, data}}` |
| `setup.enableWsl()` | `{ok, cancelled, rebootNeeded}`; hỏi xác nhận trước (R3) |
| `setup.chooseDistro(name)` | `{home, studioFound, studio}` |
| `setup.space(dir)` | `{freeGB}` |
| `setup.finish({distro, studio, data})` | `{ok, error}`; ghi cấu hình rồi khởi động phần lõi |
| `core.restart()` | `{ok, error}` (trang `stopped.html`) |

Cửa sổ chính (trang của xưởng) không có cầu nối nào.

## Dòng ghi của chế độ smoke (`--smoke`, GitHub Actions)

`smoke: window ok` · `smoke: second instance ok` · `smoke: quit ok`, rồi thoát mã 0. Lỗi thì in `smoke: fail <lý do>` và thoát mã 1.
