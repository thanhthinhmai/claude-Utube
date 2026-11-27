# File contract: 039

Định dạng chi tiết nằm ở [data-model.md](../data-model.md). Tệp này chỉ ghi ai ghi tệp nào và ai đọc.

| Tệp | Ghi bởi | Đọc bởi | Vào git |
|---|---|---|---|
| `references/<set>/profile/<vid>/camera.json` | `learn camera` | `learn save`, `camera suggest --set` | không |
| `my-styles/<style>/camera.json` | `learn save` | `camera suggest`, `points` (có thư viện không) | có |
| `my-styles/<style>/camera/<vid>-<id>-{a,b}.jpg` (360 px, ≤ 150 shot) | `learn save` | trang Camera, `options.ref_frames` | có |
| `films/<f>/camera/options.json` | `camera suggest`, `camera choose`, `camera retime` | trang Camera, `points`, `camera stills` | không |
| `films/<f>/camera/stills/S#-o<n>.jpg` (480×270) | `camera stills` | trang Camera | không |
| `films/<f>/camera/notes.json` | `camera note`, op `camera_note_*` | trang Camera, `reviews.decide` | không |
| `films/<f>/film.json` `shot_plan.<S>.camera` | chỉ `camera choose` / `retime` | AE `bundle.py` → `ae/data/camera.json`, Blender `camera.py`, `qc camera`, `qc depth` | không |

Bất biến:
- Trang app không ghi tệp nào. Mọi thay đổi đi qua op trong `edit.py` (specs/026).
- `options.json` được ghi bằng cách ghi tệp tạm rồi đổi tên, dưới khoá của phim (giống timing.json).
- Khung bằng chứng chỉ được cắt khi video mẫu còn trên máy. Video mẫu không bao giờ được chép vào `my-styles/`.
