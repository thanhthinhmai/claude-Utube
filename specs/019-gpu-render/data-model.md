# Data model: 019-gpu-render

## Render mode (probe result)

Printed by `tools/render/probe.mjs` as one JSON line; embedded in `status --json` under `"render"` and in `app status --json`.

| Field | Type | Rule |
|---|---|---|
| `mode` | `"gpu"` \| `"software"` | |
| `renderer` | string \| null | the WebGL `UNMASKED_RENDERER_WEBGL` string; null when no browser was launched |
| `reason` | string \| null | null when `mode = gpu`; one of the codes: `forced by config`, `online mode`, `no display`, `full Chromium missing`, `the browser fell back to software`, `probe failed: <message>`. JSON keeps these English codes; `status` and the app print the Vietnamese text of the table below |
| `fix` | string \| null | one command or one sentence the user can act on; null when nothing to do |
| `source` | `"auto"` \| `"config"` \| `"env"` | `env` when `STUDIO_RENDER_MODE` was already set by a parent |
| `chrome` | string \| null | wrapper path in GPU mode on Linux; null otherwise |
| `checked_at` | ISO-8601 | |

Reason codes → text and fix shown to the user:

| Code | `status` text | `fix` |
|---|---|---|
| `forced by config` | do cấu hình | `sh bin/studio config render auto` để dùng lại GPU |
| `online mode` | chế độ online | null |
| `no display` | không có màn hình đồ hoạ | Linux: chạy trong phiên có màn hình. Windows/WSL: cần Windows 11 có WSLg (`wsl --update` trong PowerShell); xưởng và app không tự bật |
| `full Chromium missing` | thiếu Chromium đầy đủ | `sh bin/studio deps gpu` (app: cài lại bản mới của app) |
| `the browser fell back to software` | trình duyệt rơi về vẽ bằng phần mềm | kiểm driver GPU của Windows / macOS rồi chạy lại `sh bin/studio status` |
| `probe failed: …` | không kiểm được (lỗi …) | null |

Validation: `mode = gpu` ⇒ `renderer` does not match `/swiftshader|llvmpipe|software/i`.

## Render setting

`.studio/config.json` (same file as the editor model, `tools/filmcheck/editor.py`): key `"render"`, values `"auto"` (default when absent) or `"software"`.

## Recording run

Log file `out/render.log` (one line per event) and state in `out/.chunks/<fingerprint>/`.

| Item | Rule |
|---|---|
| fingerprint | SHA-256 over sorted (relative path, bytes) of the film's source files + `"{w}x{h}@{fps}"` + `until` (when given); excluded: `out/`, `stills/`, `publish/`, `.check/`, `*.mp4`, `*.log`, `checks.json`, `CHECKS.md` |
| frame count `N` | `ceil(DUR × fps)` |
| chunk size `S` | `10 × fps` frames (240 at 24 fps, 300 at 30 fps), so a chunk is never over 10 s (FR-008) |
| chunk `c` | frames `[c·S, min(N, (c+1)·S))`; file `c_NNNN.mp4`, written as `c_NNNN.mp4.part` then renamed |
| state | `todo` (no file) → `rendering` (`.part` exists) → `done` (final file); a `.part` left by a crash is deleted at start |
| retries | per chunk, at most 3 browser re-opens; then the run fails |
| GPU loss | `mode = gpu` and a launch reports software ⇒ delete the fingerprint directory, set mode software, start over (logged) |
| output | concat of `c_0000 … c_{n-1}` in order → `--out` (default `out/video.mp4`); frame count must equal `N` (checked with ffprobe) |
| cleanup | after success, fingerprint directories other than the current one are removed; the current one is kept until the next successful run with another fingerprint |

Addendum (convergence, T040): the chunk folder is `out/.chunks/<fingerprint>-<mode>-s<chunk size>`. The mode keeps GPU and software chunks apart (FR-007); the chunk size is `min(10 × fps, ceil(N / workers))`, so short films give every worker work (SC-003), and a run with another size never reuses chunks that cover other frames.

`out/render.log` first line: `render: <mode> · <renderer> · <N> frames · <chunks> chunks (<done> already done) · <workers> workers`, plus ` · a Chrome window is open off-screen, do not close it` in GPU mode on Linux.
