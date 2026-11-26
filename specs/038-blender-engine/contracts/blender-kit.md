# Blender kit contract (script shot của phim)

Mỗi shot Blender là một tệp `films/<tên>/blender/S<n>.py`:

```python
def shot(k):
    k.set("auditorium", rows=8, light="dusk")        # bối cảnh của bộ dựng
    k.cam(size="wide", height="eye", lens="normal",  # theo shot_plan, có thể ghi đè
          move="dolly", frm=(0, -14, 1.6), to=(0, -9, 1.6), look=(0, 0, 1.2))
    k.cast("hero", at=(0, -2, 0), face=180, path=[(0, -2, 0), (0, 1, 0)])  # lớp từ rig AE
    k.crowd(area=(-6, 2, 6, 10), count=40, actions=["sit", "clap"])
    k.fg("seat_backs")                               # vật che tiền cảnh
    k.fx("confetti", t0=1.5)
```

Luật:
- Script chỉ gọi `k.*`. Không được `import bpy` trực tiếp. Hàm còn thiếu thì thêm vào bộ dựng chung, không viết trong phim.
- Không có đường dẫn máy. Tệp lớp nhân vật do `entry.py` tìm trong `request.json`.
- Thời lượng và fps lấy từ `timing.json`.
- Động tác của `k.cast` dùng tên trong `catalog.json` của rig (`pose`, `expr`, `walk`) qua `act=[{"t":0.5,"pose":"wave"}]`.

Đầu ra của `entry.py`:
- Khung PNG ở `<work>/<run>/S<n>/f####.png`.
- `log.txt` theo [bridge-api.md](bridge-api.md).
- Lượt tính (`mode: "plan"`) không render, chỉ ghi `layers.json` và `card_angle_max`.
