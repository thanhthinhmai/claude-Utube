# Research: Bộ dựng SVG cho Sketch Explainer

## R1. Đưa bộ dựng vào phim

- **Decision**: dùng lại `kit use` của specs/022 (chép `my-styles/<style>/kit/` vào `films/<tên>/kit/`, ghi `.from` và dấu băm).
- **Rationale**: máy chủ trang của thư viện chỉ phục vụ gốc thư viện và thư mục phim (`/@film/`), nên trang không đọc thẳng `my-styles/`. Lệnh đã có test, có `--update`.
- **Alternatives**: symlink (không chạy qua WSL/Windows, không bền khi phim được chép sang app); nạp từ URL tuyệt đối (máy chủ không phục vụ).

## R2. Thư viện người thật và đường vào phim

- **Decision**: `people/<slug>/` ở gốc dự án (trong git): `person.json` (tên, nguồn và giấy phép ảnh tham chiếu, trạng thái duyệt, dấu băm hình đã duyệt) và `figure.js` (một đối tượng cấu hình vai, cùng định dạng vai chung). `sh bin/studio people use <phim> <slug…>` chép vào `films/<tên>/people/<slug>/` và ghi `films/<tên>/people/index.json` với dấu băm lúc chép. Bảng mẫu tạo vào `people/<slug>/.sheet/` (không vào git) vì có ảnh của bên thứ ba.
- **Rationale**: người dùng chọn thư viện chung (clarify). Cùng lý do R1, trang phim chỉ thấy thư mục phim nên phải chép. Dấu băm `figure.js` làm khoá duyệt: sửa hình thì băm đổi, tự về chưa duyệt (FR-016). Phim đã dựng giữ bản chép (edge case).
- **Alternatives**: để người thật trong `kit/` (vi phạm FR-023, `check-names` chặn); trong thư mục phim (người dùng đã bác ở clarify).

## R3. Lỗi trong trang và tầng 1

- **Decision**: `film()` không ném lỗi làm hỏng trang; nó gom lỗi vào `window.KIT_ERRORS` (`[{shot, kind, name, hint}]`), dựng cảnh lỗi bằng ô báo đỏ, vẫn đặt `READY`. Trang xuất thêm `window.PEOPLE` (`[{slug, hash}]`) và `window.BUBBLES` (`[[t0, t1, shot, who, text, person]]`). `plan.mjs` đọc thêm ba biến; `plancheck.py` biến chúng thành lỗi chặn: `kit_name`, `person_unapproved`, `person_words`.
- **Rationale**: `plan.mjs` chỉ đọc biến sau `READY`; nếu `film()` ném thì tầng 1 chỉ thấy hết giờ chờ, không có mã cảnh. Kiểm duyệt và trích dẫn làm ở Python vì cần đọc `people/` và `SOURCES.md`, và test bằng `unittest` như phần còn lại của tầng 1.
- **Alternatives**: ném lỗi như bộ dựng 3D (mất thông tin ở tầng 1); kiểm tất cả trong JS (trang không đọc được `people/` ở gốc dự án).

## R4. Trích dẫn được phép cho người thật

- **Decision**: chữ trong bong bóng của người thật được phép khi nó (đã chuẩn hoá chữ thường, bỏ dấu câu) là một đoạn liên tiếp của một trích dẫn trong ngoặc kép ở `SOURCES.md`. Bong bóng chỉ gồm ký hiệu `! ? $ … ♪` và tối đa 3 ký tự luôn được phép.
- **Rationale**: `SOURCES.md` của specs/010 ghi trích dẫn trong ngoặc kép kèm nguồn; dùng lại, không thêm định dạng mới.
- **Alternatives**: danh sách trích dẫn riêng trong bảng cảnh (dễ bịa, không gắn nguồn).

## R5. Khớp số đo

- **Decision**: số mặc định lấy thẳng từ `my-styles/sketch-explainer/EVIDENCE.md` và ghi trong `catalog.json → defaults` kèm dẫn:
  - nét `0.0052 × W` cho người ở trung cảnh, đổi theo cỡ người (vì nét đo trên ảnh là nét đã phóng theo cỡ người);
  - bão hoà bối cảnh ≤ 0,15 (đổi màu bối cảnh hiện có về xám, giữ đỏ và xanh lá cho bảng và biển);
  - máy: đẩy 3,3%/giây, kéo 8,6%/giây, giữ cuối 30%, dịch 4%/giây theo bề ngang;
  - hành động mỗi 2,4 giây (khoảng 2–3), dài 1,25 giây.
- **Rationale**: khung chứng minh vòng 3 đã đạt với chính các số này (giữ 30%, dịch); hiến pháp VIII.
- **Alternatives**: để agent tự chỉnh từng phim (phim Anthropic đã lệch, bị người dùng nhận xét).

## R6. Lịch hành động

- **Decision**: `acting.js` là hàm thuần `schedule(shot, seed)` trả về danh sách hành động `{t, kind, who, dur}`: hành động đầu ở 0,15 giây; sau đó mỗi 2–3 giây (giả ngẫu nhiên theo `seed` từ mã cảnh, nên tất định); loại xoay vòng theo vai: cử chỉ, đổi biểu cảm, đồ hoạ dựng lên, ký hiệu bật lên; người cầm biển và người ngồi chỉ đổi biểu cảm. Bảng cảnh ghi hành động cụ thể thì chen vào trước, lịch tự động lấp chỗ trống.
- **Rationale**: phiên bản tự đổi cử chỉ mỗi 2,1 giây ở phim Anthropic chạy được nhưng đổi đều tăm tắp; kênh mẫu có hành động không đều (q1 0,58 – q3 2,42 giây). Hàm thuần có test `node --test` (SC-004).
- **Alternatives**: đổi theo chu kỳ cố định (đơn điệu); bắt bảng cảnh ghi mọi hành động (dài, agent hay quên).

## R7. Bối cảnh từ phần

- **Decision**: `sets/index.js` có các phần (tường, sàn, cửa sổ có phố, giá sách, đèn bàn, bảng, TV, bàn họp, bục, cột nhà chính phủ, dãy nhà, két, tủ máy chủ, quầy hàng, bản đồ, đèn rọi, ống khói nhà máy…) và 24+ bối cảnh là danh sách phần có tham số màu; `custom:<tên>` trong bảng cảnh là một danh sách phần. Bối cảnh cũ của `scenes3.js` (phòng bảng, sàn giao dịch, trường quay…) chuyển vào đây.
- **Rationale**: kênh mẫu đổi bối cảnh mỗi 4,3 giây; dựng từ phần cho đủ số bối cảnh mà mã không phình.
- **Alternatives**: mỗi bối cảnh một khối SVG viết tay (đã thấy ở phim cũ: lặp mã, khó đổi màu theo luật).

## R8. Test an toàn GPU

- **Decision**: hai lớp.
  1. `test_sketch_gpu.py` quét mã `kit/` và `people/*/figure.js`: không có lệnh `A`/`a` trong chuỗi đường (`d=` hoặc `d:`), không có `rx=`/`rx:` trừ `ellipse`, và hình tô có viền dày phải vẽ qua `segOutline` (quét các path có `fill` khác `none` cùng `stroke-width` ≥ 6 mà có hơn 4 đỉnh).
  2. Test trang chụp `catalog.html` bằng GPU (khi `sh bin/studio status` có GPU) và bằng phần mềm, so từng ô; lệch trung bình > 6/255 ở ô nào thì báo ô đó; bỏ qua khi máy không có GPU.
- **Rationale**: ba lỗi đã gặp đều chỉ hiện trên GPU (cung không tô, góc bo vỡ, vệt X trên viền dày). Quét tĩnh bắt sớm, so ảnh bắt lỗi chưa biết.
- **Alternatives**: chỉ so ảnh (cần GPU, chậm); chỉ quét tĩnh (không bắt lỗi mới).

## R9. Đo tiếng động trong đoạn

- **Decision**: `analyze(audio, words, segments=None)`: khi có `segments` (từ `video.json`), chỉ giữ tiếng động và cửa sổ nhạc có thời điểm trong một đoạn, chia cho tổng thời lượng các đoạn. `sound_set` truyền `segments` của video. Thêm `learn sound <set> --recompute`: lọc lại từ `sound.json` đã lưu (thời điểm tiếng động và cửa sổ nhạc đã có), không cần video, vì bộ `sketch-ref` đã xoá video.
- **Rationale**: lỗi gốc là `words.json` chỉ phủ các đoạn, nên lời nói ngoài đoạn bị coi là tiếng động (EVIDENCE corrections #3).
- **Alternatives**: chép lời cả video (tốn, không cần cho phong cách).

## R10. Người dẫn chuyện và kênh

- **Decision**: vai `narrator` của bộ dựng đọc trang phục từ `channel.json` của phim (trường `hero` của specs/022: `hoodie`, `hair`, `hat`, `glasses`) nếu có; mặc định là Max (hoodie cam `#e8833a`, tóc nâu sẫm). `catalog.json → avoid_hero` để trống vì kênh mẫu không có nhân vật chính cố định.
- **Rationale**: dùng lại cơ chế kênh có sẵn (FR-015).
- **Alternatives**: trường riêng cho bộ dựng 2D (trùng lặp).
