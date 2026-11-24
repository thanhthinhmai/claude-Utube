# desktop/: app desktop, bộ cài, license, chế độ Client

Chi tiết của specs/015–018. Luật chung ở `CLAUDE.md` gốc.

### App desktop (specs/015)
- `desktop/`: vỏ Electron (JavaScript thuần có `@ts-check`). Logic trong `desktop/core.js` (test: `node --test desktop/test/*.test.js`, đã nằm trong `tests/ui/run.sh`); cửa sổ, khay, thoát trong `desktop/main.js`. App chỉ gọi `sh bin/studio app …` của 014: macOS chạy thẳng, Windows chạy trong WSL2 (`wsl.exe -d <bản Linux> --cd <studio> -- sh bin/studio app …`).
- Chạy khi phát triển: `cd desktop && npm ci && npx electron .`. Terminal của VS Code đặt sẵn `ELECTRON_RUN_AS_NODE=1`, nên phải chạy `env -u ELECTRON_RUN_AS_NODE npx electron .`. Chạy thử không cần phần lõi thật: `CU_CONFIG_DIR=$(mktemp -d) CU_CORE_CMD='["node","test/fake-core.mjs"]' npx electron . --smoke`.
- GitHub Actions `.github/workflows/desktop.yml` chạy smoke trên Windows và macOS khi đẩy nhánh `NNN-desktop-*` hoặc bấm chạy tay (tốn phút chạy, macOS tốn gấp 10 lần).
- Bật WSL chỉ khi người dùng bấm "Turn on WSL" và đồng ý quyền quản trị (hiến pháp 2.2.0).

### Bộ cài (specs/016)
- Bộ cài chứa sẵn phần lõi: Windows là bản Linux `ClaudeUtube` (`deploy/core.Dockerfile`, `desktop/core-build/build-linux.sh`, cài bằng `wsl --import`); macOS là thư mục có Python, Node, FFmpeg riêng (`build-mac.sh`, giải nén vào `~/Library/Application Support/ClaudeUtube-core/<bản>`). Màn hình thiết lập cài phần lõi rồi tải mô hình (`fetch.sh voice`, `sh bin/studio app models`).
- Phát hành: gắn tag `desktop-vX.Y.Z` (hoặc bấm chạy tay `desktop-release`) → GitHub Release riêng tư có `.exe`, `.dmg`, `SHA256SUMS`. Mỗi lần chạy tốn khoảng 1 giờ phút chạy, phần lớn là macOS (tính gấp 10). Hướng dẫn cài cho người dùng: `desktop/INSTALL.md`.
- Phần lõi đóng gói có tệp `.core-version` (bỏ qua kiểm git của thư viện) và, trên macOS, `env.sh` (PATH tới Node, FFmpeg đi kèm). Thêm gói Python hay npm thì `desktop/core-build/credits-check.py` báo phải ghi vào `CREDITS`.
- Sandbox Bash của agent bật khi có `bwrap` và `socat` (bản Linux của app có sẵn) hoặc trên macOS (`STUDIO_AGENT_SANDBOX=1`).

### License và tự cập nhật (specs/017)
- Máy chủ license `tools/license/` (FastAPI, SQLite; triển khai bằng `deploy/license/`, xem README ở đó):
  - cấp key `CU-XXXX-…` (chỉ lưu mã băm), quản lý máy;
  - ký lease Ed25519 có hạn 7 ngày, app gia hạn mỗi khoảng 15 phút;
  - trang quản lý `/admin`, đăng nhập bằng mật khẩu đặt bằng `cli.py admin-password` trên VPS;
  - chuyển bản phát hành riêng tư cho app có lease còn tốt.
- App:
  - `desktop/license.js` (logic thuần) và `license.html`: hỏi key, khoá khi bị thu hồi hoặc hết hạn;
  - `desktop/updates.js`: kiểm `release.json` có chữ ký và SHA-256; Windows cài im lặng khi thoát, macOS mở `.dmg`.
- Phần lõi: `app start --gate <gate.json>`. `tools/studio/studio/gate.py` kiểm lease: khi cổng đóng, web trả 423 và worker không nhận việc mới.
- Bản build chỉ có license khi có biến repo `LICENSE_SERVER_URL` và khoá công khai trong `desktop/license-public-key.txt`. Khoá riêng chỉ nằm ở secret `LICENSE_SIGNING_KEY` và `.env` của VPS, **không bao giờ** vào repo hay vào chat.
- Test dùng khoá thử ở `desktop/test/vectors/` và máy chủ license giả `desktop/test/fake-license.mjs`.

### Chế độ Client (specs/018)
- Một bộ cài, hai chế độ: **Host** (chạy cả xưởng) hoặc **Client** (`mode: "client"`: chỉ cửa sổ app, không có phần lõi, không cần license).
- Host bật "Share with my team…" trên khay:
  - `desktop/share.js` mở cổng HTTPS (mặc định 47860) trước phần lõi; phần lõi vẫn chỉ nghe ở `127.0.0.1`;
  - chứng chỉ do `sh bin/studio app cert` tạo;
  - "Add a computer" cho mã ghép đôi dùng một lần, có hạn 10 phút.
- **Ghép đôi**: hai bên chứng minh cùng biết mã bằng HMAC gắn với dấu vân tay chứng chỉ, nên mã không đi qua mạng. Client lưu dấu vân tay, ghim nó (`setCertificateVerifyProc`) và gửi `X-CU-Client` trong mọi yêu cầu.
- **Cập nhật của Client** đi qua Host (`/__cu/update`, bằng lease của Host); Client kiểm chữ ký như 017.
- **Test**: `desktop/test/share.test.js`, Host giả `desktop/test/fake-host.mjs`, chứng chỉ thử ở `desktop/test/vectors/share-cert.json`.

## Cầu nối After Effects (specs/032)
- `desktop/aebridge.js` (logic thuần, `@ts-check`): tìm AE ở chỗ cài mặc định, hỏi hàng đợi `/api/v1/ae/bridge/*` của phần lõi bằng khoá tạo mỗi lần khởi động (`app start --bridge <CONFIG_DIR/bridge.json>`, header `X-CU-Bridge`, chỉ 127.0.0.1), chạy `AfterFX -r entry.jsx` (macOS: `osascript … DoScriptFile`); AE tự render trong hàng đợi render và vẫn mở (không `aerender`, chỉ tắt AE khi treo quá hạn); mỗi lúc một lượt dựng AE. `ae.html` + khay "After Effects…": đường dẫn, nút Test. Cổng chia sẻ (018) chặn `/api/v1/ae/bridge/*`.
- Test: `desktop/test/aebridge.test.js` với AE giả `desktop/test/fake-ae.mjs`; smoke `CU_SMOKE_AE=1 FAKE_CORE_AE=1 CU_FAKE_AE=$PWD/test/fake-ae.mjs` (in `ae build ok`). Chạy cầu nối từ WSL với AE thật khi phát triển: `node desktop/test/wsl-bridge.mjs --core http://127.0.0.1:8790 --bridge <tệp khoá> --work /mnt/e/…`.
