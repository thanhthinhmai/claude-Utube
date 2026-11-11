# Research: Chế độ máy chủ trên một máy (014)

## R1. Khởi động và giám sát

**Decision**: `app start [--data D] [--web-port N] [--proxy-port N] [--foreground]` làm lần lượt:
1. Kiểm công cụ (R8).
2. Chọn thư mục dữ liệu:
   - mặc định: `$XDG_DATA_HOME/claude-utube`, hoặc `~/.local/share/claude-utube`; macOS là `~/Library/Application Support/ClaudeUtube`;
   - từ chối thư mục nằm trong thư mục dự án, hoặc thư mục không ghi được.
3. Nếu `host.lock` đang bị giữ: in "already running" cùng địa chỉ, rồi thoát 0 (FR-010).
4. Chọn cổng trống: giao diện thử 8790–8799, proxy thử 8780–8789 (FR-014).
5. Tách tiến trình giám sát: `python -m studio.host supervise …` với `start_new_session=True`.

Tiến trình giám sát:
- giữ `host.lock` (flock) suốt đời nó, và ghi `host.json`;
- mở 3 tiến trình con với `STUDIO_MODE=online`, `STUDIO_DATA`, `STUDIO_OWNER_UNLIMITED=1`, `STUDIO_PROXY=http://127.0.0.1:<proxy>`, `RUNNER=local`; giao diện là `uvicorn studio.server:create_app --factory --host 127.0.0.1 --port <web>`;
- đọc stdout và stderr của mỗi tiến trình con, ghi vào `logs/<phần>.log` bằng `RotatingFileHandler(maxBytes=10 MB, backupCount=5)` (FR-013);
- tiến trình con nào thoát thì mở lại sau 2 giây; mở lại quá 5 lần trong 60 giây thì dừng hẳn và ghi lỗi vào `host.json`;
- nhận SIGTERM thì gửi SIGTERM cho các tiến trình con, chờ 8 giây rồi SIGKILL cả nhóm, xoá `host.json` và con trỏ, rồi nhả khoá.

`app start` đợi `/api/health` của giao diện trả lời (tối đa 30 giây), rồi in `URL: http://127.0.0.1:<web>`. `--foreground` chạy tiến trình giám sát ngay trong lệnh, dành cho vỏ desktop và cho test.

**Alternatives considered**:
- systemd hay launchd: không có trên mọi máy, và vỏ desktop cần tự quản lý tiến trình.
- Docker compose: chính là thứ 014 muốn bỏ.

## R2. Dừng an toàn

**Decision**: `app stop [--data D] [--force]`:
1. Đọc `host.json`; không có hoặc pid đã chết thì báo "not running" và thoát 0.
2. Mở cơ sở dữ liệu (đọc) và tìm các việc có trạng thái `running`, `queued` hay `waiting_review` mà có `charged` (việc của worker). Việc `running` mà không có `--force` thì từ chối, liệt kê tên việc, thoát 1 (FR-011).
3. Có `--force` thì đánh dấu các việc `running` là `stopped` ("Stopped when the studio was closed").
4. SIGTERM tiến trình giám sát, đợi tối đa 15 giây cho tới khi khoá được nhả.

Việc `queued` vẫn giữ trong hàng đợi và chạy khi mở lại.

## R3. Nâng cấp dữ liệu

**Decision**: Trong `db.init()`, nếu số phiên bản lưu trong cơ sở dữ liệu nhỏ hơn `SCHEMA_VERSION` thì chép tệp cơ sở dữ liệu thành `backup/studio-<phiên bản cũ>-<thời điểm>.db` (dùng `sqlite3 backup()`, an toàn khi đang mở) trước khi chạy các lệnh nâng cấp có sẵn. Bản VPS cũng được lợi từ việc này.

## R4. Chủ xưởng không giới hạn phim

**Decision**: `accounts.setup()` đọc `STUDIO_OWNER_UNLIMITED=1` để đặt `quota_films = 1000` và `quota_learns = 1000` cho tài khoản chủ xưởng (mức cao nhất của 007). Đây là cấu hình khi tạo tài khoản, không phải nhánh logic trong phần tính hạn mức (FR-004). Trần token của mỗi việc vẫn giữ.

## R5. Agent không có container

**Decision**:
- **Ghi tệp**: `agent.py` truyền `can_use_tool`. Khi công cụ là `Write`, `Edit` hay `NotebookEdit` và đường dẫn đã giải (resolve) nằm ngoài `WORK`, thì từ chối kèm lý do "only the job folder can be written". Lớp này áp cho cả bản Docker; ở đó vốn không có gì để ghi ngoài thư mục việc, nên hành vi không đổi.
- **Bash**: có `STUDIO_AGENT_SANDBOX=1` (chế độ máy chủ đặt cờ này) thì `ClaudeAgentOptions(sandbox=…)` bật cách ly Bash của Claude Code, chỉ cho ghi trong `WORK` và thư mục tạm.
- **Kiểm khi implement (T001)**: sandbox của Claude Code chạy được trong WSL2 không (Linux cần bubblewrap). Không chạy được thì `app start` in một dòng cảnh báo, rồi chạy không có sandbox. Spec đã chấp nhận rủi ro này: người dùng tự chạy trên máy của họ.
- Thư mục studio (`add_dirs`) vẫn đọc được, để agent đọc thư viện và hướng dẫn.

## R6. Nhập dữ liệu

**Decision**: `app import [--from P] [--data D]`:
- cần chủ xưởng đã được tạo, nếu chưa thì thoát 2 với hướng dẫn mở app để tạo;
- với mỗi mục con trực tiếp của `P/films`, `P/my-styles` và `P/channels` (kể cả tệp bị git bỏ qua): chưa có ở `accounts/<chủ xưởng>/<cùng chỗ>` thì `copytree`, đã có thì bỏ qua;
- in số mục đã chép và đã bỏ qua; không đụng tới `P`.

## R7. Luồng chat ghi vào máy chủ

**Decision**:
- **Con trỏ**: `~/.config/claude-utube/host.json` = `{data, pid, web, proxy, project}`, do tiến trình giám sát ghi và xoá.
- `studio_cli` (`job …` và `review …`) ở chế độ local mà thấy con trỏ, đúng `project` là thư mục dự án hiện tại, và `pid` còn sống, thì đặt `STUDIO_MODE=online` và `STUDIO_DATA=<data>` cho chính tiến trình đó trước khi import `studio`, rồi ghi thẳng vào cơ sở dữ liệu (SQLite ở chế độ WAL cho phép vừa đọc vừa ghi).
- **Chủ việc** = chủ xưởng (tài khoản admin đầu tiên).
- Việc của luồng chat không có `charged`, nên worker không động tới (`claim` chỉ lấy việc `queued`; `recover` bỏ qua việc không có `charged`).
- `job done --film X`: nếu `accounts/<chủ xưởng>/films/X` chưa có thì tạo liên kết tới `<dự án>/films/X`.
- `review request` và `review wait` dùng `reviews` như bản online; trang duyệt của app quyết định được.
- Không có máy chủ chạy thì mọi thứ như cũ (sổ việc `.studio/`).

## R8. Kiểm công cụ

**Decision**: `app start` kiểm:
- Python của xưởng có `fastapi`, `uvicorn` và `claude_agent_sdk` (gói `deps ui` và `deps online`);
- `ffmpeg` và `ffprobe`; `node`;
- thư viện đã cài (`lib/lemo-opuscar`);
- có Claude Code (đi kèm SDK, hoặc `claude` trên PATH).

Thiếu thứ gì thì in từng dòng `✗ <tên>: sh bin/studio deps …`, rồi thoát 2.
