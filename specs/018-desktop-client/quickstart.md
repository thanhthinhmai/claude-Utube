# Quickstart: kiểm chứng chế độ Client (018)

## 1. Test tự động

```bash
sh tests/ui/run.sh      # desktop/test/share.test.js: ghép đôi, máy giả Host, sai mã, luồng dữ liệu mã hoá, tắt cổng
sh tests/online/run.sh  # app cert
```

## 2. Chạy trên một máy (không cần máy thứ hai)

```bash
cd desktop
node test/fake-host.mjs 47861        # một Host giả: cổng chia sẻ thật + phần lõi giả; in địa chỉ và mã ghép đôi
env -u ELECTRON_RUN_AS_NODE CU_CONFIG_DIR=$(mktemp -d) npx electron .   # chọn "Connect to a studio", nhập địa chỉ và mã
```

## 3. Bằng tay với hai máy thật (SC-001)

1. Máy A (Host, đã cài và chạy được 016): khay → **Share with my team…** → bật → **Add a computer**. Cho phép app trong hộp hỏi của tường lửa.
2. Chủ xưởng tạo tài khoản member ở Settings → Users.
3. Máy B: cài cùng bộ cài → **Connect to a studio** → nhập địa chỉ và mã → đăng nhập member → giao một phim. Bấm giờ từ lúc mở app tới lúc đăng nhập xong (dưới 3 phút).

## Kết quả tự động (2026-11-12)

6 bộ test đạt (`tests/ui/run.sh` có 33 test Node). Smoke trên GitHub đạt trên cả Windows và macOS: Host chia sẻ, Client ghép đôi, mở trang qua HTTPS đã ghim, cập nhật qua Host, trang offline.

## Còn kiểm bằng tay

SC-001: hai máy thật trong cùng LAN (hoặc Tailscale), bấm giờ từ lúc Client mở app tới lúc đăng nhập xong, rồi giao một phim thật từ Client (SC-005 với phần lõi thật).
