# Research: Xưởng phim online, bản dùng thử đầu tiên

Mỗi mục: **Decision** (chọn gì) · **Rationale** (vì sao) · **Alternatives** (đã cân nhắc gì).

## R1. Cách chạy Claude cho từng việc

- **Decision**: Mỗi việc chạy một tác tử Claude không giao diện, bằng **Claude Agent SDK cho Python** (`claude-agent-sdk`, chính là bộ máy của Claude Code dưới dạng thư viện). Tác tử có sẵn công cụ đọc, ghi, sửa tệp và Bash, và đọc `CLAUDE.md` cùng các skill hiện có của xưởng. Model `claude-opus-5-5` (mặc định của Anthropic: $4 / $20 mỗi triệu token vào/ra, đọc bộ nhớ đệm $0.20). Model nằm trong cài đặt, để chủ xưởng đổi sang `claude-sonnet-5-5` ($2 / $10) nếu muốn rẻ hơn. Tên các tuỳ chọn cụ thể (thư mục làm việc, công cụ được phép, số lượt tối đa, nối lại phiên) **PHẢI** kiểm lại trên tài liệu SDK (code.claude.com/docs/en/agent-sdk) khi implement.
- **Rationale**: Spec cần đủ tính năng như bản trên máy. Bản trên máy chính là Claude Code chạy `CLAUDE.md` và skill `style-learn`. Dùng đúng bộ máy đó thì không phải viết lại quy trình làm phim hay học phong cách (hiến pháp V, VI, IX).
- **Alternatives**:
  - **Managed Agents** (Anthropic chạy vòng lặp và hộp cát): phải dựng lại toàn bộ môi trường (ffmpeg 7, Chromium, thư viện, venv) trong hộp cát của Anthropic, và tải YouTube từ hộp cát đó khó kiểm soát. Có thể xem lại khi cần nhiều máy.
  - **Tự viết vòng lặp công cụ bằng Messages API**: phải tự làm lại phần Claude Code đã có (sửa tệp, Bash, ngữ cảnh dài, skill). Tốn công, dễ lệch với bản trên máy.

## R2. Cách ly mỗi việc

- **Decision**: Mỗi việc chạy trong **một container Docker riêng**, dựng từ một ảnh `studio-job` cố định:
  - Ảnh có sẵn ffmpeg 7, Chromium/Playwright, Python và các venv, và bản thư viện ghim theo `library.lock`.
  - Container chỉ thấy thư mục của việc đó (gắn vào `/work`), không thấy dữ liệu của khách khác (FR-027).
  - Chạy bằng người dùng không phải root, ổ gốc chỉ đọc, giới hạn CPU, RAM và thời gian.
  - Mạng ra ngoài chỉ tới bộ chuyển tiếp API (R3). Việc học từ YouTube được mở thêm tới các tên miền của YouTube.
- **Rationale**: Ý tưởng của khách là dữ liệu không tin được. Tác tử có Bash, nên cách ly bằng container là lớp chặn chính. Khách có cài lệnh lạ vào ý tưởng thì cũng chỉ đụng tới thư mục của chính họ.
- **Alternatives**: chỉ dùng người dùng Linux riêng cho mỗi việc (cách ly yếu, khó giới hạn mạng); máy ảo cho mỗi việc (chậm và đắt cho bản dùng thử).

## R3. Khoá API và đo chi phí

- **Decision**: Khoá API Claude **không** vào container. Container gọi Claude qua một **bộ chuyển tiếp** (proxy) chạy trên máy chủ, đặt bằng biến `ANTHROPIC_BASE_URL`, kèm một mã riêng cho từng việc. Bộ chuyển tiếp làm 4 việc:
  1. Gắn khoá thật vào yêu cầu.
  2. Đọc `usage` của mỗi phản hồi (token vào, ra, đọc và ghi bộ nhớ đệm) và nhân với bảng giá trong cài đặt để ghi chi phí của việc (FR-008).
  3. Từ chối khi việc vượt trần chi phí riêng của nó (cài đặt, mặc định $5). Khi đó việc lỗi do xưởng và khách được trả lượt.
  4. Thu hồi mã khi việc kết thúc.
- **Rationale**: Tác tử có Bash, nên nếu khoá nằm trong container thì có thể bị in ra hoặc gửi đi. Đo ở bộ chuyển tiếp cho chi phí đúng tới từng yêu cầu, không phụ thuộc vào việc tác tử tự báo.
- **Alternatives**: đưa khoá vào container và đọc tổng `usage` mà SDK trả về khi xong (lộ khoá, và không chặn được khi việc chạy quá tay); dùng khoá con riêng cho từng việc (phải quản lý khoá qua Admin API, nặng hơn cho bản dùng thử).

## R4. Hàng đợi và giới hạn chạy cùng lúc

- **Decision**: Một tiến trình **worker** riêng lấy việc từ cơ sở dữ liệu theo thứ tự nhận:
  - Chạy tối đa N việc cùng lúc (cài đặt, mặc định 2), và mỗi khách tối đa 1 việc (FR-008a).
  - Việc được nhận bằng một giao dịch có điều kiện, để hai worker không lấy trùng một việc.
  - Hàng đợi không cần dịch vụ riêng.
- **Rationale**: Một máy chủ, ít việc. Đây là cách đơn giản nhất mà vẫn chặn được việc chạy vượt mức (SC-009).
- **Alternatives**: Celery hoặc RQ với Redis (thêm một dịch vụ mà chưa cần); chạy việc ngay trong tiến trình web (khởi động lại web là mất việc).

## R5. Chờ khách (hỏi lại, duyệt) mà không tốn chi phí

- **Decision**: Khi tác tử cần khách trả lời (câu hỏi lại, duyệt kịch bản, duyệt phong cách lần 1 hoặc 2), nó tạo yêu cầu duyệt bằng `review request` như giai đoạn 1, rồi **kết thúc lượt chạy**:
  - Worker lưu mã phiên của SDK và trả chỗ chạy cho việc khác. Việc chuyển sang `waiting_review`.
  - Khi khách quyết định, việc vào lại hàng đợi. Worker **nối lại phiên** cũ (tính năng resume của Agent SDK; kiểm lại tên tuỳ chọn khi implement), đưa quyết định vào làm tin nhắn tiếp theo.
  - Thư mục của việc được giữ nguyên giữa các lượt.
- **Rationale**: FR-021 cần lúc chờ không tốn chi phí, mà ở bản online khách có thể duyệt sau nhiều giờ. Giữ container chạy chờ sẽ chiếm một trong N chỗ.
- **Alternatives**: giữ tác tử chờ bằng `review wait` như giai đoạn 1 (chiếm chỗ, và tốn tiền nếu chờ bằng cách hỏi lại liên tục); chạy lại từ đầu sau mỗi lần duyệt (tốn token và có thể ra kết quả khác).

## R6. Cơ sở dữ liệu

- **Decision**: **SQLite** (chế độ WAL) trong `/data/studio.db`.
  - Mọi thay đổi hạn mức, hàng đợi và chi phí chạy trong một giao dịch `BEGIN IMMEDIATE`, nên đúng khi có nhiều yêu cầu cùng lúc (SC-008).
  - `store.py` có thêm một phần cho chế độ online. Chế độ trên máy (giai đoạn 1) vẫn dùng tệp JSON như cũ.
- **Rationale**: Một máy chủ, ít ghi. SQLite không cần dịch vụ riêng (hiến pháp V), dễ sao lưu bằng một tệp, và chuyển sang PostgreSQL được khi cần nhiều máy.
- **Alternatives**: PostgreSQL (đúng cho nhiều máy, nhưng thêm một dịch vụ phải vận hành); giữ tệp JSON (khó làm giao dịch hạn mức đúng khi nhiều khách gửi cùng lúc).

## R7. Tài khoản và đăng nhập

- **Decision**:
  - **Mật khẩu**: email và mật khẩu, băm bằng `argon2-cffi`.
  - **Phiên đăng nhập**: cookie `HttpOnly`, `Secure`, `SameSite=Lax`; mã phiên ngẫu nhiên, lưu bản băm trong cơ sở dữ liệu, hết hạn sau 30 ngày.
  - **Chống giả mạo yêu cầu**: giữ header `X-Studio: 1` của giai đoạn 1, thêm kiểm `Origin`.
  - **Liên kết xác minh email và đặt lại mật khẩu**: mã ngẫu nhiên dùng một lần, chỉ lưu bản băm. Xác minh hết hạn sau 24 giờ, đặt lại mật khẩu sau 1 giờ.
  - **Giới hạn tần suất**: đếm theo IP và theo email trong cơ sở dữ liệu (FR-025).
  - **Tài khoản quản trị**: tạo bằng lệnh `sh bin/studio admin create <email>`.
- **Rationale**: Đúng phạm vi đã chốt: không đăng nhập bằng Google hay mạng xã hội, chỉ một vai trò quản trị.
- **Alternatives**: dịch vụ đăng nhập ngoài như Auth0 hay Clerk (thêm phụ thuộc và chi phí, mà bản dùng thử chưa cần); liên kết đăng nhập qua email không mật khẩu (spec đã chốt email và mật khẩu).

## R8. Email

- **Decision**: Gửi qua **SMTP** của một dịch vụ email giao dịch, chủ xưởng tự chọn (cấu hình bằng biến môi trường). Thư viện chuẩn `smtplib`. Một hàng thư trong cơ sở dữ liệu, gửi lại khi lỗi. Chạy thử thì ghi thư ra tệp thay vì gửi.
- **Rationale**: Không gắn với nhà cung cấp nào; đổi dịch vụ chỉ cần đổi biến môi trường.
- **Alternatives**: SDK riêng của từng nhà cung cấp (bị gắn với một hãng).

## R9. Kiểm nội dung ý tưởng

- **Decision**: Trước khi trừ lượt, gửi **một lệnh gọi Messages API** (cùng model trong cài đặt, effort `low`, dùng structured outputs) để phân loại ý tưởng: cho phép hoặc từ chối, kèm lý do (FR-013). Có từ chối thì không trừ lượt. Bản thân tác tử vẫn tuân hiến pháp trong lúc làm phim, ví dụ không nêu tên kênh.
- **Rationale**: Rẻ (vài trăm token), chạy trước khi tốn chi phí lớn, và có lý do để báo cho khách.
- **Alternatives**: để tác tử tự từ chối giữa chừng (đã tốn lượt và tiền); lọc bằng danh sách từ khoá (dễ sai cả hai chiều).

## R10. Tải từ YouTube và xoá video gốc

- **Decision**:
  - **Tải**: `yt-dlp` (đã có trong `requirements-learn-extra.txt`), chạy trong container của việc học. Video nằm trong `/work/references/<set>/videos`, không có đường nào ra web.
  - **Xoá**: khi việc học kết thúc, worker chạy lệnh dọn sẵn có (`learn clean`) và xoá thêm mọi tệp âm thanh hay video còn sót. Một tác vụ định kỳ mỗi 15 phút quét lại để chắc chắn video bị xoá chậm nhất sau 1 giờ (FR-019, SC-004).
  - **Lỗi tải**: YouTube chặn tải từ máy chủ thì việc lỗi, báo lý do và gợi ý tải video lên.
- **Rationale**: Dùng lại công cụ đã có và đáp ứng các điều kiện của hiến pháp 2.1.0.
- **Alternatives**: tải trên máy chủ chung rồi chép vào container (video nằm ngoài vùng cách ly, khó chắc là đã xoá).

## R11. Máy chủ và triển khai

- **Decision**:
  - **Máy chủ**: một máy chủ Linux thuê (Ubuntu 24.04, khoảng 8 vCPU và 16 GB RAM, vì dựng phim cần Chromium), nhà cung cấp do chủ xưởng chọn.
  - **Dịch vụ**: **Docker Compose** chạy 3 dịch vụ: `web` (FastAPI), `worker`, `caddy` (HTTPS tự động, FR-024). Bộ chuyển tiếp API là một phần của `web`, nghe trên mạng nội bộ của Docker.
  - **Dữ liệu**: nằm trong `/data`, sao lưu bằng cách chép tệp SQLite và thư mục phim.
- **Rationale**: Ít thành phần nhất mà vẫn có HTTPS và cách ly (hiến pháp V).
- **Alternatives**: Kubernetes (quá nặng cho một máy); nền tảng không máy chủ (không chạy được Chromium, ffmpeg và việc dài).

## R12. Giữ nguyên giai đoạn 1

- **Decision**:
  - Cùng một mã nguồn, chọn chế độ bằng biến `STUDIO_MODE=local|online`, mặc định `local`.
  - Chế độ `local` giữ nguyên mọi hành vi và test của 001–006: chỉ `127.0.0.1`, không đăng nhập, lưu tệp JSON.
  - Chế độ `online` bật tài khoản, cơ sở dữ liệu, worker và bộ chuyển tiếp.
  - Hình dạng dữ liệu của API v1 (việc, yêu cầu duyệt, quyết định) không đổi (FR-028); chỉ thêm điểm truy cập mới.
- **Rationale**: Chủ xưởng vẫn dùng xưởng trên máy như cũ. Cả 3 bộ test hiện có tiếp tục chạy.
- **Alternatives**: tách thành một dự án riêng (phải sửa hai nơi cho cùng một quy trình).
