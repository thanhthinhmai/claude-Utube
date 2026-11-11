# Data Model: Vỏ app desktop (015)

## App config (`<userData>/config.json`; thư mục đổi được bằng `CU_CONFIG_DIR` khi test)

| Trường | Kiểu | Luật |
|---|---|---|
| `platform` | `win32` \| `darwin` | ghi lúc thiết lập |
| `distro` | chuỗi hoặc null | chỉ Windows: tên bản Linux WSL2 |
| `studio` | chuỗi | đường dẫn studio (Windows: đường dẫn Linux trong bản đó); có `bin/studio` |
| `data` | chuỗi | thư mục dữ liệu của phần lõi (Windows: đường dẫn Linux) |
| `home` | chuỗi hoặc null | `$HOME` trong bản Linux (Windows), dùng để thay `~` |
| `setupAt` | thời điểm ISO | |
| `trayNoticeShown` | bool | đã báo "xưởng vẫn chạy ở khay" chưa |

Cấu hình thiếu, hoặc `studio` không còn `bin/studio`, hoặc bản Linux không còn: hiện lại màn hình thiết lập (FR-008).

## Core status (từ `app status --json`, 014 cùng R2)

`{running, url, web, proxy, data, logs, parts, jobs_running, jobs_queued, jobs: [{id, name, status}]}`

## Machine check (màn hình thiết lập)

`[{id: "wsl"|"virtualization"|"distro"|"studio"|"tools"|"space", ok: bool, detail: str, fix: str|null}]`
