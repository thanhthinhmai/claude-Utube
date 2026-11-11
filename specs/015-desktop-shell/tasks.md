# Tasks: Vỏ app desktop cho Windows (qua WSL) và macOS

**Input**: `specs/015-desktop-shell/` (spec.md, plan.md, research.md, data-model.md, contracts/core.md, quickstart.md). Tính năng này xây trên 014 (`app start|status|stop`).

**Tests**: có.
- Logic của vỏ: `node --test desktop/test`, gọi từ `sh tests/ui/run.sh`.
- Hai lệnh mới của phần lõi: `tests/online/test_host.py`.
- Electron trên Windows và macOS: GitHub Actions (`desktop.yml`).

**Luật chung cho mọi task**:
- App chỉ gọi các lệnh `app …` của phần lõi; không có logic nghiệp vụ trong `desktop/`.
- Bật WSL chỉ khi người dùng bấm và đồng ý quyền quản trị (hiến pháp 2.2.0).
- Không sửa `lib/`. Sau mỗi phase, 5 bộ test phải đạt. Commit sau mỗi phase.

## Phase 1: Setup

- [ ] T001 [P] Tạo `desktop/package.json`:
  - tên `claude-utube-desktop`, `main` là `main.js`;
  - `devDependencies` chỉ có `electron` ghim đúng bản `33.2.1`;
  - scripts `start` (`electron .`) và `test` (`node --test test`).

  Chạy `npm install --package-lock-only` để có `package-lock.json`. Thêm `desktop/node_modules/` vào `.gitignore`.
- [ ] T002 [P] Vẽ icon bằng code (Python thuần, ghi PNG bằng zlib, không thư viện ngoài) trong `desktop/assets/make_icons.py`, rồi tạo:
  - `icon.png` (512×512);
  - `tray.png` (32×32);
  - `trayTemplate.png` (16×16) và `trayTemplate@2x.png` (32×32): đen trên nền trong suốt.

  Thêm dòng Electron (MIT) vào `CREDITS`.

## Phase 2: Foundational

- [ ] T003 Trong `tools/studio/studio/host.py` và `tools/studio/studio_cli.py`, viết:
  - `app check [--json]` → `{"ok", "missing", "data_default"}` (R2);
  - thêm `jobs: [{id, name, status}]` (các việc `running` có `charged`) vào `status()`.

  Test trong `tests/online/test_host.py::Check`: `app check --json` có khoá; thiếu ffmpeg thì `ok` là `false`; `app status --json` có `jobs` chứa tên một việc đang chạy.
- [ ] T004 Viết `desktop/core.js` (`// @ts-check`, CommonJS, không import Electron):
  - `loadConfig(dir)` và `saveConfig(dir, cfg)`; `configUsable(cfg, exists)`;
  - `coreCommand(cfg, args, env)` theo R1, gồm `CU_CORE_CMD`;
  - `parseUrl(stdout)`; `parseStatus(stdout)`;
  - `parseWslList(buf)`: UTF-16LE, có hay không có BOM; giữ bản có VERSION là 2; đánh dấu bản mặc định;
  - `wslStatusChecks(stdout, code)`;
  - `enableWslCommand()`;
  - `quitPlan(status)` → `{ask: bool, names: [str], stopArgs: [...]}`;
  - `isAppUrl(url, port)`;
  - `expandHome(path, home)`.

## Phase 3: User Story 1 - Mở app là có xưởng (P1) 🎯 MVP

**Goal**: mở app → cửa sổ chờ → phần lõi chạy → cửa sổ chính; một phiên duy nhất; liên kết ngoài mở bằng trình duyệt; dùng lại phần lõi đang chạy.

**Independent Test**: với cấu hình có sẵn và `CU_CORE_CMD` trỏ vào phần lõi giả, `npx electron desktop --smoke` in đủ 3 dòng smoke và thoát mã 0 (trên GitHub Actions cho Windows và macOS).

### Tests for User Story 1

- [ ] T005 [P] [US1] Viết `desktop/test/core.test.js` (node --test):
  - `coreCommand` cho macOS và Windows (đường dẫn, `--data`, `CU_CORE_CMD`);
  - `parseUrl`; `parseStatus` (có và không có `jobs`);
  - `parseWslList` với đầu ra UTF-16LE mẫu (có BOM, có dấu `*`, có bản VERSION 1 bị bỏ);
  - `isAppUrl` (`127.0.0.1` đúng cổng là đúng; cổng khác, `localhost.evil`, `https://youtube.com` là sai);
  - `quitPlan` (có việc thì hỏi và nêu tên; không có việc thì không hỏi; SC-004);
  - `configUsable`; `expandHome`.

  Sửa `tests/ui/run.sh` để chạy `node --test desktop/test` khi có `node` (không có thì in "skipped").
- [ ] T006 [P] [US1] Viết `desktop/test/fake-core.mjs`, một phần lõi giả theo contracts/core.md:
  - `app start` mở một máy chủ HTTP tách riêng (trang tiêu đề "fake core" và `/api/v1/health`), ghi `pid` và cổng vào thư mục `--data`, in `URL:`;
  - `app status --json`;
  - `app stop` giết máy chủ đó;
  - `app check --json`.

### Implementation for User Story 1

- [ ] T007 [US1] Viết `desktop/main.js`:
  - `requestSingleInstanceLock`, và `second-instance` thì đưa cửa sổ lên trước;
  - `splash.html` hiện các bước;
  - chạy `app start` qua `coreCommand`, đọc địa chỉ, rồi mở cửa sổ chính với `contextIsolation`, `sandbox`, không `nodeIntegration`;
  - `setWindowOpenHandler` và `will-navigate` mở liên kết ngoài bằng `shell.openExternal`;
  - lỗi hay quá 60 giây thì `splash.html` hiện lỗi, các dòng log cuối, và các nút Thử lại, Mở thư mục log, Thoát;
  - cấu hình chưa dùng được thì sang màn hình thiết lập (US2).
- [ ] T008 [US1] Thêm chế độ `--smoke` vào `desktop/main.js` theo contracts/core.md: tự tạo cấu hình với phần lõi giả; kiểm tiêu đề cửa sổ; chạy bản thứ hai; thoát; in các dòng `smoke:`.
- [ ] T009 [US1] Viết `.github/workflows/desktop.yml` theo R4: ma trận `windows-latest` và `macos-latest`; chạy khi đẩy nhánh `0[0-9][0-9]-desktop-*` và khi bấm chạy tay; các bước `npm ci`, `node --test`, `npx electron . --smoke`, rồi kiểm không còn tiến trình `fake-core`.

**Checkpoint**: US1 qua GitHub Actions trên Windows và macOS.

## Phase 4: User Story 2 - Thiết lập lần đầu (P2)

**Goal**: màn hình thiết lập kiểm máy, có nút Bật WSL (Windows), chọn bản Linux và studio, chọn thư mục dữ liệu, xem dung lượng trống, bấm Bắt đầu.

**Independent Test**:
- test logic: đầu ra mẫu của `wsl --status` và `-l -v` → danh sách kiểm đúng; thiếu WSL thì có mục "Bật WSL";
- smoke: không có cấu hình → hiện màn hình thiết lập (chế độ smoke kiểm có cửa sổ `setup.html`).

### Tests for User Story 2

- [ ] T010 [P] [US2] Thêm vào `desktop/test/core.test.js`:
  - `wslStatusChecks` (chưa có WSL; WSL1; chưa bật ảo hoá; đủ);
  - `machineChecks` gộp kết quả `app check` và dung lượng trống (dưới 5 GB thì thiếu);
  - `enableWslCommand` đúng lệnh PowerShell có `-Verb RunAs`.

### Implementation for User Story 2

- [ ] T011 [US2] Viết `desktop/setup.html` (tiếng Anh, giống giao diện của xưởng):
  - danh sách kiểm có trạng thái đạt hay thiếu và cách sửa;
  - Windows: nút "Turn on WSL" với hộp xác nhận nói rõ sẽ bật gì và cần khởi động lại máy; ô chọn bản Linux;
  - đường dẫn studio, thư mục dữ liệu (kèm dung lượng trống), nút Start.

  Viết `desktop/preload.js` theo contracts/core.md, và các `ipcMain.handle` tương ứng trong `main.js`.
- [ ] T012 [US2] Trong `desktop/main.js`, thêm mục khay "Change setup": dừng phần lõi (hỏi như khi thoát), mở `setup.html`, không xoá dữ liệu. Thêm vào smoke: không có cấu hình thì `setup.html` hiện ra (`smoke: setup ok`), rồi smoke tự hoàn tất thiết lập với phần lõi giả.

## Phase 5: User Story 3 - Icon khay và thoát an toàn (P3)

**Goal**: icon khay; đóng cửa sổ thì ẩn; thoát có hỏi; theo dõi phần lõi; `stopped.html`.

**Independent Test**:
- test logic `quitPlan`;
- smoke: đóng cửa sổ thì app vẫn chạy (`smoke: hide ok`); phần lõi giả có một việc thì thoát hỏi (smoke tự trả lời qua biến `CU_SMOKE_ANSWER`); phần lõi giả bị giết thì `stopped.html` hiện (`smoke: stopped ok`).

### Implementation for User Story 3

- [ ] T013 [US3] Trong `desktop/main.js`:
  - icon khay với các mục của FR-011 (macOS dùng `trayTemplate`);
  - đóng cửa sổ thì `hide()`, kèm thông báo lần đầu;
  - `before-quit` đi qua `quitPlan` và `dialog.showMessageBox`, rồi `app stop [--force]`;
  - theo dõi phần lõi 10 giây một lần, và tải `stopped.html` khi phần lõi dừng.

  Viết `desktop/stopped.html` với nút Restart.
- [ ] T014 [US3] Mở rộng phần lõi giả (`--job` khiến `app status` có một việc đang chạy) và chế độ smoke theo Independent Test ở trên. Cập nhật `desktop.yml` để kiểm các dòng smoke mới.

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T015 [P] Trong `CLAUDE.md`, thêm mục "App desktop (specs/015)": cách chạy khi phát triển (`cd desktop && npm install && npx electron .`), Windows dùng bản Linux WSL có studio, GitHub Actions `desktop.yml`. Thêm `desktop/` vào mục Cấu trúc.
- [ ] T016 Chạy đủ 5 bộ test. Đẩy nhánh để GitHub Actions chạy trên Windows và macOS, rồi ghi kết quả (đạt hay không, thời gian, phút đã dùng) vào cuối `specs/015-desktop-shell/quickstart.md`. Đối chiếu FR và SC, ghi bảng vào cuối `specs/015-desktop-shell/tasks.md`. Bài chạy bằng tay trên máy Windows và Mac thật (quickstart mục 3–4) cần người dùng làm.

## Dependencies & Execution Order

- Phase 1 → 2 → US1 → US2 → US3 → Polish.
- T004 trước T005, T007; T006 trước T008. T009 cần T008.
- US2 và US3 đều sửa `main.js`, nên làm lần lượt.

## Implementation Strategy

1. **MVP**: Phase 1 + 2 + US1, qua GitHub Actions trên cả hai hệ điều hành.
2. **US2**: thiết lập lần đầu và bật WSL.
3. **US3**: icon khay, thoát an toàn, theo dõi phần lõi.
4. Polish: tài liệu, kết quả GitHub Actions, bài chạy bằng tay của người dùng.
