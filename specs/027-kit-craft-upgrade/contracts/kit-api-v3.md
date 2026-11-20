# Contract: bộ dựng v3 (phần thêm vào `specs/023-style-craft-template/contracts/kit-api-v2.md`)

Mọi bảng cảnh v2 vẫn hợp lệ và cho cùng kết quả, chỉ trừ hai thay đổi chủ ý: số màu mặc định, và máy mặc định của cảnh hai người có `talk` mà không ghi `cam` (trước đây không có mặc định, `check()` báo lỗi khi thiếu `cam`).

## Trường mới trong `cast[i]`

| Trường | Ví dụ | Ý nghĩa |
|---|---|---|
| `item` | `"ball"` | đồ cầm từ đầu cảnh (thay cho các tư thế `hold-*`; `hold-*` vẫn dùng được) |
| `hand` | `"left"` | tay cầm của đồ `grip: one` (mặc định `right`) |
| `act` | `[[0.3, "run"], [1.2, "throw:ball"], [1.8, "give:cash@1"], [2.4, "high-five@1"]]` | act mới theo `data-model.md` |

## `cam`

- Tên mới: `hands`, `hero-low`.
- Không ghi `cam` mà cảnh có ≥ 2 người và có `talk`: máy là `ots` nhìn người đang nói; hai cảnh như vậy liền nhau thì đổi người và giữ phía.
- Không ghi `cam` trong mọi trường hợp khác: `check()` vẫn báo lỗi như cũ.

## Bối cảnh

- Tên mới: `court`, `rooftop`, `parking`, `street-dusk`.
- Hàm dựng trả thêm `outdoor`, `props: [{kind, layer}]`.
- Phần dựng mới trong `sets/parts.js`: `tree`, `streetLamp`, `fence`, `house`, `hoop`, `railing`, `parkLines`, `skyDome`, `windowGlow`, `sunBeam`. Bối cảnh `custom:` của phim dùng được tất cả.

## Trang xuất thêm

- `window.CRAFT`: theo `data-model.md`. Bắt buộc với trang dùng kit v3; trang khác không có thì `qc plan` bỏ qua luật craft và ghi vào `skipped`.

## Tất định

Mọi act mới là hàm thuần của `(acts, lt)`. Đồ ném bay theo đường tính từ thời điểm. Đồ chuyển tay có đúng một mốc chủ. Gọi `render(t)` theo thứ tự bất kỳ cho cùng một khung.
