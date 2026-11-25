# Research: Duyệt nhân vật cho phim After Effects

## R1. Dựng bảng mẫu bằng đường dựng AE sẵn có

- **Decision**: một comp `SHEET` cho mỗi lượt: mỗi hình tĩnh (góc, biểu cảm, tư thế) chiếm đúng 1 khung, nối tiếp nhau; clip đi bộ 75 khung (2,5 s) ở cuối mỗi nhân vật. AE render ra `master.mp4` như mọi lượt dựng; `tools/ae/sheet.py` đọc `sheet_<proj>.json` (danh sách khung → nhân vật, mã hình) do jsx ghi, rồi dùng ffmpeg tách mỗi khung thành JPEG 720 px và cắt clip đi bộ thành mp4 nhỏ.
- **Rationale**: `local.py` và `remote.py` (cầu nối app) chỉ biết chờ `master.mp4` và tệp kết quả; không cần dạy cầu nối định dạng mới (PNG sequence), giữ nguyên luật "AE tự render qua hàng đợi, không aerender".
- **Alternatives**: render từng hình thành PNG (cần đổi output module và cầu nối); chụp hình bằng `saveFrameToPng` (không ổn định trên mọi bản AE, chạy trong UI thread).

## R2. Rig theo phiên bản

- **Decision**: rig nằm ở `tools/ae/kit/rigs/ball/v<N>/ball.jsx`. Mỗi tệp bọc toàn bộ hàm trong một factory `CU.RIGS["ball@N"] = function(CU){ … return {make, pose, head, …}; }` để hai phiên bản cùng nạp không đè nhau. `tools/ae/rigs.lock` ghi `{"ball@1": "<sha256 cả thư mục>"}`; test `tests/ae/test_rigs.py` thất bại khi một thư mục đã khoá bị đổi. Thêm bản mới = thư mục mới + dòng khoá mới.
- **Rationale**: bất biến kiểm được bằng test (SC-006), đơn giản hơn lưu rig trong kho.
- **Alternatives**: thẻ git (không có khi chạy trong app đã cài); chép rig vào kho nhân vật (mỗi nhân vật một bản, khó báo bản mới).

## R3. Thông số nhân vật

- **Decision**: `spec` của nhân vật là đúng các tham số của `CU.ball(o)` hiện có trong `ballchar.jsx` (màu hoodie, quần, giày, kiểu mũ hoặc tóc và màu, tỉ lệ, sọc, cà vạt…). `cast.py` kiểm khoá và kiểu theo `contracts/files.md`; jsx nhận nguyên khối.
- **Rationale**: không thêm lớp chuyển đổi; Claude và rig cùng đọc một cấu trúc.

## R4. Ghi chú có ghim

- **Decision**: `cast-notes.json` mới, cùng mẫu `shot-notes.json` (id `n-<8hex>`, `base` = sha256 tệp, 409 `changed`, `lot`), khoá theo nhân vật thay vì shot; mỗi ghi chú thêm `frame` (mã hình hoặc null), `x`, `y` (0–100, một chữ số thập phân) và `kind` (`note` | `view`). Viết `castnotes.py` riêng, dùng lại các hàm tiện ích của `shotnotes.py` (băm, ghi nguyên tử) qua import.
- **Rationale**: shot-notes không có toạ độ; trộn hai loại vào một tệp làm phức tạp `derive()` và test sẵn có.

## R5. "Send notes to Claude" trong và ngoài việc làm phim

- **Decision**:
  - **Trong việc làm phim** (bước Cast đang chờ duyệt): nút gửi một quyết định `revise` cho yêu cầu duyệt `cast` (cơ chế sẵn có của specs/026). Claude của chính việc đó đang `review wait` nhận lại, chạy `cast notes show`, sửa `cast.json` hoặc rig, `ae sheet --only <các id>`, `cast notes reply …`, rồi gửi lại yêu cầu duyệt. Không tạo việc thứ hai.
  - **Ngoài việc làm phim** (trang Cast library: sửa nhân vật trong kho hoặc xem trước rig mới): app tạo việc `fix` với `input.target = "cast"` (như specs/032), worker chép thư mục làm việc tạm, agent theo `fix_prompt` nhánh cast, `finish_fix` chép kết quả về kho.
- **Rationale**: đúng câu trả lời làm rõ (app tự chạy nền, không mở chat) mà không thêm loại việc mới; trong việc làm phim, Claude đã có đủ ngữ cảnh.
- **Alternatives**: luôn tạo việc `fix` riêng (hai Claude cùng sửa một phim; việc làm phim phải dừng chờ).

## R6. Vị trí kho nhân vật

- **Decision**: `$STUDIO_DATA/accounts/<owner>/channels/<kênh>/cast/<char-id>/v<n>/` (`character.json`, `sheet/`), chỉ mục `…/cast/index.json`. `castlib.root()` lấy kho theo thứ tự: tài khoản của request (app online) → app đang chạy cho làm phim bằng chat (`host.running_pointer` + `owner_id`, như `app_film`) → không có (trả `None`, lệnh báo "the app is not running").
- **Rationale**: đúng câu trả lời làm rõ (chỉ trong app, không vào git); dùng lại cách tìm app của specs/014.

## R7. Điểm duyệt và bước

- **Decision**: `POINTS = ("script","cast","voice","shots","mix","publish")`. Mặc định bật `cast` cho phim AE: `points.set_on` thêm `cast` khi `engine(d) == "ae"` và kênh không tắt rõ. Dấu của `cast` = băm `cast/cast.json` bỏ trường duyệt + băm `cast/sheets/**/sheet.json`. Điểm `cast` "approved" khi mọi nhân vật đã duyệt với dấu hiện tại; duyệt cả dàn ghi duyệt cho từng nhân vật rồi gọi `points.approve`. Phim không phải AE: `cast` luôn `skipped`. Cổng: `voice make` gọi `points.gate(d,"cast")` sau `script`.
- **Bước**: `steps.STEPS` thêm `Cast` sau `Script`; `GRAPH`: Script→Cast, Cast→Picture (không Cast→Voice), đúng FR-005.
- **Giới hạn cũ**: các Literal `max_length=5` (server.py:50, api_online.py:176, :383) nâng lên 6.

## R8. Biểu cảm và tư thế theo kịch bản

- **Decision**: `cast.json → characters[].needs = {expressions:[{key,label,para}], poses:[{key,label,para}], walk: bool}`. Claude điền khi lập kế hoạch phim (skill film-make và `AE_PICTURE` của agent). `key` phải nằm trong danh mục rig (`CU.RIGS[..].catalog()`, được `ae sheet` ghi ra `cast/catalog.json`); `key` ngoài danh mục dựng thành ô "No picture yet".
- **Rationale**: câu trả lời làm rõ số 4; danh mục do rig khai báo nên kiểm được.

## R9. Đưa nhân vật từ kho vào phim

- **Decision**: `cast use <phim> <kênh>/<id>[@v]` chép `character.json` vào `cast.json` (giữ `from_library`) và chép ảnh bảng mẫu; nhân vật ở trạng thái duyệt nếu `needs` của phim ⊆ hình đã duyệt trong kho, nếu không chỉ hình thiếu được dựng và cần duyệt.
- **Lưu vào kho**: khi cast được duyệt và `save_to_library` bật, `castlib.save()` ghi bản mới (`v<n+1>`) nếu thông số khác bản mới nhất, nếu không chỉ thêm tên phim vào `films`.
