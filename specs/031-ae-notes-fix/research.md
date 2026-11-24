# Research: Sửa ghi chú phim After Effects tự động trên app

## R1. Chiều kết nối phần lõi ↔ After Effects
- **Decision**: App desktop kéo việc từ phần lõi qua HTTP (`127.0.0.1:<cổng web>`), không có cổng nào mở trên Windows.
- **Rationale**: Cửa sổ app desktop đã tải giao diện từ `127.0.0.1` của WSL (localhostForwarding, `specs/015-desktop-shell/research.md`); chiều WSL→Windows không có trừ chế độ mạng mirrored. macOS: cùng cách, phần lõi chạy thẳng.
- **Alternatives**: WSL interop gọi `AfterFX.exe` (chỉ chạy trên máy phát triển có `/mnt/c`, không có trong bản Linux đóng gói, bị sandbox của agent chặn); thư mục chia sẻ + theo dõi tệp (khó báo tiến độ và lỗi).

## R2. Xác thực app desktop với phần lõi
- **Decision**: App desktop tạo khoá ngẫu nhiên 32 byte, ghi `CONFIG_DIR/bridge.json`, truyền `app start --bridge <tệp>` (như `--gate`); phần lõi đọc vào `STUDIO_AE_BRIDGE` và chỉ nhận `/api/v1/ae/bridge/*` khi header `X-CU-Bridge` khớp (so sánh hằng thời gian) và yêu cầu từ 127.0.0.1. Khoá đổi mỗi lần khởi động.
- **Rationale**: Không cần tài khoản hay phiên; tiến trình khác trên máy không có khoá thì không gọi được AE (SC-006).

## R3. Gói dựng (bundle) và cách AE chạy
- **Decision**: Phần lõi (lệnh `ae` trong việc) tạo `bundle.tar`: `kit/*.jsx` + `films/<tên>/ae/*.jsx` + `entry.jsx` (danh sách shot, tên tệp ra, thư mục làm việc được thay lúc chạy bằng biến `CU.WORK`). App desktop giải nén vào thư mục làm việc của máy (`<work>/<mã yêu cầu>/`), chạy entry, rồi `aerender -project … -comp "S<n>" -output <work>/out/S<n>.mp4` cho từng shot.
- **Windows**: `AfterFX.exe -r <entry.jsx>` gửi script vào AE đang chạy hoặc mở AE; chờ `log.txt` có `DONE`; tắt AfterFX trước khi `aerender` (kinh nghiệm: aerender báo "connection forcibly closed" hoặc treo khi AE GUI giữ project).
- **macOS**: `osascript -e 'tell application id "com.adobe.AfterEffects" to DoScriptFile "<entry>"'`; `aerender` ở thư mục ứng dụng AE.
- **Rationale**: Đúng cách đã chạy ổn trên phim tập luyện (`run.sh`, `fixshots.sh`); một project chỉ chứa các shot cần dựng nên nhanh (~10 s/shot).

## R4. Phát hiện AE và lỗi
- **Decision**: Tìm AE ở chỗ cài mặc định (`C:\Program Files\Adobe\Adobe After Effects 20XX\Support Files\AfterFX.exe`, `/Applications/Adobe After Effects 20XX/`), chọn bản mới nhất; người dùng có thể chọn đường dẫn trong cửa sổ "After Effects…". "Không tiến triển": entry phải ghi dòng `START` vào log trong 240 s (AE khởi động nguội mất khoảng 90 s); không tắt AE trước khi gửi script (tắt cưỡng bức làm AE dừng ở hộp thoại lần sau), chỉ tắt trước `aerender`, mỗi shot trong 5 phút; quá hạn thì dừng tiến trình AE của lượt (taskkill / kill), báo lỗi kèm log. Cần bật "Allow Scripts to Write Files and Access Network": nếu log không được ghi, báo đúng tên tuỳ chọn đó.

## R5. Ghép shot theo khung
- **Decision**: `tools/ae/splice.py` lấy từ `fixshots.sh`: cắt theo số khung (`trim=start_frame/end_frame`, `setpts=N/FPS/TB`), ép `fps` đầu ra, giữ tiếng gốc, mã hoá lại một lần cho nhiều shot (một lệnh ffmpeg cho mọi đoạn thay vì mỗi shot một lần).
- **Rationale**: Đã kiểm trên phim tập luyện: 4128 khung, 0 khung dưới 30 dB so với dựng lại toàn bộ.

## R6. Shot nào bị ảnh hưởng khi sửa phần chung
- **Decision**: `ae uses <phim> <hàm…>`: quét `shots_*.jsx` tìm lời gọi `CU.<hàm>` (và hàm gọi gián tiếp qua bảng gọi của `kit/`), in danh sách shot. Agent dùng khi sửa `kit/`.
- **Rationale**: Đủ cho ES3 không có module; sai sót chỉ dẫn tới dựng thừa shot, không thiếu (khi nghi ngờ thì liệt kê).

## R7. Lượt sửa ghi chú và kho
- **Decision**: Tạo việc `fix` ghi `lot = {job, notes: [mã…], since}` vào `shot-notes.json` của kho (tối đa 10 ghi chú mở theo thời gian trong phim). Worker chép phim vào thư mục việc (như việc sửa phim hiện có). Agent sửa shot, chạy `ae fix`, ghi trả lời vào sổ trong thư mục việc (`notes reply`). Khi việc xong, worker: `replace_video` lên phim trong kho (giữ bản trước), rồi với mỗi ghi chú của lượt, chép `reply`/`done` từ bản trong việc vào kho bằng `shotnotes.reply` (dùng `base` mới nhất, không đè ghi chú khác), xoá `lot`. Việc lỗi: chỉ xoá `lot`.
- **Rationale**: Giữ nguyên ranh giới ghi của agent; người dùng vẫn ghi chú trong lúc việc chạy (FR-012).

## R8. Phim AE mới (US5)
- **Decision**: Việc `film` có thêm `engine: "ae"`; `film_prompt` nhánh AE dặn agent: các bước chung (kịch bản, giọng, điểm duyệt, gói đăng) giữ nguyên; bước hình là bảng shot → `films/<tên>/ae/shots_*.jsx` dùng `tools/ae/kit` → `ae build` (qua cầu nối, có luật dàn cảnh) → `ae render` bản tổng → trộn tiếng (`kit/sound/mix` của xưởng hoặc `ffmpeg amix` với giọng) → `shots.json`. Không có kit/ của phong cách web trong phim AE.
- **Rationale**: Dùng lại toàn bộ luồng chung; chỉ thay phần hình.

## R9. Bài thử trên GitHub Actions
- **Decision**: `desktop/test/fake-ae.mjs` đóng vai `AfterFX` (đọc entry, ghi `log.txt` với `START`/`DONE`, kiểm khoá một lượt) và `aerender` (sinh mp4 ngắn bằng ffmpeg có sẵn trên runner, hoặc chép mp4 mẫu nhỏ trong `desktop/test/vectors/`). Smoke `ae`: fake core có hàng đợi giả, app desktop nhận một yêu cầu, dựng 2 shot giả, gửi kết quả.
- **Rationale**: Runner không có AE; vẫn kiểm được cầu nối đầu-cuối trên cả hai hệ điều hành.
