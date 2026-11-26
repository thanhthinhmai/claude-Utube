# Contract: tệp và bộ dựng

- `timing.json`, `animatic/*`: xem [data-model.md](../data-model.md).
- **Bộ dựng AE**:
  - `bundle.py` gói `timing.json` (nếu có) thành `data/timing.json`; `entry.jsx` đặt `CU.DRAFT = true` khi `ae draft`.
  - `lib.jsx`: `CU.shotFrames(id)` → số khung từ `data/timing.json`, hoặc `undefined` khi không có tệp hay không có shot. Mã phim viết `var n = CU.shotFrames("S2") || 117;`.
  - `lib.jsx`: `CU.keyScan(comp)` → `[{layer, prop, t0, t1}]` (ES3, đệ quy `PropertyGroup`, chỉ thuộc tính `numKeys ≥ 2`, `t` theo giây trong comp).
  - `build_core.jsx`: sau mỗi shot gọi `CU.keyScan`, ghi `keys_<proj>.json`; khi `CU.DRAFT`: `MASTER.resolutionFactor=[4,4]`, render settings Draft (R6), tên tệp `draft.mp4`.
- **Phim AE mới** (skill `film-make`, `tools/ae/ANIMATIC.md`): thời lượng shot chỉ lấy từ `CU.shotFrames`; không để mảng thời lượng riêng trong `mix.py`.
- **Chuyển phim cũ**: lần dựng đầu của phim không có `timing.json` ghi tệp từ `shots_<proj>.json` (thời lượng thật), `origin` = giá trị đó.
