# Data Model: Nâng tay nghề bộ dựng 3D

## Item (đồ cầm tay), `catalog.json → items`

| Trường | Kiểu | Ghi chú |
|---|---|---|
| name | chuỗi | `phone`, `book`, `bag`, `cup`, `paper` (đã có) + `ball`, `cards`, `cash`, `box`, `keys` |
| grip | `one` \| `both` | `one` bám tay phải (hoặc tay ghi trong act), `both` giữa hai tay |
| size | số (m) | theo người cao khoảng 1,9 đơn vị kit |
| default_for | danh sách act | act dùng đồ này khi bảng cảnh không ghi đồ (edge case) |

Luật: tên duy nhất; mỗi act cần đồ (`throw`, `carry`, `give`) có một đồ mặc định.

## Act (động tác), `catalog.json → acts`

| Trường | Kiểu | Ghi chú |
|---|---|---|
| name | chuỗi | cũ: `raise-hand`, `wave`, `point`, `shrug-up`, `hands-face`, `cheer`, `lean-in`, `nod`, `tilt-head`, `swap`; mới: `run`, `jump`, `throw`, `carry`, `fall`, `push`, `type`, `give`, `high-five` |
| kind | `gesture` \| `body` \| `pair` | quyết định có tính là hành động thật không (R5) |
| dur | số (s) | thời lượng một lần; `run`, `carry`, `type` lặp tới hết cảnh |
| item | tên item hoặc null | đồ mặc định |
| needs | `partner` hoặc null | `give`, `high-five` cần người thứ hai trong cảnh |

Cách viết trong bảng cảnh: `[t, "<act>"]`, `[t, "<act>:<item>"]`, `[t, "give:<item>@<who>"]`, `[t, "high-five@<who>"]`. `<who>` là chỉ số của người trong `cast` của cảnh.

## Cam (máy), `camera.js → CAMS`

Mới: `hands` (cận tay và đồ, nhắm vào điểm bám, độ sâu nông) và `hero-low` (thấp hơn ngực, nhìn lên, cỡ trung). Mặc định `ots` theo R6.

## Set (bối cảnh), `catalog.json → sets`

| Trường | Kiểu | Ghi chú |
|---|---|---|
| name | chuỗi | thêm `court`, `rooftop`, `parking`, `street-dusk` |
| outdoor | bool | `street`, `stadium` và 4 bối cảnh mới là true |
| props_min | `{total, layer}` | đếm từ `props` lúc dựng (R7) |
| sky | bool | có vòm trời nhìn thấy |

Bối cảnh `custom:` khai báo `outdoor` trong giá trị trả về; thiếu thì coi là false và ghi cảnh báo.

## CRAFT (trang phim xuất), `window.CRAFT`

Mỗi cảnh một dòng: `[t0, t1, id, {people, action, outdoor, prop, cam}]`
- `people`: số người trong `cast`.
- `action`: có act `kind ≠ gesture` trong cảnh (bool).
- `outdoor`: theo bối cảnh.
- `prop`: có người cầm đồ ở bất kỳ lúc nào trong cảnh.
- `cam`: tên máy sau khi áp mặc định.

Cảnh không có người và cảnh thẻ chữ (`void`, cảnh có `gfx` loại `title`, `chapter` hoặc `end-choice`) được đánh dấu `card: true` và không tính vào mẫu số.

## Craft measure (số đo tay nghề), `template.json → craft`

```json
"craft": {
  "source": "learn craft-label dusk-hypothetical-3, 2026-11-xx, 2192 shots, craftlabel v1",
  "action": {"share_p25": 0.0, "share_p50": 0.0, "share_p75": 0.0, "min": 0.0, "rule": "error"},
  "outdoor": {"range": [0.0, 0.0], "rule": "warn"},
  "prop":    {"range": [0.0, 0.0], "rule": "warn"},
  "ots":     {"range": [0.0, 0.238], "rule": "warn"}
}
```

Khoảng lấy theo từng video (p25–p75 của 10 video), giống cách `shots.json` ghi khoảng. Trước khi đo xong, `action.min` = 0,5 kèm `"source": "studio rule"`.

## Craft label (nhãn của một cảnh mẫu), `craft-labels.json`

`{"v05-S053": {"card": false, "people": 2, "action": true, "outdoor": true, "prop": false}}`, cùng khoá `vNN-Snnn` với `labels-pass2.json`.
