# Data Model: Chế độ máy chủ trên một máy (014)

## Thư mục dữ liệu

| Đường dẫn | Nội dung |
|---|---|
| `studio.db` | cơ sở dữ liệu của bản online (cùng khuôn dạng với VPS) |
| `accounts/<id>/` | `films/`, `my-styles/`, `channels/`, `references/` của từng người |
| `secrets/` | khoá YouTube, đăng nhập Claude (`claude/slot-<n>`), quyền 700 |
| `jobs/<id>/` | thư mục làm việc của từng việc |
| `logs/web.log` · `proxy.log` · `worker.log` · `host.log` | log xoay vòng (10 MB × 5) |
| `backup/studio-<phiên bản>-<thời điểm>.db` | bản sao trước mỗi lần nâng cấp dữ liệu |
| `host.lock` | khoá chống chạy trùng (flock) |
| `host.json` | phiên đang chạy |

## Host session (`host.json`, và con trỏ `~/.config/claude-utube/host.json`)

```json
{"pid": 12345, "data": "/home/u/.local/share/claude-utube", "project": "/home/u/claude-Utube",
 "web": 8790, "proxy": 8780, "started": "2026-11-11T10:00:00Z",
 "children": {"web": 12350, "proxy": 12351, "worker": 12352}, "error": null}
```

## Job (thêm, chỉ cho việc của luồng chat)

`source: "chat"`, không có `charged`, `owner` = id của chủ xưởng. Worker không chạy, không hồi phục các việc này.
