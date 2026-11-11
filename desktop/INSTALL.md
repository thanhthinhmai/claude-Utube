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

## License key

Từ bản 0.2.0, lần mở đầu app hỏi **license key** dạng `CU-XXXX-XXXX-XXXX-XXXX` do chủ xưởng gửi.
- Cần có mạng lúc nhập key. Sau đó app vẫn chạy được tới 7 ngày khi mất mạng.
- Mỗi key dùng được trên một số máy nhất định. Đổi máy thì nhờ chủ xưởng gỡ máy cũ.
- Khi key bị tắt hoặc hết hạn, app khoá lại: phim đang dựng vẫn làm xong, dữ liệu giữ nguyên. Nhập key mới để mở lại.
- Xem hoặc đổi key: biểu tượng claude-Utube trên khay → **License…**.

## Cập nhật

App tự tìm bản mới (lúc mở, rồi mỗi 4 giờ; hoặc bấm **Check for updates** trên khay). Bản mới chỉ tải được khi key còn hợp lệ.
- **Windows**: app tải xong thì báo; bản mới được cài khi bạn thoát app (hoặc bấm **Restart to update** trên khay). Lần mở sau, app cài lại phần lõi; phim, kênh và tài khoản giữ nguyên.
- **macOS**: app mở tệp `.dmg` mới; kéo **claude-Utube** vào **Applications** để thay bản cũ.

Bản 0.1.0 không tự cập nhật: cài bản 0.2.0 bằng tay một lần (chạy bộ cài mới đè lên bản cũ).

## Gỡ

- Windows: Settings → Apps → claude-Utube → Uninstall. Trình gỡ hỏi có xoá luôn bản Linux `ClaudeUtube` cùng dữ liệu không (mặc định là giữ).
- macOS: kéo app vào Thùng rác. Dữ liệu nằm ở `~/Library/Application Support/ClaudeUtube` và phần lõi ở `~/Library/Application Support/ClaudeUtube-core`; xoá hai thư mục này nếu muốn xoá hết.
