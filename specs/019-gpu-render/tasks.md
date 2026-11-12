# Tasks: Xưởng dựng hình bằng GPU khi máy có GPU

**Input**: Design documents from `specs/019-gpu-render/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: included (constitution IV: important logic has automated tests). GPU-only paths are verified on the reference machine through quickstart.md.

**Organization**: by user story (US1 P1 … US4 P4).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on unfinished tasks)

---

## Phase 1: Setup

- [X] T001 Create `tools/render/` and `tests/render/` with `tests/render/run.sh` (POSIX sh: runs `node --test tests/render/*.test.mjs`, prints `ok`/`FAIL` totals like `tests/run.sh`, exit 1 on any failure)
- [X] T002 [P] Create the test film `tests/render/fixtures/tiny-film/index.html`: 2D canvas, `window.DUR = 3`, deterministic `window.render(t)` that draws the frame number big, `window.TEXTS`, `window.READY = true`, plus one WebGL canvas so the renderer string is readable (page contract of the library `core/README.md`)

---

## Phase 2: Foundational (blocks all stories)

- [X] T003 Write `tools/render/chrome-gpu.sh` from `films/pet-swap/chrome-gpu.sh` (research R2, R3): drop `--headless*`, `--hide-scrollbars`, `--mute-audio`, `--blink-settings=primaryHoverType*`; add `--use-angle=gl --enable-gpu --ignore-gpu-blocklist --ozone-platform=x11 --window-size=1920,1080 --window-position=-3000,-3000 --disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows`; export `LD_LIBRARY_PATH=/usr/lib/wsl/lib` (only when that folder exists) and `GALLIUM_DRIVER=d3d12`; find the full Chromium as `$PLAYWRIGHT_BROWSERS_PATH` (default `~/.cache/ms-playwright`)`/chromium-<rev>/chrome-linux64/chrome` where `<rev>` comes from the library's `node_modules/playwright-core/browsers.json`; exit 127 with a clear message when missing
- [X] T004 [P] Write `tools/render/lib.mjs` (`// @ts-check`): `findChromium()`, `resolveFilm(nameOrPath)` (name under `films/` or folder with `index.html`), `isSoftware(renderer)` = `/swiftshader|llvmpipe|software/i`, `readRenderer(page)` (WebGL `UNMASKED_RENDERER_WEBGL`), `fingerprint(dir, w, h, fps)` = SHA-256 over sorted (relative path, bytes) excluding `out/`, `stills/`, `publish/`, `.check/`, `*.mp4`, `*.log`, `checks.json`, `CHECKS.md`, plus `"{w}x{h}@{fps}"` (data-model.md), `planChunks(N, size)` with `size = 10 × fps` (data-model: "`10 × fps` frames (240 at 24 fps, 300 at 30 fps), so a chunk is never over 10 s")
- [X] T005 [P] Tests `tests/render/lib.test.mjs`: fingerprint stable across runs and changes when `index.html`, `timeline.json` or fps change but not when `out/` or `stills/` change; `planChunks(17153, 300)` gives 58 chunks and `planChunks(720, 240)` gives 3, with no gap or overlap; `isSoftware` on the four renderer strings of research R1
- [X] T006 [P] Tests `tests/render/wrapper.test.mjs`: run `chrome-gpu.sh` with a fake Chromium (script printing its argv) through `PLAYWRIGHT_BROWSERS_PATH`; assert `--headless=new` and `--hide-scrollbars` removed, GPU and off-screen flags present, other args kept in order; missing Chromium → exit 127

**Checkpoint**: wrapper and helpers tested.

---

## Phase 3: User Story 1 - Phim được dựng bằng GPU mà không phải làm gì thêm (P1) 🎯 MVP

**Goal**: probe + status line + `config render` + `deps gpu` + `sh bin/studio render` (GPU or software, renderer check and GPU-loss fallback).

**Independent Test**: quickstart §1, §2, §6.

### Tests for US1

- [X] T007 [P] [US1] Tests `tests/render/probe.test.mjs` for `tools/render/probe.mjs` decisions, using fake environments: config `render: software` → `{mode: "software", reason: "forced by config", source: "config"}`; `STUDIO_MODE=online` → reason `online mode`; Linux with empty `DISPLAY` → `no display`; Chromium missing → `full Chromium missing` with fix `sh bin/studio deps gpu`; `STUDIO_RENDER_MODE` set → `source: "env"` and no browser launch; output is one JSON line with all data-model fields; `mode = gpu` never with a software renderer
- [X] T008 [P] [US1] Tests `tests/render/record.test.mjs` for `tools/render/record.mjs` on the tiny film in software mode: 30 frames at 10 fps with chunk size overridable to 10 (env `STUDIO_RENDER_CHUNK`) → 3 chunks, `ffprobe -count_frames` = 30, `out/render.log` first line `render: software · … · 30 frames · 3 chunks (0 already done) · 1 workers`
- [X] T009 [P] [US1] Test GPU-loss fallback in `tests/render/record.test.mjs`: `STUDIO_RENDER_MODE=gpu` with the normal headless browser (software renderer) → log contains `GPU lost` and `re-recording everything in software`, final video 30 frames, no chunk from the first attempt kept
- [X] T010 [P] [US1] Cases in `tests/run.sh`: `status` prints a `dựng hình` line with the Vietnamese text of the data-model reason table and `status --json` has `"render"` (with a fake probe via `STUDIO_RENDER_PROBE` pointing to a script that prints fixed JSON); `config render software` then `auto` writes `.studio/config.json`; `deps gpu` with a fake library prints the download step and never calls `apt`/`brew`/`sudo`

### Implementation for US1

- [X] T011 [US1] Write `tools/render/probe.mjs` (`// @ts-check`) per research R8 and data-model "Render mode": decision order config → online → (macOS: library default browser) → no display → Chromium missing → launch through `chrome-gpu.sh` with 30 s timeout; prints one JSON line `{mode, renderer, reason, fix, source, chrome, checked_at}` with the reason codes and fixes of the data-model table (e.g. `no display` → "Windows/WSL: cần Windows 11 có WSLg (`wsl --update` trong PowerShell); xưởng và app không tự bật"); uses the library's `playwright-core` from `$STUDIO_LIB`
- [X] T012 [US1] Add the render setting to `tools/filmcheck/editor.py` (`render_setting()` / `set_render_setting(value)` with values `auto|software`, same `.studio/config.json`) and the `config render` subcommand to `tools/filmcheck/cli.py`
- [X] T013 [US1] In `bin/studio`: function `render_env` (runs the probe once unless `STUDIO_RENDER_MODE` is set; exports `STUDIO_RENDER_MODE`, `STUDIO_RENDER_RENDERER`, and in GPU mode on Linux `PLAYWRIGHT_CHROME=<repo>/tools/render/chrome-gpu.sh`); honour `STUDIO_RENDER_PROBE` override for tests
- [X] T014 [US1] In `bin/studio` `cmd_status`: the `dựng hình` line with `✓`/`✗`/`·` wording of contracts/cli.md and `"render"` in `--json` (null when the library's packages are missing: "chưa kiểm"); never changes `ready` or the exit code
- [X] T015 [US1] In `bin/studio` `cmd_deps`: `deps gpu` downloads the full Chromium with the library's `node_modules/playwright-core/cli.js install chromium` (user cache only); checks it starts; if system libraries are missing prints the `sudo … install-deps chromium` command without running it
- [X] T016 [US1] Write `tools/render/record.mjs` (`// @ts-check`) from `films/pet-swap/render_gpu.mjs` per research R6, R7 and data-model "Recording run": uses the library's `core/render/page.mjs` `openDemo` (so the browser comes from `PLAYWRIGHT_CHROME`); checks the renderer on every launch; chunks of `10 × fps` frames (`STUDIO_RENDER_CHUNK` override for tests); `--until SECONDS` records only `[0, SECONDS)` and is part of the fingerprint in `out/.chunks/<fingerprint>/`; `.part` → rename; up to 3 re-opens per chunk; GPU loss → delete the fingerprint dir, unset `PLAYWRIGHT_CHROME`, re-record in software; workers per research R5; joins with ffmpeg concat `-c copy`; verifies frame count `N = ceil(DUR × fps)`; deletes other fingerprint dirs after success; writes `out/render.log`
- [X] T017 [US1] In `bin/studio`: `render <film> [--fps N] [--workers N] [--out FILE] [--size WxH] [--until SECONDS]` → `render_env` then `node tools/render/record.mjs …`; `help` text lists `render`, `page`, `deps gpu`, `config render`
- [X] T018 [US1] Run `sh tests/render/run.sh` and `sh tests/run.sh`; then quickstart §1 and §2 on the reference machine (record `pet-swap` with `sh bin/studio render pet-swap --fps 30`, time and frame count; SC-001, SC-006)

**Checkpoint**: MVP — films record with the GPU from one studio command.

---

## Phase 4: User Story 2 - Mọi lệnh kiểm tra cũng dùng GPU (P2)

**Goal**: `qc`, `publish`, `page still|events|readcheck` run with the render env.

**Independent Test**: quickstart §3, §5.

- [X] T019 [P] [US2] Test in `tests/filmcheck/` (new case in the existing suite): `qc` on a fixture writes `film.measures.render` `{mode, renderer}` into `checks.json` taken from `STUDIO_RENDER_MODE` / `STUDIO_RENDER_RENDERER`
- [X] T020 [US2] In `bin/studio`: call `render_env` before `qc` and `publish` in `cmd_filmcheck`, and add `page <still|events|readcheck> <film> [args…]` (runs `node core/render/<tool>.mjs <film dir> args…` from the library root)
- [X] T021 [US2] In `tools/filmcheck/qc.py` (and `report.py` if it renders measures): record `measures["render"]` from the env; show it in `CHECKS.md`
- [X] T022 [US2] Run quickstart §3 and §5 on the reference machine: `qc pet-swap` ≤ 5 min without extra env; GPU vs software stills mean difference ≤ 8/255 (SC-002, SC-005)

---

## Phase 5: User Story 3 - Ghi video dài chịu được gián đoạn (P3)

**Goal**: resume across runs and after a closed window (the recorder from T016 already chunks; this phase proves and hardens it).

**Independent Test**: quickstart §4.

- [X] T023 [P] [US3] Tests in `tests/render/record.test.mjs`: (a) kill the recorder after the first chunk, run again → header `(1 already done)` or more, final 30 frames, the done chunk's file is not rewritten (same mtime); (b) change `index.html` between runs → new fingerprint, nothing reused, old dir removed after success; (c) a leftover `.part` file is deleted at start; (d) a browser that dies mid-chunk (test hook `STUDIO_RENDER_TEST_CRASH_AT=<frame>` closes the browser once) → log `reopening the browser`, final 30 frames
- [X] T024 [US3] Harden `tools/render/record.mjs` for the cases of T023 (crash hook only active when the env is set; clean `SIGINT`/`SIGTERM`: stop ffmpeg, delete `.part`, keep done chunks)
- [X] T025 [US3] Run quickstart §4 on the reference machine (close a window by hand; stop and resume) (SC-004)

---

## Phase 6: User Story 4 - App desktop cũng dựng bằng GPU (P4)

**Goal**: the app's core (Windows Linux image, macOS) uses the same mechanism and shows the mode.

**Independent Test**: quickstart §7.

- [X] T026 [P] [US4] Tests in `tests/ui/`: `LocalRunner` forwards `PLAYWRIGHT_CHROME`, `STUDIO_RENDER_MODE`, `STUDIO_RENDER_RENDERER`, `DISPLAY`, `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR`, `LD_LIBRARY_PATH`, `GALLIUM_DRIVER` to the job env (`tools/runner/worker.py`); `app status --json` contains `"render"`; the Settings → Worker API payload contains the render line
- [X] T027 [US4] `tools/runner/worker.py`: add the variables of T026 to `LocalRunner`'s forwarded base env; the Docker runner stays unchanged (online = software, FR-015)
- [X] T028 [US4] `tools/studio/studio/host.py`: `app start` runs the probe once (through `bin/studio`'s `render_env`, or `tools/render/probe.mjs` directly) and passes the render env to the worker process; `app status` prints `dựng hình …` (contracts/cli.md wording) and `--json` adds `"render"`
- [X] T029 [US4] Settings → Worker in `tools/studio/studio/web/app.js` (and the API that feeds it in `tools/studio/studio/server.py` or `api_online.py`): show `Rendering: GPU · <renderer>` or `Rendering: software · <reason>`; Client mode (018) shows it through the Host's UI with no extra code
- [X] T030 [US4] `deploy/core.Dockerfile`: after the headless shell, `node node_modules/playwright-core/cli.js install chromium` (as `studio`) and `install-deps chromium` (as root, build time only); keep `libgl1-mesa-dri libegl-mesa0`; `desktop/core-build/smoke-core.sh` runs `tools/render/probe.mjs` and prints the line (software expected in CI)
- [X] T031 [P] [US4] `CREDITS` and `desktop/core-build/credits-check.py`: add Playwright Chromium (BSD-3-Clause, with a link to its third-party notices)
- [X] T032 [US4] `tools/runner/JOB.md` and `CLAUDE.md` (film flow step 2 and the "Cấu trúc" list): record with `sh bin/studio render <film> --fps <rate>`, page tools with `sh bin/studio page …`, mention `deps gpu`, `config render`, and that a Chrome window may appear off-screen on Linux GPU machines
- [ ] T033 [US4] Manual check quickstart §7 on the reference machine with an installer built from this branch (Windows Host + Client); record results in `specs/019-gpu-render/quickstart.md` "Results"; if WSLg is not available in the imported distro, report it and keep the app on software (SC-008)

---

## Phase 7: Polish & Cross-Cutting

- [X] T034 [P] Run all suites: `sh tests/run.sh`, `sh tests/render/run.sh`, `sh tests/filmcheck/run.sh`, `sh tests/ui/run.sh`, `sh tests/learn/run.sh`, `sh tests/online/run.sh`, `sh tests/license/run.sh`
- [X] T035 [P] SC-003 timing check on the reference machine in software mode (`sh bin/studio config render software`): `sh bin/studio render pet-swap --fps 30 --until 30` vs the library's `node core/render/video.mjs films/pet-swap --fps 30` limited to the same 900 frames (temporary copy of the film with `window.DUR = 30`): same frame count, time within 10 %; write both times in quickstart.md "Results"
- [X] T036 [P] Guard checks (SC-007): `git status --porcelain lib/` empty; `grep -rnE "apt(-get)? install|brew install" tools/render bin/studio` finds nothing outside printed hints
- [X] T037 Update the memory note `reference-wsl-gpu-render` to point to the studio commands, and record results in `specs/019-gpu-render/quickstart.md` "Results"

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → US1 (MVP). US2 needs `render_env` (T013). US3 needs the recorder (T016). US4 needs US1–US2 (probe, env, recorder).
- Within US1: T011 → T013 → T014/T017; T012 before T013 (config read); T016 before T017.

## Parallel Opportunities

- T002 with T001; T004, T005, T006 together after T003.
- US1 tests T007–T010 together before the implementation.
- T019 (US2), T023 (US3), T026 and T031 (US4) can be written while US1 implementation runs.

## Implementation Strategy

MVP = Phases 1–3 (US1): one command records with the GPU, `status` tells the mode. Then US2 (checks), US3 (resume hardening), US4 (desktop app). Commit after each phase (constitution).

## Phase 8: Convergence

- [X] T038 Cap GPU-mode workers by free RAM too (same rule as software: at most free RAM ÷ 1.5 GB, at least 1, default 2) in `tools/render/record.mjs`, with a test in `tests/render/record.test.mjs` per FR-011 (partial)
- [X] T039 Warn about the Chrome window in GPU mode on Linux: add "a Chrome window is open off-screen, do not close it" to the first line of `out/render.log` (`tools/render/record.mjs`) and to the `dựng hình` GPU line of `sh bin/studio status` (`bin/studio`), with tests in `tests/render/record.test.mjs` and `tests/run.sh` per spec Edge Cases "Cửa sổ trình duyệt hiện lên lúc ghi" (missing)
- [X] T040 Record the real chunk folder name `out/.chunks/<fingerprint>-<mode>-s<chunk size>` in `specs/019-gpu-render/data-model.md` "Recording run" (as an addendum below the table) per plan: data model (partial)
