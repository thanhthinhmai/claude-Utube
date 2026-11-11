# Quickstart: kiểm chứng license và cập nhật (017)

## 1. Test tự động

```bash
sh tests/license/run.sh   # máy chủ license: lease, giới hạn, trang quản lý, chuyển tiếp với GitHub giả
sh tests/ui/run.sh        # gồm desktop/test: kiểm lease, chống lùi đồng hồ, kiểm release.json, kiểm chéo với Python
sh tests/online/run.sh    # tệp cổng: 423, worker không nhận việc mới
sh tests/run.sh; sh tests/learn/run.sh; sh tests/filmcheck/run.sh
```

## 2. Chạy cả hệ thống trên máy này (không tốn tiền)

```bash
python tools/license/cli.py keygen --out /tmp/cu-key        # in khoá công khai
LICENSE_DATA=$(mktemp -d) LICENSE_SIGNING_KEY=$(cat /tmp/cu-key) tools/.venv/bin/python tools/license/server.py --port 8899
# trình duyệt: http://127.0.0.1:8899/admin, đặt mật khẩu bằng cli.py admin-password (cùng LICENSE_DATA), tạo key
cd desktop && env -u ELECTRON_RUN_AS_NODE CU_LICENSE_SERVER=http://127.0.0.1:8899 CU_LICENSE_PUBLIC_KEY=<khoá công khai> npx electron .
```

Nhập key, thấy xưởng. Thu hồi key trên trang quản lý, đợi 1 phút (`CU_LICENSE_RENEW_MS=60000`), thấy màn hình khoá. Mở URL của xưởng bằng trình duyệt, thấy trang "locked".

## 3. Bằng tay sau khi triển khai VPS (SC-001, SC-003)

1. Làm theo `deploy/license/README.md`: thuê VPS, trỏ tên miền, `keygen`, đặt các secret và biến của repo, `docker compose up -d`, đặt mật khẩu quản trị.
2. Gắn tag `desktop-v0.2.0`. Cài bản 0.2.0, nhập key (bấm giờ, SC-001).
3. Gắn tag `desktop-v0.2.1`. Đợi app tự thấy bản mới (hoặc bấm "Check for updates"). Windows: thoát rồi mở lại, phim còn nguyên (SC-003). macOS: kéo `.dmg` mới vào Applications.
