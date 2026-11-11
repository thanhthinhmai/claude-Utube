# Research: License key và tự cập nhật (017)

## R1. Học từ neb-creative-tool

neb đã chạy thật cách làm này: key ngẫu nhiên, lease ký bằng Ed25519, một máy chủ license riêng trên VPS, và máy chủ đó chuyển tiếp bản phát hành riêng tư. 017 giữ cùng hướng, với các thay đổi sau:

| Điểm | neb | 017 |
|---|---|---|
| Máy chủ | Node, Postgres, compose 4 dịch vụ | Python FastAPI, SQLite, compose 2 dịch vụ (license, caddy); máy chủ tự sao lưu |
| Quản lý | Qua web app chính bằng mã quản trị | Trang riêng trên máy chủ license, đăng nhập bằng mật khẩu (câu Q2) |
| Thời gian dùng khi mất mạng | 3 ngày | 7 ngày (câu Q1) |
| Kiểm bản cập nhật | Chỉ dựa vào HTTPS, và trên macOS chỉ so kích thước | `release.json` ký Ed25519 kèm SHA-256 từng tệp, kiểm trên cả hai hệ điều hành |
| Cài trên Windows | electron-updater qua máy chủ loopback | Chạy bộ cài NSIS im lặng khi thoát (R6) |
| Gia hạn | Đúng 15 phút | 15 phút ± 2 phút ngẫu nhiên, để các máy không gọi cùng lúc |

## R2. Key, lease, chữ ký

- **Key**: `CU-XXXX-XXXX-XXXX-XXXX`, 16 ký tự lấy từ `ABCDEFGHJKMNPQRSTUVWXYZ23456789` (khoảng 80 bit), dùng `secrets.choice`.
  - Chuẩn hoá: viết hoa, bỏ ký tự không phải chữ hay số, bỏ chữ `CU` ở đầu, phải còn đúng 16 ký tự.
  - Máy chủ lưu `sha256(key đã chuẩn hoá)` và 4 ký tự cuối.
- **Lease**: `base64url(JSON) "." base64url(chữ ký Ed25519 trên phần đầu)`.
  - JSON là `{"v":1,"lid","did","label","iat","exp","keyExp"}`, thời gian tính bằng **giây**.
  - `exp = min(now + 7 ngày, keyExp)`.
- **Khoá**:
  - `python tools/license/cli.py keygen` in khoá công khai (base64 của 32 byte thô) và ghi khoá riêng (base64 của 32 byte thô) vào một tệp quyền 600.
  - Chủ xưởng đặt khoá riêng vào `deploy/license/.env` trên VPS và vào secret `LICENSE_SIGNING_KEY` của repo.
  - Khoá công khai được commit vào `desktop/license-public-key.txt`.
- **Kiểm chéo**: `desktop/test/vectors/` có cặp khoá thử, một lease và một `release.json` do Python ký. Node phải kiểm đạt chúng, và kiểm hỏng khi sửa một byte.

## R3. Mã máy

- **Windows**: `reg query HKLM\SOFTWARE\Microsoft\Cryptography /v MachineGuid`.
- **macOS**: `ioreg -rd1 -c IOPlatformExpertDevice`, lấy `IOPlatformUUID`.
- **Linux** (khi phát triển): `/etc/machine-id`.
- **Không đọc được**: dùng một `installId` ngẫu nhiên lưu trong `config.json`.
- **Gửi lên máy chủ**: `sha256("claude-utube-device:" + id)`, 64 ký tự hex.
- Mã máy luôn lấy ở phía Electron, không lấy trong WSL, nên cài lại phần lõi không đổi mã máy.

## R4. Tệp cổng (gate) của phần lõi

- App ghi `gate.json` vào thư mục cấu hình của app, gồm `{deviceId, lease, clock, refused}`.
- App chạy `app start --gate <đường dẫn>`:
  - Windows truyền đường dẫn dạng `/mnt/c/…` (hàm `core.wslPath` của 016);
  - `host.start` lưu đường dẫn vào `host.json` và đặt `STUDIO_LICENSE_GATE` cho web và worker.
- `gate.py` đọc lại tệp khi `mtime` đổi. Tệp được coi là tốt khi:
  - chữ ký đúng (khoá công khai ở `desktop/license-public-key.txt` trong studio);
  - `did` khớp `deviceId`;
  - `exp` và `keyExp` chưa qua;
  - đồng hồ không lùi: `now ≥ max(iat, clock) − 600 giây`;
  - `refused` không có giá trị.
- **Web**: mọi đường dẫn trừ `/api/v1/health` trả `423`. Trình duyệt nhận một trang HTML ngắn "claude-Utube is locked"; lời gọi API nhận `{"code":"license_locked"}`.
- **Worker**: trước khi lấy việc mới trong hàng đợi thì hỏi `gate.ok()`. Việc đang chạy không bị đụng.
- **Không có `--gate`**: không kiểm gì (bản phát triển, 014 chạy bằng lệnh).
- Giới hạn: người tự chạy `app start` không kèm `--gate` sẽ vượt được khoá. Spec đã nhận giới hạn này ("chỉ chặn người dùng bình thường").

## R5. Phát hành và chuyển tiếp

- **Workflow 016, job `release`**, thêm các bước:
  - tạo `release.json`: `{"version","tag","files":[{"name","size","sha256"}]}`, gồm `.exe`, `.dmg` và hai `core-manifest`;
  - ký thành `release.json.sig` bằng `python tools/license/cli.py sign-release` với secret `LICENSE_SIGNING_KEY`;
  - thiếu secret mà có biến `LICENSE_SERVER_URL` thì job lỗi.
- **Cấu hình license lúc build**: job `installers` ghi `desktop/build-config.json` = `{"licenseServer": "<vars.LICENSE_SERVER_URL>"}`. Không có biến thì không ghi tệp, và bản build không có license.
- **Máy chủ license** dùng `GITHUB_TOKEN` (fine-grained, chỉ quyền Contents read) và `GITHUB_REPO`. Hai lời gọi:
  - `GET /api/license/releases` lấy bản phát hành mới nhất có tag `desktop-v*`, không phải bản nháp, rồi trả `{tag, version, assets:[{name,size}]}`. Lưu đệm 2 phút.
  - `GET /api/license/releases/<tên>` chuyển tiếp tệp, đọc dạng luồng.
  - Tên phải khớp `^(release\.json(\.sig)?|claude-Utube-Setup-[\w.-]+\.exe|claude-Utube-[\w.-]+-arm64\.dmg)$`.
  - Cả hai cần header `X-CU-Lease`. Lease phải hợp lệ, và key cùng máy phải còn tốt **lúc này** trong cơ sở dữ liệu.

## R6. Cài bản mới

- **App**:
  - tải `release.json` và chữ ký, rồi kiểm chữ ký;
  - chỉ làm tiếp nếu phiên bản lớn hơn bản đang chạy (so semver);
  - tải bộ cài cho hệ điều hành của mình vào `updates/<tên>.part`, kiểm kích thước và SHA-256, rồi đổi tên;
  - xoá các bộ cài cũ.
- **Windows**:
  - khay hiện "Restart to update", và một thông báo;
  - khi thoát (sau khi đã dừng phần lõi như 015), chạy `spawn(<bộ cài>, ["/S", "--updated", "--force-run"], {detached: true})` rồi thoát. NSIS của electron-builder cài đè cho riêng người dùng, rồi mở lại app (`--force-run`);
  - lần mở sau, phiên bản phần lõi khác nên màn hình thiết lập hiện bước cài lại phần lõi, và dữ liệu được giữ (016 R7). App kiểm `cfg.coreVersion` với `core-manifest.json` ngay lúc khởi động (sửa nhỏ ở `main.js`).
- **macOS**: hộp hỏi "A new version is ready", bấm Open thì `shell.openPath(<dmg>)`.
- **Chưa thử**: `/S --force-run` khi app vừa thoát. Kiểm trên GitHub Windows ở T020, bằng app đóng gói và một bản phát hành giả do máy chủ license giả phục vụ.

## R7. Trang quản lý

- **Mật khẩu**: đặt bằng `docker compose exec license python cli.py admin-password`, chủ xưởng gõ trong terminal của VPS. Lưu dạng băm argon2.
- **Phiên đăng nhập**: cookie `cu_admin` (HttpOnly, Secure, SameSite=Strict, 12 giờ), lưu mã băm phiên trong bảng `sessions`. Các lời gọi ghi cần thêm header `X-CU-Admin: 1` để chống CSRF, như 007.
- **Giới hạn**: nhập sai mật khẩu 10 lần mỗi 10 phút cho mỗi địa chỉ thì bị chặn, như sai key (FR-004). Bộ đếm giữ trong bộ nhớ, đủ cho một tiến trình.
- **Trang**: tạo key (key hiện một lần, có nút chép), bảng key (trạng thái, "N/M máy", lần thấy cuối, ngày hết hạn), sửa, thu hồi hoặc bật lại, xoá, danh sách máy (gỡ, cho phép lại).
- **Địa chỉ người gọi**: lấy từ `X-Real-IP` do Caddy đặt lại bằng `{remote_host}`, nên người gọi không giả được.

## R8. Thời gian

- **Hằng số**:
  - `LEASE_DAYS = 7`;
  - `RENEW_S = 900` (± 120 ngẫu nhiên);
  - `UPDATE_EVERY_S = 14400`, lần kiểm đầu sau 30 giây;
  - `CLOCK_SKEW_S = 600`;
  - khi khoá, việc đang chạy được tối đa 6 giờ (đã có trong worker).
- **Khi test**: `CU_LICENSE_RENEW_MS` và `CU_UPDATE_EVERY_MS`. Hai biến này chỉ có tác dụng ở bản chưa đóng gói, hoặc khi đặt `CU_SMOKE`.
