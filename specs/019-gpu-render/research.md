# Research: 019-gpu-render

All measurements on the reference machine (Windows 11 + WSL2 Ubuntu 24.04, Intel UHD Graphics 730, 7 GB RAM, Mesa 25.2.8 with `d3d12_dri.so`), 2026-11-12, film `films/pet-swap` (three.js, 1080p).

## R1. How a browser gets the GPU on Linux / WSL2

**Decision**: On Linux, use the **full Playwright Chromium, headful** (`headless: false`), on the WSLg X11 display, with `--use-angle=gl --enable-gpu --ignore-gpu-blocklist --ozone-platform=x11` and the environment `LD_LIBRARY_PATH=/usr/lib/wsl/lib GALLIUM_DRIVER=d3d12`. On macOS keep the library's default (headless shell with `--use-angle=metal`), which already uses the GPU.

**Rationale**: measured renderer strings:

| Browser | Mode | Flags / env | WebGL renderer |
|---|---|---|---|
| headless shell | headless | default, `gl`, `gl-egl`, `vulkan`, + `MESA_LOADER_DRIVER_OVERRIDE=d3d12`, `EGL_PLATFORM=surfaceless/x11/wayland` | SwiftShader or llvmpipe (software) |
| full Chromium | headless | `--use-angle=gl`, x11 or wayland | SwiftShader |
| full Chromium | **headful** | `--use-angle=gl` (or `gl-egl`, `default`), `--ozone-platform=x11` | **ANGLE (Microsoft Corporation, D3D12 (Intel(R) UHD Graphics 730), OpenGL 4.1)** |
| full Chromium | headful | `--ozone-platform=wayland` | no WebGL 2 |

The headless GPU process fails with `MESA-LOADER: failed to retrieve device information` and `No suitable EGL configs found`: WSL has no `/dev/dri`, and Mesa's d3d12 path needs a display. There is no `dzn` Vulkan ICD in Ubuntu 24.04's `mesa-vulkan-drivers`.

**Alternatives considered**: building Mesa with `dzn` or adding a PPA (a system install, banned by the constitution, and still uncertain for headless); a virtual X server such as Xvfb (no GPU: Xvfb renders in software); patching the library's `browser.mjs` (constitution VI).

## R2. Plugging the GPU browser into tools we do not own

**Decision**: a POSIX-sh **wrapper executable** passed to the library through its documented `PLAYWRIGHT_CHROME` variable (`core/render/browser.mjs`: `EXE = process.env.PLAYWRIGHT_CHROME`). The wrapper drops `--headless*` and the flags Playwright adds only in headless mode, adds the GPU flags, sets the env from R1, and `exec`s the full Chromium. Every library tool (`video`, `still`, `events`, `readcheck`) and every studio tool built on the library's `page.mjs` (`tools/filmcheck/texts.mjs` for `qc`, the publish thumbnails) then use the GPU with no code change.

**Rationale**: verified on `pet-swap`: `still.mjs` without the software-GL note; `qc pet-swap` finished in 2 min 47 s (it timed out after 300 s on software GL); Playwright still drives the browser over its pipe when headful.

**Alternatives considered**: a studio copy of `page.mjs` (duplicates library code and drifts from it); a Playwright `connect` server (more moving parts, same browser).

## R3. Keeping the window out of the user's way (FR-019)

**Decision**: the wrapper adds `--window-position=-3000,-3000` (off-screen) plus `--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows`.

**Rationale**: with the window off-screen, `still.mjs` on `pet-swap` at 66 s and 333 s still reported no software note and produced correct frames (checked by eye). The throttling flags keep the page rendering when the window is hidden.

**Alternatives considered**: `--start-minimized` (WSLg ignores it for X11 windows in our test of the visible case; off-screen is simpler); a separate virtual display (loses the GPU, R1).

## R4. Is GPU output close enough to software output (SC-005)?

**Decision**: accept GPU frames as equivalent; never mix the two in one video (FR-007).

**Rationale**: 10 frames of `pet-swap` (20, 66, 120, 200, 260, 333, 400, 450, 500, 540 s), GPU vs SwiftShader: mean absolute difference **1.38/255** per channel (range 0.46–2.97); 99th percentile up to 66/255 on the frame with the strongest depth of field (blur edges differ). Text pixels match. Well inside the 8/255 target.

## R5. Speed and worker count

**Decision**: GPU mode defaults to **2 workers**. Software mode: workers = min(2, free RAM ÷ 1.5 GB), at least 1. `--workers` overrides both.

**Rationale**: GPU, 2 workers: 17,159 frames in 1,456 s (11.8 fps, 9 min 32 s of film in ≈ 24 min). Software: 0.82–0.87 fps whether 2 or 6 workers (CPU saturated); 6 workers plus a check exhausted 7 GB and the kernel killed the check (exit 137).

## R6. Resumable recording (FR-008 to FR-010)

**Decision**: the studio recorder splits the film into **chunks of 10 × fps frames** (≤ 10 s of film at any rate: 240 at 24 fps, 300 at 30 fps), encodes each chunk to its own H.264 file with the same settings as the library's `video.mjs` (`-preset medium -crf 14 -pix_fmt yuv420p`, JPEG screenshots at quality 95 piped as MJPEG), renames `*.part` to final only when ffmpeg exits 0, and joins chunks with ffmpeg's concat demuxer (`-c copy`). Chunks live in `out/.chunks/<fingerprint>/`; the fingerprint is a SHA-256 of the film's source files (everything in the film folder except `out/`, `stills/`, `publish/`, `.check/`, `*.mp4`, `*.log`, `checks.json`, `CHECKS.md`) plus width, height and fps. A changed source means a new fingerprint directory, so old chunks are never reused (FR-009); older fingerprint directories are deleted when a recording finishes.

**Rationale**: the `pet-swap` recorder lost a whole run when a window was closed; the chunked version finished 3 full renders with no loss. Concat with `-c copy` gave exactly the expected frame counts (17,575 and 17,159; checked with `ffprobe -count_frames`).

**Alternatives considered**: one segment per worker (the library's way; a crash loses up to half the film); per-frame PNG files (≈ 17,000 files, several GB).

## R7. GPU loss during a recording (FR-007, clarified 2026-11-12)

**Decision**: every browser launch reads the WebGL renderer. If the run is in GPU mode and a launch reports a software renderer, the recorder stops all workers, deletes the run's chunks, logs `render: GPU lost (<renderer>) → re-recording everything in software`, and records again with the software browser.

## R8. Detection (FR-001, FR-002)

**Decision**: `tools/render/probe.mjs` decides, in this order:
1. `.studio/config.json` `"render": "software"` → software, reason "forced by config".
2. `STUDIO_MODE=online` → software, reason "online mode".
3. macOS → launch the library's default browser, read the renderer; GPU unless it contains `SwiftShader|llvmpipe|software`.
4. Linux without `DISPLAY` → software, reason "no display".
5. Linux without the full Chromium → software, reason "full Chromium missing", fix `sh bin/studio deps gpu`.
6. Otherwise launch through the wrapper with a 30 s timeout, read the renderer; GPU or software (reason "the browser fell back to software", fix: check the GPU driver / WSLg).

The result is JSON `{mode, renderer, reason, fix, chrome, checked_at}`. `bin/studio` exports `STUDIO_RENDER_MODE` and, in GPU mode on Linux, `PLAYWRIGHT_CHROME=<wrapper>` for the commands it runs, so children do not probe again. `status` always probes afresh (edge case "stale result").

## R9. Desktop app

**Decision**:
- **Windows core** (`deploy/core.Dockerfile`): install the full Chromium with Playwright (`install chromium` + `install-deps chromium`) next to the headless shell, and keep Ubuntu's `libgl1-mesa-dri` / `libegl-mesa0` (Mesa d3d12). `/usr/lib/wsl/lib` and the WSLg display are provided by WSL itself to every WSL2 distro, including imported ones. The host (`app start`) probes once at start and passes the render env to the worker. `LocalRunner` (worker.py) forwards `PLAYWRIGHT_CHROME`, `STUDIO_RENDER_MODE`, `DISPLAY`, `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR`, `LD_LIBRARY_PATH`, `GALLIUM_DRIVER` to jobs.
- **macOS core**: no browser change (Metal headless already uses the GPU); the probe reports it.
- **Status**: `app status --json` and the web UI's Settings → Worker show the render line; Client mode (018) shows the Host's because it is the Host's UI.
- **Size**: the full Chromium adds ≈ 190 MB to the Linux image (CREDITS: Chromium, BSD-3-Clause and its third-party notices).

**To verify during implement** (cannot be done in CI): an imported `ClaudeUtube` distro on the reference machine gets `DISPLAY` and the d3d12 renderer. Only `Ubuntu-24.04` is installed here today.

## R10. Agents call library tools directly

**Decision**: `CLAUDE.md` (chat flow) and `tools/runner/JOB.md` (app worker) tell the agent to record with `sh bin/studio render <film>` and to run page tools with `sh bin/studio page <still|events|readcheck> <film> …`. Direct library calls still work (in the app they still get the GPU through the forwarded env, without resume).
