# Contract: lệnh

## `sh bin/studio learn craft-label <set> [--force]`

- Đọc bảng ảnh cảnh của `references/<set>/profile/vNN/shot-sheets/`, gọi `claude -p` (model của xưởng) khoảng 110 cảnh mỗi lượt, rồi ghi `references/<set>/profile/craft-labels.json`.
- Cache theo `craftlabel` version và nguồn bảng ảnh: chạy lại thì chỉ gán phần còn thiếu. `--force` gán lại tất cả.
- In mỗi video một dòng `✓ vNN: N shots (k call(s), <model>)`, rồi in bảng tỉ lệ theo video (action, outdoor, prop, ots) và khoảng p25–p75.
- `--write <style>`: ghi `craft` vào `my-styles/<style>/template.json` và thêm một mục vào `EVIDENCE.md`.
- Mã thoát: 0 đạt; 1 thiếu bảng ảnh hoặc `claude` lỗi sau 2 lần thử; 2 sai cú pháp.

## `sh bin/studio qc plan <film>`: luật mới (tầng 1)

| Luật | Mức | Khi nào |
|---|---|---|
| `craft_action` | lỗi | tỉ lệ cảnh có người có hành động < `craft.action.min` |
| `craft_outdoor` | cảnh báo phong cách | tỉ lệ cảnh ngoài trời ngoài `craft.outdoor.range` |
| `craft_prop` | cảnh báo phong cách | tỉ lệ cảnh có đồ trong tay ngoài khoảng |
| `craft_ots` | cảnh báo phong cách | tỉ lệ cảnh qua vai ngoài khoảng |
| `craft_item_default` | cảnh báo | act cần đồ mà không ghi đồ (đã dùng đồ mặc định) |

Mỗi dòng lỗi có: số đo, giới hạn, và tối đa 8 mã cảnh nên sửa (với `craft_action`: các cảnh có người mà chỉ có cử chỉ, dài nhất trước). Phim chấp nhận lệch phong cách bằng `qc accept-style` như cũ. `craft_action` là lỗi nên không miễn được bằng `accept-style`; chỉ miễn được từng cảnh bằng `qc except <film> <cảnh> craft_action --reason …`, và tính lại tỉ lệ sau khi bỏ cảnh được miễn.
