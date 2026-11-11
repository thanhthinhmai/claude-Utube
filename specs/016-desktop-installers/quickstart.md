# Quickstart: kiểm chứng bộ cài (016)

## 1. Test tự động trên máy phát triển

```bash
sh tests/ui/run.sh        # gồm test logic của bước cài (desktop/test)
sh tests/online/run.sh    # gồm app models (Whisper giả) và cấu hình sandbox
sh tests/run.sh; sh tests/learn/run.sh; sh tests/filmcheck/run.sh
```

## 2. GitHub Actions (tốn phút chạy)

Trang Actions › desktop-release › Run workflow (version `0.1.0-test`), hoặc gắn tag `desktop-v0.1.0`. Cần thấy:
- `core-linux` và `core-mac`: dung lượng ≤ 1,9 GB; smoke-core đạt; credits-check đạt;
- `installers`: có `.exe` và `.dmg`; smoke đạt;
- `release`: một Release riêng tư có đủ tệp và `SHA256SUMS`.

## 3. Bằng tay trên máy Windows sạch (SC-001, SC-003)

1. Tải `claude-Utube-Setup-X.Y.Z.exe` từ Release (hoặc lấy tệp chủ xưởng gửi), chạy nó (More info → Run anyway).
2. Mở app → thiết lập: WSL2 (bật nếu cần) → cài phần lõi → tải mô hình → Start → tạo chủ xưởng → đăng nhập Claude → làm một phim 45 giây có giọng đọc.
3. Bấm giờ từ lúc chạy tệp cài tới trang tạo chủ xưởng (< 20 phút).

## 4. Bằng tay trên máy Mac (SC-002, SC-003)

1. Mở `.dmg`, kéo app vào Applications, mở app (System Settings → Privacy & Security → Open Anyway).
2. Thiết lập → Start → tạo chủ xưởng → đăng nhập Claude → làm một phim 45 giây.
3. Bấm giờ (< 10 phút).
