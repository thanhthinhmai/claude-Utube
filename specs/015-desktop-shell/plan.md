# Implementation Plan: Vỏ app desktop cho Windows (qua WSL) và macOS

**Branch**: `015-desktop-shell` | **Date**: 2026-11-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/015-desktop-shell/spec.md`

## Summary

Thêm thư mục `desktop/`: một app Electron viết bằng JavaScript thuần có `// @ts-check`, không có bước build (giống `app.js`).

- **Logic** nằm trong `desktop/core.js`, không phụ thuộc Electron nên test được bằng `node --test`:
  - đọc và ghi cấu hình;
  - dựng lệnh gọi phần lõi theo hệ điều hành (R1);
  - đọc trạng thái phần lõi;
  - kiểm máy;
  - quyết định khi thoát.
- **Phần Electron** nằm trong `desktop/main.js`:
  - một phiên duy nhất;
  - cửa sổ chờ (`splash.html`), màn hình thiết lập (`setup.html` cùng `preload.js`), cửa sổ chính trỏ vào `127.0.0.1:<cổng>`;
  - icon khay; đóng cửa sổ thì ẩn xuống khay; thoát an toàn;
  - theo dõi phần lõi 10 giây một lần.
- **Gọi phần lõi** (R1): app chỉ gọi các lệnh `app …` của 014.
  - macOS: `sh <studio>/bin/studio app …`.
  - Windows: `wsl.exe -d <bản Linux> --cd <studio> -- sh bin/studio app …`. Thư mục dữ liệu là đường dẫn Linux bên trong bản đó.
- **Phần lõi trả thêm thông tin** (R2): thêm `app check --json` (danh sách công cụ còn thiếu) và tên các việc đang chạy vào `app status --json`.
- **Thiết lập lần đầu** (R3):
  - Windows: đọc `wsl.exe -l -v` (đầu ra mã hoá UTF-16LE), giữ các bản Linux có VERSION là 2. Nút "Bật WSL" chạy `Start-Process wsl -ArgumentList '--install --no-distribution' -Verb RunAs` qua PowerShell; Windows hiện hộp hỏi quyền quản trị (hiến pháp 2.2.0).
  - Cả hai hệ điều hành: tìm studio (mặc định `~/claude-Utube`), chạy `app check --json`, chọn thư mục dữ liệu, xem dung lượng trống bằng `df`.
- **Kiểm trên Windows và macOS thật** (R4): GitHub Actions `.github/workflows/desktop.yml` cho `windows-latest` và `macos-latest`.
  - Chạy test logic, rồi chạy thử Electron với một **phần lõi giả** (`desktop/test/fake-core.mjs`, trả lời `app start|status|stop` và `/api/v1/health`), qua biến `CU_CORE_CMD`.
  - Kiểm: mở được, mở lần hai, thoát không để lại tiến trình nào.
  - Đường gọi WSL thật không chạy được trên máy của GitHub (không có WSL2), nên được test bằng logic và bằng tay trên máy Windows của người dùng.
- **Test logic** của `desktop/` chạy trong `sh tests/ui/run.sh`, nên vẫn là 5 bộ test như cũ.

Chi tiết: [research.md](research.md) · [data-model.md](data-model.md) · [contracts/](contracts/) · [quickstart.md](quickstart.md).

## Technical Context

**Language/Version**: JavaScript (ES2022, CommonJS cho Electron main), có `// @ts-check`. Node 22. Python 3.12 cho 2 lệnh mới của phần lõi.

**Primary Dependencies**: Electron 33.2.1 (ghim đúng bản, chỉ cài trong `desktop/` để chạy app và trên GitHub Actions). Không có framework giao diện; các trang HTML viết tay.

**Storage**: cấu hình app ở `app.getPath("userData")/config.json` (Windows `%APPDATA%/ClaudeUtube`, macOS `~/Library/Application Support/ClaudeUtube`). Dữ liệu của xưởng vẫn do phần lõi giữ (014).

**Testing**:
- `node --test desktop/test/*.test.js`: logic, không cần Electron. Gọi từ `tests/ui/run.sh`.
- GitHub Actions: chạy thử Electron trên Windows và macOS với phần lõi giả.
- Phần lõi (Python): test trong `tests/online/test_host.py`.

**Target Platform**: Windows 10 22H2 hoặc 11 bản 64-bit (phần lõi trong WSL2); macOS trên chip Apple (phần lõi chạy thẳng).

**Project Type**: app desktop (vỏ) bọc dịch vụ có sẵn.

**Performance Goals**: mở app tới khi có giao diện < 30 giây (SC-001). Phần lõi tự sẵn sàng trong khoảng 2 giây (014).

**Constraints**:
- Bật WSL chỉ khi người dùng bấm và đồng ý quyền quản trị (hiến pháp 2.2.0).
- Cửa sổ chính chỉ mở trang `127.0.0.1` (FR-003).
- Không bộ cài, không cập nhật (016).

**Scale/Scope**: một người dùng trên mỗi máy.

## Constitution Check

| Nguyên tắc | Kết quả |
|---|---|
| I. Spec là nguồn sự thật | ✓ Đã làm rõ 3 câu. Hiến pháp đã sửa trước khi plan (2.2.0) |
| II. Không đoán | ✓ có điều kiện. Chưa thử trên máy này: Electron trên Windows và macOS. GitHub Actions kiểm (FR-016). Đường WSL thật không chạy được trên máy của GitHub; ghi rõ, kiểm bằng tay trên máy Windows của người dùng (quickstart) |
| III. MVP theo story | ✓ US1 tự chạy được khi đã có cấu hình (tự tạo cấu hình bằng tay hay bằng biến môi trường). US2, US3 thêm sau |
| IV. Đo được | ✓ SC-002 và SC-004 có test logic; SC-001 và SC-003 kiểm trên GitHub Actions và bằng tay |
| V. Đơn giản | ✓ JavaScript thuần không bước build; app chỉ gọi lệnh của 014; không framework giao diện. Một mục ở Complexity Tracking |
| VI. Thư viện gốc | ✓ Không đụng `lib/` |
| VII. Một bộ máy dựng hình | ✓ Electron chỉ là cửa sổ app. Dựng phim vẫn bằng thư viện (Chromium của Playwright) |
| VIII–IX | ✓ Không đổi |
| Phần mềm hệ thống (2.2.0) | ✓ Nút "Bật WSL" nói rõ sẽ bật gì và cần khởi động lại máy; Windows hỏi quyền quản trị; không bật khi chưa bấm |
| Bản quyền, nội dung | ✓ Icon tự vẽ; Electron dùng giấy phép MIT, ghi vào `CREDITS` |

Kiểm lại sau thiết kế: đạt.

## Project Structure

### Documentation (this feature)

```text
specs/015-desktop-shell/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/
│   └── core.md      # lệnh của phần lõi mà app gọi; app check; app status mở rộng; IPC của setup.html
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
desktop/
├── package.json                 # electron 33.2.1 (devDependency), scripts start/test
├── main.js                      # Electron: một phiên, cửa sổ chờ, thiết lập, cửa sổ chính, khay, thoát, theo dõi
├── core.js                      # logic không phụ thuộc Electron (R1–R3)
├── preload.js                   # cầu nối của setup.html và stopped.html
├── splash.html · setup.html · stopped.html
├── assets/icon.png · trayTemplate.png · trayTemplate@2x.png · tray.png
├── test/core.test.js            # node --test
└── test/fake-core.mjs           # phần lõi giả cho GitHub Actions
tools/studio/studio/host.py      # sửa: check() cho app check --json; status() thêm tên việc đang chạy
tools/studio/studio_cli.py       # sửa: app check [--json]
.github/workflows/desktop.yml    # Windows và macOS: test logic, chạy thử Electron với phần lõi giả
tests/ui/run.sh                  # sửa: chạy thêm node --test desktop/test
CLAUDE.md · CREDITS              # sửa: cách chạy app desktop khi phát triển; giấy phép Electron
```

**Structure Decision**:
- `desktop/` đứng riêng ở gốc repo, giống neb. Code nghiệp vụ không có logic riêng cho desktop.
- Bản VPS không đổi.

## Complexity Tracking

| Vi phạm | Vì sao cần | Cách đơn giản hơn bị loại vì |
|---|---|---|
| Thêm một hệ sinh thái mới (Node, Electron) vào repo vốn là Python | Spec đòi một app desktop thật, giống neb, chạy trên Windows và macOS | Một trang mở bằng trình duyệt không có icon khay, không có một phiên duy nhất, không thoát an toàn, và không bật được WSL. Các vỏ khác (Tauri, pywebview) thì người dùng chưa quen, còn neb đã chạy Electron |
