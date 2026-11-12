# Implementation Plan: Xưởng dựng hình bằng GPU khi máy có GPU

**Branch**: `019-gpu-render` | **Date**: 2026-11-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/019-gpu-render/spec.md`

## Summary

Make every studio command that opens a film page use the GPU when the machine can, and fall back to software otherwise. On Linux / WSL2 the GPU is reachable only through the **full Chromium, headful, on the WSLg X11 display** (research R1); the studio plugs it into the library's unmodified tools through the library's documented `PLAYWRIGHT_CHROME` variable, with a small wrapper that turns Playwright's headless launch into a headful, off-screen, GPU launch (R2, R3). A probe decides the mode and `bin/studio` exports it to the commands it runs (R8). A new studio recorder `sh bin/studio render` records in 300-frame chunks that survive browser crashes and resume across runs, and re-records in software if the GPU is lost mid-run (R6, R7). The desktop app gets the same: the Windows core image ships the full Chromium, the host probes at start and passes the env to the worker, and the status shows the mode (R9).

## Technical Context

**Language/Version**: POSIX sh (bin/studio, wrapper); Node.js 20+ ES modules, plain JS with `// @ts-check` (probe, recorder; same style as `desktop/`); Python 3.11+ (filmcheck `config render`, `qc` measure field, studio host/worker env)

**Primary Dependencies**: the library's `playwright-core` and `core/render/page.mjs` (unchanged, used as is); ffmpeg 7 (already required); Playwright's full Chromium build matching the library's `playwright-core` (downloaded by `deps gpu`; shipped in the Windows core image)

**Storage**: files only: `.studio/config.json` key `render`; `<film>/out/.chunks/<fingerprint>/c_NNNN.mp4`; `<film>/out/render.log`

**Testing**: `node --test` (new `tests/render/*.test.mjs`, run by new `tests/render/run.sh`); existing `sh tests/run.sh` (status/deps/config cases), `tests/filmcheck`, `tests/ui` (host/worker env, Settings → Worker line). A tiny 2D-canvas test film (3 s, 10 fps) for recorder tests in software mode. GPU paths are verified on the reference machine (quickstart), not in CI.

**Target Platform**: Linux and WSL2 (GPU when a display and the full Chromium are present), macOS (GPU through the library's Metal default), online containers (software, unchanged)

**Project Type**: CLI tools of the studio + desktop app packaging

**Performance Goals**: `pet-swap` (17,153 frames, 1080p) recorded in ≤ 40 min on the reference machine (measured 24 min); `qc pet-swap` ≤ 5 min (measured 2 min 47 s); probe ≤ 30 s

**Constraints**: no file in `lib/` changes (constitution VI); no OS package installed by any studio command (constitution "Phần mềm hệ thống"); one video never mixes GPU and software frames; default workers must not exhaust 7 GB RAM

**Scale/Scope**: one machine, films up to ~15 min; 2 GPU workers

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|---|---|---|
| I. Spec là nguồn sự thật | ✓ | spec.md approved with 2 clarifications; no tech in the spec |
| II. Không đoán | ✓ | scope and GPU-loss behaviour clarified; remaining unknown (imported distro gets WSLg) is a verification task, not a guess (R9) |
| III. MVP trước | ✓ | US1 alone (probe + status + `render` + env) is shippable and testable |
| IV. Đo được | ✓ | SC-001…008 with numbers; tests for probe decisions, wrapper flags, fingerprint, resume, fallback; frame counts with ffprobe; GPU vs software pixel difference measured |
| V. Đơn giản | ✓ with note | one wrapper + one probe + one recorder; see Complexity Tracking for the recorder |
| VI. Thư viện gốc giữ nguyên | ✓ | only the library's documented `PLAYWRIGHT_CHROME` hook and its public `page.mjs` are used |
| VII. Một bộ máy dựng hình | ✓ | same engine (browser + the film's WebGL page); only the browser binary differs |
| VIII, IX | n/a | |
| Phần mềm hệ thống | ✓ | `deps gpu` downloads a browser build into the user's cache (like the library's own headless shell); if Chromium lacks system libraries the studio prints the `install-deps` command and stops. The Windows core image installs packages at **build time** of the app's own Linux, as it already does for the headless shell |
| Bản quyền | ✓ | Chromium (BSD-3-Clause + third-party notices) added to `CREDITS`; `credits-check.py` updated |

Post-design re-check: still passing; no new principle touched by data-model or contracts.

## Project Structure

### Documentation (this feature)

```text
specs/019-gpu-render/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/cli.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
tools/render/                     # new
├── chrome-gpu.sh                 # PLAYWRIGHT_CHROME wrapper: headful, off-screen, GPU flags + WSL env (R2, R3)
├── probe.mjs                     # mode decision → one JSON line (R8)
├── record.mjs                    # chunked, resumable recorder; GPU-loss fallback (R6, R7)
└── lib.mjs                       # shared: fingerprint, chunk plan, renderer check, film resolution
bin/studio                        # status line + JSON; deps gpu; render; page; config render → filmcheck;
                                  # render env exported before qc/publish/render/page/app
tools/filmcheck/cli.py            # `config render`; checks.json film.measures.render
tools/filmcheck/editor.py         # render setting read/write next to editor_model (same config file)
tools/studio/studio/host.py       # app start: probe once, pass env; app status shows the line
tools/runner/worker.py            # LocalRunner forwards the render env to jobs
tools/runner/JOB.md, CLAUDE.md    # agents record with `studio render`, page tools via `studio page`
tools/studio/studio/web/app.js    # Settings → Worker: "Rendering: GPU · <renderer>" / "software · <reason>"
deploy/core.Dockerfile            # full Chromium + install-deps chromium (Windows core)
desktop/core-build/smoke-core.sh  # probe runs (software in CI) and prints the line
desktop/core-build/credits-check.py, CREDITS
tests/render/                     # new: run.sh, *.test.mjs, fixtures/tiny-film/
tests/run.sh, tests/ui/…          # new cases
```

**Structure Decision**: a new `tools/render/` folder next to `tools/filmcheck/` holds the three pieces that touch the browser; `bin/studio` stays the single entry point. Node is used for the probe and the recorder because they drive the library's Playwright-based `page.mjs`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| A studio recorder next to the library's `video.mjs` | FR-008/FR-010 need chunks that survive a browser crash and resume across runs; FR-007 needs a per-launch renderer check and a full software re-record | `video.mjs` writes one segment per worker and cannot resume; it cannot be changed (constitution VI). Re-running it after a crash loses up to the whole film (measured once on `pet-swap`) |
