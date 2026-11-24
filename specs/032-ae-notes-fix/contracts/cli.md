# Lệnh `sh bin/studio ae …`

Mọi lệnh in `film: <thư mục>` (chọn thư mục như spec 029 R8) và từ chối phim không có `engine: "ae"` (mã 2, nói phim dùng bộ máy nào).

| Lệnh | Việc | Mã thoát |
|---|---|---|
| `ae build <phim> [--shots S1,S13…]` | dựng các shot (mặc định: mọi shot) qua cầu nối (trong việc) hoặc AE trên máy (`local.py`, ngoài việc); in `CHECK …` của luật dàn cảnh | 0 xong · 1 lỗi dựng hoặc có CHECK · 3 không có AE / cầu nối |
| `ae render <phim>` | dựng và render bản tổng, ghép tiếng, ghi `shots.json` | 0 · 1 · 3 |
| `ae fix <phim> <S…>` | dựng lại các shot rồi ghép vào video hiện có theo khung; ra `out/fix.mp4` + `shots.json`; ngoài việc thì gọi luôn `film replace` | 0 · 1 · 3 |
| `ae uses <phim> <hàm…>` | in các shot dùng hàm của bộ dựng chung | 0 |
| `ae status` | cầu nối có sẵn không, AE tìm thấy ở đâu, hàng đợi | 0 |
| `ae new <phim> [--fps 30]` | tạo `film.json` + `ae/shots.jsx` trống cho phim AE mới | 0 · 2 |
| `config ae [--afterfx P] [--aerender P] [--work D]` | cấu hình AE cho dòng lệnh ngoài app (`~/.config/claude-utube/ae.json`) | 0 · 2 |
