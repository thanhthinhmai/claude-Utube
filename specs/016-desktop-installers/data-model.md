# Data Model: Bộ cài app desktop (016)

## core-manifest.json (đi kèm tệp phần lõi trong bộ cài)

```json
{"version": "0.1.0", "os": "linux-x64", "file": "claude-utube-core-linux-x64-0.1.0.tar.gz",
 "sha256": "…", "bytes": 1234567890, "unpacked_bytes": 4567890123, "lib_commit": "bebbbe1…",
 "built": "2026-11-11T12:00:00Z"}
```

## App config (015, thêm trường)

| Trường | Kiểu | Luật |
|---|---|---|
| `coreKind` | `packaged` \| `existing` | `packaged`: phần lõi đóng gói của 016; `existing`: bản studio có sẵn (015) |
| `coreVersion` | chuỗi hoặc null | phiên bản phần lõi đã cài (`packaged`) |
| `modelsReady` | bool | Kokoro, Whisper `base.en` và `base` đã tải xong |

Với `packaged`:
- Windows: `distro = "ClaudeUtube"`, `studio = "/home/studio/claude-Utube"`, `data = "/home/studio/.local/share/claude-utube"`.
- macOS: `studio = "~/Library/Application Support/ClaudeUtube/core-<ver>"`, `data` = mặc định của 014.

## Phần lõi đã cài

- Tệp `.core-version` trong thư mục studio, chứa phiên bản.
- macOS có thêm `env.sh`, gồm `PATH` với `node/bin` và `ffmpeg`, và `PLAYWRIGHT_BROWSERS_PATH`.
