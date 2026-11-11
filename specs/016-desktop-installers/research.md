# Research: Bộ cài app desktop (016)

## R1. Phần lõi Linux cho Windows

**Decision**: `deploy/core.Dockerfile`:
- `FROM ubuntu:24.04`.
- `apt-get install` các gói: `python3 python3-venv python3-pip ffmpeg git ca-certificates curl xz-utils bubblewrap socat fontconfig fonts-noto-core fonts-noto-cjk sudo`, cùng các thư viện Chromium cần (`npx playwright install-deps chromium`).
- Node 22: tệp `node-v22.x-linux-x64.tar.xz` chính thức, giải nén vào `/usr/local`.
- Người dùng `studio` (uid 1000). `/etc/wsl.conf`:

  ```ini
  [user]
  default=studio
  [boot]
  systemd=false
  [interop]
  appendWindowsPath=false
  ```
- Studio:
  - `COPY` mã nguồn (thư mục build là `git archive` của tag) vào `/home/studio/claude-Utube`;
  - chạy `sh bin/studio setup`, tức clone thư viện đúng `LIB_COMMIT` (chỉ tải, không cài phần mềm hệ thống, vì đang ở trong image);
  - chạy `sh bin/studio deps voice music`, `deps ui`, `deps online`, `deps learn`;
  - Chromium của Playwright vào `/home/studio/.cache/ms-playwright`.
- **Không có mô hình**: xoá `lib/lemo-opuscar/core/tts/*.onnx|*.bin` và `~/.cache/huggingface` nếu có (R3).
- Ghi tệp `/home/studio/claude-Utube/.core-version` chứa phiên bản của bản phát hành.

**Đóng gói**: `docker create` rồi `docker export` (rootfs dạng tar), nén `gzip -6`. Ghi `core-manifest.json`, gồm phiên bản, `sha256`, kích thước nén và kích thước giải nén.

**Cài trong app**:
1. Giải nén gzip bằng Node `zlib` dạng luồng, ra `%LOCALAPPDATA%\ClaudeUtube\tmp\core.tar`.
2. `wsl --import ClaudeUtube %LOCALAPPDATA%\ClaudeUtube\wsl <tar> --version 2`.
3. Xoá tệp tar.

Không dựa vào việc `wsl --import` có đọc thẳng `.tar.gz` hay không (khác nhau giữa các bản WSL).

**Kiểm khi implement (T001)**:
- Kích thước tar.gz thật. Phải ≤ 1,9 GB; vượt thì bỏ `deps learn` (chỉ cần khi học phong cách từ YouTube) rồi đo lại.
- Container của image chạy được `app start`, `/api/v1/health` và `app stop`.

## R2. Phần lõi macOS

**Decision**: `desktop/core-build/build-mac.sh` chạy trên máy `macos-14` (arm64) của GitHub:
- **Python**: `cpython-3.12.x+<ngày>-aarch64-apple-darwin-install_only.tar.gz` của python-build-standalone (giấy phép PSF cùng các thành phần đi kèm, ghi vào `CREDITS`). `python/bin/python3 -m pip install` cài thẳng vào nó:
  - `tools/requirements-ui.txt`, `requirements-online.txt`, `requirements-learn.txt`;
  - các tệp `requirements*.txt` của thư viện (core, voice, music).
- **Node**: `node-v22.x-darwin-arm64.tar.gz` chính thức (MIT).
- **ffmpeg, ffprobe**: bản tĩnh arm64 từ gói npm `ffmpeg-static` 5.2.0 và `@ffprobe-installer/darwin-arm64`. Giấy phép GPL-3.0, phát lại được, kèm tệp giấy phép và đường dẫn tới mã nguồn trong `CREDITS`.
  - **Kiểm khi implement (T001)**: chạy được trên `macos-14`; nếu nguồn này không còn bản arm64 thì dừng và hỏi.
- **Studio và thư viện**: như R1, kể cả `node_modules` của thư viện (`npm ci`) và Chromium của Playwright ở `ms-playwright/` trong phần lõi (`PLAYWRIGHT_BROWSERS_PATH`).
- **Không venv lúc build**. Lúc cài, chạy `python3 -m venv --system-site-packages` cho `tools/.venv` và `lib/lemo-opuscar/.venv`, vì `bin/studio` và thư viện tìm đúng hai đường dẫn đó. Cách này tránh đường dẫn tuyệt đối của máy build.
- **`bin/studio` trên phần lõi Mac**: thêm `<core>/node/bin` và `<core>/ffmpeg` vào đầu `PATH`, qua tệp `<core>/env.sh` được nạp khi có (sửa nhỏ trong `bin/studio`). App cũng đặt `PATH` khi gọi phần lõi.
- **Cài trong app**: giải nén vào `~/Library/Application Support/ClaudeUtube/core-<ver>/` bằng `tar -xzf` (lệnh có sẵn của macOS), rồi tạo 2 venv. Gỡ cờ quarantine bằng `xattr -dr com.apple.quarantine` cho phần lõi đã giải nén (giống neb).

**Đường dẫn espeak** (giới hạn 160 byte của thư viện): `~/Library/Application Support/ClaudeUtube/core-0.1.0/python/lib/python3.12/site-packages/espeakng_loader/espeak-ng-data` dài khoảng 120 byte với tên người dùng ngắn. Màn hình thiết lập kiểm độ dài thật và báo nếu vượt.

## R3. Mô hình

**Decision**:
- **Kokoro**: `sh lib/lemo-opuscar/tools/fetch.sh voice` (thư viện tải `voice.tar` từ bản phát hành công khai `lemomo-ai/lemo-opuscar`, tag `assets`, có SHA-256 trong `tools/assets.json`). Tải tiếp khi mất mạng: chạy lại lệnh.
- **Whisper**: lệnh mới `sh bin/studio app models`, gọi `faster_whisper.utils.download_model` cho `base.en` và `base` vào bộ nhớ đệm HuggingFace của người dùng `studio`. Bản `small` (tiếng Trung) được tải khi cần, ở lần đầu `asr_check` dùng nó. HuggingFace tự kiểm tệp; lệnh in tiến độ theo từng tệp.
- Màn hình thiết lập chạy hai lệnh này sau khi cài phần lõi, hiện tiến độ, và cho bấm "Thử lại" khi lỗi mạng.

## R4. Bộ cài (electron-builder)

**Decision**: `desktop/electron-builder.yml`:
- **Chung**: `appId: com.claudeutube.desktop`, `productName: claude-Utube`; `asar: false`, vì `core.js` và `main.js` nhỏ, không cần asar; `extraResources: [{from: "../dist/core/${os}", to: "core"}]`.
- **Windows**: `nsis: {oneClick: false, perMachine: false, allowToChangeInstallationDirectory: false, include: installer.nsh}`; `target: nsis` (x64).
- **macOS**: `target: dmg` (arm64); `identity: null` để ký ad-hoc (electron-builder ký `-`); `extendInfo.NSLocalNetworkUsageDescription`.
- `installer.nsh`, macro `customUnInstall`: hộp hỏi "Remove the studio's Linux and your data?" (mặc định No); Yes thì chạy `wsl --unregister ClaudeUtube`.
- **Giới hạn NSIS** khoảng 2 GB; tệp phần lõi ≤ 1,9 GB (R1).

## R5. Sandbox Bash của agent

**Decision**:
- `host.part_env` đặt `STUDIO_AGENT_SANDBOX=1` khi `shutil.which("bwrap") and shutil.which("socat")`, hoặc khi `sys.platform == "darwin"`.
- `agent.py` truyền `sandbox={"enabled": True, "autoAllowBashIfSandboxed": True, "allowUnsandboxedCommands": False, "network": {"allowLocalBinding": True}}`, và quyền ghi qua luật `Edit(<WORK>/**)` (theo tài liệu `SandboxSettings`: giới hạn ghi tệp đặt bằng luật Edit).
- Không có sandbox thì giữ cảnh báo của 014.
- **Kiểm khi implement (T001)**: trong container của phần lõi Linux, chạy `claude -p` bản thật? Không làm được, vì cần tài khoản. Thay vào đó, kiểm cơ chế mà Claude Code dùng: `bwrap` chặn ghi ngoài thư mục việc và vẫn cho kết nối tới `127.0.0.1` (`sh bin/studio job step` qua proxy). Lời gọi Claude thật với sandbox được kiểm trong bài chạy bằng tay (SC-003). Nếu Claude Code từ chối chạy sandbox trong WSL (thiếu `CAP_SYS_ADMIN` hay user namespace), ghi lại, rồi tắt sandbox kèm cảnh báo; không chặn cả 016.

## R6. Phát hành

**Decision**: `.github/workflows/desktop-release.yml`:
- **Khi chạy**: `push: tags: ["desktop-v*"]`, và `workflow_dispatch` (input `version`).
- **Các job**:
  1. **`core-linux`** (`ubuntu-latest`):
     - `build-linux.sh`;
     - `smoke-core.sh` trong container: `app check` đạt; `app start` rồi `/api/v1/health`; tạo chủ xưởng qua API rồi `app stop`; kiểm bwrap chặn ghi;
     - `credits-check.py`;
     - lưu artifact `core-linux`.
  2. **`core-mac`** (`macos-14`): `build-mac.sh`; `smoke-core.sh` (chạy thẳng); `credits-check.py`; artifact `core-mac`.
  3. **`installers`** (ma trận Windows và macOS; cần job 1 hoặc 2):
     - tải artifact phần lõi vào `dist/core/<os>`;
     - `npx electron-builder`;
     - smoke: chạy app đã cài ở chế độ `--smoke` với phần lõi giả (như 015). Bước cài phần lõi thật cần WSL2 (Windows) hoặc được kiểm ở job 2 (macOS).
  4. **`release`**: `softprops/action-gh-release` (ghim bản), tạo Release riêng tư `desktop-vX.Y.Z` với 2 bộ cài, 2 `core-manifest.json` và `SHA256SUMS`. Tệp phần lõi đã nằm trong bộ cài, nên không đưa lên riêng.
- **Phút chạy**: mỗi bản phát hành khoảng 25 phút Linux, 25 phút macOS (tính gấp 10) và 10 phút Windows (tính gấp 2). Chỉ chạy khi có tag hoặc bấm tay.

## R7. Cài lại phần lõi (Windows) mà giữ dữ liệu

**Decision**: khi `core-version` trong bản Linux khác `core-manifest.json` của bộ cài:
1. Hỏi người dùng (cài lại mất vài phút; dữ liệu được giữ).
2. `app stop`.
3. `wsl -d ClaudeUtube -- tar -czf /mnt/<ổ Windows>/…/data-backup.tgz -C <thư mục dữ liệu> .`; kiểm chỗ trống trên ổ Windows trước.
4. `wsl --unregister ClaudeUtube`, rồi `--import` bản mới.
5. Giải nén lại dữ liệu vào bản mới, chạy `app start` (014 tự nâng cấp cơ sở dữ liệu và sao lưu, FR-006 của 014), rồi xoá tệp sao lưu.

macOS: phần lõi mới nằm ở `core-<ver>` mới, dữ liệu vốn ở ngoài phần lõi. Xoá `core-<cũ>` sau khi bản mới chạy được.
