# Contract: worker, container việc và bộ chuyển tiếp API

## Worker → container
- **Ảnh**: `studio-job:<phiên bản xưởng>`, dựng từ `deploy/job.Dockerfile`. Gồm ffmpeg 7, Chromium, Python, venv `tools/.venv`, thư viện ghim theo `library.lock`, `CLAUDE.md`, `.claude/skills/`, `bin/`, `tools/`. Các thư mục này chỉ đọc, chép vào `/studio`.
- **Gắn vào**: `/data/jobs/<id>` vào `/work`, có quyền ghi. Khi học bằng video tải lên, các tệp tải lên được chép sẵn vào `/work/references/<set>/videos/`.
- **Biến môi trường**:
  - `ANTHROPIC_BASE_URL=http://proxy:8780`
  - `ANTHROPIC_API_KEY=<mã riêng của việc>`: mã do bộ chuyển tiếp cấp, không phải khoá thật
  - `STUDIO_MODE=online`, `STUDIO_JOB=<id>`
- **Giới hạn**:
  - `--user 1000`, `--read-only` (trừ `/work` và `/tmp`), `--cap-drop ALL`, `--pids-limit 512`
  - CPU và RAM theo cài đặt (mặc định 4 CPU, 8 GB)
  - Mỗi lượt chạy tối đa 60 phút
- **Mạng**: mạng Docker `jobnet` (internal), chỉ tới dịch vụ `proxy`. Việc học từ YouTube dùng thêm `jobnet-yt`, đi qua bộ lọc ra ngoài chỉ cho các tên miền của YouTube và googlevideo.
- **Lệnh chạy**: `python /studio/tools/runner/agent.py`. Chương trình này gọi Claude Agent SDK với:
  - thư mục làm việc `/work`;
  - lời nhắc từ `input` của việc, hoặc quyết định của khách khi nối lại phiên;
  - nạp `CLAUDE.md` và các skill;
  - công cụ: đọc, ghi, sửa tệp và Bash; **không** có công cụ web, trừ khi `yt-dlp` chạy qua Bash.
- **Mã thoát**: 0 xong · 10 chờ khách (`agent.py` in ra mã phiên SDK) · khác là lỗi. Worker đọc `/work/.result.json` (`{status, session, film?, style?, error?}`).

## Container → xưởng
Bên trong container, các lệnh `sh bin/studio job …` và `review …` vẫn như giai đoạn 1 ([cli.md](../../003-studio-ui/contracts/cli.md)). Ở chế độ online, các lệnh này gọi `http://proxy:8780/internal/…` bằng mã của việc, thay cho việc ghi `.studio/`:
- `review request` tạo yêu cầu duyệt, rồi `agent.py` kết thúc lượt bằng mã thoát 10 (research R5).
- `review wait` bị tắt và in hướng dẫn kết thúc lượt.
- `job done` ghi kết quả. Worker kiểm chất lượng phim (research R14) rồi mới chép kết quả về thư mục của khách.
- `job fail "<lỗi>" --by studio|customer` ghi trạng thái cuối. Tác tử chọn `--by` theo bảng ở spec FR-006a; thiếu cờ thì tính là `studio`, tức nghiêng về phía khách. Cờ này chỉ có ở chế độ online.

## Bộ chuyển tiếp API
- **Nghe**: `proxy:8780`, chỉ trên mạng nội bộ của Docker.
- **`POST /v1/messages`**, cùng hình dạng Messages API:
  1. Kiểm mã của việc (còn hạn, việc đang `running`).
  2. Kiểm `cost_usd` của việc nhỏ hơn `job_cost_cap_usd`.
  3. Thay mã bằng khoá thật, gửi tới `api.anthropic.com`, trả nguyên phản hồi (kể cả khi phản hồi chạy dòng).
  4. Đọc `usage`, cộng chi phí vào Job và Usage day.

  Vượt trần chi phí của việc thì trả `429` và đánh dấu việc lỗi do xưởng (`failure_kind=studio`), khách được trả lượt. Lỗi `429`, `529` và `5xx` từ Anthropic được trả nguyên kèm `retry-after` để SDK tự thử lại (R13).
- **`/internal/jobs/{id}/…`** và **`/internal/reviews/…`**: phần của API dành cho lệnh trong container; chỉ cho mã của chính việc đó.
- **Ghi nhật ký**: chỉ ghi số token và chi phí, không ghi nội dung lời nhắc.

## Worker
- **Vòng lặp mỗi 2 giây**:
  1. Trong một giao dịch, chọn việc `queued` cũ nhất mà chủ của nó chưa có việc `running`, khi tổng số việc `running` còn dưới N.
  2. Đặt việc đó thành `running` và bật container.
- **Khởi động lại**: việc đang `running` mà không còn container thì chạy lại tối đa 1 lần (nối phiên nếu có). Lần thứ hai thì `failed`, lỗi do xưởng, trả lượt.
- **Thư**: khi việc chuyển sang `waiting_review` thì gửi `review_needed` (FR-023), nếu khách bật email.
- **Theo dõi**: lượt chạy nào không có phản hồi thành công từ Claude trong 30 phút thì dừng, tính là lỗi do xưởng (R13).
- **Dọn mỗi 15 phút**:
  - xoá video gốc, ảnh ghép và lời chép của các việc học đã kết thúc; giữ số đo và tối đa 6 khung hình bằng chứng (R10);
  - dừng các việc chờ duyệt quá hạn và gửi email;
  - xoá hẳn các tài khoản đã yêu cầu xoá đủ hạn;
  - gửi thư còn trong hàng.

## Quyền Docker của worker
Worker cần quyền tạo và dừng container. Quyền trực tiếp trên `/var/run/docker.sock` gần như là toàn quyền máy chủ, nên worker **không** gắn socket thật. Worker đi qua một bộ lọc socket (ví dụ `tecnativa/docker-socket-proxy`) chỉ cho phép các lệnh: tạo, chạy, xem, dừng, xoá container và đọc nhật ký của container. Thêm nữa, worker chỉ tạo container từ ảnh `studio-job:*`, và chỉ với các cờ ở mục "Giới hạn". Ghi rủi ro này ở Complexity Tracking của plan.
