# Cài claude-Utube

claude-Utube chạy trên máy của bạn, bằng tài khoản Claude của chính bạn. Chủ xưởng gửi cho bạn một tệp cài; bạn không cần gõ lệnh nào.

## Windows 10 (22H2) hoặc 11, 64-bit

1. Chạy `claude-Utube-Setup-<bản>.exe`. Windows báo "Windows protected your PC" vì bộ cài chưa ký số: bấm **More info → Run anyway**.
2. Mở claude-Utube từ Start menu. Màn hình **Set up claude-Utube** hiện ra.
3. Nếu thấy dòng "WSL is not turned on": bấm **Turn on WSL**, đồng ý quyền quản trị, rồi khởi động lại máy và mở lại app. Nếu thấy "Virtualization is off": bật ảo hoá (Intel VT-x hoặc AMD-V) trong BIOS.
4. Chọn **Install the studio** rồi bấm **Install**. App cài bản Linux riêng của nó (`ClaudeUtube`, không đụng tới bản Linux khác của bạn) và tải mô hình giọng đọc (khoảng 0,5 GB). Mất khoảng 10–20 phút. Mất mạng giữa chừng thì bấm **Try again**.
5. Tạo tài khoản chủ xưởng, rồi vào **AI accounts** đăng nhập tài khoản Claude của bạn.

Cần khoảng **10 GB** trống trên ổ C.

## macOS 14 trở lên, chip Apple (M1 trở về sau)

1. Mở `claude-Utube-<bản>-arm64.dmg`, kéo **claude-Utube** vào **Applications**.
2. Mở app. macOS báo không mở được vì chưa ký: vào **System Settings → Privacy & Security**, bấm **Open Anyway**, rồi mở lại.
3. Chọn **Install the studio** rồi bấm **Install** (khoảng 5–10 phút).
4. Tạo tài khoản chủ xưởng, rồi đăng nhập Claude ở **AI accounts**.

Cần khoảng **8 GB** trống.

## Cài bản mới

Chạy bộ cài của bản mới đè lên bản cũ. Lần mở đầu tiên, app hỏi cài lại phần lõi: phim, kênh và tài khoản được giữ nguyên.

## Gỡ

- Windows: Settings → Apps → claude-Utube → Uninstall. Trình gỡ hỏi có xoá luôn bản Linux `ClaudeUtube` cùng dữ liệu không (mặc định là giữ).
- macOS: kéo app vào Thùng rác. Dữ liệu nằm ở `~/Library/Application Support/ClaudeUtube` và phần lõi ở `~/Library/Application Support/ClaudeUtube-core`; xoá hai thư mục này nếu muốn xoá hết.
