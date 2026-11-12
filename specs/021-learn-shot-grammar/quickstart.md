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
