# Quickstart: kiểm chứng học phong cách

## Test tự động (không cần mạng, không cần mô hình chép lời)

```sh
sh bin/studio deps learn
sh tests/learn/run.sh
```

Kỳ vọng: mọi test `ok`, mã thoát 0. Bao gồm:
- Video tổng hợp 30 fps có 5 cắt cứng, 1 chớp sáng, 1 hoà tan: phát hiện 5/5 cắt, 0 báo nhầm (SC-002).
- Pan 2 px/khung và 0,3 px/khung: đo được đúng hướng và độ lớn (±10%); 0,3 px vẫn tính là đứng yên theo ngưỡng 720p.
- Khung màu đặc có độ sáng biết trước: sai số ≤ 0,02 (SC-002).
- Tốc độ đọc từ `words.json` giả: sai số ≤ 10% (SC-002).
- Số khung đo = số khung mong đợi (SC-001); video 5 phút chỉ đo 180 s đúng các đoạn.
- Đo bị ngắt rồi chạy lại: video đã xong không đo lại (FR-011).
- `check-names` bắt tên kênh, tên có dấu và chuỗi 6 từ; không bắt cụm ngắn (SC-003).
- `compare` với hai ảnh biết trước cho đúng `pass` và `fail` (SC-004).
- `save` từ chối slug trùng hoặc gói có media; khi đạt thì thêm dòng vào `my-styles/README.md` (SC-008); `clean` chỉ xoá trong bộ (SC-006).

## Hiệu năng (SC-005)

```sh
sh bin/studio learn measure perf     # bộ tổng hợp 18 phút do tests/learn/make_fixtures.py --perf tạo
```

Kỳ vọng: dưới 60 phút; in khung/giây.

## Trên máy người dùng (cần mạng và quyền truy cập nền tảng video)

1. `sh bin/studio deps learn --extra`
2. Trong Claude Code: "Học phong cách của kênh <link>, 12 video gần nhất".
3. Kiểm: hai lần dừng duyệt (SC-007); `STYLE.md` có 11 mục và `(evidence: …)` ở mọi luật; `git status` không có media (SC-006); sau khi lưu, "làm phim 30 giây theo phong cách <tên>" chọn được phong cách đó ngay (SC-008).
