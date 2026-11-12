# Contract: commands (019-gpu-render)

Exit codes follow the studio's habit: `0` done, `1` the work failed, `2` usage error.

## `sh bin/studio status [--json]` (changed)

Text mode adds one line after the tools:

```
  ✓ dựng hình   GPU · ANGLE (Microsoft Corporation, D3D12 (Intel(R) UHD Graphics 730), OpenGL 4.1)
  ✗ dựng hình   phần mềm · thiếu Chromium đầy đủ → sh bin/studio deps gpu
  · dựng hình   phần mềm · không có màn hình đồ hoạ
  · dựng hình   chưa kiểm (chưa cài gói lõi của thư viện)
```

`✓` GPU; `✗` software with a fix the user can run; `·` software with nothing to fix here (forced, online, no display) or not checked. The line never changes `ready` or the exit code.

JSON mode adds `"render": <render mode>` (data-model.md), or `"render": null` when not checked.

## `sh bin/studio deps gpu` (new)

Downloads the full Playwright Chromium matching the library's `playwright-core` into the user's browser cache (`PLAYWRIGHT_BROWSERS_PATH`, default `~/.cache/ms-playwright`). On Linux, also prints, without running it, the system-library command when Chromium cannot start (`sudo …/playwright-core/cli.js install-deps chromium`). Never installs OS packages itself. Prints `✓ Chromium đầy đủ đã có` when present.

## `sh bin/studio config render auto|software` (new)

Writes `"render"` to `.studio/config.json`. Prints the new value. `auto` is the default.

## `sh bin/studio render <film> [--fps N] [--workers N] [--out FILE] [--size WxH]` (new)

Records the film's video, resumable (data-model.md "Recording run").
- `<film>`: a name under `films/` or a path to a folder with `index.html`.
- Defaults: `--fps` 24 (as the library; pass the rate the style sets, e.g. 30); `--workers` per research R5; `--out` `<film>/out/video.mp4`; `--size` 1920x1080.
- Progress on stdout and in `<film>/out/render.log`: the header line, then `<done>/<n> chunks  <seconds>s` every 5 chunks, then `video <path> · <N> frames · <seconds>s`.
- Exit 1 when a chunk fails 4 times, when ffmpeg fails, or when the joined video does not have `N` frames.

## `sh bin/studio page <still|events|readcheck> <film> [args…]` (new)

Runs the library's `core/render/<tool>.mjs` on the film, from the library root, with the render environment. Arguments after `<film>` are passed unchanged. Exit code is the tool's.

## `sh bin/studio qc|publish …` (changed)

Unchanged arguments. Run with the render environment, so the on-screen text pass and the thumbnails use the GPU. `checks.json` → `film.measures.render` records `{mode, renderer}`.

## `sh bin/studio app start` (changed) · `app status [--json]` (changed)

`app start` probes once and passes the render environment to the worker. `app status` prints the render line (same wording as `status`); `--json` adds `"render"`.

## Environment (internal, between studio processes)

| Variable | Set by | Meaning |
|---|---|---|
| `STUDIO_RENDER_MODE` | `bin/studio`, `app start` | `gpu` or `software`; children trust it and do not probe again |
| `PLAYWRIGHT_CHROME` | same, only GPU on Linux | path of `tools/render/chrome-gpu.sh` |
| `STUDIO_RENDER_RENDERER` | same | the renderer string, for logs |
