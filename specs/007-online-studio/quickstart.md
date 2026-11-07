# Quickstart: kiểm tra 007

## 1. Test tự động (không cần mạng, không tốn tiền)

```sh
sh tests/run.sh
sh tests/learn/run.sh
sh tests/ui/run.sh
sh tests/online/run.sh
```

Ba lệnh đầu là bộ test của giai đoạn 1; tất cả phải vẫn đạt ở chế độ `local`. Lệnh cuối dùng tác tử giả và API Claude giả. Khi không có Docker thì các test container được bỏ qua kèm lý do.

| Kịch bản | Kiểm | Theo |
|---|---|---|
| Đăng ký, xác minh, đăng nhập, đặt lại mật khẩu | thư ghi ra tệp; liên kết dùng một lần, có hạn | US1/AC1–2, FR-001–002 |
| Hai khách | mọi điểm truy cập trả `404` với tài nguyên của khách kia | SC-003 |
| 10 lần giao việc cùng lúc, hạn mức 2 | đúng 2 việc được nhận | SC-008 |
| 20 việc, N = 2 | không lúc nào có hơn 2 việc chạy, không khách nào có 2 việc chạy | SC-009 |
| API giả tính tiền vượt trần ngày | việc mới nhận `503 daily_cap`; việc đang chạy vẫn xong | SC-005, US3/AC2 |
| Việc vượt trần chi phí riêng | việc lỗi do xưởng, khách được trả lượt | FR-006, R3 |
| Tác tử giả tạo yêu cầu duyệt | container dừng (mã 10); quyết định trên web làm việc chạy tiếp bằng phiên cũ | FR-020–021, R5 |
| Việc học kết thúc | không còn tệp video hay âm thanh gốc; không có đường API nào trả chúng | SC-004 |
| Container | không đọc được thư mục việc khác; không thấy khoá API thật; không ra mạng ngoài trừ bộ chuyển tiếp | FR-027, R2–R3 |

## 2. Chạy thử trên máy (chế độ online)

```sh
sh bin/studio deps online
sh bin/studio online up
sh bin/studio admin create you@example.com
```

`online up` dựng hai ảnh Docker, chạy Compose với Caddy ở `localhost` (chứng chỉ nội bộ), thư ghi ra `/data/outbox/`. Mở `https://localhost`, đăng ký một tài khoản khách, mở thư xác minh trong `/data/outbox/`, rồi giao một phim 20 giây theo một phong cách thư viện. Cần `ANTHROPIC_API_KEY` thật trong `deploy/.env`; lần chạy này **tốn tiền**, và chi phí hiện trên trang quản trị.

Kết quả mong đợi: việc đi qua `queued` → `running` → `done`; phim xem và tải được; hạn mức còn lại giảm 1; trang quản trị hiện chi phí của việc.

## 3. Bài chạy thật (bằng tay, tốn tiền)

```sh
sh tests/online/live.sh
```

Bài chạy làm 3 phim 30 giây và một lần học từ 3 video tải lên. Nó in thời gian và chi phí của mỗi việc (dùng cho SC-006), và chạy lại kiểm tra âm thanh và kiểm tra đọc chữ trên từng phim (SC-002).

## 4. Triển khai lên máy chủ

Xem `deploy/README.md`: tên miền trỏ về máy chủ, điền `deploy/.env` (khoá API, SMTP, tên miền), chạy `docker compose up -d`, tạo tài khoản quản trị, sao lưu `/data`. Nên hỏi luật sư trước khi mở đăng ký cho công chúng (hiến pháp 2.1.0).
