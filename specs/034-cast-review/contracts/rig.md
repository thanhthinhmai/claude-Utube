# Contract: rig theo phiên bản và comp bảng mẫu (ExtendScript)

## Đăng ký rig

Mỗi `tools/ae/kit/rigs/ball/v<N>/ball.jsx` chỉ có một câu lệnh cấp đầu:

```js
CU.RIGS = CU.RIGS || {};
CU.RIGS["ball@N"] = function (CU) {
  // toàn bộ hàm của rig là biến cục bộ trong factory (không gán vào CU.*)
  return {
    make: function (o) { /* = CU.ball(o) của phim thử; o = spec + {name, dur, view, look, keys, walk, item, …} */ },
    pose: function (name) { /* = CU.ballPose */ },
    place: function (comp, P, x, y, s, moves) { /* = CU.place */ },
    carry: function (comp, layer, name) { /* = CU.carry */ },
    expression: function (key) { /* preset {look, mouth, …} hoặc null */ },
    view: function (key) { /* tuỳ chọn của góc front|back|34 hoặc null */ },
    size: {w, h, fx, fy, headY, R}
  };
};
```

- Danh mục (góc, biểu cảm, tư thế, walk, khoá spec, mũ) nằm ở `v<N>/catalog.json` cạnh `ball.jsx` để Python đọc được mà không cần AE; cả thư mục bị khoá trong `rigs.lock`.
- Phim gọi qua `CU.rig("ball@1")`; hàm này do `bundle.py` sinh trong `entry.jsx`: `CU.rig = function (id) { return CU._rig[id] || (CU._rig[id] = CU.RIGS[id](CU)); };`.
- Shot gọi nhân vật qua `CU.char("hero", {view, dur, …})`: `bundle.py` sinh `CU.CAST` từ `cast/cast.json`, nên nhân vật luôn dựng bằng đúng `rig` và `spec` đã duyệt.
- `bundle.py` gói mọi thư mục `rigs/ball/v<N>/` mà `cast/cast.json` của phim nhắc tới, cộng bản mới nhất (cho shot chưa gắn nhân vật).
- Tên comp do rig tạo bắt đầu bằng `"B "` (không `"P "`: build_core thu gọn precomp `"P …"`, xem specs/032).

## Comp bảng mẫu (`tools/ae/kit/castsheet.jsx`)

- `tools/ae/sheet.py` lên danh sách hình (Python, từ `cast.json` và `catalog.json`) và ghi `data/cast_sheet.json` = `{fps, cast, frames:[{character, key, group, label, kind: view|expr|pose|walk|group, len: 1|75, view?, expr?, pose?, para?}]}`; key ngoài danh mục bị bỏ trước (không vẽ, `missing_reason` ở `sheet.json`). Mỗi lượt AE tối đa 100 hình, không tách một nhân vật.
- `CU.castSheet(plan)` đăng ký mỗi hình là một shot `S<n>` rồi dùng `CU.build` như mọi lượt:
  - **Hình tĩnh**: 1 khung, nền phẳng `#ecebf0`, nhân vật giữa, chân ở 92% chiều cao, cao 80% khung. Thứ tự: `front`, `back`, `34`, `expr-<key>` (cận đầu, góc trước), `pose-<key>` (toàn thân).
  - **Clip đi bộ**: 75 khung, đi tại chỗ (`walk` của rig, nền trượt), nếu `needs.walk`.
  - **Nhóm**: một khung `group` xếp các thành viên cạnh nhau.
- Khung 1920×1080, 30 fps. Hình nào lỗi khi dựng thì khung đó trống và AE ghi dòng `CHECK missing <n> <character> <key>: <lý do>`; shot không bao giờ ném lỗi nên số khung luôn khớp danh sách.
- Render như mọi lượt (`master.mp4` qua hàng đợi render của AE); `tools/ae/sheet.py` tách khung bằng ffmpeg.
