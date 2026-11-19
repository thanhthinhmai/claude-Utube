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
