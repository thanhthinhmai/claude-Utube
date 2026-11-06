# Contract: hồ sơ đo

Định dạng file chi tiết ở [data-model.md](../data-model.md). Các điểm ràng buộc với bên dùng (skill, agent, `save`):

- `frames.csv`: dòng đầu là tên cột theo đúng thứ tự `i,t,dx,dy,motion,motion_ok,hist_d,cut,flash,luma,contrast,sat,dark,bright`. Số thực in 4 chữ số thập phân.
- `video.json` và `summary.json`: UTF-8, có khoá `schema: "style-learn/1"`. Thêm trường mới chỉ được thêm, không đổi nghĩa trường cũ.
- Đơn vị cố định: thời gian = giây; chuyển động `motion_720` = px/khung ở chiều rộng 720; màu 0–1; độ lớn âm thanh = LUFS; tốc độ đọc theo `unit`.
- `sheets/<id>_<NNNN>.jpg`: `NNNN` = chỉ số ảnh ghép tính từ 0, mỗi ảnh 2 giây; nhãn trong ảnh là thời điểm gốc của video.
- `measurements/summary.json` khi lưu vào `my-styles/`: là `summary.json` đã bỏ `skipped[].id`, mọi `title`, `channel`, `origin`.
