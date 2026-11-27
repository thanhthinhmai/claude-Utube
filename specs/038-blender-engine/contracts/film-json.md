# film.json / shots.json contract

Xem [data-model.md](../data-model.md), các mục "Shot plan", "Shot marks" và "Layers plan". Tương thích ngược:

- `film.json` không có `shot_plan` → mọi shot dùng AE. `bundle.tar` và `build.mp4` y hệt bản 032 (test so sha của bundle).
- `shots.json` có `source:"ae"` và không có `engines` vẫn đọc được ở mọi nơi (trang phim, `notes`, `film replace`).
- Trang phim của app chỉ đọc `shots`. `engines` là thêm vào, trang cũ bỏ qua.
