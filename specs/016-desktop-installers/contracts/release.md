# Contract: tệp phát hành và các bước cài trong app

## Tệp của một bản phát hành `desktop-vX.Y.Z` (GitHub Release riêng tư)

| Tệp | Nội dung |
|---|---|
| `claude-Utube-Setup-X.Y.Z.exe` | bộ cài Windows (NSIS, cho riêng người dùng, chưa ký số), chứa `core/claude-utube-core-linux-x64-X.Y.Z.tar.gz` và `core/core-manifest.json` |
| `claude-Utube-X.Y.Z-arm64.dmg` | macOS chip Apple (ký ad-hoc), chứa `core/claude-utube-core-darwin-arm64-X.Y.Z.tar.gz` và `core/core-manifest.json` |
| `core-manifest-linux-x64.json` · `core-manifest-darwin-arm64.json` | như data-model.md |
| `SHA256SUMS` | mã SHA-256 của mọi tệp trên |

## Các bước cài phần lõi trong màn hình thiết lập (`coreKind = packaged`)

| # | Windows | macOS | Tiến độ hiện ra |
|---|---|---|---|
| 1 | kiểm WSL2 (015) | — | |
| 2 | kiểm SHA-256 của tệp phần lõi với `core-manifest.json` | như Windows | "Checking the studio package…" |
| 3 | kiểm chỗ trống: ổ của `%LOCALAPPDATA%` ≥ `unpacked_bytes` + kích thước nén + 1 GB | ổ nhà ≥ `unpacked_bytes` + 1 GB | |
| 4 | giải nén gzip → `.tar` tạm; `wsl --import ClaudeUtube …\wsl <tar> --version 2`; xoá `.tar` | `tar -xzf` → `ClaudeUtube-core/<ver>/`; `xattr -dr com.apple.quarantine`; tạo 2 venv | "Installing the studio (a few minutes)…" |
| 5 | `sh lib/lemo-opuscar/tools/fetch.sh voice` trong phần lõi | như Windows | "Downloading the voice model (350 MB)…" |
| 6 | `sh bin/studio app models` | như Windows | "Downloading the speech check models…" |
| 7 | `app check --json` (015) | như Windows | |
| 8 | ghi cấu hình (`coreKind`, `coreVersion`, `modelsReady`) và chạy `app start` (015) | như Windows | |

Lỗi ở bước nào thì hiện lỗi và nút "Try again", rồi chạy lại từ bước đó.

## `sh bin/studio app models`

Tải Whisper `base.en` và `base` vào bộ nhớ đệm HuggingFace. In một dòng cho mỗi mô hình (`✓ base.en`). Mã 0 khi xong; mã 1 khi lỗi mạng, kèm dòng lỗi. Chạy lại thì bỏ qua mô hình đã có.
