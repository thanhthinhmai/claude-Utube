# Research: Thư viện phong cách trên Film Studio

## §1 Dung lượng poster (đo thật)

Bản tải thử trong thư mục tạm: kho `lemo-opuscar` ở commit ghim `bebbbe1`, tải từng phần (`blob:none`), danh sách sparse chỉ có `/styles/*/poster.jpg`.

| Đo | Kết quả |
|---|---|
| Số poster | 66 (đủ mọi phong cách, trừ `_template`) |
| Tổng dung lượng | 22 MB |
| Lớn nhất | 1,4 MB (`risograph`) |
| Kích thước ảnh | 1920×1080 JPEG |
| Thời gian fetch + checkout | ~1,5 s (mạng của phiên này) |

- **Decision**: Tải poster gốc, không tải gì khác của phim mẫu.
- **Rationale**: 22 MB chấp nhận được (người dùng chọn "vài chục MB"); không cần bước tạo ảnh.
- **Alternatives considered**: Tải `styleboard/` (ảnh tổng hợp): không có ảnh riêng cho từng phong cách; tải phim mẫu: hàng trăm MB, người dùng đã chọn chỉ link.

## §2 Cập nhật máy đã `setup` trước đây

Thử trên bản tải thử: đổi `.git/info/sparse-checkout` rồi chạy `git sparse-checkout reapply`. Git tự lấy các file còn thiếu (kho tải từng phần tự hỏi máy chủ), `git status` sạch.

- **Decision**: Lần cài đầu vẫn tải với danh sách cũ (không poster), rồi dùng chung bước poster. Trong `setup`, nếu thư viện vừa cài, ở trạng thái `ok` hoặc `outdated` mà danh sách sparse khác `SPARSE` **hoặc** số poster ít hơn số phong cách, thì ghi danh sách mới và chạy `reapply`. Lỗi (mất mạng) → báo "✗ poster chưa tải được: chạy lại sh bin/studio setup khi có mạng", mã thoát vẫn theo phần thư viện (phần làm phim không hỏng). Lần sau điều kiện "thiếu poster" vẫn đúng nên `setup` thử lại.
- **Rationale**: Không tải lại thư viện; dùng đúng cơ chế git đang dùng.
- **Alternatives considered**: Xoá và tải lại thư viện: chậm, mất `node_modules` đã cài; tải poster riêng qua HTTP: thêm một kênh tải và không khớp phiên bản ghim một cách tự nhiên.

## §3 Ảnh trên trang lưới

66 ảnh 1920×1080 (22 MB) trên một trang.

- **Decision**: Trả ảnh gốc, `<img loading="lazy" decoding="async">`, khung 16:9; máy chủ gửi `Cache-Control: max-age=86400` và `ETag` (poster đổi chỉ khi đổi phiên bản thư viện).
- **Rationale**: Chạy trên `127.0.0.1` nên băng thông không đáng kể; tải lười chỉ giải mã ảnh trong khung nhìn; không cần Pillow ở tầng `ui`.
- **Alternatives considered**: Tạo ảnh thu nhỏ bằng Pillow vào `.studio/`: thêm phụ thuộc và bước xử lý; để dành nếu SC-003 không đạt khi đo.

## §4 Nguồn dữ liệu thẻ

`styles/<slug>/style.json` có `slug, num, en, cn, category_en, category_cn, film, line, line_cn, uses[], frame_sec, dur`. Đếm thật: 66 phong cách, 11 nhóm (Evidence Films 8, Edit & Documentary 8, Hand-drawn & Painting 8, Information & Keynote 8, Materials & 3D 7, Graphic & Type 7, Print & Printmaking 6, Cartoon & Anime 4, Games 4, East Asian Traditions 4, Cinema & Eras 2).

- **Decision**: Đọc `style.json` mỗi lần gọi (66 file nhỏ), trả các trường trên + `has_poster`; bỏ thư mục `_template` và mọi thư mục có tên sai mẫu hoặc `style.json` hỏng (đếm vào `skipped`).
- **Rationale**: Đơn giản, luôn khớp đĩa sau khi `setup` đổi phiên bản; đọc 66 file < 50 ms.
- **Alternatives considered**: Đọc `styles/README.md` (bảng sinh tự động): thiếu nhiều trường; bộ nhớ đệm: không cần ở quy mô này.

## §5 Link GitHub

- **Decision**: `https://github.com/<owner>/<repo>/tree/<commit>/styles/<slug>`, với `<owner>/<repo>` lấy từ `LIB_REPO` trong `library.lock` (chỉ khi là `github.com`) và `<commit>` từ `lib/lemo-opuscar/.git/HEAD` (thư viện luôn ở trạng thái detached nên file chứa SHA). Kho không phải GitHub → không có link.
- **Rationale**: Đúng phiên bản đang ghim (FR-009); không cần chạy `git`.

## §6 Câu lệnh mẫu

- **Decision**: `Make a 40-second film in the <en> style about …` cho cả phong cách thư viện và phong cách riêng. Chép bằng `navigator.clipboard.writeText`; lỗi (trang không ở ngữ cảnh an toàn, trình duyệt chặn) → hiện ô chữ đã bôi đen sẵn.
- **Rationale**: `http://localhost` là ngữ cảnh an toàn nên chép được; đường dự phòng cho FR-010.

## §7 Lọc và tìm

- **Decision**: Tải danh sách một lần, lọc trên trình duyệt; trạng thái trong địa chỉ `#/library?group=<nhóm>&q=<chuỗi>`. Tìm không phân biệt hoa thường và dấu trên `en`, `cn`, `slug`, `uses`.
- **Rationale**: Đạt < 0,2 s (SC-003) và giữ được khi tải lại (FR-008).
