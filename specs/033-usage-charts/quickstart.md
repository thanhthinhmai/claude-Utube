# Quickstart: kiểm 033

## Test tự động

```sh
sh tests/online/run.sh      # test_admin.py: API usage (ô tổng, đủ ngày, theo nguồn, 422) + trình duyệt
sh tests/ui/run.sh          # không được hỏng gì ở trang khác
```

Mong đợi: tất cả đạt (bước trình duyệt bị bỏ qua nếu thiếu node hoặc playwright-core, và phải ghi rõ là đã bỏ qua).

## Xem thử thật

1. Chạy xưởng có dữ liệu lượt gọi: `sh bin/studio app start --data <thư mục thử> --web-port 8801 --proxy-port 8802` (không dùng cổng 8790 khi app đã cài đang chạy).
2. Đăng nhập chủ xưởng → Settings → Usage.
3. Kiểm:
   - 3 ô Hôm nay / 7 ngày / 30 ngày có số.
   - 2 biểu đồ có 30 cột; rê chuột vào một cột thấy ngày, số theo từng nguồn và tổng.
   - Bấm "7 ngày": còn 7 cột, các bảng đổi theo, địa chỉ có `range=7`; tải lại vẫn giữ.
   - "Xem dạng bảng" cho cùng số.
   - Bề ngang 390 px và chế độ tối vẫn đọc được, không cuộn ngang cả trang.
