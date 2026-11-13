# Quickstart: kiểm chứng 021

## Test tự động
```sh
sh tests/filmcheck/run.sh   # focus.py trên ảnh vẽ sẵn (nét / mờ / có dải đen và phụ đề); labeler với claude giả;
                            # shotcheck: blurred, so phân bố, chuỗi cùng cỡ, nhãn dùng lại theo dấu vân tay
sh tests/learn/run.sh       # learn shots trên video thử tạo bằng ffmpeg (cắt biết trước), gom bối cảnh, summary, save --update giữ nhật ký sửa
sh tests/run.sh && sh tests/render/run.sh && sh tests/ui/run.sh && sh tests/online/run.sh   # không có gì hỏng
git -C lib/lemo-opuscar status --short   # SC-007: trống
```

## Chạy thật

| # | Việc | Kết quả mong đợi | SC |
|---|---|---|---|
| 1 | `learn fetch dusk-hypothetical-2 --channel <kênh tham chiếu> --count 10`, `measure`, `shots`, `label` | mỗi cảnh có nhãn; số cắt mỗi phút 16–26 | US1 |
| 2 | `learn label dusk-hypothetical-2 --pass 2 --sample 40` | `agreement.json`: cùng cỡ ≥ 0,80, lệch ≤ 1 bậc ≥ 0,95, cùng góc ≥ 0,80 | SC-001 |
| 3 | `focus.py` trên 192 khung của `pet-swap` và trên `styleframe.jpg` | ≥ 120 khung không ô nào nét; khung mẫu `focused_share` ≥ 0,5 | SC-002 |
| 4 | Thời gian học lại | ≤ 1,5 lần lần học trước (ghi cả hai con số) | SC-003 |
| 5 | `learn save … --update`, xem `EVIDENCE.md`, `STYLE.md` §2, §6, `shots.json` | đủ số của FR-005 kèm bằng chứng; mọi dòng nhật ký sửa cũ còn | SC-004 |
| 6 | `qc shots` trên phim thử có nhãn biết trước | đủ mọi khung mờ và lệch đã cài, ≤ 1 báo nhầm trên 30 | SC-005 |
| 7 | `qc shots pet-swap` | báo khung mờ, tỉ lệ toàn rất rộng, ngang tầm mắt, chuỗi cùng cỡ, kèm mã cảnh | SC-006 |
| 8 | Phim mẫu: `sh my-styles/dusk-hypothetical/demo/build.sh`, rồi các tầng 1–4 | phim 15–30 s; số khung đúng; đạt các tầng; phân bố nằm trong khoảng của phong cách | SC-008 |
| 9 | `learn clean dusk-hypothetical-2` | video và âm thanh đã xoá; bảng ảnh và nhãn còn | SC-007 |

Phải mở bằng mắt ít nhất một bảng ảnh cảnh có nhãn, và xem phim mẫu (hiến pháp IV).

## Kết quả (2026-11-13)

| SC | Kết quả | Số đo |
|---|---|---|
| SC-001 | **Không đạt** (độ nhất quán) | 40 cảnh, hai lượt độc lập: cùng cỡ cảnh **0,70** (cần 0,80); lệch ≤ 1 bậc **1,00** (cần 0,95, đạt); cùng góc máy **0,675** (cần 0,80), 0,765 nếu bỏ thẻ chữ. (So với bộ nhãn trước khi thêm tên nơi: 0,78 / 1,00 / 0,78.) Lệch nhiều nhất giữa cận và trung, toàn và toàn rất rộng: các cặp bậc kề nhau |
| SC-002 | **Đạt** | `FOCUS_T = 200`: `pet-swap` 146/192 khung không ô nào nét (cần ≥ 120); khung mẫu `styleframe.jpg` 0,917 phần khung nét (cần ≥ 0,5) |
| SC-003 | **Đạt** (so được một phần) | Học lại: tải 71 s, đo 814 s, tách cảnh 160 s, gán nhãn 428 s (gán lại có tên nơi 475 s), lượt thứ hai 31 s. Lần học trước chỉ còn thời gian bước đo (khoảng 800 s, theo giờ ghi của `frames.csv`): bước đo bằng nhau; các bước mới thêm khoảng 11 phút |
| SC-004 | **Đạt** | `EVIDENCE.md`: 15 hàng cách quay mới trong "Key numbers", nhật ký sửa thêm #8–#11, giữ nguyên #1–#7; `STYLE.md` mục 1, 2, 6, 10 ghi bằng số; `shots.json` có đủ các khoảng |
| SC-005 | **Đạt** | `grammar-30`: đủ 3 `blurred`, cảnh báo cỡ cảnh, góc máy và chuỗi 6 cảnh cùng cỡ đúng mã cảnh; không có báo nhầm (`tests/filmcheck/test_shots.py`) |
| SC-006 | **Đạt** | `qc shots pet-swap`: 145 khung mờ (chặn); cận 43% (kênh 5–30%), toàn rất rộng 2% (kênh 5–22%), độ nét trung vị 0 (kênh 0,5–0,83) là cảnh báo kèm mã cảnh; ngang tầm mắt 74% và chuỗi cùng cỡ 4 nằm trong khoảng của kênh. Gán nhãn 192 cảnh: 1 lượt, 4 bảng ảnh; lần chạy sau dùng lại nhãn |
| SC-007 | **Đạt** | `lib/lemo-opuscar` sạch; `learn clean` xoá 877 MB video và âm thanh, còn 15 MB số đo, nhãn và bảng ảnh có nhãn |
| SC-008 | **Chưa làm** | Phim mẫu (T028–T031) để cho phiên sau |

**Số đo cách quay của kênh** (10 video mới nhất, 772 cảnh có nhãn): trung 34%, toàn 27%, cận 20%, toàn rất rộng 14%, đặc tả 5%; ngang tầm mắt 66%, từ trên chéo 19%, qua vai 7%, thấp 5%, thẳng từ trên 1%; đổi cỡ ở 69% số lần cắt; chủ thể nét ở 100% cảnh, trung vị 0,67 phần khung nét; 16 nơi mỗi video.

**Đổi so với plan khi làm**:
- tách cảnh bằng điểm cảnh của ffmpeg (`scdet` bỏ sót các lần cắt tối);
- `FOCUS_T` theo luật 99% (luật 95% cho 614, chặn 5% khung của chính kênh);
- bối cảnh lấy từ tên nơi do lượt gán nhãn ghi (gom theo màu thất bại; người dùng chọn A);
- lượt gán nhãn luôn dùng Opus, không theo cài đặt của người biên tập.

Bộ test: `tests/run.sh` (87 ok) · `tests/render` (đạt) · `tests/learn` (47) · `tests/filmcheck` (178) · `tests/ui` (41 + 33 desktop) · `tests/license` (18) · `tests/online` (196; trong lần chạy cả bộ có 2 lỗi kết nối chập chờn ở `test_host`, chạy riêng thì đạt 17/17).
