# Tasks: Bộ cài app desktop và phần lõi đóng gói sẵn (016)

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/release.md, quickstart.md

## Phase 1: Setup và kiểm trước (chặn mọi phase sau)

- [ ] T001 Kiểm 3 điều chưa thử của plan (ghi kết quả vào research.md, mục "Kết quả T001"): (a) build `deploy/core.Dockerfile` trên máy này, đo tar.gz sau `docker export | gzip -6` (≤ 1,9 GB) và chạy `app start` → `/api/v1/health` → `app stop` trong container; (b) trong container, `bwrap` chặn ghi ngoài thư mục việc nhưng vẫn cho `curl http://127.0.0.1:<cổng>`; (c) nguồn ffmpeg tĩnh arm64 cho macOS có tồn tại và có giấy phép phát lại (chạy thật trên `macos-14` ở T019). Khác plan thì dừng và hỏi
- [ ] T002 [P] `desktop/package.json`: thêm devDependency `electron-builder` 25.1.8 (ghim), scripts `pack:win`, `pack:mac`; `npm install` cập nhật `package-lock.json`
- [ ] T003 [P] `.gitignore`: thêm `dist/`, `desktop/dist/`

## Phase 2: Nền tảng (phần lõi dùng chung cho cả hai hệ điều hành)

- [ ] T004 [P] `tools/studio/studio/host.py` và `tools/studio/studio_cli.py`: lệnh `app models [--json]` theo contracts/release.md (tải Whisper `base.en` và `base` bằng `faster_whisper.utils.download_model`, bỏ qua mô hình đã có, mã 0/1). Biến `CU_MODELS_FAKE=1` cho test (không mạng)
- [ ] T005 [P] `tools/studio/studio/host.py` (`part_env`) và `tools/runner/agent.py`: `STUDIO_AGENT_SANDBOX=1` khi có `bwrap` và `socat`, hoặc trên macOS; agent bật `sandbox` theo R5 (ghi trong thư mục việc, mạng `127.0.0.1`). Không có sandbox thì giữ cảnh báo của 014
- [ ] T006 [P] `bin/studio`: nạp `<studio>/env.sh` nếu có (PATH cho node và ffmpeg đi kèm, `PLAYWRIGHT_BROWSERS_PATH`)
- [ ] T007 Test cho T004–T006 trong `tests/online/test_host.py` (app models với `CU_MODELS_FAKE`; sandbox bật/tắt theo `which`; tuỳ chọn sandbox truyền vào agent) và `tests/run.sh` (env.sh được nạp)
- [ ] T008 [P] `desktop/core-build/credits-check.py`: đọc danh sách gói (dpkg, pip, npm của thư viện, Node, Chromium, mô hình) của một phần lõi đã build và so với `CREDITS`; thiếu thì mã 1 kèm danh sách. Test nhỏ trong `tests/ui/` với danh sách giả
- [ ] T009 [P] `desktop/core-build/smoke-core.sh`: nhận lệnh gọi phần lõi; kiểm `app check`, `app start`, `/api/v1/health`, tạo chủ xưởng qua API, `app stop`; kiểm sandbox (bwrap trên Linux, `sandbox-exec` trên macOS) chặn ghi ra ngoài thư mục việc (SC-006)

## Phase 3: User Story 1 — Cài trên Windows bằng một tệp (P1) 🎯 MVP

**Mục tiêu**: một tệp `.exe` cài app; màn hình thiết lập cài bản Linux `ClaudeUtube` và tải mô hình.

**Kiểm độc lập**: build Linux core + bộ cài Windows trên Actions; trên máy Windows có WSL2, chạy tệp cài tới trang tạo chủ xưởng (quickstart §3).

- [ ] T010 [US1] `deploy/core.Dockerfile` theo R1 (Ubuntu 24.04, apt, Node 22, bubblewrap, socat, người dùng `studio`, `/etc/wsl.conf`, studio, thư viện ở `LIB_COMMIT`, các `deps`, Chromium, không có mô hình, `.core-version`)
- [ ] T011 [US1] `desktop/core-build/build-linux.sh`: `git archive` → `docker build` → `docker export` → gzip → SHA-256 → `core-manifest.json` (data-model.md) trong `dist/core/linux/`
- [ ] T012 [US1] `desktop/core.js`: hàm thuần cho bước cài: `readManifest`, `verifySha256` (luồng), `spaceNeeded(manifest, os)`, `importCommand(tar)` (`wsl.exe --import ClaudeUtube <dir> <tar> --version 2`), `installedVersion` (đọc `.core-version`), `needsReinstall`, `packagedConfig(os)` (data-model.md), `modelSteps()`; R7: `backupCommand`, `restoreCommand`
- [ ] T013 [US1] `desktop/test/install.test.js`: test cho T012 (lệnh dựng ra, so phiên bản, SHA-256 trên tệp nhỏ, chỗ trống, cấu hình packaged)
- [ ] T014 [US1] `desktop/main.js` và `desktop/preload.js`: IPC `setup.installCore` chạy các bước 2–8 của contracts/release.md, gửi tiến độ về cửa sổ; giải nén gzip dạng luồng ra tệp `.tar` tạm; lỗi ở bước nào thì trả về bước đó để "Try again"
- [ ] T015 [US1] `desktop/setup.html`: khi có `resources/core/core-manifest.json` thì hiện lựa chọn "Install the studio (recommended)" và "Use a studio I already have" (015); thanh tiến độ cho từng bước; nút "Try again"; hỏi trước khi cài lại phần lõi khi phiên bản khác (FR-012)
- [ ] T016 [US1] `desktop/electron-builder.yml` (R4, Windows NSIS per-user, `extraResources`) và `desktop/installer.nsh` (trình gỡ hỏi xoá bản Linux và dữ liệu, mặc định giữ)
- [ ] T017 [US1] `test/fake-core.mjs` và chế độ `--smoke`: thêm đường cài phần lõi giả (`CU_FAKE_INSTALL=1`: manifest nhỏ, lệnh import giả) để smoke kiểm được màn hình cài trên Actions

## Phase 4: User Story 2 — Cài trên macOS bằng một tệp (P2)

**Mục tiêu**: một `.dmg` chip Apple; thiết lập giải nén phần lõi, tạo venv, tải mô hình.

**Kiểm độc lập**: build Mac core + `.dmg` trên `macos-14`; smoke-core đạt; quickstart §4 bằng tay.

- [ ] T018 [US2] `desktop/core-build/build-mac.sh` theo R2 (python-build-standalone, pip, Node, ffmpeg và ffprobe tĩnh, studio, thư viện, `npm ci`, Chromium, `env.sh`, `.core-version`, tar.gz, SHA-256, manifest) trong `dist/core/mac/`
- [ ] T019 [US2] Chạy thử build-mac.sh trên `macos-14` qua `workflow_dispatch` (một lần, kiểm T001c và espeak ≤ 160 byte)
- [ ] T020 [US2] `desktop/core.js` và `main.js`: nhánh macOS của bước cài (`tar -xzf`, `xattr -dr com.apple.quarantine`, 2 lệnh `venv --system-site-packages`, kiểm độ dài đường dẫn espeak); test trong `desktop/test/install.test.js`
- [ ] T021 [US2] `desktop/electron-builder.yml`: `dmg` arm64, `identity: null`, `NSLocalNetworkUsageDescription`

## Phase 5: User Story 3 — Build và phát hành tự động (P3)

**Mục tiêu**: tag `desktop-vX.Y.Z` → Release riêng tư có đủ tệp (SC-004).

**Kiểm độc lập**: `workflow_dispatch` với version `0.1.0-test` cho ra Release nháp đủ tệp.

- [ ] T022 [US3] `.github/workflows/desktop-release.yml` theo R6: `core-linux` (build, smoke-core trong container, credits-check), `core-mac`, `installers` (ma trận, electron-builder, smoke), `release` (Release riêng tư, `SHA256SUMS`); action ghim bản
- [ ] T023 [P] [US3] `.github/workflows/desktop.yml`: nâng `actions/checkout` và `actions/setup-node` lên v5
- [ ] T024 [US3] Chạy `desktop-release.yml` một lần (`workflow_dispatch`, `0.1.0-test`), sửa tới khi đạt; ghi kết quả (dung lượng, thời gian, phút chạy) vào research.md

## Phase 6: Hoàn thiện

- [ ] T025 [P] `CREDITS`: mọi phần mềm và mô hình đi kèm (Ubuntu và gói apt theo nhóm, Python, các gói pip, Node, các gói npm của thư viện, Chromium, ffmpeg GPL kèm đường dẫn mã nguồn, Kokoro Apache-2.0, Whisper MIT, espeak-ng GPL-3.0, thư viện lemo-opuscar MIT); credits-check.py đạt
- [ ] T026 [P] `CLAUDE.md` mục "App desktop": cách build bộ cài, tag phát hành; `desktop/README.md` hoặc `deploy/README.md`: hướng dẫn cài cho người dùng (More info → Run anyway; Open Anyway)
- [ ] T027 Chạy đủ 5 bộ test (`tests/run.sh`, `tests/learn/run.sh`, `tests/ui/run.sh`, `tests/filmcheck/run.sh`, `tests/online/run.sh`) và đối chiếu SC-001…SC-006; ghi phần còn kiểm bằng tay vào quickstart.md

## Dependencies

- Phase 1 (T001) chặn mọi phase sau.
- Phase 2 chặn US1 và US2. T009 dùng cho T022.
- US1 và US2 độc lập với nhau; US3 cần T011, T016 (và T018, T021 cho macOS).
- T025 cần danh sách gói từ T010 và T018.

## Parallel

- T002, T003 cùng lúc. T004, T005, T006, T008, T009 cùng lúc (khác file).
- US1 (T010–T017) và US2 (T018–T021) có thể làm song song sau Phase 2.

## Implementation Strategy

MVP = Phase 1 + 2 + US1: có `.exe` cài được trên Windows. Rồi US2 (macOS), rồi US3 (tự động phát hành). Mỗi lần chạy GitHub Actions tốn phút chạy (macOS gấp 10), nên chỉ chạy T019 và T024 khi phần trước đã đạt ở máy này.
