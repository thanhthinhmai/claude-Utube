# Contract: rig ball@3

Như `ball@2` (specs/034 contracts/rig.md), khác ở:

- `CU.RIGS["ball@3"](CU)` trả `{id, size, sizeOf, make, pose, key, place, carry, expression, view}`.
- `size = {w:1000, h:1400, fx:500, fy:1360, headY:300, R:200}` (tuổi `kid`).
- `sizeOf(spec)` → như `size` với `headY` theo `spec.age` (`kid`/`adult` 300, `toddler` ≈ 704).
- `make(o)` nhận thêm `o.age` = `"kid"` (mặc định) | `"adult"` | `"toddler"`. Các khoá khác như `ball@2`; `stripe`, `tie` được bỏ qua.
- Điều khiển trên null `CTRL`: `HL`, `HR`, `FL`, `FR`, `lean`, `crouch` (giống `ball@2`). Vị trí tư thế (`pose`) tính theo vai và hông của tuổi.
- `catalog.json`: thêm `"ages": ["kid", "adult", "toddler"]`; `spec` thêm `"age"`, bỏ `stripe`, `tie`.
