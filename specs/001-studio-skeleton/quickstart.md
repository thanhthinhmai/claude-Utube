# Quickstart: kiểm chứng khung xưởng phim

## Test tự động (không cần mạng)

```sh
sh tests/run.sh
```

Kỳ vọng: mọi dòng `ok`, dòng cuối `PASS n/n`, mã thoát 0. Kịch bản phủ: tải mới, chạy lại không tải, nâng phiên bản, thư viện bị sửa, thư mục lạ, công cụ thiếu, công cụ cũ, ffmpeg không đọc được phiên bản, Python cũ nhưng có uv, `status --json`, chạy từ thư mục con, đường dẫn có dấu cách, gitignore phim và video (SC-002…006).

## Kiểm chứng thật với GitHub (cần mạng)

1. Bản sao mới: `git clone https://github.com/thanhthinhmai/claude-utube && cd claude-utube`
2. `time sh bin/studio setup` → thư viện ở `lib/lemo-opuscar`, đúng `LIB_COMMIT`; dưới 5 phút (SC-001).
3. `time sh bin/studio setup` lần nữa → "đã đúng phiên bản", dưới 10 giây (SC-002).
4. `time sh bin/studio status` → dưới 5 giây, `library_styles` = 66 (SC-003).
5. `git -C lib/lemo-opuscar status --porcelain --untracked-files=no` → rỗng (SC-006).
6. `ls lib/lemo-opuscar/styles/watercolor` → **không** có `demo/` (sparse).

## Điều hướng của Claude (SC-007)

Đọc `CLAUDE.md` với 3 yêu cầu mẫu:
- "Làm phim 40 giây phong cách màu nước về quán cà phê" → luồng làm phim, thư mục `films/<tên>/`, không tạo spec.
- "Học phong cách của kênh X" → báo chưa có (tính năng 002).
- "Viết thêm công cụ Y" → spec-kit.
