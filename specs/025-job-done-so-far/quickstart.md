# Quickstart: kiểm chứng 025

## 1. Test tự động

```sh
sh tests/ui/run.sh        # test_done_so_far (API, danh sách tệp, ca từ chối) + browser_done.cjs
sh tests/online/run.sh    # test_done_access (quyền online)
sh tests/run.sh && sh tests/filmcheck/run.sh && sh tests/learn/run.sh
```

## 2. Phim thật (SC-001, SC-002, SC-005)

1. `sh bin/studio ui` rồi mở trang việc của `pause-ten-seconds` (mã trong `films/pause-ten-seconds/.job`).
2. Khu "Done so far": Script 10/10 và 8,0/10, 2 vòng sửa; Voice 339 dòng, lọc ra 12 dòng "Read as"; Shots 175 cảnh, 5 bảng ảnh; Mix 10:06 nghe được tới cuối; Render 61/61, GPU.
3. Bấm nghe một dòng giọng: tiếng phát trong dưới 1 giây.

## 3. Tự cập nhật (SC-003)

Mở trang việc của một việc thử, chạy `sh bin/studio job step <mã> Voice` rồi tạo `voices/` và kết quả tầng voice: nút "Voice" đổi trạng thái trong ≤ 10 s, mục đang mở không mất.
