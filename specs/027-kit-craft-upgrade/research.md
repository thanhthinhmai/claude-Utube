# Research: Nâng tay nghề bộ dựng 3D

## R1. Gán nhãn tay nghề: module riêng hay mở rộng `labeler.py`

- **Decision**: module riêng `tools/filmcheck/craftlabel.py`, dùng lại cách gọi `claude -p` và cách chia bảng ảnh của `labeler.py`. Phiên bản prompt riêng, cache riêng (`craft-labels.json`).
- **Rationale**: thêm trường vào `labeler.py` sẽ đổi phiên bản của nó, làm mất cache nhãn cỡ cảnh và góc của cả bộ mẫu và mọi phim (tầng 2 dùng chung). Ba nhãn mới chỉ cần cho bộ mẫu và cho phép đối chiếu ở US4.
- **Alternatives**: mở rộng `labeler.py` (bị loại: gán lại 2.192 cảnh lẫn mọi phim); đoán từ `place` (bị loại: mẫu 40 cảnh cho thấy `place` không nói gì về hành động hay đồ trong tay).

## R2. Định nghĩa nhãn (để tính tỉ lệ khớp được với bảng cảnh)

- **Decision**:
  - `action`: ít nhất một người trong khung đang làm một việc có mục đích với thân mình, với đồ vật hoặc với người khác (chạy, ném, bê, chơi bài, ôm, đưa đồ). Các trường hợp sau **không** tính: chỉ đứng, ngồi, nhìn, gật, nghiêng đầu, đổi nét mặt, giơ tay chào.
  - `outdoor`: thấy trời, hoặc nơi rõ là ngoài trời.
  - `prop`: một người đang cầm đồ vật.
  - Thẻ chữ, thẻ số liệu, khung trống là `card` và không tính vào mẫu số. Cảnh không có người không tính vào mẫu số của `action` và `prop`.
- **Rationale**: định nghĩa giống hệt cách kit phân loại `kind` của act (R5), nên số của phim so được với số của kênh mẫu (FR-016).
- **Alternatives**: thang 0–3 mức độ hành động (bị loại: khó khớp với bảng cảnh).

## R3. Đồ cầm tay và đồ chuyển tay, giữ tất định

- **Decision**:
  - Mỗi đồ có `grip` gồm `one` (bám tay phải) hoặc `both` (giữa hai tay, như cách cũ), `offset` và `rot` so với bàn tay.
  - Đồ chuyển tay giữa hai người: act `give:<item>@<who>`. Hàm thuần `handoff(lt, t, dur)` cho biết đồ thuộc người nào ở thời điểm `lt`; tay hai người gặp nhau ở điểm giữa tại `t + dur/2`.
  - Ném: đồ bay theo đường parabol tính từ thời điểm, không dùng vật lý.
- **Rationale**: `render(t)` phải tất định; không mô phỏng vật lý thì vẫn test được bằng `node --test`.
- **Alternatives**: IK hai khớp (để sau); vật lý (bị loại: không tất định khi nhảy khung).

## R4. Hậu kỳ: chi phí AO và số mặc định

- **Decision**: bật GTAO của `post.js` (aoAmt khoảng 0,6, bán kính 0,35). Đo thời gian mỗi khung trên GPU, có và không AO, ở 1920×1080, trên 3 bối cảnh. Nếu một phút phim tăng hơn 50% thì giảm số mẫu AO, hoặc chỉ bật AO cho cảnh cỡ trung và gần (cảnh toàn ít thấy AO). Số màu bắt đầu từ v2 (phơi sáng ×1,16, bão hoà ×1,12, contrast 0,08, vignette 0,18, bloom 0,38 ngưỡng 0,85, sương `#c9a0c4` 6–34 m) rồi chỉnh bằng `learn compare`.
- **Rationale**: SC-006. Bản thử v2 chụp ảnh tĩnh nhanh, nhưng chưa đo trên phim dài.
- **Alternatives**: SSAO (bị loại: GTAO đã có trong thư viện); bóng đổ thật nhiều hơn (tốn hơn và vẫn không ra bóng mềm ở góc khuất).

## R5. Phân loại act để đếm "hành động thật"

- **Decision**: `catalog.json → acts` đổi thành bảng `{name: {kind}}`, với `kind` là `gesture`, `body` hoặc `pair`. Các act cũ (`raise-hand`, `wave`, `point`, `shrug-up`, `hands-face`, `cheer`, `lean-in`, `nod`, `tilt-head`, `swap`) và mọi `face:`/`look:` là `gesture`. Riêng `pose:` lấy `kind` của tư thế (`pose:run` là `body`). Một tư thế cầm đồ đứng yên (`hold-phone`) chỉ tính `prop`, không tính `action`. `actOk` vẫn nhận danh sách tên cũ (tương thích ngược).
- **Rationale**: FR-016; phân loại nằm ở một chỗ, cả kit và kiểm cùng đọc.

## R6. Mặc định qua vai và luật 180°

- **Decision**: trong `plan()`, cảnh có ≥ 2 người, có `talk` và không có `cam` thì nhận `cam: {name: 'ots', subject: <người đang nói>}`. Hai cảnh qua vai liền nhau cùng cặp người thì đổi `subject`, giữ máy cùng một phía của đường nối hai người (dấu của `yaw` theo thứ tự cặp). `place()` đã có `shoulder`. Bảng cảnh cũ luôn ghi `cam`, nên không bị đổi.
- **Rationale**: FR-005 và tương thích ngược.

## R7. Bối cảnh: mật độ đồ đếm thế nào

- **Decision**: mỗi bối cảnh trả về `props: [{kind, layer}]` khi dựng (tiền, trung, hậu theo khoảng cách tới máy toàn mặc định). `props_min` trong danh mục ghi tổng và mỗi lớp ≥ 1. Test dựng bối cảnh trong node (three.js chạy không cần WebGL cho phần hình học) rồi đếm.
- **Rationale**: FR-008 test được mà không cần dựng hình.
- **Alternatives**: đếm vật trên ảnh (bị loại: không ổn định, tốn).

## R8. Khoảng màu nếu mâu thuẫn

- **Decision**: chạy `learn compare` trên khung chứng minh với số v3. Nếu độ sáng trung vị vượt 0,29 thì đo lại độ sáng trung vị trên ô bảng ảnh của 10 video (bỏ viền, bỏ thẻ), bằng chính công cụ đo của style-learn. Nếu số đo lại khác `style.json` thì sửa `style.json` và `EVIDENCE.md` kèm bằng chứng, rồi kiểm lại. Không nới tay.
- **Rationale**: FR-012 và hiến pháp VIII. Bảng ảnh cho độ sáng trung bình 59–71 ở kênh mẫu so với 53–55 ở phim, trong khi phim đã qua khoảng 0,22–0,29. Có thể khoảng cũ đo cả khung đen ở chỗ chuyển cảnh, hoặc trung vị lệch so với trung bình; phải đo mới biết.
