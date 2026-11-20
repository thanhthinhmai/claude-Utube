# Quickstart: kiểm spec 027

Chạy từ gốc repo. Dựng bằng GPU (`sh bin/studio status` phải có dòng `dựng hình: gpu`).

## 0. Đo tay nghề kênh mẫu (FR-014)

```sh
sh bin/studio learn craft-label dusk-hypothetical-3            # khoảng 20 lượt gọi Opus trên gói của chủ xưởng
sh bin/studio learn craft-label dusk-hypothetical-3 --write dusk-hypothetical
```
Mong đợi: 2.192 cảnh có nhãn; `template.json → craft` có khoảng và nguồn; `EVIDENCE.md` có mục mới. Kiểm tay 30 cảnh ngẫu nhiên trên bảng ảnh: nhãn `action` đúng ≥ 85%.

## 1. US1: đồ, động tác, góc máy

```sh
node --test my-styles/dusk-hypothetical/kit/test/*.test.mjs
sh bin/studio kit use kit-acting --style dusk-hypothetical   # trang thử: mỗi act mới một cảnh
sh bin/studio page still kit-acting --range 0:40:2 --size 960x540
sh bin/studio page clip kit-acting --from 0 --to 10
```
Mong đợi: test xanh; bảng so ba hàng (ô kênh mẫu có `action` hoặc `prop`, trước, sau) và clip được người dùng duyệt; đồ không rời tay, chuyển tay đúng một khung.

## 2. US2: bối cảnh

Trang `kit/catalog.html` xuất khung toàn và khung trung có người cho mỗi bối cảnh. Mong đợi: `node --test` đếm `props_min` đạt; bảng so với ô kênh mẫu có `place` cùng loại được người dùng duyệt.

## 3. US3: ánh sáng và hậu kỳ

```sh
sh bin/studio learn compare dusk-hypothetical-3 --ref <khung gốc> --ours <khung chứng minh v3> --round 1
```
Mong đợi: độ sáng và độ bão hoà trung vị trong khoảng; đo thời gian mỗi khung có và không AO, một phút phim tăng ≤ 50%; `films/pause-ten-seconds` dựng 5 khung giống hệt trước (kit đã chép không đổi).

## 4. US4: phút đầu làm lại

```sh
# films/pause-ten-redo: lines/voices/cues 0:00–1:00 của pause-ten-seconds, kit v3
sh bin/studio qc plan pause-ten-redo
sh bin/studio qc shots pause-ten-redo
sh bin/studio render pause-ten-redo --fps 60
sh bin/studio qc pause-ten-redo
```
Mong đợi: tầng 0–4 không có lỗi nặng; `craft_action` đạt; chuyển động trong cảnh cao hơn bản gốc; nhãn tầng 2 khớp ≥ 80%. Bảng so ba hàng và hai clip 60 s (trước, sau) để người dùng chọn.

## Kết quả (2026-11-19)

| Tiêu chí | Kết quả | Số đo |
|---|---|---|
| SC-001 cảnh có người có hành động ≥ mức tối thiểu | **Đạt** | phút làm lại 31% (5/16) so với mức 10% (p25 kênh mẫu, trung vị 14%); bản gốc 0% |
| SC-002 đồ trong tay, qua vai, ngoài trời trong khoảng kênh mẫu | **Đạt một phần** | đồ 19% (khoảng 8–25%) ✓, qua vai 14% (4–24%) ✓, ngoài trời 18% (29–76%) ✗: kịch bản đặt phút đầu trong quán, đã chấp nhận có lý do |
| SC-003 chuyển động trong cảnh cao hơn, không `still_person` | **Đạt một phần** | độ khác trung bình giữa hai khung (bỏ chỗ cắt) 0,625 → 0,680 (+9%), trung vị 0,412 → 0,338 (−18%); không cảnh nào `still_person` |
| SC-004 độ sáng, bão hoà trong khoảng; `learn compare` | **Đạt** (theo cách đo trong khung hình, R8) | bối cảnh v3: sáng 0,354, bão hoà 0,387 so với kênh mẫu 0,327 / 0,360; theo cách đo cả khung (có dải đen) phim vẫn cảnh báo `style_luma`, đã ghi lý do |
| SC-005 nhãn tầng 2 khớp ≥ 80% | **Đạt** | 19/23 (83%; cỡ cảnh lệch ≤ 1 bậc, góc đúng). Lệch: S001 máy `hands` đọc thành med·high; S006, S017, S021 cảnh đồ vật hoặc thẻ |
| SC-006 thời gian dựng tăng ≤ 50% | **Đạt** | 450–466 s/phút phim (hai lượt dựng 469 s và 486 s cho 62,6 s) so với 416 s/phút của bản gốc (+12%); AO 8 mẫu +14 ms/khung |
| SC-007 bảng so được duyệt | **Bỏ qua theo người dùng** (giai đoạn thử: không dừng chờ duyệt) | bảng so: `films/kit-acting/compare-acts.jpg`, `compare-cams.jpg`, `films/kit-sets/compare-us2.jpg`, `compare-us3.jpg`, `films/pause-ten-redo/compare/compare.jpg` và hai clip `before-0-62.mp4`, `after-0-62.mp4` |
| SC-008 phim cũ không đổi | **Đạt** | 10/10 khung giống hệt từng byte |

Tầng 4 của phút làm lại còn 1 lỗi do cách cắt: phút đầu dừng giữa đoạn P10 nên giọng thiếu phần còn lại của kịch bản (`qc` so cả kịch bản). Phim đầy đủ không gặp lỗi này.
