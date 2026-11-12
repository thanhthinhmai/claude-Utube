# Contract: lệnh (021)

Mã thoát như các lệnh khác của xưởng:
- **0**: xong hoặc đạt;
- **1**: có lỗi hoặc chưa đạt;
- **2**: sai cách dùng hoặc không chạy được.

## `sh bin/studio learn shots <set> [--only vNN …]`
- Cần video còn trên máy (chạy trước `clean`).
- Với mỗi video: dò cắt cảnh (research R2), chụp khung giữa mỗi cảnh ở 960×540, đo độ nét (R1), tính chữ ký màu và gom bối cảnh (R4).
- Ghi ra `profile/<vid>/shots.json` (chưa có nhãn) và `profile/<vid>/shot-sheets/<vid>_shots_<n>.jpg` (6 cột, tối đa 48 ô, mỗi ô ghi `S001`, rộng dưới 1280 px).
- In số cảnh và số cắt mỗi phút của từng video. Ngoài khoảng 16–26 lần mỗi phút thì in `!`; khoảng này đọc từ `cuts_per_min` của phong cách nếu đang học lại.
- Chạy lại thì tiếp tục từ chỗ dừng.

## `sh bin/studio learn label <set> [--pass 2 --sample 40]`
- Chạy lượt gán nhãn độc lập (R3) trên các bảng ảnh cảnh, rồi ghi nhãn vào `shots.json`.
- `--pass 2 --sample 40`: lượt thứ hai, độc lập, trên 40 cảnh lấy đều từ các video (chọn ngẫu nhiên với seed cố định); ghi riêng ra `labels-pass2.json` và tính `agreement.json` (SC-001). In ra `scale same 0.85 · within one 0.97 · angle same 0.82`.
- In các cảnh có `check: true` để người học xem lại trên bảng ảnh. Sửa một nhãn bằng tay: `learn label <set> --set vNN:S014 scale=huge`. Lần sửa được ghi lại trong `shots.json` là `edited_by: "user"`.

## `sh bin/studio learn summary <set>`
- Như cũ, thêm `shot_grammar` cho mỗi video và cho cả bộ.

## `sh bin/studio learn save <set> --slug S … [--update]`
- Như cũ, thêm ghi `shots.json` của phong cách (data-model "ShotGrammarRefs") từ `summary.json`.
- `--update`: ghi đè phong cách riêng đã có cùng slug. Từ chối (mã 1) khi `EVIDENCE.md` mới làm mất một dòng của bảng "Corrections log" cũ. Giữ `created`, ghi `updated`.

## `sh bin/studio qc shots <film>` (specs/020, đổi thêm)
- Mỗi khung có thêm `focus` (R1). Luật mới mức `block`: `blurred` (không ô nào nét; được phép ngoại lệ).
- Gọi lượt gán nhãn khi `.check/labels.json` cũ hơn nguồn phim. In `labels: 192 shots · claude-opus-5-5 · 4 sheets` hoặc `labels: reused`.
- Luật mới mức `warn` khi phong cách có `shots.json`: `style_scale_<loại>`, `style_angle_<loại>`, `style_scale_change`, `style_same_scale_run`, `style_focus`, `style_top_set`, mỗi luật kèm mã cảnh. Phong cách không có `shots.json` thì in `! shot grammar: the style has no measurements, skipped`. Lượt gán nhãn không chạy được thì có `shot_grammar_unchecked` (`warn`).
- Bảng ảnh: mỗi ô ghi `<mã> · <cỡ> · <góc>`.

## `sh bin/studio qc except <film> <shot> blurred --reason "…"`
- `blurred` được thêm vào danh sách luật cho phép ngoại lệ (specs/020 R10).
