# Contract: trang phim (020)

Trang phim (`films/<tên>/index.html` và các script của nó) xuất các giá trị dưới đây lên `window` khi `READY === true`. Hợp đồng này nằm trong code của phim, không trong thư viện (hiến pháp VI). Luồng làm phim nhắc người làm phim xuất chúng.

| Tên | Bắt buộc | Dạng | Dùng ở |
|---|---|---|---|
| `DUR` | có (đã có từ thư viện) | số giây | mọi tầng |
| `SHOTS` | có với phim mới | `[[t0, t1, set, id], …]`, nối liền từ 0 tới `DUR` | tầng 1, 2, 3 (mã cảnh) |
| `CUES` | không (nếu không có thì đọc `cues.json`, rồi `.srt`) | `[[t0, t1, text], …]` | tầng 1 (`cue_short`), tầng 2 (vùng phụ đề), gói đăng |
| `CARDS` | không (nếu không có thì chạy `readcheck`) | `[[t0, t1, id, text], …]` | tầng 1 (`card_read`), tầng 2 (thêm ảnh lúc thẻ hiện rõ nhất) |
| `TEXTS(t)` | không (đã có từ 010) | `[{id, text, x0, y0, x1, y1}]` | tầng 2 (hộp chữ, phông) |
| `CLEAN` | trang **đọc** giá trị này | bool, do công cụ đặt | thumbnail: khi `true`, phim không vẽ phụ đề hay thẻ chữ lên canvas |

`films/pet-swap` đã xuất `SHOTS` (đúng dạng trên) và `TEXTS`, nên dùng làm mẫu.
