# Contract: rig theo phiên bản và comp bảng mẫu (ExtendScript)

## Đăng ký rig

Mỗi `tools/ae/kit/rigs/ball/v<N>/ball.jsx` chỉ có một câu lệnh cấp đầu:

```js
CU.RIGS = CU.RIGS || {};
CU.RIGS["ball@N"] = function (CU) {
  // toàn bộ hàm của rig là biến cục bộ trong factory (không gán vào CU.*)
  return {
    catalog: function () { return {views:[...], expressions:[...], poses:[...], walk:true}; },
    make: function (o) { /* = CU.ball(o) của phim thử; o = spec + {name, dur, view, look, keys, walk, item, …} */ },
    pose: function (name) { /* = CU.ballPose */ },
    place: function (comp, P, x, y, s, moves) { /* = CU.place */ },
    carry: function (comp, layer, name) { /* = CU.carry */ }
  };
};
```

- Phim gọi qua `CU.rig("ball@1")`; hàm này do `bundle.py` sinh trong `entry.jsx`: `CU.rig = function (id) { return CU._rig[id] || (CU._rig[id] = CU.RIGS[id](CU)); };`.
- Shot gọi nhân vật qua `CU.char("hero", {view, dur, …})`: `bundle.py` sinh `CU.CAST` từ `cast/cast.json`, nên nhân vật luôn dựng bằng đúng `rig` và `spec` đã duyệt.
- `bundle.py` gói mọi thư mục `rigs/ball/v<N>/` mà `cast/cast.json` của phim nhắc tới, cộng bản mới nhất (cho shot chưa gắn nhân vật).
- Tên comp do rig tạo bắt đầu bằng `"B "` (không `"P "`: build_core thu gọn precomp `"P …"`, xem specs/032).

## Comp bảng mẫu (`tools/ae/kit/castsheet.jsx`)

- `CU.castSheet(cast, only)`: với mỗi nhân vật (hoặc chỉ các id trong `only`):
  - **Hình tĩnh**: mỗi hình 1 khung, nền phẳng `#ecebf0`, nhân vật đặt giữa, chân ở 92% chiều cao, cao 80% khung. Thứ tự: `front`, `back`, `34`, rồi `expr-<key>` (cận đầu, góc trước), rồi `pose-<key>` (toàn thân).
  - **Clip đi bộ**: 75 khung, nhân vật đi tại chỗ (`walk` của rig, nền trượt), nếu `needs.walk`.
  - **Nhóm**: một khung `group` xếp các thành viên cạnh nhau.
- Khung 1920×1080, 30 fps. Hình nào lỗi (hàm rig ném lỗi, key ngoài danh mục) thì khung đó trống và ghi `missing`.
- Ghi `CU.WORK + "/sheet_<proj>.json"`: `{frames:[{character, key, group, label, para?, frame: <chỉ số khung>, len: 1|75, missing?: "lý do"}], catalog:{…}}`.
- Render như mọi lượt (`master.mp4` qua hàng đợi render của AE); `tools/ae/sheet.py` tách khung bằng ffmpeg.
