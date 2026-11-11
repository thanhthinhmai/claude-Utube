# Quickstart: kiểm chứng gói đăng (011)

## 1. Test tự động (không tốn tiền)

```bash
sh tests/filmcheck/run.sh     # test_publish (luật, chương, phụ đề, gói mẫu cố ý lỗi), test_thumbs (cần trình duyệt)
sh tests/online/run.sh        # việc giả có bước Publish, [publish-bad], [publish-cap], trang việc trong trình duyệt
sh tests/run.sh; sh tests/learn/run.sh; sh tests/ui/run.sh
```

Kết quả cần thấy:
- Gói mẫu đạt: 0 lỗi.
- Mỗi gói mẫu cố ý lỗi trượt đúng một mã lỗi (SC-002).
- `--check-only` chạy < 10 giây (SC-003).
- Phụ đề khớp kịch bản 100%, lệch ≤ 0,3 giây (SC-006).
- Việc giả có `[publish-cap]` vẫn `done`, với `qa.publish.cut` có lý do.

## 2. Gói đăng cho một phim cũ ở local (FR-001a)

```bash
ls films/                                   # chọn một phim đã xong, ví dụ <phim>
# trong khung chat: nhờ Claude "làm gói đăng cho <phim>"; Claude viết films/<phim>/publish/pack.json
sh bin/studio publish <phim>                # mã 0 đạt, 1 trượt (in lỗi), 2 không làm được
cat films/<phim>/publish/PUBLISH.md
```

Kết quả cần thấy:
- Có 3 thumbnail đúng phong cách của phim.
- Mô tả có chương bắt đầu từ `0:00` (khi phim có `narration.json`).
- `CHECKS.md` có phần "Publish".
- Phim làm trước 010 thì `PUBLISH.md` có mục `## Missing`.

## 3. Bài chạy thật online (tốn tiền, làm bằng tay một lần)

```bash
sh tests/online/live.sh --idea "<một ý tưởng 45–60 giây có số liệu>" --tag p011
```

Kết quả cần thấy:
- Việc `done`.
- Trang việc có mục Publish: 3 ảnh, copy được tiêu đề và mô tả, tải được phụ đề và cả gói.
- `qa.publish.pass = true`, đạt ngay vòng đầu hoặc sau 1 vòng sửa (SC-005).
- Token từ lúc `job step Publish` tới `job done` ≤ 5% tổng token của việc (SC-004). Đo từ bảng `call` theo mốc giờ của hai dòng log.
- Bước Publish thêm ≤ 3 phút.
- Tự mở YouTube Studio, dán thử tiêu đề, mô tả và phụ đề vào một video nháp riêng tư. Không cần sửa chữ nào, và chương hiện đúng (SC-005, kiểm bằng tay).

## Kết quả T029 (2026-11-11)

Chạy mục 2 trên phim có sẵn `banh-mi-dem` (20 giây, làm trước 010, không có `narration.json`, `SCRIPT.md` hay `SOURCES.md`). `pack.json` được viết tay theo contracts/files.md.

- `sh bin/studio publish banh-mi-dem`: mã 0, chạy 3,7 giây.
- 3 thumbnail 1280×720 (417–532 KB) dùng đúng phông `Baloo VN` của phim. Chữ cao 0,228 chiều cao ảnh; độ tương phản 5,61, 14,93 và 7,34.
- Chương và phụ đề được ghi "không áp dụng". `PUBLISH.md` có mục `## Missing` ghi 2 lý do: không có `narration.json`, và không kiểm được số vì thiếu kịch bản và nguồn.
- Xem bằng mắt: ảnh đúng phong cách phim, chữ đọc rõ. Ảnh 2 (`position: top`) đè lên đồng hồ "02:00" của chính phim; agent tránh được bằng cách chọn `position` khác. Máy kiểm không bắt lỗi này, vì không có luật về chữ của phim nằm dưới chữ của thumbnail.

## Kết quả T033 (2026-11-11)

Chạy lại `publish banh-mi-dem` sau khi thêm luật `thumb_covers_text`. `texts_checked` là `true` cho cả 3 ảnh. Ảnh 2 (`position: top`) che hộp chữ "02:00" của phim 6,9%, dưới ngưỡng 10%: hai chữ chạm mép nhau chứ không che nhau, khớp với lần xem bằng mắt ở T029. Gói vẫn đạt.
