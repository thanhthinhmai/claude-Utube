# Quickstart: kiểm chứng vỏ app desktop (015)

## 1. Test tự động trên máy phát triển

```bash
sh tests/ui/run.sh            # gồm node --test desktop/test (logic của vỏ)
sh tests/online/run.sh        # gồm app check --json và tên việc trong app status --json
```

## 2. GitHub Actions (Windows và macOS)

Đẩy nhánh `015-desktop-shell`, hoặc bấm Run workflow ở trang Actions › desktop. Cả hai máy phải có đủ 3 dòng `smoke: window ok`, `smoke: second instance ok`, `smoke: quit ok`, và bước kiểm tiến trình còn sót phải đạt.

## 3. Bằng tay trên máy Windows của bạn (đường WSL thật)

Cần: một bản Linux WSL2 có studio đã chạy được `sh bin/studio app start` (014).

```powershell
cd <repo trên Windows>\desktop      # hoặc chép thư mục desktop/ sang Windows
npm install
npx electron .
```

- Lần đầu: màn hình thiết lập liệt kê bản Linux WSL2. Chọn bản có studio, kiểm thư mục dữ liệu, bấm Bắt đầu, rồi thấy trang tạo chủ xưởng.
- Đóng cửa sổ: app vẫn ở khay. Mở lại app: chỉ một bản.
- Thoát khi đang có việc: app hỏi, nêu tên việc.
- Sau khi thoát: `wsl -d <bản> -- pgrep -f claude-utube` trả rỗng.

## 4. Bằng tay trên máy Mac của bạn

Cần: studio ở `~/claude-Utube` chạy được `sh bin/studio app start`.

```bash
cd ~/claude-Utube/desktop && npm install && npx electron .
```

Kiểm cùng các mục như mục 3. Icon trên thanh menu phải đổi màu theo nền sáng hay tối.
