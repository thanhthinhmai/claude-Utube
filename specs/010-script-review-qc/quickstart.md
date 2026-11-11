# Quickstart: kiểm tính năng 010

## Tự động (không mạng, không tốn hạn mức)

```sh
sh tests/run.sh            # máy chấm kịch bản và máy QC trên tệp mẫu
sh tests/online/run.sh     # luồng việc online với Claude Code giả và dịch vụ giả
```

Kết quả mong đợi:
- Kịch bản mẫu tốt: `script check` thoát 0. Mỗi kịch bản mẫu lỗi trượt đúng luật của nó (SC-002 dưới 5 giây).
- Phim mẫu tốt: `qc` báo 0 lỗi. Mỗi phim mẫu lỗi (lặng dài, cắt giữa câu, cảnh chốt ngắn, đuôi dài, hình đứng im, ký tự thiếu phông) trượt đúng một mục, kèm mốc giây (SC-003).
- Việc giả có một vòng sửa kịch bản: trang việc hiện điểm máy chấm, điểm biên tập của 2 lượt, `fix_rounds = 1`. Các đoạn không bị ghi lỗi giữ nguyên (SC-004).
- Biên tập giả trả chưa đạt 3 lượt: việc lỗi do xưởng, lượt được trả, chưa có file giọng.

## Bằng tay (tốn hạn mức, một lần trước khi gộp)

1. Local: trong khung chat, nhờ làm một phim 45 giây có lời đọc về một chủ đề có số liệu. Kiểm trong `films/<tên>/`: có `SCRIPT.md`, `SOURCES.md` (đường dẫn thật), `CHECKS.md` có điểm máy chấm ≥ 7, điểm biên tập ≥ 8 và số đo QC đạt.
2. Online: `sh bin/studio online up`, giao cùng loại phim, có chọn duyệt treatment.
   - Lần duyệt gồm bản tóm tắt, kịch bản và điểm (FR-019).
   - Duyệt xong, phim chạy hết; trang việc hiện điểm và số đo.
   - Ghi tổng token của việc và phần token của bước kịch bản (SC-005: ≤ 15%).
3. Online: kiểm `WebSearch` và `web fetch` chạy qua proxy (R4): `SOURCES.md` có đường dẫn mở được, nhật ký proxy chỉ ghi tên miền.
