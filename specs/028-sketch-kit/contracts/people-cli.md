# Contract: lệnh thư viện người thật

Mọi lệnh chạy từ gốc dự án; mã thoát 0 = xong, 1 = lỗi dùng lệnh, 2 = không tìm thấy, 3 = bị chặn.

| Lệnh | Việc |
|---|---|
| `sh bin/studio people list` | in mọi người: slug, tên, trạng thái (`approved` / `not approved` / `changed since approval`) |
| `sh bin/studio people new <slug> --name "<tên>" [--role "<vai>"] [--ref-url <url> --license <giấy phép> --author <tác giả>] [--from <tệp figure.js>]` | tạo `people/<slug>/` với `figure.js` (từ tệp có sẵn hoặc mẫu), `person.json` chưa duyệt; ảnh tham chiếu tải vào `.sheet/ref.*` (không vào git) |
| `sh bin/studio people sheet <slug>` | vẽ bảng mẫu `people/<slug>/.sheet/sheet.jpg`: hình nhìn thẳng, 3/4, sau lưng, 4 biểu cảm, cạnh ảnh tham chiếu (nếu có); in đường dẫn |
| `sh bin/studio people approve <slug> [--note "<ghi chú>"] [--source chat|ui]` | ghi duyệt với băm hiện tại của `figure.js`. **Chỉ chạy khi người dùng đã duyệt bảng mẫu**; agent không tự duyệt (như `lesson approve`) |
| `sh bin/studio people use <phim> <slug…>` | chép người đã duyệt vào `films/<phim>/people/`, ghi `index.json`; người chưa duyệt → mã 3, in người nào |
| `sh bin/studio people check <phim>` | so bản chép trong phim với thư viện: báo người chưa duyệt hoặc đã đổi; tầng 1 dùng cùng hàm |

Luồng làm phim (ghi vào `CLAUDE.md`): phim có người thật → `people list`; người chưa có → `people new` + `people sheet`, gửi bảng mẫu cho người dùng, chờ duyệt, `people approve`; rồi `people use <phim> …` trước khi viết bảng cảnh.
