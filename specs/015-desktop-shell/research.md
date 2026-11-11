# Research: Vỏ app desktop (015)

## R1. Gọi phần lõi theo hệ điều hành

**Decision**: `core.coreCommand(config, args)` trả `{file, args}`:
- **macOS**: `{file: "/bin/sh", args: ["<studio>/bin/studio", "app", ...args, "--data", "<data>"]}`. `PATH` thêm `/opt/homebrew/bin` và `/usr/local/bin`, vì app mở từ Finder không có PATH của shell.
- **Windows**: `{file: "wsl.exe", args: ["-d", "<distro>", "--cd", "<studio>", "--", "sh", "bin/studio", "app", ...args, "--data", "<data>"]}`. `<studio>` và `<data>` là đường dẫn Linux bên trong bản đó; `~` được thay bằng `$HOME` của bản đó, lấy một lần lúc thiết lập bằng `wsl.exe -d <distro> -- sh -c 'echo $HOME'`.
- **Biến `CU_CORE_CMD`** (chuỗi JSON, ví dụ `["node","desktop/test/fake-core.mjs"]`): thay phần đầu của lệnh. Chỉ dùng cho test và GitHub Actions.

App gọi:
- `app start` (đợi kết quả, rồi đọc dòng `URL:`);
- `app status --json` (10 giây một lần, và trước khi thoát);
- `app stop [--force]`;
- `app check --json` (lúc thiết lập).

Phần lõi tự chạy nền, nên app không giữ tiến trình nào của phần lõi.

**Địa chỉ**: dòng `URL: http://127.0.0.1:<cổng>` của `app start`, hoặc `url` của `app status --json`. Trên Windows, WSL2 tự chuyển `127.0.0.1` của Windows vào bản Linux (chế độ mạng mặc định, `localhostForwarding`).

**Alternatives considered**: giữ các tiến trình của phần lõi làm tiến trình con của Electron, như neb. Bị loại vì phần lõi trên Windows nằm trong WSL, khác tiến trình; và 014 đã có tiến trình giám sát riêng.

## R2. Phần lõi trả thêm

**Decision**:
- `app check [--json]`: `{"ok": bool, "missing": [str], "data_default": str}`, gọi `host.check_tools()` của 014.
- `app status --json` thêm `jobs`: `[{"id", "name", "status"}]` cho các việc `running` của worker. App dùng danh sách này để nêu tên việc khi hỏi lúc thoát (FR-013).

## R3. Thiết lập lần đầu

**Windows**:
1. `wsl.exe --status`. Lệnh lỗi, hoặc đầu ra báo chưa bật, thì trạng thái là "chưa có WSL". Đầu ra có "virtualization" hay "Virtual Machine Platform" chưa bật thì trạng thái là "chưa bật ảo hoá".
2. `wsl.exe -l -v`: đầu ra mã hoá UTF-16LE. Bỏ ký tự rỗng, đọc từng dòng `* NAME STATE VERSION`, giữ các bản có VERSION là 2.
3. Nút "Bật WSL":
   - hộp xác nhận nói rõ "Windows sẽ bật WSL2 và Virtual Machine Platform, cần quyền quản trị, rồi khởi động lại máy";
   - sau đó chạy `powershell -NoProfile -Command "Start-Process wsl -ArgumentList '--install','--no-distribution' -Verb RunAs -Wait"`, và Windows hiện hộp hỏi quyền quản trị;
   - xong thì báo khởi động lại máy.
   - Nếu người dùng từ chối quyền quản trị, PowerShell báo lỗi; app báo "đã huỷ" và không làm gì thêm.
4. Người dùng chọn bản Linux, rồi app tìm studio: thử `~/claude-Utube` (có `bin/studio`), cho sửa đường dẫn.

**macOS**: tìm studio ở `~/claude-Utube`, cho sửa đường dẫn.

**Cả hai**:
- `app check --json`; mỗi mục thiếu hiện câu hướng dẫn của 014.
- Thư mục dữ liệu mặc định lấy từ `data_default` của `app check`.
- Dung lượng trống: `df -Pk <thư mục>` qua cùng đường gọi (macOS: thẳng; Windows: trong WSL). Cần ít nhất 5 GB.
- Bấm Bắt đầu thì ghi cấu hình.

## R4. Kiểm trên Windows và macOS (GitHub Actions)

**Decision**: `.github/workflows/desktop.yml`:
- **Khi chạy**: `push` lên các nhánh `0[0-9][0-9]-desktop-*`, và `workflow_dispatch`.
- **Ma trận**: `windows-latest`, `macos-latest`.
- **Các bước**:
  1. checkout;
  2. setup-node 22;
  3. `npm ci` trong `desktop/`;
  4. `node --test desktop/test`;
  5. `npx electron desktop --smoke`, với `CU_CORE_CMD='["node","desktop/test/fake-core.mjs"]'` và `CU_CONFIG_DIR=<tạm>`.

Ở **chế độ smoke**, `main.js`:
- tự tạo cấu hình, rồi mở app;
- đợi cửa sổ chính tải xong trang của phần lõi giả (tiêu đề "fake core"), ghi `smoke: window ok`;
- chạy chính nó lần nữa và đợi bản thứ hai thoát trong 10 giây (`smoke: second instance ok`);
- gọi thoát, ghi `smoke: quit ok`, và thoát với mã 0.

Bước sau trong workflow kiểm `fake-core` không còn chạy:
- Windows: `Get-Process node` không còn tiến trình của phần lõi giả;
- macOS: `pgrep -f fake-core` trả rỗng.

**Giới hạn**: máy Windows của GitHub không có WSL2 (không có ảo hoá lồng nhau), nên đường gọi `wsl.exe` thật chỉ được test bằng logic (lệnh dựng ra, đọc đầu ra UTF-16LE). Bài chạy thật trên máy Windows của người dùng nằm trong quickstart. macOS có thể chạy thêm phần lõi thật sau này (016); ở 015 dùng phần lõi giả.

**Chi phí**: mỗi lần chạy khoảng 5 phút trên Windows và khoảng 5 phút trên macOS. Với repo riêng tư, phút macOS tính gấp 10 lần. Workflow không chạy ở mọi lần đẩy.

## R5. Cửa sổ, khay, thoát

- **Một phiên duy nhất**: `app.requestSingleInstanceLock()`; sự kiện `second-instance` thì hiện và đưa cửa sổ chính lên trước.
- **Cửa sổ chính**: `webPreferences {contextIsolation: true, nodeIntegration: false, sandbox: true}`. `setWindowOpenHandler` và `will-navigate`: địa chỉ không phải `http://127.0.0.1:<cổng>` thì `shell.openExternal` và chặn trong cửa sổ.
- **Đóng cửa sổ**: `preventDefault` rồi `hide()`. Lần đầu thì hiện thông báo một lần (`Notification`, hoặc `tray.displayBalloon` trên Windows), và ghi `trayNoticeShown` vào cấu hình.
- **Thoát**:
  - chạy `app status --json`; có việc thì hiện `dialog.showMessageBox` nêu tên việc (Huỷ hoặc Thoát);
  - đồng ý thì `app stop --force`, không có việc thì `app stop`;
  - rồi `app.exit(0)`. `before-quit` đi qua cùng đường này, kể cả khi hệ điều hành yêu cầu thoát.
- **Theo dõi**: mỗi 10 giây gọi `app status --json`. Phần lõi không còn chạy thì cửa sổ chính tải `stopped.html` với nút "Khởi động lại" (gọi `app start`).
- **Icon khay**: macOS dùng `trayTemplate.png` (tự đổi màu theo nền); Windows dùng `tray.png`. Các mục theo FR-011.
- **Mở thư mục**:
  - macOS: `shell.openPath`;
  - Windows: thư mục nằm trong WSL, mở bằng `\\wsl.localhost\<distro>\<đường dẫn>` qua `shell.openPath`.
