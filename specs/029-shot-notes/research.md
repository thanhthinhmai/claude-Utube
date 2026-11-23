# Research: Ghi chú từng shot

## R1. Lưu ghi chú ở đâu

- **Decision**: Tệp `shot-notes.json` trong thư mục phim, ảnh trong `shot-notes/` cạnh đó.
- **Rationale**: Spec FR-008 yêu cầu Claude đọc thẳng được không cần app. Thư mục phim đã là đơn vị của mọi thứ (video, checks.json, publish/). Chế độ online đã tách thư mục theo người (`store.as_account`), nên quyền đọc ghi đi theo sẵn.
- **Alternatives considered**: Bảng SQLite của chế độ online (không có ở chế độ local, Claude phải gọi API mới đọc được); ghi vào `checks.json` (trộn với kết quả kiểm tra, dễ ghi đè lẫn nhau).

## R2. Chống mất thay đổi khi hai người cùng lưu

- **Decision**: Mỗi lần đọc trả về `base` = sha256 của nội dung tệp. Lưu (PUT toàn sổ) phải gửi `base`; không khớp thì trả 409 `changed` kèm sổ hiện tại. Giao diện áp lại thao tác vừa làm lên sổ mới rồi lưu lại một lần; vẫn lỗi thì báo người dùng tải lại. Ghi trong khoá tệp (`fcntl`) để hai yêu cầu đồng thời không xen nhau.
- **Rationale**: Cùng cách `--base` của `edit.py` (specs/026, mã 4 "nội dung đã đổi") mà người dùng đã quen; đơn giản, đủ cho nhóm nhỏ (SC-004).
- **Alternatives considered**: API theo từng thao tác (thêm/sửa/xoá ghi chú) không cần base: nhiều đường hơn, khó cho CLI; khoá theo phiên: phức tạp, dễ kẹt khoá.

## R3. Ảnh nhỏ của shot

- **Decision**: Cắt theo yêu cầu bằng ffmpeg (`-ss t -i video -frames:v 1 -vf scale=320:-2`), đệm ở `.shots/thumbs/<dấu video>/<chỉ số>_<a|b|c>.jpg`; dấu video = kích thước + mtime của tệp video, đổi video thì thư mục đệm mới, thư mục cũ bị xoá. Lần đầu cắt cả lượt bằng một tiến trình nền, giao diện hiện ô giữ chỗ tới khi ảnh có.
- **Rationale**: 40 shot × 3 ảnh ≈ 120 lần ffmpeg ~0,05–0,1 s mỗi lần trên máy xưởng → ≤ 15 s lần đầu (SC-002). Không cần lưu ảnh vào git.
- **Alternatives considered**: Sinh ảnh lúc dựng phim (không có cho phim cũ, phim AE); ảnh động theo thời gian bằng `<video>` (nặng trình duyệt với 120 phần tử).

## R4. Phát riêng một shot

- **Decision**: Trên `<video>` hiện có: đặt `currentTime = t0`, `play()`, nghe `timeupdate` và theo dõi bằng `requestAnimationFrame` để dừng khi `currentTime ≥ t1 − 0,03`.
- **Rationale**: `timeupdate` chỉ bắn ~4 lần/giây (có thể trễ 0,25 s); kiểm theo khung vẽ cho sai lệch ≤ 1 khung (≤ 0,04 s), đạt ±0,2 s (SC-003).
- **Alternatives considered**: Media Fragments `#t=a,b` (trình duyệt xử lý không đều, không phát lại được).

## R5. Mốc shot cho phim web

- **Decision**: (a) `record.mjs` đã đọc `window.SHOTS`; sau khi ghép video thì ghi `out/shots.json`; tầng 4 `qc` (chạy sau khi thư viện ghép tiếng ra `<tên>.mp4`) chép nó cạnh video của phim khi độ dài khớp, nếu không thì chạy `shots export`. Không sửa `mux.sh` của thư viện (hiến pháp VI). (b) Lệnh `sh bin/studio shots export <phim> [--dir D]` mở trang phim bằng `plan.mjs` có sẵn để lấy `SHOTS` và `DUR`, so với độ dài video (ffprobe), ghi `shots.json`. Không dựng lại hình.
- **Rationale**: Dùng đúng dữ liệu tầng 1 (specs/020) đã kiểm; phim cũ có mốc shot trong vài giây (FR-003a).
- **Alternatives considered**: Dò cắt cảnh từ video (sai với chuyển cảnh mờ, phim không cần).

## R6. Mốc shot cho phim After Effects

- **Decision**: Bước ghép bản tổng của dự án AE (comp MASTER đặt các shot nối nhau) ghi `shots.json` theo cùng định dạng (inPoint/outPoint của từng lớp shot), ghi ra cạnh video khi render. Đây là mã của phim tập luyện (`films/ae-crayon-test/ae/build_core.jsx`, không vào git); xưởng chỉ định nghĩa định dạng (contracts/files.md) và `shots export` không dùng cho phim AE.
- **Rationale**: Bản tổng biết chính xác mốc từng shot; khớp ≤ 1 khung (SC-005).

## R7. Bản video trước

- **Decision**: `sh bin/studio film replace <phim> <video mới> [--shots <tệp>] [--dir D]`: đổi tên video hiện có thành `<tên>.prev.mp4` và `shots.json` thành `shots.prev.json` (xoá bản prev cũ), rồi chuyển video mới vào bằng `os.replace` (inode mới, không đụng bản hard link trong dự án). API phục vụ `GET /films/{name}/video?prev=1` và `shots?prev=1`.
- **Rationale**: Spec chọn giữ đúng một bản (câu 3). Đổi tên thay vì chép giữ dung lượng thấp.

## R8. Thư mục phim mà lệnh của Claude dùng

- **Decision**: Lệnh `notes`, `film replace`, `shots export` nhận `--dir` rõ ràng; không có thì dùng bản phim trong kho của chủ xưởng khi app đang chạy và có phim đó (như `link_film` của `studio_cli.py`), nếu không thì `films/<phim>` của dự án. Lệnh in ra thư mục đã chọn.
- **Rationale**: Ghi chú được viết trên app nằm trong kho của app; Claude phải đọc đúng bản đó.

## R9. Ảnh dán Ctrl+V

- **Decision**: Giao diện bắt sự kiện `paste` trên ô ghi chú, lấy `clipboardData.items` loại `image/*`, tải lên `POST /films/{name}/notes/images` (multipart). Máy chủ kiểm byte đầu (PNG `89 50 4E 47`, JPEG `FF D8 FF`, WebP `RIFF....WEBP`) và cỡ ≤ 10 MB, đặt tên `img-<12 ký tự hex ngẫu nhiên>.<đuôi>`. Ảnh không được sổ nào nhắc tới sau 1 giờ thì bị dọn khi lưu sổ.
- **Rationale**: Không tin tên tệp hay loại MIME của trình duyệt; tên ngẫu nhiên chặn đường dẫn lạ (SC-007, SC-008).
