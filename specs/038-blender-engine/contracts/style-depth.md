# Style depth contract

## Labeler schema v3 (`tools/filmcheck/labeler.py`)

Mỗi shot gồm các trường cũ (`id`, `scale`, `angle`, `foreground_blur`, `place`, `confidence`) cộng thêm:

```json
{"cam_height":"low|eye|high|top","lens":"wide|normal|long","depth":"shallow|mid|deep",
 "layers":["fg","mid","bg","far"],"occluder":true}
```

- `LABELER_VERSION` tăng lên, nên cache cũ (`.check/labels.json`, `profile/<vid>/shots.json`) được đo lại.
- Hints gửi kèm mỗi khung: `{"horizon":0.42,"hfov_deg":62|null,"lines":118}` từ `vanish.py`.
- Lượt Claude dùng `models.current()`.

## `vanish.py`

`measure(img) -> {"horizon": float|None, "hfov_deg": float|None, "vps": [[x,y],…], "lines": int}`

- Ít hơn 20 đường thẳng thì mọi giá trị là `None`.
- `horizon` < 0,3 mà nhãn là `cam_height=low`, hoặc ngược lại, thì shot được đánh `check`.

## Luật `qc depth` (so với `depth.by_size[size]` của phong cách)

| Luật | Chặn khi | Cách sửa gợi ý |
|---|---|---|
| `depth_close` | cỡ đo được chặt hơn `shot_plan.size`, hoặc `lens=long` trong khi mẫu có `long` < 10% | lùi máy, dùng ống kính normal hay wide |
| `depth_shallow` | số lớp < `layers_p25`, hoặc `depth` thấp hơn mức mà mẫu dùng ≥ 25% | thêm vật che tiền cảnh, tường xa, cửa sổ |
| `card_angle` | `card_angle_max` > 75° | xoay nhân vật về phía máy hoặc dời máy |

Cảnh báo cả phim:
- `size_share`: tỉ lệ một cỡ cảnh lệch quá 10 điểm phần trăm.
- `few_samples`: cỡ cảnh có `n` < 5, chỉ cảnh báo, không chặn.
